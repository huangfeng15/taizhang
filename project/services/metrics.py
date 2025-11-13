from __future__ import annotations

from functools import lru_cache
from typing import Dict, Iterable, Optional, Sequence, Tuple

from django.core.cache import cache

from project.services.statistics import (
    get_procurement_statistics,
    get_contract_statistics,
    get_payment_statistics,
    get_settlement_statistics,
)

DEFAULT_CACHE_TIMEOUT = 300  # 5 分钟


def _normalize_year(year: Optional[int]) -> Optional[int]:
    # 统一委托 shared 工具，保持行为不变
    from project.services.shared.utils import normalize_year
    return normalize_year(year)


def _normalize_project_codes(codes: Optional[Sequence[str]]) -> Tuple[str, ...]:
    # 统一委托 shared 工具，保持行为不变
    from project.services.shared.utils import normalize_project_codes
    return normalize_project_codes(codes)


def _build_cache_key(prefix: str, year: Optional[int], project_codes: Tuple[str, ...]) -> str:
    # 使用 shared 工具构造相同格式的键：metrics:{prefix}:{year|all}:{codes|all}
    from project.services.shared.utils import build_cache_key
    return build_cache_key(prefix, year, project_codes, namespace='metrics')


@lru_cache(maxsize=128)
def _compute_combined_statistics(year: Optional[int], project_codes: Tuple[str, ...]) -> Dict[str, Dict]:
    codes_list: Optional[Sequence[str]] = list(project_codes) if project_codes else None
    return {
        'procurement': get_procurement_statistics(year, codes_list),
        'contract': get_contract_statistics(year, codes_list),
        'payment': get_payment_statistics(year, codes_list),
        'settlement': get_settlement_statistics(year, codes_list),
    }


def get_combined_statistics(
    year: Optional[int] = None,
    project_codes: Optional[Iterable[str]] = None,
    *,
    use_cache: bool = True,
) -> Dict[str, Dict]:
    normalized_year = _normalize_year(year)
    normalized_codes = _normalize_project_codes(project_codes)
    cache_key = _build_cache_key('combined', normalized_year, normalized_codes)

    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    data = _compute_combined_statistics(normalized_year, normalized_codes)
    if use_cache:
        cache.set(cache_key, data, DEFAULT_CACHE_TIMEOUT)
    return data
