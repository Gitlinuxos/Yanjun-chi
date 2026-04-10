"""
Pydantic 数据模型定义
用于结构化存储旅行计划相关数据
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TravelStyle(str, Enum):
    """旅行风格枚举"""
    NATURE = "自然"
    CULTURE = "人文"
    ADVENTURE = "冒险"
    RELAX = "休闲"
    FOOD = "美食"
    HISTORY = "历史"


class TransportType(str, Enum):
    """交通工具类型"""
    PLANE = "飞机"
    HIGH_SPEED_RAIL = "高铁"
    TRAIN = "普通火车"
    BUS = "大巴"
    CAR = "自驾"


class UserProfile(BaseModel):
    """用户画像模型"""
    name: str = Field(default="游客", description="用户姓名")
    age: Optional[int] = Field(default=None, description="年龄")
    contact: Optional[str] = Field(default=None, description="联系方式")
    
    # 旅行偏好
    preferred_styles: List[TravelStyle] = Field(
        default_factory=list, 
        description="喜欢的旅行类型"
    )
    interests: List[str] = Field(
        default_factory=list, 
        description="兴趣标签"
    )
    
    # 约束条件
    budget: Optional[float] = Field(default=None, description="预算 (元)")
    days: Optional[int] = Field(default=None, description="旅行天数")
    travelers: int = Field(default=1, description="出行人数")
    start_date: Optional[str] = Field(default=None, description="出发日期")
    
    # 交通偏好
    transport_preference: str = Field(
        default="balanced",
        description="交通偏好：speed/comfort/economy/balanced"
    )
    
    # 特殊需求
    special_needs: List[str] = Field(
        default_factory=list,
        description="特殊需求"
    )
    
    class Config:
        use_enum_values = True


class Destination(BaseModel):
    """目的地模型"""
    name: str = Field(description="目的地名称")
    country: str = Field(default="中国", description="国家")
    description: str = Field(description="目的地简介")
    
    # 特色标签
    features: List[str] = Field(
        default_factory=list,
        description="特色标签"
    )
    
    # 推荐信息
    best_season: str = Field(default="全年", description="最佳季节")
    recommended_days: int = Field(default=3, description="建议游玩天数")
    estimated_cost: float = Field(default=0, description="预估人均费用")
    
    # 推荐理由
    reason: str = Field(default="", description="推荐理由")
    
    # 多模态内容
    images: List[str] = Field(default_factory=list, description="图片链接")
    videos: List[str] = Field(default_factory=list, description="视频链接")
    
    # 来源信息
    source: str = Field(default="manual", description="信息来源")
    update_time: Optional[datetime] = Field(default=None, description="更新时间")


class TransportOption(BaseModel):
    """交通方案模型"""
    type: TransportType = Field(description="交通工具类型")
    duration: float = Field(description="耗时 (小时)")
    cost: float = Field(description="费用 (元)")
    comfort_level: int = Field(ge=1, le=5, description="舒适度评分 1-5")
    description: str = Field(description="方案描述")
    
    # 额外信息
    notes: List[str] = Field(default_factory=list, description="注意事项")


class ItineraryDay(BaseModel):
    """每日行程模型"""
    day: int = Field(ge=1, description="第几天")
    date: Optional[str] = Field(default=None, description="日期")
    
    # 时间段安排
    morning: str = Field(default="", description="上午安排")
    noon: str = Field(default="", description="中午安排")
    afternoon: str = Field(default="", description="下午安排")
    evening: str = Field(default="", description="晚上安排")
    
    # 详细信息
    attractions: List[str] = Field(default_factory=list, description="景点列表")
    meals: List[str] = Field(default_factory=list, description="餐饮建议")
    transport: str = Field(default="", description="市内交通")
    
    # 提示
    tips: List[str] = Field(default_factory=list, description="当日提示")


class BudgetBreakdown(BaseModel):
    """预算分解模型"""
    total_budget: float = Field(description="总预算")
    
    # 分类预算
    transport: float = Field(default=0, description="交通费用")
    accommodation: float = Field(default=0, description="住宿费用")
    food: float = Field(default=0, description="餐饮费用")
    tickets: float = Field(default=0, description="门票费用")
    shopping: float = Field(default=0, description="购物费用")
    others: float = Field(default=0, description="其他费用")
    
    # 状态
    status: str = Field(default="sufficient", description="预算状态")
    remaining: float = Field(default=0, description="剩余预算")
    
    # 建议
    suggestions: List[str] = Field(default_factory=list, description="节省建议")
    
    def calculate_total(self) -> float:
        """计算总花费"""
        return self.transport + self.accommodation + self.food + \
               self.tickets + self.shopping + self.others
    
    def update_status(self):
        """更新预算状态"""
        total_spent = self.calculate_total()
        self.remaining = self.total_budget - total_spent
        
        if self.remaining < 0:
            self.status = "over_budget"
        elif self.remaining < self.total_budget * 0.2:
            self.status = "tight"
        else:
            self.status = "sufficient"


class WeatherInfo(BaseModel):
    """天气信息模型"""
    date: str = Field(description="日期")
    temperature_high: int = Field(description="最高温度")
    temperature_low: int = Field(description="最低温度")
    condition: str = Field(description="天气状况")
    precipitation: int = Field(ge=0, le=100, description="降水概率 (%)")
    wind: str = Field(default="", description="风力风向")
    
    # 建议
    advice: str = Field(default="", description="出行建议")
    warning: Optional[str] = Field(default=None, description="预警信息")


class TravelPlanState(BaseModel):
    """旅行计划整体状态 (共享黑板)"""
    # 用户信息
    user_profile: Optional[UserProfile] = Field(default=None)
    
    # 推荐结果
    recommended_destinations: List[Destination] = Field(default_factory=list)
    selected_destination: Optional[Destination] = Field(default=None)
    
    # 交通方案
    transport_options: List[TransportOption] = Field(default_factory=list)
    selected_transport: Optional[TransportOption] = Field(default=None)
    
    # 行程安排
    itinerary: List[ItineraryDay] = Field(default_factory=list)
    
    # 预算
    budget: Optional[BudgetBreakdown] = Field(default=None)
    
    # 天气
    weather_forecast: List[WeatherInfo] = Field(default_factory=list)
    
    # 对话历史
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    
    # 状态标记
    is_confirmed: bool = Field(default=False, description="计划是否已确认")
    iteration_count: int = Field(default=0, description="修改迭代次数")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str):
        """添加对话消息"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # 限制历史记录长度
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        self.updated_at = datetime.now()
