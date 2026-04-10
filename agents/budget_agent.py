"""预算精算师"""
import asyncio
from typing import Dict, Any, Optional

from .base_agent import BaseAgent


class BudgetAgent(BaseAgent):
    """实时费用估算，预算监控与优化建议"""
    
    @property
    def role(self) -> str:
        return "Budget Analyst"
    
    @property
    def system_prompt(self) -> str:
        return """你是一位专业的预算分析师。
你的任务是根据旅行计划估算各项费用并提供预算建议。

输出格式：
{
  "total_budget": 总预算，
  "breakdown": {
    "transport": 交通费，
    "accommodation": 住宿费，
    "food": 餐饮费，
    "tickets": 门票费，
    "shopping": 购物费，
    "others": 其他费用
  },
  "status": "sufficient/tight/over_budget",
  "remaining": 剩余预算，
  "suggestions": ["节省建议"]
}

注意事项：
1. 各项费用之和应等于总花费
2. 预算状态要根据总预算判断
3. 提供实用的节省建议
4. 输出必须是合法的 JSON 格式"""
    
    async def process(
        self,
        user_input: str,
        total_budget: float,
        destination: str,
        days: int,
        travelers: int = 1,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        context = {
            "total_budget": total_budget,
            "destination": destination,
            "days": days,
            "travelers": travelers
        }
        prompt = self.build_prompt(user_input, context)
        
        result = self.call_llm(prompt)
        return result
