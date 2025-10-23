"""
业务数据统计服务

提供采购、合同、付款、结算的统计分析功能
"""
from django.db.models import Sum, Count, Q, Avg, Max, Min
from django.db.models.functions import TruncMonth, TruncYear
from datetime import datetime, timedelta
from decimal import Decimal


def get_procurement_statistics(year=None):
    """
    采购统计
    
    Args:
        year: 统计年份，默认为当前年份
        
    Returns:
        dict: 包含采购统计数据
    """
    from procurement.models import Procurement
    
    if year is None:
        year = datetime.now().year
    
    # 基础查询集 - 按开标日期筛选年份
    queryset = Procurement.objects.filter(
        bid_opening_date__year=year
    )
    
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
                'amount': float(method['amount'] or 0),
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
        month=TruncMonth('bid_opening_date')
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
                'amount': float(item['amount'] or 0)
            })
    
    return {
        'year': year,
        'total_count': total_count,
        'total_budget': float(total_budget),
        'total_winning': float(total_winning),
        'savings_amount': float(total_budget - total_winning),
        'savings_rate': round(savings_rate, 2),
        'method_distribution': method_distribution,
        'avg_cycle_days': round(avg_cycle_days, 1),
        'archived_count': archived_count,
        'archive_rate': archive_rate,
        'monthly_trend': monthly_data
    }


def get_contract_statistics(year=None):
    """
    合同统计
    
    Args:
        year: 统计年份，默认为当前年份
        
    Returns:
        dict: 包含合同统计数据
    """
    from contract.models import Contract
    
    if year is None:
        year = datetime.now().year
    
    # 基础查询集 - 按签订日期筛选年份
    queryset = Contract.objects.filter(
        signing_date__year=year
    )
    
    # 基本统计
    total_count = queryset.count()
    total_amount = queryset.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
    
    # 按合同类型统计
    type_stats = queryset.values('contract_type').annotate(
        count=Count('contract_code'),
        amount=Sum('contract_amount')
    ).order_by('-count')
    
    type_distribution = []
    for item in type_stats:
        if item['contract_type']:
            type_distribution.append({
                'type': item['contract_type'],
                'count': item['count'],
                'amount': float(item['amount'] or 0),
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
                'amount': float(item['amount'] or 0),
                'percentage': round(item['count'] / total_count * 100, 2) if total_count > 0 else 0
            })
    
    # 主合同统计
    main_contracts = queryset.filter(contract_type='主合同')
    main_count = main_contracts.count()
    main_amount = main_contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
    
    # 补充协议统计
    supplements = queryset.filter(contract_type='补充协议')
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
                'amount': float(item['amount'] or 0)
            })
    
    return {
        'year': year,
        'total_count': total_count,
        'total_amount': float(total_amount),
        'main_count': main_count,
        'main_amount': float(main_amount),
        'supplement_count': supplement_count,
        'supplement_amount': float(supplement_amount),
        'type_distribution': type_distribution,
        'source_distribution': source_distribution,
        'archived_count': archived_count,
        'archive_rate': archive_rate,
        'monthly_trend': monthly_data
    }


def get_payment_statistics(year=None):
    """
    付款统计
    
    Args:
        year: 统计年份，默认为当前年份
        
    Returns:
        dict: 包含付款统计数据
    """
    from payment.models import Payment
    from contract.models import Contract
    from settlement.models import Settlement
    
    if year is None:
        year = datetime.now().year
    
    # 基础查询集 - 按付款日期筛选年份
    queryset = Payment.objects.filter(
        payment_date__year=year
    )
    
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
                'amount': float(item['amount'] or 0)
            })
    
    # 计算预计剩余支付金额
    # 获取所有主合同
    main_contracts = Contract.objects.filter(contract_type='主合同')
    total_remaining = Decimal('0')
    
    for contract in main_contracts:
        # 获取合同+补充协议总额
        contract_total = contract.get_contract_with_supplements_amount()
        
        # 检查是否有结算
        try:
            from settlement.models import Settlement
            settlement = Settlement.objects.filter(main_contract=contract).first()
            if settlement:
                # 有结算，使用结算价
                base_amount = settlement.final_amount
            else:
                # 无结算，使用合同价+补充协议
                base_amount = contract_total
        except:
            base_amount = contract_total
        
        # 获取已付金额
        paid_amount = contract.get_total_paid_amount()
        
        # 计算剩余
        remaining = base_amount - paid_amount
        if remaining > 0:
            total_remaining += remaining
    
    return {
        'year': year,
        'total_count': total_count,
        'total_amount': float(total_amount),
        'avg_amount': float(avg_amount),
        'max_amount': float(max_amount),
        'min_amount': float(min_amount),
        'settled_count': settled_count,
        'settled_amount': float(settled_amount),
        'unsettled_count': unsettled_count,
        'unsettled_amount': float(unsettled_amount),
        'estimated_remaining': float(total_remaining),
        'monthly_trend': monthly_data
    }


