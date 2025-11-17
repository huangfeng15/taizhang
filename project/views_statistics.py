from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from project.utils.pagination import apply_pagination
from django.db.models import Sum, Count, Value, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import extend_schema, OpenApiParameter

from contract.models import Contract
from project.enums import FilePositioning, PROCUREMENT_METHODS_COMMON_LABELS
from project.services.metrics import get_combined_statistics
from project.filter_config import get_monitoring_filter_config, resolve_monitoring_year
from project.views_helpers import (
    _extract_monitoring_filters,
    _build_monitoring_filter_fields,
    _build_pagination_querystring,
    _resolve_global_filters,
    _get_page_size,
)


def statistics_view(request):
    """
    统计分析页面 - 显示采购、合同、付款、结算的统计数据和图表
    """
    import json

    year_context, project_codes, project_filter, filter_config = _extract_monitoring_filters(request)

    stats_bundle = get_combined_statistics(
        year_context['year_filter'],
        project_filter,
    )
    procurement_stats = stats_bundle['procurement']
    contract_stats = stats_bundle['contract']
    payment_stats = stats_bundle['payment']
    settlement_stats = stats_bundle['settlement']

    procurement_method_labels = [item['method'] for item in procurement_stats['method_distribution']]
    procurement_method_data = [item['count'] for item in procurement_stats['method_distribution']]

    procurement_monthly_data = [0] * 12
    for item in procurement_stats['monthly_trend']:
        month_str = item['month']
        if month_str:
            month = int(month_str.split('-')[1])
            procurement_monthly_data[month - 1] = item['count']

    cycle_by_method = procurement_stats.get('cycle_by_method', {})
    common_methods = procurement_stats.get('common_methods', [])

    procurement_duration_common_labels = PROCUREMENT_METHODS_COMMON_LABELS
    procurement_duration_common_within15 = [cycle_by_method.get(m, {}).get('within_15', 0) for m in common_methods]
    procurement_duration_common_within25 = [cycle_by_method.get(m, {}).get('within_25', 0) for m in common_methods]
    procurement_duration_common_within40 = [cycle_by_method.get(m, {}).get('within_40', 0) for m in common_methods]
    procurement_duration_common_within60 = [cycle_by_method.get(m, {}).get('within_60', 0) for m in common_methods]
    procurement_duration_common_over60 = [cycle_by_method.get(m, {}).get('over_60', 0) for m in common_methods]

    all_methods = procurement_stats.get('all_methods_list', [])
    procurement_duration_all_labels = all_methods
    procurement_duration_all_within15 = [cycle_by_method.get(m, {}).get('within_15', 0) for m in all_methods]
    procurement_duration_all_within25 = [cycle_by_method.get(m, {}).get('within_25', 0) for m in all_methods]
    procurement_duration_all_within40 = [cycle_by_method.get(m, {}).get('within_40', 0) for m in all_methods]
    procurement_duration_all_within60 = [cycle_by_method.get(m, {}).get('within_60', 0) for m in all_methods]
    procurement_duration_all_over60 = [cycle_by_method.get(m, {}).get('over_60', 0) for m in all_methods]

    contract_type_labels = [item['type'] for item in contract_stats['type_distribution']]
    contract_type_data = [item['amount'] for item in contract_stats['type_distribution']]

    contract_source_labels = [item['source'] for item in contract_stats['source_distribution']]
    contract_source_data = [item['count'] for item in contract_stats['source_distribution']]

    context = {
        'year_context': year_context,
        'monitoring_filters': _build_monitoring_filter_fields(filter_config),
        'procurement_stats': procurement_stats,
        'contract_stats': contract_stats,
        'procurement_method_labels': json.dumps(procurement_method_labels, ensure_ascii=False),
        'procurement_method_data': json.dumps(procurement_method_data, ensure_ascii=False),
        'procurement_monthly_data': json.dumps(procurement_monthly_data, ensure_ascii=False),
        'procurement_duration_common_labels': json.dumps(procurement_duration_common_labels, ensure_ascii=False),
        'procurement_duration_common_within15': json.dumps(procurement_duration_common_within15, ensure_ascii=False),
        'procurement_duration_common_within25': json.dumps(procurement_duration_common_within25, ensure_ascii=False),
        'procurement_duration_common_within40': json.dumps(procurement_duration_common_within40, ensure_ascii=False),
        'procurement_duration_common_within60': json.dumps(procurement_duration_common_within60, ensure_ascii=False),
        'procurement_duration_common_over60': json.dumps(procurement_duration_common_over60, ensure_ascii=False),
        'procurement_duration_all_labels': json.dumps(procurement_duration_all_labels, ensure_ascii=False),
        'procurement_duration_all_within15': json.dumps(procurement_duration_all_within15, ensure_ascii=False),
        'procurement_duration_all_within25': json.dumps(procurement_duration_all_within25, ensure_ascii=False),
        'procurement_duration_all_within40': json.dumps(procurement_duration_all_within40, ensure_ascii=False),
        'procurement_duration_all_within60': json.dumps(procurement_duration_all_within60, ensure_ascii=False),
        'procurement_duration_all_over60': json.dumps(procurement_duration_all_over60, ensure_ascii=False),
        'contract_type_labels': json.dumps(contract_type_labels, ensure_ascii=False),
        'contract_type_data': json.dumps(contract_type_data, ensure_ascii=False),
        'contract_source_labels': json.dumps(contract_source_labels, ensure_ascii=False),
        'contract_source_data': json.dumps(contract_source_data, ensure_ascii=False),
        'payment_stats': payment_stats,
        'settlement_stats': settlement_stats,
        'pagination_query': _build_pagination_querystring(request, excluded_keys=['page']),
        **filter_config,
    }
    return render(request, 'monitoring/statistics.html', context)


