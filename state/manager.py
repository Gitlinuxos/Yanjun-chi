"""
状态管理器 - 维护共享黑板和 KV-Cache
"""
import json
import hashlib
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .models import TravelPlanState, UserProfile, Destination, StatePatch, StagingArea, ConflictInfo
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
    """
    
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