def get_settlement_statistics():
    """
    结算统计
    
    Returns:
        dict: 包含结算统计数据
    """
    from settlement.models import Settlement
    from contract.models import Contract
    
    # 所有结算记录
    queryset = Settlement.objects.all()
    
    # 基本统计
    total_count = queryset.count()
    total_amount = queryset.aggregate(total=Sum('final_amount'))['total'] or Decimal('0')
    
    # 平均结算金额
    avg_amount = queryset.aggregate(avg=Avg('final_amount'))['avg'] or Decimal('0')
    
    # 按年份统计
    yearly_stats = queryset.annotate(
        year=TruncYear('completion_date')
    ).values('year').annotate(
        count=Count('settlement_code'),
        amount=Sum('final_amount')
    ).order_by('year')
    
    yearly_data = []
    for item in yearly_stats:
        if item['year']:
            yearly_data.append({
                'year': item['year'].year,
                'count': item['count'],
                'amount': float(item['amount'] or 0)
            })
    
    # 计算结算率（已结算的主合同数 / 总主合同数）
    total_main_contracts = Contract.objects.filter(contract_type='主合同').count()
    settlement_rate = round(total_count / total_main_contracts * 100, 2) if total_main_contracts > 0 else 0
    
    # 待结算合同统计
    pending_settlements = Contract.objects.filter(
        contract_type='主合同'
    ).exclude(
        settlement__isnull=False
    )
    
    pending_count = pending_settlements.count()
    pending_amount = Decimal('0')
    for contract in pending_settlements:
        pending_amount += contract.get_contract_with_supplements_amount()
    
    # 结算与合同差异分析
    variance_analysis = []
    for settlement in queryset:
        contract_amount = settlement.get_total_contract_amount()
        variance = settlement.final_amount - contract_amount
        variance_rate = float(variance / contract_amount * 100) if contract_amount > 0 else 0
        
        variance_analysis.append({
            'settlement_code': settlement.settlement_code,
            'contract_amount': float(contract_amount),
            'settlement_amount': float(settlement.final_amount),
            'variance': float(variance),
            'variance_rate': round(variance_rate, 2)
        })
    
    return {
        'total_count': total_count,
        'total_amount': float(total_amount),
        'avg_amount': float(avg_amount),
        'settlement_rate': settlement_rate,
        'pending_count': pending_count,
        'pending_amount': float(pending_amount),
        'yearly_data': yearly_data,
        'variance_analysis': variance_analysis[:10]  # 只返回前10条
    }


def get_overview_statistics(year=None):
    """
    获取综合统计概览
    
    Args:
        year: 统计年份，默认为当前年份
        
    Returns:
        dict: 综合统计数据
    """
    if year is None:
        year = datetime.now().year
    
    procurement_stats = get_procurement_statistics(year)
    contract_stats = get_contract_statistics(year)
    payment_stats = get_payment_statistics(year)
    settlement_stats = get_settlement_statistics()
    
    return {
        'year': year,
        'procurement': procurement_stats,
        'contract': contract_stats,
        'payment': payment_stats,
        'settlement': settlement_stats
    }


def get_year_comparison(years):
    """
    多年度数据对比
    
    Args:
        years: 年份列表，例如 [2023, 2024, 2025]
        
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
        proc_stats = get_procurement_statistics(year)
        comparison_data['procurement'].append({
            'year': year,
            'count': proc_stats['total_count'],
            'amount': proc_stats['total_winning']
        })
        
        contract_stats = get_contract_statistics(year)
        comparison_data['contract'].append({
            'year': year,
            'count': contract_stats['total_count'],
            'amount': contract_stats['total_amount']
        })
        
        payment_stats = get_payment_statistics(year)
        comparison_data['payment'].append({
            'year': year,
            'count': payment_stats['total_count'],
            'amount': payment_stats['total_amount']
        })
        
        # 添加行数据，便于模板直接迭代
        comparison_data['rows'].append({
            'year': year,
            'procurement_count': proc_stats['total_count'],
            'procurement_amount': proc_stats['total_winning'],
            'contract_count': contract_stats['total_count'],
            'contract_amount': contract_stats['total_amount'],
            'payment_count': payment_stats['total_count'],
            'payment_amount': payment_stats['total_amount'],
        })
    
    return comparison_data