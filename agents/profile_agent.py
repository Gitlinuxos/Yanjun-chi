"""用户画像分析师智能体"""
from typing import Dict, Any, List
from .base_agent import BaseAgent


class ProfileAgent(BaseAgent):
    """从对话中提取并更新用户画像"""
    
    def __init__(self, api_key: str, tool_gateway, mock_mode: bool = False):
        super().__init__(api_key, tool_gateway, mock_mode)
        self.name = "ProfileAgent"
    
    async def process(self, user_input: str, conversation_history: List[Dict], 
                     current_state: Any) -> Dict[str, Any]:
        """提取用户信息"""
        self.log("正在分析用户偏好...")
        
        if self.mock_mode:
            return await self._mock_process(user_input, current_state)
        
        # 真实 LLM 调用实现信息提取
        system_prompt = """你是一个用户画像分析专家。从用户对话中提取旅行相关信息。

请以 JSON 格式返回：
{
    "travel_styles": ["自然风光", "休闲度假"],
    "budget": 5000,
    "days": 5,
    "people_count": 1,
    "departure_city": "北京",
    "special_needs": "",
    "transport_preference": "平衡"
}
"""
        user_prompt = f"用户输入：{user_input}"
        
        try:
            result = await self.call_llm(system_prompt, user_prompt)
            return {'user_profile': result}
        except:
            return await self._mock_process(user_input, current_state)
    
    async def _mock_process(self, user_input: str, current_state: Any) -> Dict[str, Any]:
        """模拟处理"""
        # 简单的关键词匹配
        profile = {}
        
        if '山' in user_input or '水' in user_input or '自然' in user_input:
            profile['travel_styles'] = ['自然风光']
        
        if '放松' in user_input or '休闲' in user_input:
            if 'travel_styles' not in profile:
                profile['travel_styles'] = []
            profile['travel_styles'].append('休闲度假')
        
        # 提取数字（预算和天数）
        import re
        numbers = re.findall(r'\d+', user_input)
        for num in numbers:
            n = int(num)
            if 1000 <= n <= 100000:
                profile['budget'] = n
            elif 1 <= n <= 30:
                profile['days'] = n
        
        if not profile:
            profile = {
                'travel_styles': ['自然风光', '休闲度假'],
                'budget': 5000,
                'days': 5,
                'people_count': 1
            }
        
        self.log(f"提取到用户画像：{profile}")
        return {'user_profile': profile}
