"""
异步并发调度核心引擎
提供基于 asyncio 的任务调度、背压控制、资源隔离能力
"""
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass(order=True)
class PrioritizedTask:
    """优先队列任务包装器"""
    priority: int
    timestamp: float = field(compare=False)
    task_id: str = field(compare=False)
    coroutine: Callable = field(compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[Exception] = field(default=None, compare=False)


class BackpressureQueue:
    """
    背压队列
    防止消息积压，支持有界缓冲和流式处理
    """
    
    def __init__(self, max_size: int = 1000, name: str = "default"):
        self.max_size = max_size
        self.name = name
        self._queue: deque = deque()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._high_water_mark = 0
        
    @property
    def current_size(self) -> int:
        return len(self._queue)
    
    @property
    def utilization_rate(self) -> float:
        """队列利用率"""
        if self.max_size == 0:
            return 0.0
        return len(self._queue) / self.max_size
    
    async def put(self, item: Any, timeout: Optional[float] = None) -> bool:
        """
        放入元素，支持超时
        当队列满时阻塞或超时返回 False
        """
        async with self._not_full:
            while len(self._queue) >= self.max_size:
                if timeout is not None and timeout <= 0:
                    return False
                try:
                    await asyncio.wait_for(
                        self._not_full.wait(),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    return False
            
            self._queue.append(item)
            self._total_enqueued += 1
            self._high_water_mark = max(self._high_water_mark, len(self._queue))
            
            # 更新水位线告警
            if self.utilization_rate > 0.8:
                logger.warning(
                    f"Queue '{self.name}' high water mark: "
                    f"{self._high_water_mark}/{self.max_size} "
                    f"({self.utilization_rate:.2%})"
                )
        
        async with self._not_empty:
            self._not_empty.notify()
        
        return True
    
    async def get(self, timeout: Optional[float] = None) -> Optional[Any]:
        """获取元素，支持超时"""
        async with self._not_empty:
            while len(self._queue) == 0:
                if timeout is not None and timeout <= 0:
                    return None
                try:
                    await asyncio.wait_for(
                        self._not_empty.wait(),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    return None
            
            item = self._queue.popleft()
            self._total_dequeued += 1
        
        async with self._not_full:
            self._not_full.notify()
        
        return item
    
    def clear(self):
        """清空队列"""
        self._queue.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.name,
            "current_size": len(self._queue),
            "max_size": self.max_size,
            "utilization_rate": self.utilization_rate,
            "total_enqueued": self._total_enqueued,
            "total_dequeued": self._total_dequeued,
            "high_water_mark": self._high_water_mark,
        }


class CircuitBreaker:
    """
    熔断器
    防止雪崩效应，支持自动恢复
    """
    
    class State(Enum):
        CLOSED = "closed"      # 正常状态
        OPEN = "open"          # 熔断打开
        HALF_OPEN = "half_open" # 半开状态（试探恢复）
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: float = 60.0,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.name = name
        
        self._state = self.State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> State:
        return self._state
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过熔断器调用函数"""
        async with self._lock:
            if not await self._allow_request():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is open"
                )
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _allow_request(self) -> bool:
        """判断是否允许请求"""
        if self._state == self.State.CLOSED:
            return True
        
        if self._state == self.State.OPEN:
            # 检查是否已过超时时间
            if (time.time() - self._last_failure_time) >= self.timeout:
                self._state = self.State.HALF_OPEN
                self._success_count = 0
                logger.info(f"Circuit breaker '{self.name}' entering half-open state")
                return True
            return False
        
        # HALF_OPEN 状态允许有限请求
        return True
    
    async def _on_success(self):
        """成功回调"""
        async with self._lock:
            if self._state == self.State.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = self.State.CLOSED
                    self._failure_count = 0
                    logger.info(f"Circuit breaker '{self.name}' closed (recovered)")
            else:
                self._failure_count = max(0, self._failure_count - 1)
    
    async def _on_failure(self):
        """失败回调"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._failure_count >= self.failure_threshold:
                self._state = self.State.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' opened after "
                    f"{self._failure_count} failures"
                )
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
        }


class AdaptiveRateLimiter:
    """
    自适应限流器
    根据系统负载动态调整速率限制
    """
    
    def __init__(
        self,
        initial_rate: float = 10.0,  # 初始每秒请求数
        min_rate: float = 1.0,
        max_rate: float = 100.0,
        adjustment_factor: float = 0.1
    ):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.adjustment_factor = adjustment_factor
        
        self._timestamps: deque = deque(maxlen=100)
        self._lock = asyncio.Lock()
        self._last_adjustment_time = time.time()
    
    async def acquire(self) -> bool:
        """获取许可，如果超过速率限制则等待"""
        async with self._lock:
            now = time.time()
            
            # 清理旧的时间戳（保留最近 1 秒）
            while self._timestamps and self._timestamps[0] < now - 1.0:
                self._timestamps.popleft()
            
            # 检查当前速率
            current_qps = len(self._timestamps)
            
            if current_qps >= self.current_rate:
                # 计算需要等待的时间
                wait_time = (current_qps - self.current_rate + 1) / self.current_rate
                await asyncio.sleep(wait_time)
            
            self._timestamps.append(time.time())
            return True
    
    async def adjust_rate(self, success: bool, latency: Optional[float] = None):
        """根据执行结果动态调整速率"""
        async with self._lock:
            now = time.time()
            
            # 每 5 秒调整一次
            if now - self._last_adjustment_time < 5.0:
                return
            
            if success:
                # 成功且延迟低，适当提高速率
                if latency is None or latency < 1.0:
                    self.current_rate = min(
                        self.max_rate,
                        self.current_rate * (1 + self.adjustment_factor)
                    )
            else:
                # 失败，降低速率
                self.current_rate = max(
                    self.min_rate,
                    self.current_rate * (1 - self.adjustment_factor * 2)
                )
            
            self._last_adjustment_time = now
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_rate": self.current_rate,
            "min_rate": self.min_rate,
            "max_rate": self.max_rate,
            "recent_qps": len(self._timestamps),
        }


