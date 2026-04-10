"""交通规划师智能体"""
from typing import Dict, Any, List
from .base_agent import BaseAgent


class TransportAgent(BaseAgent):
    """规划和推荐交通方案"""
    
    def __init__(self, api_key: str, tool_gateway, mock_mode: bool = False):
        super().__init__(api_key, tool_gateway, mock_mode)
        self.name = "TransportAgent"
    
    async def process(self, user_input: str, conversation_history: List[Dict], 
                     current_state: Any) -> Dict[str, Any]:
        """生成交通方案"""
        self.log("正在规划交通方案...")
        
        if self.mock_mode:
            return await self._mock_process(user_input, current_state)
        
        # 真实 LLM 调用
        system_prompt = """你是一个交通规划专家。根据目的地和用户偏好推荐交通方式。

可选交通方式：飞机、高铁、普通火车、大巴、自驾

请返回 JSON 格式：
{
    "transport_options": [
        {
            "type": "交通方式",
            "duration": 耗时 (小时),
            "cost": 费用 (元),
            "comfort_level": 舒适度 1-5,
            "description": "描述"
        }
    ],
    "recommended": "推荐的方式"
}
"""
        user_profile = current_state.user_profile if current_state else {}
        dest = current_state.selected_destination if current_state else None
        user_prompt = f"用户偏好：{user_profile}, 目的地：{dest}"
        
        try:
            result = await self.call_llm(system_prompt, user_prompt)
            return result
        except:
            return await self._mock_process(user_input, current_state)
    
    async def _mock_process(self, user_input: str, current_state: Any) -> Dict[str, Any]:
        """模拟处理 - 返回预设交通方案"""
        # 根据距离和偏好生成方案
        transport_options = [
            {
                'type': '飞机',
                'duration': 2.5,
                'cost': 1200,
                'comfort_level': 4,
                'description': '最快速度到达，适合时间紧张的旅客'
            },
            {
                'type': '高铁',
                'duration': 6,
                'cost': 550,
                'comfort_level': 5,
                'description': '舒适便捷，准点率高，推荐选择'
            },
            {
                'type': '普通火车',
                'duration': 12,
                'cost': 300,
                'comfort_level': 3,
                'description': '经济实惠，适合预算有限的旅客'
            },
            {
                'type': '自驾',
                'duration': 8,
                'cost': 800,
                'comfort_level': 4,
                'description': '自由灵活，可沿途游玩'
            }
        ]
        
        # 根据用户偏好推荐
        profile = current_state.user_profile if current_state and current_state.user_profile else {}
        pref = profile.get('transport_preference', '平衡') if hasattr(profile, 'get') else profile.get('transport_preference', '平衡')
        
        recommended = '高铁'  # 默认推荐
        if pref == '速度优先':
            recommended = '飞机'
        elif pref == '经济优先':
            recommended = '普通火车'
        elif pref == '舒适优先':
            recommended = '高铁'
        
        self.log(f"生成交通方案，推荐：{recommended}")
        
        return {
            'transport_options': transport_options,
            'recommended': recommended
        }
