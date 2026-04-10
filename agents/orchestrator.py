"""协调者 Agent - 核心大脑"""
import asyncio
from typing import Dict, Any, Optional, List

from .base_agent import BaseAgent


class OrchestratorAgent(BaseAgent):
    """
    协调者 Agent
    - 意图识别
    - 任务分发
    - 结果汇总
    - 流程控制
    """
    
    @property
    def role(self) -> str:
        return "Orchestrator"
    
    @property
    def system_prompt(self) -> str:
        return """你是一位智能旅行助手的协调者。
你的任务是理解用户意图，调度专业 Agent，并汇总结果。

可用意图类型：
- greet: 问候/打招呼
- extract_profile: 提取用户偏好
- recommend_destination: 推荐目的地
- plan_transport: 规划交通
- generate_itinerary: 生成行程
- calculate_budget: 计算预算
- check_weather: 查询天气
- modify_plan: 修改计划
- confirm_plan: 确认计划
- chat: 普通聊天

输出格式：
{
  "intent": "意图类型",
  "confidence": 置信度 (0-1),
  "parameters": {...},
  "response": "直接回复用户的话"
}

注意事项：
1. 准确识别用户意图
2. 提取关键参数
3. 对于模糊请求要主动询问
4. 输出必须是合法的 JSON 格式"""
    
    def __init__(self, state_manager, tool_gateway, web_services, agents: Dict[str, BaseAgent]):
        super().__init__(state_manager, tool_gateway, web_services)
        self.agents = agents
    
    async def process(self, user_input: str, **kwargs) -> Optional[Dict[str, Any]]:
        # 第一步：识别意图
        intent_result = await self._recognize_intent(user_input)
        
        if not intent_result:
            return {"error": "无法理解您的意图"}
        
        intent = intent_result.get("intent", "chat")
        parameters = intent_result.get("parameters", {})
        
        # 第二步：根据意图分发任务
        result = await self._dispatch_task(intent, user_input, parameters)
        
        # 第三步：汇总结果
        return self._format_response(intent, intent_result, result)
    
    async def _recognize_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        """识别用户意图"""
        prompt = self.build_prompt(user_input)
        result = self.call_llm(prompt)
        return result
    
    async def _dispatch_task(
        self, 
        intent: str, 
        user_input: str, 
        parameters: Dict
    ) -> Optional[Dict[str, Any]]:
        """分发任务到专业 Agent"""
        
        task_map = {
            "extract_profile": ("profile_agent", ["user_input"]),
            "recommend_destination": ("destination_agent", ["user_input", "user_profile"]),
            "plan_transport": ("transport_agent", ["user_input", "destination"]),
            "generate_itinerary": ("itinerary_agent", ["user_input", "destination", "days"]),
            "calculate_budget": ("budget_agent", ["user_input", "total_budget", "destination", "days"]),
            "check_weather": ("weather_agent", ["user_input", "city", "days"]),
        }
        
        if intent not in task_map:
            return None
        
        agent_name, required_params = task_map[intent]
        agent = self.agents.get(agent_name)
        
        if not agent:
            return {"error": f"找不到对应的 Agent: {agent_name}"}
        
        # 准备参数
        call_params = {"user_input": user_input}
        for param in required_params:
            if param != "user_input":
                call_params[param] = parameters.get(param) or kwargs.get(param)
        
        # 调用 Agent
        try:
            result = await agent.process(**call_params)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def _format_response(
        self, 
        intent: str, 
        intent_result: Dict, 
        task_result: Optional[Dict]
    ) -> Dict[str, Any]:
        """格式化最终响应"""
        response = {
            "intent": intent,
            "original_input": intent_result.get("response", ""),
            "task_result": task_result
        }
        
        if task_result and "error" in task_result:
            response["status"] = "error"
            response["message"] = task_result["error"]
        else:
            response["status"] = "success"
        
        return response
