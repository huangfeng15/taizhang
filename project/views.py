"""
项目管理视图
"""
from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from project.models import Project
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment


def dashboard(request):
    """数据概览页面"""
    # 统计数据
    stats = {
        'project_count': Project.objects.count(),
        'procurement_count': Procurement.objects.count(),
        'contract_count': Contract.objects.count(),
        'total_amount': Contract.objects.aggregate(
            total=Sum('contract_amount')
        )['total'] or 0,
    }
    
    # 项目列表及其统计信息
    projects = Project.objects.all()[:10]
    project_list = []
    for project in projects:
        project_list.append({
            'project_code': project.project_code,
            'project_name': project.project_name,
            'project_manager': project.project_manager,
            'status': project.status,
            'procurement_count': project.procurements.count(),
            'contract_count': project.contracts.count(),
            'contract_total': project.contracts.aggregate(
                total=Sum('contract_amount')
            )['total'] or 0,
        })
    
    # 最近采购项目
    recent_procurements = Procurement.objects.select_related('project').all()[:10]
    
    context = {
        'stats': stats,
        'projects': project_list,
        'recent_procurements': recent_procurements,
    }
    return render(request, 'dashboard.html', context)


def project_list(request):
    """项目列表页面"""
    # 获取搜索参数
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    # 基础查询
    projects = Project.objects.all()
    
    # 应用搜索过滤
    if search_query:
        projects = projects.filter(
            Q(project_code__icontains=search_query) |
            Q(project_name__icontains=search_query) |
            Q(project_manager__icontains=search_query)
        )
    
    # 应用状态过滤
    if status_filter:
        projects = projects.filter(status=status_filter)
    
    # 排序
    projects = projects.order_by('-created_at')
    
    # 分页
    paginator = Paginator(projects, 20)  # 每页显示20条
    page = request.GET.get('page', 1)
    
    try:
        projects_page = paginator.page(page)
    except PageNotAnInteger:
        projects_page = paginator.page(1)
    except EmptyPage:
        projects_page = paginator.page(paginator.num_pages)
    
    # 构建项目列表数据
    project_list = []
    for project in projects_page:
        project_list.append({
            'project_code': project.project_code,
            'project_name': project.project_name,
            'project_manager': project.project_manager,
            'status': project.status,
            'created_at': project.created_at,
            'procurement_count': project.procurements.count(),
            'contract_count': project.contracts.count(),
            'contract_total': project.contracts.aggregate(
                total=Sum('contract_amount')
            )['total'] or 0,
        })
    
    context = {
        'projects': project_list,
        'page_obj': projects_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Project.STATUS_CHOICES,
    }
    return render(request, 'project_list.html', context)


def project_detail(request, project_code):
    """项目详情页面"""
    from settlement.models import Settlement
    
    project = get_object_or_404(Project, project_code=project_code)
    
    # 获取关联的采购和合同
    procurements = project.procurements.all()
    contracts = project.contracts.all()
    
    # 计算合同总额
    total_contract_amount = contracts.aggregate(
        total=Sum('contract_amount')
    )['total'] or 0
    
    # 获取所有关联合同的付款记录
    all_payments = Payment.objects.filter(contract__project=project).order_by('-payment_date')
    total_paid = all_payments.aggregate(total=Sum('payment_amount'))['total'] or 0
    payment_count = all_payments.count()
    
    # 统计结算信息
    settlement_count = Settlement.objects.filter(main_contract__project=project).count()
    
    # 计算付款进度
    payment_progress = 0
    if total_contract_amount and total_contract_amount > 0:
        payment_progress = (total_paid / total_contract_amount) * 100
    
    context = {
        'project': project,
        'procurements': procurements,
        'contracts': contracts,
        'total_contract_amount': total_contract_amount,
        'payment_count': payment_count,
        'total_paid': total_paid,
        'payment_progress': payment_progress,
        'settlement_count': settlement_count,
        'recent_payments': all_payments[:5],  # 最近5条付款记录
    }
    return render(request, 'project_detail.html', context)


def procurement_list(request):
    """采购列表页面"""
    # 获取搜索参数
    search_query = request.GET.get('q', '')
    project_filter = request.GET.get('project', '')
    
    # 基础查询
    procurements = Procurement.objects.select_related('project').all()
    
    # 应用搜索过滤
    if search_query:
        procurements = procurements.filter(
            Q(procurement_code__icontains=search_query) |
            Q(project_name__icontains=search_query) |
            Q(winning_bidder__icontains=search_query) |
            Q(procurement_unit__icontains=search_query)
        )
    
    # 应用项目过滤
    if project_filter:
        procurements = procurements.filter(project__project_code=project_filter)
    
    # 排序
    procurements = procurements.order_by('-created_at')
    
    # 分页
    paginator = Paginator(procurements, 20)
    page = request.GET.get('page', 1)
    
    try:
        procurements_page = paginator.page(page)
    except PageNotAnInteger:
        procurements_page = paginator.page(1)
    except EmptyPage:
        procurements_page = paginator.page(paginator.num_pages)
    
    # 获取所有项目用于过滤
    projects = Project.objects.all()
    
    context = {
        'procurements': procurements_page,
        'page_obj': procurements_page,
        'search_query': search_query,
        'project_filter': project_filter,
        'projects': projects,
    }
    return render(request, 'procurement_list.html', context)


