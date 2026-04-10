"""气象顾问智能体"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random
from .base_agent import BaseAgent


class WeatherAgent(BaseAgent):
    """提供天气预报和出行建议"""
    
    def __init__(self, api_key: str, tool_gateway, mock_mode: bool = False):
        super().__init__(api_key, tool_gateway, mock_mode)
        self.name = "WeatherAgent"
        
        # 天气类型
        self.weather_conditions = ['晴', '多云', '阴', '小雨', '中雨', '大雨']
    
    async def process(self, user_input: str, conversation_history: List[Dict], 
                     current_state: Any) -> Dict[str, Any]:
        """获取天气预报"""
        self.log("正在查询天气...")
        
        if self.mock_mode:
            return await self._mock_process(user_input, current_state)
        
        # 真实场景可调用天气 API
        # 这里使用 LLM 生成建议
        system_prompt = """你是一个气象顾问。根据目的地和时间提供天气预警和出行建议。

请返回 JSON 格式：
{
    "weather_forecast": [
        {
            "date": "日期",
            "temperature_high": 最高温，
            "temperature_low": 最低温，
            "condition": "天气状况",
            "precipitation": 降水概率，
            "wind": "风力",
            "suggestion": "出行建议"
        }
    ],
    "alerts": ["天气预警"]
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
        """模拟处理 - 生成天气预报"""
        profile = current_state.user_profile if current_state and current_state.user_profile else None
        days = profile.days if profile and profile.days else 5
        
        weather_forecast = []
        base_date = datetime.now() + timedelta(days=7)
        alerts = []
        
        for i in range(days):
            date_str = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            
            # 随机生成天气
            condition = random.choice(self.weather_conditions)
            temp_high = random.randint(20, 35)
            temp_low = temp_high - random.randint(5, 12)
            precipitation = random.randint(0, 80) if '雨' in condition else random.randint(0, 30)
            wind = random.choice(['微风', '1-2 级', '2-3 级', '3-4 级'])
            
            # 生成建议
            if '大雨' in condition:
                suggestion = "暴雨天气，建议调整行程或准备雨具"
                alerts.append(f"{date_str}有大雨，请注意安全")
            elif '雨' in condition:
                suggestion = "有降雨，请携带雨具，注意防滑"
            elif temp_high > 32:
                suggestion = "天气炎热，注意防晒补水"
            elif temp_low < 15:
                suggestion = "早晚温差大，建议带外套"
            else:
                suggestion = "天气适宜，适合户外活动"
            
            weather_forecast.append({
                'date': date_str,
                'temperature_high': temp_high,
                'temperature_low': temp_low,
                'condition': condition,
                'precipitation': precipitation,
                'wind': wind,
                'suggestion': suggestion
            })
        
        self.log(f"生成{days}天天气预报")
        
        return {
            'weather_forecast': weather_forecast,
            'alerts': alerts
        }
