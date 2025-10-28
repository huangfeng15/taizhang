"""
业务数据统计服务

提供采购、合同、付款、结算的统计分析功能
"""
from django.db.models import Sum, Count, Q, Avg, Max, Min
from django.db.models.functions import TruncMonth, TruncYear
from datetime import datetime, timedelta
from decimal import Decimal


def get_procurement_statistics(year=None, project_codes=None):
    """
    采购统计
    
    Args:
        year: 统计年份，None表示全部年份，整数表示具体年份
        project_codes: 项目编码列表，None表示全部项目
        
    Returns:
        dict: 包含采购统计数据
    """
    from procurement.models import Procurement
    
    # 基础查询集 - 使用select_related和only优化查询
    queryset = Procurement.objects.select_related('project').only(
        'procurement_code', 'project_name', 'procurement_method',
        'budget_amount', 'winning_amount', 'archive_date',
        'result_publicity_release_date', 'requirement_approval_date',
        'notice_issue_date', 'planned_completion_date',
        'project__project_code', 'project__project_name'
    )
    
    # 年份筛选 - 按结果公示发布时间统计
    # year=None表示全部年份，不进行筛选
    if year is not None:
        queryset = queryset.filter(result_publicity_release_date__year=year)
    
    # 项目筛选
    if project_codes:
        queryset = queryset.filter(project__project_code__in=project_codes)
    
    # 基本统计
    total_count = queryset.count()
    total_budget = queryset.aggregate(total=Sum('budget_amount'))['total'] or Decimal('0')
    total_winning = queryset.aggregate(total=Sum('winning_amount'))['total'] or Decimal('0')
    
    # 节约率计算
    savings_rate = 0
    if total_budget > 0:
        savings_rate = float((total_budget - total_winning) / total_budget * 100)
    
    # 采购方式分布
    procurement_methods = queryset.values('procurement_method').annotate(
        count=Count('procurement_code'),
        amount=Sum('winning_amount')
    ).order_by('-count')
    
    # 处理采购方式数据
    method_distribution = []
    for method in procurement_methods:
        if method['procurement_method']:
            method_distribution.append({
                'method': method['procurement_method'],
                'count': method['count'],
                'amount': float(method['amount'] or 0) / 10000,  # 转换为万元
                'percentage': round(method['count'] / total_count * 100, 2) if total_count > 0 else 0
            })
    
    # 采购周期分析（从需求审批到中标通知）
    cycle_data = queryset.filter(
        requirement_approval_date__isnull=False,
        notice_issue_date__isnull=False
    )
    
    avg_cycle_days = 0
    if cycle_data.exists():
        total_days = 0
        count = 0
        for proc in cycle_data:
            if proc.notice_issue_date and proc.requirement_approval_date:
                days = (proc.notice_issue_date - proc.requirement_approval_date).days
                if days > 0:
                    total_days += days
                    count += 1
        if count > 0:
            avg_cycle_days = total_days / count
    
    # 归档情况统计
    archived_count = queryset.filter(archive_date__isnull=False).count()
    archive_rate = round(archived_count / total_count * 100, 2) if total_count > 0 else 0
    
    # 月度趋势
    monthly_trend = queryset.annotate(
        month=TruncMonth('result_publicity_release_date')
    ).values('month').annotate(
        count=Count('procurement_code'),
        amount=Sum('winning_amount')
    ).order_by('month')
    
    monthly_data = []
    for item in monthly_trend:
        if item['month']:
            monthly_data.append({
                'month': item['month'].strftime('%Y-%m'),
                'count': item['count'],
                'amount': float(item['amount'] or 0) / 10000  # 转换为万元
            })
    
    # 采购周期分析 - 按采购方式分组
    cycle_by_method = {}
    # 默认常用方式（6种）
    common_methods = ['公开招标', '单一来源', '询价采购', '直接采购', '竞价采购', '战采应用']
    # 全部方式（10种）- 与原型图保持一致
    all_methods_list = ['公开招标', '邀请招标', '竞争性谈判', '竞争性磋商', '询价采购', '单一来源', '直接采购', '竞价采购', '比选', '战采应用']
    
    for proc in cycle_data:
        method = proc.procurement_method
        if not method:
            continue
        if method not in cycle_by_method:
            cycle_by_method[method] = {'under_30': 0, '30_to_60': 0, '60_to_90': 0, 'over_90': 0}
        
        if proc.notice_issue_date and proc.requirement_approval_date:
            days = (proc.notice_issue_date - proc.requirement_approval_date).days
            if days > 0:
                if days < 30:
                    cycle_by_method[method]['under_30'] += 1
                elif days < 60:
                    cycle_by_method[method]['30_to_60'] += 1
                elif days < 90:
                    cycle_by_method[method]['60_to_90'] += 1
                else:
                    cycle_by_method[method]['over_90'] += 1
    
    # 采购偏差分析 - Top 5
    top_deviations = []
    for proc in queryset.filter(
        planned_completion_date__isnull=False,
        result_publicity_release_date__isnull=False
    ):
        # 确保两个日期都不为None后再进行计算
        if proc.result_publicity_release_date is not None and proc.planned_completion_date is not None:
            deviation_days = (proc.result_publicity_release_date - proc.planned_completion_date).days
            if deviation_days != 0:  # 只统计有偏差的
                top_deviations.append({
                    'project_name': proc.project_name,
                    'planned_date': proc.planned_completion_date,
                    'actual_date': proc.result_publicity_release_date,
                    'deviation_days': deviation_days
                })
    
    # 按偏差绝对值排序,取前5
    top_deviations.sort(key=lambda x: abs(x['deviation_days']), reverse=True)
    top_deviations = top_deviations[:5]
    
    return {
        'year': year if year is not None else '全部',
        'total_count': total_count,
        'total_budget': float(total_budget) / 10000,  # 转换为万元
        'total_winning': float(total_winning) / 10000,  # 转换为万元
        'savings_amount': float(total_budget - total_winning) / 10000,  # 转换为万元
        'savings_rate': round(savings_rate, 2),
        'method_distribution': method_distribution,
        'avg_cycle_days': round(avg_cycle_days, 1),
        'archived_count': archived_count,
        'archive_rate': archive_rate,
        'monthly_trend': monthly_data,
        'cycle_by_method': cycle_by_method,
        'common_methods': common_methods,
        'top_deviations': top_deviations,
    }