class AsyncScheduler:
    """
    异步调度器
    统一管理任务执行、并发控制、资源隔离
    """
    
    def __init__(
        self,
        max_concurrency: int = 10,
        queue_size: int = 1000,
        default_timeout: float = 30.0
    ):
        self.max_concurrency = max_concurrency
        self.default_timeout = default_timeout
        
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._task_queue = BackpressureQueue(max_size=queue_size, name="scheduler")
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._rate_limiter = AdaptiveRateLimiter()
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._shutdown = False
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(name=name)
        return self._circuit_breakers[name]
    
    async def submit(
        self,
        coro_func: Callable,
        *args,
        task_id: Optional[str] = None,
        priority: int = 0,
        timeout: Optional[float] = None,
        circuit_breaker_name: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        提交任务执行
        
        Args:
            coro_func: 协程函数
            *args: 位置参数
            task_id: 任务 ID（可选）
            priority: 优先级（数字越小优先级越高）
            timeout: 超时时间（秒）
            circuit_breaker_name: 熔断器名称
            **kwargs: 关键字参数
        
        Returns:
            任务执行结果
        """
        if self._shutdown:
            raise RuntimeError("Scheduler is shut down")
        
        task_id = task_id or f"task_{time.time()}_{id(coro_func)}"
        timeout = timeout or self.default_timeout
        
        # 检查熔断器
        if circuit_breaker_name:
            cb = self.get_circuit_breaker(circuit_breaker_name)
            if cb.state == CircuitBreaker.State.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{circuit_breaker_name}' is open"
                )
        
        # 限流
        await self._rate_limiter.acquire()
        
        async with self._semaphore:
            start_time = time.time()
            try:
                # 执行任务
                if circuit_breaker_name:
                    cb = self.get_circuit_breaker(circuit_breaker_name)
                    result = await asyncio.wait_for(
                        cb.call(coro_func, *args, **kwargs),
                        timeout=timeout
                    )
                else:
                    result = await asyncio.wait_for(
                        coro_func(*args, **kwargs),
                        timeout=timeout
                    )
                
                latency = time.time() - start_time
                
                # 调整限流器
                await self._rate_limiter.adjust_rate(success=True, latency=latency)
                
                return result
                
            except asyncio.TimeoutError:
                latency = time.time() - start_time
                await self._rate_limiter.adjust_rate(success=False, latency=latency)
                logger.warning(f"Task '{task_id}' timed out after {timeout}s")
                raise TaskTimeoutError(f"Task '{task_id}' timed out")
                
            except CircuitBreakerOpenError:
                raise
                
            except Exception as e:
                latency = time.time() - start_time
                await self._rate_limiter.adjust_rate(success=False, latency=latency)
                
                # 记录熔断器失败
                if circuit_breaker_name:
                    cb = self.get_circuit_breaker(circuit_breaker_name)
                    await cb._on_failure()
                
                logger.error(f"Task '{task_id}' failed: {e}")
                raise
    
    async def submit_batch(
        self,
        tasks: List[Dict[str, Any]],
        return_exceptions: bool = False
    ) -> List[Any]:
        """
        批量提交任务
        
        Args:
            tasks: 任务配置列表，每项包含：
                   - coro_func: 协程函数
                   - args: 位置参数
                   - kwargs: 关键字参数
                   - task_id: 任务 ID
                   - priority: 优先级
                   - timeout: 超时时间
                   - circuit_breaker_name: 熔断器名称
            return_exceptions: 是否返回异常而不是抛出
        
        Returns:
            结果列表
        """
        coroutines = []
        for task_config in tasks:
            coro = self.submit(**task_config)
            coroutines.append(coro)
        
        if return_exceptions:
            results = await asyncio.gather(*coroutines, return_exceptions=True)
            return list(results)
        else:
            return await asyncio.gather(*coroutines)
    
    async def shutdown(self, wait: bool = True, timeout: float = 5.0):
        """关闭调度器"""
        self._shutdown = True
        
        if wait:
            # 等待活跃任务完成
            if self._active_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(
                            *self._active_tasks.values(),
                            return_exceptions=True
                        ),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning("Shutdown timeout, cancelling remaining tasks")
        
        # 取消所有活跃任务
        for task_id, task in self._active_tasks.items():
            if not task.done():
                task.cancel()
        
        # 清空队列
        self._task_queue.clear()
        
        logger.info("Scheduler shut down complete")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        return {
            "max_concurrency": self.max_concurrency,
            "active_tasks": len(self._active_tasks),
            "queue_size": self._task_queue.current_size,
            "queue_utilization": self._task_queue.utilization_rate,
            "circuit_breakers": {
                name: cb.get_stats()
                for name, cb in self._circuit_breakers.items()
            },
            "rate_limiter": self._rate_limiter.get_stats(),
            "shutdown": self._shutdown,
        }


class CircuitBreakerOpenError(Exception):
    """熔断器打开异常"""
    pass


class TaskTimeoutError(Exception):
    """任务超时异常"""
    pass


class MemoryLimitExceededError(Exception):
    """内存限制超出异常"""
    pass
