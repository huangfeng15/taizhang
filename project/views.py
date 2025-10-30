from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db import connections
from django.db.models import (
    Count,
    Sum,
    Q,
    OuterRef,
    Subquery,
    Value,
    DecimalField,
    Case,
    When,
    Exists,
    F,
    BooleanField,
    ExpressionWrapper,
)
from django.db.models.functions import Coalesce
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, date, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any
from io import StringIO, BytesIO
import csv
from pathlib import Path
import json
import os
import shutil
import tempfile
import pandas as pd

from .models import Project
from contract.models import Contract
from procurement.models import Procurement
from payment.models import Payment
from settlement.models import Settlement
from supplier_eval.models import SupplierEvaluation
from project.enums import FilePositioning, PROCUREMENT_METHODS_COMMON_LABELS

from project.services.archive_monitor import ArchiveMonitorService
from project.services.update_monitor import UpdateMonitorService
from project.services.completeness import get_completeness_overview, get_project_completeness_ranking
from project.services.statistics import get_procurement_statistics, get_contract_statistics, get_payment_statistics, get_settlement_statistics
from project.services.metrics import get_combined_statistics
from project.filter_config import get_monitoring_filter_config, resolve_monitoring_year
from project.utils.filters import apply_text_filter, apply_multi_field_search
from project.constants import BASE_YEAR, get_current_year, get_year_range, DEFAULT_MONITOR_START_DATE


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


IMPORT_TEMPLATE_DEFINITIONS = {
    'project': {
        'long': {
            'filename': 'project_import_template_long.csv',
            'headers': [
                '项目编码',
                '序号',
                '项目名称',
                '项目描述',
                '项目负责人',
                '项目状态',
                '备注',
                '模板说明',
            ],
            'notes': [
                '【必填字段】项目编码*、项目名称*（标记*号的为必填字段，不能为空）',
                '【编码规则】项目编码仅允许字母、数字、中文、连字符(-)、下划线(_)和点(.)，禁止使用 / 等特殊字符',
                '【状态选项】项目状态可选值：进行中、已完成、已暂停、已取消（留空默认为"进行中"）',
                '【说明】本模板说明行可保留或删除，不影响导入。导入时系统会自动跳过说明行。',
            ],
        },
    },
    'procurement': {
        'long': {
            'filename': 'procurement_import_template_long.csv',
            'headers': [
                '项目编码',
                '序号',
                '招采编号',
                '采购项目名称',
                '采购单位',
                '中标单位',
                '中标单位联系人及方式',
                '采购方式',
                '采购类别',
                '采购预算金额(元)',
                '采购控制价（元）',
                '中标金额（元）',
                '计划结束采购时间',
                '候选人公示结束时间',
                '结果公示发布时间',
                '中标通知书发放日期',
                '采购经办人',
                '需求部门',
                '申请人联系电话（需求部门）',
                '采购需求书审批完成日期（OA）',
                '采购平台',
                '资格审查方式',
                '评标谈判方式',
                '定标方法',
                '公告发布时间',
                '报名截止时间',
                '开标时间',
                '评标委员会成员',
                '投标担保形式及金额（元）',
                '投标担保退回日期',
                '履约担保形式及金额（元）',
                '候选人公示期质疑情况',
                '应招未招说明（由公开转单一或邀请的情况）',
                '资料归档日期',
                '模板说明',
            ],
            'notes': [
                '【必填字段】招采编号*、采购项目名称*（标记*号的为必填字段，不能为空）',
                '【编码规则】招采编号仅允许字母、数字、中文、连字符(-)、下划线(_)和点(.)，禁止使用 / 等特殊字符。建议格式：GC2025001',
                '【项目关联】项目编码字段用于关联已存在的项目，必须填写系统中已存在的项目编码',
                '【时间要求】公告发布时间、报名截止时间、开标时间、候选人公示结束时间、结果公示发布时间等均使用 YYYY-MM-DD 格式',
                '【金额格式】所有金额列仅填写数字（可带小数），单位为元，例如：1500000.00 或 1500000',
                '【采购方式】常见选项：公开招标、单一来源采购、公开询价、直接采购、公开竞价、战采结果应用等，可结合采购类别填写',
                '【担保信息】投标担保与履约担保可填写形式与金额，例如：银行保函 500000.00',
                '【质疑情况】候选人公示期质疑情况用于记录公示期处理情况，可留空',
                '【说明】本模板说明行可保留或删除，不影响导入。导入时系统会自动跳过说明行。',
            ],
        },
    },
    'contract': {
        'long': {
            'filename': 'contract_import_template_long.csv',
            'headers': [
                '项目编码',
                '关联采购编号',
                '文件定位',
                '合同来源',
                '关联主合同编号',
                '序号',
                '合同序号',
                '合同编号',
                '合同名称',
                '合同签订经办人',
                '合同类型',
                '甲方',
                '乙方',
                '含税签约合同价（元）',
                '合同签订日期',
                '甲方法定代表人及联系方式',
                '甲方联系人及联系方式',
                '甲方负责人及联系方式',
                '乙方法定代表人及联系方式',
                '乙方联系人及联系方式',
                '乙方负责人及联系方式',
                '合同工期/服务期限',
                '支付方式',
                '履约担保退回时间',
                '资料归档日期',
                '模板说明',
            ],
            'notes': [
                '【必填字段】合同编号*、合同名称*、甲方*、乙方*、合同签订日期*（标记*号的为必填字段，不能为空）',
                '【编码规则】合同编号与合同序号仅允许字母、数字、中文、连字符(-)、下划线(_)和点(.)，禁止使用 / 等特殊字符',
                '【文件定位】仅支持四种类型：主合同、补充协议、解除协议、框架协议（留空默认为"主合同"）',
                '【关联规则】补充协议或解除协议必须填写"关联主合同编号"，关联已存在的主合同',
                '【合同类型】第11列的合同类型用于描述合同性质，如服务类、货物类、工程类等',
                '【合同来源】可选值：采购合同、直接签订（留空默认为"采购合同"）',
                '【项目关联】项目编码字段用于关联已存在的项目，必须填写系统中已存在的项目编码',
                '【采购关联】关联采购编号字段用于关联已存在的采购记录，如无采购可留空',
                '【联系信息】甲乙方的法定代表人、联系人、负责人信息均为可选字段，建议填写完整以便管理',
                '【日期格式】合同签订日期、履约担保退回时间等日期字段统一使用 YYYY-MM-DD 格式',
                '【金额格式】含税签约合同价仅填写数字（可带小数），单位为元，例如：2500000.00',
                '【说明】本模板说明行可保留或删除，不影响导入。导入时系统会自动跳过说明行。',
            ],
        },
    },
    'payment': {
        'long': {
            'filename': 'payment_import_template_long.csv',
            'headers': [
                '项目编码',
                '序号',
                '付款编号',
                '关联合同编号',
                '实付金额(元)',
                '付款日期',
                '结算价（元）',
                '是否办理结算',
                '模板说明',
            ],
            'notes': [
                '【必填字段】关联合同编号*、实付金额*、付款日期*（标记*号的为必填字段，不能为空）',
                '【编码规则】付款编号可留空由系统自动生成；如手动填写需遵守编号格式限制（禁止 / 等特殊字符）',
                '【合同关联】关联合同编号必须填写系统中已存在的合同编号或合同序号',
                '【日期格式】付款日期必须使用 YYYY-MM-DD 格式，例如：2025-10-20',
                '【金额格式】实付金额和结算价仅填写数字（可带小数），单位为元，例如：500000.00',
                '【结算标记】是否办理结算可填写：是、否、true、false（留空默认为"否"）',
                '【结算价说明】如果该笔付款是结算付款，需在"结算价"栏填写最终结算金额',
                '【说明】本模板说明行可保留或删除，不影响导入。导入时系统会自动跳过说明行。',
            ],
        },
        'wide': {
            'filename': 'payment_import_template_wide.csv',
            'headers': [
                '合同编号或序号',
                '结算价（元）',
                '是否办理结算',
            ] + [f'{year}年{month}月' for year in range(BASE_YEAR, get_current_year() + 2) for month in range(1, 13)] + ['模板说明'],
            'notes': [
                '【宽表格式】第1列填写合同编号或合同序号，后续月份列填写当期付款金额',
                '【月份范围】已预设2019年1月至2025年12月共84个月份列，覆盖常用时间范围',
                '【金额填写】每个月份列中填写当月的付款金额，单位为元，仅填写数字',
                '【结算信息】如某合同已办理结算，在"结算价"和"是否办理结算"列填写相应信息',
                '【留空规则】无付款的月份留空即可，不影响导入',
                '【说明】本模板说明行可保留或删除，不影响导入。导入时系统会自动跳过说明行。',
            ],
        },
    },
    'evaluation': {
        'long': {
            'filename': 'supplier_evaluation_import_template_long.csv',
            'headers': [
                '项目编码',
                '序号',
                '评价编号',
                '关联合同编号',
                '供应商名称',
                '评价日期区间',
                '评价人员',
                '评分',
                '评价类型',
                '模板说明',
            ],
            'notes': [
                '【必填字段】评价编号*、关联合同编号*、供应商名称*（标记*号的为必填字段，不能为空）',
                '【编码规则】评价编号须遵守编号格式限制（禁止 / 等特殊字符），推荐格式：HT2024-001-PJ01',
                '【合同关联】关联合同编号必须填写系统中已存在的合同编号',
                '【评分范围】评分范围为 0-100 之间的数字，可带小数（如：85.5），可留空',
                '【评价类型】建议填写：履约过程评价、末次评价、阶段性评价等',
                '【日期区间】评价日期区间格式示例：2024年1-6月、2024年上半年、2024Q1等',
                '【说明】本模板说明行可保留或删除，不影响导入。导入时系统会自动跳过说明行。',
            ],
        },
        'wide': {
            'filename': 'supplier_evaluation_import_template_wide.csv',
            'headers': [
                '关联合同编号',
                '供应商名称',
            ] + [f'{year}年{half}' for year in range(BASE_YEAR, get_current_year() + 2) for half in ['上半年', '下半年']] + ['模板说明'],
            'notes': [
                '【宽表格式】第1列填写合同编号，第2列填写供应商名称',
                '【评价周期】已预设2019年至2025年，每年上下半年共14个评价周期列',
                '【评分填写】每个周期列中填写对应时期的评分（0-100），可保留一位或两位小数',
                '【留空规则】如某时期暂无评价，对应单元格可留空',
                '【说明】本模板说明行可保留或删除，不影响导入。导入时系统会自动跳过说明行。',
            ],
        },
    },
}


def _get_page_size(request, default=20, max_size=200):
    """解析分页大小，限制范围避免异常输入。"""
    try:
        size = int(request.GET.get('page_size', default))
    except (TypeError, ValueError):
        return default
    return max(1, min(size, max_size))


def dashboard(request):
    """数据概览页面"""
    global_filters = _resolve_global_filters(request)
    year_filter = global_filters['year_filter']
    project_scope = Project.objects.all()
    if global_filters['project']:
        project_scope = project_scope.filter(project_code=global_filters['project'])

    procurement_scope = Procurement.objects.all()
    contract_scope = Contract.objects.all()
    payment_scope = Payment.objects.all()

    if global_filters['project']:
        procurement_scope = procurement_scope.filter(project__project_code=global_filters['project'])
        contract_scope = contract_scope.filter(project__project_code=global_filters['project'])
        payment_scope = payment_scope.filter(contract__project__project_code=global_filters['project'])

    if year_filter is not None:
        procurement_scope = procurement_scope.filter(result_publicity_release_date__year=year_filter)
        contract_scope = contract_scope.filter(signing_date__year=year_filter)
        payment_scope = payment_scope.filter(payment_date__year=year_filter)

    # 统计数据 - 每次访问时实时计算
    total_amount_yuan = contract_scope.aggregate(Sum('contract_amount'))['contract_amount__sum'] or 0
    stats = {
        'project_count': project_scope.count(),
        'procurement_count': procurement_scope.count(),
        'contract_count': contract_scope.count(),
        'total_amount': total_amount_yuan,
        'total_amount_wan': round(float(total_amount_yuan) / 10000, 2),  # 转换为万元
    }
    
    # 项目列表(前5个) - 实时计算每个项目的统计数据
    projects_queryset = project_scope.order_by('-created_at')[:5]
    projects = []
    for project in projects_queryset:
        project_procurements = Procurement.objects.filter(project=project)
        project_contracts = Contract.objects.filter(project=project)
        if year_filter is not None:
            project_procurements = project_procurements.filter(result_publicity_release_date__year=year_filter)
            project_contracts = project_contracts.filter(signing_date__year=year_filter)
        # 实时计算采购数量
        procurement_count = project_procurements.count()
        # 实时计算合同数量
        contract_count = project_contracts.count()
        # 实时计算合同总额
        contract_total = project_contracts.aggregate(
            total=Sum('contract_amount')
        )['total'] or 0
        
        # 添加计算后的属性
        setattr(project, 'procurement_count', procurement_count)
        setattr(project, 'contract_count', contract_count)
        setattr(project, 'contract_total', contract_total)
        projects.append(project)
    
    # 最近采购(前10个)
    recent_procurements = procurement_scope.select_related('project').order_by('-result_publicity_release_date', '-created_at')[:10]
    
    context = {
        'stats': stats,
        'projects': projects,
        'recent_procurements': recent_procurements,
        'global_selected_year': global_filters['year_value'],
        'global_selected_project': global_filters['project'],
    }
    return render(request, 'dashboard.html', context)


def project_list(request):
    """项目列表页面"""
    global_filters = _resolve_global_filters(request)
    # 获取过滤参数
    search_query = request.GET.get('q', '')
    # 自动检测搜索模式：如果包含逗号则为and，否则为or
    has_comma = ',' in search_query or '，' in search_query
    search_mode = request.GET.get('q_mode', 'and' if has_comma else 'or')
    status_filter = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20)
    
    # 高级筛选参数
    project_code_filter = request.GET.get('project_code', '')
    project_name_filter = request.GET.get('project_name', '')
    project_manager_filter = request.GET.get('project_manager', '')
    created_at_start = request.GET.get('created_at_start', '')
    created_at_end = request.GET.get('created_at_end', '')
    
    # 基础查询
    projects = Project.objects.all()
    if global_filters['project']:
        projects = projects.filter(project_code=global_filters['project'])
    if global_filters['year_filter'] is not None:
        projects = projects.filter(created_at__year=global_filters['year_filter'])
    
    # 搜索过滤
    search_mode_value = search_mode if search_mode in {'and', 'or'} else 'auto'
    projects = apply_multi_field_search(
        projects,
        ['project_code', 'project_name', 'project_manager'],
        search_query,
        mode=search_mode_value,
    )

    # 状态过滤
    if status_filter:
        projects = projects.filter(status=status_filter)

    # 高级筛选
    projects = apply_text_filter(projects, 'project_code', project_code_filter)
    projects = apply_text_filter(projects, 'project_name', project_name_filter)
    projects = apply_text_filter(projects, 'project_manager', project_manager_filter)
    if created_at_start:
        projects = projects.filter(created_at__gte=created_at_start)
    if created_at_end:
        projects = projects.filter(created_at__lte=created_at_end)

    contract_total_subquery = Contract.objects.filter(
        project=OuterRef('pk')
    ).values('project').annotate(
        total=Sum('contract_amount')
    ).values('total')

    projects = projects.annotate(
        procurement_count=Count('procurements', distinct=True),
        contract_count=Count('contracts', distinct=True),
        contract_total=Coalesce(
            Subquery(contract_total_subquery),
            Value(0, output_field=DecimalField(max_digits=15, decimal_places=2)),
        ),
    ).order_by('-created_at')

    # 分页
    paginator = Paginator(projects, page_size)
    page_obj = paginator.get_page(page)

    context = {
        'projects': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Project._meta.get_field('status').choices,
    }
    return render(request, 'project_list.html', context)


