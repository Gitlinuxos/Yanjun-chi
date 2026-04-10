#!/usr/bin/env python3
"""旅行计划助手单元测试"""

from travel_assistant import (
    UserProfile, DestinationRecommender, TransportRecommender,
    WeatherService, BudgetManager, ItineraryGenerator, DESTINATIONS_DB
)
from datetime import datetime

def test_user_profile():
    """测试用户信息类"""
    print("\n=== 测试 UserProfile ===")
    user = UserProfile()
    user.name = "测试用户"
    user.age = 30
    user.preferences = ["自然", "人文"]
    user.available_days = 5
    user.budget = 8000.0
    user.travelers = 2
    user.transport_preference = "舒适"
    
    data = user.to_dict()
    assert data["name"] == "测试用户"
    assert data["available_days"] == 5
    print("✓ UserProfile 测试通过")

def test_destination_recommender():
    """测试目的地推荐引擎"""
    print("\n=== 测试 DestinationRecommender ===")
    user = UserProfile()
    user.preferences = ["自然", "休闲"]
    user.available_days = 5
    user.budget = 10000.0
    user.travelers = 2
    
    recommender = DestinationRecommender(user)
    recommendations = recommender.recommend(top_n=3)
    
    assert len(recommendations) == 3
    assert "score" in recommendations[0]
    assert "match_reason" in recommendations[0]
    print(f"✓ 推荐了 {len(recommendations)} 个目的地")
    print(f"  第一名：{recommendations[0]['name']} (分数：{recommendations[0]['score']:.1f})")

def test_transport_recommender():
    """测试交通工具推荐"""
    print("\n=== 测试 TransportRecommender ===")
    user = UserProfile()
    user.transport_preference = "速度"
    
    recommender = TransportRecommender(user)
    transports = recommender.recommend_transport(1500)  # 1500公里
    
    assert len(transports) > 0
    print(f"✓ 推荐了 {len(transports)} 种交通方式")
    for t in transports[:2]:
        print(f"  - {t['name']}: ¥{t['estimated_cost']:.0f}, {t['estimated_time']}小时")

def test_weather_service():
    """测试天气服务"""
    print("\n=== 测试 WeatherService ===")
    service = WeatherService()
    start_date = datetime.now()
    forecast = service.get_forecast(start_date, 5)
    
    assert len(forecast) == 5
    assert "weather" in forecast[0]
    assert "temp_high" in forecast[0]
    assert "advice" in forecast[0]
    print(f"✓ 生成了 {len(forecast)} 天天气预报")
    print(f"  示例：{forecast[0]['date']} {forecast[0]['weather']} {forecast[0]['temp_low']}~{forecast[0]['temp_high']}°C")

def test_budget_manager():
    """测试预算管理"""
    print("\n=== 测试 BudgetManager ===")
    manager = BudgetManager(10000.0, 2)
    breakdown = manager.estimate_breakdown(600, 4, 800)
    status = manager.check_budget()
    
    assert "transport" in breakdown
    assert status["total_budget"] == 10000.0
    print(f"✓ 预算状态：{status['status']}")
    print(f"  使用率：{status['usage_rate']}%")
    print(f"  剩余：¥{status['remaining']:.0f}")

def test_itinerary_generator():
    """测试行程生成器"""
    print("\n=== 测试 ItineraryGenerator ===")
    user = UserProfile()
    user.transport_preference = "舒适"
    
    generator = ItineraryGenerator(user)
    dest_info = DESTINATIONS_DB["hangzhou"]
    plan = generator.generate("hangzhou", dest_info, 3)
    
    assert plan["destination"] == "杭州"
    assert plan["duration_days"] == 3
    assert "transport" in plan
    assert "daily_schedule" in plan
    assert len(plan["daily_schedule"]) == 3
    
    print(f"✓ 生成了 {plan['destination']} {plan['duration_days']}天行程")
    if plan["transport"]:
        print(f"  推荐交通：{plan['transport']['name']}")
    print(f"  行程亮点：{', '.join(plan['highlights'])}")

def test_plan_modification():
    """测试计划修改功能"""
    print("\n=== 测试计划修改 ===")
    user = UserProfile()
    user.transport_preference = "舒适"
    
    generator = ItineraryGenerator(user)
    dest_info = DESTINATIONS_DB["beijing"]
    plan = generator.generate("beijing", dest_info, 4)
    
    original_days = plan["duration_days"]
    modified_plan = generator.modify_plan(plan, "减少 1 天")
    
    assert modified_plan["duration_days"] == original_days - 1
    assert len(modified_plan["daily_schedule"]) == original_days - 1
    print(f"✓ 计划从 {original_days}天 修改为 {modified_plan['duration_days']}天")

def run_all_tests():
    """运行所有测试"""
    print("="*50)
    print("旅行计划助手 - 功能模块测试")
    print("="*50)
    
    test_user_profile()
    test_destination_recommender()
    test_transport_recommender()
    test_weather_service()
    test_budget_manager()
    test_itinerary_generator()
    test_plan_modification()
    
    print("\n" + "="*50)
    print("✅ 所有测试通过！")
    print("="*50)

if __name__ == "__main__":
    run_all_tests()
