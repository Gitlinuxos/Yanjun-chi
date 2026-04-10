"""交通规划师"""
import asyncio
from typing import Dict, Any, Optional

from .base_agent import BaseAgent


class TransportAgent(BaseAgent):
    """实时查询票价与时刻，多模态方案对比"""
    
    @property
    def role(self) -> str:
        return "Transport Planner"
    
    @property
    def system_prompt(self) -> str:
        return """你是一位专业的交通规划师。
你的任务是根据目的地和用户偏好推荐交通方案。

输出格式：
{
  "options": [
    {
      "type": "飞机/高铁/普通火车/大巴/自驾",
      "duration": 耗时 (小时),
      "cost": 费用 (元),
      "comfort_level": 1-5,
      "description": "方案描述",
      "notes": ["注意事项"]
    }
  ]
}

注意事项：
1. 提供至少 3 种交通方案
2. 根据用户偏好排序 (speed/comfort/economy/balanced)
3. 费用估算要合理
4. 输出必须是合法的 JSON 格式"""
    
    async def process(
        self, 
        user_input: str,
        destination: str,
        origin: str = "出发地",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        context = {"destination": destination, "origin": origin}
        prompt = self.build_prompt(user_input, context)
        
        # 检查缓存
        cache_key = f"transport:{origin}->{destination}"
        cached = self.state_manager.cache_lookup(cache_key, "transport")
        if cached:
            return cached
        
        # 调用 LLM 生成方案
        result = self.call_llm(prompt)
        
        # 存入缓存
        if result:
            self.state_manager.cache_store(cache_key, result, "transport")
        
        return result