def ranking_view(request):
    """
    业务排名页面
    """
    from project.services.ranking import (
        get_procurement_on_time_ranking,
        get_procurement_cycle_ranking,
        get_procurement_quantity_ranking,
        get_archive_timeliness_ranking,
        get_archive_speed_ranking,
        get_contract_ranking,
        get_settlement_ranking,
        get_comprehensive_ranking,
    )

    current_year = datetime.now().year
    selected_year = request.GET.get('year', '')
    ranking_type = request.GET.get('type', 'comprehensive')
    rank_by = request.GET.get('rank_by', 'project')

    if selected_year == '' or selected_year == 'all':
        year_filter = None
    elif selected_year and selected_year.isdigit():
        year_filter = int(selected_year)
    else:
        year_filter = None

    _, _, _, filter_config = _extract_monitoring_filters(request)

    ranking_filters = _build_monitoring_filter_fields(
        filter_config,
        extra_fields=[
            {
                'type': 'select',
                'name': 'rank_by',
                'label': '维度',
                'value': rank_by,
                'autosubmit': True,
                'options': [
                    {'value': 'project', 'label': '按项目'},
                    {'value': 'person', 'label': '按个人'},
                ],
            },
            {
                'type': 'hidden',
                'name': 'type',
                'value': ranking_type,
            },
        ],
    )

    context = {
        'page_title': '业务排名',
        'ranking_type': ranking_type,
        'rank_by': rank_by,
        'monitoring_filters': ranking_filters,
        'pagination_query': _build_pagination_querystring(request, excluded_keys=['page']),
        **filter_config,
    }

    if ranking_type == 'procurement_ontime':
        context['procurement_ranking'] = get_procurement_on_time_ranking(rank_type=rank_by, year=year_filter)
    elif ranking_type == 'procurement_cycle':
        context['procurement_ranking'] = get_procurement_cycle_ranking(rank_type=rank_by, year=year_filter)
    elif ranking_type == 'procurement_quantity':
        context['procurement_ranking'] = get_procurement_quantity_ranking(rank_type=rank_by, year=year_filter)
    elif ranking_type == 'archive_timeliness':
        context['archive_ranking'] = get_archive_timeliness_ranking(rank_type=rank_by, year=year_filter)
    elif ranking_type == 'archive_speed':
        context['archive_ranking'] = get_archive_speed_ranking(rank_type=rank_by, year=year_filter)
    elif ranking_type == 'contract':
        context['contract_ranking'] = get_contract_ranking(rank_type=rank_by, year=year_filter)
    elif ranking_type == 'settlement':
        context['settlement_ranking'] = get_settlement_ranking(rank_type=rank_by)
    else:
        context['comprehensive_ranking'] = get_comprehensive_ranking(year=year_filter)

    return render(request, 'monitoring/ranking.html', context)


