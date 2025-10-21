from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Sum, Q
from django.core.serializers import serialize
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.core.paginator import Paginator
from io import StringIO
import json
import os
import tempfile

from .models import Project
from contract.models import Contract
from procurement.models import Procurement
from payment.models import Payment


def dashboard(request):
    """数据概览页面"""
    # 统计数据 - 每次访问时实时计算
    stats = {
        'project_count': Project.objects.count(),
        'procurement_count': Procurement.objects.count(),
        'contract_count': Contract.objects.count(),
        'total_amount': Contract.objects.aggregate(Sum('contract_amount'))['contract_amount__sum'] or 0,
    }
    
    # 项目列表(前5个) - 实时计算每个项目的统计数据
    projects_queryset = Project.objects.order_by('-created_at')[:5]
    projects = []
    for project in projects_queryset:
        # 实时计算采购数量
        procurement_count = Procurement.objects.filter(project=project).count()
        # 实时计算合同数量
        contract_count = Contract.objects.filter(project=project).count()
        # 实时计算合同总额
        contract_total = Contract.objects.filter(project=project).aggregate(
            total=Sum('contract_amount')
        )['total'] or 0
        
        # 添加计算后的属性
        project.procurement_count = procurement_count
        project.contract_count = contract_count
        project.contract_total = contract_total
        projects.append(project)
    
    # 最近采购(前10个)
    recent_procurements = Procurement.objects.select_related('project').order_by('-bid_opening_date')[:10]
    
    context = {
        'stats': stats,
        'projects': projects,
        'recent_procurements': recent_procurements,
    }
    return render(request, 'dashboard.html', context)


