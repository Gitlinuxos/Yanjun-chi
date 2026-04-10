"""目的地推荐专家智能体"""
from typing import Dict, Any, List
from .base_agent import BaseAgent


class DestinationAgent(BaseAgent):
    """基于用户偏好推荐目的地"""
    
    def __init__(self, api_key: str, tool_gateway, mock_mode: bool = False):
        super().__init__(api_key, tool_gateway, mock_mode)
        self.name = "DestinationAgent"
        
        # 内置目的地数据库（模拟模式使用）
        self.destinations_db = [
            {
                'name': '桂林',
                'description': '山水甲天下，漓江风光如画',
                'features': ['自然风光', '山水', '竹筏', '喀斯特地貌'],
                'best_season': ['春季', '秋季'],
                'avg_cost': 4500,
                'suggested_days': 5,
                'reason': '完美匹配"有山有水"的需求'
            },
            {
                'name': '杭州',
                'description': '人间天堂，西湖美景与历史文化交融',
                'features': ['自然风光', '人文历史', '西湖', '美食'],
                'best_season': ['春季', '秋季', '冬季'],
                'avg_cost': 4000,
                'suggested_days': 4,
                'reason': '人文与自然完美结合'
            },
            {
                'name': '张家界',
                'description': '奇峰三千，秀水八百',
                'features': ['自然风光', '山峰', '玻璃栈道', '国家森林公园'],
                'best_season': ['春季', '夏季', '秋季'],
                'avg_cost': 5000,
                'suggested_days': 5,
                'reason': '世界级自然景观'
            },
            {
                'name': '三亚',
                'description': '热带海滨度假胜地',
                'features': ['海滩', '度假', '潜水', '热带风光'],
                'best_season': ['冬季', '春季'],
                'avg_cost': 6000,
                'suggested_days': 5,
                'reason': '阳光沙滩的休闲之选'
            },
            {
                'name': '成都',
                'description': '天府之国，美食与熊猫的故乡',
                'features': ['美食', '文化', '大熊猫', '休闲'],
                'best_season': ['春季', '秋季'],
                'avg_cost': 4000,
                'suggested_days': 4,
                'reason': '慢生活体验之都'
            }
        ]
    
    async def process(self, user_input: str, conversation_history: List[Dict], 
                     current_state: Any) -> Dict[str, Any]:
        """生成目的地推荐"""
        self.log("正在生成目的地推荐...")
        
        if self.mock_mode:
            return await self._mock_process(user_input, current_state)
        
        # 真实 LLM 调用
        system_prompt = """你是一个旅行目的地推荐专家。根据用户偏好推荐合适的目的地。

请返回 JSON 格式：
{
    "destinations": [
        {
            "name": "目的地名称",
            "description": "简介",
            "features": ["特色标签"],
            "avg_cost": 人均花费，
            "suggested_days": 建议天数，
            "reason": "推荐理由"
        }
    ]
}
"""
        user_profile = current_state.user_profile if current_state else {}
        user_prompt = f"用户偏好：{user_profile}"
        
        try:
            result = await self.call_llm(system_prompt, user_prompt)
            return result
        except:
            return await self._mock_process(user_input, current_state)
    
    async def _mock_process(self, user_input: str, current_state: Any) -> Dict[str, Any]:
        """模拟处理 - 返回预设推荐"""
        # 简单匹配逻辑
        profile = current_state.user_profile if current_state and current_state.user_profile else {}
        
        styles = profile.get('travel_styles', []) if hasattr(profile, 'get') else profile.get('travel_styles', [])
        budget = profile.get('budget', 5000) if hasattr(profile, 'get') else profile.get('budget', 5000)
        days = profile.get('days', 5) if hasattr(profile, 'get') else profile.get('days', 5)
        
        # 筛选匹配目的地
        matched = []
        for dest in self.destinations_db:
            score = 0
            
            # 风格匹配
            for style in (styles if isinstance(styles, list) else []):
                if any(style in feature for feature in dest['features']):
                    score += 2
            
            # 预算匹配
            if dest['avg_cost'] <= budget * 1.1:
                score += 2
            
            # 天数匹配
            if abs(dest['suggested_days'] - days) <= 1:
                score += 1
            
            if score > 0:
                dest_copy = dest.copy()
                dest_copy['match_score'] = score
                matched.append(dest_copy)
        
        # 按评分排序
        matched.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        # 返回前 3 个
        recommendations = matched[:3] if matched else self.destinations_db[:3]
        
        self.log(f"推荐目的地：{[d['name'] for d in recommendations]}")
        
        return {'destinations': recommendations}
