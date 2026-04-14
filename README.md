# 旅行计划助手 (Travel Assistant) - V3.2

## 项目概述
基于 Qwen 大语言模型的多智能体协作旅行规划系统。本版本 (V3.2) 在 V3.1 基础上引入了**临时区 (Staging Area)**和**两阶段提交 (2PC)**机制，彻底解决了多智能体并发修改导致的状态冲突问题，确保数据一致性和系统稳定性。

**⚠️ 注意**: 本系统必须联网使用。无网络连接时，系统将拒绝提供服务以确保数据准确性。

## 📜 版本迭代历史

| 版本 | 核心特性 | 架构模式 | 状态 |
| :--- | :--- | :--- | :--- |
| **V1.0** | 规则驱动，内置静态数据库 | 单体模块化 | ❌ 已废弃 |
| **V2.0** | 引入 Qwen 大模型，多智能体协作 | 共享黑板 + 状态机 | ⚠️ 基础版 |
| **V3.0** | 全面联网，实时数据检索 (天气/人文/票务) | 联网中间件 + RAG | ⚠️ 高延迟风险 |
| **V3.1** | 精准 System Prompt + Few-Shot + KV-Cache 检索 | 智能缓存 + 鲁棒协作 | ⚠️ 并发风险 |
| **V3.2** | **临时区 (Staging Area) + 两阶段提交 (2PC) + 乐观锁** | **事务性状态管理** | ✅ **当前版本** |

### V3.2 核心升级点
1. **临时区机制**: 所有 Agent 的修改先提交到临时区，不直接写入主状态。
2. **两阶段提交**: Phase 1 收集补丁并检测冲突，Phase 2 原子性提交。
3. **乐观锁控制**: 基于状态哈希的版本控制，防止脏写。
4. **冲突检测**: 自动识别 write-write 冲突和 version mismatch。
5. **向下兼容**: 保留 V3.1 的所有功能（KV-Cache、Few-Shot、联网检索）。

## ✨ 核心功能模块

### 1. 多智能体协作系统
系统由 7 个专业智能体组成，通过协调者 (Orchestrator) 统一调度：
- **协调者 (Orchestrator)**: 意图识别、任务分发、结果汇总。
- **用户画像分析师 (Profile Agent)**: 从对话中提取偏好，构建用户画像。
- **目的地推荐专家 (Destination Agent)**: 实时检索热门目的地，深度挖掘人文历史。
- **交通规划师 (Transport Agent)**: 实时查询票价与时刻，多模态方案对比。
- **行程编排师 (Itinerary Agent)**: 生成详细日程，逻辑校验与动态调整。
- **预算精算师 (Budget Agent)**: 实时费用估算，预算监控与优化建议。
- **气象顾问 (Weather Agent)**: 实时天气预报，灾害预警与出行建议。

### 2. 智能缓存机制 (KV-Cache)
- **语义检索**: 将用户查询向量化，相似度 > 0.92 即命中缓存。
- **分级 TTL**: 天气 (30min)、交通 (10min)、人文 (7d)，确保数据时效性。
- **热点预加载**: 系统启动时预加载热门城市基础信息。

### 3. 联网数据源
- **搜索引擎**: Serper/Bing API (通用信息检索)
- **天气服务**: OpenWeatherMap/QWeather API (实时天气与预警)
- **知识库**: Wikipedia/API (人文历史深度内容)
- **多媒体**: 自动抓取图片/视频链接 (需 API 支持)

### 4. 可靠性保障
- **网络健康检查**: 启动时强制检测，运行时监控。
- **熔断降级**: API 连续失败自动切换至模拟模式并警告。
- **结构化输出**: 强制 JSON Schema 约束，防止解析错误。

## 🚀 快速开始

### 环境准备
```bash
pip install dashscope requests numpy scikit-learn pydantic aiohttp
```

### 配置 API Key
在 `config.py` 中设置必要的 API 密钥：
```python
DASHSCOPE_API_KEY = "your_qwen_api_key"
SERPER_API_KEY = "your_search_api_key"  # 可选，用于搜索
WEATHER_API_KEY = "your_weather_api_key" # 可选，用于天气
```

### 运行程序
```bash
python travel_assistant.py
```

### 交互示例
```text
🤖 旅行助手：您好！我是您的智能旅行规划助手。请告诉我您想去哪里，或者您喜欢的旅行类型？
👤 用户：我想去一个有历史感的地方，大概 5 天，预算 5000 元。
🤖 旅行助手：[分析意图] -> [检索缓存] -> [调用联网搜索] -> [生成推荐]
...
```

## 📂 项目结构
```
/workspace/
├── README.md                 # 项目文档
├── config.py                 # 配置文件 (API Keys)
├── travel_assistant.py       # 主入口与 CLI 交互
├── state/
│   ├── __init__.py
│   ├── models.py             # Pydantic 数据模型
│   └── manager.py            # 状态管理与 KV-Cache
├── agents/
│   ├── __init__.py
│   ├── base_agent.py         # Agent 基类 (Prompt/Few-Shot)
│   ├── orchestrator.py       # 协调者
│   ├── profile_agent.py      # 用户画像
│   ├── destination_agent.py  # 目的地推荐
│   ├── transport_agent.py    # 交通规划
│   ├── itinerary_agent.py    # 行程编排
│   ├── budget_agent.py       # 预算管理
│   └── weather_agent.py      # 气象服务
└── tools/
    ├── __init__.py
    ├── gateway.py            # 工具网关 (缓存/重试/降级)
    ├── validators.py         # 参数校验
    └── web_services.py       # 联网服务 (搜索/天气/Wiki)
```

## 🔒 安全性与隐私
- **数据本地化**: 用户画像仅保存在内存中，会话结束即销毁。
- **API 安全**: 敏感 Key 存储在 `config.py` 中，不提交至版本控制。
- **内容过滤**: 所有联网返回内容经过清洗，过滤不安全信息。

## 🛠 开发指南
- **添加新 Agent**: 继承 `BaseAgent`，实现 `process()` 方法，注册到 `Orchestrator`。
- **更新 Prompt**: 修改 `agents/base_agent.py` 中的 `SYSTEM_PROMPTS` 字典。
- **扩展工具**: 在 `tools/web_services.py` 中添加新 API 封装，并在 `ToolGateway` 注册。

## 📝 License
MIT License