def get_contract_statistics(year=None, project_codes=None):
    """
    合同统计
    
    Args:
        year: 统计年份，None表示全部年份，整数表示具体年份
        project_codes: 项目编码列表，None表示全部项目
        
    Returns:
        dict: 包含合同统计数据
    """
    from contract.models import Contract
    
    # 基础查询集 - 使用select_related和only优化查询
    queryset = Contract.objects.select_related('project').only(
        'contract_code', 'contract_name', 'file_positioning',
        'contract_source', 'contract_amount', 'signing_date',
        'archive_date', 'project__project_code', 'project__project_name'
    )
    
    # 年份筛选 - 按合同签订时间统计
    # year=None表示全部年份，不进行筛选
    if year is not None:
        queryset = queryset.filter(signing_date__year=year)
    
    # 项目筛选
    if project_codes:
        queryset = queryset.filter(project__project_code__in=project_codes)
    
    # 基本统计
    total_count = queryset.count()
    total_amount = queryset.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
    
    # 按合同类型统计
    type_stats = queryset.values('file_positioning').annotate(
        count=Count('contract_code'),
        amount=Sum('contract_amount')
    ).order_by('-count')
    
    type_distribution = []
    for item in type_stats:
        if item['file_positioning']:
            type_distribution.append({
                'type': item['file_positioning'],
                'count': item['count'],
                'amount': float(item['amount'] or 0) / 10000,  # 转换为万元
                'percentage': round(item['count'] / total_count * 100, 2) if total_count > 0 else 0
            })
    
    # 按合同来源统计
    source_stats = queryset.values('contract_source').annotate(
        count=Count('contract_code'),
        amount=Sum('contract_amount')
    ).order_by('-count')
    
    source_distribution = []
    for item in source_stats:
        if item['contract_source']:
            source_distribution.append({
                'source': item['contract_source'],
                'count': item['count'],
                'amount': float(item['amount'] or 0) / 10000,  # 转换为万元
                'percentage': round(item['count'] / total_count * 100, 2) if total_count > 0 else 0
            })
    
    # 主合同统计
    main_contracts = queryset.filter(file_positioning='主合同')
    main_count = main_contracts.count()
    main_amount = main_contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
    
    # 补充协议统计
    supplements = queryset.filter(file_positioning='补充协议')
    supplement_count = supplements.count()
    supplement_amount = supplements.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
    
    # 归档情况
    archived_count = queryset.filter(archive_date__isnull=False).count()
    archive_rate = round(archived_count / total_count * 100, 2) if total_count > 0 else 0
    
    # 月度趋势
    monthly_trend = queryset.annotate(
        month=TruncMonth('signing_date')
    ).values('month').annotate(
        count=Count('contract_code'),
        amount=Sum('contract_amount')
    ).order_by('month')
    
    monthly_data = []
    for item in monthly_trend:
        if item['month']:
            monthly_data.append({
                'month': item['month'].strftime('%Y-%m'),
                'count': item['count'],
                'amount': float(item['amount'] or 0) / 10000  # 转换为万元
            })
    
    return {
        'year': year if year is not None else '全部',
        'total_count': total_count,
        'total_amount': float(total_amount) / 10000,  # 转换为万元
        'main_count': main_count,
        'main_amount': float(main_amount) / 10000,  # 转换为万元
        'supplement_count': supplement_count,
        'supplement_amount': float(supplement_amount) / 10000,  # 转换为万元
        'type_distribution': type_distribution,
        'source_distribution': source_distribution,
        'archived_count': archived_count,
        'archive_rate': archive_rate,
        'monthly_trend': monthly_data
    }