def project_list(request):
    """项目列表页面"""
    # 获取过滤参数
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 20)
    
    # 高级筛选参数
    project_code_filter = request.GET.get('project_code', '')
    project_name_filter = request.GET.get('project_name', '')
    project_manager_filter = request.GET.get('project_manager', '')
    created_at_start = request.GET.get('created_at_start', '')
    created_at_end = request.GET.get('created_at_end', '')
    
    # 基础查询
    projects = Project.objects.all()
    
    # 搜索过滤
    if search_query:
        projects = projects.filter(
            Q(project_code__icontains=search_query) |
            Q(project_name__icontains=search_query) |
            Q(project_manager__icontains=search_query)
        )
    
    # 状态过滤
    if status_filter:
        projects = projects.filter(status=status_filter)
    
    # 高级筛选
    if project_code_filter:
        projects = projects.filter(project_code__icontains=project_code_filter)
    if project_name_filter:
        projects = projects.filter(project_name__icontains=project_name_filter)
    if project_manager_filter:
        projects = projects.filter(project_manager__icontains=project_manager_filter)
    if created_at_start:
        projects = projects.filter(created_at__gte=created_at_start)
    if created_at_end:
        projects = projects.filter(created_at__lte=created_at_end)
    
    projects = projects.order_by('-created_at')
    
    # 先分页
    paginator = Paginator(projects, page_size)
    page_obj = paginator.get_page(page)
    
    # 为每个项目实时计算统计数据
    projects_with_stats = []
    for project in page_obj:
        # 实时计算采购数量
        procurement_count = Procurement.objects.filter(project=project).count()
        # 实时计算合同数量
        contract_count = Contract.objects.filter(project=project).count()
        # 实时计算合同总额
        contract_total = Contract.objects.filter(project=project).aggregate(
            total=Sum('contract_amount')
        )['total'] or 0
        
        # 添加计算后的属性
        project.procurement_count = procurement_count
        project.contract_count = contract_count
        project.contract_total = contract_total
        projects_with_stats.append(project)
    
    # 更新page_obj的object_list
    page_obj.object_list = projects_with_stats
    
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
    
    # 实时计算总数量
    procurement_count = Procurement.objects.filter(project=project).count()
    contract_count = Contract.objects.filter(project=project).count()
    
    # 获取所有相关数据用于统计
    all_procurements = Procurement.objects.filter(project=project)
    all_contracts = Contract.objects.filter(project=project)
    all_payments = Payment.objects.filter(contract__project=project)
    
    # 计算统计数据
    # 合同总额
    total_contract_amount = all_contracts.aggregate(Sum('contract_amount'))['contract_amount__sum'] or 0
    
    # 累计付款
    total_paid = all_payments.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0
    
    # 付款笔数
    payment_count = all_payments.count()
    
    # 结算数量（综合统计：Settlement表 + Payment表中的结算标记）
    from settlement.models import Settlement
    from django.db.models import Q
    
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
    # 获取过滤参数
    search_query = request.GET.get('q', '')
    project_filter = request.GET.get('project', '')
    contract_type_filter = request.GET.get('contract_type', '')
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 20)
    
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
    payment_ratio_range = request.GET.get('payment_ratio_range', '')
    signing_date_start = request.GET.get('signing_date_start', '')
    signing_date_end = request.GET.get('signing_date_end', '')
    performance_guarantee_return_date_start = request.GET.get('performance_guarantee_return_date_start', '')
    performance_guarantee_return_date_end = request.GET.get('performance_guarantee_return_date_end', '')
    contract_amount_min = request.GET.get('contract_amount_min', '')
    contract_amount_max = request.GET.get('contract_amount_max', '')
    
    # 基础查询
    contracts = Contract.objects.select_related('project')
    
    # 搜索过滤
    if search_query:
        contracts = contracts.filter(
            Q(contract_code__icontains=search_query) |
            Q(contract_name__icontains=search_query) |
            Q(party_b__icontains=search_query)
        )
    
    # 项目过滤
    if project_filter:
        contracts = contracts.filter(project__project_code=project_filter)
    
    # 合同类型过滤
    if contract_type_filter:
        contracts = contracts.filter(contract_type=contract_type_filter)
    
    # 高级筛选
    if contract_code_filter:
        contracts = contracts.filter(contract_code__icontains=contract_code_filter)
    if contract_sequence_filter:
        contracts = contracts.filter(contract_sequence__icontains=contract_sequence_filter)
    if contract_name_filter:
        contracts = contracts.filter(contract_name__icontains=contract_name_filter)
    if party_a_filter:
        contracts = contracts.filter(party_a__icontains=party_a_filter)
    if party_b_filter:
        contracts = contracts.filter(party_b__icontains=party_b_filter)
    if party_b_contact_filter:
        contracts = contracts.filter(party_b_contact__icontains=party_b_contact_filter)
    if contract_officer_filter:
        contracts = contracts.filter(contract_officer__icontains=contract_officer_filter)
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
    
    # 注意：is_settled和payment_ratio筛选需要在数据处理后进行，因为它们依赖于Payment表的计算
    
    # 添加付款相关数据的注解
    contracts = contracts.annotate(
        total_paid_amount=Sum('payments__payment_amount'),
        payment_count=Count('payments', distinct=True)
    )
    
    contracts = contracts.order_by('-signing_date')
    
    # 预加载结算信息
    from settlement.models import Settlement
    settlement_dict = {
        s.main_contract.contract_code: s for s in Settlement.objects.select_related('main_contract')
    }
    
    # 预加载补充协议数据
    supplements_data = {}
    main_contracts = [c for c in contracts if c.contract_type == '主合同']
    if main_contracts:
        main_contract_codes = [c.contract_code for c in main_contracts]
        supplements = Contract.objects.filter(
            parent_contract__contract_code__in=main_contract_codes
        ).values('parent_contract__contract_code').annotate(
            supplements_total=Sum('contract_amount')
        )
        supplements_data = {
            s['parent_contract__contract_code']: s['supplements_total'] or 0
            for s in supplements
        }
    
    # 为每个合同添加额外的付款相关数据
    contract_data = []
    for contract in contracts:
        # 创建一个字典来存储所有需要的数据
        contract_info = {
            'contract': contract,
            'total_paid_amount': contract.total_paid_amount or 0,
            'payment_count': contract.payment_count or 0,
            'has_settlement': False,
            'settlement_amount': None,
            'payment_ratio': 0
        }
        
        # 从付款记录中获取结算信息
        # 检查该合同的任何一笔付款是否标记为已结算
        latest_payment = Payment.objects.filter(
            contract=contract,
            is_settled=True
        ).order_by('-payment_date').first()
        
        if latest_payment:
            contract_info['has_settlement'] = True
            contract_info['settlement_amount'] = latest_payment.settlement_amount
        
        # 同时也检查settlement模块(如果存在)
        if contract.contract_type == '主合同' and contract.contract_code in settlement_dict:
            settlement = settlement_dict[contract.contract_code]
            contract_info['has_settlement'] = True
            # 优先使用settlement模块的结算价,如果没有则使用付款记录的
            if settlement.final_amount:
                contract_info['settlement_amount'] = settlement.final_amount
        
        # 计算累计付款比例
        if contract.contract_type == '主合同':
            # 主合同的付款比例计算
            if contract_info['has_settlement'] and contract_info['settlement_amount']:
                # 有结算价，使用结算价作为基数
                if contract_info['settlement_amount'] > 0:
                    contract_info['payment_ratio'] = (contract_info['total_paid_amount'] / contract_info['settlement_amount']) * 100
            else:
                # 没有结算价，使用合同价+补充协议金额作为基数
                base_amount = contract.contract_amount or 0
                # 获取补充协议总额
                supplements_total = supplements_data.get(contract.contract_code, 0)
                base_amount += supplements_total
                
                if base_amount > 0:
                    contract_info['payment_ratio'] = (contract_info['total_paid_amount'] / base_amount) * 100
        else:
            # 补充协议或解除协议，使用自身合同价作为基数
            if contract.contract_amount and contract.contract_amount > 0:
                contract_info['payment_ratio'] = (contract_info['total_paid_amount'] / contract.contract_amount) * 100
        
        contract_data.append(contract_info)
    
    # 是否已结算筛选（在计算完成后进行）
    if has_settlement_filter:
        filtered_contract_data = []
        for contract_info in contract_data:
            if has_settlement_filter.lower() == 'true' and contract_info['has_settlement']:
                filtered_contract_data.append(contract_info)
            elif has_settlement_filter.lower() == 'false' and not contract_info['has_settlement']:
                filtered_contract_data.append(contract_info)
        contract_data = filtered_contract_data
    
    # 付款比例筛选（在计算完成后进行）
    if payment_ratio_range:
        filtered_contract_data = []
        for contract_info in contract_data:
            payment_ratio = contract_info['payment_ratio']
            # 解析范围 (例如: "0-50", "50-80", "80-100", "100-")
            if '-' in payment_ratio_range:
                parts = payment_ratio_range.split('-')
                min_ratio = float(parts[0]) if parts[0] else 0
                max_ratio = float(parts[1]) if parts[1] else float('inf')
                
                if min_ratio <= payment_ratio <= max_ratio:
                    filtered_contract_data.append(contract_info)
        contract_data = filtered_contract_data
    
    # 分页处理 - 对contract_data进行分页
    paginator = Paginator(contract_data, page_size)
    page_obj = paginator.get_page(page)
    
    # 获取所有项目用于过滤
    projects = Project.objects.all()
    
    context = {
        'contracts': page_obj,
        'page_obj': page_obj,
        'projects': projects,
        'search_query': search_query,
        'project_filter': project_filter,
        'contract_type_filter': contract_type_filter,
        'contract_types': Contract._meta.get_field('contract_type').choices,
    }
    return render(request, 'contract_list.html', context)


