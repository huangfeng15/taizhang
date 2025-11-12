
"""
供应商管理模块 - 视图层
提供供应商履约评价、承接项目、约谈记录的展示和管理
"""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from decimal import Decimal

from supplier_eval.models import SupplierEvaluation, SupplierInterview
from supplier_eval.services import SupplierAnalysisService
from contract.models import Contract
from project.utils.filters import apply_text_filter, apply_multi_field_search


def _get_page_size(request, default=20, max_size=200):
    """解析分页大小,限制范围避免异常输入"""
    try:
        size = int(request.GET.get('page_size', default))
    except (TypeError, ValueError):
        return default
    return max(1, min(size, max_size))


def _resolve_global_filters(request):
    """
    统一解析全局筛选参数,兼容旧字段
    
    Returns:
        {
            "year_value": "2024" 或 "all",
            "year_filter": int | None,
            "project": "PRJ001" 或 "",
            "project_list": ["PRJ001"] 或 []
        }
    """
    from django.utils import timezone
    from project.constants import get_current_year

    current_year = get_current_year()
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


@login_required
@require_http_methods(['GET'])
def supplier_evaluation_list(request):
    """
    供应商履约评价列表页面（主列表）
    
    功能:
    - 展示每个供应商在指定年度的最新履约评价
    - 支持年度切换查看
    - 支持按供应商名称搜索
    - 支持按评分等级筛选
    - 点击"详情"可查看供应商的历史所有评价记录
    """
    from django.utils import timezone
    from project.constants import get_current_year
    
    # 获取筛选参数
    search_query = request.GET.get('q', '')
    score_level_filter = request.GET.get('score_level', '')  # excellent/good/qualified/unqualified
    year_filter = request.GET.get('year', '')
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20)
    
    # 确定显示年度（默认当前年度）
    current_year = get_current_year()
    try:
        display_year = int(year_filter) if year_filter else current_year
    except (ValueError, TypeError):
        display_year = current_year
    
    # 获取指定年度每个供应商的最新评价
    latest_evaluations = SupplierAnalysisService.get_latest_evaluations_by_year(display_year)
    
    # 搜索过滤（供应商名称）
    if search_query:
        latest_evaluations = [
            item for item in latest_evaluations
            if search_query.lower() in item['supplier_name'].lower()
        ]
    
    # 评分等级过滤
    if score_level_filter == 'excellent':
        latest_evaluations = [item for item in latest_evaluations if item['comprehensive_score'] and item['comprehensive_score'] >= 90]
    elif score_level_filter == 'good':
        latest_evaluations = [item for item in latest_evaluations if item['comprehensive_score'] and 80 <= item['comprehensive_score'] < 90]
    elif score_level_filter == 'qualified':
        latest_evaluations = [item for item in latest_evaluations if item['comprehensive_score'] and 70 <= item['comprehensive_score'] < 80]
    elif score_level_filter == 'unqualified':
        latest_evaluations = [item for item in latest_evaluations if item['comprehensive_score'] and item['comprehensive_score'] < 70]
    
    # 分页
    paginator = Paginator(latest_evaluations, page_size)
    page_obj = paginator.get_page(page)
    
    # 获取统计数据（基于当前年度）
    year_evaluations = SupplierEvaluation.objects.filter(
        created_at__year=display_year,
        comprehensive_score__isnull=False
    )
    total = year_evaluations.count()
    excellent = year_evaluations.filter(comprehensive_score__gte=90).count()
    good = year_evaluations.filter(comprehensive_score__gte=80, comprehensive_score__lt=90).count()
    unqualified = year_evaluations.filter(comprehensive_score__lt=70).count()
    
    stats = {
        'total': total,
        'excellent': excellent,
        'good': good,
        'unqualified': unqualified,
    }
    
    # 获取可选年度列表（从评价记录中提取）
    available_years = SupplierEvaluation.objects.dates('created_at', 'year', order='DESC')
    year_choices = [year.year for year in available_years]
    if not year_choices:
        year_choices = [current_year]
    
    context = {
        'page_title': '供应商履约评价',
        'evaluations': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'score_level_filter': score_level_filter,
        'display_year': display_year,
        'year_choices': year_choices,
        'stats': stats,
        'score_level_choices': [
            ('', '全部等级'),
            ('excellent', '优秀(≥90分)'),
            ('good', '良好(≥80分)'),
            ('qualified', '合格(≥70分)'),
            ('unqualified', '不合格(<70分)'),
        ],
    }
    return render(request, 'supplier/evaluation_list.html', context)


