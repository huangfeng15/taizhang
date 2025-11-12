"""
工作周期监控V2路由配置
"""
from django.urls import path
from project import views_monitoring_cycle_v2

urlpatterns = [
    # 工作周期监控主页面
    path('monitoring/cycle/v2/', views_monitoring_cycle_v2.cycle_monitor_v2, name='cycle_monitor_v2'),
    
    # 工作周期监控API接口
    path('monitoring/cycle/v2/api/', views_monitoring_cycle_v2.cycle_monitor_api, name='cycle_monitor_api'),
]