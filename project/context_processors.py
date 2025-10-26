from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from .models import Project


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
    current_year = datetime.now().year
    # 允许用户选择从 2019 年到下一年度，便于提前录入计划数据
    year_start = 2019
    year_end = current_year + 1
    year_options: List[int] = list(range(year_start, year_end + 1))

    project_options = [
        {"code": project.project_code, "name": project.project_name}
        for project in Project.objects.all().order_by("project_name")
    ]

    return {
        "global_filter_projects": project_options,
        "global_year_options": year_options,
        "global_current_year": current_year,
    }

