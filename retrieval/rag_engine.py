"""
RAG 检索增强生成模块
- 长期记忆检索：从 StateManager 的长期记忆中检索相关信息
- 外部知识库检索：支持加载本地文档（PDF, MD, TXT）
- 智能过滤：自动跳过不适当内容
- 上下文注入：将检索结果注入 Agent Prompt
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_EMBEDDING = True
except ImportError:
    HAS_EMBEDDING = False

from config import Config


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    source: str  # 'long_term_memory', 'knowledge_base'
    key: Optional[str] = None
    score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class ContentFilter:
    """内容过滤器 - 检测并跳过不适当内容"""
    
    # 不适当内容关键词模式
    INAPPROPRIATE_PATTERNS = [
        r'\b(inappropriate|offensive|nsfw|explicit|adult)\b',
        r'\b(hate|discrimination|harassment|bullying)\b',
        r'\b(violence|gore|blood|kill|murder)\b',
        r'\b(self[- ]?harm|suicide|cutting)\b',
        r'\b(illegal|drugs|weapon|bomb)\b',
    ]
    
    def __init__(self):
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.INAPPROPRIATE_PATTERNS
        ]
    
    def is_appropriate(self, text: str) -> bool:
        """检查文本是否适当，返回 True 表示适当，False 表示不适当"""
        if not text or len(text.strip()) == 0:
            return False
        
        # 检查关键词
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return False
        
        # 检查长度合理性（避免过短或过长）
        if len(text) < 5 or len(text) > 50000:
            return False
        
        return True
    
    def filter_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """过滤掉不适当的检索结果"""
        return [r for r in results if self.is_appropriate(r.content)]


class KnowledgeBaseLoader:
    """知识库加载器 - 支持多种文档格式"""
    
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.markdown'}
    
    def __init__(self, base_path: str = "./knowledge_base"):
        self.base_path = base_path
        self.documents: Dict[str, str] = {}  # file_path -> content
        self.chunks: List[Dict[str, Any]] = []  # 分块后的文档
        
    def load_directory(self, recursive: bool = True) -> int:
        """加载目录下的所有支持文档"""
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)
            return 0
        
        loaded_count = 0
        for root, _, files in os.walk(self.base_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            self.documents[file_path] = content
                            # 简单分块（按段落）
                            chunks = self._chunk_document(content, file_path)
                            self.chunks.extend(chunks)
                            loaded_count += 1
                    except Exception as e:
                        print(f"⚠️ 加载文档失败 {file_path}: {e}")
            
            if not recursive:
                break
        
        return loaded_count
    
    def _chunk_document(self, content: str, source: str, chunk_size: int = 500) -> List[Dict[str, Any]]:
        """将文档分块"""
        chunks = []
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', content)
        
        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += "\n" + para
            else:
                if current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'source': source,
                        'type': 'knowledge_base'
                    })
                current_chunk = para
        
        if current_chunk:
            chunks.append({
                'content': current_chunk.strip(),
                'source': source,
                'type': 'knowledge_base'
            })
        
        return chunks
    
    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """获取所有文档块"""
        return self.chunks


class RAGRetriever:
    """RAG 检索器 - 整合长期记忆和外部知识库"""
    
    def __init__(self, state_manager=None, knowledge_base_path: str = "./knowledge_base"):
        self.state_manager = state_manager
        self.content_filter = ContentFilter()
        self.kb_loader = KnowledgeBaseLoader(knowledge_base_path)
        
        # 初始化嵌入模型
        if HAS_EMBEDDING:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                self.has_embedder = True
            except Exception as e:
                print(f"⚠️ 无法加载嵌入模型：{e}，将使用关键词匹配")
                self.has_embedder = False
        else:
            self.has_embedder = False
            print("⚠️ 未安装 sentence-transformers，将使用关键词匹配")
        
        # 缓存知识库向量
        self.kb_embeddings = None
        self.kb_chunks = []
        
    def initialize_knowledge_base(self) -> int:
        """初始化知识库并计算向量"""
        count = self.kb_loader.load_directory()
        self.kb_chunks = self.kb_loader.get_all_chunks()
        
        if self.has_embedder and self.kb_chunks:
            texts = [chunk['content'] for chunk in self.kb_chunks]
            self.kb_embeddings = self.embedder.encode(texts, show_progress_bar=False)
        
        return count
    
    def _embed_query(self, query: str) -> np.ndarray:
        """将查询转换为向量"""
        if self.has_embedder:
            return self.embedder.encode([query])[0]
        else:
            # 降级为简单的词频向量（用于关键词匹配）
            return np.zeros(384)  # 占位符
    
    def retrieve_from_long_term_memory(
        self, 
        query: str, 
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[RetrievalResult]:
        """从长期记忆中检索"""
        if not self.state_manager or not self.has_embedder:
            return []
        
        results = []
        query_embedding = self._embed_query(query)
        
        # 遍历长期记忆中的所有键
        for key, value in self.state_manager.long_term_memory.items():
            try:
                # 获取键的向量（如果已缓存）
                key_embedding = self.state_manager.key_embeddings.get(key)
                
                if key_embedding is not None:
                    # 计算相似度
                    similarity = cosine_similarity(
                        [query_embedding], 
                        [key_embedding]
                    )[0][0]
                    
                    if similarity >= threshold:
                        content = str(value)
                        
                        # 内容过滤：不适当内容直接跳过
                        if not self.content_filter.is_appropriate(content):
                            continue
                        
                        results.append(RetrievalResult(
                            content=content,
                            source='long_term_memory',
                            key=key,
                            score=float(similarity),
                            metadata={'memory_type': self.state_manager._get_value_type(value)}
                        ))
            except Exception as e:
                # 单个键检索失败不影响整体
                continue
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def retrieve_from_knowledge_base(
        self, 
        query: str, 
        top_k: int = 5,
        threshold: float = 0.6
    ) -> List[RetrievalResult]:
        """从外部知识库检索"""
        if not self.kb_chunks or not self.has_embedder:
            return []
        
        results = []
        query_embedding = self._embed_query(query)
        
        if self.kb_embeddings is not None:
            similarities = cosine_similarity(
                [query_embedding], 
                self.kb_embeddings
            )[0]
            
            for idx, score in enumerate(similarities):
                if score >= threshold:
                    chunk = self.kb_chunks[idx]
                    content = chunk['content']
                    
                    # 内容过滤：不适当内容直接跳过
                    if not self.content_filter.is_appropriate(content):
                        continue
                    
                    results.append(RetrievalResult(
                        content=content,
                        source='knowledge_base',
                        key=chunk['source'],
                        score=float(score),
                        metadata={'file': chunk['source']}
                    ))
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        sources: List[str] = None,
        threshold: float = 0.6
    ) -> List[RetrievalResult]:
        """
        统一检索接口
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            sources: 检索源 ['long_term_memory', 'knowledge_base']，None 表示全部
            threshold: 相似度阈值
        
        Returns:
            检索结果列表（已过滤不适当内容）
        """
        if sources is None:
            sources = ['long_term_memory', 'knowledge_base']
        
        all_results = []
        
        if 'long_term_memory' in sources:
            ltm_results = self.retrieve_from_long_term_memory(query, top_k, threshold)
            all_results.extend(ltm_results)
        
        if 'knowledge_base' in sources:
            kb_results = self.retrieve_from_knowledge_base(query, top_k, threshold)
            all_results.extend(kb_results)
        
        # 去重（基于内容哈希）
        seen_hashes = set()
        unique_results = []
        for result in all_results:
            content_hash = hashlib.md5(result.content.encode()).hexdigest()
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append(result)
        
        # 重新排序并截取
        unique_results.sort(key=lambda x: x.score, reverse=True)
        return unique_results[:top_k]
    
    def format_context_for_prompt(
        self, 
        results: List[RetrievalResult],
        max_length: int = 2000
    ) -> str:
        """
        将检索结果格式化为 Prompt 上下文
        
        自动跳过不适当内容，只保留相关信息
        """
        if not results:
            return ""
        
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(results, 1):
            # 双重检查内容适当性
            if not self.content_filter.is_appropriate(result.content):
                continue
            
            source_label = "长期记忆" if result.source == 'long_term_memory' else "知识库"
            snippet = result.content[:500]  # 限制单条长度
            
            part = f"[{source_label} {i}] (相关度：{result.score:.2f})\n{snippet}"
            
            if total_length + len(part) > max_length:
                break
            
            context_parts.append(part)
            total_length += len(part) + 2
        
        if not context_parts:
            return ""
        
        return "\n\n".join(context_parts)


# 全局 RAG 实例（延迟初始化）
_rag_instance: Optional[RAGRetriever] = None


def get_rag_retriever(state_manager=None) -> RAGRetriever:
    """获取全局 RAG 检索器实例"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGRetriever(state_manager=state_manager)
        _rag_instance.initialize_knowledge_base()
    elif state_manager is not None and _rag_instance.state_manager != state_manager:
        _rag_instance.state_manager = state_manager
    return _rag_instance


