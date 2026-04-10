"""模拟服务 - 用于演示和测试"""
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List


class MockWeatherService:
    """模拟天气服务"""
    
    def __init__(self):
        self.conditions = ['晴', '多云', '阴', '小雨', '中雨']
    
    def get_forecast(self, location: str, days: int = 5) -> List[Dict[str, Any]]:
        """获取天气预报"""
        forecast = []
        base_date = datetime.now() + timedelta(days=7)
        
        for i in range(days):
            date = base_date + timedelta(days=i)
            condition = random.choice(self.conditions)
            temp_high = random.randint(20, 35)
            
            forecast.append({
                'date': date.strftime('%Y-%m-%d'),
                'condition': condition,
                'temp_high': temp_high,
                'temp_low': temp_high - random.randint(5, 12),
                'location': location
            })
        
        return forecast


class MockTransportService:
    """模拟交通服务"""
    
    def __init__(self):
        self.transport_types = [
            {'type': '飞机', 'speed': '快', 'comfort': 4},
            {'type': '高铁', 'speed': '快', 'comfort': 5},
            {'type': '普通火车', 'speed': '慢', 'comfort': 3},
            {'type': '大巴', 'speed': '慢', 'comfort': 2}
        ]
    
    def search(self, from_loc: str, to_loc: str, date: str = None) -> List[Dict[str, Any]]:
        """搜索交通方案"""
        results = []
        
        for transport in self.transport_types:
            if transport['type'] == '飞机':
                duration = random.uniform(1.5, 4)
                price = random.randint(800, 2000)
            elif transport['type'] == '高铁':
                duration = random.uniform(3, 8)
                price = random.randint(300, 800)
            else:
                duration = random.uniform(6, 15)
                price = random.randint(100, 400)
            
            results.append({
                'type': transport['type'],
                'from': from_loc,
                'to': to_loc,
                'duration': round(duration, 1),
                'price': price,
                'comfort_level': transport['comfort']
            })
        
        return results
