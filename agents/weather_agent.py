"""气象顾问"""
import asyncio
from typing import Dict, Any, Optional, List

from .base_agent import BaseAgent


class WeatherAgent(BaseAgent):
    """实时天气预报，灾害预警与出行建议"""
    
    @property
    def role(self) -> str:
        return "Weather Advisor"
    
    @property
    def system_prompt(self) -> str:
        return """你是一位专业的气象顾问。
你的任务是提供旅行期间的天气预报和出行建议。

输出格式：
{
  "forecast": [
    {
      "date": "YYYY-MM-DD",
      "temperature_high": 最高温，
      "temperature_low": 最低温，
      "condition": "天气状况",
      "precipitation": 降水概率 (0-100),
      "wind": "风力风向",
      "advice": "出行建议",
      "warning": "预警信息 (可选)"
    }
  ]
}

注意事项：
1. 提供完整的旅行期间预报
2. 如有恶劣天气要给出预警
3. 建议要具体实用
4. 输出必须是合法的 JSON 格式"""
    
    async def process(
        self,
        user_input: str,
        city: str,
        days: int = 5,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        # 检查缓存
        cache_key = f"weather:{city}:{days}days"
        cached = self.state_manager.cache_lookup(cache_key, "weather")
        if cached:
            return cached
        
        # 调用实时天气 API
        weather_data = self.web_services.get_weather(city, days)
        
        # 格式化结果
        result = {"forecast": weather_data}
        
        # 存入缓存
        self.state_manager.cache_store(cache_key, result, "weather")
        
        return result
