from __future__ import annotations

from functools import lru_cache
from typing import Dict, Iterable, Optional, Sequence, Tuple

from django.core.cache import cache


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
    # 统一通过 ReportDataService 聚合统计，避免直接散落调用（SRP/DRY）
    from datetime import date
    from project.services.report_data_service import ReportDataService

    codes_list: Optional[Sequence[str]] = list(project_codes) if project_codes else None
    start = date(year, 1, 1) if year is not None else None
    end = date(year, 12, 31) if year is not None else None
    rds = ReportDataService(start, end, codes_list)

    return {
        'procurement': rds.get_procurement_statistics(),
        'contract': rds.get_contract_statistics(),
        'payment': rds.get_payment_statistics(),
        'settlement': rds.get_settlement_statistics(),
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