def project_detail(request, project_code):
    """项目详情页面"""
    project = get_object_or_404(Project, project_code=project_code)
    global_filters = _resolve_global_filters(request)
    year_filter = global_filters['year_filter']
    
    # 实时计算总数量
    procurement_scope = Procurement.objects.filter(project=project)
    contract_scope = Contract.objects.filter(project=project)
    payment_scope = Payment.objects.filter(contract__project=project)
    if year_filter is not None:
        procurement_scope = procurement_scope.filter(result_publicity_release_date__year=year_filter)
        contract_scope = contract_scope.filter(signing_date__year=year_filter)
        payment_scope = payment_scope.filter(payment_date__year=year_filter)

    procurement_count = procurement_scope.count()
    contract_count = contract_scope.count()
    
    # 获取所有相关数据用于统计
    all_procurements = procurement_scope
    all_contracts = contract_scope
    all_payments = payment_scope
    
    # 计算统计数据
    # 合同总额
    total_contract_amount = all_contracts.aggregate(Sum('contract_amount'))['contract_amount__sum'] or 0
    
    # 累计付款
    total_paid = all_payments.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
    
    # 付款笔数
    payment_count = all_payments.count()
    
    # 结算数量（综合统计：Settlement表 + Payment表中的结算标记）
    # 统计已结算的合同数量（去重）
    # 包括：1. Settlement表中有记录的合同  2. Payment表中标记为已结算的合同
    settlement_count = Contract.objects.filter(
        Q(project=project) & (
            Q(settlement__isnull=False) |  # Settlement表中有记录
            Q(payments__is_settled=True) |  # Payment中标记为已结算
            Q(payments__settlement_amount__isnull=False)  # Payment中有结算价
        )
    ).distinct().count()
    
    # 计算付款进度
    payment_progress = 0
    if total_contract_amount and total_contract_amount > 0:
        payment_progress = (total_paid / total_contract_amount) * 100
    
    # 最近的记录（各取10条）
    recent_procurements = all_procurements.order_by('-bid_opening_date')[:10]
    recent_contracts = all_contracts.order_by('-signing_date')[:10]
    recent_payments = all_payments.order_by('-payment_date')[:10]
    
    context = {
        'project': project,
        'procurement_count': procurement_count,  # 采购总数
        'contract_count': contract_count,  # 合同总数
        'procurements': recent_procurements,
        'contracts': recent_contracts,
        'total_contract_amount': total_contract_amount,
        'total_paid': total_paid,
        'payment_count': payment_count,
        'settlement_count': settlement_count,
        'payment_progress': payment_progress,
        'recent_payments': recent_payments,
    }
    return render(request, 'project_detail.html', context)


