"""状态管理器 - 管理共享黑板"""
from typing import Dict, Any, Optional
from datetime import datetime
import copy

from .models import TravelPlanState, UserProfile, Destination, TransportOption, ItineraryDay, BudgetBreakdown, WeatherForecast


class StateManager:
    """状态管理器 - 维护单一事实来源"""
    
    def __init__(self):
        """初始化状态管理器"""
        self._state = TravelPlanState()
        self._version = 0
        self._history = []
    
    def get_state(self) -> TravelPlanState:
        """获取当前状态副本"""
        return copy.deepcopy(self._state)
    
    def update_state(self, new_state: Dict[str, Any]) -> None:
        """更新状态
        
        Args:
            new_state: 包含要更新字段的新状态字典
        """
        # 保存旧状态到历史
        if self._version < 100:  # 限制历史记录数量
            self._history.append({
                'version': self._version,
                'timestamp': datetime.now().isoformat(),
                'state': copy.deepcopy(self._state.dict())
            })
        
        # 更新状态
        for key, value in new_state.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        
        self._state.updated_at = datetime.now().isoformat()
        self._version += 1
    
    def update_field(self, field_name: str, value: Any) -> None:
        """更新单个字段
        
        Args:
            field_name: 字段名
            value: 新值
        """
        if hasattr(self._state, field_name):
            setattr(self._state, field_name, value)
            self._state.updated_at = datetime.now().isoformat()
            self._version += 1
    
    def add_modification(self, modification: Dict[str, Any]) -> None:
        """添加修改记录
        
        Args:
            modification: 修改记录字典
        """
        modification['timestamp'] = datetime.now().isoformat()
        self._state.modification_history.append(modification)
        
        # 限制历史记录数量
        if len(self._state.modification_history) > 20:
            self._state.modification_history = self._state.modification_history[-20:]
    
    def get_version(self) -> int:
        """获取当前版本号"""
        return self._version
    
    def reset(self) -> None:
        """重置状态"""
        self._state = TravelPlanState()
        self._version = 0
        self._history = []
    
    def rollback(self, version: int) -> bool:
        """回滚到指定版本
        
        Args:
            version: 目标版本号
            
        Returns:
            bool: 是否成功回滚
        """
        for record in reversed(self._history):
            if record['version'] == version:
                self._state = TravelPlanState(**record['state'])
                self._version = version
                return True
        return False
    
    def get_current_step(self) -> str:
        """获取当前步骤"""
        return self._state.current_step
    
    def set_current_step(self, step: str) -> None:
        """设置当前步骤"""
        self._state.current_step = step
        self._state.updated_at = datetime.now().isoformat()
