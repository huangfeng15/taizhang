"""
日期处理工具函数
提供日期计算、格式化等辅助功能
"""
from datetime import datetime, timedelta, date
from typing import Optional, Tuple
from django.utils import timezone


def calculate_days_between(start_date: Optional[date], end_date: Optional[date]) -> Optional[int]:
    """
    计算两个日期之间的天数差
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        int: 天数差，如果任一日期为None则返回None
    """
    if not start_date or not end_date:
        return None
    return (end_date - start_date).days


def calculate_days_ago(target_date: Optional[date]) -> Optional[int]:
    """
    计算指定日期距今的天数
    
    Args:
        target_date: 目标日期
        
    Returns:
        int: 距今天数，如果日期为None则返回None
    """
    if not target_date:
        return None
    today = timezone.now().date()
    return (today - target_date).days


def format_date_display(target_date: Optional[date]) -> str:
    """
    格式化日期显示（带距今天数）
    
    Args:
        target_date: 目标日期
        
    Returns:
        str: 格式化的日期字符串，例如 "2025-01-15 (98天前)"
    """
    if not target_date:
        return "未录入"
    
    days_ago = calculate_days_ago(target_date)
    if days_ago is None:
        return target_date.strftime('%Y-%m-%d')
    
    if days_ago == 0:
        return f"{target_date.strftime('%Y-%m-%d')} (今天)"
    elif days_ago == 1:
        return f"{target_date.strftime('%Y-%m-%d')} (昨天)"
    elif days_ago < 0:
        return f"{target_date.strftime('%Y-%m-%d')} ({abs(days_ago)}天后)"
    else:
        return f"{target_date.strftime('%Y-%m-%d')} ({days_ago}天前)"


def get_alert_level_by_days(days: Optional[int], threshold_warning: int = 30, threshold_critical: int = 40) -> str:
    """
    根据天数判断预警级别
    
    Args:
        days: 天数
        threshold_warning: 警告阈值
        threshold_critical: 严重阈值
        
    Returns:
        str: 预警级别 ('normal'/'warning'/'critical')
    """
    if days is None:
        return 'normal'
    
    if days > threshold_critical:
        return 'critical'
    elif days > threshold_warning:
        return 'warning'
    else:
        return 'normal'


def get_year_quarter(target_date: Optional[date] = None) -> Tuple[int, int]:
    """
    获取指定日期所在的年份和季度
    
    Args:
        target_date: 目标日期，默认为当前日期
        
    Returns:
        tuple: (年份, 季度)
    """
    if not target_date:
        target_date = timezone.now().date()
    
    year = target_date.year
    quarter = (target_date.month - 1) // 3 + 1
    
    return year, quarter


def get_quarter_date_range(year: int, quarter: int) -> Tuple[date, date]:
    """
    获取指定季度的起止日期
    
    Args:
        year: 年份
        quarter: 季度 (1-4)
        
    Returns:
        tuple: (起始日期, 结束日期)
    """
    if quarter < 1 or quarter > 4:
        raise ValueError("季度必须在1-4之间")
    
    start_month = (quarter - 1) * 3 + 1
    
    if quarter == 4:
        end_month = 12
        end_day = 31
    else:
        end_month = quarter * 3
        # 计算该月最后一天
        next_month = end_month + 1
        end_day = (date(year, next_month, 1) - timedelta(days=1)).day
    
    start_date = date(year, start_month, 1)
    end_date = date(year, end_month, end_day)
    
    return start_date, end_date


def get_month_date_range(year: int, month: int) -> Tuple[date, date]:
    """
    获取指定月份的起止日期
    
    Args:
        year: 年份
        month: 月份 (1-12)
        
    Returns:
        tuple: (起始日期, 结束日期)
    """
    if month < 1 or month > 12:
        raise ValueError("月份必须在1-12之间")
    
    start_date = date(year, month, 1)
    
    # 计算该月最后一天
    if month == 12:
        end_date = date(year, 12, 31)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date


def get_week_date_range(target_date: Optional[date] = None) -> Tuple[date, date]:
    """
    获取指定日期所在周的起止日期（周一到周日）
    
    Args:
        target_date: 目标日期，默认为当前日期
        
    Returns:
        tuple: (起始日期, 结束日期)
    """
    if not target_date:
        target_date = timezone.now().date()
    
    # 获取周一（weekday()返回0-6，0是周一）
    start_date = target_date - timedelta(days=target_date.weekday())
    end_date = start_date + timedelta(days=6)
    
    return start_date, end_date


def get_current_year() -> int:
    """
    获取当前年份
    
    Returns:
        int: 当前年份
    """
    return timezone.now().year


def get_current_month() -> int:
    """
    获取当前月份
    
    Returns:
        int: 当前月份
    """
    return timezone.now().month


def get_current_quarter() -> int:
    """
    获取当前季度
    
    Returns:
        int: 当前季度 (1-4)
    """
    return (timezone.now().month - 1) // 3 + 1


def format_duration(days: Optional[int]) -> str:
    """
    格式化时长显示
    
    Args:
        days: 天数
        
    Returns:
        str: 格式化的时长字符串
    """
    if days is None:
        return "未知"
    
    if days == 0:
        return "当天"
    elif days < 0:
        return f"提前{abs(days)}天"
    else:
        return f"{days}天"


def is_overdue(reference_date: Optional[date], deadline_days: int) -> bool:
    """
    判断是否逾期
    
    Args:
        reference_date: 参考日期（如公示日期、签订日期）
        deadline_days: 截止天数
        
    Returns:
        bool: 是否逾期
    """
    if not reference_date:
        return False
    
    deadline = reference_date + timedelta(days=deadline_days)
    return timezone.now().date() > deadline


def get_overdue_days(reference_date: Optional[date], deadline_days: int) -> Optional[int]:
    """
    计算逾期天数
    
    Args:
        reference_date: 参考日期
        deadline_days: 截止天数
        
    Returns:
        int: 逾期天数，未逾期返回0，无法计算返回None
    """
    if not reference_date:
        return None
    
    deadline = reference_date + timedelta(days=deadline_days)
    overdue = (timezone.now().date() - deadline).days
    
    return max(0, overdue)