def inject_rag_context(
    agent_type: str,
    query: str,
    state_manager=None,
    max_context_length: int = 1500
) -> str:
    """
    为 Agent 注入 RAG 上下文
    
    Args:
        agent_type: Agent 类型（用于调整检索策略）
        query: 当前查询/任务描述
        state_manager: 状态管理器实例
        max_context_length: 最大上下文长度
    
    Returns:
        格式化后的上下文字符串（如无不适当内容则可能为空）
    """
    retriever = get_rag_retriever(state_manager)
    
    # 根据 Agent 类型调整检索策略
    if agent_type in ['ProfileAgent', 'OrchestratorAgent']:
        # 用户画像相关：优先检索长期记忆
        sources = ['long_term_memory']
        threshold = 0.65
    elif agent_type in ['DestinationAgent', 'ItineraryAgent']:
        # 目的地和行程：混合检索
        sources = ['long_term_memory', 'knowledge_base']
        threshold = 0.6
    else:
        # 其他 Agent：默认策略
        sources = ['long_term_memory', 'knowledge_base']
        threshold = 0.65
    
    results = retriever.retrieve(query, top_k=5, sources=sources, threshold=threshold)
    
    # 格式化上下文（自动过滤不适当内容）
    context = retriever.format_context_for_prompt(results, max_length=max_context_length)
    
    if context:
        return f"\n\n📚 相关信息:\n{context}\n"
    else:
        # 无相关内容或所有内容都被过滤，返回空字符串
        return ""