@login_required
@require_http_methods(['GET'])
def supplier_evaluation_detail(request, supplier_name):
    """
    供应商履约评价详情页面
    
    功能:
    - 展示指定供应商历史上所有合同的完整履约评价记录
    - 跨年度的所有评价数据
    - 每份合同的详细评价信息和时间线
    - 显示评价趋势图表
    """
    import json
    from collections import defaultdict
    
    # 获取该供应商的所有历史评价记录
    all_evaluations = SupplierAnalysisService.get_supplier_all_evaluations(supplier_name)
    
    # 分页
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20)
    paginator = Paginator(all_evaluations, page_size)
    page_obj = paginator.get_page(page)
    
    # 获取供应商汇总信息
    supplier_summary = SupplierAnalysisService.get_supplier_summary(supplier_name)
    summary = supplier_summary[0] if supplier_summary else None
    
    # 获取评价统计
    evaluation_stats = SupplierAnalysisService.get_evaluation_statistics(supplier_name)
    
    # 准备趋势数据（按年度分组）
    trend_data = defaultdict(list)
    for item in all_evaluations:
        year = item['year']
        if item['comprehensive_score']:
            trend_data[year].append(float(item['comprehensive_score']))
    
    # 计算每年的平均分
    trend_chart_data = []
    for year in sorted(trend_data.keys()):
        avg_score = sum(trend_data[year]) / len(trend_data[year])
        trend_chart_data.append({
            'year': year,
            'avg_score': round(avg_score, 2),
            'count': len(trend_data[year])
        })
    
    # 转换为JSON字符串供模板使用
    trend_chart_json = json.dumps(trend_chart_data)
    
    context = {
        'page_title': f'供应商履约评价详情 - {supplier_name}',
        'supplier_name': supplier_name,
        'evaluations': page_obj,
        'page_obj': page_obj,
        'summary': summary,
        'stats': evaluation_stats,
        'trend_chart_json': trend_chart_json,
        'total_evaluations': len(all_evaluations),
    }
    return render(request, 'supplier/evaluation_detail.html', context)


@login_required
@require_http_methods(['GET'])
def supplier_contract_list(request):
    """
    供应商承接项目查询页面
    
    功能:
    - 查询供应商承接的所有合同
    - 显示合同总金额(含补充协议)
    - 显示付款进度和付款笔数
    - 支持按供应商名称、合同状态筛选
    """
    # 获取筛选参数
    search_query = request.GET.get('q', '')
    supplier_name = request.GET.get('supplier_name') or request.GET.get('supplier', '')
    contract_status = request.GET.get('contract_status') or request.GET.get('status', '')
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20)

    # 如果没有指定供应商,显示汇总列表
    if not supplier_name and not search_query:
        # 获取所有供应商汇总
        supplier_list = SupplierAnalysisService.get_supplier_summary()
        
        # 分页
        paginator = Paginator(supplier_list, page_size)
        page_obj = paginator.get_page(page)
        
        context = {
            'page_title': '供应商承接项目查询',
            'suppliers': page_obj,
            'contracts': page_obj,
            'page_obj': page_obj,
            'is_summary_view': True,
            'search_query': search_query,
        }
        return render(request, 'supplier/contract_list.html', context)
    
    # 显示特定供应商的合同详情
    target_supplier = supplier_name or search_query
    
    # 获取合同列表
    contracts = SupplierAnalysisService.get_supplier_contracts(
        target_supplier,
        contract_status=contract_status if contract_status != 'all' else None
    )
    
    # 分页
    paginator = Paginator(contracts, page_size)
    page_obj = paginator.get_page(page)
    
    # 计算汇总数据
    total_amount = sum(c['contract_total_amount'] or 0 for c in contracts)
    total_paid = sum(c['total_paid'] or 0 for c in contracts)
    ongoing_count = sum(1 for c in contracts if c['is_ongoing'])
    
    context = {
        'page_title': f'供应商承接项目 - {target_supplier}',
        'contracts': page_obj,
        'page_obj': page_obj,
        'supplier_name': target_supplier,
        'contract_status': contract_status,
        'is_summary_view': False,
        'total_contracts': len(contracts),
        'ongoing_count': ongoing_count,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'status_choices': [
            ('all', '全部合同'),
            ('ongoing', '在执行'),
            ('settled', '已结算'),
        ],
    }
    return render(request, 'supplier/contract_list.html', context)


