from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from .models import Project
from .constants import BASE_YEAR, get_current_year


def _resolve_selected_year(request, current_year: int) -> str:
    raw_year = request.GET.get('global_year') or request.GET.get('year')
    if raw_year == 'all':
        return 'all'
    if raw_year:
        return raw_year
    return str(current_year)


def _resolve_selected_project(request) -> str:
    return request.GET.get('global_project') or request.GET.get('project') or ''


def global_filter_options(request) -> Dict[str, object]:
    """
    为全局筛选组件提供项目和年度选项。

    返回结构：
        {
            "global_filter_projects": [{"code": "...", "name": "..."}],
            "global_year_options": [2019, 2020, ...],
            "global_current_year": 2024
        }
    """
    current_year = get_current_year()
    # 允许用户选择从基准年份到下一年度，便于提前录入计划数据
    year_start = BASE_YEAR
    year_end = current_year + 1
    year_options: List[int] = list(range(year_start, year_end + 1))

    project_options = [
        {"code": project.project_code, "name": project.project_name}
        for project in Project.objects.all().order_by("project_name")
    ]

    selected_year_value = _resolve_selected_year(request, current_year)
    return {
        "global_filter_projects": project_options,
        "global_year_options": year_options,
        "global_current_year": current_year,
        "global_selected_year": selected_year_value,
        "global_selected_project": _resolve_selected_project(request),
    }