def contract_list(request):
    """合同列表页面"""
    from .filter_config import get_contract_filter_config

    global_filters = _resolve_global_filters(request)
    
    # 获取过滤参数
    search_query = request.GET.get('q', '')
    # 自动检测搜索模式：如果包含逗号则为and，否则为or
    has_comma = ',' in search_query or '，' in search_query
    search_mode = request.GET.get('q_mode', 'and' if has_comma else 'or')
    project_filter = request.GET.get('project', '') or global_filters['project']
    file_positioning_filter = request.GET.get('file_positioning', '')
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20)
    
    # 获取排序参数
    sort_field = request.GET.get('sort', 'signing_date')
    sort_order = request.GET.get('order', 'desc')
    
    # 高级筛选参数
    contract_code_filter = request.GET.get('contract_code', '')
    contract_sequence_filter = request.GET.get('contract_sequence', '')
    contract_name_filter = request.GET.get('contract_name', '')
    party_a_filter = request.GET.get('party_a', '')
    party_b_filter = request.GET.get('party_b', '')
    party_b_contact_filter = request.GET.get('party_b_contact', '')
    contract_officer_filter = request.GET.get('contract_officer', '')
    contract_source_filter = request.GET.get('contract_source', '')
    has_settlement_filter = request.GET.get('has_settlement', '')
    payment_ratio_min = request.GET.get('payment_ratio_min', '')
    payment_ratio_max = request.GET.get('payment_ratio_max', '')
    signing_date_start = request.GET.get('signing_date_start', '')
    signing_date_end = request.GET.get('signing_date_end', '')
    performance_guarantee_return_date_start = request.GET.get('performance_guarantee_return_date_start', '')
    performance_guarantee_return_date_end = request.GET.get('performance_guarantee_return_date_end', '')
    contract_amount_min = request.GET.get('contract_amount_min', '')
    contract_amount_max = request.GET.get('contract_amount_max', '')
    
    # 基础查询
    contracts = Contract.objects.select_related('project')

    # 年度筛选
    if global_filters['year_filter'] is not None:
        contracts = contracts.filter(signing_date__year=global_filters['year_filter'])
    
    # 搜索过滤
    search_mode_value = search_mode if search_mode in {'and', 'or'} else 'auto'
    contracts = apply_multi_field_search(
        contracts,
        ['contract_sequence', 'contract_name', 'party_b'],
        search_query,
        mode=search_mode_value,
    )
    
    # 项目过滤
    if project_filter:
        contracts = contracts.filter(project__project_code=project_filter)
    
    # 合同类型过滤
    if file_positioning_filter:
        contracts = contracts.filter(file_positioning=file_positioning_filter)
    
    contracts = apply_text_filter(contracts, 'contract_code', contract_code_filter)
    contracts = apply_text_filter(contracts, 'contract_sequence', contract_sequence_filter)
    contracts = apply_text_filter(contracts, 'contract_name', contract_name_filter)
    contracts = apply_text_filter(contracts, 'party_a', party_a_filter)
    contracts = apply_text_filter(contracts, 'party_b', party_b_filter)
    contracts = apply_text_filter(contracts, 'party_b_contact', party_b_contact_filter)
    contracts = apply_text_filter(contracts, 'contract_officer', contract_officer_filter)
    
    # 合同来源过滤
    if contract_source_filter:
        contracts = contracts.filter(contract_source=contract_source_filter)
    if signing_date_start:
        contracts = contracts.filter(signing_date__gte=signing_date_start)
    if signing_date_end:
        contracts = contracts.filter(signing_date__lte=signing_date_end)
    if performance_guarantee_return_date_start:
        contracts = contracts.filter(performance_guarantee_return_date__gte=performance_guarantee_return_date_start)
    if performance_guarantee_return_date_end:
        contracts = contracts.filter(performance_guarantee_return_date__lte=performance_guarantee_return_date_end)
    if contract_amount_min:
        contracts = contracts.filter(contract_amount__gte=contract_amount_min)
    if contract_amount_max:
        contracts = contracts.filter(contract_amount__lte=contract_amount_max)
    
    # 注意：is_settled和payment_ratio筛选依赖聚合结果，下方统一完成

    zero_decimal = Value(Decimal('0'), output_field=DecimalField(max_digits=18, decimal_places=2))
    contracts = contracts.annotate(
        total_paid_amount=Coalesce(Sum('payments__payment_amount'), zero_decimal),
        payment_count=Count('payments', distinct=True),
    )

    supplements_subquery = (
        Contract.objects.filter(parent_contract=OuterRef('pk'))
        .values('parent_contract')
        .annotate(total=Sum('contract_amount'))
        .values('total')
    )

    settlement_payment_subquery = (
        Payment.objects.filter(
            contract=OuterRef('pk'),
            is_settled=True,
            settlement_amount__isnull=False,
        )
        .order_by('-payment_date')
        .values('settlement_amount')[:1]
    )

    settlement_record_subquery = (
        Settlement.objects.filter(main_contract=OuterRef('pk')).values('final_amount')[:1]
    )

    contracts = contracts.annotate(
        supplements_total=Coalesce(
            Subquery(
                supplements_subquery,
                output_field=DecimalField(max_digits=18, decimal_places=2),
            ),
            zero_decimal,
        ),
        settlement_final_amount=Subquery(
            settlement_record_subquery,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        settlement_payment_amount=Subquery(
            settlement_payment_subquery,
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        has_settlement_record=Exists(Settlement.objects.filter(main_contract=OuterRef('pk'))),
        has_settlement_payment=Exists(
            Payment.objects.filter(contract=OuterRef('pk'), is_settled=True)
        ),
    )

    contracts = contracts.annotate(
        contract_plus_supplements=ExpressionWrapper(
            Coalesce(F('contract_amount'), zero_decimal)
            + Coalesce(F('supplements_total'), zero_decimal),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        settlement_amount=Coalesce(
            F('settlement_final_amount'),
            F('settlement_payment_amount'),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        has_settlement=Case(
            When(has_settlement_record=True, then=Value(True)),
            When(has_settlement_payment=True, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        ),
    )

    contracts = contracts.annotate(
        base_amount=Case(
            When(
                file_positioning='主合同',
                settlement_amount__isnull=False,
                then=F('settlement_amount'),
            ),
            When(file_positioning='主合同', then=F('contract_plus_supplements')),
            default=Coalesce(F('contract_amount'), zero_decimal),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    )

    contracts = contracts.annotate(
        payment_ratio=Case(
            When(
                base_amount__gt=0,
                then=ExpressionWrapper(
                    F('total_paid_amount')
                    * Value(100, output_field=DecimalField(max_digits=5, decimal_places=2))
                    / F('base_amount'),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
            ),
            default=Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

    # 应用排序
    sort_field_mapping = {
        'contract_sequence': 'contract_sequence',
        'contract_code': 'contract_code',
        'contract_name': 'contract_name',
        'party_b': 'party_b',
        'contract_amount': 'contract_amount',
        'signing_date': 'signing_date',
        'payment_ratio': 'payment_ratio',
    }
    
    # 验证排序字段
    if sort_field not in sort_field_mapping:
        sort_field = 'signing_date'
        sort_order = 'desc'
    
    # 构建排序字符串
    actual_sort_field = sort_field_mapping[sort_field]
    if sort_order.lower() == 'desc':
        contracts = contracts.order_by(f'-{actual_sort_field}')
    else:
        contracts = contracts.order_by(actual_sort_field)

    def _parse_decimal(value: str) -> Optional[Decimal]:
        if value in (None, ''):
            return None
        try:
            return Decimal(value)
        except (InvalidOperation, TypeError, ValueError):
            return None

    if has_settlement_filter:
        normalized = has_settlement_filter.lower()
        if normalized == 'true':
            contracts = contracts.filter(has_settlement=True)
        elif normalized == 'false':
            contracts = contracts.filter(has_settlement=False)

    min_ratio = _parse_decimal(payment_ratio_min)
    max_ratio = _parse_decimal(payment_ratio_max)
    if min_ratio is not None:
        contracts = contracts.filter(payment_ratio__gte=min_ratio)
    if max_ratio is not None:
        contracts = contracts.filter(payment_ratio__lte=max_ratio)

    paginator = Paginator(contracts, page_size)
    page_obj = paginator.get_page(page)

    contract_data = []
    for contract in page_obj.object_list:
        contract_data.append(
            {
                'contract': contract,
                'total_paid_amount': contract.total_paid_amount or Decimal('0'),
                'payment_count': contract.payment_count or 0,
                'has_settlement': bool(contract.has_settlement),
                'settlement_amount': contract.settlement_amount,
                'payment_ratio': contract.payment_ratio or Decimal('0'),
            }
        )

    # 创建新的分页对象，避免类型不匹配问题
    from django.core.paginator import Page
    # 创建新的分页对象，避免类型不匹配问题
    # 直接使用 contract_data，不修改 page_obj.object_list
    # 在模板中使用 contract_data 而不是 page_obj.object_list
    
    # 获取所有项目用于过滤
    projects = Project.objects.all()
    
    # 获取筛选配置
    filter_config = get_contract_filter_config(request)
    
    context = {
        'contracts': contract_data,  # 使用处理后的 contract_data
        'page_obj': page_obj,
        'projects': projects,
        'search_query': search_query,
        'project_filter': project_filter,
        'file_positioning_filter': file_positioning_filter,
        'file_positionings': Contract._meta.get_field('file_positioning').choices,
        'current_sort': sort_field,
        'current_order': sort_order,
        **filter_config,  # 添加筛选配置
    }
    return render(request, 'contract_list.html', context)


def contract_list_enhanced(request):
    """增强版合同列表页面 - 支持Vue.js交互"""
    # 获取所有合同数据（使用 only() 优化查询字段）
    contracts = Contract.objects.select_related('project').only(
        'contract_code', 'contract_name', 'file_positioning', 'contract_source',
        'party_b', 'contract_amount', 'signing_date',
        'project__project_code', 'project__project_name'
    ).order_by('-signing_date')
    
    # 转换为JSON格式（使用列表推导式提高性能）
    contracts_data = [
        {
            'contract_code': c.contract_code,
            'contract_name': c.contract_name,
            'file_positioning': c.file_positioning,
            'contract_source': c.contract_source,
            'party_b': c.party_b,
            'contract_amount': float(c.contract_amount) if c.contract_amount else None,
            'signing_date': c.signing_date.strftime('%Y-%m-%d') if c.signing_date else None,
            'project': {
                'project_code': c.project.project_code,
                'project_name': c.project.project_name
            } if c.project else None
        }
        for c in contracts
    ]
    
    # 获取所有项目（仅需要的字段）
    projects = Project.objects.only('project_code', 'project_name').order_by('project_name')
    projects_data = [
        {
            'project_code': p.project_code,
            'project_name': p.project_name
        }
        for p in projects
    ]
    
    context = {
        'contracts_json': json.dumps(contracts_data, ensure_ascii=False),
        'projects_json': json.dumps(projects_data, ensure_ascii=False),
    }
    return render(request, 'contract_list_enhanced.html', context)


def contract_detail(request, contract_code):
    """合同详情页面"""
    contract = get_object_or_404(Contract, contract_code=contract_code)
    
    # 获取相关付款记录
    payments = Payment.objects.filter(contract=contract).order_by('-payment_date')
    
    # 计算累计付款
    total_paid = payments.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
    
    # 计算付款进度
    payment_progress = 0
    if contract.contract_amount and contract.contract_amount > 0:
        payment_progress = (total_paid / contract.contract_amount) * 100
    
    # 获取关联的采购信息
    procurement = contract.procurement if contract.procurement else None
    
    # 获取结算信息（如果是主合同）
    from project.enums import FilePositioning
    settlement = None
    if contract.file_positioning == FilePositioning.MAIN_CONTRACT.value:
        try:
            settlement = getattr(contract, 'settlement', None)
        except:
            settlement = None
    
    # 获取补充协议（如果是主合同）
    supplements = []
    if contract.file_positioning == FilePositioning.MAIN_CONTRACT.value:
        supplements = getattr(contract, 'supplements', Contract.objects.none()).all().order_by('signing_date')
    
    # 获取履约评价
    evaluations = getattr(contract, 'evaluations', Contract.objects.none()).all() if hasattr(contract, 'evaluations') else []
    
    context = {
        'contract': contract,
        'payments': payments,
        'total_paid': total_paid,
        'payment_progress': payment_progress,
        'procurement': procurement,
        'settlement': settlement,
        'supplements': supplements,
        'evaluations': evaluations,
    }
    return render(request, 'contract_detail.html', context)


def procurement_list(request):
    """采购列表页面"""
    from .filter_config import get_procurement_filter_config

    global_filters = _resolve_global_filters(request)
    
    # 获取过滤参数
    search_query = request.GET.get('q', '')
    # 自动检测搜索模式：如果包含逗号则为and，否则为or
    has_comma = ',' in search_query or '，' in search_query
    search_mode = request.GET.get('q_mode', 'and' if has_comma else 'or')
    project_filter = request.GET.getlist('project')  # 改为多选
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20)
    
    # 高级筛选参数
    procurement_code_filter = request.GET.get('procurement_code', '')
    project_name_filter = request.GET.get('project_name', '')
    procurement_unit_filter = request.GET.get('procurement_unit', '')
    procurement_category_filter = request.GET.get('procurement_category', '')
    procurement_method_filter = request.GET.get('procurement_method', '')
    qualification_review_filter = request.GET.get('qualification_review_method', '')
    bid_evaluation_filter = request.GET.get('bid_evaluation_method', '')
    bid_awarding_filter = request.GET.get('bid_awarding_method', '')
    winning_bidder_filter = request.GET.get('winning_bidder', '')
    candidate_publicity_issue_filter = request.GET.get('candidate_publicity_issue', '')
    non_bidding_explanation_filter = request.GET.get('non_bidding_explanation', '')
    announcement_release_date_start = request.GET.get('announcement_release_date_start', '')
    announcement_release_date_end = request.GET.get('announcement_release_date_end', '')
    registration_deadline_start = request.GET.get('registration_deadline_start', '')
    registration_deadline_end = request.GET.get('registration_deadline_end', '')
    bid_opening_date_start = request.GET.get('bid_opening_date_start', '')
    bid_opening_date_end = request.GET.get('bid_opening_date_end', '')
    candidate_publicity_end_start = request.GET.get('candidate_publicity_end_date_start', '')
    candidate_publicity_end_end = request.GET.get('candidate_publicity_end_date_end', '')
    result_publicity_release_start = request.GET.get('result_publicity_release_date_start', '')
    result_publicity_release_end = request.GET.get('result_publicity_release_date_end', '')
    planned_completion_date_start = request.GET.get('planned_completion_date_start', '')
    planned_completion_date_end = request.GET.get('planned_completion_date_end', '')
    notice_issue_date_start = request.GET.get('notice_issue_date_start', '')
    notice_issue_date_end = request.GET.get('notice_issue_date_end', '')
    archive_date_start = request.GET.get('archive_date_start', '')
    archive_date_end = request.GET.get('archive_date_end', '')
    budget_amount_min = request.GET.get('budget_amount_min', '')
    budget_amount_max = request.GET.get('budget_amount_max', '')
    winning_amount_min = request.GET.get('winning_amount_min', '')
    winning_amount_max = request.GET.get('winning_amount_max', '')
    
    # 基础查询
    procurements = Procurement.objects.select_related('project')

    # 年度筛选（默认使用结果公示发布时间）
    if global_filters['year_filter'] is not None:
        procurements = procurements.filter(result_publicity_release_date__year=global_filters['year_filter'])
    
    # 搜索过滤
    search_mode_value = search_mode if search_mode in {'and', 'or'} else 'auto'
    procurements = apply_multi_field_search(
        procurements,
        ['procurement_code', 'project_name', 'procurement_category', 'winning_bidder'],
        search_query,
        mode=search_mode_value,
    )
    
    # 项目过滤 - 支持多选（过滤掉空字符串）
    project_filter = [p for p in project_filter if p]
    if not project_filter and global_filters['project']:
        project_filter = [global_filters['project']]
    if project_filter:
        procurements = procurements.filter(project__project_code__in=project_filter)
    
    procurements = apply_text_filter(procurements, 'procurement_code', procurement_code_filter)
    procurements = apply_text_filter(procurements, 'project_name', project_name_filter)
    procurements = apply_text_filter(procurements, 'procurement_unit', procurement_unit_filter)
    procurements = apply_text_filter(procurements, 'procurement_category', procurement_category_filter)
    procurements = apply_text_filter(procurements, 'procurement_method', procurement_method_filter)
    procurements = apply_text_filter(procurements, 'qualification_review_method', qualification_review_filter)
    procurements = apply_text_filter(procurements, 'bid_evaluation_method', bid_evaluation_filter)
    procurements = apply_text_filter(procurements, 'bid_awarding_method', bid_awarding_filter)
    procurements = apply_text_filter(procurements, 'winning_bidder', winning_bidder_filter)
    procurements = apply_text_filter(procurements, 'candidate_publicity_issue', candidate_publicity_issue_filter)
    procurements = apply_text_filter(procurements, 'non_bidding_explanation', non_bidding_explanation_filter)

    if announcement_release_date_start:
        procurements = procurements.filter(announcement_release_date__gte=announcement_release_date_start)
    if announcement_release_date_end:
        procurements = procurements.filter(announcement_release_date__lte=announcement_release_date_end)
    if registration_deadline_start:
        procurements = procurements.filter(registration_deadline__gte=registration_deadline_start)
    if registration_deadline_end:
        procurements = procurements.filter(registration_deadline__lte=registration_deadline_end)
    if bid_opening_date_start:
        procurements = procurements.filter(bid_opening_date__gte=bid_opening_date_start)
    if bid_opening_date_end:
        procurements = procurements.filter(bid_opening_date__lte=bid_opening_date_end)
    if candidate_publicity_end_start:
        procurements = procurements.filter(candidate_publicity_end_date__gte=candidate_publicity_end_start)
    if candidate_publicity_end_end:
        procurements = procurements.filter(candidate_publicity_end_date__lte=candidate_publicity_end_end)
    if result_publicity_release_start:
        procurements = procurements.filter(result_publicity_release_date__gte=result_publicity_release_start)
    if result_publicity_release_end:
        procurements = procurements.filter(result_publicity_release_date__lte=result_publicity_release_end)
    if planned_completion_date_start:
        procurements = procurements.filter(planned_completion_date__gte=planned_completion_date_start)
    if planned_completion_date_end:
        procurements = procurements.filter(planned_completion_date__lte=planned_completion_date_end)
    if notice_issue_date_start:
        procurements = procurements.filter(notice_issue_date__gte=notice_issue_date_start)
    if notice_issue_date_end:
        procurements = procurements.filter(notice_issue_date__lte=notice_issue_date_end)
    if archive_date_start:
        procurements = procurements.filter(archive_date__gte=archive_date_start)
    if archive_date_end:
        procurements = procurements.filter(archive_date__lte=archive_date_end)
    if budget_amount_min:
        procurements = procurements.filter(budget_amount__gte=budget_amount_min)
    if budget_amount_max:
        procurements = procurements.filter(budget_amount__lte=budget_amount_max)
    if winning_amount_min:
        procurements = procurements.filter(winning_amount__gte=winning_amount_min)
    if winning_amount_max:
        procurements = procurements.filter(winning_amount__lte=winning_amount_max)
    
    procurements = procurements.order_by('-result_publicity_release_date', '-bid_opening_date', '-created_at')
    
    # 分页处理
    paginator = Paginator(procurements, page_size)
    page_obj = paginator.get_page(page)
    
    # 获取筛选配置
    filter_config = get_procurement_filter_config(request)
    
    context = {
        'procurements': page_obj,
        'page_obj': page_obj,
        **filter_config,  # 添加筛选配置
    }
    return render(request, 'procurement_list.html', context)


def procurement_detail(request, procurement_code):
    """采购详情页面"""
    procurement = get_object_or_404(Procurement, procurement_code=procurement_code)
    
    # 获取相关合同
    contracts = Contract.objects.filter(
        procurement=procurement
    ).order_by('-signing_date')
    
    # 获取付款汇总数据
    # 获取该采购下所有合同的付款记录
    all_payments = Payment.objects.filter(
        contract__procurement=procurement
    ).order_by('-payment_date')
    
    # 计算付款统计数据
    total_paid = all_payments.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
    payment_count = all_payments.count()
    
    # 计算结算数量（综合统计：Settlement表 + Payment表中的结算标记）
    settlement_count = Contract.objects.filter(
        procurement=procurement
    ).filter(
        Q(settlement__isnull=False) |  # Settlement表中有记录
        Q(payments__is_settled=True) |  # Payment中标记为已结算
        Q(payments__settlement_amount__isnull=False)  # Payment中有结算价
    ).distinct().count()
    
    # 计算合同总额
    total_contract_amount = contracts.aggregate(Sum('contract_amount'))['contract_amount__sum'] or 0
    
    context = {
        'procurement': procurement,
        'contracts': contracts,
        'all_payments': all_payments[:10],  # 只显示最近10条
        'total_paid': total_paid,
        'payment_count': payment_count,
        'settlement_count': settlement_count,
        'total_contract_amount': total_contract_amount,
    }
    return render(request, 'procurement_detail.html', context)


def payment_list(request):
    """付款列表页面"""
    from .filter_config import get_payment_filter_config

    global_filters = _resolve_global_filters(request)
    
    # 获取过滤参数
    search_query = request.GET.get('q', '')
    # 自动检测搜索模式：如果包含逗号则为and，否则为or
    has_comma = ',' in search_query or '，' in search_query
    search_mode = request.GET.get('q_mode', 'and' if has_comma else 'or')
    project_filter = request.GET.getlist('project')  # 改为多选
    is_settled_filter = request.GET.getlist('is_settled')  # 改为多选
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20, max_size=1000)
    
    # 高级筛选参数
    payment_code_filter = request.GET.get('payment_code', '')
    contract_name_filter = request.GET.get('contract_name', '')
    payment_date_start = request.GET.get('payment_date_start', '')
    payment_date_end = request.GET.get('payment_date_end', '')
    payment_amount_min = request.GET.get('payment_amount_min', '')
    payment_amount_max = request.GET.get('payment_amount_max', '')
    
    # 基础查询
    payments = Payment.objects.select_related('contract', 'contract__project')

    # 年度筛选
    if global_filters['year_filter'] is not None:
        payments = payments.filter(payment_date__year=global_filters['year_filter'])
    
    # 搜索过滤
    search_mode_value = search_mode if search_mode in {'and', 'or'} else 'auto'
    payments = apply_multi_field_search(
        payments,
        ['payment_code', 'contract__contract_name'],
        search_query,
        mode=search_mode_value,
    )
    
    # 项目过滤 - 支持多选（过滤掉空字符串）
    project_filter = [p for p in project_filter if p]
    if not project_filter and global_filters['project']:
        project_filter = [global_filters['project']]
    if project_filter:
        payments = payments.filter(contract__project__project_code__in=project_filter)
    
    # 结算状态过滤 - 支持多选（过滤掉空字符串）
    is_settled_filter = [s for s in is_settled_filter if s]
    if is_settled_filter:
        is_settled_values = [v.lower() == 'true' for v in is_settled_filter]
        payments = payments.filter(is_settled__in=is_settled_values)
    
    payments = apply_text_filter(payments, 'payment_code', payment_code_filter)
    payments = apply_text_filter(payments, 'contract__contract_name', contract_name_filter)
    
    if payment_date_start:
        payments = payments.filter(payment_date__gte=payment_date_start)
    if payment_date_end:
        payments = payments.filter(payment_date__lte=payment_date_end)
    if payment_amount_min:
        payments = payments.filter(payment_amount__gte=payment_amount_min)
    if payment_amount_max:
        payments = payments.filter(payment_amount__lte=payment_amount_max)
    
    payments = payments.order_by('-payment_date')
    
    # 分页处理
    paginator = Paginator(payments, page_size)
    page_obj = paginator.get_page(page)
    
    # 获取筛选配置
    filter_config = get_payment_filter_config(request)
    
    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        **filter_config,  # 添加筛选配置
    }
    return render(request, 'payment_list.html', context)


def payment_detail(request, payment_code):
    """付款详情页面"""
    payment = get_object_or_404(Payment, payment_code=payment_code)
    contract = payment.contract
    
    # 获取该合同的所有付款记录
    all_payments = Payment.objects.filter(contract=contract).order_by('-payment_date')
    
    # 计算累计付款和付款进度
    total_paid = all_payments.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
    payment_progress = 0
    if contract.contract_amount and contract.contract_amount > 0:
        payment_progress = (total_paid / contract.contract_amount) * 100
    
    context = {
        'payment': payment,
        'contract': contract,
        'all_payments': all_payments,
        'total_paid': total_paid,
        'payment_progress': payment_progress,
    }
    return render(request, 'payment_detail.html', context)


@require_http_methods(["GET", "POST", "DELETE", "PUT"])
def database_management(request):
    """数据库管理：备份、恢复、清理"""
    default_db = settings.DATABASES.get('default', {})
    engine = default_db.get('ENGINE', '')
    db_name = default_db.get('NAME')
    db_path = None

    if engine.endswith('sqlite3') and db_name:
        db_path = Path(db_name)
        if not db_path.is_absolute():
            db_path = Path(settings.BASE_DIR) / db_name
        db_path = db_path.resolve()

    backups_dir = Path(settings.BASE_DIR) / 'backups' / 'database'
    backups_dir.mkdir(parents=True, exist_ok=True)

    def _format_size(num_bytes: int) -> str:
        size = float(num_bytes)
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        for unit in units:
            if size < 1024 or unit == units[-1]:
                return f'{size:.2f} {unit}'
            size /= 1024
        return f'{num_bytes} B'

    def _collect_db_stat(path: Path):
        if not path or not path.exists():
            return None
        stat = path.stat()
        modified_at = timezone.localtime(datetime.fromtimestamp(stat.st_mtime, tz=dt_timezone.utc))
        return {
            'path': str(path),
            'size_bytes': stat.st_size,
            'modified_at': modified_at,
            'size_display': _format_size(stat.st_size),
            'modified_display': modified_at.strftime('%Y-%m-%d %H:%M:%S'),
        }

    if request.method == "DELETE":
        # 处理删除备份的请求
        try:
            data = json.loads(request.body)
            file_name = data.get('file_name')
            if not file_name:
                return JsonResponse({'success': False, 'message': '未指定要删除的备份文件'}, status=400)
            
            backup_file = backups_dir / file_name
            if not backup_file.exists():
                return JsonResponse({'success': False, 'message': '备份文件不存在'}, status=404)
            
            # 删除备份文件
            backup_file.unlink()
            return JsonResponse({'success': True, 'message': f'备份文件 {file_name} 已删除'})
        except Exception as exc:
            return JsonResponse({'success': False, 'message': f'删除失败：{exc}'}, status=500)
    
    if request.method == "PUT":
        # 处理重命名备份的请求
        try:
            data = json.loads(request.body)
            old_name = data.get('old_name')
            new_name = data.get('new_name', '').strip()
            
            if not old_name or not new_name:
                return JsonResponse({'success': False, 'message': '请提供原文件名和新文件名'}, status=400)
            
            # 验证并清理新文件名
            import re
            clean_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)
            clean_name = clean_name.strip('. ')
            
            if not clean_name:
                return JsonResponse({'success': False, 'message': '新文件名无效'}, status=400)
            
            # 确保文件名以 .sqlite3 结尾
            if not clean_name.lower().endswith('.sqlite3'):
                clean_name += '.sqlite3'
            
            old_file = backups_dir / old_name
            new_file = backups_dir / clean_name
            
            if not old_file.exists():
                return JsonResponse({'success': False, 'message': '原备份文件不存在'}, status=404)
            
            if new_file.exists():
                return JsonResponse({'success': False, 'message': f'文件名已存在：{clean_name}'}, status=400)
            
            # 重命名文件
            old_file.rename(new_file)
            return JsonResponse({'success': True, 'message': f'备份文件已重命名为：{clean_name}'})
        except Exception as exc:
            return JsonResponse({'success': False, 'message': f'重命名失败：{exc}'}, status=500)
    
    if request.method == "POST":
        action = request.POST.get('action')
        try:
            if action == 'clear':
                # 保存当前用户信息
                from django.contrib.auth import get_user_model
                User = get_user_model()
                current_user_id = request.user.id
                current_username = request.user.username
                is_superuser = request.user.is_superuser
                is_staff = request.user.is_staff
                
                if engine.endswith('sqlite3') and db_path:
                    connections.close_all()
                    if db_path.exists():
                        # 清理SQLite残留文件，避免锁定
                        related_suffixes = ['', '-journal', '-wal', '-shm']
                        for suffix in related_suffixes:
                            target = db_path if suffix == '' else db_path.with_name(db_path.name + suffix)
                            if target.exists():
                                target.unlink()
                    call_command('migrate', interactive=False, verbosity=0)
                    
                    # 重新创建管理员用户
                    try:
                        user = User.objects.create_superuser(
                            username=current_username,
                            email='admin@example.com',
                            password='admin123',  # 默认密码
                            is_staff=True,
                            is_superuser=True
                        )
                        # 重新登录用户
                        from django.contrib.auth import login
                        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                        messages.success(request, '数据库已重置并重新迁移结构。管理员账户已重新创建（用户名：{}，默认密码：admin123）。'.format(current_username))
                    except Exception as e:
                        messages.warning(request, f'数据库已重置，但重新创建管理员账户失败：{e}。请手动创建管理员账户。')
                else:
                    call_command('flush', interactive=False, verbosity=0)
                    messages.success(request, '数据库数据已清空。')
            elif action == 'backup':
                if not db_path:
                    raise ValueError('当前数据库引擎不支持文件级备份。')
                if not db_path.exists():
                    raise FileNotFoundError('未找到数据库文件，无法备份。')
                
                # 获取用户输入的备份名称和描述
                backup_name = request.POST.get('backup_name', '').strip()
                backup_description = request.POST.get('backup_description', '').strip()
                
                # 验证备份名称
                if not backup_name:
                    raise ValueError('请输入备份名称。')
                
                # 清理文件名，移除不合法字符
                import re
                # 移除文件名中的非法字符
                clean_name = re.sub(r'[<>:"/\\|?*]', '_', backup_name)
                # 移除首尾空格和点
                clean_name = clean_name.strip('. ')
                # 如果清理后为空，使用默认名称
                if not clean_name:
                    clean_name = f'backup-{timezone.now().strftime("%Y%m%d%H%M%S")}'
                
                # 确保文件名以 .sqlite3 结尾
                if not clean_name.lower().endswith('.sqlite3'):
                    clean_name += '.sqlite3'
                
                # 检查文件是否已存在
                backup_file = backups_dir / clean_name
                if backup_file.exists():
                    raise ValueError(f'备份文件已存在：{clean_name}')
                
                connections.close_all()
                shutil.copy2(db_path, backup_file)
                
                # 构建成功消息
                success_message = f'备份成功：{clean_name}'
                if backup_description:
                    success_message += f'（描述：{backup_description}）'
                
                messages.success(request, success_message)
            elif action == 'restore':
                if not db_path:
                    raise ValueError('当前数据库引擎不支持文件级恢复。')
                file_name = request.POST.get('file_name')
                if not file_name:
                    raise ValueError('请选择要恢复的备份文件。')
                source_file = backups_dir / file_name
                if not source_file.exists():
                    raise FileNotFoundError('备份文件不存在，请刷新后重试。')
                
                # 保存当前用户信息和会话key
                from django.contrib.auth import get_user_model
                User = get_user_model()
                current_username = request.user.username
                session_key = request.session.session_key
                
                # 关闭所有数据库连接
                connections.close_all()
                
                # 恢复备份文件
                shutil.copy2(source_file, db_path)
                
                # 清除当前会话缓存，强制重新从数据库读取
                from django.core.cache import cache
                cache.clear()
                
                # 尝试重新登录用户
                try:
                    from django.contrib.auth import login
                    # 检查用户是否在恢复的数据库中存在
                    user = User.objects.filter(username=current_username).first()
                    if user:
                        # 删除旧的会话数据
                        request.session.flush()
                        # 强制登录恢复的用户，创建新会话
                        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                        messages.success(request, f'恢复成功，已加载备份：{file_name}。您已自动重新登录。')
                    else:
                        # 用户不在备份中，清除会话
                        request.session.flush()
                        messages.warning(request, f'恢复成功，已加载备份：{file_name}。您的账户在此备份中不存在，请使用备份中的管理员账户登录。')
                except Exception as e:
                    # 出错时也清除会话
                    request.session.flush()
                    messages.warning(request, f'恢复成功，已加载备份：{file_name}。自动登录失败：{e}。请手动重新登录。')
            else:
                messages.error(request, '未知操作，请刷新后重试。')
        except Exception as exc:
            messages.error(request, f'操作失败：{exc}')
        return redirect('database_management')

    backups = []
    if backups_dir.exists():
        for file in sorted(backups_dir.glob('*.sqlite3'), key=lambda f: f.stat().st_mtime, reverse=True):
            stat = file.stat()
            backups.append({
                'name': file.name,
                'size_bytes': stat.st_size,
                'size_display': _format_size(stat.st_size),
                'modified_at': timezone.localtime(datetime.fromtimestamp(stat.st_mtime, tz=dt_timezone.utc)),
            })
    for backup in backups:
        backup['modified_display'] = backup['modified_at'].strftime('%Y-%m-%d %H:%M:%S')

    context = {
        'engine': engine,
        'db_stat': _collect_db_stat(db_path) if db_path else None,
        'backups': backups,
        'supports_file_ops': bool(db_path),
    }
    return render(request, 'database_management.html', context)


@require_http_methods(['GET'])
def download_import_template(request):
    """下载各模块导入模板（包含字段限制说明）。"""
    module = request.GET.get('module', 'project')
    mode = request.GET.get('mode', 'long')

    module_config = IMPORT_TEMPLATE_DEFINITIONS.get(module)
    if not module_config:
        return HttpResponse('不支持的导入模块', status=400)

    template_config = module_config.get(mode)
    if not template_config:
        return HttpResponse('当前模块暂不支持该模板类型', status=400)

    headers = template_config['headers']
    note_column = template_config.get('note_column', '模板说明')

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)

    for note in template_config.get('notes', []):
        note_text = str(note).strip()
        row = []
        for header in headers:
            row.append(note_text if header == note_column else '')
        writer.writerow(row)

    csv_bytes = buffer.getvalue().encode('utf-8-sig')
    response = HttpResponse(csv_bytes, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{template_config["filename"]}"'
    response['Content-Length'] = str(len(csv_bytes))
    return response


@csrf_exempt
@require_POST
def batch_delete_contracts(request):
    """批量删除合同"""
    try:
        data = json.loads(request.body)
        contract_codes = data.get('ids', [])
        
        if not contract_codes:
            return JsonResponse({'success': False, 'message': '未选择要删除的合同'})
        
        # 执行删除操作
        deleted_count = Contract.objects.filter(contract_code__in=contract_codes).delete()[0]
        
        return JsonResponse({
            'success': True,
            'message': f'成功删除 {deleted_count} 个合同',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败: {str(e)}'})


@csrf_exempt
@require_POST
def batch_delete_payments(request):
    """批量删除付款记录"""
    try:
        data = json.loads(request.body)
        payment_codes = data.get('ids', [])
        
        if not payment_codes:
            return JsonResponse({'success': False, 'message': '未选择要删除的付款记录'})
        
        # 执行删除操作
        deleted_count = Payment.objects.filter(payment_code__in=payment_codes).delete()[0]
        
        return JsonResponse({
            'success': True,
            'message': f'成功删除 {deleted_count} 条付款记录',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败: {str(e)}'})


@csrf_exempt
@require_POST
def batch_delete_procurements(request):
    """批量删除采购项目"""
    try:
        data = json.loads(request.body)
        procurement_codes = data.get('ids', [])
        
        if not procurement_codes:
            return JsonResponse({'success': False, 'message': '未选择要删除的采购项目'})
        
        # 执行删除操作
        deleted_count = Procurement.objects.filter(procurement_code__in=procurement_codes).delete()[0]
        
        return JsonResponse({
            'success': True,
            'message': f'成功删除 {deleted_count} 个采购项目',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败: {str(e)}'})


@csrf_exempt
@require_POST
def import_data(request):
    """通用数据导入接口"""
    try:
        # 获取上传的文件
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'message': '未找到上传文件'})
        
        uploaded_file = request.FILES['file']
        module = request.POST.get('module', 'project')  # project/procurement/contract/payment
        
        # 验证文件类型
        if not uploaded_file.name.endswith('.csv'):
            return JsonResponse({'success': False, 'message': '只支持CSV文件格式'})
        
        # 保存临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        try:
            # 自动检测导入模式（长表 vs 宽表）
            import csv
            import chardet
            
            # 检测文件编码
            with open(tmp_file_path, 'rb') as f:
                raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                detected_encoding = result.get('encoding', 'utf-8-sig')
                if detected_encoding and result.get('confidence', 0) > 0.7:
                    encoding_map = {'GB2312': 'gbk', 'ISO-8859-1': 'latin1', 'ascii': 'utf-8'}
                    detected_encoding = encoding_map.get(detected_encoding, detected_encoding)
                else:
                    detected_encoding = 'utf-8-sig'
            
            # 读取第一行判断列数
            with open(tmp_file_path, 'r', encoding=detected_encoding) as f:
                reader = csv.reader(f)
                header = next(reader)
                column_count = len(header)
            
            # 判断是长表还是宽表
            # 付款和评价模块：超过10列认为是宽表（通常宽表有几十个日期列）
            # 其他模块：默认使用长表
            import_mode = 'long'
            if module in ['payment', 'evaluation'] and column_count > 10:
                import_mode = 'wide'
            
            # 调用导入命令
            out = StringIO()
            call_command(
                'import_excel',
                tmp_file_path,
                '--module', module,
                '--mode', import_mode,
                '--conflict-mode', 'update',
                stdout=out,
                stderr=out
            )
            
            output = out.getvalue()
            
            # 清理ANSI转义序列的辅助函数
            import re
            def clean_ansi(text):
                """移除ANSI转义序列"""
                ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
                return ansi_escape.sub('', text)
            
            # 解析输出统计信息
            stats = {
                'total': 0,
                'success': 0,
                'failed': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0
            }
            
            # 从输出中提取统计数据（清理ANSI转义序列后）
            cleaned_output = clean_ansi(output)
            for line in cleaned_output.split('\n'):
                if '总行数:' in line:
                    try:
                        stats['total'] = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif '成功:' in line:
                    try:
                        stats['success'] = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif '失败:' in line:
                    try:
                        stats['failed'] = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif '新增记录:' in line:
                    try:
                        stats['created'] = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif '更新记录:' in line:
                    try:
                        stats['updated'] = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif '跳过记录:' in line:
                    try:
                        stats['skipped'] = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
            
            # 提取错误信息
            errors = []
            in_error_section = False
            for line in output.split('\n'):
                if '错误详情:' in line:
                    in_error_section = True
                    continue
                if in_error_section and line.strip().startswith('-'):
                    errors.append(line.strip()[2:])  # 移除 "- " 前缀
                elif in_error_section and '===' in line:
                    break
            
            return JsonResponse({
                'success': True,
                'message': f'导入完成！成功 {stats["success"]} 条，失败 {stats["failed"]} 条',
                'stats': stats,
                'errors': errors[:10],  # 只返回前10条错误
                'output': output
            })
            
        finally:
            # 清理临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'导入失败: {str(e)}'
        })


@csrf_exempt
@require_POST
def batch_delete_projects(request):
    """批量删除项目"""
    try:
        data = json.loads(request.body)
        project_codes = data.get('ids', [])
        
        if not project_codes:
            return JsonResponse({'success': False, 'message': '未选择要删除的项目'})
        
        # 执行删除操作
        deleted_count = Project.objects.filter(project_code__in=project_codes).delete()[0]
        
        return JsonResponse({
            'success': True,
            'message': f'成功删除 {deleted_count} 个项目',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败: {str(e)}'})


@require_http_methods(['GET', 'POST'])
def export_project_data(request):
    """导出项目数据为Excel文件"""
    import zipfile
    from datetime import datetime
    from io import BytesIO
    
    if request.method == 'GET':
        # 显示项目选择页面
        projects = Project.objects.all().order_by('project_name')
        
        context = {
            'projects': projects,
            'page_title': '导出项目数据',
        }
        return render(request, 'export_project_selection.html', context)
    
    # POST请求 - 执行导出
    try:
        # 获取选中的项目编码列表
        project_codes = request.POST.getlist('project_codes')
        
        if not project_codes:
            return JsonResponse({
                'success': False,
                'message': '请至少选择一个项目'
            }, status=400)
        
        # 获取选中的项目
        projects = Project.objects.filter(project_code__in=project_codes)
        
        if not projects.exists():
            return JsonResponse({
                'success': False,
                'message': '未找到选中的项目'
            }, status=404)
        
        # 如果只有一个项目，直接返回该项目的Excel文件
        if len(projects) == 1:
            project = projects.first()
            if project is None:
                return JsonResponse({
                    'success': False,
                    'message': '项目不存在'
                }, status=404)
            excel_file = _generate_project_excel(project, request.user)
            filename = f"{project.project_name}_数据导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            response = HttpResponse(
                excel_file.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        # 多个项目 - 为每个项目生成独立的Excel工作簿，打包成ZIP
        zip_buffer = BytesIO()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for project in projects:
                # 为每个项目生成独立的Excel文件
                excel_file = _generate_project_excel(project, request.user)
                # 使用项目名称作为文件名
                filename = f"{project.project_name}_数据导出_{timestamp}.xlsx"
                zip_file.writestr(filename, excel_file.getvalue())
        
        zip_buffer.seek(0)
        zip_filename = f"项目数据导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        response = HttpResponse(
            zip_buffer.getvalue(),
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'导出失败: {str(e)}'
        }, status=500)


def _generate_project_excel(project, user):
    """为单个项目生成Excel文件"""
    import pandas as pd
    from datetime import datetime
    from io import BytesIO
    
    try:
        # 创建Excel写入器
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # 项目工作表（单个项目）
            project_data = [{
                '项目编码': project.project_code,
                '项目名称': project.project_name,
                '项目描述': project.description or '',
                '项目负责人': project.project_manager or '',
                '项目状态': project.status,
                '备注': project.remarks or '',
                '创建时间': project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else '',
                '更新时间': project.updated_at.strftime('%Y-%m-%d %H:%M:%S') if project.updated_at else '',
            }]
            
            df_projects = pd.DataFrame(project_data)
            df_projects.to_excel(writer, sheet_name='项目信息', index=False)
            
            # 采购工作表
            procurement_data = []
            procurements = Procurement.objects.filter(project=project)
            for procurement in procurements:
                procurement_data.append({
                    '项目编码': project.project_code,
                    '项目名称': project.project_name,
                    '招采编号': procurement.procurement_code,
                    '采购项目名称': procurement.project_name,
                    '采购单位': procurement.procurement_unit or '',
                    '中标单位': procurement.winning_bidder or '',
                    '中标单位联系人及方式': procurement.winning_contact or '',
                    '采购方式': procurement.procurement_method or '',
                    '采购类别': procurement.procurement_category or '',
                    '采购预算金额(元)': float(procurement.budget_amount) if procurement.budget_amount else 0,
                    '采购控制价（元）': float(procurement.control_price) if procurement.control_price else 0,
                    '中标金额（元）': float(procurement.winning_amount) if procurement.winning_amount else 0,
                    '计划结束采购时间': procurement.planned_completion_date.strftime('%Y-%m-%d') if procurement.planned_completion_date else '',
                    '候选人公示结束时间': procurement.candidate_publicity_end_date.strftime('%Y-%m-%d') if procurement.candidate_publicity_end_date else '',
                    '结果公示发布时间': procurement.result_publicity_release_date.strftime('%Y-%m-%d') if procurement.result_publicity_release_date else '',
                    '中标通知书发放日期': procurement.notice_issue_date.strftime('%Y-%m-%d') if procurement.notice_issue_date else '',
                    '采购经办人': procurement.procurement_officer or '',
                    '需求部门': procurement.demand_department or '',
                    '申请人联系电话（需求部门）': procurement.demand_contact or '',
                    '采购需求书审批完成日期（OA）': procurement.requirement_approval_date.strftime('%Y-%m-%d') if procurement.requirement_approval_date else '',
                    '采购平台': procurement.procurement_platform or '',
                    '资格审查方式': procurement.qualification_review_method or '',
                    '评标谈判方式': procurement.bid_evaluation_method or '',
                    '定标方法': procurement.bid_awarding_method or '',
                    '公告发布时间': procurement.announcement_release_date.strftime('%Y-%m-%d') if procurement.announcement_release_date else '',
                    '报名截止时间': procurement.registration_deadline.strftime('%Y-%m-%d') if procurement.registration_deadline else '',
                    '开标时间': procurement.bid_opening_date.strftime('%Y-%m-%d') if procurement.bid_opening_date else '',
                    '评标委员会成员': procurement.evaluation_committee or '',
                    '投标担保形式及金额（元）': procurement.bid_guarantee or '',
                    '投标担保退回日期': procurement.bid_guarantee_return_date.strftime('%Y-%m-%d') if procurement.bid_guarantee_return_date else '',
                    '履约担保形式及金额（元）': procurement.performance_guarantee or '',
                    '候选人公示期质疑情况': procurement.candidate_publicity_issue or '',
                    '应招未招说明（由公开转单一或邀请的情况）': procurement.non_bidding_explanation or '',
                    '资料归档日期': procurement.archive_date.strftime('%Y-%m-%d') if procurement.archive_date else '',
                    '创建时间': procurement.created_at.strftime('%Y-%m-%d %H:%M:%S') if procurement.created_at else '',
                    '更新时间': procurement.updated_at.strftime('%Y-%m-%d %H:%M:%S') if procurement.updated_at else '',
                })
            
            if procurement_data:
                df_procurement = pd.DataFrame(procurement_data)
                df_procurement.to_excel(writer, sheet_name='采购信息', index=False)
            
            # 合同工作表
            contract_data = []
            contracts = Contract.objects.filter(project=project)
            for contract in contracts:
                # 获取累计付款金额
                total_paid = contract.get_total_paid_amount()
                payment_count = contract.get_payment_count()
                
                contract_data.append({
                    '项目编码': project.project_code,
                    '项目名称': project.project_name,
                    '关联采购编号': contract.procurement.procurement_code if contract.procurement else '',
                    '合同类型': contract.file_positioning,
                    '合同来源': contract.contract_source,
                    '关联主合同编号': contract.parent_contract.contract_code if contract.parent_contract else '',
                    '序号': contract.contract_sequence or '',
                    '合同序号': contract.contract_sequence or '',
                    '合同编号': contract.contract_code,
                    '合同名称': contract.contract_name,
                    '合同签订经办人': contract.contract_officer or '',
                    '甲方': contract.party_a or '',
                    '乙方': contract.party_b or '',
                    '含税签约合同价（元）': float(contract.contract_amount) if contract.contract_amount else 0,
                    '合同签订日期': contract.signing_date.strftime('%Y-%m-%d') if contract.signing_date else '',
                    '甲方法定代表人及联系方式': contract.party_a_legal_representative or '',
                    '甲方联系人及联系方式': contract.party_a_contact_person or '',
                    '甲方负责人及联系方式': contract.party_a_manager or '',
                    '乙方法定代表人及联系方式': contract.party_b_legal_representative or '',
                    '乙方联系人及联系方式': contract.party_b_contact_person or '',
                    '乙方负责人及联系方式': contract.party_b_manager or '',
                    '合同工期/服务期限': contract.duration or '',
                    '支付方式': contract.payment_method or '',
                    '履约担保退回时间': contract.performance_guarantee_return_date.strftime('%Y-%m-%d') if contract.performance_guarantee_return_date else '',
                    '资料归档日期': contract.archive_date.strftime('%Y-%m-%d') if contract.archive_date else '',
                    '累计付款金额（元）': total_paid,
                    '付款笔数': payment_count,
                    '付款比例': f"{contract.get_payment_ratio():.2f}%" if contract.get_payment_ratio() > 0 else '0%',
                    '创建时间': contract.created_at.strftime('%Y-%m-%d %H:%M:%S') if contract.created_at else '',
                    '更新时间': contract.updated_at.strftime('%Y-%m-%d %H:%M:%S') if contract.updated_at else '',
                })
            
            if contract_data:
                df_contract = pd.DataFrame(contract_data)
                df_contract.to_excel(writer, sheet_name='合同信息', index=False)
            
            # 付款工作表
            payment_data = []
            for contract in contracts:
                payments = Payment.objects.filter(contract=contract)
                for payment in payments:
                    payment_data.append({
                        '项目编码': project.project_code,
                        '项目名称': project.project_name,
                                '关联合同编号': contract.contract_code,
                                '合同名称': contract.contract_name,
                                '付款编号': payment.payment_code,
                                '实付金额(元)': float(payment.payment_amount),
                                '付款日期': payment.payment_date.strftime('%Y-%m-%d'),
                                '结算价（元）': float(payment.settlement_amount) if payment.settlement_amount else 0,
                                '是否办理结算': '是' if payment.is_settled else '否',
                        '创建时间': payment.created_at.strftime('%Y-%m-%d %H:%M:%S') if payment.created_at else '',
                        '更新时间': payment.updated_at.strftime('%Y-%m-%d %H:%M:%S') if payment.updated_at else '',
                    })
            
            if payment_data:
                df_payment = pd.DataFrame(payment_data)
                df_payment.to_excel(writer, sheet_name='付款信息', index=False)
            
            # 结算工作表
            settlement_data = []
            main_contracts = Contract.objects.filter(project=project, file_positioning=FilePositioning.MAIN_CONTRACT.value)
            for contract in main_contracts:
                try:
                    settlement = getattr(contract, 'settlement', None)
                    if settlement:
                        settlement_data.append({
                            '项目编码': project.project_code,
                            '项目名称': project.project_name,
                                    '关联合同编号': contract.contract_code,
                                    '合同名称': contract.contract_name,
                                    '结算编号': settlement.settlement_code,
                                    '最终结算金额(元)': float(settlement.final_amount),
                                    '完成日期': settlement.completion_date.strftime('%Y-%m-%d') if settlement.completion_date else '',
                                    '结算备注': settlement.remarks or '',
                                    '创建时间': settlement.created_at.strftime('%Y-%m-%d %H:%M:%S') if settlement.created_at else '',
                            '更新时间': settlement.updated_at.strftime('%Y-%m-%d %H:%M:%S') if settlement.updated_at else '',
                        })
                except:
                    # 如果没有结算记录，跳过
                    pass
            
            if settlement_data:
                df_settlement = pd.DataFrame(settlement_data)
                df_settlement.to_excel(writer, sheet_name='结算信息', index=False)
            
            # 供应商评价工作表
            evaluation_data = []
            for contract in contracts:
                evaluations = SupplierEvaluation.objects.filter(contract=contract)
                for evaluation in evaluations:
                    evaluation_data.append({
                        '项目编码': project.project_code,
                        '项目名称': project.project_name,
                                '关联合同编号': contract.contract_code,
                                '合同名称': contract.contract_name,
                                '评价编号': evaluation.evaluation_code,
                                '供应商名称': evaluation.supplier_name,
                                '评价日期区间': evaluation.evaluation_period or '',
                                '评价人员': evaluation.evaluator or '',
                                '评分': float(evaluation.score) if evaluation.score else 0,
                                '评价类型': evaluation.evaluation_type or '',
                        '创建时间': evaluation.created_at.strftime('%Y-%m-%d %H:%M:%S') if evaluation.created_at else '',
                        '更新时间': evaluation.updated_at.strftime('%Y-%m-%d %H:%M:%S') if evaluation.updated_at else '',
                    })
            
            if evaluation_data:
                df_evaluation = pd.DataFrame(evaluation_data)
                df_evaluation.to_excel(writer, sheet_name='供应商评价', index=False)
            
            # 添加导出信息工作表
            export_info = [{
                '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '导出人': user.username if user.is_authenticated else '系统',
                '项目编码': project.project_code,
                '项目名称': project.project_name,
                '采购总数': len(procurement_data),
                '合同总数': len(contract_data),
                '付款总数': len(payment_data),
                '结算总数': len(settlement_data),
                '评价总数': len(evaluation_data),
            }]
            
            df_export_info = pd.DataFrame(export_info)
            df_export_info.to_excel(writer, sheet_name='导出信息', index=False)
        
        # 返回BytesIO对象
        output.seek(0)
        return output
        
    except Exception as e:
        raise Exception(f'生成Excel失败: {str(e)}')


# ==================== 监控与报表功能 ====================

from django.contrib.auth.decorators import login_required




def archive_monitor(request):
    """
    归档监控页面
    展示采购与合同的归档进度及逾期列表
    保持与原型一致
    """
    year_context, project_codes, project_filter, filter_config = _extract_monitoring_filters(request)

    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=50)
    module_param = request.GET.get('module', 'procurement')
    allowed_modules = {'procurement', 'contract', 'settlement'}
    if module_param not in allowed_modules:
        module_param = 'procurement'

    archive_service = ArchiveMonitorService(
        year=year_context['year_filter'],
        project_codes=project_filter
    )

    archive_overview = archive_service.get_archive_overview()
    all_overdue_list = archive_service.get_overdue_list()
    procurement_overdue = [item for item in all_overdue_list if item['module'] == '采购']
    contract_overdue = [item for item in all_overdue_list if item['module'] == '合同']

    project_archive_performance = archive_service.get_project_archive_performance()

    procurement_page_obj = None
    contract_page_obj = None
    procurement_paginator = None
    contract_paginator = None

    if procurement_overdue:
        procurement_paginator = Paginator(procurement_overdue, page_size)
        procurement_page_obj = procurement_paginator.get_page(page if module_param == 'procurement' else 1)
    if contract_overdue:
        contract_paginator = Paginator(contract_overdue, page_size)
        contract_page_obj = contract_paginator.get_page(page if module_param == 'contract' else 1)

    base_query_string = _build_pagination_querystring(request, excluded_keys=['page', 'module'])
    procurement_pagination_query = _build_pagination_querystring(
        request,
        excluded_keys=['page', 'module'],
        extra_params={'module': 'procurement'}
    )
    contract_pagination_query = _build_pagination_querystring(
        request,
        excluded_keys=['page', 'module'],
        extra_params={'module': 'contract'}
    )

    context = {
        'archive_data': archive_overview,
        'overdue_list': all_overdue_list,
        'procurement_page': procurement_page_obj,
        'contract_page': contract_page_obj,
        'procurement_paginator': procurement_paginator,
        'contract_paginator': contract_paginator,
        'available_years': year_context['available_years'],
        'selected_year': year_context['display_year'],
        'year_filter_value': year_context['selected_year_value'],
        'selected_project_value': project_codes[0] if project_codes else '',
        'project_performance': project_archive_performance,
        'active_module': module_param,
        'procurement_pagination_query': procurement_pagination_query,
        'contract_pagination_query': contract_pagination_query,
        'page_title': '归档监控',
        'monitoring_filters': _build_monitoring_filter_fields(filter_config),
        **filter_config,
    }
    return render(request, 'monitoring/archive.html', context)
def update_monitor(request):
    """Render the event-driven update monitoring dashboard."""
    from project.services.update_monitor import UpdateMonitorService

    global_filters = _resolve_global_filters(request)

    # Parse year and start-date filters
    current_year = timezone.now().year
    selected_year_raw = global_filters['year_value']
    selected_year: Optional[int] = (
        None if selected_year_raw == 'all' else global_filters['year_filter']
    )

    # 从session中获取上次的筛选条件
    session_key = 'update_monitor_filters'
    saved_filters = request.session.get(session_key, {})
    
    # Parse start_date filter (支持多种日期格式: YYYYMMDD 或 YYYY-MM-DD)
    # 优先使用URL参数，其次使用session中保存的值
    start_date_raw = request.GET.get('start_date', '')
    if not start_date_raw and 'start_date' in saved_filters:
        start_date_raw = saved_filters['start_date']
    
    start_date: Optional[date] = None
    start_date_max = f"{current_year}-{timezone.now().month:02d}-{timezone.now().day:02d}"
    
    if start_date_raw:
        # 清理输入：移除所有非数字字符
        clean_date = ''.join(c for c in start_date_raw if c.isdigit())
        
        try:
            # 尝试解析YYYYMMDD格式（8位数字）
            if len(clean_date) == 8:
                start_date = datetime.strptime(clean_date, '%Y%m%d').date()
            # 尝试解析标准日期格式
            elif '-' in start_date_raw:
                start_date = datetime.strptime(start_date_raw, '%Y-%m-%d').date()
            else:
                start_date = None
            
            # 确保起始日期不超过今天
            if start_date and start_date > timezone.now().date():
                start_date = timezone.now().date()
                start_date_raw = start_date.strftime('%Y%m%d')
            elif start_date:
                # 标准化为YYYYMMDD格式用于显示
                start_date_raw = start_date.strftime('%Y%m%d')
        except ValueError:
            # 日期格式无效，忽略该参数
            start_date = None
            start_date_raw = ''
    
    # 如果没有提供起始日期，使用配置的默认监控起始日期
    if not start_date:
        start_date = DEFAULT_MONITOR_START_DATE
        start_date_raw = start_date.strftime('%Y%m%d')
    
    # 保存当前筛选条件到session（只在有URL参数时保存）
    if request.GET.get('start_date') or request.GET.get('year'):
        current_filters = {
            'start_date': start_date_raw,
            'year': selected_year_raw,
        }
        request.session[session_key] = current_filters

    # 构建年度下拉
    base_years = list(range(BASE_YEAR, current_year + 1))
    available_years = sorted(set(base_years))
    year_options = [{'value': 'all', 'label': '全部年度'}] + [
        {'value': str(year), 'label': f'{year}年'} for year in available_years
    ]

    service = UpdateMonitorService()
    snapshot = service.build_snapshot(year=selected_year, start_date=start_date)

    # 优化显示信息
    display_year = '全部年度' if selected_year is None else f'{selected_year}年'
    if selected_year is None:
        display_start = '2000年01月01日起（全部历史数据）'
    else:
        display_start = start_date.strftime('%Y年%m月%d日')

    monitoring_filters = [
        {
            'type': 'text',
            'name': 'start_date',
            'label': '监控起始日期',
            'value': start_date_raw,
            'placeholder': '格式: YYYYMMDD 或 YYYY-MM-DD',
            'help_text': '填写以限定监控时间范围，留空则默认使用所选年度的起始日期。',
            'attrs': {
                'id': 'update-monitoring-start-date',
                'maxlength': '10',
                'inputmode': 'numeric',
            },
            'autosubmit': False,
        },
    ]

    context = {
        'page_title': '更新监控',
        'monitoring_data': snapshot,
        'selected_year_value': selected_year_raw if selected_year is not None else 'all',
        'year_options': year_options,
        'start_date_value': start_date_raw,
        'start_date_max': start_date_max,
        'display_year': display_year,
        'display_start': display_start,
        'monitoring_filters': monitoring_filters,
        'global_selected_project': global_filters['project'],
    }

    return render(request, 'monitoring/update.html', context)


def completeness_check(request):
    """
    完整性监测页面
    展示核心字段的填写完整度与项目排名
    """
    year_context, project_codes, project_filter, filter_config = _extract_monitoring_filters(request)

    procurement_page = request.GET.get('procurement_page', 1)
    contract_page = request.GET.get('contract_page', 1)
    ranking_page = request.GET.get('ranking_page', 1)
    page_size = 10

    overview = get_completeness_overview(
        year=year_context['year_filter'],
        project_codes=project_filter
    )

    procurement_field_stats = overview['procurement_field_check']['field_stats']
    contract_field_stats = overview['contract_field_check']['field_stats']

    procurement_paginator = Paginator(procurement_field_stats, page_size)
    procurement_page_obj = procurement_paginator.get_page(procurement_page)

    contract_paginator = Paginator(contract_field_stats, page_size)
    contract_page_obj = contract_paginator.get_page(contract_page)

    # 获取所有项目的完整性排名（不受project_filter限制，确保显示所有项目）
    all_project_rankings = get_project_completeness_ranking(
        year=year_context['year_filter'],
        project_codes=None  # 传入None确保获取所有项目
    )
    
    # 对项目排行榜进行分页
    ranking_paginator = Paginator(all_project_rankings, page_size)
    ranking_page_obj = ranking_paginator.get_page(ranking_page)

    context = {
        'page_title': '完整性监测',
        'overview': overview,
        'procurement_page_obj': procurement_page_obj,
        'contract_page_obj': contract_page_obj,
        'ranking_page_obj': ranking_page_obj,
        'available_years': year_context['available_years'],
        'year_filter': year_context['selected_year_value'],
        'project_filter': project_codes[0] if project_codes else '',
        'monitoring_filters': _build_monitoring_filter_fields(filter_config),
        'procurement_pagination_query': _build_pagination_querystring(request, excluded_keys=['procurement_page']),
        'contract_pagination_query': _build_pagination_querystring(request, excluded_keys=['contract_page']),
        'ranking_pagination_query': _build_pagination_querystring(request, excluded_keys=['ranking_page']),
        **filter_config,
    }

    return render(request, 'monitoring/completeness.html', context)
def statistics_view(request):
    """
    统计分析页面 - 100%还原原型图设计
    显示采购、合同、付款、结算的统计数据和图表
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
    
    # 准备采购方式图表数据
    procurement_method_labels = [item['method'] for item in procurement_stats['method_distribution']]
    procurement_method_data = [item['count'] for item in procurement_stats['method_distribution']]
    
    # 准备月度采购趋势数据(填充12个月)
    procurement_monthly_data = [0] * 12
    for item in procurement_stats['monthly_trend']:
        month_str = item['month']  # 格式: YYYY-MM
        if month_str:
            month = int(month_str.split('-')[1])
            procurement_monthly_data[month - 1] = item['count']
    
    # 准备采购周期分析数据
    cycle_by_method = procurement_stats.get('cycle_by_method', {})
    common_methods = procurement_stats.get('common_methods', [])
    
    # 常用方式数据 - 使用配置常量
    from project.enums import PROCUREMENT_METHODS_COMMON_LABELS
    procurement_duration_common_labels = PROCUREMENT_METHODS_COMMON_LABELS
    procurement_duration_common_under30 = [cycle_by_method.get(m, {}).get('under_30', 0) for m in common_methods]
    procurement_duration_common_30to60 = [cycle_by_method.get(m, {}).get('30_to_60', 0) for m in common_methods]
    procurement_duration_common_60to90 = [cycle_by_method.get(m, {}).get('60_to_90', 0) for m in common_methods]
    procurement_duration_common_over90 = [cycle_by_method.get(m, {}).get('over_90', 0) for m in common_methods]
    
    # 全部方式数据（使用预定义的10种方式，与原型图保持一致）
    all_methods = procurement_stats.get('all_methods_list', [])
    procurement_duration_all_labels = all_methods
    procurement_duration_all_under30 = [cycle_by_method.get(m, {}).get('under_30', 0) for m in all_methods]
    procurement_duration_all_30to60 = [cycle_by_method.get(m, {}).get('30_to_60', 0) for m in all_methods]
    procurement_duration_all_60to90 = [cycle_by_method.get(m, {}).get('60_to_90', 0) for m in all_methods]
    procurement_duration_all_over90 = [cycle_by_method.get(m, {}).get('over_90', 0) for m in all_methods]
    
    # 准备合同类型图表数据（包含所有类型：主合同、补充协议、解除协议、框架协议）
    contract_type_labels = [item['type'] for item in contract_stats['type_distribution']]
    contract_type_data = [item['amount'] for item in contract_stats['type_distribution']]
    
    # 准备合同来源图表数据
    contract_source_labels = [item['source'] for item in contract_stats['source_distribution']]
    contract_source_data = [item['count'] for item in contract_stats['source_distribution']]
    
    # 准备付款TOP项目数据 - 优化查询,使用数据库聚合避免N+1问题
    from collections import defaultdict
    
    # 使用annotate一次性计算所需数据
    main_contracts = Contract.objects.filter(
        file_positioning=FilePositioning.MAIN_CONTRACT.value
    ).select_related('project').prefetch_related('supplements', 'payments').annotate(
        total_paid=Coalesce(Sum('payments__payment_amount'), Value(0), output_field=DecimalField()),
        payment_count=Count('payments'),
        supplements_total=Coalesce(
            Sum('supplements__contract_amount', filter=Q(supplements__file_positioning=FilePositioning.SUPPLEMENT.value)),
            Value(0),
            output_field=DecimalField()
        )
    )
    
    if year_context['year_filter']:
        main_contracts = main_contracts.filter(signing_date__year=year_context['year_filter'])
    if project_filter:
        main_contracts = main_contracts.filter(project__project_code__in=project_filter)
    
    # 按项目聚合
    project_payments = {}
    
    for contract in main_contracts:
        if not contract.project:
            continue
            
        project_key = contract.project.project_code
        
        # 初始化项目数据
        if project_key not in project_payments:
            project_payments[project_key] = {
                'total_paid': 0.0,
                'payment_count': 0,
                'contract_amount': 0.0,
                'project_name': contract.project.project_name
            }
        
        # 使用预计算的值,避免额外查询
        # contract.supplements_total 是通过 annotate 计算的聚合字段
        supplements_total = getattr(contract, 'supplements_total', 0) or 0
        contract_with_supplements = float(contract.contract_amount or 0) + float(supplements_total)
        
        # contract.total_paid 和 contract.payment_count 也是通过 annotate 计算的字段
        total_paid = getattr(contract, 'total_paid', 0) or 0
        payment_count = getattr(contract, 'payment_count', 0) or 0
        
        project_payments[project_key]['contract_amount'] += contract_with_supplements
        project_payments[project_key]['total_paid'] += float(total_paid)
        project_payments[project_key]['payment_count'] += int(payment_count)
    
    # 计算支付率并转换为万元
    for key in project_payments:
        contract_amt = project_payments[key]['contract_amount']
        if contract_amt > 0:
            project_payments[key]['payment_ratio'] = (project_payments[key]['total_paid'] / contract_amt) * 100
        else:
            project_payments[key]['payment_ratio'] = 0.0
        # 转换为万元用于显示
        project_payments[key]['total_paid'] = project_payments[key]['total_paid'] / 10000
        project_payments[key]['contract_amount'] = contract_amt / 10000
    
    # 按总付款额排序,取TOP 5
    payment_top_projects = sorted(
        [{'project_name': v['project_name'], **v} for v in project_payments.values()],
        key=lambda x: x['total_paid'],
        reverse=True
    )[:5]
    
    # 准备结算偏差分析数据
    settlement_variance_analysis = []
    for item in settlement_stats.get('variance_analysis', [])[:5]:
        settlement_variance_analysis.append({
            'contract_name': item.get('contract_name', 'N/A'),  # 使用合同名称
            'contract_amount': item['contract_amount'],
            'settlement_amount': item['settlement_amount'],
            'variance': item['variance'],
            'variance_rate': item['variance_rate']
        })
    
    context = {
        'page_title': '统计分析',
        'selected_year': year_context['display_year'],
        'year_filter_value': year_context['selected_year_value'],
        'available_years': year_context['available_years'],
        **filter_config,
        
        # 统计数据
        'procurement_stats': procurement_stats,
        'contract_stats': contract_stats,
        'payment_stats': {
            **payment_stats,
            'top_projects': payment_top_projects
        },
        'settlement_stats': {
            **settlement_stats,
            'variance_analysis': settlement_variance_analysis
        },
        'monitoring_filters': _build_monitoring_filter_fields(filter_config),
        
        # 图表数据 - 转换为JSON
        'procurement_method_labels': json.dumps(procurement_method_labels, ensure_ascii=False),
        'procurement_method_data': json.dumps(procurement_method_data),
        'procurement_monthly_data': json.dumps(procurement_monthly_data),
        
        # 采购周期数据 - 常用方式
        'procurement_duration_common_labels': json.dumps(procurement_duration_common_labels, ensure_ascii=False),
        'procurement_duration_common_under30': json.dumps(procurement_duration_common_under30),
        'procurement_duration_common_30to60': json.dumps(procurement_duration_common_30to60),
        'procurement_duration_common_60to90': json.dumps(procurement_duration_common_60to90),
        'procurement_duration_common_over90': json.dumps(procurement_duration_common_over90),
        
        # 采购周期数据 - 全部方式
        'procurement_duration_all_labels': json.dumps(procurement_duration_all_labels, ensure_ascii=False),
        'procurement_duration_all_under30': json.dumps(procurement_duration_all_under30),
        'procurement_duration_all_30to60': json.dumps(procurement_duration_all_30to60),
        'procurement_duration_all_60to90': json.dumps(procurement_duration_all_60to90),
        'procurement_duration_all_over90': json.dumps(procurement_duration_all_over90),
        
        # 合同类型数据（按金额）
        'contract_type_labels': json.dumps(contract_type_labels, ensure_ascii=False),
        'contract_type_data': json.dumps(contract_type_data),
        
        'contract_source_labels': json.dumps(contract_source_labels, ensure_ascii=False),
        'contract_source_data': json.dumps(contract_source_data),
    }
    
    return render(request, 'monitoring/statistics.html', context)


def ranking_view(request):
    """
    业务排名页面
    显示项目和个人在采购、归档、合同、结算等维度的业务排名
    按照指标体系需求文档第6章设计
    """
    from project.services.ranking import (
        get_procurement_on_time_ranking,
        get_procurement_cycle_ranking,
        get_procurement_quantity_ranking,
        get_archive_timeliness_ranking,
        get_archive_speed_ranking,
        get_contract_ranking,
        get_settlement_ranking,
        get_comprehensive_ranking
    )
    from datetime import datetime
    
    # Parse year and start-date filters
    current_year = datetime.now().year
    selected_year = request.GET.get('year', '')
    ranking_type = request.GET.get('type', 'comprehensive')
    rank_by = request.GET.get('rank_by', 'project')  # project/person
    
    # 转换年份参数 - 空字符串表示全部年份
    if selected_year == '' or selected_year == 'all':
        year_filter = None
    elif selected_year and selected_year.isdigit():
        year_filter = int(selected_year)
    else:
        # 如果没有提供年份参数，默认显示全部
        year_filter = None
    
    # 获取筛选配置
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
        **filter_config,  # 添加筛选配置
    }
    
    # 根据排名类型获取数据
    if ranking_type == 'procurement_ontime':
        # 6.3.1 采购计划准时完成率排名
        context['procurement_ranking'] = get_procurement_on_time_ranking(
            rank_type=rank_by,
            year=year_filter
        )
    elif ranking_type == 'procurement_cycle':
        # 6.3.2 采购周期效率排名
        context['procurement_ranking'] = get_procurement_cycle_ranking(
            rank_type=rank_by,
            year=year_filter
        )
    elif ranking_type == 'procurement_quantity':
        # 6.3.3 采购完成数量排名
        context['procurement_ranking'] = get_procurement_quantity_ranking(
            rank_type=rank_by,
            year=year_filter
        )
    elif ranking_type == 'archive_timeliness':
        # 6.4.1 归档及时率排名
        context['archive_ranking'] = get_archive_timeliness_ranking(
            rank_type=rank_by,
            year=year_filter
        )
    elif ranking_type == 'archive_speed':
        # 6.4.2 归档速度排名
        context['archive_ranking'] = get_archive_speed_ranking(
            rank_type=rank_by,
            year=year_filter
        )
    elif ranking_type == 'contract':
        # 合同签订排名
        context['contract_ranking'] = get_contract_ranking(
            rank_type=rank_by,
            year=year_filter
        )
    elif ranking_type == 'settlement':
        # 结算完成排名（不支持年份筛选）
        context['settlement_ranking'] = get_settlement_ranking(
            rank_type=rank_by
        )
    else:
        # 6.6 综合业务排名
        context['comprehensive_ranking'] = get_comprehensive_ranking(year=year_filter)
    
    return render(request, 'monitoring/ranking.html', context)


def generate_report(request):
    """
    报表生成页面
    生成周报、月报、季报、年报
    """
    from project.services.report_generator import (
        WeeklyReportGenerator,
        MonthlyReportGenerator,
        QuarterlyReportGenerator,
        AnnualReportGenerator,
        export_to_excel
    )
    from datetime import datetime, date
    import os
    import tempfile
    
    if request.method == 'GET':
        # 显示报表生成表单
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_quarter = (current_month - 1) // 3 + 1
        
        # 获取全局筛选参数
        global_filters = _resolve_global_filters(request)
        
        # 获取所有项目用于项目报告选择
        all_projects = Project.objects.all().order_by('project_name')
        
        context = {
            'page_title': '报表生成',
            'current_year': current_year,
            'current_month': current_month,
            'current_quarter': current_quarter,
            'available_years': get_year_range(include_future=True),
            'available_months': list(range(1, 13)),
            'available_quarters': [1, 2, 3, 4],
            'selected_projects': all_projects,  # 所有项目用于下拉选择
            'global_selected_year': global_filters['year_value'],
            'global_selected_project': global_filters['project'],
        }
        return render(request, 'reports/form.html', context)
    
    # POST请求 - 生成报表
    try:
        # POST请求需要从request.POST获取参数，而不是request.GET
        report_type = request.POST.get('report_type', 'monthly')
        export_format = request.POST.get('export_format', 'preview')  # preview/excel/word
        
        # 获取项目筛选参数
        project_param = request.POST.get('project', '').strip()
        project_code_param = request.POST.get('project_code', '').strip()  # 项目报告专用
        
        # 如果是项目报告类型，使用project_code参数
        if report_type == 'project':
            project_codes = [project_code_param] if project_code_param else None
        else:
            project_codes = [project_param] if project_param else None
        
        year = int(request.POST.get('year', datetime.now().year))
        month = int(request.POST.get('month', datetime.now().month))
        quarter = int(request.POST.get('quarter', 1))
        
        # 根据报表类型生成数据，传入项目筛选参数
        if report_type == 'project':
            # 项目报告 - 生成项目全生命周期报告
            if not project_codes or not project_codes[0]:
                messages.error(request, '请选择要生成报告的项目')
                return redirect('generate_report')
            generator = AnnualReportGenerator(year, project_codes=project_codes)
        elif report_type == 'weekly':
            # 周报需要指定具体日期
            target_date_str = request.POST.get('target_date')
            if target_date_str:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            else:
                target_date = date.today()
            generator = WeeklyReportGenerator(target_date, project_codes=project_codes)
        elif report_type == 'monthly':
            generator = MonthlyReportGenerator(year, month, project_codes=project_codes)
        elif report_type == 'quarterly':
            generator = QuarterlyReportGenerator(year, quarter, project_codes=project_codes)
        elif report_type == 'annual':
            generator = AnnualReportGenerator(year, project_codes=project_codes)
        else:
            return JsonResponse({
                'success': False,
                'message': '不支持的报表类型'
            }, status=400)
        
        # 生成报表数据
        report_data = generator.generate_data()
        
        # 根据导出格式处理
        if export_format == 'word':
            # Word导出使用旧的export_to_word，不是professional版本
            try:
                from project.services.report_generator import export_to_word
            except ImportError as e:
                messages.error(request, f'Word导出功能不可用，请确保已安装python-docx库: pip install python-docx')
                return redirect('generate_report')
            
            # 创建临时文件
            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.docx')
            os.close(tmp_fd)  # 立即关闭文件描述符
            
            try:
                # 导出为Word文档
                export_to_word(report_data, tmp_path)
                
                # 验证文件是否生成成功
                if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                    raise Exception('Word文档生成失败，文件为空或不存在')
                
                # 读取文件内容
                with open(tmp_path, 'rb') as f:
                    word_content = f.read()
                
                # 生成安全的文件名
                safe_title = report_data.get('title', '工作报表').replace('/', '-').replace('\\', '-')
                filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                
                # 返回Word文件
                response = HttpResponse(
                    word_content,
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
                # 使用URL编码确保中文文件名正确显示
                from urllib.parse import quote
                encoded_filename = quote(filename.encode('utf-8'))
                response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
                return response
            except Exception as e:
                messages.error(request, f'生成Word文档失败: {str(e)}')
                return redirect('generate_report')
            finally:
                # 清理临时文件
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except Exception:
                    pass  # 忽略清理错误
        elif export_format == 'excel':
            # 导出为Excel文件
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # 导出到临时文件
                export_to_excel(report_data, tmp_path)
                
                # 读取文件内容
                with open(tmp_path, 'rb') as f:
                    excel_content = f.read()
                
                # 生成文件名
                filename = f"{report_data['title']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                # 返回Excel文件
                response = HttpResponse(
                    excel_content,
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            finally:
                # 清理临时文件
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        else:
            # 预览模式 - 显示报表内容
            context = {
                'page_title': '报表预览',
                'report_data': report_data,
                'report_type': report_type,
            }
            return render(request, 'reports/preview.html', context)
    
    except Exception as e:
        messages.error(request, f'生成报表失败: {str(e)}')
        return redirect('generate_report')


def report_preview(request):
    """
    报表预览视图 - 处理GET请求生成报表预览
    """
    from project.services.report_generator import (
        WeeklyReportGenerator,
        MonthlyReportGenerator,
        QuarterlyReportGenerator,
        AnnualReportGenerator
    )
    from datetime import datetime, date
    
    try:
        # 获取报表类型和参数
        report_type = request.GET.get('report_type', 'monthly')
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        quarter = int(request.GET.get('quarter', 1))
        
        # 获取项目筛选参数
        project_param = request.GET.get('project', '').strip()
        project_codes = [project_param] if project_param else None
        
        # 根据报表类型生成数据
        if report_type == 'weekly':
            target_date_str = request.GET.get('target_date')
            if target_date_str:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            else:
                target_date = date.today()
            generator = WeeklyReportGenerator(target_date, project_codes=project_codes)
        elif report_type == 'monthly':
            generator = MonthlyReportGenerator(year, month, project_codes=project_codes)
        elif report_type == 'quarterly':
            generator = QuarterlyReportGenerator(year, quarter, project_codes=project_codes)
        elif report_type == 'annual':
            generator = AnnualReportGenerator(year, project_codes=project_codes)
        else:
            messages.error(request, '不支持的报表类型')
            return redirect('generate_report')
        
        # 生成报表数据
        report_data = generator.generate_data()
        
        context = {
            'page_title': '报表预览',
            'report_data': report_data,
            'report_type': report_type,
        }
        return render(request, 'reports/preview.html', context)
    
    except Exception as e:
        messages.error(request, f'生成报表失败: {str(e)}')
        return redirect('generate_report')


def report_export(request):
    """
    报表导出视图 - 处理GET请求导出Excel
    """
    from project.services.report_generator import (
        WeeklyReportGenerator,
        MonthlyReportGenerator,
        QuarterlyReportGenerator,
        AnnualReportGenerator,
        export_to_excel
    )
    from datetime import datetime, date
    import os
    import tempfile
    
    try:
        # 获取报表类型和参数
        report_type = request.GET.get('report_type', 'monthly')
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        quarter = int(request.GET.get('quarter', 1))
        
        # 获取项目筛选参数
        project_param = request.GET.get('project', '').strip()
        project_codes = [project_param] if project_param else None
        
        # 根据报表类型生成数据
        if report_type == 'weekly':
            target_date_str = request.GET.get('target_date')
            if target_date_str:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            else:
                target_date = date.today()
            generator = WeeklyReportGenerator(target_date, project_codes=project_codes)
        elif report_type == 'monthly':
            generator = MonthlyReportGenerator(year, month, project_codes=project_codes)
        elif report_type == 'quarterly':
            generator = QuarterlyReportGenerator(year, quarter, project_codes=project_codes)
        elif report_type == 'annual':
            generator = AnnualReportGenerator(year, project_codes=project_codes)
        else:
            messages.error(request, '不支持的报表类型')
            return redirect('generate_report')
        
        # 生成报表数据
        report_data = generator.generate_data()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 导出到临时文件
            export_to_excel(report_data, tmp_path)
            
            # 读取文件内容
            with open(tmp_path, 'rb') as f:
                excel_content = f.read()
            
            # 生成文件名
            filename = f"{report_data['title']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # 返回Excel文件
            response = HttpResponse(
                excel_content,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        messages.error(request, f'导出报表失败: {str(e)}')
        return redirect('generate_report')


def monitoring_cockpit(request):
    """综合监测驾驶舱"""
    year_context, project_codes, project_filter, filter_config = _extract_monitoring_filters(request)

    year_filter = year_context['year_filter']
    start_date = date(year_filter, 1, 1) if year_filter else date(2019, 1, 1)

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

    kpis = {
        'timeliness_rate': update_snapshot['kpis']['overallTimelinessRate'] if update_snapshot['kpis']['overallTimelinessRate'] is not None else 0,
        'timely_events': update_snapshot['kpis']['totalEvents'] - update_snapshot['kpis']['delayedEvents'],
        'total_events': update_snapshot['kpis']['totalEvents'],
        'archive_rate': archive_overview['overall_rate'],
        'overdue_items': archive_overview['procurement']['overdue'] + archive_overview['contract']['overdue'],
        'completeness_rate': round((completeness_overview['procurement_field_check']['completeness_rate'] + completeness_overview['contract_field_check']['completeness_rate']) / 2, 2),
        'completeness_issues_main': "合同-支付对账异常" if completeness_overview.get('payment_check', {}).get('summary', {}).get('overpaid_contracts', 0) > 0 else "关键字段完整",
        'risk_items': completeness_overview.get('error_count', 0),
        'risk_issues_main': "资金超额、资料滞后"
    }

    core_stats = {
        'total_budget': procurement_stats['total_budget'],
        'total_projects': Project.objects.filter(project_code__in=project_codes).count() if project_codes else Project.objects.count(),
        'total_contract_amount': contract_stats['total_amount'],
        'total_contracts': contract_stats['total_count'],
        'total_payment_amount': payment_stats['total_amount'],
        'payment_progress': (payment_stats['total_amount'] / contract_stats['total_amount'] * 100) if contract_stats['total_amount'] > 0 else 0
    }

    procurement_method_chart_data = {
        'labels': [item['method'] for item in procurement_stats['method_distribution']],
        'datasets': [{
            'label': '采购金额',
            'data': [item['amount'] for item in procurement_stats['method_distribution']],
            'backgroundColor': ['#1890ff', '#13c2c2', '#2fc25b', '#facc14', '#f04864', '#8543e0', '#3436c7'],
        }]
    }

    contract_type_chart_data = {
        'labels': [item['type'] for item in contract_stats['type_distribution']],
        'datasets': [{
            'label': '合同数量',
            'data': [item['count'] for item in contract_stats['type_distribution']],
            'backgroundColor': '#1890ff',
        }]
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
            }
        ]
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
        'page_title': '综合监测驾驶舱',
        'year_options': year_context['available_years'],
        'selected_year': year_context['selected_year_value'],
        'start_date_value': start_date.isoformat(),
        'monitoring_snapshot': update_snapshot,
        'update_statistics': update_snapshot['statistics'],
        'overdue_list': overdue_list,
        **filter_config,

        'kpis': kpis,
        'core_stats': core_stats,

        'procurement_method_chart_data_json': json.dumps(procurement_method_chart_data, ensure_ascii=False),
        'contract_type_chart_data_json': json.dumps(contract_type_chart_data, ensure_ascii=False),
        'monthly_trend_chart_data_json': json.dumps(monthly_trend_chart_data, ensure_ascii=False),

        'heatmap_projects': heatmap_projects,
        'archive_progress': archive_progress,
        'completeness_progress': completeness_progress,
        'completeness_issues': completeness_issues,
    }

    return render(request, 'monitoring/cockpit.html', context)














# ==================== 专业Word报告生成功能 ====================

@require_http_methods(['GET', 'POST'])
def generate_professional_report(request):
    """
    专业报告生成与导出
    支持周报、月报、季报、年报，支持单个/多个项目
    导出Word文档格式
    """
    from project.services.professional_report_generator import (
        WeeklyReportGenerator,
        MonthlyReportGenerator,
        QuarterlyReportGenerator,
        AnnualReportGenerator,
    )
    from project.services.word_exporter import export_to_word_professional
    from datetime import datetime, date
    import os
    import tempfile
    
    if request.method == 'GET':
        # 显示报表生成表单
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_quarter = (current_month - 1) // 3 + 1
        
        # 获取全局筛选参数
        global_filters = _resolve_global_filters(request)
        
        # 获取所有项目用于多选
        projects = Project.objects.all().order_by('project_name')
        
        context = {
            'page_title': '专业报告生成',
            'current_year': current_year,
            'current_month': current_month,
            'current_quarter': current_quarter,
            'available_years': get_year_range(include_future=True),
            'available_months': list(range(1, 13)),
            'available_quarters': [1, 2, 3, 4],
            'projects': projects,
            'selected_projects': global_filters['project_list'],
            'global_selected_year': global_filters['year_value'],
            'global_selected_project': global_filters['project'],
        }
        return render(request, 'reports/professional_form.html', context)
    
    # POST请求 - 生成并导出Word报告
    try:
        # 获取项目筛选参数（支持多选）
        project_codes = request.POST.getlist('projects')
        if not project_codes:
            project_param = request.POST.get('project', '').strip()
            project_codes = [project_param] if project_param else None
        else:
            project_codes = [p for p in project_codes if p]  # 过滤空值
            if not project_codes:
                project_codes = None
        
        report_type = request.POST.get('report_type', 'monthly')
        year = int(request.POST.get('year', datetime.now().year))
        month = int(request.POST.get('month', datetime.now().month))
        quarter = int(request.POST.get('quarter', 1))
        
        # 根据报表类型生成数据
        if report_type == 'weekly':
            target_date_str = request.POST.get('target_date')
            if target_date_str:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            else:
                target_date = date.today()
            generator = WeeklyReportGenerator(target_date, project_codes=project_codes)
        elif report_type == 'monthly':
            generator = MonthlyReportGenerator(year, month, project_codes=project_codes)
        elif report_type == 'quarterly':
            generator = QuarterlyReportGenerator(year, quarter, project_codes=project_codes)
        elif report_type == 'annual':
            generator = AnnualReportGenerator(year, project_codes=project_codes)
        else:
            return JsonResponse({
                'success': False,
                'message': '不支持的报表类型'
            }, status=400)
        
        # 生成报表数据
        report_data = generator.generate_report_data()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 导出为Word文档
            export_to_word_professional(report_data, tmp_path)
            
            # 读取文件内容
            with open(tmp_path, 'rb') as f:
                word_content = f.read()
            
            # 生成文件名
            meta = report_data.get('meta', {})
            report_title = meta.get('report_title', '工作报告')
            filename = f"{report_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            
            # 返回Word文件
            response = HttpResponse(
                word_content,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        messages.error(request, f'生成报告失败: {str(e)}')
        return redirect('generate_professional_report')


# ==================== 高级综合报告生成功能 ====================

@require_http_methods(['GET', 'POST'])
def generate_comprehensive_report(request):
    """
    生成综合详细报告（年度总结、部门总结等）
    使用新的AdvancedReportGenerator和comprehensive_word_exporter
    """
    from project.services.advanced_report_generator import (
        AnnualComprehensiveReportGenerator,
        DepartmentReportGenerator,
        AdvancedReportGenerator
    )
    from project.services.comprehensive_word_exporter import export_comprehensive_word_report
    from datetime import datetime, date
    import os
    import tempfile
    
    if request.method == 'GET':
        # 显示报表生成表单
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # 获取全局筛选参数
        global_filters = _resolve_global_filters(request)
        
        # 获取所有项目用于多选
        projects = Project.objects.all().order_by('project_name')
        
        context = {
            'page_title': '综合报告生成',
            'current_year': current_year,
            'current_month': current_month,
            'available_years': get_year_range(include_future=True),
            'available_months': list(range(1, 13)),
            'projects': projects,
            'selected_projects': global_filters['project_list'],
            'global_selected_year': global_filters['year_value'],
            'global_selected_project': global_filters['project'],
        }
        return render(request, 'reports/comprehensive_form.html', context)
    
    # POST请求 - 生成并导出Word报告
    try:
        # 获取报告类型
        report_type = request.POST.get('report_type', 'annual')  # annual/department/custom
        
        # 获取项目筛选参数（支持多选）
        project_codes = request.POST.getlist('projects')
        if not project_codes:
            project_param = request.POST.get('project', '').strip()
            project_codes = [project_param] if project_param else None
        else:
            project_codes = [p for p in project_codes if p]  # 过滤空值
            if not project_codes:
                project_codes = None
        
        year = int(request.POST.get('year', datetime.now().year))
        
        # 根据报表类型生成数据
        if report_type == 'annual':
            # 年度综合报告
            generator = AnnualComprehensiveReportGenerator(year, project_codes=project_codes)
        elif report_type == 'department':
            # 部门总结报告
            department_name = request.POST.get('department_name', '采购部门')
            
            # 根据选择确定时间范围
            period_type = request.POST.get('period_type', 'year')  # month/quarter/year
            
            if period_type == 'month':
                month = int(request.POST.get('month', datetime.now().month))
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year, 12, 31)
                else:
                    from calendar import monthrange
                    end_date = date(year, month, monthrange(year, month)[1])
            elif period_type == 'quarter':
                quarter = int(request.POST.get('quarter', 1))
                start_month = (quarter - 1) * 3 + 1
                start_date = date(year, start_month, 1)
                end_month = start_month + 2
                if end_month == 12:
                    end_date = date(year, 12, 31)
                else:
                    from calendar import monthrange
                    end_date = date(year, end_month, monthrange(year, end_month)[1])
            else:  # year
                start_date = date(year, 1, 1)
                end_date = date(year, 12, 31)
            
            generator = DepartmentReportGenerator(start_date, end_date, department_name)
        else:
            # 自定义时间范围
            start_date_str = request.POST.get('start_date')
            end_date_str = request.POST.get('end_date')
            
            if not start_date_str or not end_date_str:
                messages.error(request, '请提供开始和结束日期')
                return redirect('generate_comprehensive_report')
            
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            generator = AdvancedReportGenerator(start_date, end_date, project_codes=project_codes)
        
        # 生成报表数据
        report_data = generator.generate_comprehensive_report()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 导出为Word文档
            export_comprehensive_word_report(report_data, tmp_path)
            
            # 验证文件是否生成成功
            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                raise Exception('Word文档生成失败，文件为空或不存在')
            
            # 读取文件内容
            with open(tmp_path, 'rb') as f:
                word_content = f.read()
            
            # 生成文件名
            meta = report_data.get('meta', {})
            report_title = meta.get('report_title', '工作报告')
            filename = f"{report_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            
            # 返回Word文件
            response = HttpResponse(
                word_content,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            # 使用URL编码确保中文文件名正确显示
            from urllib.parse import quote
            encoded_filename = quote(filename.encode('utf-8'))
            response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
            return response
        finally:
            # 清理临时文件
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass  # 忽略清理错误
    except Exception as e:
        messages.error(request, f'生成报告失败: {str(e)}')
        return redirect('generate_comprehensive_report')


# ==================== 前端编辑功能 ====================

@require_http_methods(['GET', 'POST'])
def project_edit(request, project_code):
    """
    项目编辑视图 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from project.forms import ProjectForm
    
    try:
        project = Project.objects.get(project_code=project_code)
    except Project.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': '项目不存在'
            }, status=404)
        return HttpResponse('项目不存在', status=404)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({
                    'success': True,
                    'message': '项目信息更新成功'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'保存失败: {str(e)}'
                }, status=400)
        else:
            # 构建详细的错误信息
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")
            
            detailed_message = '表单验证失败：\n' + '\n'.join(error_messages)
            
            return JsonResponse({
                'success': False,
                'message': detailed_message,
                'errors': form.errors,
                'field_errors': {
                    field: list(errors) for field, errors in form.errors.items()
                }
            }, status=400)
    
    # GET请求 - 返回表单HTML
    form = ProjectForm(instance=project)
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '编辑项目信息',
        'submit_url': f'/projects/{project_code}/edit/',
        'module_type': 'project',
    })


@require_http_methods(['GET', 'POST'])
def contract_edit(request, contract_code):
    """
    合同编辑视图 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from project.forms import ContractForm
    
    try:
        contract = Contract.objects.get(contract_code=contract_code)
    except Contract.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': '合同不存在'
            }, status=404)
        return HttpResponse('合同不存在', status=404)
    
    if request.method == 'POST':
        form = ContractForm(request.POST, instance=contract)
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({
                    'success': True,
                    'message': '合同信息更新成功'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'保存失败: {str(e)}'
                }, status=400)
        else:
            # 构建详细的错误信息
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")
            
            detailed_message = '表单验证失败：\n' + '\n'.join(error_messages)
            
            return JsonResponse({
                'success': False,
                'message': detailed_message,
                'errors': form.errors,
                'field_errors': {
                    field: list(errors) for field, errors in form.errors.items()
                }
            }, status=400)
    
    # GET请求
    form = ContractForm(instance=contract)
    
    # 准备初始显示文本
    initial_display = {}
    if contract.project:
        initial_display['project'] = f"{contract.project.project_code} - {contract.project.project_name}"
    if contract.procurement:
        initial_display['procurement'] = f"{contract.procurement.procurement_code} - {contract.procurement.project_name}"
    if contract.parent_contract:
        initial_display['parent_contract'] = f"{contract.parent_contract.contract_sequence or contract.parent_contract.contract_code} - {contract.parent_contract.contract_name}"
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '编辑合同信息',
        'submit_url': f'/contracts/{contract_code}/edit/',
        'module_type': 'contract',
        'initial_display': initial_display,
    })


@require_http_methods(['GET', 'POST'])
def procurement_edit(request, procurement_code):
    """
    采购编辑视图 - AJAX接口
    """
    from project.forms import ProcurementForm
    
    try:
        procurement = Procurement.objects.get(procurement_code=procurement_code)
    except Procurement.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': '采购项目不存在'
            }, status=404)
        return HttpResponse('采购项目不存在', status=404)
    
    if request.method == 'POST':
        form = ProcurementForm(request.POST, instance=procurement)
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({
                    'success': True,
                    'message': '采购信息更新成功'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'保存失败: {str(e)}'
                }, status=400)
        else:
            # 构建详细的错误信息
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")
            
            detailed_message = '表单验证失败：\n' + '\n'.join(error_messages)
            
            return JsonResponse({
                'success': False,
                'message': detailed_message,
                'errors': form.errors,
                'field_errors': {
                    field: list(errors) for field, errors in form.errors.items()
                }
            }, status=400)
    
    form = ProcurementForm(instance=procurement)
    
    # 准备初始显示文本
    initial_display = {}
    if procurement.project:
        initial_display['project'] = f"{procurement.project.project_code} - {procurement.project.project_name}"
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '编辑采购信息',
        'submit_url': f'/procurements/{procurement_code}/edit/',
        'module_type': 'procurement',
        'initial_display': initial_display,
    })


@require_http_methods(['GET', 'POST'])
def payment_edit(request, payment_code):
    """
    付款编辑视图 - AJAX接口
    """
    from project.forms import PaymentForm
    
    try:
        payment = Payment.objects.get(payment_code=payment_code)
    except Payment.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': '付款记录不存在'
            }, status=404)
        return HttpResponse('付款记录不存在', status=404)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            try:
                form.save()
                return JsonResponse({
                    'success': True,
                    'message': '付款信息更新成功'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'保存失败: {str(e)}'
                }, status=400)
        else:
            # 构建详细的错误信息
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")
            
            detailed_message = '表单验证失败：\n' + '\n'.join(error_messages)
            
            return JsonResponse({
                'success': False,
                'message': detailed_message,
                'errors': form.errors,
                'field_errors': {
                    field: list(errors) for field, errors in form.errors.items()
                }
            }, status=400)
    
    form = PaymentForm(instance=payment)
    
    # 准备初始显示文本
    initial_display = {}
    if payment.contract:
        initial_display['contract'] = f"{payment.contract.contract_sequence or payment.contract.contract_code} - {payment.contract.contract_name}"
        if payment.contract.project:
            initial_display['project'] = f"{payment.contract.project.project_code} - {payment.contract.project.project_name}"
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '编辑付款信息',
        'submit_url': f'/payments/{payment_code}/edit/',
        'module_type': 'payment',
        'initial_display': initial_display,
    })



@require_http_methods(['GET', 'POST'])
def procurement_create(request):
    """
    采购新增视图 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from project.forms import ProcurementForm
    
    if request.method == 'POST':
        form = ProcurementForm(request.POST)
        if form.is_valid():
            try:
                procurement = form.save()
                return JsonResponse({
                    'success': True,
                    'message': '采购项目创建成功',
                    'procurement_code': procurement.procurement_code
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'保存失败: {str(e)}'
                }, status=400)
        else:
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")
            
            return JsonResponse({
                'success': False,
                'message': '表单验证失败：\n' + '\n'.join(error_messages),
                'errors': form.errors
            }, status=400)
    
    # GET请求 - 返回表单HTML
    form = ProcurementForm()
    # 移除readonly属性，允许输入新的编号
    form.fields['procurement_code'].widget.attrs.pop('readonly', None)
    form.fields['procurement_code'].disabled = False
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '新增采购项目',
        'submit_url': '/procurements/create/',
        'module_type': 'procurement',
    })