@login_required
@require_http_methods(['GET'])
def supplier_interview_list(request):
    """
    供应商约谈记录列表页面
    
    功能:
    - 展示所有约谈记录
    - 支持按供应商名称、约谈类型筛选
    - 支持按跟进状态筛选
    - 突出显示违约约谈
    """
    # 获取筛选参数
    search_query = request.GET.get('q', '')
    supplier_name_filter = request.GET.get('supplier_name', '')
    interview_type_filter = request.GET.get('interview_type', '')
    status_filter = request.GET.get('status', '')
    has_contract_filter = request.GET.get('has_contract', '')
    page = request.GET.get('page', 1)
    page_size = _get_page_size(request, default=20)
    
    # 基础查询
    interviews = SupplierInterview.objects.select_related('contract')
    
    # 搜索过滤
    if search_query:
        interviews = interviews.filter(
            Q(supplier_name__icontains=search_query) |
            Q(interviewer__icontains=search_query) |
            Q(reason__icontains=search_query)
        )
    
    # 供应商名称过滤
    interviews = apply_text_filter(interviews, 'supplier_name', supplier_name_filter)
    
    # 约谈类型过滤
    if interview_type_filter:
        interviews = interviews.filter(interview_type=interview_type_filter)
    
    # 跟进状态过滤
    if status_filter:
        interviews = interviews.filter(status=status_filter)
    
    # 是否签约供应商过滤
    if has_contract_filter:
        normalized = has_contract_filter.lower()
        if normalized == 'true':
            interviews = interviews.filter(has_contract=True)
        elif normalized == 'false':
            interviews = interviews.filter(has_contract=False)
    
    # 按约谈日期降序排序
    interviews = interviews.order_by('-interview_date', '-created_at')
    
    # 分页
    paginator = Paginator(interviews, page_size)
    page_obj = paginator.get_page(page)
    
    # 获取统计数据
    stats = SupplierAnalysisService.get_interview_statistics()
    
    context = {
        'page_title': '供应商约谈记录',
        'interviews': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'supplier_name_filter': supplier_name_filter,
        'interview_type_filter': interview_type_filter,
        'status_filter': status_filter,
        'has_contract_filter': has_contract_filter,
        'stats': stats,
        'interview_type_choices': SupplierInterview.INTERVIEW_TYPE_CHOICES,
        'status_choices': SupplierInterview.STATUS_CHOICES,
        'has_contract_choices': [
            ('', '全部'),
            ('true', '已签约'),
            ('false', '未签约'),
        ],
    }
    return render(request, 'supplier/interview_list.html', context)


@login_required
@require_http_methods(['GET'])
def supplier_interview_detail(request, interview_id):
    """
    供应商约谈记录详情页面
    
    功能:
    - 查看约谈记录的完整详情
    - 显示关联合同信息
    - 显示历史约谈记录
    """
    interview = get_object_or_404(SupplierInterview, id=interview_id)
    
    # 获取同一供应商的其他约谈记录
    related_interviews = SupplierInterview.objects.filter(
        supplier_name=interview.supplier_name
    ).exclude(id=interview_id).order_by('-interview_date')[:10]
    
    context = {
        'page_title': f'约谈记录详情 - {interview.supplier_name}',
        'interview': interview,
        'related_interviews': related_interviews,
    }
    return render(request, 'supplier/interview_detail.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def supplier_interview_create(request):
    """
    创建供应商约谈记录 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from supplier_eval.forms import SupplierInterviewForm
    
    if request.method == 'POST':
        form = SupplierInterviewForm(request.POST)
        if form.is_valid():
            try:
                interview = form.save(commit=False)
                if request.user.is_authenticated:
                    interview.created_by = request.user.username
                interview.save()
                
                return JsonResponse({
                    'success': True,
                    'message': '约谈记录创建成功',
                    'interview_id': interview.id
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
            
            return JsonResponse({
                'success': False,
                'message': '表单验证失败:\n' + '\n'.join(error_messages),
                'errors': form.errors
            }, status=400)
    
    # GET请求 - 返回表单HTML
    form = SupplierInterviewForm()
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '新增约谈记录',
        'submit_url': '/supplier/interviews/create/',
        'module_type': 'supplier_interview',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def supplier_interview_edit(request, interview_id):
    """
    编辑供应商约谈记录 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from supplier_eval.forms import SupplierInterviewForm
    
    try:
        interview = SupplierInterview.objects.get(id=interview_id)
    except SupplierInterview.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': '约谈记录不存在'
            }, status=404)
        return HttpResponse('约谈记录不存在', status=404)
    
    if request.method == 'POST':
        form = SupplierInterviewForm(request.POST, instance=interview)
        if form.is_valid():
            try:
                interview = form.save(commit=False)
                if request.user.is_authenticated:
                    interview.updated_by = request.user.username
                interview.save()
                
                return JsonResponse({
                    'success': True,
                    'message': '约谈记录更新成功'
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
            
            return JsonResponse({
                'success': False,
                'message': '表单验证失败:\n' + '\n'.join(error_messages),
                'errors': form.errors
            }, status=400)
    
    # GET请求 - 返回表单HTML
    form = SupplierInterviewForm(instance=interview)
    
    # 准备初始显示文本
    initial_display = {}
    if interview.contract:
        initial_display['contract'] = f"{interview.contract.contract_sequence or interview.contract.contract_code} - {interview.contract.contract_name}"
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '编辑约谈记录',
        'submit_url': f'/supplier/interviews/{interview_id}/edit/',
        'module_type': 'supplier_interview',
        'initial_display': initial_display,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def supplier_evaluation_create(request):
    """
    创建供应商履约评价 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from supplier_eval.forms import SupplierEvaluationForm
    
    if request.method == 'POST':
        form = SupplierEvaluationForm(request.POST)
        if form.is_valid():
            try:
                evaluation = form.save(commit=False)
                
                # 自动从合同获取供应商名称（如果未填写）
                if evaluation.contract and not evaluation.supplier_name:
                    evaluation.supplier_name = evaluation.contract.party_b
                
                if request.user.is_authenticated:
                    evaluation.created_by = request.user.username
                
                # 注意：评价编号会在模型的 save() 方法中自动生成（如果用户未填写）
                evaluation.save()
                
                return JsonResponse({
                    'success': True,
                    'message': '履约评价创建成功',
                    'evaluation_code': evaluation.evaluation_code
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
            
            return JsonResponse({
                'success': False,
                'message': '表单验证失败:\n' + '\n'.join(error_messages),
                'errors': form.errors
            }, status=400)
    
    # GET请求 - 返回表单HTML
    form = SupplierEvaluationForm()
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '新增履约评价',
        'submit_url': '/supplier/evaluations/create/',
        'module_type': 'supplier_eval',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def supplier_evaluation_edit(request, evaluation_code):
    """
    编辑供应商履约评价 - AJAX接口
    GET: 返回表单HTML
    POST: 保存数据
    """
    from supplier_eval.forms import SupplierEvaluationForm
    
    try:
        evaluation = SupplierEvaluation.objects.get(evaluation_code=evaluation_code)
    except SupplierEvaluation.DoesNotExist:
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'message': '履约评价记录不存在'
            }, status=404)
        return HttpResponse('履约评价记录不存在', status=404)
    
    if request.method == 'POST':
        form = SupplierEvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            try:
                evaluation = form.save(commit=False)
                
                # 自动从合同获取供应商名称
                if evaluation.contract and not evaluation.supplier_name:
                    evaluation.supplier_name = evaluation.contract.party_b
                
                if request.user.is_authenticated:
                    evaluation.updated_by = request.user.username
                
                evaluation.save()
                
                return JsonResponse({
                    'success': True,
                    'message': '履约评价更新成功'
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
            
            return JsonResponse({
                'success': False,
                'message': '表单验证失败:\n' + '\n'.join(error_messages),
                'errors': form.errors
            }, status=400)
    
    # GET请求 - 返回表单HTML
    form = SupplierEvaluationForm(instance=evaluation)
    
    # 准备初始显示文本
    initial_display = {}
    if evaluation.contract:
        initial_display['contract'] = f"{evaluation.contract.contract_sequence or evaluation.contract.contract_code} - {evaluation.contract.contract_name}"
    
    return render(request, 'components/edit_form.html', {
        'form': form,
        'title': '编辑履约评价',
        'submit_url': f'/supplier/evaluations/{evaluation_code}/edit/',
        'module_type': 'supplier_eval',
        'initial_display': initial_display,
    })
