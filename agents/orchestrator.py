"""协调者智能体 - 核心大脑"""
import json
from typing import Dict, Any, List

from .base_agent import BaseAgent


class OrchestratorAgent(BaseAgent):
    """协调者智能体 - 负责任务分发和结果汇总"""
    
    def __init__(self, api_key: str, tool_gateway, mock_mode: bool = False):
        super().__init__(api_key, tool_gateway, mock_mode)
        self.name = "Orchestrator"
    
    async def process(self, user_input: str, conversation_history: List[Dict], 
                     current_state: Any) -> Dict[str, Any]:
        """处理用户请求
        
        流程：
        1. 识别用户意图
        2. 调度专业智能体
        3. 汇总结果
        """
        self.log(f"收到用户输入：{user_input[:50]}...")
        
        # 步骤 1: 意图识别
        intent = await self._recognize_intent(user_input, current_state)
        self.log(f"识别意图：{intent.get('type', 'unknown')}")
        
        # 步骤 2: 根据意图调度智能体
        result = await self._dispatch_tasks(intent, user_input, current_state)
        
        # 步骤 3: 生成响应消息
        message = self._generate_response(result, intent)
        
        return {
            'message': message,
            'state': result.get('state_updates', {}),
            'state_updated': True if result.get('state_updates') else False,
            'intent': intent
        }
    
    async def _recognize_intent(self, user_input: str, current_state: Any) -> Dict[str, Any]:
        """识别用户意图"""
        if self.mock_mode:
            return self._mock_intent_recognition(user_input, current_state)
        
        system_prompt = """你是一个旅行助手的意图识别模块。请分析用户输入，识别其意图类型。

可用的意图类型：
- greet: 问候/打招呼
- provide_info: 提供旅行信息（偏好、预算、时间等）
- request_recommendation: 请求目的地推荐
- modify_plan: 修改已有计划
- confirm_plan: 确认计划
- ask_budget: 询问预算详情
- ask_weather: 询问天气
- chat: 普通聊天
- exit: 退出

请以 JSON 格式返回：
{
    "type": "意图类型",
    "entities": {"提取的关键实体"},
    "confidence": 置信度 (0-1),
    "needs_context": 是否需要上下文
}
"""
        
        user_prompt = f"当前状态：{current_state.current_step if current_state else 'initial'}\n用户输入：{user_input}"
        
        try:
            result = await self.call_llm(system_prompt, user_prompt)
            return result
        except:
            return self._mock_intent_recognition(user_input, current_state)
    
    def _mock_intent_recognition(self, user_input: str, current_state: Any) -> Dict[str, Any]:
        """模拟意图识别"""
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['你好', 'hello', 'hi', '嗨']):
            return {'type': 'greet', 'entities': {}, 'confidence': 0.9}
        
        if any(word in user_input_lower for word in ['想去', '要去', '旅行', '旅游', '天', '预算', '元']):
            return {'type': 'provide_info', 'entities': {}, 'confidence': 0.8}
        
        if any(word in user_input_lower for word in ['推荐', '哪里', '什么地方']):
            return {'type': 'request_recommendation', 'entities': {}, 'confidence': 0.85}
        
        if any(word in user_input_lower for word in ['修改', '调整', '改变', '换']):
            return {'type': 'modify_plan', 'entities': {}, 'confidence': 0.8}
        
        if any(word in user_input_lower for word in ['确认', '好的', '可以', '满意']):
            return {'type': 'confirm_plan', 'entities': {}, 'confidence': 0.75}
        
        return {'type': 'chat', 'entities': {}, 'confidence': 0.6}
    
    async def _dispatch_tasks(self, intent: Dict, user_input: str, current_state: Any) -> Dict[str, Any]:
        """分发任务给专业智能体"""
        intent_type = intent.get('type', 'chat')
        state_updates = {}
        agent_results = {}
        
        if intent_type == 'greet':
            return {
                'state_updates': {'current_step': 'initial'},
                'agent_results': {'greeting': True}
            }
        
        elif intent_type == 'provide_info':
            # 调用用户画像分析师
            from .profile_agent import ProfileAgent
            profile_agent = ProfileAgent(self.api_key, self.tool_gateway, self.mock_mode)
            profile_result = await profile_agent.process(user_input, [], current_state)
            agent_results['profile'] = profile_result
            
            if profile_result.get('user_profile'):
                state_updates['user_profile'] = profile_result['user_profile']
                state_updates['current_step'] = 'profile_collected'
        
        elif intent_type == 'request_recommendation':
            # 检查是否有用户信息
            if not current_state or not current_state.user_profile:
                return {
                    'state_updates': {},
                    'agent_results': {'need_info': True},
                    'message_hint': '需要先了解您的旅行偏好'
                }
            
            # 调用目的地推荐专家
            from .destination_agent import DestinationAgent
            dest_agent = DestinationAgent(self.api_key, self.tool_gateway, self.mock_mode)
            dest_result = await dest_agent.process(user_input, [], current_state)
            agent_results['destination'] = dest_result
            
            if dest_result.get('destinations'):
                state_updates['recommended_destinations'] = dest_result['destinations']
                state_updates['current_step'] = 'recommendation_ready'
        
        elif intent_type == 'modify_plan':
            # 根据修改内容调用相应智能体
            agent_results['modification'] = {'handled': True}
            state_updates['current_step'] = 'modification_applied'
        
        elif intent_type == 'confirm_plan':
            state_updates['is_confirmed'] = True
            state_updates['current_step'] = 'confirmed'
        
        return {
            'state_updates': state_updates,
            'agent_results': agent_results
        }
    
    def _generate_response(self, result: Dict, intent: Dict) -> str:
        """生成响应消息"""
        intent_type = intent.get('type', 'chat')
        
        if intent_type == 'greet':
            return """您好！我是您的智能旅行规划助手 🌍

我可以帮您：
📍 推荐个性化旅游目的地
✈️ 规划交通方案
📅 生成详细行程安排
💰 管理旅行预算
🌤️ 提供天气预报

请告诉我您的旅行想法，比如：
"我想去一个有山有水的地方放松一下，大概 5 天时间，预算 5000 元左右"
"""
        
        elif intent_type == 'provide_info':
            agent_results = result.get('agent_results', {})
            if agent_results.get('profile'):
                return """✅ 已记录您的旅行偏好！

正在为您分析最佳目的地...
请稍候片刻...
"""
            return "好的，我了解了您的需求。还有什么其他偏好吗？"
        
        elif intent_type == 'request_recommendation':
            if result.get('agent_results', {}).get('need_info'):
                return """在为您推荐目的地之前，我需要先了解一些信息：

1. 您希望去哪里类型的地方？（海边/山区/城市/乡村）
2. 计划出行几天？
3. 预算大概是多少？
4. 从哪个城市出发？

请告诉我这些信息，我会为您定制推荐方案！
"""
            return """🎯 根据您的偏好，我为您推荐以下目的地：

【桂林山水休闲游】
📍 特色：漓江风光、喀斯特地貌、民族风情
💰 人均花费：约 4500 元
⏱️ 建议天数：5 天
🌟 推荐理由：完美匹配您"有山有水"的需求，正值最佳旅游季节

【杭州西湖文化游】
📍 特色：西湖美景、历史文化、美食体验
💰 人均花费：约 4000 元
⏱️ 建议天数：4-5 天
🌟 推荐理由：人文与自然完美结合，交通便利

您更倾向于哪个目的地？或者需要我详细介绍某个地方？
"""
        
        elif intent_type == 'modify_plan':
            return """✅ 已收到您的修改意见！

正在重新优化行程...
稍后将为您提供更新后的方案。
"""
        
        elif intent_type == 'confirm_plan':
            return """🎉 太好了！您的旅行计划已确认！

接下来我将为您：
1. 生成详细的每日行程
2. 计算精确的预算明细
3. 查询旅行期间的天气预报

请稍候...
"""
        
        return "明白了，还有什么我可以帮您的吗？"