def contract_list_enhanced(request):
    """增强版合同列表页面 - 支持Vue.js交互"""
    # 获取所有合同数据（使用 only() 优化查询字段）
    contracts = Contract.objects.select_related('project').only(
        'contract_code', 'contract_name', 'contract_type', 'contract_source',
        'party_b', 'contract_amount', 'signing_date',
        'project__project_code', 'project__project_name'
    ).order_by('-signing_date')
    
    # 转换为JSON格式（使用列表推导式提高性能）
    contracts_data = [
        {
            'contract_code': c.contract_code,
            'contract_name': c.contract_name,
            'contract_type': c.contract_type,
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
    settlement = None
    if contract.contract_type == '主合同':
        try:
            settlement = contract.settlement
        except:
            settlement = None
    
    # 获取补充协议（如果是主合同）
    supplements = []
    if contract.contract_type == '主合同':
        supplements = contract.supplements.all().order_by('signing_date')
    
    # 获取履约评价
    evaluations = contract.evaluations.all() if hasattr(contract, 'evaluations') else []
    
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
    # 获取过滤参数
    search_query = request.GET.get('q', '')
    project_filter = request.GET.get('project', '')
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 20)
    
    # 高级筛选参数
    procurement_code_filter = request.GET.get('procurement_code', '')
    project_name_filter = request.GET.get('project_name', '')
    procurement_unit_filter = request.GET.get('procurement_unit', '')
    winning_bidder_filter = request.GET.get('winning_bidder', '')
    bid_opening_date_start = request.GET.get('bid_opening_date_start', '')
    bid_opening_date_end = request.GET.get('bid_opening_date_end', '')
    budget_amount_min = request.GET.get('budget_amount_min', '')
    budget_amount_max = request.GET.get('budget_amount_max', '')
    winning_amount_min = request.GET.get('winning_amount_min', '')
    winning_amount_max = request.GET.get('winning_amount_max', '')
    
    # 基础查询
    procurements = Procurement.objects.select_related('project')
    
    # 搜索过滤
    if search_query:
        procurements = procurements.filter(
            Q(procurement_code__icontains=search_query) |
            Q(project_name__icontains=search_query) |
            Q(winning_bidder__icontains=search_query)
        )
    
    # 项目过滤
    if project_filter:
        procurements = procurements.filter(project__project_code=project_filter)
    
    # 高级筛选
    if procurement_code_filter:
        procurements = procurements.filter(procurement_code__icontains=procurement_code_filter)
    if project_name_filter:
        procurements = procurements.filter(project_name__icontains=project_name_filter)
    if procurement_unit_filter:
        procurements = procurements.filter(procurement_unit__icontains=procurement_unit_filter)
    if winning_bidder_filter:
        procurements = procurements.filter(winning_bidder__icontains=winning_bidder_filter)
    if bid_opening_date_start:
        procurements = procurements.filter(bid_opening_date__gte=bid_opening_date_start)
    if bid_opening_date_end:
        procurements = procurements.filter(bid_opening_date__lte=bid_opening_date_end)
    if budget_amount_min:
        procurements = procurements.filter(budget_amount__gte=budget_amount_min)
    if budget_amount_max:
        procurements = procurements.filter(budget_amount__lte=budget_amount_max)
    if winning_amount_min:
        procurements = procurements.filter(winning_amount__gte=winning_amount_min)
    if winning_amount_max:
        procurements = procurements.filter(winning_amount__lte=winning_amount_max)
    
    procurements = procurements.order_by('-bid_opening_date')
    
    # 分页处理
    paginator = Paginator(procurements, page_size)
    page_obj = paginator.get_page(page)
    
    # 获取所有项目用于过滤
    projects = Project.objects.all()
    
    context = {
        'procurements': page_obj,
        'page_obj': page_obj,
        'projects': projects,
        'search_query': search_query,
        'project_filter': project_filter,
    }
    return render(request, 'procurement_list.html', context)


def procurement_detail(request, procurement_code):
    """采购详情页面"""
    procurement = get_object_or_404(Procurement, procurement_code=procurement_code)
    
    # 获取相关合同
    contracts = Contract.objects.filter(
        procurement=procurement
    ).order_by('-signing_date')
    
    context = {
        'procurement': procurement,
        'contracts': contracts,
    }
    return render(request, 'procurement_detail.html', context)


def payment_list(request):
    """付款列表页面"""
    # 获取过滤参数
    search_query = request.GET.get('q', '')
    contract_filter = request.GET.get('contract', '')
    project_filter = request.GET.get('project', '')
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 20)
    
    # 高级筛选参数
    payment_code_filter = request.GET.get('payment_code', '')
    contract_name_filter = request.GET.get('contract_name', '')
    payment_date_start = request.GET.get('payment_date_start', '')
    payment_date_end = request.GET.get('payment_date_end', '')
    payment_amount_min = request.GET.get('payment_amount_min', '')
    payment_amount_max = request.GET.get('payment_amount_max', '')
    is_settled_filter = request.GET.get('is_settled', '')
    
    # 基础查询
    payments = Payment.objects.select_related('contract', 'contract__project')
    
    # 搜索过滤
    if search_query:
        payments = payments.filter(
            Q(payment_code__icontains=search_query) |
            Q(contract__contract_name__icontains=search_query)
        )
    
    # 合同过滤
    if contract_filter:
        payments = payments.filter(contract__contract_code=contract_filter)
    
    # 项目过滤
    if project_filter:
        payments = payments.filter(contract__project__project_code=project_filter)
    
    # 高级筛选
    if payment_code_filter:
        payments = payments.filter(payment_code__icontains=payment_code_filter)
    if contract_name_filter:
        payments = payments.filter(contract__contract_name__icontains=contract_name_filter)
    if payment_date_start:
        payments = payments.filter(payment_date__gte=payment_date_start)
    if payment_date_end:
        payments = payments.filter(payment_date__lte=payment_date_end)
    if payment_amount_min:
        payments = payments.filter(payment_amount__gte=payment_amount_min)
    if payment_amount_max:
        payments = payments.filter(payment_amount__lte=payment_amount_max)
    if is_settled_filter:
        # 处理布尔值筛选
        is_settled = is_settled_filter.lower() == 'true'
        payments = payments.filter(is_settled=is_settled)
    
    payments = payments.order_by('-payment_date')
    
    # 分页处理
    paginator = Paginator(payments, page_size)
    page_obj = paginator.get_page(page)
    
    # 获取所有项目用于过滤（用于筛选）
    projects = Project.objects.all()
    
    # 获取所有合同用于过滤
    contracts = Contract.objects.all()
    
    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        'projects': projects,
        'contracts': contracts,
        'search_query': search_query,
        'contract_filter': contract_filter,
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



@require_POST
@csrf_exempt
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


@require_POST
@csrf_exempt
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


@require_POST
@csrf_exempt
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


@require_POST
@csrf_exempt
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
                detected_encoding = result['encoding']
                if result['confidence'] > 0.7:
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


@require_POST
@csrf_exempt
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