def get_payment_statistics(year=None, project_codes=None):
    """
    付款统计
    
    Args:
        year: 统计年份，None表示全部年份，整数表示具体年份
        project_codes: 项目编码列表，None表示全部项目
        
    Returns:
        dict: 包含付款统计数据
    """
    from payment.models import Payment
    from contract.models import Contract
    from settlement.models import Settlement
    
    # 基础查询集 - 使用select_related优化查询
    queryset = Payment.objects.select_related('contract', 'contract__project').only(
        'payment_code', 'payment_amount', 'payment_date', 'is_settled',
        'contract__contract_code', 'contract__project__project_code'
    )
    
    # 年份筛选 - 按付款时间统计
    # year=None表示全部年份，不进行筛选
    if year is not None:
        queryset = queryset.filter(payment_date__year=year)
    
    # 项目筛选
    if project_codes:
        queryset = queryset.filter(contract__project__project_code__in=project_codes)
    
    # 基本统计
    total_count = queryset.count()
    total_amount = queryset.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
    
    # 平均付款金额
    avg_amount = queryset.aggregate(avg=Avg('payment_amount'))['avg'] or Decimal('0')
    
    # 最大和最小付款
    max_amount = queryset.aggregate(max=Max('payment_amount'))['max'] or Decimal('0')
    min_amount = queryset.aggregate(min=Min('payment_amount'))['min'] or Decimal('0')
    
    # 已结算付款统计
    settled_count = queryset.filter(is_settled=True).count()
    settled_amount = queryset.filter(is_settled=True).aggregate(
        total=Sum('payment_amount')
    )['total'] or Decimal('0')
    
    # 未结算付款统计
    unsettled_count = queryset.filter(is_settled=False).count()
    unsettled_amount = queryset.filter(is_settled=False).aggregate(
        total=Sum('payment_amount')
    )['total'] or Decimal('0')
    
    # 月度付款趋势
    monthly_trend = queryset.annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(
        count=Count('payment_code'),
        amount=Sum('payment_amount')
    ).order_by('month')
    
    monthly_data = []
    for item in monthly_trend:
        if item['month']:
            monthly_data.append({
                'month': item['month'].strftime('%Y-%m'),
                'count': item['count'],
                'amount': float(item['amount'] or 0) / 10000  # 转换为万元
            })
    
    # 计算预计剩余支付金额
    # 获取所有主合同（应用年份和项目筛选）
    main_contracts_query = Contract.objects.filter(file_positioning='主合同')
    
    # 应用项目筛选
    if project_codes:
        main_contracts_query = main_contracts_query.filter(project__project_code__in=project_codes)
    
    # 应用年份筛选（按签订日期）
    if year is not None:
        main_contracts_query = main_contracts_query.filter(signing_date__year=year)
    
    total_remaining = Decimal('0')
    
    for contract in main_contracts_query:
        # 获取合同+补充协议总额
        contract_total = contract.get_contract_with_supplements_amount()
        
        # 检查是否有结算
        try:
            settlement = Settlement.objects.filter(main_contract=contract).first()
            if settlement:
                # 有结算，使用结算价
                base_amount = settlement.final_amount
            else:
                # 无结算，使用合同价+补充协议
                base_amount = contract_total
        except:
            base_amount = contract_total
        
        # 获取已付金额（需要应用相同的筛选条件）
        paid_query = Payment.objects.filter(contract=contract)
        if year is not None:
            paid_query = paid_query.filter(payment_date__year=year)
        paid_amount = paid_query.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
        
        # 计算剩余（包括负值，即超付情况）
        remaining = base_amount - paid_amount
        total_remaining += remaining
    
    return {
        'year': year if year is not None else '全部',
        'total_count': total_count,
        'total_amount': float(total_amount) / 10000,  # 转换为万元
        'avg_amount': float(avg_amount) / 10000,  # 转换为万元
        'max_amount': float(max_amount) / 10000,  # 转换为万元
        'min_amount': float(min_amount) / 10000,  # 转换为万元
        'settled_count': settled_count,
        'settled_amount': float(settled_amount) / 10000,  # 转换为万元
        'unsettled_count': unsettled_count,
        'unsettled_amount': float(unsettled_amount) / 10000,  # 转换为万元
        'estimated_remaining': float(total_remaining) / 10000,  # 转换为万元
        'monthly_trend': monthly_data,
        'payment_rate': round(float(total_amount) / float(total_remaining + total_amount) * 100, 2) if (total_remaining + total_amount) > 0 else 0  # 计算支付率
    }


