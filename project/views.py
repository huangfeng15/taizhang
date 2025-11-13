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
import json
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
import project.views_helpers as _views_helpers
import project.views_projects as _views_projects
import project.views_contracts as _views_contracts
import project.views_procurements as _views_procurements
import project.views_payments as _views_payments
import project.views_statistics as _views_statistics
import project.views_reports as _views_reports
import project.views_monitoring as _views_monitoring
import project.views_ops as _views_ops
import project.views_api as _views_api


def _resolve_global_filters(request) -> Dict[str, Any]:
    return _views_helpers._resolve_global_filters(request)


def _extract_monitoring_filters(request):
    return _views_helpers._extract_monitoring_filters(request)


def _build_monitoring_filter_fields(filter_config, *, include_project=True, extra_fields=None):
    return _views_helpers._build_monitoring_filter_fields(filter_config, include_project=include_project, extra_fields=extra_fields)


def _build_pagination_querystring(request, excluded_keys=None, extra_params=None):
    return _views_helpers._build_pagination_querystring(request, excluded_keys=excluded_keys, extra_params=extra_params)


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
    'supplier_eval': {
        'long': {
            'filename': 'supplier_eval_import_template_long.csv',
            'headers': [
                '序号',
                '合同编号',
                '履约综合评价得分',
                '末次评价得分',
            ] + [f'{year}年度评价得分' for year in range(BASE_YEAR, get_current_year() + 2)] + [
                '第1次过程评价得分',
                '第2次过程评价得分',
                '备注',
                '模板说明',
            ],
            'notes': [
                '必填：序号*、合同编号*；其余可留空。',
                '评价编号由系统基于"EVAL-<合同编码>-<序号>"规则自动生成。',
                '分数范围0-100，可保留1-2位小数；留空不导入该项。',
                '可选：按年动态列（如"2024年度评价得分"）会自动识别，无需固定年份。',
                '可选：过程评价列（如"第1次过程评价得分"、"第2次过程评价得分"）会自动识别。',
                '模板说明列可删除，不影响导入。'
            ],
        },
    },
}


def _get_page_size(request, default=20, max_size=200):
    return _views_helpers._get_page_size(request, default=default, max_size=max_size)


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
    return _views_projects.project_list(request)


def project_detail(request, project_code):
    return _views_projects.project_detail(request, project_code)


def contract_list(request):
    return _views_contracts.contract_list(request)


def contract_list_enhanced(request):
    return _views_contracts.contract_list_enhanced(request)


def contract_detail(request, contract_code):
    return _views_contracts.contract_detail(request, contract_code)


def procurement_list(request):
    return _views_procurements.procurement_list(request)


def procurement_detail(request, procurement_code):
    return _views_procurements.procurement_detail(request, procurement_code)


def payment_list(request):
    return _views_payments.payment_list(request)


def payment_detail(request, payment_code):
    return _views_payments.payment_detail(request, payment_code)


@require_http_methods(["GET", "POST", "DELETE", "PUT"])
def database_management(request):
    return _views_ops.database_management(request)


@require_http_methods(['GET'])
def download_import_template(request):
    return _views_ops.download_import_template(request)


@csrf_exempt
@require_POST
def batch_delete_contracts(request):
    return _views_ops.batch_delete_contracts(request)


@csrf_exempt
@require_POST
def batch_delete_payments(request):
    return _views_ops.batch_delete_payments(request)


@csrf_exempt
@require_POST
def batch_delete_procurements(request):
    return _views_ops.batch_delete_procurements(request)


@csrf_exempt
@require_POST
def import_data(request):
    return _views_ops.import_data(request)


@csrf_exempt
@require_POST
def batch_delete_projects(request):
    return _views_ops.batch_delete_projects(request)


@require_http_methods(['GET', 'POST'])
def export_project_data(request):
    return _views_ops.export_project_data(request)


@csrf_exempt
@require_POST
def import_project_data(request):
    return _views_ops.import_project_data(request)


@require_POST
def restore_database_no_auth(request):
    return _views_ops.restore_database_no_auth(request)


def _generate_project_excel(project, user):
    from project.services.export_service import generate_project_excel
    return generate_project_excel(project, user)


# ==================== 监控与报表功能 ====================

from django.contrib.auth.decorators import login_required




def archive_monitor(request):
    return _views_monitoring.archive_monitor(request)

def update_monitor(request):
    return _views_monitoring.update_monitor(request)

def completeness_check(request):
    return _views_monitoring.completeness_check(request)
def statistics_view(request):
    return _views_statistics.statistics_view(request)


def ranking_view(request):
    return _views_statistics.ranking_view(request)


def generate_report(request):
    return _views_reports.generate_report(request)


def report_preview(request):
    return _views_reports.report_preview(request)


def report_export(request):
    return _views_reports.report_export(request)


def monitoring_cockpit(request):
    return _views_monitoring.monitoring_cockpit(request)














# ==================== 专业Word报告生成功能 ====================

@require_http_methods(['GET', 'POST'])
def generate_professional_report(request):
    return _views_reports.generate_professional_report(request)




# ==================== 前端编辑功能 ====================

@require_http_methods(['GET', 'POST'])
def project_edit(request, project_code):
    return _views_projects.project_edit(request, project_code)


@require_http_methods(['GET', 'POST'])
def contract_edit(request, contract_code):
    return _views_contracts.contract_edit(request, contract_code)


@require_http_methods(['GET', 'POST'])
def procurement_edit(request, procurement_code):
    return _views_procurements.procurement_edit(request, procurement_code)


@require_http_methods(['GET', 'POST'])
def payment_edit(request, payment_code):
    return _views_payments.payment_edit(request, payment_code)



@require_http_methods(['GET', 'POST'])
def procurement_create(request):
    return _views_procurements.procurement_create(request)


@require_http_methods(['GET', 'POST'])
def contract_create(request):
    return _views_contracts.contract_create(request)


@require_http_methods(['GET', 'POST'])
def payment_create(request):
    return _views_payments.payment_create(request)


@require_http_methods(['GET', 'POST'])
def project_create(request):
    return _views_projects.project_create(request)


# ==================== 统计数据详情查看功能 ====================

@require_http_methods(['GET'])
def statistics_detail_api(request, module):
    return _views_statistics.statistics_detail_api(request, module)


@require_http_methods(['GET'])
def statistics_detail_page(request, module):
    return _views_statistics.statistics_detail_page(request, module)


@require_http_methods(['GET'])
def statistics_detail_export(request, module):
    return _views_statistics.statistics_detail_export(request, module)


# ==================== 级联选择器API ====================

def api_projects_list(request):
    return _views_api.api_projects_list(request)


def api_procurements_list(request):
    return _views_api.api_procurements_list(request)


def api_contracts_list(request):
    return _views_api.api_contracts_list(request)


@staff_member_required
def completeness_field_config(request):
    return _views_monitoring.completeness_field_config(request)


@staff_member_required
@require_POST
def update_completeness_field_config(request):
    return _views_monitoring.update_completeness_field_config(request)


def user_manual(request):
    """用户使用手册页面"""
    return render(request, 'user_manual.html')
