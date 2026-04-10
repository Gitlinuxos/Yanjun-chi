"""目的地推荐专家"""
import asyncio
from typing import Dict, Any, Optional, List

from state.models import Destination

from .base_agent import BaseAgent


class DestinationAgent(BaseAgent):
    """实时检索热门目的地，深度挖掘人文历史"""
    
    @property
    def role(self) -> str:
        return "Destination Expert"
    
    @property
    def system_prompt(self) -> str:
        return """你是一位资深的旅游目的地专家。
你的任务是根据用户偏好推荐合适的旅游目的地。

输出格式：
{
  "destinations": [
    {
      "name": "目的地名称",
      "description": "简介",
      "features": ["特色标签"],
      "best_season": "最佳季节",
      "recommended_days": 建议天数,
      "estimated_cost": 人均费用,
      "reason": "推荐理由"
    }
  ]
}

注意事项：
1. 推荐 3-5 个目的地
2. 理由要充分结合用户偏好
3. 费用估算要合理
4. 输出必须是合法的 JSON 格式"""
    
    async def process(
        self, 
        user_input: str, 
        user_profile: Optional[Dict] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        context = {"user_profile": user_profile} if user_profile else {}
        prompt = self.build_prompt(user_input, context)
        
        # 先尝试从缓存获取
        cached = self.state_manager.cache_lookup(
            f"recommend:{user_input}", 
            "destination"
        )
        if cached:
            return cached
        
        # 调用联网搜索获取最新信息
        search_results = self.web_services.search_web(
            f"{user_input} 旅游攻略 最佳目的地",
            num_results=3
        )
        
        # 调用 LLM 生成推荐
        result = self.call_llm(prompt)
        
        # 存入缓存
        if result:
            self.state_manager.cache_store(
                f"recommend:{user_input}",
                result,
                "destination"
            )
        
        return result
