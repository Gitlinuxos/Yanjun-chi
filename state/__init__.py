"""状态管理模块"""
from .models import (
    UserProfile, Destination, TransportOption, 
    ItineraryDay, TravelPlanState, BudgetBreakdown
)
from .manager import StateManager

__all__ = [
    'UserProfile', 'Destination', 'TransportOption',
    'ItineraryDay', 'TravelPlanState', 'BudgetBreakdown',
    'StateManager'
]