@require_http_methods(['GET', 'POST'])
def contract_create(request):
    """
    合同新增视图 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from project.forms import ContractForm
    
    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            try:
                contract = form.save()
                return JsonResponse({
                    'success': True,
                    'message': '合同创建成功',
                    'contract_code': contract.contract_code
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'保存失败: {str(e)}'
                }, status=400)
        else:
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")
            
            return JsonResponse({
                'success': False,
                'message': '表单验证失败：\n' + '\n'.join(error_messages),
                'errors': form.errors
            }, status=400)
    
    # GET请求 - 返回表单HTML
    form = ContractForm()
    # 移除readonly属性
    form.fields['contract_code'].widget.attrs.pop('readonly', None)
    form.fields['contract_code'].disabled = False
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '新增合同',
        'submit_url': '/contracts/create/',
        'module_type': 'contract',
    })


@require_http_methods(['GET', 'POST'])
def payment_create(request):
    """
    付款新增视图 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from project.forms import PaymentForm
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                payment = form.save()
                return JsonResponse({
                    'success': True,
                    'message': '付款记录创建成功',
                    'payment_code': payment.payment_code
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'保存失败: {str(e)}'
                }, status=400)
        else:
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")
            
            return JsonResponse({
                'success': False,
                'message': '表单验证失败：\n' + '\n'.join(error_messages),
                'errors': form.errors
            }, status=400)
    
    # GET请求 - 返回表单HTML
    form = PaymentForm()
    # 付款编号可以为空（自动生成）
    form.fields['payment_code'].required = False
    form.fields['payment_code'].widget.attrs['placeholder'] = '留空则自动生成'
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '新增付款记录',
        'submit_url': '/payments/create/',
        'module_type': 'payment',
    })


