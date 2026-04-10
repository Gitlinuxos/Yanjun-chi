"""Agent 基类"""
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, api_key: str, tool_gateway, mock_mode: bool = False):
        """初始化智能体
        
        Args:
            api_key: Dashscope API 密钥
            tool_gateway: 工具网关实例
            mock_mode: 是否使用模拟模式
        """
        self.api_key = api_key
        self.tool_gateway = tool_gateway
        self.mock_mode = mock_mode
        self.name = self.__class__.__name__
        self.max_retries = 3
    
    @abstractmethod
    async def process(self, user_input: str, conversation_history: List[Dict], 
                     current_state: Any) -> Dict[str, Any]:
        """处理请求的抽象方法
        
        Args:
            user_input: 用户输入
            conversation_history: 对话历史
            current_state: 当前状态
            
        Returns:
            Dict: 处理结果
        """
        pass
    
    async def call_llm(self, system_prompt: str, user_prompt: str, 
                       response_format: Optional[Dict] = None) -> Dict[str, Any]:
        """调用大语言模型
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            response_format: 期望的响应格式
            
        Returns:
            Dict: LLM 响应
        """
        if self.mock_mode:
            return await self._mock_llm_call(system_prompt, user_prompt)
        
        # 真实 API 调用 (使用 dashscope)
        for attempt in range(self.max_retries):
            try:
                result = await self._real_llm_call(system_prompt, user_prompt, response_format)
                return result
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 指数退避
        
        return {}
    
    async def _real_llm_call(self, system_prompt: str, user_prompt: str, 
                             response_format: Optional[Dict] = None) -> Dict[str, Any]:
        """真实的 LLM 调用实现"""
        try:
            import dashscope
            from dashscope import Generation
            
            # 构建消息
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
            
            # 调用 Qwen 模型
            response = Generation.call(
                model='qwen-max',
                messages=messages,
                result_format='message',
                api_key=self.api_key
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                # 尝试解析 JSON
                try:
                    return json.loads(content)
                except:
                    return {'content': content}
            else:
                raise Exception(f"API 调用失败：{response.code}")
                
        except ImportError:
            # dashscope 未安装，降级到模拟模式
            return await self._mock_llm_call(system_prompt, user_prompt)
    
    async def _mock_llm_call(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """模拟 LLM 调用（用于演示）"""
        await asyncio.sleep(0.5)  # 模拟延迟
        return {
            'mock': True,
            'content': '模拟响应'
        }
    
    def log(self, message: str):
        """日志输出"""
        print(f"[{self.name}] {message}")
