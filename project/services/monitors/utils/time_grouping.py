"""
时间分组与趋势辅助工具

目的：消除 `archive_statistics.py` 与 `cycle_statistics.py` 中的重复分组/排序/对齐逻辑，
在不改变现有行为的前提下复用公共实现（KISS/DRY/OCP）。
"""
from __future__ import annotations

from typing import Iterable, List, Dict, Any

from django.db.models import Avg


def group_by_month(queryset, *, cycle_field: str) -> List[Dict[str, Any]]:
    """
    按业务月分组聚合（仅统计有数据的月份）。

    Args:
        queryset: 已带有 business_month 字段的查询集
        cycle_field: 周期字段名（如 'archive_cycle' 或 'work_cycle'）
    Returns:
        [{'month': 1, 'period': '1月', 'avg_cycle': 12, 'count': 3}, ...]
    """
    trend: List[Dict[str, Any]] = []
    for month in range(1, 13):
        month_qs = queryset.filter(business_month=month)
        count = month_qs.count()
        if count > 0:
            avg_td = month_qs.aggregate(avg=Avg(cycle_field))['avg']
            avg_cycle = round(avg_td.days, 1) if avg_td else 0
            trend.append({
                'month': month,
                'period': f'{month}月',
                'avg_cycle': avg_cycle,
                'count': count,
            })
    return trend


def group_by_half_year(queryset, *, cycle_field: str) -> List[Dict[str, Any]]:
    """
    按上/下半年聚合（仅统计有数据的半年）。

    要求查询集包含 business_year 和 business_month。
    """
    trend: List[Dict[str, Any]] = []
    years = queryset.values_list('business_year', flat=True).distinct().order_by('business_year')
    for year in years:
        # 上半年
        h1_qs = queryset.filter(business_year=year, business_month__lte=6)
        h1_cnt = h1_qs.count()
        if h1_cnt > 0:
            h1_avg_td = h1_qs.aggregate(avg=Avg(cycle_field))['avg']
            h1_avg = round(h1_avg_td.days, 1) if h1_avg_td else 0
            trend.append({
                'year': year,
                'half': 1,
                'period': f'{year}上半年',
                'avg_cycle': h1_avg,
                'count': h1_cnt,
            })

        # 下半年
        h2_qs = queryset.filter(business_year=year, business_month__gt=6)
        h2_cnt = h2_qs.count()
        if h2_cnt > 0:
            h2_avg_td = h2_qs.aggregate(avg=Avg(cycle_field))['avg']
            h2_avg = round(h2_avg_td.days, 1) if h2_avg_td else 0
            trend.append({
                'year': year,
                'half': 2,
                'period': f'{year}下半年',
                'avg_cycle': h2_avg,
                'count': h2_cnt,
            })
    return trend


def sort_halfyear_labels(labels: Iterable[str]) -> List[str]:
    """规范化并按年/半年排序标签（支持 '2024-H1/H2' 或 '2024上半年/下半年'）。"""
    def key(lbl: str):
        try:
            if '-H' in lbl:
                year_str, half = lbl.split('-H')
                return (int(year_str), int(half))
            if '上半年' in lbl:
                year_str = lbl.split('上半年')[0]
                return (int(year_str), 1)
            if '下半年' in lbl:
                year_str = lbl.split('下半年')[0]
                return (int(year_str), 2)
        except Exception:
            pass
        return (9999, 9)

    return sorted(set(labels), key=key)


def sort_month_labels(labels: Iterable[str]) -> List[str]:
    """按月份自然顺序排序（标签形如 '1月'/'12月'）。"""
    def key(lbl: str):
        try:
            if '月' in lbl:
                return int(lbl.replace('月', ''))
        except Exception:
            pass
        return 99

    return sorted(set(labels), key=key)


def align_series(trend_list: List[Dict[str, Any]], labels: Iterable[str]) -> List[Any]:
    """将趋势数据对齐到统一标签序列，缺失位置返回 None。"""
    mapping = {item['period']: item.get('avg_cycle') for item in trend_list}
    return [mapping.get(lbl, None) for lbl in labels]

