"""通用筛选工具函数"""

from __future__ import annotations

from typing import Iterable, List, Tuple

from django.db.models import Q, QuerySet

__all__ = [
    "apply_text_filter",
    "apply_multi_field_search",
]


def _split_keywords(value: str) -> Tuple[List[str], str]:
    """将筛选值拆分为关键字列表以及匹配模式（and/or）。"""
    if not value:
        return [], "or"

    normalized = value.replace("，", ",")
    if "," in normalized:
        keywords = [keyword.strip() for keyword in normalized.split(",") if keyword.strip()]
        return keywords, "and"

    keywords = [keyword.strip() for keyword in normalized.split() if keyword.strip()]
    return keywords, "or"


def apply_text_filter(queryset: QuerySet, field_name: str, filter_value: str) -> QuerySet:
    """
    按照项目中通用规则（逗号=且，空格=或）对单个字段进行模糊筛选。

    Args:
        queryset: 原始查询集
        field_name: 需要筛选的字段名称（支持跨表语法）
        filter_value: 用户输入的原始筛选值
    """
    if not filter_value:
        return queryset

    keywords, mode = _split_keywords(filter_value)
    if not keywords:
        return queryset

    lookup = f"{field_name}__icontains"

    if mode == "and":
        for keyword in keywords:
            queryset = queryset.filter(**{lookup: keyword})
        return queryset

    # mode == "or"
    q_object = Q()
    for keyword in keywords:
        q_object |= Q(**{lookup: keyword})
    return queryset.filter(q_object) if q_object else queryset


def apply_multi_field_search(
    queryset: QuerySet,
    fields: Iterable[str],
    search_term: str,
    *,
    mode: str = "auto",
) -> QuerySet:
    """
    在多个字段上执行模糊搜索，复用逗号=且、空格=或的规则。

    Args:
        queryset: 原始查询集
        fields: 需要参与匹配的字段列表
        search_term: 用户输入的搜索词
        mode: 'and' / 'or' / 'auto'，auto 时根据输入是否包含逗号自动判定
    """
    if not search_term:
        return queryset

    normalized = search_term.replace("，", ",")
    mode = mode.lower()
    if mode not in {"and", "or"}:
        mode = "and" if "," in normalized else "or"

    if mode == "and":
        keywords = [token.strip() for token in normalized.split(",") if token.strip()]
        for keyword in keywords:
            if not keyword:
                continue
            q_object = Q()
            for field in fields:
                q_object |= Q(**{f"{field}__icontains": keyword})
            queryset = queryset.filter(q_object)
        return queryset

    # mode == "or"
    keywords = [token.strip() for token in normalized.replace(",", " ").split() if token.strip()]
    if not keywords:
        return queryset

    q_object = Q()
    for keyword in keywords:
        for field in fields:
            q_object |= Q(**{f"{field}__icontains": keyword})

    return queryset.filter(q_object) if q_object else queryset
