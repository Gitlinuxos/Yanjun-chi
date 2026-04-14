"""
状态管理器 - 维护共享黑板和 KV-Cache
"""
import json
import hashlib
import time
import heapq
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .models import (
    TravelPlanState, UserProfile, Destination, StatePatch, StagingArea, 
    ConflictInfo, MemoryEntry
)
from config import (
    CACHE_TTL_WEATHER, CACHE_TTL_TRANSPORT, CACHE_TTL_GENERAL,
    CACHE_SIMILARITY_THRESHOLD
)


class SimpleEmbedding:
    """简易向量化器 (用于演示，生产环境应使用真实 Embedding 模型)"""
    
    def __init__(self, dim: int = 128):
        self.dim = dim
        self._cache: Dict[str, np.ndarray] = {}
    
    def encode(self, text: str) -> np.ndarray:
        """将文本转换为向量 (基于哈希的简易实现)"""
        if text in self._cache:
            return self._cache[text]
        
        # 使用哈希生成确定性向量
        hash_bytes = hashlib.md5(text.encode()).digest()
        vector = np.array([
            (hash_bytes[i % 16] - 128) / 128.0 
            for i in range(self.dim)
        ], dtype=np.float32)
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        self._cache[text] = vector
        return vector


class CacheEntry:
    """缓存条目"""
    
    def __init__(self, query: str, result: Any, ttl: int, vector: np.ndarray):
        self.query = query
        self.result = result
        self.vector = vector
        self.created_at = time.time()
        self.ttl = ttl
        self.hit_count = 0
    
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl
    
    def similarity(self, other_vector: np.ndarray) -> float:
        """计算与另一个向量的相似度"""
        return cosine_similarity(
            self.vector.reshape(1, -1),
            other_vector.reshape(1, -1)
        )[0][0]