@require_http_methods(['GET', 'POST'])
def project_create(request):
    """
    项目新增视图 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from project.forms import ProjectForm
    
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            try:
                project = form.save()
                return JsonResponse({
                    'success': True,
                    'message': '项目创建成功',
                    'project_code': project.project_code
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'保存失败: {str(e)}'
                }, status=400)
        else:
            error_messages = []
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")
            
            return JsonResponse({
                'success': False,
                'message': '表单验证失败：\n' + '\n'.join(error_messages),
                'errors': form.errors
            }, status=400)
    
    # GET请求 - 返回表单HTML
    form = ProjectForm()
    # 移除readonly属性
    form.fields['project_code'].widget.attrs.pop('readonly', None)
    form.fields['project_code'].disabled = False
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '新增项目',
        'submit_url': '/projects/create/',
        'module_type': 'project',
    })


# ==================== 统计数据详情查看功能 ====================

@require_http_methods(['GET'])
def statistics_detail_api(request, module):
    """
    统计数据详情API - 返回JSON格式的分页数据
    
    Args:
        module: 统计模块 (procurement/contract/payment/settlement)
    
    Query Parameters:
        year: 年份筛选
        project: 项目编码
        page: 页码 (默认1)
        page_size: 每页数量 (默认50)
    
    Returns:
        JSON: {'success': True, 'data': [...], 'pagination': {...}, 'summary': {...}}
    """
    try:
        # 解析筛选参数
        global_filters = _resolve_global_filters(request)
        year_filter = global_filters['year_filter']
        project_codes = global_filters['project_list']
        project_filter = project_codes if project_codes else None
        
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 50)), 100)  # 最大100条
        
        # 根据模块获取详情数据
        if module == 'procurement':
            from project.services.statistics import get_procurement_details, get_procurement_statistics
            details = get_procurement_details(year_filter, project_filter)
            stats = get_procurement_statistics(year_filter, project_filter)
            summary = {
                'total_count': stats['total_count'],
                'total_budget': stats['total_budget'],
                'total_winning': stats['total_winning'],
                'savings_rate': stats['savings_rate'],
            }
        elif module == 'contract':
            from project.services.statistics import get_contract_details, get_contract_statistics
            details = get_contract_details(year_filter, project_filter)
            stats = get_contract_statistics(year_filter, project_filter)
            summary = {
                'total_count': stats['total_count'],
                'total_amount': stats['total_amount'],
                'main_count': stats['main_count'],
                'supplement_count': stats['supplement_count'],
            }
        elif module == 'payment':
            from project.services.statistics import get_payment_details, get_payment_statistics
            details = get_payment_details(year_filter, project_filter)
            stats = get_payment_statistics(year_filter, project_filter)
            summary = {
                'total_count': stats['total_count'],
                'total_amount': stats['total_amount'],
                'payment_rate': stats['payment_rate'],
                'estimated_remaining': stats['estimated_remaining'],
            }
        elif module == 'settlement':
            from project.services.statistics import get_settlement_details, get_settlement_statistics
            details = get_settlement_details(year_filter, project_filter)
            stats = get_settlement_statistics(year_filter, project_filter)
            summary = {
                'total_count': stats['total_count'],
                'total_amount': stats['total_amount'],
                'settlement_rate': stats['settlement_rate'],
                'pending_count': stats['pending_count'],
            }
        else:
            return JsonResponse({'success': False, 'message': '不支持的统计模块'}, status=400)
        
        # 分页处理
        paginator = Paginator(details, page_size)
        page_obj = paginator.get_page(page)
        
        # 构建响应数据
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
        return JsonResponse({
            'success': False,
            'message': f'获取数据失败: {str(e)}'
        }, status=500)


@require_http_methods(['GET'])
def statistics_detail_page(request, module):
    """
    统计数据详情页面 - 完整的列表页面
    
    Args:
        module: 统计模块 (procurement/contract/payment/settlement)
    """
    try:
        # 解析筛选参数
        global_filters = _resolve_global_filters(request)
        year_filter = global_filters['year_filter']
        project_codes = global_filters['project_list']
        project_filter = project_codes if project_codes else None
        
        page = request.GET.get('page', 1)
        page_size = _get_page_size(request, default=20, max_size=100)
        
        # 获取筛选配置
        year_context = resolve_monitoring_year(request)
        year_context['selected_year_value'] = global_filters['year_value']
        year_context['year_filter'] = year_filter
        filter_config = get_monitoring_filter_config(request, year_context=year_context)
        
        # 根据模块获取详情数据和统计汇总
        if module == 'procurement':
            from project.services.statistics import get_procurement_details, get_procurement_statistics
            details = get_procurement_details(year_filter, project_filter)
            stats = get_procurement_statistics(year_filter, project_filter)
            page_title = '采购统计详情'
            template_name = 'monitoring/statistics_procurement_details.html'
        elif module == 'contract':
            from project.services.statistics import get_contract_details, get_contract_statistics
            details = get_contract_details(year_filter, project_filter)
            stats = get_contract_statistics(year_filter, project_filter)
            page_title = '合同统计详情'
            template_name = 'monitoring/statistics_contract_details.html'
        elif module == 'payment':
            from project.services.statistics import get_payment_details, get_payment_statistics
            details = get_payment_details(year_filter, project_filter)
            stats = get_payment_statistics(year_filter, project_filter)
            page_title = '付款统计详情'
            template_name = 'monitoring/statistics_payment_details.html'
        elif module == 'settlement':
            from project.services.statistics import get_settlement_details, get_settlement_statistics
            details = get_settlement_details(year_filter, project_filter)
            stats = get_settlement_statistics(year_filter, project_filter)
            page_title = '结算统计详情'
            template_name = 'monitoring/statistics_settlement_details.html'
        else:
            messages.error(request, '不支持的统计模块')
            return redirect('statistics_view')
        
        # 分页处理
        paginator = Paginator(details, page_size)
        page_obj = paginator.get_page(page)
        
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
        messages.error(request, f'加载详情页面失败: {str(e)}')
        return redirect('statistics_view')


@require_http_methods(['GET'])
def statistics_detail_export(request, module):
    """
    统计数据详情导出 - 导出Excel文件
    
    Args:
        module: 统计模块 (procurement/contract/payment/settlement)
    """
    try:
        # 解析筛选参数
        global_filters = _resolve_global_filters(request)
        year_filter = global_filters['year_filter']
        project_codes = global_filters['project_list']
        project_filter = project_codes if project_codes else None
        
        # 根据模块获取详情数据
        if module == 'procurement':
            from project.services.statistics import get_procurement_details
            details = get_procurement_details(year_filter, project_filter)
            filename = f'采购统计详情_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            columns = [
                ('采购编号', 'procurement_code'),
                ('项目名称', 'project_name'),
                ('项目编码', 'project_code'),
                ('采购单位', 'procurement_unit'),
                ('中标单位', 'winning_bidder'),
                ('采购方式', 'procurement_method'),
                ('采购类别', 'procurement_category'),
                ('预算金额(元)', 'budget_amount'),
                ('中标金额(元)', 'winning_amount'),
                ('控制价(元)', 'control_price'),
                ('节约金额(元)', 'savings_amount'),
                ('节约率(%)', 'savings_rate'),
                ('结果公示发布时间', 'result_publicity_release_date'),
                ('归档日期', 'archive_date'),
            ]
        elif module == 'contract':
            from project.services.statistics import get_contract_details
            details = get_contract_details(year_filter, project_filter)
            filename = f'合同统计详情_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            columns = [
                ('合同编号', 'contract_code'),
                ('合同序号', 'contract_sequence'),
                ('合同名称', 'contract_name'),
                ('文件定位', 'file_positioning'),
                ('合同来源', 'contract_source'),
                ('甲方', 'party_a'),
                ('乙方', 'party_b'),
                ('合同金额(元)', 'contract_amount'),
                ('签订日期', 'signing_date'),
                ('累计付款(元)', 'total_paid'),
                ('付款笔数', 'payment_count'),
                ('付款比例(%)', 'payment_ratio'),
                ('归档日期', 'archive_date'),
                ('项目编码', 'project_code'),
                ('项目名称', 'project_name'),
            ]
        elif module == 'payment':
            from project.services.statistics import get_payment_details
            details = get_payment_details(year_filter, project_filter)
            filename = f'付款统计详情_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            columns = [
                ('付款编号', 'payment_code'),
                ('付款金额(元)', 'payment_amount'),
                ('付款日期', 'payment_date'),
                ('是否结算', 'is_settled'),
                ('结算价(元)', 'settlement_amount'),
                ('关联合同编号', 'contract_code'),
                ('关联合同序号', 'contract_sequence'),
                ('合同名称', 'contract_name'),
                ('乙方', 'party_b'),
                ('项目编码', 'project_code'),
                ('项目名称', 'project_name'),
            ]
        elif module == 'settlement':
            from project.services.statistics import get_settlement_details
            details = get_settlement_details(year_filter, project_filter)
            filename = f'结算统计详情_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            columns = [
                ('合同编号', 'contract_code'),
                ('合同名称', 'contract_name'),
                ('乙方', 'party_b'),
                ('签订日期', 'signing_date'),
                ('合同金额(元)', 'contract_amount'),
                ('结算金额(元)', 'settlement_amount'),
                ('差异金额(元)', 'variance'),
                ('差异率(%)', 'variance_rate'),
                ('结算日期', 'payment_date'),
                ('项目编码', 'project_code'),
                ('项目名称', 'project_name'),
            ]
        else:
            messages.error(request, '不支持的统计模块')
            return redirect('statistics_view')
        
        # 数据量检查
        if len(details) > 10000:
            messages.warning(request, f'数据量较大({len(details)}条),建议使用筛选条件缩小范围后再导出')
            return redirect('statistics_view')
        
        # 使用pandas生成Excel
        data_for_export = []
        for item in details:
            row = {}
            for col_name, col_key in columns:
                value = item.get(col_key, '')
                # 处理日期格式
                if isinstance(value, (date, datetime)):
                    value = value.strftime('%Y-%m-%d')
                # 处理布尔值
                elif isinstance(value, bool):
                    value = '是' if value else '否'
                row[col_name] = value
            data_for_export.append(row)
        
        df = pd.DataFrame(data_for_export)
        
        # 创建Excel文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='详情数据', index=False)
        
        output.seek(0)
        
        # 返回文件
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        messages.error(request, f'导出失败: {str(e)}')
        return redirect('statistics_view')


# ==================== 级联选择器API ====================

def api_projects_list(request):
    """项目列表API - 支持搜索和分页"""
    search = request.GET.get('search', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    
    projects = Project.objects.all()
    
    if search:
        projects = projects.filter(
            Q(project_code__icontains=search) |
            Q(project_name__icontains=search)
        )
    
    paginator = Paginator(projects, page_size)
    page_obj = paginator.get_page(page)
    
    data = [{
        'id': project.project_code,
        'project_code': project.project_code,
        'project_name': project.project_name,
        'display_text': f"{project.project_code} - {project.project_name}"
    } for project in page_obj]
    
    return JsonResponse({
        'success': True,
        'data': data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })


def api_procurements_list(request):
    """采购列表API - 支持项目筛选和搜索"""
    search = request.GET.get('search', '')
    project = request.GET.get('project', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    
    procurements = Procurement.objects.select_related('project')
    
    if project:
        procurements = procurements.filter(project__project_code=project)
    
    if search:
        procurements = procurements.filter(
            Q(procurement_code__icontains=search) |
            Q(project_name__icontains=search)
        )
    
    paginator = Paginator(procurements, page_size)
    page_obj = paginator.get_page(page)
    
    data = [{
        'id': procurement.procurement_code,
        'procurement_code': procurement.procurement_code,
        'project_name': procurement.project_name,
        'project_code': procurement.project.project_code if procurement.project else '',
        'display_text': f"{procurement.procurement_code} - {procurement.project_name}"
    } for procurement in page_obj]
    
    return JsonResponse({
        'success': True,
        'data': data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })


def api_contracts_list(request):
    """合同列表API - 支持项目和采购筛选"""
    search = request.GET.get('search', '')
    project = request.GET.get('project_id', '') or request.GET.get('project', '')
    procurement = request.GET.get('procurement', '')
    file_positioning = request.GET.get('file_positioning', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    
    contracts = Contract.objects.select_related('project', 'procurement')
    
    if project:
        contracts = contracts.filter(project__project_code=project)
    
    if procurement:
        contracts = contracts.filter(procurement__procurement_code=procurement)
    
    if file_positioning:
        contracts = contracts.filter(file_positioning=file_positioning)
    
    if search:
        contracts = contracts.filter(
            Q(contract_code__icontains=search) |
            Q(contract_name__icontains=search) |
            Q(contract_sequence__icontains=search)
        )
    
    paginator = Paginator(contracts, page_size)
    page_obj = paginator.get_page(page)
    
    data = [{
        'id': contract.contract_code,
        'contract_code': contract.contract_code,
        'contract_name': contract.contract_name,
        'contract_sequence': contract.contract_sequence or '',
        'file_positioning': contract.file_positioning,
        'project_code': contract.project.project_code if contract.project else '',
        'project_name': contract.project.project_name if contract.project else '',
        'procurement_code': contract.procurement.procurement_code if contract.procurement else '',
        'display_text': f"{contract.contract_sequence or contract.contract_code} - {contract.contract_name}"
    } for contract in page_obj]
    
    return JsonResponse({
        'success': True,
        'data': data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })
