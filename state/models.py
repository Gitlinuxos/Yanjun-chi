"""数据模型定义"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from enum import Enum


class TravelStyle(str, Enum):
    """旅行风格枚举"""
    NATURE = "自然风光"
    CULTURE = "人文历史"
    ADVENTURE = "冒险探索"
    RELAXATION = "休闲度假"
    FOOD = "美食之旅"
    SHOPPING = "购物娱乐"


class TransportType(str, Enum):
    """交通工具类型"""
    PLANE = "飞机"
    HIGH_SPEED_RAIL = "高铁"
    TRAIN = "普通火车"
    BUS = "大巴"
    CAR = "自驾"


class UserProfile(BaseModel):
    """用户画像"""
    name: str = Field(default="", description="姓名")
    age: int = Field(default=0, description="年龄")
    contact: str = Field(default="", description="联系方式")
    travel_styles: List[str] = Field(default_factory=list, description="偏好旅行风格")
    interests: List[str] = Field(default_factory=list, description="兴趣标签")
    budget: float = Field(default=0, description="预算 (元)")
    days: int = Field(default=0, description="可用天数")
    people_count: int = Field(default=1, description="出行人数")
    special_needs: str = Field(default="", description="特殊需求")
    transport_preference: str = Field(default="平衡", description="交通偏好：速度优先/舒适优先/经济优先/平衡")
    departure_city: str = Field(default="", description="出发城市")


class Destination(BaseModel):
    """目的地信息"""
    name: str = Field(description="目的地名称")
    description: str = Field(description="简介")
    features: List[str] = Field(default_factory=list, description="特色标签")
    best_season: List[str] = Field(default_factory=list, description="最佳季节")
    avg_cost: float = Field(description="人均预计花费")
    suggested_days: int = Field(description="建议游玩天数")
    reason: str = Field(default="", description="推荐理由")
    match_score: float = Field(default=0, description="匹配度评分")


class TransportOption(BaseModel):
    """交通方案"""
    type: str = Field(description="交通工具类型")
    duration: float = Field(description="耗时 (小时)")
    cost: float = Field(description="费用 (元)")
    comfort_level: int = Field(default=3, description="舒适度 1-5")
    description: str = Field(default="", description="描述")


class ItineraryDay(BaseModel):
    """每日行程"""
    day: int = Field(description="第几天")
    date: str = Field(default="", description="日期")
    activities: List[Dict[str, str]] = Field(default_factory=list, description="活动列表")
    meals: Dict[str, str] = Field(default_factory=dict, description="餐饮安排")
    accommodation: str = Field(default="", description="住宿")
    tips: str = Field(default="", description="小贴士")


class BudgetBreakdown(BaseModel):
    """预算明细"""
    transport: float = Field(default=0, description="交通费用")
    accommodation: float = Field(default=0, description="住宿费用")
    food: float = Field(default=0, description="餐饮费用")
    tickets: float = Field(default=0, description="门票费用")
    shopping: float = Field(default=0, description="购物费用")
    other: float = Field(default=0, description="其他费用")
    total: float = Field(default=0, description="总计")
    status: str = Field(default="充足", description="预算状态：充足/紧张/超支")
    
    def calculate_total(self):
        """计算总费用"""
        self.total = self.transport + self.accommodation + self.food + self.tickets + self.shopping + self.other


class WeatherForecast(BaseModel):
    """天气预报"""
    date: str = Field(description="日期")
    temperature_high: int = Field(description="最高温度")
    temperature_low: int = Field(description="最低温度")
    condition: str = Field(description="天气状况")
    precipitation: int = Field(default=0, description="降水概率%")
    wind: str = Field(default="", description="风力")
    suggestion: str = Field(default="", description="出行建议")


class TravelPlanState(BaseModel):
    """旅行计划状态 - 共享黑板"""
    # 用户信息
    user_profile: Optional[UserProfile] = Field(default=None)
    
    # 推荐目的地
    recommended_destinations: List[Destination] = Field(default_factory=list)
    selected_destination: Optional[Destination] = Field(default=None)
    
    # 交通方案
    transport_options: List[TransportOption] = Field(default_factory=list)
    selected_transport: Optional[TransportOption] = Field(default=None)
    
    # 行程安排
    itinerary: List[ItineraryDay] = Field(default_factory=list)
    
    # 预算
    budget_breakdown: Optional[BudgetBreakdown] = Field(default=None)
    
    # 天气
    weather_forecast: List[WeatherForecast] = Field(default_factory=list)
    
    # 状态标记
    current_step: str = Field(default="initial", description="当前步骤")
    is_confirmed: bool = Field(default=False, description="是否已确认")
    modification_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
