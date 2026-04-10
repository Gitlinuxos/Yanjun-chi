"""行程编排师智能体"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base_agent import BaseAgent


class ItineraryAgent(BaseAgent):
    """生成详细行程安排"""
    
    def __init__(self, api_key: str, tool_gateway, mock_mode: bool = False):
        super().__init__(api_key, tool_gateway, mock_mode)
        self.name = "ItineraryAgent"
    
    async def process(self, user_input: str, conversation_history: List[Dict], 
                     current_state: Any) -> Dict[str, Any]:
        """生成行程计划"""
        self.log("正在编排行程...")
        
        if self.mock_mode:
            return await self._mock_process(user_input, current_state)
        
        # 真实 LLM 调用
        system_prompt = """你是一个旅行行程规划专家。根据目的地和天数生成详细行程。

请返回 JSON 格式：
{
    "itinerary": [
        {
            "day": 1,
            "date": "日期",
            "activities": [
                {"time": "上午", "activity": "活动内容", "location": "地点"},
                {"time": "下午", "activity": "活动内容", "location": "地点"}
            ],
            "meals": {"breakfast": "", "lunch": "", "dinner": ""},
            "accommodation": "住宿建议",
            "tips": "小贴士"
        }
    ]
}
"""
        dest = current_state.selected_destination if current_state else None
        days = current_state.user_profile.days if current_state and current_state.user_profile else 5
        user_prompt = f"目的地：{dest}, 天数：{days}"
        
        try:
            result = await self.call_llm(system_prompt, user_prompt)
            return result
        except:
            return await self._mock_process(user_input, current_state)
    
    async def _mock_process(self, user_input: str, current_state: Any) -> Dict[str, Any]:
        """模拟处理 - 生成示例行程"""
        dest = current_state.selected_destination if current_state and current_state.selected_destination else None
        days = 5
        
        if dest and hasattr(dest, 'suggested_days'):
            days = dest.suggested_days
        elif isinstance(dest, dict):
            days = dest.get('suggested_days', 5)
        
        if current_state and current_state.user_profile:
            profile_days = current_state.user_profile.days
            if profile_days and profile_days > 0:
                days = profile_days
        
        # 生成示例行程
        itinerary = []
        base_date = datetime.now() + timedelta(days=7)
        
        for day in range(1, days + 1):
            date_str = (base_date + timedelta(days=day-1)).strftime("%Y-%m-%d")
            
            day_plan = {
                'day': day,
                'date': date_str,
                'activities': [],
                'meals': {'breakfast': '', 'lunch': '', 'dinner': ''},
                'accommodation': '当地舒适型酒店',
                'tips': ''
            }
            
            if day == 1:
                day_plan['activities'] = [
                    {'time': '上午', 'activity': '抵达目的地，办理入住', 'location': '市区'},
                    {'time': '下午', 'activity': '市区游览，适应环境', 'location': '市中心'},
                    {'time': '晚上', 'activity': '品尝当地特色美食', 'location': '美食街'}
                ]
                day_plan['meals'] = {'breakfast': '自理', 'lunch': '当地小吃', 'dinner': '特色餐厅'}
                day_plan['tips'] = '第一天不要安排太满，注意休息适应'
                
            elif day == days:
                day_plan['activities'] = [
                    {'time': '上午', 'activity': '购买纪念品，整理行李', 'location': '商业区'},
                    {'time': '下午', 'activity': '前往机场/车站，返程', 'location': '交通枢纽'}
                ]
                day_plan['meals'] = {'breakfast': '酒店早餐', 'lunch': '简餐', 'dinner': '自理'}
                day_plan['tips'] = '预留充足时间前往车站，注意航班时间'
                
            else:
                day_plan['activities'] = [
                    {'time': '上午', 'activity': '游览主要景点 A', 'location': '核心景区'},
                    {'time': '中午', 'activity': '景区内用餐', 'location': '景区餐厅'},
                    {'time': '下午', 'activity': '游览主要景点 B', 'location': '周边景点'},
                    {'time': '晚上', 'activity': '自由活动或观看演出', 'location': '市区'}
                ]
                day_plan['meals'] = {'breakfast': '酒店早餐', 'lunch': '景区餐', 'dinner': '当地特色'}
                day_plan['tips'] = '穿舒适的鞋子，带好防晒用品'
            
            itinerary.append(day_plan)
        
        self.log(f"生成{days}天行程")
        
        return {'itinerary': itinerary}
