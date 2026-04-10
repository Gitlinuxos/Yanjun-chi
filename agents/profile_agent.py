"""用户画像分析师"""
import asyncio
from typing import Dict, Any, Optional

from .base_agent import BaseAgent


class ProfileAgent(BaseAgent):
    """从对话中提取用户偏好，构建用户画像"""
    
    @property
    def role(self) -> str:
        return "Profile Analyst"
    
    @property
    def system_prompt(self) -> str:
        return """你是一位专业的用户画像分析师。
你的任务是从用户的自然语言描述中提取旅行相关信息。

提取字段包括：
- name: 姓名 (可选)
- days: 旅行天数
- budget: 预算 (元)
- travelers: 出行人数
- preferred_styles: 旅行风格 (NATURE/CULTURE/ADVENTURE/RELAX/FOOD/HISTORY)
- interests: 兴趣标签列表
- special_needs: 特殊需求

注意事项：
1. 如果信息缺失，不要编造，留空或设为 null
2. 旅行风格必须从枚举值中选择
3. 输出必须是合法的 JSON 格式
4. 先思考 (<reasoning>)，再输出 JSON"""
    
    async def process(self, user_input: str, **kwargs) -> Optional[Dict[str, Any]]:
        prompt = self.build_prompt(user_input)
        result = self.call_llm(prompt)
        return result
