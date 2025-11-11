from typing import Any

from django.core.paginator import Paginator
from django.db.models import (
    Count,
    Sum,
    Q,
    OuterRef,
    Subquery,
    Value,
    DecimalField,
)
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Project
from contract.models import Contract
from procurement.models import Procurement
from payment.models import Payment

from project.utils.filters import apply_text_filter, apply_multi_field_search
from project.views_helpers import _resolve_global_filters, _get_page_size


def project_list(request):
    """项目列表页面（已抽取至独立模块）。"""
    global_filters = _resolve_global_filters(request)

    search_query = request.GET.get('q', '')
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
    """项目详情页面（已抽取至独立模块）。"""
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
    total_contract_amount = all_contracts.aggregate(Sum('contract_amount'))['contract_amount__sum'] or 0

    # 累计付款
    total_paid = all_payments.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0

    # 付款笔数
    payment_count = all_payments.count()

    # 结算数量（综合统计：Settlement表 + Payment表中的结算标记）
    settlement_count = Contract.objects.filter(
        Q(project=project) & (
            Q(settlement__isnull=False) |
            Q(payments__is_settled=True) |
            Q(payments__settlement_amount__isnull=False)
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
        'procurement_count': procurement_count,
        'contract_count': contract_count,
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

