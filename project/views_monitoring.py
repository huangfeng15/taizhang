import json
from datetime import date

from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.shortcuts import render
from django.http import JsonResponse

from project.services.archive_monitor import ArchiveMonitorService
from project.services.update_monitor import UpdateMonitorService
from project.services.completeness import get_completeness_overview
from project.services.metrics import get_combined_statistics
from project.views_helpers import _extract_monitoring_filters, _resolve_global_filters
from project.constants import BASE_YEAR
from .models import Project


def monitoring_cockpit(request):
    """综合监控驾驶舱。"""
    year_context, project_codes, project_filter, filter_config = _extract_monitoring_filters(request)
    year_filter = year_context['year_filter']
    start_date = date(year_filter, 1, 1) if year_filter else date(BASE_YEAR, 1, 1)

    archive_service = ArchiveMonitorService(year=year_filter, project_codes=project_filter)
    archive_overview = archive_service.get_archive_overview()
    overdue_list = archive_service.get_overdue_list()[:5]

    update_service = UpdateMonitorService()
    update_snapshot = update_service.build_snapshot(year=year_filter, start_date=start_date)

    completeness_overview = get_completeness_overview(year=year_filter, project_codes=project_filter)
    stats_bundle = get_combined_statistics(year_filter, project_filter)
    procurement_stats = stats_bundle['procurement']
    contract_stats = stats_bundle['contract']
    payment_stats = stats_bundle['payment']

    from project.services.monitors.workload_statistics import WorkloadStatistics
    workload_stats = WorkloadStatistics(time_dimension='current_year', dimension_type='person')
    workload_ranking = workload_stats.get_workload_ranking()
    workload_summary = {
        'procurement': sum(r['procurement_count'] for r in workload_ranking),
        'contract': sum(r['contract_count'] for r in workload_ranking),
        'payment': sum(r['payment_count'] for r in workload_ranking),
        'settlement': sum(r['settlement_count'] for r in workload_ranking),
    }

    kpis = {
        'timeliness_rate': update_snapshot['kpis']['overallTimelinessRate'] if update_snapshot['kpis']['overallTimelinessRate'] is not None else 0,
        'timely_events': update_snapshot['kpis']['totalEvents'] - update_snapshot['kpis']['delayedEvents'],
        'total_events': update_snapshot['kpis']['totalEvents'],
        'archive_rate': archive_overview['overall_rate'],
        'overdue_items': archive_overview['procurement']['overdue'] + archive_overview['contract']['overdue'],
        'completeness_rate': round((completeness_overview['procurement_field_check']['completeness_rate'] + completeness_overview['contract_field_check']['completeness_rate']) / 2, 2),
        'completeness_issues_main': "合同-支付对账异常" if completeness_overview.get('payment_check', {}).get('summary', {}).get('overpaid_contracts', 0) > 0 else "关键字段完整",
        'risk_items': completeness_overview.get('error_count', 0),
        'risk_issues_main': "资金超额、资料滞后",
    }

    core_stats = {
        'total_budget': procurement_stats['total_budget'],
        'total_projects': Project.objects.filter(project_code__in=project_codes).count() if project_codes else Project.objects.count(),
        'total_contract_amount': contract_stats['total_amount'],
        'total_contracts': contract_stats['total_count'],
        'total_payment_amount': payment_stats['total_amount'],
        'payment_progress': (payment_stats['total_amount'] / contract_stats['total_amount'] * 100) if contract_stats['total_amount'] > 0 else 0,
    }

    procurement_method_chart_data = {
        'labels': [item['method'] for item in procurement_stats['method_distribution']],
        'datasets': [{
            'label': '采购金额',
            'data': [item['amount'] for item in procurement_stats['method_distribution']],
            'backgroundColor': ['#1890ff', '#13c2c2', '#2fc25b', '#facc14', '#f04864', '#8543e0', '#3436c7'],
        }],
    }

    contract_type_chart_data = {
        'labels': [item['type'] for item in contract_stats['type_distribution']],
        'datasets': [{
            'label': '合同数量',
            'data': [item['count'] for item in contract_stats['type_distribution']],
            'backgroundColor': '#1890ff',
        }],
    }

    monthly_labels = [f"{i}月" for i in range(1, 13)]
    proc_monthly = {int(item['month'].split('-')[1]): item['amount'] for item in procurement_stats['monthly_trend']}
    cont_monthly = {int(item['month'].split('-')[1]): item['amount'] for item in contract_stats['monthly_trend']}
    pay_monthly = {int(item['month'].split('-')[1]): item['amount'] for item in payment_stats['monthly_trend']}

    monthly_trend_chart_data = {
        'labels': monthly_labels,
        'datasets': [
            {
                'label': '采购金额',
                'data': [proc_monthly.get(i, 0) for i in range(1, 13)],
                'borderColor': '#1890ff',
                'backgroundColor': 'rgba(24, 144, 255, 0.1)',
                'tension': 0.4,
                'fill': True,
            },
            {
                'label': '合同金额',
                'data': [cont_monthly.get(i, 0) for i in range(1, 13)],
                'borderColor': '#2fc25b',
                'backgroundColor': 'rgba(47, 194, 91, 0.1)',
                'tension': 0.4,
                'fill': True,
            },
            {
                'label': '支付金额',
                'data': [pay_monthly.get(i, 0) for i in range(1, 13)],
                'borderColor': '#facc14',
                'backgroundColor': 'rgba(250, 204, 20, 0.1)',
                'tension': 0.4,
                'fill': True,
            },
        ],
    }

    heatmap_projects = update_snapshot['projects']

    archive_progress = {
        'procurement': archive_overview['procurement']['rate'],
        'contract': archive_overview['contract']['rate'],
        'settlement': archive_overview['settlement']['rate'],
    }

    completeness_progress = {
        'procurement': completeness_overview['procurement_field_check']['completeness_rate'],
        'contract': completeness_overview['contract_field_check']['completeness_rate'],
        'payment': 98,
        'settlement': 75,
    }
    completeness_issues = completeness_overview.get('contract_check', {}).get('issues', [])[:5]

    context = {
        'page_title': '综合监控驾驶舱',
        'year_options': year_context['available_years'],
        'selected_year': year_context['selected_year_value'],
        'start_date_value': start_date.isoformat(),
        'monitoring_snapshot': update_snapshot,
        'update_statistics': update_snapshot['statistics'],
        'overdue_list': overdue_list,
        **filter_config,
        'kpis': kpis,
        'core_stats': core_stats,
        'workload_summary': workload_summary,
        'procurement_method_chart_data_json': json.dumps(procurement_method_chart_data, ensure_ascii=False),
        'contract_type_chart_data_json': json.dumps(contract_type_chart_data, ensure_ascii=False),
        'monthly_trend_chart_data_json': json.dumps(monthly_trend_chart_data, ensure_ascii=False),
        'heatmap_projects': heatmap_projects,
        'archive_progress': archive_progress,
        'completeness_progress': completeness_progress,
        'completeness_issues': completeness_issues,
    }
    return render(request, 'monitoring/cockpit.html', context)


