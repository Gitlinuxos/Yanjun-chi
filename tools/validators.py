"""参数校验器"""
from typing import Dict, Any, List, Optional


def validate_params(params: Dict[str, Any], required: List[str]) -> tuple[bool, str]:
    """
    校验必需参数
    返回 (是否通过，错误信息)
    """
    missing = [p for p in required if p not in params or params[p] is None]
    if missing:
        return False, f"缺少必需参数：{', '.join(missing)}"
    return True, ""


def validate_search_query(query: str) -> tuple[bool, str]:
    """校验搜索查询"""
    if not query or len(query.strip()) < 2:
        return False, "搜索关键词太短"
    if len(query) > 200:
        return False, "搜索关键词太长"
    return True, ""


def validate_location(location: str) -> tuple[bool, str]:
    """校验地点名称"""
    if not location or len(location.strip()) < 2:
        return False, "地点名称无效"
    return True, ""


def validate_date(date_str: str) -> tuple[bool, str]:
    """校验日期格式 (YYYY-MM-DD)"""
    import re
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False, "日期格式应为 YYYY-MM-DD"
    return True, ""
