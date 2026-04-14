"""
RAG Engine (Retrieval-Augmented Generation)
负责长期记忆的检索、安全过滤及上下文增强
"""

import re
from typing import List, Dict, Any, Optional
from state.manager import StateManager

class RAGEngine:
    """RAG 引擎：连接状态管理与 LLM，提供安全的上下文增强"""
    
    # 不适当内容关键词列表 (简化版，实际生产建议使用更完善的库)
    INAPPROPRIATE_PATTERNS = [
        r"\b(hate|kill|bomb|terrorist|nsfw|porn|sex)\b",
        r"\b(attack|hack|exploit|malware|virus)\b",
        r"\b(password|secret_key|api_key)\s*[:=]\s*['\"][^'\"]{8,}['\"]", # 潜在硬编码密钥
    ]
    
    # 代码生成安全提示
    SAFE_CODE_INSTRUCTION = (
        "IMPORTANT: When generating code, strictly avoid using real secrets, "
        "hardcoded credentials, or malicious patterns. Use placeholders like "
        "'YOUR_API_KEY' instead. Do not output any sensitive information."
    )

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.INAPPROPRIATE_PATTERNS]

    def is_content_safe(self, text: str) -> bool:
        """
        检查内容是否安全。
        如果发现不适当内容，返回 False (静默失败，不输出具体原因)。
        """
        if not text:
            return True
        
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return False
        return True

    def retrieve_context(self, query: str, top_k: int = 3, category_filter: Optional[List[str]] = None) -> str:
        """
        检索长期记忆并构建上下文字符串。
        自动过滤不安全的内容片段。
        """
        memories = self.state_manager.retrieve_relevant_memories(
            query=query, 
            top_k=top_k * 2, # 多取一些以防被过滤
            category_filter=category_filter
        )
        
        safe_memories = []
        for mem in memories:
            content = mem.get('content', '')
            # 安全检查：如果不适当，直接跳过，不记录也不输出
            if self.is_content_safe(content):
                safe_memories.append(mem)
            
            # 如果过滤后数量足够，提前退出
            if len(safe_memories) >= top_k:
                break
        
        if not safe_memories:
            return ""
        
        # 构建上下文字符串
        context_parts = []
        for i, mem in enumerate(safe_memories, 1):
            timestamp = mem.get('timestamp', 'Unknown')
            content = mem.get('content', '')
            source = mem.get('source', 'Memory')
            
            context_parts.append(
                f"[Memory {i}] (Time: {timestamp}, Source: {source})\n{content}"
            )
        
        return "\n\n".join(context_parts)

    def augment_prompt(self, base_prompt: str, query: str, is_code_generation: bool = False) -> str:
        """
        增强 Prompt：注入检索到的长期记忆和安全指令。
        """
        # 1. 检索相关记忆 (优先检索用户画像和业务事实)
        relevant_context = self.retrieve_context(
            query=query, 
            top_k=3, 
            category_filter=['user_profile', 'business_fact', 'reflection']
        )
        
        augmented_parts = []
        
        # 2. 添加安全指令 (如果是代码生成任务)
        if is_code_generation:
            augmented_parts.append(self.SAFE_CODE_INSTRUCTION)
        
        # 3. 添加检索到的上下文
        if relevant_context:
            memory_section = (
                "### Long-Term Memory Context ###\n"
                "The following information is retrieved from your long-term memory. "
                "Use it to personalize your response and maintain consistency.\n"
                f"{relevant_context}\n"
                "### End of Memory Context ###\n"
            )
            augmented_parts.append(memory_section)
        
        # 4. 拼接最终 Prompt
        if augmented_parts:
            return "\n\n".join(augmented_parts) + "\n\n" + base_prompt
        
        return base_prompt

    def process_response(self, response: str) -> Optional[str]:
        """
        后处理：再次检查 LLM 生成的回复是否安全。
        如果不安全，返回 None (调用方需处理为空的情况，不输出错误信息)。
        """
        if self.is_content_safe(response):
            return response
        return None
