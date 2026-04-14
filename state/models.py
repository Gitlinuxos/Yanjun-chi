"""
Pydantic 数据模型定义
用于结构化存储旅行计划相关数据
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import hashlib
import numpy as np


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


class StatePatch(BaseModel):
    """
    状态修改补丁：封装单个 Agent 的修改意图
    """
    agent_id: str = Field(description="提交修改的 Agent ID")
    target_path: str = Field(description="JSONPath 风格的目标路径，如 'user_profile.preferences' 或 'itinerary.days.0'")
    operation: Literal["update", "append", "delete"] = Field(description="操作类型")
    value: Any = Field(default=None, description="新值")
    base_version_hash: str = Field(description="提交时的状态哈希，用于乐观锁检查")
    timestamp: datetime = Field(default_factory=datetime.now)
    description: str = Field(default="", description="修改描述")
    
    def get_patch_id(self) -> str:
        """生成唯一补丁 ID"""
        return f"{self.agent_id}_{self.timestamp.isoformat()}"


class ConflictInfo(BaseModel):
    """冲突详情"""
    patch_id_1: str = Field(description="第一个冲突补丁 ID")
    patch_id_2: str = Field(description="第二个冲突补丁 ID")
    path: str = Field(description="冲突路径")
    reason: str = Field(description="冲突原因：write-write conflict / version mismatch")
    resolution: Optional[str] = Field(default=None, description="解决建议")


class MemoryEntry(BaseModel):
    """
    长期记忆条目
    支持高级衰减策略、智能冲突解决和优先级写回
    """
    id: str = Field(description="记忆唯一 ID")
    agent_id: str = Field(description="创建/更新该记忆的 Agent ID")
    category: Literal["user_profile", "identity", "business_fact", "reflection", "general"] = Field(
        description="记忆类别"
    )
    content: Dict[str, Any] = Field(description="记忆内容")
    
    # 元数据
    confidence: float = Field(ge=0.0, le=1.0, default=1.0, description="置信度")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    access_count: int = Field(default=0, description="访问次数")
    last_accessed: Optional[datetime] = Field(default=None, description="最后访问时间")
    
    # 衰减参数
    decay_rate: float = Field(default=0.01, description="基础衰减率 (每天)")
    half_life: float = Field(default=30.0, description="半衰期 (天)")
    usage_boost: float = Field(default=0.05, description="每次访问提升的置信度")
    max_confidence: float = Field(default=1.0, description="最大置信度")
    min_confidence: float = Field(default=0.0, description="最小置信度")
    
    # 写回控制
    write_back_priority: float = Field(default=0.5, description="写回优先级 (0-1)")
    pending_write: bool = Field(default=False, description="是否等待写回")
    
    def compute_decayed_confidence(self) -> float:
        """
        计算衰减后的置信度
        混合衰减策略：时间指数衰减 + 使用频率加权 + 置信度自调节 + 半衰期控制
        
        公式：
        conf(t) = conf_0 * exp(-λ*t) * (1 + α*log(1+n)) * (1 - β*(1-conf_0))
        
        其中：
        - λ: 衰减率 (与半衰期相关：λ = ln(2) / half_life)
        - α: 使用频率增益系数
        - n: 访问次数
        - β: 初始置信度调节系数
        """
        now = datetime.now()
        
        # 1. 时间衰减 (指数衰减模型)
        days_elapsed = (now - self.created_at).total_seconds() / 86400
        decay_lambda = np.log(2) / self.half_life  # 通过半衰期计算衰减常数
        time_decay_factor = np.exp(-decay_lambda * days_elapsed)
        
        # 2. 使用频率加权 (对数增长，避免过度放大)
        # 访问越频繁，衰减补偿越多，但有上限
        usage_factor = 1.0 + 0.15 * np.log1p(self.access_count)
        usage_factor = min(usage_factor, 1.5)  # 上限 1.5 倍
        
        # 3. 最近访问衰减 (最后访问时间越近，置信度越高)
        recency_factor = 1.0
        if self.last_accessed:
            days_since_access = (now - self.last_accessed).total_seconds() / 86400
            # 7 天内访问过有加成
            recency_factor = 1.0 + 0.1 * max(0, (7 - days_since_access) / 7)
        
        # 4. 置信度自调节 (高置信度信息更稳定)
        stability_factor = 0.7 + 0.3 * self.confidence
        
        # 5. 类别重要性加权 (从父类获取)
        category_weights = {
            "user_profile": 1.2,
            "identity": 1.15,
            "business_fact": 1.1,
            "reflection": 1.0,
            "general": 0.9
        }
        category_factor = category_weights.get(self.category, 1.0)
        
        # 综合计算
        base_decay = self.confidence * time_decay_factor
        adjusted_conf = base_decay * usage_factor * recency_factor * stability_factor * category_factor
        
        # 边界约束
        final_conf = max(self.min_confidence, min(adjusted_conf, self.max_confidence))
        
        return round(final_conf, 4)
    
    def compute_write_back_priority(self) -> float:
        """
        计算写回优先级
        综合考虑：类别重要性 + 置信度 + 时效性 + 访问频率
        
        返回：0-1 之间的优先级分数
        """
        # 1. 类别基础优先级
        category_priority = {
            "user_profile": 1.0,
            "identity": 0.95,
            "business_fact": 0.9,
            "reflection": 0.85,
            "general": 0.5
        }
        base_score = category_priority.get(self.category, 0.5)
        
        # 2. 置信度加权 (置信度越高越优先)
        conf_weight = self.compute_decayed_confidence()
        
        # 3. 时效性 (新创建或刚更新的优先)
        now = datetime.now()
        hours_since_update = (now - self.updated_at).total_seconds() / 3600
        freshness_score = max(0, 1.0 - hours_since_update / 24)  # 24 小时内为高分
        
        # 4. 访问频率 (经常被访问的记忆更重要)
        frequency_score = min(1.0, self.access_count / 10)
        
        # 综合计算 (加权平均)
        priority = (
            base_score * 0.4 +      # 类别权重 40%
            conf_weight * 0.3 +     # 置信度权重 30%
            freshness_score * 0.2 + # 时效性权重 20%
            frequency_score * 0.1   # 频率权重 10%
        )
        
        return round(min(1.0, max(0.0, priority)), 4)
    
    def record_access(self, update_confidence: bool = True):
        """
        记录访问，可选地提升置信度
        
        参数:
        - update_confidence: 是否同时提升置信度 (某些场景下只记录访问不提升置信度)
        """
        self.access_count += 1
        self.last_accessed = datetime.now()
        
        if update_confidence:
            # 访问提升置信度，但有上限且增益递减
            current_conf = self.confidence
            boost = self.usage_boost * (1.0 / (1.0 + self.access_count * 0.05))
            self.confidence = min(current_conf + boost, self.max_confidence)
        
        # 重新计算写回优先级
        self.write_back_priority = self.compute_write_back_priority()
        self.pending_write = True
    
    def should_prune(self, threshold: float = 0.2) -> bool:
        """判断是否应该被剪枝 (置信度过低且长时间未访问)"""
        current_conf = self.compute_decayed_confidence()
        
        # 双重条件：置信度低 AND 长时间未访问
        if current_conf < threshold:
            if self.last_accessed:
                days_since_access = (datetime.now() - self.last_accessed).total_seconds() / 86400
                return days_since_access > 7  # 7 天以上未访问才剪枝
            else:
                return True  # 从未被访问过的低置信度记忆直接剪枝
        
        return False
    
    def merge_with(self, other: 'MemoryEntry', strategy: str = "confidence_weighted") -> 'MemoryEntry':
        """
        与另一个记忆条目合并
        策略：
        - confidence_weighted: 按置信度加权平均
        - latest: 保留最新的
        - higher_confidence: 保留置信度高的
        - temporal_decay: 考虑时间衰减的加权
        """
        if strategy == "latest":
            if self.updated_at >= other.updated_at:
                return self
            else:
                return other
        
        elif strategy == "higher_confidence":
            self_conf = self.compute_decayed_confidence()
            other_conf = other.compute_decayed_confidence()
            if self_conf >= other_conf:
                return self
            else:
                return other
        
        elif strategy == "temporal_decay":
            # 考虑时间衰减的加权：新信息权重更高
            self_conf = self.compute_decayed_confidence()
            other_conf = other.compute_decayed_confidence()
            
            # 时间权重：越新的信息权重越高
            now = datetime.now()
            self_age = (now - self.updated_at).total_seconds() / 86400
            other_age = (now - other.updated_at).total_seconds() / 86400
            
            self_time_weight = np.exp(-0.05 * self_age)
            other_time_weight = np.exp(-0.05 * other_age)
            
            # 综合权重 = 置信度权重 * 时间权重
            self_final_weight = self_conf * self_time_weight
            other_final_weight = other_conf * other_time_weight
            
            total_weight = self_final_weight + other_final_weight
            if total_weight == 0:
                return self
            
            if self_final_weight >= other_final_weight:
                return self
            else:
                return other
        
        else:  # confidence_weighted (默认)
            self_conf = self.compute_decayed_confidence()
            other_conf = other.compute_decayed_confidence()
            total_conf = self_conf + other_conf
            
            if total_conf == 0:
                return self
            
            # 加权平均内容
            merged_content = {}
            all_keys = set(self.content.keys()) | set(other.content.keys())
            
            for key in all_keys:
                self_val = self.content.get(key)
                other_val = other.content.get(key)
                
                if self_val is None:
                    merged_content[key] = other_val
                elif other_val is None:
                    merged_content[key] = self_val
                elif isinstance(self_val, (int, float)) and isinstance(other_val, (int, float)):
                    # 数值类型加权平均
                    weight_self = self_conf / total_conf
                    merged_content[key] = round(self_val * weight_self + other_val * (1 - weight_self), 2)
                elif isinstance(self_val, list) and isinstance(other_val, list):
                    # 列表类型：合并去重
                    merged_content[key] = list(set(self_val + other_val))
                else:
                    # 非数值类型：选择置信度高的
                    if self_conf >= other_conf:
                        merged_content[key] = self_val
                    else:
                        merged_content[key] = other_val
            
            # 创建合并后的新条目
            new_confidence = (self_conf * self_conf + other_conf * other_conf) / total_conf if total_conf > 0 else 0
            
            return MemoryEntry(
                id=self.id,  # 保留较早的 ID
                agent_id=self.agent_id,
                category=self.category,
                content=merged_content,
                confidence=min(new_confidence, self.max_confidence),
                created_at=min(self.created_at, other.created_at),
                updated_at=datetime.now(),
                access_count=self.access_count + other.access_count,
                last_accessed=max(
                    self.last_accessed or self.created_at,
                    other.last_accessed or other.created_at
                ),
                decay_rate=self.decay_rate,
                half_life=self.half_life,
                usage_boost=self.usage_boost,
                max_confidence=self.max_confidence
            )


class StagingArea(BaseModel):
    """
    临时区：存储待提交的修改补丁
    实现两阶段提交 (2PC) 的 Prepare 阶段
    """
    patches: List[StatePatch] = Field(default_factory=list)
    is_locked: bool = Field(default=False, description="是否已锁定，防止并发修改")
    created_at: datetime = Field(default_factory=datetime.now)
    version_hash: Optional[str] = Field(default=None, description="创建时的状态版本哈希")
    
    def add_patch(self, patch: StatePatch):
        """添加补丁到临时区"""
        self.patches.append(patch)
        
    def clear(self):
        """清空临时区"""
        self.patches = []
        self.is_locked = False
        self.version_hash = None
        
    def get_patches_by_agent(self, agent_id: str) -> List[StatePatch]:
        """获取指定 Agent 的所有补丁"""
        return [p for p in self.patches if p.agent_id == agent_id]
        
    def has_conflicts(self) -> bool:
        """检查是否存在路径冲突（简单版：同一路径被多次修改）"""
        paths = [p.target_path for p in self.patches]
        return len(paths) != len(set(paths))
        
    def get_conflicting_patches(self) -> List[tuple]:
        """返回所有冲突的补丁对"""
        conflicts = []
        path_map = {}
        for patch in self.patches:
            if patch.target_path in path_map:
                conflicts.append((path_map[patch.target_path], patch))
            else:
                path_map[patch.target_path] = patch
        return conflicts


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
    
    # 长期记忆存储
    long_term_memories: List[Dict[str, Any]] = Field(default_factory=list)
    
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