def archive_monitor(request):
    """归档监控（项目/个人视图）。"""
    from project.services.monitors.archive_statistics import ArchiveStatisticsService
    from project.services.monitors.config import SEVERITY_CONFIG, CYCLE_RULES

    global_filters = _extract_monitoring_filters(request)[0]  # year_context not needed here
    global_filters = _resolve_global_filters(request)
    view_mode = request.GET.get('view_mode', 'project')
    target_code = request.GET.get('target_code', '')
    show_all = request.GET.get('show_all', '') == 'true'

    stats_service = ArchiveStatisticsService()

    if view_mode == 'project':
        overview_data = stats_service.get_projects_archive_overview(
            year_filter=global_filters['year_value'], project_filter=global_filters['project']
        )
    else:
        overview_data = stats_service.get_persons_archive_overview(
            year_filter=global_filters['year_value'], project_filter=global_filters['project']
        )

    detail_data = None
    if target_code:
        if view_mode == 'project':
            detail_data = stats_service.get_project_trend_and_problems(
                project_code=target_code,
                year_filter=global_filters['year_value'],
                show_all=show_all,
            )
        else:
            detail_data = stats_service.get_person_trend_and_problems(
                person_name=target_code,
                year_filter=global_filters['year_value'],
                project_filter=global_filters['project'],
                show_all=show_all,
            )

    all_persons_data = None
    multi_trend = None
    if view_mode == 'person':
        all_persons_data = stats_service.get_all_persons_trend_and_problems(
            year_filter=global_filters['year_value'], project_filter=global_filters['project']
        )
        multi_trend = stats_service.get_persons_multi_trend(
            year_filter=global_filters['year_value'], project_filter=global_filters['project'], top_n=10
        )
    else:
        if global_filters['project']:
            multi_trend = stats_service.get_project_officers_multi_trend(
                project_code=global_filters['project'], year_filter=global_filters['year_value'], top_n=10
            )
        else:
            multi_trend = stats_service.get_projects_multi_trend(
                year_filter=global_filters['year_value'], top_n=10
            )

    year_context, project_codes, project_filter_config, filter_config = _extract_monitoring_filters(request)
    trend_data_json = {}
    if detail_data is not None:
        trend_data_json = {
            'procurement': detail_data.get('procurement_trend', []),
            'contract': detail_data.get('contract_trend', []),
        }

    all_persons_trend_json = {}
    if all_persons_data:
        all_persons_trend_json = {
            'procurement': all_persons_data.get('procurement_trend', []),
            'contract': all_persons_data.get('contract_trend', []),
        }
    multi_trend_json = json.dumps(multi_trend or {}, ensure_ascii=False)

    context = {
        'page_title': '归档监控',
        'view_mode': view_mode,
        'target_code': target_code,
        'overview_data': overview_data,
        'detail_data': detail_data,
        'all_persons_data': all_persons_data,
        'show_all': show_all,
        'trend_data_json': json.dumps(trend_data_json, ensure_ascii=False),
        'all_persons_trend_json': json.dumps(all_persons_trend_json, ensure_ascii=False),
        'multi_trend_json': multi_trend_json,
        'severity_config': SEVERITY_CONFIG,
        'filter_config': filter_config,
        'procurement_method_choices': list((CYCLE_RULES.get('procurement', {}).get('deadline_map', {}) or {}).keys()),
    }
    return render(request, 'monitoring/archive.html', context)


def update_monitor(request):
    """
    更新监控 - 双视图模式（项目视图/个人视图）
    参照archive_monitor的成功设计模式
    """
    from project.services.monitors.update_statistics_facade import UpdateStatisticsFacade
    from datetime import datetime

    # 1. 解析全局筛选参数（与归档监控完全一致）
    global_filters = _resolve_global_filters(request)
    view_mode = request.GET.get('view_mode', 'project')
    target_code = request.GET.get('target_code', '')
    show_all = request.GET.get('show_all', '') == 'true'
    
    # 解析起始日期参数
    start_date = None
    start_date_str = request.GET.get('start_date', '')
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = None

    # 2. 初始化统计门面（简洁的接口调用）
    facade = UpdateStatisticsFacade(start_date=start_date)

    # 3. 获取概览数据（项目视图或个人视图）
    overview_data = facade.get_overview(
        view_mode=view_mode,
        year_filter=global_filters['year_value'],
        project_filter=global_filters['project'],
        start_date=start_date
    )

    # 4. 获取详情数据（如果有目标）
    detail_data = None
    if target_code:
        detail_data = facade.get_detail(
            view_mode=view_mode,
            target_code=target_code,
            year_filter=global_filters['year_value'],
            project_filter=global_filters['project'],
            show_all=show_all
        )

    # 5. 获取主页面的趋势和问题数据
    trend_and_problems = facade.get_trend_and_problems(
        view_mode=view_mode,
        year_filter=global_filters['year_value'],
        project_filter=global_filters['project'],
        show_all=show_all
    )

    # 6. 构建上下文（与归档监控保持一致的结构）
    year_context, project_codes, project_filter_config, filter_config = _extract_monitoring_filters(request)
    
    # 准备趋势图数据（JSON格式）
    trend_data_json = {}
    if detail_data:
        trend_data_json = {
            'procurement': detail_data.get('procurement_trend', []),
            'contract': detail_data.get('contract_trend', []),
            'payment': detail_data.get('payment_trend', []),
            'settlement': detail_data.get('settlement_trend', []),
        }

    # 准备主页面趋势数据
    main_trend_json = {}
    if trend_and_problems:
        main_trend_json = {
            'procurement': trend_and_problems.get('procurement_trend', []),
            'contract': trend_and_problems.get('contract_trend', []),
            'payment': trend_and_problems.get('payment_trend', []),
            'settlement': trend_and_problems.get('settlement_trend', []),
        }

    context = {
        'page_title': '更新监控',
        'view_mode': view_mode,
        'target_code': target_code,
        'overview_data': overview_data,
        'detail_data': detail_data,
        'trend_and_problems': trend_and_problems,
        'show_all': show_all,
        'start_date': start_date_str,
        'trend_data_json': json.dumps(trend_data_json, ensure_ascii=False),
        'main_trend_json': json.dumps(main_trend_json, ensure_ascii=False),
        'filter_config': filter_config,
    }
    return render(request, 'monitoring/update.html', context)


def completeness_check(request):
    """齐全性校验 - 问题列表视图。"""
    from project.services.monitors.completeness_checker import CompletenessChecker

    global_filters = _resolve_global_filters(request)
    responsible_person = request.GET.get('responsible_person', '')
    show_all = request.GET.get('show_all', '') == 'true'

    filters = {}
    if global_filters['year_filter']:
        filters['year_filter'] = global_filters['year_filter']
    if global_filters['project']:
        filters['project'] = global_filters['project']
    if responsible_person:
        filters['responsible_person'] = responsible_person

    return_url = request.get_full_path()

    checker = CompletenessChecker()
    problems = checker.check_problems(filters, return_url=return_url, show_all=show_all)
    statistics = checker.get_statistics(problems, filters)

    year_context, project_codes, project_filter, filter_config = _extract_monitoring_filters(request)
    context = {
        'problems': problems,
        'statistics': statistics,
        'selected_project': global_filters['project'],
        'selected_person': responsible_person,
        'show_all': show_all,
        'page_title': '齐全性校验',
        'filter_config': filter_config,
    }
    return render(request, 'monitoring/completeness_problems.html', context)


@staff_member_required
def completeness_field_config(request):
    """齐全性字段配置页面。"""
    from project.models_completeness_config import CompletenessFieldConfig
    from project.services.completeness import get_default_procurement_fields, get_default_contract_fields
    from procurement.models import Procurement
    from contract.models import Contract

    model_type = request.GET.get('model_type', 'procurement')

    if model_type == 'procurement':
        default_fields = get_default_procurement_fields()
        model_class = Procurement
    else:
        default_fields = get_default_contract_fields()
        model_class = Contract

    for idx, field_name in enumerate(default_fields):
        try:
            field = model_class._meta.get_field(field_name)
            field_label = field.verbose_name
        except Exception:
            field_label = field_name

        CompletenessFieldConfig.objects.get_or_create(
            model_type=model_type,
            field_name=field_name,
            defaults={'field_label': field_label, 'is_enabled': True, 'sort_order': idx},
        )

    configs = CompletenessFieldConfig.objects.filter(model_type=model_type).order_by('sort_order', 'field_name')

    context = {
        'model_type': model_type,
        'configs': configs,
        'procurement_count': CompletenessFieldConfig.objects.filter(model_type='procurement').count(),
        'contract_count': CompletenessFieldConfig.objects.filter(model_type='contract').count(),
    }
    return render(request, 'monitoring/completeness_field_config.html', context)