def get_settlement_statistics(year=None, project_codes=None):
    """
    结算统计 - 从Payment表中统计已结算付款的结算金额
    
    注意：settlement_amount是合同的结算总价，需要按合同去重避免重复计算
    
    Args:
        year: 统计年份，None表示全部年份，整数表示具体年份
        project_codes: 项目编码列表，None表示全部项目
        
    Returns:
        dict: 包含结算统计数据
    """
    from settlement.models import Settlement
    from contract.models import Contract
    from payment.models import Payment
    
    # 从Payment表中查询已结算的记录（有结算金额的付款）
    queryset = Payment.objects.filter(
        is_settled=True,
        settlement_amount__isnull=False
    ).select_related('contract', 'contract__project', 'contract__parent_contract').only(
        'payment_code', 'settlement_amount', 'payment_date',
        'contract__contract_code', 'contract__file_positioning',
        'contract__project__project_code',
        'contract__parent_contract__contract_code'
    )
    
    # 年份筛选 - 按付款日期统计
    if year is not None:
        queryset = queryset.filter(payment_date__year=year)
    
    # 项目筛选
    if project_codes:
        queryset = queryset.filter(contract__project__project_code__in=project_codes)
    
    # 按主合同分组统计，避免重复计算
    # settlement_amount 是合同的结算总价，同一合同的多笔付款会重复这个值
    settlement_by_contract = {}
    
    for payment in queryset:
        if not payment.contract:
            continue
        
        # 确定主合同编号
        if payment.contract.file_positioning == '主合同':
            main_contract_code = payment.contract.contract_code
        elif payment.contract.parent_contract:
            main_contract_code = payment.contract.parent_contract.contract_code
        else:
            # 补充协议但没有父合同，跳过
            continue
        
        # 每个主合同只记录一次结算金额（取第一次遇到的值）
        if main_contract_code not in settlement_by_contract:
            settlement_by_contract[main_contract_code] = payment.settlement_amount or Decimal('0')
    
    # 统计已结算的合同数量
    total_count = len(settlement_by_contract)
    
    # 统计结算总金额 - 按合同去重后求和
    total_amount = sum(settlement_by_contract.values())
    
    # 平均结算金额（按合同平均）
    avg_amount = total_amount / total_count if total_count > 0 else Decimal('0')
    
    # 按年份统计
    yearly_stats = queryset.annotate(
        year=TruncYear('payment_date')
    ).values('year').annotate(
        count=Count('payment_code'),
        amount=Sum('settlement_amount')
    ).order_by('year')
    
    yearly_data = []
    for item in yearly_stats:
        if item['year']:
            yearly_data.append({
                'year': item['year'].year,
                'count': item['count'],
                'amount': float(item['amount'] or 0) / 10000  # 转换为万元
            })
    
    # 计算结算率（已结算的主合同数 / 总主合同数）
    # 应用年份和项目筛选
    main_contracts_query = Contract.objects.filter(file_positioning='主合同')
    if year is not None:
        main_contracts_query = main_contracts_query.filter(signing_date__year=year)
    if project_codes:
        main_contracts_query = main_contracts_query.filter(project__project_code__in=project_codes)
    
    total_main_contracts = main_contracts_query.count()
    settlement_rate = round(total_count / total_main_contracts * 100, 2) if total_main_contracts > 0 else 0
    
    # 待结算合同统计 - 排除已有结算付款的主合同
    pending_settlements = main_contracts_query.exclude(
        contract_code__in=settlement_by_contract.keys()
    )
    
    pending_count = pending_settlements.count()
    pending_amount = Decimal('0')
    for contract in pending_settlements:
        pending_amount += contract.get_contract_with_supplements_amount()
    
    # 结算与合同差异分析 - 使用去重后的结算数据
    variance_analysis = []
    
    for contract_code, settlement_amount in settlement_by_contract.items():
        try:
            contract = Contract.objects.get(contract_code=contract_code)
        except Contract.DoesNotExist:
            continue
        
        # 获取合同总额（主合同+补充协议）
        contract_amount = contract.get_contract_with_supplements_amount()
        
        variance = settlement_amount - contract_amount
        variance_rate = float(variance / contract_amount * 100) if contract_amount > 0 else 0
        
        variance_analysis.append({
            'settlement_code': contract_code,
            'contract_amount': float(contract_amount) / 10000,  # 转换为万元
            'settlement_amount': float(settlement_amount) / 10000,  # 转换为万元
            'variance': float(variance) / 10000,  # 转换为万元
            'variance_rate': round(variance_rate, 2)
        })
    
    # 按差异金额绝对值排序
    variance_analysis.sort(key=lambda x: abs(x['variance']), reverse=True)
    
    return {
        'total_count': total_count,
        'total_amount': float(total_amount) / 10000,  # 转换为万元
        'avg_amount': float(avg_amount) / 10000,  # 转换为万元
        'settlement_rate': settlement_rate,
        'pending_count': pending_count,
        'pending_amount': float(pending_amount) / 10000,  # 转换为万元
        'yearly_data': yearly_data,
        'variance_analysis': variance_analysis[:10]  # 只返回前10条
    }


