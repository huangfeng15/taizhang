"""
共享工具方法（仅内部复用，不改变对外行为）：
- 年份与项目编码归一化
- 缓存键构造（与现有metrics一致的格式）
- 安全比率/百分比计算
"""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Optional, Sequence, Tuple


def normalize_year(year: Optional[int]) -> Optional[int]:
    """将 'all'/'', None 视为全量，其他转为 int。"""
    return int(year) if year not in (None, '', 'all') else None


def normalize_project_codes(codes: Optional[Sequence[str]]) -> Tuple[str, ...]:
    """清洗项目编码列表：去空、排序、转为不可变元组便于缓存。"""
    if not codes:
        return tuple()
    filtered = [code for code in codes if code]
    return tuple(sorted(filtered))


def build_cache_key(prefix: str, year: Optional[int], project_codes: Tuple[str, ...], *, namespace: str = 'metrics') -> str:
    """构造统一缓存键（与现有metrics一致）：`{namespace}:{prefix}:{year|all}:{codes|all}`"""
    year_key = year if year is not None else 'all'
    codes_key = ','.join(project_codes) if project_codes else 'all'
    return f'{namespace}:{prefix}:{year_key}:{codes_key}'


def safe_ratio(part: float, total: float, *, digits: Optional[int] = None) -> float:
    """安全比率：当 total<=0 返回 0。可选小数位数四舍五入。"""
    if not total:
        return 0.0
    value = part / total
    return round(value, digits) if digits is not None else value


def percent(part: float, total: float, *, digits: int = 1) -> float:
    """百分比（0-100），当 total<=0 返回 0。默认保留1位小数。"""
    return round(safe_ratio(part, total) * 100, digits)