@staff_member_required
@require_POST
def update_completeness_field_config(request):
    """更新齐全性字段配置。"""
    from project.models_completeness_config import CompletenessFieldConfig

    try:
        data = json.loads(request.body)
        model_type = data.get('model_type')
        field_configs = data.get('fields', [])

        for config_data in field_configs:
            field_name = config_data.get('field_name')
            is_enabled = config_data.get('is_enabled', True)
            CompletenessFieldConfig.objects.filter(model_type=model_type, field_name=field_name).update(
                is_enabled=is_enabled
            )

        return JsonResponse({'success': True, 'message': '配置已更新'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'更新失败: {str(e)}'}, status=400)




def cycle_monitor(request):
    """工作周期监控（项目/个人视图）。"""
    from project.services.monitors.cycle_statistics import CycleStatisticsService
    from project.services.monitors.config import SEVERITY_CONFIG, CYCLE_RULES

    global_filters = _extract_monitoring_filters(request)[0]
    global_filters = _resolve_global_filters(request)
    view_mode = request.GET.get('view_mode', 'project')
    target_code = request.GET.get('target_code', '')
    show_all = request.GET.get('show_all', '') == 'true'
    procurement_method = request.GET.get('procurement_method', '')

    stats_service = CycleStatisticsService()

    if view_mode == 'project':
        overview_data = stats_service.get_projects_cycle_overview(
            year_filter=global_filters['year_value'],
            project_filter=global_filters['project'],
            procurement_method=procurement_method if procurement_method else None
        )
    else:
        overview_data = stats_service.get_persons_cycle_overview(
            year_filter=global_filters['year_value'],
            project_filter=global_filters['project'],
            procurement_method=procurement_method if procurement_method else None
        )

    detail_data = None
    if target_code:
        if view_mode == 'project':
            detail_data = stats_service.get_project_trend_and_problems(
                project_code=target_code,
                year_filter=global_filters['year_value'],
                procurement_method=procurement_method if procurement_method else None,
                show_all=show_all,
            )
        else:
            detail_data = stats_service.get_person_trend_and_problems(
                person_name=target_code,
                year_filter=global_filters['year_value'],
                project_filter=global_filters['project'],
                procurement_method=procurement_method if procurement_method else None,
                show_all=show_all,
            )

    # 获取多序列趋势数据
    multi_trend = None
    if view_mode == 'person':
        multi_trend = stats_service.get_persons_multi_trend(
            year_filter=global_filters['year_value'],
            project_filter=global_filters['project'],
            procurement_method=procurement_method if procurement_method else None,
            top_n=10
        )
    else:
        if global_filters['project']:
            multi_trend = stats_service.get_project_officers_multi_trend(
                project_code=global_filters['project'],
                year_filter=global_filters['year_value'],
                procurement_method=procurement_method if procurement_method else None,
                top_n=10
            )
        else:
            multi_trend = stats_service.get_projects_multi_trend(
                year_filter=global_filters['year_value'],
                procurement_method=procurement_method if procurement_method else None,
                top_n=10
            )

    year_context, project_codes, project_filter_config, filter_config = _extract_monitoring_filters(request)
    trend_data_json = {}
    if detail_data is not None:
        trend_data_json = {
            'procurement': detail_data.get('procurement_trend', []),
            'contract': detail_data.get('contract_trend', []),
        }

    multi_trend_json = json.dumps(multi_trend or {}, ensure_ascii=False)

    # 获取采购方式选项
    from project.enums import ProcurementMethod
    procurement_method_choices = [
        {'value': '', 'label': '全部采购方式'},
    ]
    for method in ProcurementMethod:
        procurement_method_choices.append({
            'value': method.value,
            'label': method.label
        })

    context = {
        'page_title': '工作周期监控',
        'view_mode': view_mode,
        'target_code': target_code,
        'overview_data': overview_data,
        'detail_data': detail_data,
        'show_all': show_all,
        'procurement_method': procurement_method,
        'procurement_method_choices': procurement_method_choices,
        'trend_data_json': json.dumps(trend_data_json, ensure_ascii=False),
        'multi_trend_json': multi_trend_json,
        'severity_config': SEVERITY_CONFIG,
        'filter_config': filter_config,
        'cycle_rules': CYCLE_RULES,
    }
    return render(request, 'monitoring/cycle.html', context)
