"""参数校验器"""
from typing import Dict, Any, List, Optional


def validate_tool_params(params: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """验证工具参数是否符合 Schema
    
    Args:
        params: 待验证的参数
        schema: JSON Schema
        
    Returns:
        Dict: {'valid': bool, 'message': str}
    """
    required = schema.get('required', [])
    properties = schema.get('properties', {})
    
    # 检查必填字段
    for field in required:
        if field not in params:
            return {'valid': False, 'message': f'缺少必填字段：{field}'}
    
    # 检查类型
    for field, value in params.items():
        if field in properties:
            prop_schema = properties[field]
            expected_type = prop_schema.get('type')
            
            if not _check_type(value, expected_type):
                return {
                    'valid': False, 
                    'message': f'{field} 类型错误，应为 {expected_type}'
                }
            
            # 检查枚举值
            if 'enum' in prop_schema and value not in prop_schema['enum']:
                return {
                    'valid': False,
                    'message': f'{field} 值不在允许范围内：{prop_schema["enum"]}'
                }
            
            # 检查数值范围
            if expected_type in ['integer', 'number']:
                if 'minimum' in prop_schema and value < prop_schema['minimum']:
                    return {
                        'valid': False,
                        'message': f'{field} 不能小于 {prop_schema["minimum"]}'
                    }
                if 'maximum' in prop_schema and value > prop_schema['maximum']:
                    return {
                        'valid': False,
                        'message': f'{field} 不能大于 {prop_schema["maximum"]}'
                    }
    
    return {'valid': True, 'message': ''}


def _check_type(value: Any, expected_type: str) -> bool:
    """检查值是否符合预期类型"""
    type_mapping = {
        'string': str,
        'integer': int,
        'number': (int, float),
        'boolean': bool,
        'array': list,
        'object': dict
    }
    
    expected_python_type = type_mapping.get(expected_type)
    if expected_python_type is None:
        return True
    
    return isinstance(value, expected_python_type)
