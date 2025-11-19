"""
周报管理模块 - 应用配置
"""
from django.apps import AppConfig


class WeeklyReportConfig(AppConfig):
    """周报管理应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'weekly_report'
    verbose_name = '周报管理'