@extend_schema(
    summary="统计详情（JSON）",
    description="按模块（采购/合同/付款/结算）返回统计详情数据与汇总信息，用于前端表格和图表。",
    parameters=[
        OpenApiParameter(
            name="module",
            type=str,
            location=OpenApiParameter.PATH,
            description="统计模块：procurement/contract/payment/settlement",
            required=True,
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            description="页码（从1开始）",
            required=False,
        ),
        OpenApiParameter(
            name="page_size",
            type=int,
            location=OpenApiParameter.QUERY,
            description="每页数量，默认50，最大100",
            required=False,
        ),
    ],
    tags=["统计"],
)
def statistics_detail_api(request, module):
    """统计详情数据API，返回JSON格式的表格数据。"""
    try:
        global_filters = _resolve_global_filters(request)
        year_filter = global_filters['year_filter']
        project_codes = global_filters['project_list']
        project_filter = project_codes if project_codes else None

        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 50)), 100)

        # 统一统计入口：通过 ReportDataService 获取汇总统计与详情（SRP/DRY）
        from project.services.report_data_service import ReportDataService
        rds = ReportDataService(None, None, project_filter)

        if module == 'procurement':
            details = rds.get_procurement_details()
            stats = rds.get_procurement_statistics()
            summary = {
                'total_count': stats['total_count'],
                'total_budget': stats['total_budget'],
                'total_winning': stats['total_winning'],
                'savings_rate': stats['savings_rate'],
            }
        elif module == 'contract':
            details = rds.get_contract_details()
            stats = rds.get_contract_statistics()
            summary = {
                'total_count': stats['total_count'],
                'total_amount': stats['total_amount'],
                'main_count': stats['main_count'],
                'supplement_count': stats['supplement_count'],
            }
        elif module == 'payment':
            details = rds.get_payment_details()
            stats = rds.get_payment_statistics()
            summary = {
                'total_count': stats['total_count'],
                'total_amount': stats['total_amount'],
                'payment_rate': stats['payment_rate'],
                'estimated_remaining': stats['estimated_remaining'],
            }
        elif module == 'settlement':
            details = rds.get_settlement_details()
            stats = rds.get_settlement_statistics()
            summary = {
                'total_count': stats['total_count'],
                'total_amount': stats['total_amount'],
                'settlement_rate': stats['settlement_rate'],
                'pending_count': stats['pending_count'],
            }
        else:
            return JsonResponse({'success': False, 'message': '不支持的统计模块'}, status=400)

        page_obj = apply_pagination(details, request, page_size=page_size)
        paginator = page_obj.paginator

        response_data = {
            'success': True,
            'module': module,
            'data': list(page_obj),
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'page_size': page_size,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
            },
            'summary': summary,
            'filters': {
                'year': year_filter,
                'project_codes': project_codes,
            }
        }

        return JsonResponse(response_data, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'获取数据失败: {str(e)}'}, status=500)


def statistics_detail_page(request, module):
    """统计详情列表页（HTML）。"""
    try:
        global_filters = _resolve_global_filters(request)
        year_filter = global_filters['year_filter']
        project_codes = global_filters['project_list']
        project_filter = project_codes if project_codes else None

        page = request.GET.get('page', 1)
        page_size = _get_page_size(request, default=20, max_size=100)

        year_context = resolve_monitoring_year(request)
        year_context['selected_year_value'] = global_filters['year_value']
        year_context['year_filter'] = year_filter
        filter_config = get_monitoring_filter_config(request, year_context=year_context)

        # 统一统计入口：通过 ReportDataService 获取汇总统计与详情（SRP/DRY）
        from project.services.report_data_service import ReportDataService
        rds = ReportDataService(None, None, project_filter)

        if module == 'procurement':
            details = rds.get_procurement_details()
            stats = rds.get_procurement_statistics()
            page_title = '采购统计详情'
            template_name = 'monitoring/statistics_procurement_details.html'
        elif module == 'contract':
            details = rds.get_contract_details()
            stats = rds.get_contract_statistics()
            page_title = '合同统计详情'
            template_name = 'monitoring/statistics_contract_details.html'
        elif module == 'payment':
            details = rds.get_payment_details()
            stats = rds.get_payment_statistics()
            page_title = '付款统计详情'
            template_name = 'monitoring/statistics_payment_details.html'
        elif module == 'settlement':
            details = rds.get_settlement_details()
            stats = rds.get_settlement_statistics()
            page_title = '结算统计详情'
            template_name = 'monitoring/statistics_settlement_details.html'
        else:
            messages.error(request, '不支持的统计模块')
            return redirect('statistics_view')

        page_obj = apply_pagination(details, request, page_size=page_size)
        paginator = page_obj.paginator

        context = {
            'page_title': page_title,
            'module': module,
            'details': page_obj,
            'page_obj': page_obj,
            'stats': stats,
            **filter_config,
            'pagination_query': _build_pagination_querystring(request, excluded_keys=['page']),
        }

        return render(request, template_name, context)

    except Exception as e:
        messages.error(request, f'加载详情页失败: {str(e)}')
        return redirect('statistics_view')


