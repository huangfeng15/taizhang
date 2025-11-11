from typing import Any, Dict
from django.utils import timezone

from project.filter_config import (
    get_monitoring_filter_config,
    resolve_monitoring_year,
)


def _resolve_global_filters(request) -> Dict[str, Any]:
    """
    统一解析全局筛选参数，兼容旧字段。

    返回:
        {
            "year_value": "2024" 或 "all",
            "year_filter": int | None,
            "project": "PRJ001" 或 "",
            "project_list": ["PRJ001"] 或 []
        }
    """
    current_year = timezone.now().year
    raw_year = request.GET.get('global_year') or request.GET.get('year')
    year_value = None
    year_filter = None
    if raw_year == 'all':
        year_value = 'all'
        year_filter = None
    elif raw_year:
        try:
            year_filter = int(raw_year)
            year_value = str(year_filter)
        except (TypeError, ValueError):
            year_filter = current_year
            year_value = str(current_year)
    else:
        year_filter = current_year
        year_value = str(current_year)

    raw_projects = request.GET.getlist('global_project')
    if not raw_projects:
        raw_projects = [value for value in request.GET.getlist('project') if value]
    project_single = raw_projects[0] if raw_projects else request.GET.get('project', '')
    project_list = [project_single] if project_single else []

    return {
        'year_value': year_value,
        'year_filter': year_filter,
        'project': project_single,
        'project_list': project_list,
    }


def _extract_monitoring_filters(request):
    """统一整理监控相关视图需要的年份与项目筛选条件。"""
    global_filters = _resolve_global_filters(request)
    # 利用 resolve_monitoring_year 以保持原有逻辑中的年度范围等配置
    year_context = resolve_monitoring_year(request)
    year_context['selected_year_value'] = global_filters['year_value']
    year_context['year_filter'] = global_filters['year_filter']
    filter_config = get_monitoring_filter_config(request, year_context=year_context)
    project_codes = global_filters['project_list']
    project_filter = project_codes if project_codes else None
    return year_context, project_codes, project_filter, filter_config


def _build_monitoring_filter_fields(filter_config, *, include_project=True, extra_fields=None):
    """
    监控中心页面的筛选项由全局组件负责，此处仅保留补充字段。
    `include_project` 参数保留以兼容旧调用，暂不使用。
    """
    fields = []
    if extra_fields:
        fields.extend(extra_fields)
    return fields


def _build_pagination_querystring(request, excluded_keys=None, extra_params=None):
    params = request.GET.copy()
    excluded_keys = excluded_keys or []
    for key in excluded_keys:
        if key in params:
            params.pop(key, None)
    extra_params = extra_params or {}
    for key, value in extra_params.items():
        params[key] = value
    return params.urlencode()


def _get_page_size(request, default=20, max_size=200):
    """解析分页大小，限制范围避免异常输入。"""
    try:
        size = int(request.GET.get('page_size', default))
    except (TypeError, ValueError):
        return default
    return max(1, min(size, max_size))

