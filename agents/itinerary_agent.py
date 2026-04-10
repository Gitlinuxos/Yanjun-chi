"""行程编排师"""
import asyncio
from typing import Dict, Any, Optional

from .base_agent import BaseAgent


class ItineraryAgent(BaseAgent):
    """生成详细日程，逻辑校验与动态调整"""
    
    @property
    def role(self) -> str:
        return "Itinerary Planner"
    
    @property
    def system_prompt(self) -> str:
        return """你是一位经验丰富的行程规划师。
你的任务是为选定的目的地生成详细的每日行程。

输出格式：
{
  "itinerary": [
    {
      "day": 1,
      "date": "可选日期",
      "morning": "上午安排",
      "noon": "中午安排",
      "afternoon": "下午安排",
      "evening": "晚上安排",
      "attractions": ["景点列表"],
      "meals": ["餐饮建议"],
      "transport": "市内交通",
      "tips": ["当日提示"]
    }
  ]
}

注意事项：
1. 行程安排要合理，不要过于紧凑
2. 考虑景点之间的距离和交通时间
3. 包含当地特色美食推荐
4. 输出必须是合法的 JSON 格式"""
    
    async def process(
        self,
        user_input: str,
        destination: str,
        days: int,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        context = {"destination": destination, "days": days}
        prompt = self.build_prompt(user_input, context)
        
        # 检查缓存
        cache_key = f"itinerary:{destination}:{days}days"
        cached = self.state_manager.cache_lookup(cache_key, "general")
        if cached:
            return cached
        
        # 调用 LLM 生成行程
        result = self.call_llm(prompt)
        
        # 存入缓存
        if result:
            self.state_manager.cache_store(cache_key, result, "general")
        
        return result
