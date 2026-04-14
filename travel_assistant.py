#!/usr/bin/env python3
"""
旅行计划助手 V3.3 - 主入口
基于 Qwen 大模型的多智能体协作系统 (支持 RAG 增强生成)
"""
import asyncio
import sys
from datetime import datetime

# 导入配置和模块
from config import DASHSCOPE_API_KEY, SIMULATION_MODE
from state.manager import StateManager
from tools.gateway import ToolGateway
from tools.web_services import WebServices
from agents.rag_engine import RAGEngine
from agents import (
    OrchestratorAgent, ProfileAgent, DestinationAgent,
    TransportAgent, ItineraryAgent, BudgetAgent, WeatherAgent
)


class TravelAssistant:
    """旅行计划助手主类"""
    
    def __init__(self):
        # 初始化状态管理器
        self.state_manager = StateManager()
        
        # 初始化联网服务
        self.web_services = WebServices()
        
        # 检查网络连接
        if not self.web_services.check_network():
            print("⚠️  警告：网络连接失败！系统将进入模拟模式。")
            print("   请检查网络连接后重新启动以获得完整功能。")
        
        # 初始化工具网关
        self.tool_gateway = ToolGateway(self.state_manager)
        
        # 初始化 RAG 引擎 (长期记忆检索与安全过滤)
        self.rag_engine = RAGEngine(self.state_manager)
        
        # 初始化所有 Agent (注入 RAG 引擎)
        self.agents = {
            "profile_agent": ProfileAgent(
                self.state_manager, self.tool_gateway, self.web_services,
                rag_engine=self.rag_engine
            ),
            "destination_agent": DestinationAgent(
                self.state_manager, self.tool_gateway, self.web_services,
                rag_engine=self.rag_engine
            ),
            "transport_agent": TransportAgent(
                self.state_manager, self.tool_gateway, self.web_services,
                rag_engine=self.rag_engine
            ),
            "itinerary_agent": ItineraryAgent(
                self.state_manager, self.tool_gateway, self.web_services,
                rag_engine=self.rag_engine
            ),
            "budget_agent": BudgetAgent(
                self.state_manager, self.tool_gateway, self.web_services,
                rag_engine=self.rag_engine
            ),
            "weather_agent": WeatherAgent(
                self.state_manager, self.tool_gateway, self.web_services,
                rag_engine=self.rag_engine
            ),
        }
        
        # 初始化协调者 (注入 RAG 引擎)
        self.orchestrator = OrchestratorAgent(
            self.state_manager, 
            self.tool_gateway, 
            self.web_services,
            self.agents,
            rag_engine=self.rag_engine
        )
        
        # 打印欢迎信息
        self._print_welcome()
    
    def _print_welcome(self):
        """打印欢迎信息"""
        print("\n" + "="*60)
        print("🌍  旅行计划助手 V3.1 - 多智能体协作系统")
        print("="*60)
        print(f"📅 当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"🔗 网络状态：{'✅ 已连接' if self.web_services.check_network() else '❌ 未连接'}")
        print(f"🤖 运行模式：{'模拟模式' if SIMULATION_MODE or not DASHSCOPE_API_KEY else '在线模式'}")
        print("-"*60)
        print("💡 提示：告诉我您的旅行想法，我会为您规划完美行程！")
        print("   例如：'我想去一个有历史感的地方，5 天，预算 5000 元'")
        print("="*60 + "\n")
    
    async def chat(self, user_input: str) -> str:
        """处理用户输入并返回响应"""
        # 记录对话
        self.state_manager.state.add_message("user", user_input)
        
        try:
            # 调用协调者处理
            result = await self.orchestrator.process(user_input)
            
            if not result:
                response = "抱歉，我暂时无法处理您的请求。"
            elif result.get("status") == "error":
                response = f"出现错误：{result.get('message', '未知错误')}"
            else:
                # 构建友好回复
                intent = result.get("intent", "chat")
                task_result = result.get("task_result", {})
                
                response = self._format_response(intent, task_result)
            
            # 记录助手回复
            self.state_manager.state.add_message("assistant", response)
            return response
            
        except Exception as e:
            # 避免泄露敏感异常信息，仅记录日志，返回通用错误消息
            import logging
            logging.error(f"处理请求时发生异常：{type(e).__name__}")
            error_msg = "处理请求时出错，请稍后重试或联系管理员。"
            print(f"[ERROR] {error_msg}")
            return error_msg
    
    def _format_response(self, intent: str, task_result: dict) -> str:
        """格式化任务结果为友好文本"""
        
        if intent == "extract_profile":
            if task_result:
                name = task_result.get("name", "游客")
                days = task_result.get("days", "?")
                budget = task_result.get("budget", "?")
                return f"👤 好的，{name}！我了解到您计划旅行{days}天，预算约{budget}元。\n接下来让我为您推荐合适的目的地吧！"
        
        elif intent == "recommend_destination":
            destinations = task_result.get("destinations", [])
            if destinations:
                lines = ["🎯 根据您的偏好，我为您推荐以下目的地：\n"]
                for i, dest in enumerate(destinations[:3], 1):
                    lines.append(f"{i}. 📍 {dest.get('name', '未知')}")
                    lines.append(f"   {dest.get('description', '')}")
                    lines.append(f"   💡 推荐理由：{dest.get('reason', '')}")
                    lines.append("")
                lines.append("您对哪个目的地感兴趣？我可以为您详细规划行程！")
                return "\n".join(lines)
        
        elif intent == "generate_itinerary":
            itinerary = task_result.get("itinerary", [])
            if itinerary:
                lines = ["📅 为您生成的行程安排：\n"]
                for day in itinerary[:3]:
                    lines.append(f"第{day.get('day', '?')}天:")
                    lines.append(f"  🌅 上午：{day.get('morning', '自由活动')}")
                    lines.append(f"  🌞 下午：{day.get('afternoon', '自由活动')}")
                    lines.append(f"  🌙 晚上：{day.get('evening', '休息')}")
                    lines.append("")
                return "\n".join(lines)
        
        elif intent == "check_weather":
            forecast = task_result.get("forecast", [])
            if forecast:
                lines = ["🌤️ 天气预报：\n"]
                for day in forecast[:3]:
                    lines.append(f"{day.get('date', '?')}: {day.get('condition', '?')}")
                    lines.append(f"  温度：{day.get('temperature_low', '?')}~{day.get('temperature_high', '?')}°C")
                    lines.append(f"  💡 {day.get('advice', '')}")
                    lines.append("")
                return "\n".join(lines)
        
        # 默认回复
        return "收到您的需求，我正在为您规划...请稍等。"
    
    async def run_cli(self):
        """运行命令行交互界面（带速率限制）"""
        print("🤖 旅行助手：您好！我是您的智能旅行规划助手。")
        print("   请告诉我您想去哪里，或者您喜欢的旅行类型？\n")
        
        # 速率限制配置
        max_requests_per_minute = 10
        request_timestamps = []
        
        while True:
            try:
                # 获取用户输入
                user_input = input("👤 您：").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["exit", "quit", "退出", "再见"]:
                    print("\n🤖 旅行助手：感谢您的使用，祝您旅途愉快！再见！👋")
                    break
                
                if user_input.lower() in ["help", "帮助", "?"]:
                    self._print_help()
                    continue
                
                # 速率限制检查
                import time
                current_time = time.time()
                # 移除超过 60 秒的请求记录
                request_timestamps = [ts for ts in request_timestamps if current_time - ts < 60]
                
                if len(request_timestamps) >= max_requests_per_minute:
                    print(f"\n⚠️  请求过于频繁，请稍后再试（限制：{max_requests_per_minute} 次/分钟）\n")
                    continue
                
                request_timestamps.append(current_time)
                
                # 处理输入
                print("\n🤖 旅行助手：正在思考中...", end="", flush=True)
                response = await self.chat(user_input)
                print("\r" + " " * 20 + "\r", end="")  # 清除"正在思考中"
                print(f"🤖 旅行助手：{response}\n")
                
            except KeyboardInterrupt:
                print("\n\n🤖 旅行助手：检测到中断，已退出。")
                break
            except EOFError:
                break
    
    def _print_help(self):
        """打印帮助信息"""
        print("\n" + "-"*40)
        print("💡 使用帮助:")
        print("  • 描述您的旅行想法，如：")
        print("    '我想去海边度假，5 天，预算 8000 元'")
        print("    '推荐一个适合秋天的历史文化名城'")
        print("  • 可以询问天气：'查一下北京下周的天气'")
        print("  • 可以修改计划：'把行程改成 4 天'")
        print("  • 输入 '退出' 结束程序")
        print("-"*40 + "\n")


async def main():
    """主函数"""
    assistant = TravelAssistant()
    await assistant.run_cli()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已退出。")
