"""工具网关 - 统一管理工具调用"""
import asyncio
from typing import Dict, Any, List, Optional, Callable
from functools import wraps


class ToolGateway:
    """工具网关 - Agent 不直接调用工具，通过网关执行"""
    
    def __init__(self, mock_mode: bool = False):
        """初始化工具网关
        
        Args:
            mock_mode: 是否使用模拟模式
        """
        self.mock_mode = mock_mode
        self.tools: Dict[str, Dict] = {}
        self.max_retries = 3
        self.timeout = 15
        
        # 注册内置工具
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        # 天气查询工具
        self.register_tool(
            name='query_weather',
            description='查询指定日期和地点的天气预报',
            func=self._mock_query_weather if self.mock_mode else None,
            params_schema={
                'type': 'object',
                'properties': {
                    'location': {'type': 'string'},
                    'date': {'type': 'string'},
                    'days': {'type': 'integer'}
                },
                'required': ['location']
            }
        )
        
        # 交通查询工具
        self.register_tool(
            name='query_transport',
            description='查询两地之间的交通方案',
            func=self._mock_query_transport if self.mock_mode else None,
            params_schema={
                'type': 'object',
                'properties': {
                    'from': {'type': 'string'},
                    'to': {'type': 'string'},
                    'date': {'type': 'string'}
                },
                'required': ['from', 'to']
            }
        )
    
    def register_tool(self, name: str, description: str, func: Optional[Callable], 
                     params_schema: Dict[str, Any]):
        """注册工具
        
        Args:
            name: 工具名称
            description: 工具描述
            func: 工具函数
            params_schema: 参数 JSON Schema
        """
        self.tools[name] = {
            'name': name,
            'description': description,
            'func': func,
            'params_schema': params_schema
        }
    
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            Dict: 执行结果
        """
        # 检查工具是否存在
        if tool_name not in self.tools:
            return {
                'success': False,
                'error': f'工具不存在：{tool_name}',
                'data': None
            }
        
        tool = self.tools[tool_name]
        
        # 参数校验
        validation_result = self._validate_params(params, tool['params_schema'])
        if not validation_result['valid']:
            return {
                'success': False,
                'error': f'参数校验失败：{validation_result["message"]}',
                'data': None
            }
        
        # 执行工具（带重试）
        for attempt in range(self.max_retries):
            try:
                result = await asyncio.wait_for(
                    self._execute_tool(tool, params),
                    timeout=self.timeout
                )
                return {
                    'success': True,
                    'error': None,
                    'data': result
                }
            except asyncio.TimeoutError:
                if attempt == self.max_retries - 1:
                    return {
                        'success': False,
                        'error': f'工具调用超时 ({self.timeout}s)',
                        'data': None
                    }
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return {
                        'success': False,
                        'error': str(e),
                        'data': None
                    }
            
            # 指数退避
            await asyncio.sleep(2 ** attempt)
        
        return {
            'success': False,
            'error': '未知错误',
            'data': None
        }
    
    async def _execute_tool(self, tool: Dict, params: Dict) -> Any:
        """执行具体工具"""
        if tool['func'] is None:
            # 没有实际函数，返回模拟数据
            return self._get_mock_data(tool['name'], params)
        
        # 同步函数
        result = tool['func'](**params)
        return result
    
    def _validate_params(self, params: Dict, schema: Dict) -> Dict[str, Any]:
        """验证参数是否符合 Schema"""
        required = schema.get('required', [])
        properties = schema.get('properties', {})
        
        # 检查必填字段
        for field in required:
            if field not in params:
                return {'valid': False, 'message': f'缺少必填字段：{field}'}
        
        # 检查类型
        for field, value in params.items():
            if field in properties:
                expected_type = properties[field].get('type')
                if expected_type == 'string' and not isinstance(value, str):
                    return {'valid': False, 'message': f'{field} 应为字符串类型'}
                elif expected_type == 'integer' and not isinstance(value, int):
                    return {'valid': False, 'message': f'{field} 应为整数类型'}
        
        return {'valid': True, 'message': ''}
    
    def _get_mock_data(self, tool_name: str, params: Dict) -> Dict:
        """获取模拟数据"""
        if tool_name == 'query_weather':
            return {
                'location': params.get('location', '未知'),
                'forecast': [
                    {'date': '2024-01-01', 'condition': '晴', 'temp': '20-28°C'},
                    {'date': '2024-01-02', 'condition': '多云', 'temp': '18-26°C'}
                ]
            }
        elif tool_name == 'query_transport':
            return {
                'from': params.get('from'),
                'to': params.get('to'),
                'options': [
                    {'type': '高铁', 'duration': '6h', 'price': 550},
                    {'type': '飞机', 'duration': '2.5h', 'price': 1200}
                ]
            }
        return {}
    
    def _mock_query_weather(self, location: str, date: str = None, days: int = 3) -> Dict:
        """模拟天气查询"""
        return {
            'location': location,
            'forecast': [{'date': f'Day{i}', 'condition': '晴', 'temp': '25°C'} for i in range(days)]
        }
    
    def _mock_query_transport(self, from_loc: str, to_loc: str, date: str = None) -> Dict:
        """模拟交通查询"""
        return {
            'from': from_loc,
            'to': to_loc,
            'options': [
                {'type': '高铁', 'duration': '6h', 'price': 550},
                {'type': '飞机', 'duration': '2.5h', 'price': 1200}
            ]
        }
