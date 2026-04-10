"""
Agent 基类
提供统一的 LLM 调用、Prompt 模板、Few-Shot 示例管理
"""
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from config import DASHSCOPE_API_KEY, DEFAULT_MODEL, SIMULATION_MODE


# Few-Shot 示例库
FEW_SHOT_EXAMPLES = {
    "profile": [
        {
            "input": "我想去北京玩 5 天，预算 5000 元，喜欢历史文化",
            "output": '{"name": "游客", "days": 5, "budget": 5000, "preferred_styles": ["HISTORY"], "interests": ["历史文化"]}'
        },
        {
            "input": "我们一家三口想去三亚度假，孩子 5 岁，希望轻松一点",
            "output": '{"travelers": 3, "preferred_styles": ["RELAX"], "special_needs": ["带小孩", "轻松行程"]}'
        }
    ],
    "destination": [
        {
            "input": "推荐一个适合秋天去的历史文化名城",
            "output": '{"destinations": [{"name": "西安", "reason": "古都文化深厚，秋季气候宜人"}]}'
        }
    ],
    "itinerary": [
        {
            "input": "生成北京 3 日游行程",
            "output": '{"itinerary": [{"day": 1, "morning": "天安门广场", "afternoon": "故宫博物院"}]}'
        }
    ]
}


class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(self, state_manager, tool_gateway, web_services):
        self.state_manager = state_manager
        self.tool_gateway = tool_gateway
        self.web_services = web_services
        self.model = DEFAULT_MODEL
    
    @property
    @abstractmethod
    def role(self) -> str:
        """Agent 角色名称"""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """系统提示词"""
        pass
    
    def get_few_shot_examples(self, category: str) -> List[Dict[str, str]]:
        """获取 Few-Shot 示例"""
        return FEW_SHOT_EXAMPLES.get(category, [])
    
    def build_prompt(
        self, 
        user_input: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建完整 Prompt"""
        examples = self.get_few_shot_examples(self.role.lower())
        
        prompt_parts = [
            f"# Role: {self.role}",
            "",
            "## System Instructions",
            self.system_prompt,
            "",
            "## Examples (Few-Shot)"
        ]
        
        for ex in examples[:3]:  # 最多 3 个示例
            prompt_parts.append(f"Input: {ex['input']}")
            prompt_parts.append(f"Output: {ex['output']}")
        
        prompt_parts.append("")
        prompt_parts.append("## Current Task")
        
        if context:
            prompt_parts.append(f"Context: {json.dumps(context, ensure_ascii=False)}")
        
        prompt_parts.append(f"User Input: {user_input}")
        prompt_parts.append("")
        prompt_parts.append("Please respond with valid JSON format.")
        
        return "\n".join(prompt_parts)
    
    def call_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """调用 LLM (支持模拟模式)"""
        if SIMULATION_MODE or not DASHSCOPE_API_KEY:
            return self._simulate_response(prompt)
        
        try:
            import dashscope
            dashscope.api_key = DASHSCOPE_API_KEY
            
            response = dashscope.Generation.call(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                result_format='message'
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                return self._parse_json_response(content)
        except Exception as e:
            print(f"LLM 调用失败 [{self.role}]: {e}")
        
        return self._simulate_response(prompt)
    
    def _parse_json_response(self, content: str) -> Optional[Dict[str, Any]]:
        """解析 JSON 响应"""
        try:
            # 尝试直接解析
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试提取 JSON 片段
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None
    
    def _simulate_response(self, prompt: str) -> Optional[Dict[str, Any]]:
        """模拟 LLM 响应"""
        # 根据角色返回不同的模拟数据
        if "profile" in self.role.lower():
            return {"name": "游客", "days": 5, "budget": 5000}
        elif "destination" in self.role.lower():
            return {
                "destinations": [
                    {"name": "北京", "description": "中国首都，历史文化名城"}
                ]
            }
        return {"status": "simulated"}
    
    @abstractmethod
    async def process(self, user_input: str, **kwargs) -> Optional[Dict[str, Any]]:
        """处理用户输入 (异步)"""
        pass