def statistics_detail_export(request, module):
    """统计详情导出 - Excel。统一通过 ReportDataService 获取详情（SRP/DRY）。"""
    from project.utils.excel_beautifier import beautify_worksheet
    import pandas as pd
    from io import BytesIO
    from datetime import datetime

    try:
        global_filters = _resolve_global_filters(request)
        year_filter = global_filters['year_filter']
        project_codes = global_filters['project_list']
        project_filter = project_codes if project_codes else None

        # 统一统计入口
        from project.services.report_data_service import ReportDataService
        rds = ReportDataService(None, None, project_filter)

        if module == 'procurement':
            details = rds.get_procurement_details()
            filename = f'采购统计详情_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            columns = [
                ('采购编号', 'procurement_code'),
                ('项目名称', 'project_name'),
                ('项目编号', 'project_code'),
                ('采购单位', 'procurement_unit'),
                ('中标单位', 'winning_bidder'),
                ('采购方式', 'procurement_method'),
                ('采购类别', 'procurement_category'),
                ('预算(元)', 'budget_amount'),
                ('中标价(元)', 'winning_amount'),
                ('控制价(元)', 'control_price'),
                ('节约额(元)', 'savings_amount'),
                ('节约率(%)', 'savings_rate'),
                ('结果公示日期', 'result_publicity_release_date'),
                ('归档日期', 'archive_date'),
            ]
        elif module == 'contract':
            details = rds.get_contract_details()
            filename = f'合同统计详情_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            columns = [
                ('合同编号', 'contract_code'),
                ('合同序号', 'contract_sequence'),
                ('合同名称', 'contract_name'),
                ('文件定位', 'file_positioning'),
                ('合同来源', 'contract_source'),
                ('甲方', 'party_a'),
                ('乙方', 'party_b'),
                ('合同额(元)', 'contract_amount'),
                ('签订日期', 'signing_date'),
                ('累计支付(元)', 'total_paid'),
                ('支付次数', 'payment_count'),
                ('支付比例(%)', 'payment_ratio'),
                ('归档日期', 'archive_date'),
                ('项目编号', 'project_code'),
                ('项目名称', 'project_name'),
            ]
        elif module == 'payment':
            details = rds.get_payment_details()
            filename = f'付款统计详情_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            columns = [
                ('付款单号', 'payment_code'),
                ('付款额(元)', 'payment_amount'),
                ('付款日期', 'payment_date'),
                ('是否结算', 'is_settled'),
                ('结算金额(元)', 'settlement_amount'),
                ('对应合同号', 'contract_code'),
                ('对应合同序号', 'contract_sequence'),
                ('合同名称', 'contract_name'),
                ('乙方', 'party_b'),
                ('项目编号', 'project_code'),
                ('项目名称', 'project_name'),
            ]
        elif module == 'settlement':
            details = rds.get_settlement_details()
            filename = f'结算统计详情_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            columns = [
                ('合同编号', 'contract_code'),
                ('合同名称', 'contract_name'),
                ('乙方', 'party_b'),
                ('签订日期', 'signing_date'),
                ('合同额(元)', 'contract_amount'),
                ('结算额(元)', 'settlement_amount'),
                ('差异额(元)', 'variance'),
                ('差异率(%)', 'variance_rate'),
                ('最后支付日期', 'payment_date'),
                ('项目编号', 'project_code'),
                ('项目名称', 'project_name'),
            ]
        else:
            messages.error(request, '不支持的统计模块')
            return redirect('statistics_view')

        if len(details) > 10000:
            messages.warning(request, f'数据量过大({len(details)}条), 请缩小范围后再导出')
            return redirect('statistics_view')

        data_for_export = []
        for item in details:
            row = {}
            for col_name, col_key in columns:
                value = item.get(col_key, '')
                if isinstance(value, (date, datetime)):
                    value = value.strftime('%Y-%m-%d')
                elif isinstance(value, bool):
                    value = '是' if value else '否'
                row[col_name] = value
            data_for_export.append(row)

        df = pd.DataFrame(data_for_export)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='统计详情', index=False)
            # 可选：样式美化
            try:
                beautify_worksheet(writer.book.active)
            except Exception:
                pass

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'导出失败: {str(e)}'}, status=500)
