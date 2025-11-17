"""
业务常量集中管理
遵循 DRY 原则，避免魔法值散落在代码各处
"""
import os
from datetime import date, datetime
from typing import List


def get_base_year() -> int:
    """
    获取系统基准年份（数据起始年份）
    
    默认为 2019，可通过环境变量 SYSTEM_BASE_YEAR 覆盖
    """
    year_str = os.environ.get('SYSTEM_BASE_YEAR', '2019').strip()
    try:
        base_year = int(year_str)
        current_year = datetime.now().year
        if base_year < 2000 or base_year > current_year:
            raise ValueError(f"基准年份必须在 2000 到 {current_year} 之间")
        return base_year
    except ValueError as e:
        print(f"[警告] SYSTEM_BASE_YEAR 配置无效 ({year_str})，使用默认值 2019")
        return 2019


def get_year_window() -> int:
    """
    获取年份窗口（向未来延伸的年数）
    
    默认为 1 年（允许录入下一年度数据），可通过环境变量 SYSTEM_YEAR_WINDOW 覆盖
    """
    window_str = os.environ.get('SYSTEM_YEAR_WINDOW', '1').strip()
    try:
        window = int(window_str)
        if window < 0 or window > 5:
            raise ValueError("年份窗口必须在 0 到 5 之间")
        return window
    except ValueError:
        print(f"[警告] SYSTEM_YEAR_WINDOW 配置无效 ({window_str})，使用默认值 1")
        return 1


def get_default_monitor_start_date() -> date:
    """
    获取更新监控默认起始日期
    
    默认为 2025-10-01，可通过环境变量 MONITOR_START_DATE 覆盖
    """
    date_str = os.environ.get('MONITOR_START_DATE', '2025-10-01').strip()
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        print(f"[警告] MONITOR_START_DATE 配置无效 ({date_str})，使用默认值 2025-10-01")
        return date(2025, 10, 1)


# ==================== 导出常量 ====================

BASE_YEAR = get_base_year()
YEAR_WINDOW = get_year_window()
DEFAULT_MONITOR_START_DATE = get_default_monitor_start_date()


# ==================== 辅助函数 ====================

def get_year_range(include_future: bool = True) -> List[int]:
    """
    获取系统支持的年份范围列表
    
    Args:
        include_future: 是否包含未来年份（用于数据录入）
    
    Returns:
        年份列表，例如 [2019, 2020, ..., 2025, 2026]
    """
    current_year = datetime.now().year
    end_year = current_year + YEAR_WINDOW if include_future else current_year
    return list(range(BASE_YEAR, end_year + 1))


def get_current_year() -> int:
    """获取当前年份"""
    return datetime.now().year