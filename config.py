"""
配置文件 - 存储 API 密钥和系统配置
⚠️ 请勿将此文件提交到版本控制系统
"""
import os

# Qwen DashScope API Key (必需)
# 强制从环境变量获取，不提供默认值
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if DASHSCOPE_API_KEY is None:
    import warnings
    warnings.warn(
        "DASHSCOPE_API_KEY 未设置！请通过环境变量设置有效的 API 密钥。",
        UserWarning,
        stacklevel=2
    )
    DASHSCOPE_API_KEY = ""  # 空字符串表示未配置

# 搜索 API Key (可选，用于联网搜索)
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# 天气 API Key (可选，用于实时天气)
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")

# 系统配置
SIMULATION_MODE = False  # 是否启用模拟模式 (无 API Key 时自动启用)
CACHE_TTL_WEATHER = 1800  # 天气缓存 TTL (秒) = 30 分钟
CACHE_TTL_TRANSPORT = 600  # 交通缓存 TTL (秒) = 10 分钟
CACHE_TTL_GENERAL = 604800  # 通用信息缓存 TTL (秒) = 7 天
CACHE_SIMILARITY_THRESHOLD = 0.92  # 向量相似度阈值
MAX_RETRY_ATTEMPTS = 3  # 最大重试次数
REQUEST_TIMEOUT = 30  # 请求超时时间 (秒)

# 模型配置
DEFAULT_MODEL = "qwen-max"  # 默认使用 Qwen-Max
FAST_MODEL = "qwen-turbo"  # 快速任务使用 Qwen-Turbo

# RAG & Memory 配置
RAG_ENABLED = True
RAG_TOP_K = 5                # 检索返回的最大条目数
RAG_SIMILARITY_THRESHOLD = 0.75  # 最低相似度阈值
RAG_MEMORY_CATEGORIES = ["user_profile", "preferences", "business_fact", "reflection"]  # 需要检索的记忆类别
RAG_MAX_CONTEXT_ITEMS = 5    # System Prompt 中最多注入几条记忆

# 网络检测
NETWORK_CHECK_URL = "https://www.baidu.com"
NETWORK_CHECK_TIMEOUT = 5