def contract_list(request):
    """合同列表页面"""
    # 获取搜索参数
    search_query = request.GET.get('q', '')
    project_filter = request.GET.get('project', '')
    contract_type_filter = request.GET.get('contract_type', '')
    
    # 基础查询
    contracts = Contract.objects.select_related('project', 'procurement').all()
    
    # 应用搜索过滤
    if search_query:
        contracts = contracts.filter(
            Q(contract_code__icontains=search_query) |
            Q(contract_name__icontains=search_query) |
            Q(party_b__icontains=search_query)
        )
    
    # 应用项目过滤
    if project_filter:
        contracts = contracts.filter(project__project_code=project_filter)
    
    # 应用合同类型过滤
    if contract_type_filter:
        contracts = contracts.filter(contract_type=contract_type_filter)
    
    # 排序
    contracts = contracts.order_by('-created_at')
    
    # 分页
    paginator = Paginator(contracts, 20)
    page = request.GET.get('page', 1)
    
    try:
        contracts_page = paginator.page(page)
    except PageNotAnInteger:
        contracts_page = paginator.page(1)
    except EmptyPage:
        contracts_page = paginator.page(paginator.num_pages)
    
    # 获取所有项目用于过滤
    projects = Project.objects.all()
    
    context = {
        'contracts': contracts_page,
        'page_obj': contracts_page,
        'search_query': search_query,
        'project_filter': project_filter,
        'contract_type_filter': contract_type_filter,
        'projects': projects,
        'contract_types': Contract.CONTRACT_TYPE_CHOICES,
    }
    return render(request, 'contract_list.html', context)


def contract_detail(request, contract_code):
    """合同详情页面"""
    from settlement.models import Settlement
    from supplier_eval.models import SupplierEvaluation
    from django.db.models import Sum
    
    contract = get_object_or_404(Contract, contract_code=contract_code)
    
    # 获取关联的采购信息
    procurement = contract.procurement
    
    # 获取关联的付款记录
    payments = contract.payments.all().order_by('-payment_date')
    total_paid = payments.aggregate(total=Sum('payment_amount'))['total'] or 0
    
    # 获取结算信息（如果是主合同）
    settlement = None
    if contract.contract_type == '主合同':
        try:
            settlement = Settlement.objects.get(main_contract=contract)
        except Settlement.DoesNotExist:
            pass
    # 如果是补充协议，获取主合同的结算信息
    elif contract.parent_contract:
        try:
            settlement = Settlement.objects.get(main_contract=contract.parent_contract)
        except Settlement.DoesNotExist:
            pass
    
    # 获取履约评价记录
    evaluations = contract.evaluations.all().order_by('-created_at')
    
    # 获取补充协议（如果是主合同）
    supplements = []
    if contract.contract_type == '主合同':
        supplements = contract.supplements.all().order_by('created_at')
    
    # 计算付款进度
    payment_progress = 0
    if contract.contract_amount and contract.contract_amount > 0:
        payment_progress = (total_paid / contract.contract_amount) * 100
    
    context = {
        'contract': contract,
        'procurement': procurement,
        'payments': payments,
        'total_paid': total_paid,
        'payment_progress': payment_progress,
        'settlement': settlement,
        'evaluations': evaluations,
        'supplements': supplements,
    }
    return render(request, 'contract_detail.html', context)


def payment_list(request):
    """付款列表页面"""
    # 获取搜索参数
    search_query = request.GET.get('q', '')
    project_filter = request.GET.get('project', '')
    
    # 基础查询
    payments = Payment.objects.select_related('contract__project').all()
    
    # 应用搜索过滤
    if search_query:
        payments = payments.filter(
            Q(payment_code__icontains=search_query) |
            Q(contract__contract_name__icontains=search_query)
        )
    
    # 应用项目过滤
    if project_filter:
        payments = payments.filter(contract__project__project_code=project_filter)
    
    # 排序
    payments = payments.order_by('-created_at')
    
    # 分页
    paginator = Paginator(payments, 20)
    page = request.GET.get('page', 1)
    
    try:
        payments_page = paginator.page(page)
    except PageNotAnInteger:
        payments_page = paginator.page(1)
    except EmptyPage:
        payments_page = paginator.page(paginator.num_pages)
    
    # 获取所有项目用于过滤
    projects = Project.objects.all()
    
    context = {
        'payments': payments_page,
        'page_obj': payments_page,
        'search_query': search_query,
        'project_filter': project_filter,
        'projects': projects,
    }
    return render(request, 'payment_list.html', context)


def procurement_detail(request, procurement_code):
    """采购详情页面"""
    from settlement.models import Settlement
    from django.db.models import Sum
    
    procurement = get_object_or_404(Procurement, procurement_code=procurement_code)
    
    # 获取关联的合同
    contracts = procurement.contracts.all().order_by('-created_at')
    
    # 计算合同总额
    total_contract_amount = contracts.aggregate(total=Sum('contract_amount'))['total'] or 0
    
    # 获取所有关联合同的付款记录
    all_payments = Payment.objects.filter(contract__procurement=procurement).order_by('-payment_date')
    total_paid = all_payments.aggregate(total=Sum('payment_amount'))['total'] or 0
    
    # 统计结算信息
    settlement_count = Settlement.objects.filter(main_contract__procurement=procurement).count()
    
    context = {
        'procurement': procurement,
        'contracts': contracts,
        'total_contract_amount': total_contract_amount,
        'all_payments': all_payments[:10],  # 只显示最近10条
        'total_paid': total_paid,
        'payment_count': all_payments.count(),
        'settlement_count': settlement_count,
    }
    return render(request, 'procurement_detail.html', context)


def payment_detail(request, payment_code):
    """付款详情页面"""
    payment = get_object_or_404(Payment, payment_code=payment_code)
    
    # 获取关联的合同
    contract = payment.contract
    
    # 获取该合同的所有付款记录
    all_payments = contract.payments.all().order_by('-payment_date')
    total_paid = all_payments.aggregate(total=Sum('payment_amount'))['total'] or 0
    
    # 计算付款进度
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
