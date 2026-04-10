"""
配置文件 - 存储 API 密钥和系统配置
⚠️ 请勿将此文件提交到版本控制系统
"""
import os

# Qwen DashScope API Key (必需)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "your_qwen_api_key_here")

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

# 网络检测
NETWORK_CHECK_URL = "https://www.baidu.com"
NETWORK_CHECK_TIMEOUT = 5