class StateManager:
    """
    状态管理器
    - 维护旅行计划共享状态
    - 提供 KV-Cache 语义检索
    - 实现临时区 (Staging Area) 和两阶段提交
    - 管理长期记忆 (衰减、冲突解决、优先级写回)
    """
    
    # 记忆类别优先级 (高价值信息优先写回)
    MEMORY_PRIORITY = {
        "user_profile": 1.0,      # 用户画像：最高优先级
        "identity": 0.95,         # 身份属性
        "business_fact": 0.9,     # 业务事实
        "reflection": 0.85,       # LLM 反思结果
        "general": 0.5            # 一般信息：最低优先级
    }
    
    # 不同类别的衰减率配置
    MEMORY_DECAY_RATES = {
        "user_profile": 0.005,    # 用户画像衰减慢
        "identity": 0.008,
        "business_fact": 0.01,
        "reflection": 0.02,       # 反思结果衰减较快
        "general": 0.03           # 一般信息衰减最快
    }
    
    def __init__(self):
        # 共享状态
        self.state = TravelPlanState()
        
        # KV-Cache: key -> CacheEntry
        self.cache: Dict[str, CacheEntry] = {}
        
        # 向量化器
        self.embedder = SimpleEmbedding()
        
        # 缓存锁 (防止并发重复请求)
        self._pending_requests: Dict[str, bool] = {}
        
        # 临时区 (Staging Area)
        self.staging_area: Optional[StagingArea] = None
        
        # 状态版本哈希 (用于乐观锁)
        self._version_hash: str = self._compute_state_hash()
        
        # 长期记忆索引：memory_id -> MemoryEntry
        self.long_term_memories: Dict[str, MemoryEntry] = {}
        
        # 记忆写入队列 (按优先级排序)
        self._memory_write_queue: List[Tuple[float, MemoryEntry]] = []
    
    def _compute_state_hash(self) -> str:
        """计算当前状态的哈希值"""
        state_json = self.state.model_dump_json()
        return hashlib.sha256(state_json.encode()).hexdigest()
    
    def get_state(self) -> TravelPlanState:
        """获取当前状态"""
        return self.state
    
    def get_version_hash(self) -> str:
        """获取当前状态版本哈希"""
        return self._version_hash
    
    def update_profile(self, profile: UserProfile):
        """更新用户画像"""
        self.state.user_profile = profile
        self.state.updated_at = datetime.now()
        self._version_hash = self._compute_state_hash()
    
    def add_destination(self, dest: Destination):
        """添加推荐目的地"""
        self.state.recommended_destinations.append(dest)
        self.state.updated_at = datetime.now()
        self._version_hash = self._compute_state_hash()
    
    def select_destination(self, name: str) -> bool:
        """选择目的地"""
        for dest in self.state.recommended_destinations:
            if dest.name == name:
                self.state.selected_destination = dest
                self.state.updated_at = datetime.now()
                self._version_hash = self._compute_state_hash()
                return True
        return False
    
    # ========== 临时区 (Staging Area) 管理方法 ==========
    
    def create_staging_area(self) -> StagingArea:
        """创建新的临时区"""
        if self.staging_area and not self.staging_area.is_locked:
            # 如果已有未提交的临时区，先清空
            self.staging_area.clear()
        
        self.staging_area = StagingArea(
            version_hash=self._version_hash,
            is_locked=True
        )
        return self.staging_area
    
    def submit_patch(self, patch: StatePatch) -> Tuple[bool, Optional[ConflictInfo]]:
        """
        提交补丁到临时区 (Phase 1 of 2PC)
        返回：(是否成功，冲突信息)
        """
        if not self.staging_area:
            return False, ConflictInfo(
                patch_id_1="none",
                patch_id_2="none",
                path="none",
                reason="Staging area not initialized"
            )
        
        # 检查版本一致性
        if patch.base_version_hash != self._version_hash:
            return False, ConflictInfo(
                patch_id_1=patch.get_patch_id(),
                patch_id_2="current_state",
                path=patch.target_path,
                reason="version_mismatch",
                resolution="Please fetch latest state and retry"
            )
        
        # 添加到临时区
        self.staging_area.add_patch(patch)
        return True, None
    
    def check_conflicts(self) -> List[ConflictInfo]:
        """检查临时区内的冲突"""
        if not self.staging_area:
            return []
        
        conflicts = []
        conflicting_patches = self.staging_area.get_conflicting_patches()
        
        for patch1, patch2 in conflicting_patches:
            conflicts.append(ConflictInfo(
                patch_id_1=patch1.get_patch_id(),
                patch_id_2=patch2.get_patch_id(),
                path=patch1.target_path,
                reason="write-write_conflict",
                resolution="Keep one value or merge manually"
            ))
        
        return conflicts
    
    def commit_staging(self) -> Tuple[bool, str]:
        """
        提交临时区的所有补丁到主状态 (Phase 2 of 2PC)
        返回：(是否成功，消息)
        """
        if not self.staging_area:
            return False, "No staging area to commit"
        
        # 检查是否有冲突
        conflicts = self.check_conflicts()
        if conflicts:
            return False, f"Found {len(conflicts)} conflicts. Please resolve first."
        
        # 应用所有补丁
        for patch in self.staging_area.patches:
            self._apply_patch(patch)
        
        # 更新版本哈希
        self._version_hash = self._compute_state_hash()
        self.state.updated_at = datetime.now()
        
        # 清空临时区
        self.staging_area.clear()
        self.staging_area = None
        
        return True, "Successfully committed all changes"
    
    def abort_staging(self):
        """放弃临时区的所有修改"""
        if self.staging_area:
            self.staging_area.clear()
            self.staging_area = None
    
    def _apply_patch(self, patch: StatePatch):
        """应用单个补丁到主状态"""
        # 简单的路径解析和应用 (生产环境应使用更完善的 JSONPath 库)
        parts = patch.target_path.split('.')
        
        current = self.state.model_dump()
        
        # 处理 user_profile 为 None 的情况
        if parts[0] == 'user_profile' and current.get('user_profile') is None:
            current['user_profile'] = {}
        
        parent = current
        for i, part in enumerate(parts[:-1]):
            if part.isdigit():
                parent = parent[int(part)]
            else:
                if parent.get(part) is None:
                    parent[part] = {}
                parent = parent[part]
        
        last_key = parts[-1]
        if patch.operation == "update":
            parent[last_key] = patch.value
        elif patch.operation == "delete":
            if last_key in parent:
                del parent[last_key]
        elif patch.operation == "append":
            if isinstance(parent.get(last_key), list):
                parent[last_key].append(patch.value)
        
        # 重新加载状态
        self.state = TravelPlanState.model_validate(current)
    
    def clear_cache(self, category: Optional[str] = None):
        """清理缓存"""
        if category:
            keys_to_remove = [
                k for k in self.cache.keys() 
                if k.startswith(f"{category}:")
            ]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache.clear()
    
    def cache_lookup(self, query: str, category: str = "general") -> Optional[Any]:
        """
        缓存查找 (语义检索)
        返回命中结果或 None
        """
        cache_key = f"{category}:{query}"
        query_vector = self.embedder.encode(query)
        
        # 精确匹配优先
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if not entry.is_expired():
                entry.hit_count += 1
                return entry.result
            else:
                del self.cache[cache_key]
        
        # 语义相似度匹配
        best_match = None
        best_score = 0
        
        for key, entry in self.cache.items():
            if not key.startswith(f"{category}:"):
                continue
            if entry.is_expired():
                continue
            
            score = entry.similarity(query_vector)
            if score > CACHE_SIMILARITY_THRESHOLD and score > best_score:
                best_score = score
                best_match = entry
        
        if best_match:
            best_match.hit_count += 1
            return best_match.result
        
        return None
    
    def cache_store(self, query: str, result: Any, category: str = "general"):
        """存储到缓存"""
        cache_key = f"{category}:{query}"
        query_vector = self.embedder.encode(query)
        
        # 根据类别设置 TTL
        ttl_map = {
            "weather": CACHE_TTL_WEATHER,
            "transport": CACHE_TTL_TRANSPORT,
            "general": CACHE_TTL_GENERAL,
            "destination": CACHE_TTL_GENERAL
        }
        ttl = ttl_map.get(category, CACHE_TTL_GENERAL)
        
        self.cache[cache_key] = CacheEntry(
            query=query,
            result=result,
            ttl=ttl,
            vector=query_vector
        )
    
    def is_pending(self, query: str, category: str) -> bool:
        """检查是否有进行中的请求"""
        key = f"{category}:{query}"
        return self._pending_requests.get(key, False)
    
    def set_pending(self, query: str, category: str, pending: bool):
        """设置请求状态"""
        key = f"{category}:{query}"
        self._pending_requests[key] = pending
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total = len(self.cache)
        hits = sum(e.hit_count for e in self.cache.values())
        expired = sum(1 for e in self.cache.values() if e.is_expired())
        
        return {
            "total_entries": total,
            "total_hits": hits,
            "expired_entries": expired,
            "hit_rate": hits / (hits + total) if (hits + total) > 0 else 0
        }
    
    # ========== 长期记忆管理方法 ==========
    
    def _generate_memory_id(self, agent_id: str, category: str, content_hash: str) -> str:
        """生成记忆唯一 ID"""
        return f"{category}_{agent_id}_{content_hash[:16]}"
    
    def _compute_content_hash(self, content: Dict[str, Any]) -> str:
        """计算内容哈希"""
        content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def add_memory(
        self,
        agent_id: str,
        category: str,
        content: Dict[str, Any],
        confidence: float = 1.0,
        immediate: bool = False,
        half_life: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        添加/更新长期记忆
        
        参数:
        - agent_id: 提交记忆的 Agent ID
        - category: 记忆类别 (user_profile/identity/business_fact/reflection/general)
        - content: 记忆内容
        - confidence: 初始置信度
        - immediate: 是否立即写回 (高优先级记忆可设为 True)
        - half_life: 半衰期 (天)，不传则使用默认值
        
        返回：(是否成功，消息)
        """
        if category not in self.MEMORY_PRIORITY:
            return False, f"Unknown memory category: {category}"
        
        content_hash = self._compute_content_hash(content)
        memory_id = self._generate_memory_id(agent_id, category, content_hash)
        
        # 检查是否已存在相同内容的记忆
        existing = self.long_term_memories.get(memory_id)
        
        if existing:
            # 更新现有记忆：记录访问，提升置信度
            existing.record_access()
            existing.updated_at = datetime.now()
            existing.content = content
            existing.confidence = max(existing.confidence, confidence)
            return True, f"Updated existing memory: {memory_id}"
        
        # 创建新记忆条目
        decay_rate = self.MEMORY_DECAY_RATES.get(category, 0.01)
        
        # 根据类别设置默认半衰期
        if half_life is None:
            half_life_map = {
                "user_profile": 90.0,     # 用户画像半衰期长
                "identity": 60.0,
                "business_fact": 30.0,
                "reflection": 14.0,       # 反思结果半衰期短
                "general": 7.0            # 一般信息半衰期最短
            }
            half_life = half_life_map.get(category, 30.0)
        
        new_memory = MemoryEntry(
            id=memory_id,
            agent_id=agent_id,
            category=category,
            content=content,
            confidence=confidence,
            decay_rate=decay_rate,
            half_life=half_life
        )
        
        # 计算初始写回优先级
        new_memory.write_back_priority = new_memory.compute_write_back_priority()
        
        # 加入写入队列 (负优先级用于最大堆)
        priority = new_memory.write_back_priority
        heapq.heappush(self._memory_write_queue, (-priority, new_memory))
        
        if immediate or priority >= 0.85:
            # 高优先级记忆立即写回
            self._commit_memory_to_state(new_memory)
            return True, f"High-priority memory committed immediately: {memory_id} (priority={priority:.2f})"
        
        return True, f"Memory queued for write-back: {memory_id} (priority={priority:.2f})"
    
    def flush_memory_queue(self, max_items: int = 10) -> int:
        """
        刷新记忆写入队列
        按优先级顺序提交记忆到状态
        
        返回：实际提交的记忆数量
        """
        count = 0
        while self._memory_write_queue and count < max_items:
            neg_priority, memory = heapq.heappop(self._memory_write_queue)
            
            # 检查记忆是否应该被剪枝
            if memory.should_prune():
                continue
            
            # 检查是否有冲突
            conflict = self._check_memory_conflict(memory)
            if conflict:
                # 解决冲突
                resolved = self._resolve_memory_conflict(memory, conflict)
                if resolved:
                    self._commit_memory_to_state(resolved)
                    count += 1
            else:
                self._commit_memory_to_state(memory)
                count += 1
        
        return count
    
    def _commit_memory_to_state(self, memory: MemoryEntry):
        """将记忆提交到状态存储"""
        self.long_term_memories[memory.id] = memory
        
        # 同步到状态对象 (用于持久化)
        self.state.long_term_memories.append({
            "id": memory.id,
            "category": memory.category,
            "content": memory.content,
            "confidence": memory.compute_decayed_confidence(),
            "updated_at": memory.updated_at.isoformat()
        })
        
        # 限制记忆数量
        if len(self.state.long_term_memories) > 100:
            self.state.long_term_memories = self.state.long_term_memories[-100:]
    
    def _check_memory_conflict(self, new_memory: MemoryEntry) -> Optional[MemoryEntry]:
        """
        检查新记忆是否与现有记忆冲突
        冲突定义：同类别、内容键重叠但值不同
        """
        for existing in self.long_term_memories.values():
            if existing.category != new_memory.category:
                continue
            if existing.id == new_memory.id:
                continue
            
            # 检查内容是否有重叠键
            common_keys = set(existing.content.keys()) & set(new_memory.content.keys())
            if not common_keys:
                continue
            
            # 检查重叠键的值是否冲突
            for key in common_keys:
                if existing.content[key] != new_memory.content[key]:
                    return existing
        
        return None
    
    def _resolve_memory_conflict(
        self, 
        new_memory: MemoryEntry, 
        existing: MemoryEntry,
        strategy: str = "auto"
    ) -> Optional[MemoryEntry]:
        """
        解决记忆冲突
        
        策略:
        - auto: 自动选择 (基于置信度、时间戳和类别重要性)
        - merge: 合并两个记忆 (支持 confidence_weighted/temporal_decay)
        - keep_new: 保留新的
        - keep_existing: 保留现有的
        - higher_confidence: 保留置信度高的
        - latest_timestamp: 保留时间戳最新的
        """
        if strategy == "keep_new":
            return new_memory
        elif strategy == "keep_existing":
            return existing
        elif strategy == "higher_confidence":
            new_conf = new_memory.compute_decayed_confidence()
            existing_conf = existing.compute_decayed_confidence()
            return new_memory if new_conf > existing_conf else existing
        elif strategy == "latest_timestamp":
            return new_memory if new_memory.updated_at >= existing.updated_at else existing
        elif strategy == "merge":
            # 默认使用 confidence_weighted 合并策略
            return existing.merge_with(new_memory, strategy="confidence_weighted")
        else:  # auto - 智能决策
            new_conf = new_memory.compute_decayed_confidence()
            existing_conf = existing.compute_decayed_confidence()
            
            # 1. 检查置信度差异是否显著 (>0.15)
            conf_diff = abs(new_conf - existing_conf)
            if conf_diff > 0.15:
                # 置信度差异显著，直接选择高的
                winner = new_memory if new_conf > existing_conf else existing
                return winner
            
            # 2. 置信度接近时，考虑类别重要性
            category_importance = {
                "user_profile": 1.0,
                "identity": 0.95,
                "business_fact": 0.9,
                "reflection": 0.85,
                "general": 0.5
            }
            new_importance = category_importance.get(new_memory.category, 0.5)
            existing_importance = category_importance.get(existing.category, 0.5)
            
            importance_diff = abs(new_importance - existing_importance)
            if importance_diff > 0.1:
                # 类别重要性差异显著，选择重要的
                winner = new_memory if new_importance > existing_importance else existing
                return winner
            
            # 3. 类别相同或重要性接近，考虑时间戳
            time_diff_hours = abs((new_memory.updated_at - existing.updated_at).total_seconds()) / 3600
            if time_diff_hours > 24:
                # 时间差超过 24 小时，保留较新的
                return new_memory if new_memory.updated_at >= existing.updated_at else existing
            
            # 4. 时间也很接近，采用加权合并
            # 根据具体场景选择合适的合并策略
            if new_memory.access_count > existing.access_count * 2:
                # 新记忆访问次数远多于旧记忆，倾向于新记忆
                return new_memory.merge_with(existing, strategy="confidence_weighted")
            elif existing.access_count > new_memory.access_count * 2:
                # 旧记忆访问次数远多于新记忆，倾向于旧记忆
                return existing.merge_with(new_memory, strategy="confidence_weighted")
            else:
                # 访问次数相近，按置信度加权合并
                return existing.merge_with(new_memory, strategy="confidence_weighted")
    
    def get_memories(
        self, 
        category: Optional[str] = None,
        min_confidence: float = 0.3,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取记忆列表
        
        参数:
        - category: 过滤类别 (None 表示全部)
        - min_confidence: 最小置信度阈值
        - limit: 最大返回数量
        """
        results = []
        
        for memory in self.long_term_memories.values():
            # 类别过滤
            if category and memory.category != category:
                continue
            
            # 置信度过滤
            current_conf = memory.compute_decayed_confidence()
            if current_conf < min_confidence:
                continue
            
            # 记录访问
            memory.record_access()
            
            results.append({
                "id": memory.id,
                "category": memory.category,
                "content": memory.content,
                "confidence": current_conf,
                "access_count": memory.access_count,
                "created_at": memory.created_at.isoformat(),
                "updated_at": memory.updated_at.isoformat()
            })
        
        # 按置信度降序排序
        results.sort(key=lambda x: x["confidence"], reverse=True)
        
        return results[:limit]
    
    def prune_memories(self, threshold: float = 0.2) -> int:
        """
        剪枝低置信度记忆
        
        返回：被删除的记忆数量
        """
        to_remove = []
        
        for memory_id, memory in self.long_term_memories.items():
            if memory.should_prune(threshold):
                to_remove.append(memory_id)
        
        for memory_id in to_remove:
            del self.long_term_memories[memory_id]
        
        # 同步清理状态中的记忆
        self.state.long_term_memories = [
            m for m in self.state.long_term_memories
            if m["id"] not in to_remove
        ]
        
        return len(to_remove)
    
    def apply_decay_to_all_memories(self):
        """对所有记忆应用衰减 (定期调用)"""
        for memory in self.long_term_memories.values():
            # compute_decayed_confidence 会自动计算当前置信度
            # 这里可以添加日志或监控
            current_conf = memory.compute_decayed_confidence()
            if current_conf < 0.1:
                # 极低置信度记忆标记为待删除
                pass
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        total = len(self.long_term_memories)
        by_category = {}
        avg_confidence = 0
        
        for memory in self.long_term_memories.values():
            cat = memory.category
            if cat not in by_category:
                by_category[cat] = {"count": 0, "total_conf": 0}
            by_category[cat]["count"] += 1
            conf = memory.compute_decayed_confidence()
            by_category[cat]["total_conf"] += conf
            avg_confidence += conf
        
        # 计算各类别平均置信度
        for cat in by_category:
            count = by_category[cat]["count"]
            by_category[cat]["avg_confidence"] = by_category[cat]["total_conf"] / count if count > 0 else 0
        
        return {
            "total_memories": total,
            "by_category": by_category,
            "avg_confidence": avg_confidence / total if total > 0 else 0,
            "queue_size": len(self._memory_write_queue)
        }
