"""
联网服务模块
提供搜索、天气、维基百科等真实 API 调用
"""
import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from config import (
    SERPER_API_KEY, WEATHER_API_KEY, 
    REQUEST_TIMEOUT, SIMULATION_MODE
)


class WebServices:
    """联网服务网关"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TravelAssistant/3.1'
        })
    
    def check_network(self) -> bool:
        """检查网络连接"""
        try:
            response = requests.get(
                "https://www.baidu.com",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        联网搜索 (使用 Serper API 或模拟数据)
        """
        if SIMULATION_MODE or not SERPER_API_KEY:
            return self._mock_search(query, num_results)
        
        try:
            response = self.session.post(
                "https://google.serper.dev/search",
                headers={
                    'X-API-KEY': SERPER_API_KEY,
                    'Content-Type': 'application/json'
                },
                json={'q': query, 'num': num_results},
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get('organic', [])[:num_results]:
                    results.append({
                        'title': item.get('title', ''),
                        'link': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'source': 'serper'
                    })
                return results
        except Exception as e:
            print(f"搜索失败：{e}")
        
        return self._mock_search(query, num_results)
    
    def get_weather(self, city: str, days: int = 5) -> List[Dict[str, Any]]:
        """
        获取天气预报 (使用真实 API 或模拟数据)
        """
        if SIMULATION_MODE or not WEATHER_API_KEY:
            return self._mock_weather(city, days)
        
        try:
            # 这里以 OpenWeatherMap 为例
            response = self.session.get(
                f"http://api.openweathermap.org/data/2.5/forecast",
                params={
                    'q': city,
                    'appid': WEATHER_API_KEY,
                    'units': 'metric',
                    'lang': 'zh_cn'
                },
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                # 处理返回数据...
                return self._parse_weather_data(data, days)
        except Exception as e:
            print(f"天气查询失败：{e}")
        
        return self._mock_weather(city, days)
    
    def get_wikipedia_info(self, topic: str) -> Dict[str, Any]:
        """
        获取维基百科信息
        """
        try:
            response = self.session.get(
                f"https://zh.wikipedia.org/api/rest_v1/page/summary/{topic}",
                params={'redirect': 1},
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'title': data.get('title', ''),
                    'description': data.get('description', ''),
                    'extract': data.get('extract', ''),
                    'thumbnail': data.get('thumbnail', {}).get('source', ''),
                    'source': 'wikipedia'
                }
        except Exception as e:
            print(f"维基百科查询失败：{e}")
        
        return self._mock_wikipedia(topic)
    
    def _mock_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """模拟搜索结果"""
        return [
            {
                'title': f'{query} - 旅游攻略',
                'link': f'https://example.com/{query}',
                'snippet': f'关于{query}的详细旅游攻略，包含景点推荐、美食介绍...',
                'source': 'mock'
            },
            {
                'title': f'{query} 最佳旅行时间',
                'link': f'https://example.com/{query}/best-time',
                'snippet': f'探索{query}的最佳季节和天气情况...',
                'source': 'mock'
            }
        ][:num_results]
    
    def _mock_weather(self, city: str, days: int) -> List[Dict[str, Any]]:
        """模拟天气数据"""
        import random
        conditions = ['晴', '多云', '小雨', '阴', '大雨']
        forecast = []
        
        for i in range(days):
            date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            forecast.append({
                'date': date,
                'temperature_high': random.randint(20, 35),
                'temperature_low': random.randint(15, 25),
                'condition': random.choice(conditions),
                'precipitation': random.randint(0, 80),
                'wind': f'{random.randint(1, 5)}级',
                'advice': '适宜出行' if random.random() > 0.3 else '建议携带雨具',
                'warning': None,
                'source': 'mock'
            })
        
        return forecast
    
    def _mock_wikipedia(self, topic: str) -> Dict[str, Any]:
        """模拟维基百科信息"""
        return {
            'title': topic,
            'description': f'关于{topic}的详细介绍',
            'extract': f'{topic}是一个著名的旅游目的地，拥有丰富的历史文化和自然景观...',
            'thumbnail': '',
            'source': 'mock'
        }
    
    def _parse_weather_data(self, data: Dict, days: int) -> List[Dict[str, Any]]:
        """解析天气 API 数据 (简化版)"""
        # 实际实现需要解析 OpenWeatherMap 的返回格式
        return self._mock_weather("unknown", days)