def get_overview_statistics(year=None, project_codes=None):
    """
    获取综合统计概览
    
    Args:
        year: 统计年份，默认为当前年份
        project_codes: 项目编码列表，None表示全部项目
        
    Returns:
        dict: 综合统计数据
    """
    if year is None:
        year = datetime.now().year
    
    procurement_stats = get_procurement_statistics(year, project_codes)
    contract_stats = get_contract_statistics(year, project_codes)
    payment_stats = get_payment_statistics(year, project_codes)
    settlement_stats = get_settlement_statistics()
    
    return {
        'year': year,
        'procurement': procurement_stats,
        'contract': contract_stats,
        'payment': payment_stats,
        'settlement': settlement_stats
    }


def get_year_comparison(years, project_codes=None):
    """
    多年度数据对比
    
    Args:
        years: 年份列表，例如 [2023, 2024, 2025]
        project_codes: 项目编码列表，None表示全部项目
        
    Returns:
        dict: 多年度对比数据
    """
    comparison_data = {
        'years': years,
        'procurement': [],
        'contract': [],
        'payment': [],
        'rows': []  # 新增：按行组织的数据，便于模板迭代
    }
    
    for year in years:
        proc_stats = get_procurement_statistics(year, project_codes)
        comparison_data['procurement'].append({
            'year': year,
            'count': proc_stats['total_count'],
            'amount': proc_stats['total_winning']  # 已在get_procurement_statistics中转换
        })
        
        contract_stats = get_contract_statistics(year, project_codes)
        comparison_data['contract'].append({
            'year': year,
            'count': contract_stats['total_count'],
            'amount': contract_stats['total_amount']  # 已在get_contract_statistics中转换
        })
        
        payment_stats = get_payment_statistics(year, project_codes)
        comparison_data['payment'].append({
            'year': year,
            'count': payment_stats['total_count'],
            'amount': payment_stats['total_amount']  # 已在get_payment_statistics中转换
        })
        
        # 添加行数据，便于模板直接迭代
        comparison_data['rows'].append({
            'year': year,
            'procurement_count': proc_stats['total_count'],
            'procurement_amount': proc_stats['total_winning'],  # 已转换
            'contract_count': contract_stats['total_count'],
            'contract_amount': contract_stats['total_amount'],  # 已转换
            'payment_count': payment_stats['total_count'],
            'payment_amount': payment_stats['total_amount'],  # 已转换
        })
    
    return comparison_data