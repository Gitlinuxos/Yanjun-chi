"""
弹性防护模块
提供熔断、限流、超时控制、内存保护等弹性能力
"""
import asyncio
import time
import logging
import tracemalloc
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass
from enum import Enum
import sys

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """内存快照"""
    timestamp: float
    current_mb: float
    peak_mb: float
    top_allocators: List[tuple]


class MemoryProtector:
    """
    内存保护器
    监控内存使用，防止内存溢出
    """
    
    def __init__(
        self,
        max_memory_mb: float = 512.0,
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.9
    ):
        self.max_memory_mb = max_memory_mb
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        
        self._enabled = False
        self._snapshots: List[MemorySnapshot] = []
        self._max_snapshots = 100
    
    def start_monitoring(self):
        """启动内存监控"""
        tracemalloc.start()
        self._enabled = True
        logger.info(f"Memory monitoring started (max: {self.max_memory_mb}MB)")
    
    def stop_monitoring(self):
        """停止内存监控"""
        if self._enabled:
            tracemalloc.stop()
            self._enabled = False
            logger.info("Memory monitoring stopped")
    
    def get_current_usage(self) -> MemorySnapshot:
        """获取当前内存使用情况"""
        if not self._enabled:
            return MemorySnapshot(
                timestamp=time.time(),
                current_mb=0.0,
                peak_mb=0.0,
                top_allocators=[]
            )
        
        current, peak = tracemalloc.get_traced_memory()
        current_mb = current / 1024 / 1024
        peak_mb = peak / 1024 / 1024
        
        # 获取前 10 个内存分配者
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')[:10]
        top_allocators = [
            (str(stat.traceback), stat.size / 1024)
            for stat in top_stats
        ]
        
        usage_ratio = current_mb / self.max_memory_mb if self.max_memory_mb > 0 else 0
        
        snapshot_obj = MemorySnapshot(
            timestamp=time.time(),
            current_mb=current_mb,
            peak_mb=peak_mb,
            top_allocators=top_allocators
        )
        
        # 记录快照
        self._snapshots.append(snapshot_obj)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots.pop(0)
        
        # 告警
        if usage_ratio >= self.critical_threshold:
            logger.critical(
                f"CRITICAL: Memory usage at {usage_ratio:.2%} "
                f"({current_mb:.2f}MB / {self.max_memory_mb:.2f}MB)"
            )
        elif usage_ratio >= self.warning_threshold:
            logger.warning(
                f"WARNING: Memory usage at {usage_ratio:.2%} "
                f"({current_mb:.2f}MB / {self.max_memory_mb:.2f}MB)"
            )
        
        return snapshot_obj
    
    def check_memory_limit(self) -> bool:
        """检查是否超出内存限制"""
        if not self._enabled:
            return True
        
        usage = self.get_current_usage()
        return usage.current_mb < self.max_memory_mb
    
    async def execute_with_memory_limit(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        在内存限制下执行函数
        如果超出限制则抛出异常
        """
        if not self.check_memory_limit():
            usage = self.get_current_usage()
            raise MemoryLimitExceededError(
                f"Memory limit exceeded: {usage.current_mb:.2f}MB "
                f"(limit: {self.max_memory_mb:.2f}MB)"
            )
        
        return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._enabled:
            return {"enabled": False}
        
        usage = self.get_current_usage()
        usage_ratio = usage.current_mb / self.max_memory_mb if self.max_memory_mb > 0 else 0
        
        return {
            "enabled": self._enabled,
            "current_mb": usage.current_mb,
            "peak_mb": usage.peak_mb,
            "max_mb": self.max_memory_mb,
            "usage_ratio": usage_ratio,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "snapshot_count": len(self._snapshots),
        }


class TimeoutController:
    """
    超时控制器
    统一管理任务超时，防止无限等待
    """
    
    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self._active_timeouts: Set[str] = set()
        self._timeout_stats = {
            "total": 0,
            "success": 0,
            "timeout": 0,
        }
    
    async def execute_with_timeout(
        self,
        coro_func: Callable,
        *args,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        带超时控制执行协程
        
        Args:
            coro_func: 协程函数
            *args: 位置参数
            task_id: 任务 ID
            timeout: 超时时间（秒）
            **kwargs: 关键字参数
        
        Returns:
            执行结果
        
        Raises:
            asyncio.TimeoutError: 超时异常
        """
        timeout = timeout or self.default_timeout
        task_id = task_id or f"task_{time.time()}_{id(coro_func)}"
        
        self._active_timeouts.add(task_id)
        self._timeout_stats["total"] += 1
        
        try:
            result = await asyncio.wait_for(
                coro_func(*args, **kwargs),
                timeout=timeout
            )
            self._timeout_stats["success"] += 1
            return result
            
        except asyncio.TimeoutError:
            self._timeout_stats["timeout"] += 1
            logger.warning(f"Task '{task_id}' timed out after {timeout}s")
            raise
            
        finally:
            self._active_timeouts.discard(task_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "default_timeout": self.default_timeout,
            "active_timeouts": len(self._active_timeouts),
            **self._timeout_stats,
        }


class DeadlockDetector:
    """
    死锁检测器
    通过超时和资源依赖图检测潜在死锁
    """
    
    def __init__(self, detection_interval: float = 5.0):
        self.detection_interval = detection_interval
        self._resource_graph: Dict[str, Set[str]] = {}  # 资源依赖图
        self._waiting_tasks: Dict[str, str] = {}  # 任务等待的资源
        self._holding_tasks: Dict[str, Set[str]] = {}  # 任务持有的资源
        self._last_detection_time = 0.0
        self._deadlock_detected = False
    
    def register_resource(self, resource_id: str):
        """注册资源"""
        if resource_id not in self._resource_graph:
            self._resource_graph[resource_id] = set()
    
    def acquire_resource(self, task_id: str, resource_id: str):
        """任务获取资源"""
        self.register_resource(resource_id)
        
        if task_id not in self._holding_tasks:
            self._holding_tasks[task_id] = set()
        self._holding_tasks[task_id].add(resource_id)
        
        if task_id in self._waiting_tasks and self._waiting_tasks[task_id] == resource_id:
            del self._waiting_tasks[task_id]
    
    def wait_for_resource(self, task_id: str, resource_id: str):
        """任务等待资源"""
        self.register_resource(resource_id)
        self._waiting_tasks[task_id] = resource_id
    
    def release_resource(self, task_id: str, resource_id: str):
        """任务释放资源"""
        if task_id in self._holding_tasks:
            self._holding_tasks[task_id].discard(resource_id)
            if not self._holding_tasks[task_id]:
                del self._holding_tasks[task_id]
    
    def detect_deadlock(self) -> bool:
        """
        检测是否存在死锁
        使用 DFS 检测循环依赖
        """
        # 构建等待图
        wait_graph: Dict[str, str] = {}
        
        for waiting_task, resource in self._waiting_tasks.items():
            # 找到持有该资源的任务
            for holding_task, resources in self._holding_tasks.items():
                if resource in resources and holding_task != waiting_task:
                    wait_graph[waiting_task] = holding_task
                    break
        
        # DFS 检测循环
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            if node in wait_graph:
                neighbor = wait_graph[node]
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task in wait_graph:
            if task not in visited:
                if has_cycle(task):
                    self._deadlock_detected = True
                    logger.error(f"Deadlock detected involving tasks: {list(rec_stack)}")
                    return True
        
        self._deadlock_detected = False
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "detection_interval": self.detection_interval,
            "resources_count": len(self._resource_graph),
            "waiting_tasks": len(self._waiting_tasks),
            "holding_tasks": len(self._holding_tasks),
            "deadlock_detected": self._deadlock_detected,
        }


class MemoryLimitExceededError(Exception):
    """内存限制超出异常"""
    pass


class DeadlockDetectedError(Exception):
    """检测到死锁异常"""
    pass
