"""
旅行计划助手 - 多智能体系统主程序
基于 Qwen 大模型的智能旅行规划系统
"""

import asyncio
import os
import json
from datetime import datetime

# 导入状态管理模块
from state.models import TravelPlanState, UserProfile, Destination, TransportOption, ItineraryDay, BudgetBreakdown, WeatherForecast
from state.manager import StateManager

# 导入智能体模块
from agents.base_agent import BaseAgent
from agents.orchestrator import OrchestratorAgent
from agents.profile_agent import ProfileAgent
from agents.destination_agent import DestinationAgent
from agents.transport_agent import TransportAgent
from agents.itinerary_agent import ItineraryAgent
from agents.budget_agent import BudgetAgent
from agents.weather_agent import WeatherAgent

# 导入工具网关
from tools.gateway import ToolGateway


class TravelAssistant:
    """旅行计划助手主类"""
    
    def __init__(self, api_key: str = None):
        """初始化旅行助手"""
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        
        if not self.api_key:
            print("⚠️  警告：未设置 DASHSCOPE_API_KEY，将使用模拟模式运行")
            self.mock_mode = True
        else:
            self.mock_mode = False
        
        # 初始化状态管理器
        self.state_manager = StateManager()
        
        # 初始化工具网关
        self.tool_gateway = ToolGateway(mock_mode=self.mock_mode)
        
        # 初始化所有智能体
        self.agents = {
            'orchestrator': OrchestratorAgent(self.api_key, self.tool_gateway, self.mock_mode),
            'profile': ProfileAgent(self.api_key, self.tool_gateway, self.mock_mode),
            'destination': DestinationAgent(self.api_key, self.tool_gateway, self.mock_mode),
            'transport': TransportAgent(self.api_key, self.tool_gateway, self.mock_mode),
            'itinerary': ItineraryAgent(self.api_key, self.tool_gateway, self.mock_mode),
            'budget': BudgetAgent(self.api_key, self.tool_gateway, self.mock_mode),
            'weather': WeatherAgent(self.api_key, self.tool_gateway, self.mock_mode),
        }
        
        # 对话历史
        self.conversation_history = []
        
    async def chat(self, user_input: str) -> str:
        """处理用户输入并返回响应"""
        # 添加用户输入到历史
        self.conversation_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        })
        
        # 限制历史记录长度（滑动窗口）
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        # 通过协调者处理请求
        orchestrator = self.agents['orchestrator']
        response = await orchestrator.process(
            user_input=user_input,
            conversation_history=self.conversation_history,
            current_state=self.state_manager.get_state()
        )
        
        # 更新状态
        if response.get('state_updated'):
            self.state_manager.update_state(response['state'])
        
        # 添加助手响应到历史
        self.conversation_history.append({
            'role': 'assistant',
            'content': response['message'],
            'timestamp': datetime.now().isoformat()
        })
        
        return response['message']
    
    def run_cli(self):
        """运行命令行交互界面"""
        print("=" * 60)
        print("🌍 旅行计划助手 (多智能体版)")
        print("基于 Qwen 大模型的智能旅行规划系统")
        print("=" * 60)
        print()
        
        if self.mock_mode:
            print("⚠️  当前为模拟模式，所有回复均为示例数据")
            print("   设置 DASHSCOPE_API_KEY 环境变量以启用真实 AI 功能")
            print()
        
        print("💡 提示：")
        print("  - 描述您的旅行需求（如：我想去有山有水的地方，5 天，预算 5000 元）")
        print("  - 对推荐计划提出修改意见（如：减少 1 天、改乘高铁）")
        print("  - 输入 '退出' 或 'quit' 结束程序")
        print()
        
        while True:
            try:
                user_input = input("👤 您：").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['退出', 'quit', 'exit', 'q']:
                    print("\n👋 感谢您的使用，祝您旅途愉快！")
                    break
                
                # 异步处理用户输入
                response = asyncio.run(self.chat(user_input))
                print(f"\n🤖 旅行助手：{response}\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 程序中断，再见！")
                break
            except Exception as e:
                print(f"\n❌ 发生错误：{str(e)}")
                print("请重试或检查配置\n")


def main():
    """主函数"""
    assistant = TravelAssistant()
    assistant.run_cli()


if __name__ == "__main__":
    main()
