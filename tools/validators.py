"""参数校验器 - 增强输入验证安全性"""
import re
from typing import Dict, Any, List, Optional


# 危险字符模式，用于检测 SQL 注入、XSS 等攻击
DANGEROUS_PATTERNS = [
    r'(<script|</script|javascript:|on\w+\s*=)',  # XSS 相关
    r"(--|\b(union|select|insert|delete|drop|update|exec)\b)",  # SQL 注入相关
    r'(\.\./|\.\.\\)',  # 路径遍历
]

def validate_params(params: Dict[str, Any], required: List[str]) -> tuple[bool, str]:
    """
    校验必需参数
    返回 (是否通过，错误信息)
    """
    missing = [p for p in required if p not in params or params[p] is None]
    if missing:
        return False, f"缺少必需参数：{', '.join(missing)}"
    return True, ""


def check_dangerous_content(text: str) -> bool:
    """检查文本是否包含危险内容"""
    if not text:
        return False
    
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def validate_search_query(query: str) -> tuple[bool, str]:
    """校验搜索查询"""
    if not query or len(query.strip()) < 2:
        return False, "搜索关键词太短"
    if len(query) > 200:
        return False, "搜索关键词太长"
    
    # 检查危险字符
    if check_dangerous_content(query):
        return False, "搜索关键词包含非法字符"
    
    return True, ""


def validate_location(location: str) -> tuple[bool, str]:
    """校验地点名称"""
    if not location or len(location.strip()) < 2:
        return False, "地点名称无效"
    
    # 检查危险字符
    if check_dangerous_content(location):
        return False, "地点名称包含非法字符"
    
    return True, ""


def validate_date(date_str: str) -> tuple[bool, str]:
    """校验日期格式 (YYYY-MM-DD)"""
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False, "日期格式应为 YYYY-MM-DD"
    return True, ""
