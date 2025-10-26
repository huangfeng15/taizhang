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
    return int(year) if year not in (None, '', 'all') else None


def _normalize_project_codes(codes: Optional[Sequence[str]]) -> Tuple[str, ...]:
    if not codes:
        return tuple()
    filtered = [code for code in codes if code]
    return tuple(sorted(filtered))


def _build_cache_key(prefix: str, year: Optional[int], project_codes: Tuple[str, ...]) -> str:
    year_key = year if year is not None else 'all'
    codes_key = ','.join(project_codes) if project_codes else 'all'
    return f'metrics:{prefix}:{year_key}:{codes_key}'


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
