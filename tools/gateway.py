"""
工具网关 - 统一管理工具调用
提供缓存、重试、降级机制
"""
import time
import json
from typing import Dict, Any, Optional, Callable
from functools import wraps

from config import MAX_RETRY_ATTEMPTS, SIMULATION_MODE
from .validators import validate_params, validate_search_query, validate_location


class ToolGateway:
    """
    工具网关
    - 参数校验
    - 缓存管理
    - 重试机制
    - 降级处理
    """
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.retry_count = 0
    
    def call_tool(
        self, 
        tool_name: str, 
        params: Dict[str, Any], 
        tool_func: Callable,
        category: str = "general"
    ) -> Optional[Any]:
        """
        统一工具调用入口
        """
        # 1. 构建缓存查询键
        query_key = f"{tool_name}:{json.dumps(params, sort_keys=True)}"
        
        # 2. 检查缓存
        cached_result = self.state_manager.cache_lookup(query_key, category)
        if cached_result is not None:
            return cached_result
        
        # 3. 检查是否有进行中的请求 (防止并发重复)
        if self.state_manager.is_pending(query_key, category):
            # 等待中，返回 None
            return None
        
        # 4. 设置进行中状态
        self.state_manager.set_pending(query_key, category, True)
        
        try:
            # 5. 执行带重试的调用
            result = self._execute_with_retry(tool_func, params, tool_name)
            
            # 6. 存入缓存
            if result is not None:
                self.state_manager.cache_store(query_key, result, category)
            
            return result
            
        except Exception as e:
            print(f"工具调用失败 [{tool_name}]: {e}")
            return self._get_fallback_result(tool_name, params)
            
        finally:
            # 7. 清除进行中状态
            self.state_manager.set_pending(query_key, category, False)
    
    def _execute_with_retry(
        self, 
        tool_func: Callable, 
        params: Dict[str, Any],
        tool_name: str
    ) -> Optional[Any]:
        """带重试的执行"""
        last_error = None
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                return tool_func(**params)
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    wait_time = (attempt + 1) * 0.5
                    time.sleep(wait_time)
        
        raise last_error
    
    def _get_fallback_result(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """降级结果"""
        if SIMULATION_MODE:
            # 模拟模式下返回模拟数据
            return self._generate_mock_result(tool_name, params)
        return None
    
    def _generate_mock_result(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """生成模拟结果"""
        if tool_name == "search":
            return [
                {"title": f"关于{params.get('query', '搜索')}的信息", "snippet": "..."}
            ]
        elif tool_name == "weather":
            return [{"date": "2024-01-01", "condition": "晴", "temperature_high": 25}]
        return {}
