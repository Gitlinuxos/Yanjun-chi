"""预算精算师智能体"""
from typing import Dict, Any, List
from .base_agent import BaseAgent


class BudgetAgent(BaseAgent):
    """计算和管理旅行预算"""
    
    def __init__(self, api_key: str, tool_gateway, mock_mode: bool = False):
        super().__init__(api_key, tool_gateway, mock_mode)
        self.name = "BudgetAgent"
    
    async def process(self, user_input: str, conversation_history: List[Dict], 
                     current_state: Any) -> Dict[str, Any]:
        """计算预算明细"""
        self.log("正在核算预算...")
        
        if self.mock_mode:
            return await self._mock_process(user_input, current_state)
        
        # 真实 LLM 调用
        system_prompt = """你是一个旅行预算专家。根据行程和目的地计算详细预算。

请返回 JSON 格式：
{
    "budget_breakdown": {
        "transport": 交通费用，
        "accommodation": 住宿费用，
        "food": 餐饮费用，
        "tickets": 门票费用，
        "shopping": 购物费用，
        "other": 其他费用，
        "total": 总计，
        "status": "充足/紧张/超支"
    },
    "suggestions": ["节省建议"]
}
"""
        dest = current_state.selected_destination if current_state else None
        days = current_state.user_profile.days if current_state and current_state.user_profile else 5
        budget = current_state.user_profile.budget if current_state and current_state.user_profile else 5000
        user_prompt = f"目的地：{dest}, 天数：{days}, 预算：{budget}"
        
        try:
            result = await self.call_llm(system_prompt, user_prompt)
            return result
        except:
            return await self._mock_process(user_input, current_state)
    
    async def _mock_process(self, user_input: str, current_state: Any) -> Dict[str, Any]:
        """模拟处理 - 计算预算"""
        profile = current_state.user_profile if current_state and current_state.user_profile else None
        budget_limit = profile.budget if profile and profile.budget else 5000
        days = profile.days if profile and profile.days else 5
        
        # 估算各项费用
        transport = 1000  # 往返交通
        accommodation = 400 * days  # 住宿
        food = 200 * days  # 餐饮
        tickets = 300 * (days - 1)  # 门票
        shopping = 500  # 购物
        other = 300  # 其他
        
        total = transport + accommodation + food + tickets + shopping + other
        
        # 判断预算状态
        if total <= budget_limit * 0.8:
            status = "充足"
        elif total <= budget_limit:
            status = "紧张"
        else:
            status = "超支"
        
        # 生成建议
        suggestions = []
        if status == "超支":
            suggestions.append("考虑选择经济型住宿可节省约 500 元")
            suggestions.append("减少购物预算或选择免费景点")
        elif status == "紧张":
            suggestions.append("建议预留应急资金")
            suggestions.append("可选择当地特色小吃代替正餐")
        else:
            suggestions.append("预算充足，可适当提升体验")
            suggestions.append("推荐尝试当地特色表演或 SPA")
        
        budget_breakdown = {
            'transport': transport,
            'accommodation': accommodation,
            'food': food,
            'tickets': tickets,
            'shopping': shopping,
            'other': other,
            'total': total,
            'status': status
        }
        
        self.log(f"预算核算完成：总计{total}元，状态：{status}")
        
        return {
            'budget_breakdown': budget_breakdown,
            'suggestions': suggestions
        }
