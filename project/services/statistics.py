"""
业务数据统计服务

提供采购、合同、付款、结算的统计分析功能
"""
from django.db.models import Sum, Count, Q, Avg, Max, Min
from django.db.models.functions import TruncMonth, TruncYear
from datetime import datetime, timedelta
from decimal import Decimal
from project.enums import FilePositioning, PROCUREMENT_METHODS_COMMON, PROCUREMENT_METHODS_ALL
from project.constants import get_current_year


def get_procurement_statistics(year=None, project_codes=None):
    """采购统计
    按项目名称去重统计：相同项目名称只统计一次；
    预算金额/中标金额/控制价取该名称下的最大值；
    返回同时包含万元单位展示值和以元为单位的原始值（*_amount）。
    保持现有对外结构与键名不变。
    """
    from decimal import Decimal
    from django.db.models import Count, Sum
    from django.db.models.functions import TruncMonth
    from procurement.models import Procurement

    # 基础查询（最小必要字段）
    queryset = Procurement.objects.select_related('project').only(
        'project_name', 'procurement_method',
        'budget_amount', 'winning_amount', 'control_price',
        'archive_date', 'result_publicity_release_date',
        'project__project_code', 'project__project_name'
    )

    # 年份过滤（按结果公示发布时间）
    if year is not None:
        queryset = queryset.filter(result_publicity_release_date__year=year)

    # 项目过滤
    if project_codes:
        queryset = queryset.filter(project__project_code__in=project_codes)

    # 去重后的最大值聚合（按项目名称）
    project_name_max = {}
    for proc in queryset:
        name = proc.project_name
        if not name:
            continue
        if name not in project_name_max:
            project_name_max[name] = {
                'budget_amount': proc.budget_amount or Decimal('0'),
                'winning_amount': proc.winning_amount or Decimal('0'),
                'control_price': proc.control_price or Decimal('0'),
                'procurement_method': proc.procurement_method,
                'archive_date': proc.archive_date,
                'requirement_approval_date': proc.requirement_approval_date,
                'result_publicity_release_date': proc.result_publicity_release_date,
            }
        else:
            cur = project_name_max[name]
            # 取最大值
            cur['budget_amount'] = max(cur['budget_amount'], proc.budget_amount or Decimal('0'))
            cur['winning_amount'] = max(cur['winning_amount'], proc.winning_amount or Decimal('0'))
            cur['control_price'] = max(cur['control_price'], proc.control_price or Decimal('0'))
            # 归档日期取最新的非空值
            if proc.archive_date and (not cur['archive_date'] or proc.archive_date > cur['archive_date']):
                cur['archive_date'] = proc.archive_date
            # 日期字段也保留（用于周期计算）
            if proc.requirement_approval_date:
                cur['requirement_approval_date'] = proc.requirement_approval_date
            if proc.result_publicity_release_date:
                cur['result_publicity_release_date'] = proc.result_publicity_release_date

    # 基本汇总
    total_count = len(project_name_max)
    total_budget_amount = sum(v['budget_amount'] for v in project_name_max.values())
    total_winning_amount = sum(v['winning_amount'] for v in project_name_max.values())

    # 节约率（以元为单位计算百分比）
    savings_rate = 0.0
    if total_budget_amount > 0:
        savings_rate = float((total_budget_amount - total_winning_amount) / total_budget_amount * 100)

    # 采购方式分布（基于去重后数据）
    method_distribution = []
    method_stats = {}
    for v in project_name_max.values():
        method = v['procurement_method']
        if not method:
            continue
        if method not in method_stats:
            method_stats[method] = {'count': 0, 'amount': Decimal('0')}
        method_stats[method]['count'] += 1
        # 使用中标金额累计（若无中标金额则为0）
        method_stats[method]['amount'] += (v['winning_amount'] or Decimal('0'))
    for method, agg in method_stats.items():
        method_distribution.append({
            'method': method,
            'count': agg['count'],
            'amount': float(agg['amount']) / 10000.0,  # 万元
        })

    # 月度趋势（按结果公示发布时间聚合）
    monthly_trend_qs = queryset.annotate(
        month=TruncMonth('result_publicity_release_date')
    ).values('month').annotate(
        count=Count('procurement_code'),
        amount=Sum('winning_amount')
    ).order_by('month')

    monthly_trend = []
    for item in monthly_trend_qs:
        if item['month']:
            monthly_trend.append({
                'month': item['month'].strftime('%Y-%m'),
                'count': item['count'] or 0,
                'amount': float(item['amount'] or 0) / 10000.0,  # 万元
            })

    # 采购周期分析（按采购方式统计周期分布）
    # 使用去重后的数据，保持与采购方式分布统计口径一致
    cycle_by_method = {}
    all_methods_set = set()
    
    for name, data in project_name_max.items():
        method = data['procurement_method']
        if not method:
            continue
        all_methods_set.add(method)
        
        if method not in cycle_by_method:
            cycle_by_method[method] = {
                'within_15': 0, 'within_25': 0, 'within_40': 0,
                'within_60': 0, 'over_60': 0, 'no_data': 0
            }
        
        # 直接使用去重后数据中保存的日期信息
        requirement_date = data.get('requirement_approval_date')
        result_date = data.get('result_publicity_release_date')
        
        # 计算采购周期（从需求批复到结果公示发布）
        if requirement_date and result_date:
            cycle_days = (result_date - requirement_date).days
            
            if cycle_days <= 15:
                cycle_by_method[method]['within_15'] += 1
            elif cycle_days <= 25:
                cycle_by_method[method]['within_25'] += 1
            elif cycle_days <= 40:
                cycle_by_method[method]['within_40'] += 1
            elif cycle_days <= 60:
                cycle_by_method[method]['within_60'] += 1
            else:
                cycle_by_method[method]['over_60'] += 1
        else:
            # 没有日期数据的记录计入no_data
            cycle_by_method[method]['no_data'] += 1
    
    common_methods = list(PROCUREMENT_METHODS_COMMON)
    all_methods_list = sorted(list(all_methods_set))

    return {
        'year': year if year is not None else '全部',
        'total_count': total_count,
        # 展示用（万元）
        'total_budget': float(total_budget_amount) / 10000.0,
        'total_winning': float(total_winning_amount) / 10000.0,
        'savings_rate': round(savings_rate, 2),
        'method_distribution': method_distribution,
        'monthly_trend': monthly_trend,
        # 原始值（元）供财务分析使用
        'total_budget_amount': float(total_budget_amount),
        'total_winning_amount': float(total_winning_amount),
        # 采购周期分析
        'cycle_by_method': cycle_by_method,
        'common_methods': common_methods,
        'all_methods_list': all_methods_list,
    }


def get_contract_statistics(year=None, project_codes=None):
    """合同统计（保持既有结构与键名）"""
    from decimal import Decimal
    from django.db.models import Count, Sum
    from django.db.models.functions import TruncMonth
    from contract.models import Contract, FilePositioning

    # 基础查询
    queryset = Contract.objects.select_related('project').only(
        'contract_code', 'contract_name', 'file_positioning',
        'contract_source', 'contract_amount', 'signing_date',
        'archive_date', 'project__project_code', 'project__project_name'
    )

    # 年份过滤（按签订日期）
    if year is not None:
        queryset = queryset.filter(signing_date__year=year)

    # 项目过滤
    if project_codes:
        queryset = queryset.filter(project__project_code__in=project_codes)

    # 基本统计
    total_count = queryset.count()
    total_amount = queryset.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')

    # 合同类型分布
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
                'amount': float(item['amount'] or 0) / 10000.0,  # 万元
                'percentage': round(item['count'] / total_count * 100, 2) if total_count > 0 else 0
            })

    # 合同来源分布
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
                'amount': float(item['amount'] or 0) / 10000.0,  # 万元
                'percentage': round(item['count'] / total_count * 100, 2) if total_count > 0 else 0
            })

    # 主合同/补充协议/解除/框架 统计
    main_contracts = queryset.filter(file_positioning=FilePositioning.MAIN_CONTRACT.value)
    main_count = main_contracts.count()
    main_amount = main_contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')

    supplements = queryset.filter(file_positioning=FilePositioning.SUPPLEMENT.value)
    supplement_count = supplements.count()
    supplement_amount = supplements.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')

    terminations = queryset.filter(file_positioning=FilePositioning.TERMINATION.value)
    termination_count = terminations.count()
    termination_amount = terminations.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')

    frameworks = queryset.filter(file_positioning=FilePositioning.FRAMEWORK.value)
    framework_count = frameworks.count()
    framework_amount = frameworks.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')

    # 归档情况
    archived_count = queryset.filter(archive_date__isnull=False).count()
    archive_rate = round(archived_count / total_count * 100, 2) if total_count > 0 else 0

    # 月度趋势（按签订日期）
    monthly_trend_qs = queryset.annotate(
        month=TruncMonth('signing_date')
    ).values('month').annotate(
        count=Count('contract_code'),
        amount=Sum('contract_amount')
    ).order_by('month')

    monthly_trend = []
    for item in monthly_trend_qs:
        if item['month']:
            monthly_trend.append({
                'month': item['month'].strftime('%Y-%m'),
                'count': item['count'],
                'amount': float(item['amount'] or 0) / 10000.0,  # 万元
            })

    return {
        'year': year if year is not None else '全部',
        'total_count': total_count,
        'total_amount': float(total_amount) / 10000.0,  # 万元
        'main_count': main_count,
        'main_amount': float(main_amount) / 10000.0,  # 万元
        'supplement_count': supplement_count,
        'supplement_amount': float(supplement_amount) / 10000.0,  # 万元
        'termination_count': termination_count,
        'termination_amount': float(termination_amount) / 10000.0,  # 万元
        'framework_count': framework_count,
        'framework_amount': float(framework_amount) / 10000.0,  # 万元
        'type_distribution': type_distribution,
        'source_distribution': source_distribution,
        'archived_count': archived_count,
        'archive_rate': archive_rate,
        'monthly_trend': monthly_trend,
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
    main_contracts_query = Contract.objects.filter(file_positioning=FilePositioning.MAIN_CONTRACT.value)
    
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
        
        # 获取已付金额（不应用年份筛选，因为要计算该合同的总已付金额）
        # 只应用项目筛选（如果有的话）
        paid_query = Payment.objects.filter(contract=contract)
        # 注意：这里不应用年份筛选，因为我们要计算该合同的所有历史付款
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
        if payment.contract.file_positioning == FilePositioning.MAIN_CONTRACT.value:
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
    main_contracts_query = Contract.objects.filter(file_positioning=FilePositioning.MAIN_CONTRACT.value)
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
            'contract_sequence': contract.contract_sequence or '',  # 使用合同序号
            'contract_name': contract.contract_name,  # 合同名称
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
    获取综合统计概览（精简实现，保持对外结构与含义不变）。
    - year: 统计年度；None 时采用当前年
    - project_codes: 项目代码列表；None 表示全量
    返回值字段保持与原实现一致。
    """
    if year is None:
        year = get_current_year()

    return {
        'year': year,
        'procurement': get_procurement_statistics(year, project_codes),
        'contract': get_contract_statistics(year, project_codes),
        'payment': get_payment_statistics(year, project_codes),
        # 与原实现一致：settlement 不强制按年过滤
        'settlement': get_settlement_statistics(),
    }


def get_year_comparison(years, project_codes=None):
    """
    多年度数据对比（精简实现，保持兼容）。
    返回结构：{
      'years': [...],
      'procurement': [{'year', 'count', 'amount'}, ...],
      'contract': [{'year', 'count', 'amount'}, ...],
      'payment': [{'year', 'count', 'amount'}, ...],
      'rows': [{ 集合行数据 }]
    }
    """
    data = {
        'years': years,
        'procurement': [],
        'contract': [],
        'payment': [],
        'rows': [],
    }

    for y in years:
        p = get_procurement_statistics(y, project_codes)
        c = get_contract_statistics(y, project_codes)
        pay = get_payment_statistics(y, project_codes)

        data['procurement'].append({'year': y, 'count': p['total_count'], 'amount': p['total_winning']})
        data['contract'].append({'year': y, 'count': c['total_count'], 'amount': c['total_amount']})
        data['payment'].append({'year': y, 'count': pay['total_count'], 'amount': pay['total_amount']})

        data['rows'].append({
            'year': y,
            'procurement_count': p['total_count'],
            'procurement_amount': p['total_winning'],
            'contract_count': c['total_count'],
            'contract_amount': c['total_amount'],
            'payment_count': pay['total_count'],
            'payment_amount': pay['total_amount'],
        })

    return data


# ==================== 详情查询函数 ====================
# 用于支持统计数据的详情查看和导出功能

def get_procurement_details(year=None, project_codes=None):
    """
    获取采购统计的详细数据列表
    
    按采购项目名称去重,返回每个项目名称的代表性记录
    (取预算金额、中标金额、控制价的最大值对应的记录)
    
    Args:
        year: 统计年份,None表示全部年份
        project_codes: 项目编码列表,None表示全部项目
        
    Returns:
        list: 采购详情数据列表,每条记录包含完整的采购信息
    """
    from procurement.models import Procurement
    
    # 基础查询集 - 优化查询性能
    queryset = Procurement.objects.select_related('project').only(
        'procurement_code', 'project_name', 'procurement_method',
        'budget_amount', 'winning_amount', 'control_price', 'archive_date',
        'result_publicity_release_date', 'requirement_approval_date',
        'notice_issue_date', 'planned_completion_date', 'procurement_unit',
        'winning_bidder', 'procurement_category', 'candidate_publicity_end_date',
        'project__project_code', 'project__project_name'
    )
    
    # 年份筛选
    if year is not None:
        queryset = queryset.filter(result_publicity_release_date__year=year)
    
    # 项目筛选
    if project_codes:
        queryset = queryset.filter(project__project_code__in=project_codes)
    
    # 按项目名称分组,取每组的代表性记录
    project_name_records = {}
    
    for proc in queryset:
        project_name = proc.project_name
        if not project_name:
            continue
        
        budget = proc.budget_amount or Decimal('0')
        winning = proc.winning_amount or Decimal('0')
        control = proc.control_price or Decimal('0')
        
        # 如果是第一次遇到此项目名称,或当前记录的金额更大,则保存
        if project_name not in project_name_records:
            project_name_records[project_name] = proc
        else:
            current_proc = project_name_records[project_name]
            current_budget = current_proc.budget_amount or Decimal('0')
            current_winning = current_proc.winning_amount or Decimal('0')
            current_control = current_proc.control_price or Decimal('0')
            
            # 比较金额,取最大值对应的记录
            if (budget + winning + control) > (current_budget + current_winning + current_control):
                project_name_records[project_name] = proc
    
    # 构建详情列表
    details = []
    for proc in project_name_records.values():
        budget_amount = proc.budget_amount or Decimal('0')
        winning_amount = proc.winning_amount or Decimal('0')
        control_price = proc.control_price or Decimal('0')
        savings_amount = budget_amount - winning_amount
        savings_rate = float(savings_amount / budget_amount * 100) if budget_amount > 0 else 0
        
        details.append({
            'procurement_code': proc.procurement_code,
            'project_name': proc.project_name,
            'project_code': proc.project.project_code if proc.project else '',
            'project_full_name': proc.project.project_name if proc.project else '',
            'procurement_unit': proc.procurement_unit or '',
            'winning_bidder': proc.winning_bidder or '',
            'procurement_method': proc.procurement_method or '',
            'procurement_category': proc.procurement_category or '',
            'budget_amount': float(budget_amount),  # 元
            'winning_amount': float(winning_amount),  # 元
            'control_price': float(control_price),  # 元
            'savings_amount': float(savings_amount),  # 元
            'savings_rate': round(savings_rate, 2),  # 百分比
            'result_publicity_release_date': proc.result_publicity_release_date,
            'candidate_publicity_end_date': proc.candidate_publicity_end_date,
            'archive_date': proc.archive_date,
        })
    
    # 按结果公示发布时间倒序排列
    # 使用date对象的min值来避免datetime和date类型比较错误
    from datetime import date as date_type
    details.sort(key=lambda x: x['result_publicity_release_date'] or date_type.min, reverse=True)
    
    return details


def get_contract_details(year=None, project_codes=None):
    """
    获取合同统计的详细数据列表
    
    返回所有合同记录及其付款统计信息
    
    Args:
        year: 统计年份,None表示全部年份
        project_codes: 项目编码列表,None表示全部项目
        
    Returns:
        list: 合同详情数据列表,包含付款统计信息
    """
    from contract.models import Contract
    from payment.models import Payment
    from django.db.models import Sum, Count, DecimalField, Value
    from django.db.models.functions import Coalesce
    
    # 基础查询集
    queryset = Contract.objects.select_related('project', 'parent_contract').only(
        'contract_code', 'contract_sequence', 'contract_name', 'file_positioning',
        'contract_source', 'party_a', 'party_b', 'contract_amount', 'signing_date',
        'archive_date', 'contract_officer',
        'project__project_code', 'project__project_name',
        'parent_contract__contract_code'
    )
    
    # 年份筛选
    if year is not None:
        queryset = queryset.filter(signing_date__year=year)
    
    # 项目筛选
    if project_codes:
        queryset = queryset.filter(project__project_code__in=project_codes)
    
    # 使用annotate预计算付款统计
    zero_decimal = Value(Decimal('0'), output_field=DecimalField(max_digits=18, decimal_places=2))
    queryset = queryset.annotate(
        total_paid=Coalesce(Sum('payments__payment_amount'), zero_decimal),
        payment_count=Count('payments', distinct=True)
    )
    
    # 构建详情列表
    details = []
    for contract in queryset:
        contract_amount = contract.contract_amount or Decimal('0')
        total_paid = getattr(contract, 'total_paid', Decimal('0')) or Decimal('0')
        payment_ratio = float(total_paid / contract_amount * 100) if contract_amount > 0 else 0
        payment_count = getattr(contract, 'payment_count', 0) or 0
        
        details.append({
            'contract_code': contract.contract_code,
            'contract_sequence': contract.contract_sequence or '',
            'contract_name': contract.contract_name,
            'file_positioning': contract.file_positioning,
            'contract_source': contract.contract_source or '',
            'party_a': contract.party_a or '',
            'party_b': contract.party_b or '',
            'contract_amount': float(contract_amount),  # 元
            'signing_date': contract.signing_date,
            'archive_date': contract.archive_date,
            'contract_officer': contract.contract_officer or '',
            'project_code': contract.project.project_code if contract.project else '',
            'project_name': contract.project.project_name if contract.project else '',
            'parent_contract_code': contract.parent_contract.contract_code if contract.parent_contract else '',
            'total_paid': float(total_paid),  # 元
            'payment_count': payment_count,
            'payment_ratio': round(payment_ratio, 2),  # 百分比
        })
    
    # 按签订日期倒序排列
    from datetime import date as date_type
    details.sort(key=lambda x: x['signing_date'] or date_type.min, reverse=True)
    
    return details


def get_payment_details(year=None, project_codes=None):
    """
    获取付款统计的详细数据列表
    
    返回所有付款记录
    
    Args:
        year: 统计年份,None表示全部年份
        project_codes: 项目编码列表,None表示全部项目
        
    Returns:
        list: 付款详情数据列表
    """
    from payment.models import Payment
    
    # 基础查询集
    queryset = Payment.objects.select_related(
        'contract', 
        'contract__project'
    ).only(
        'payment_code', 'payment_amount', 'payment_date', 
        'is_settled', 'settlement_amount',
        'contract__contract_code', 'contract__contract_sequence', 
        'contract__contract_name', 'contract__party_b',
        'contract__project__project_code', 'contract__project__project_name'
    )
    
    # 年份筛选
    if year is not None:
        queryset = queryset.filter(payment_date__year=year)
    
    # 项目筛选
    if project_codes:
        queryset = queryset.filter(contract__project__project_code__in=project_codes)
    
    # 构建详情列表
    details = []
    for payment in queryset:
        payment_amount = payment.payment_amount or Decimal('0')
        settlement_amount = payment.settlement_amount or Decimal('0')
        
        details.append({
            'payment_code': payment.payment_code,
            'payment_amount': float(payment_amount),  # 元
            'payment_date': payment.payment_date,
            'is_settled': payment.is_settled,
            'settlement_amount': float(settlement_amount) if settlement_amount else 0,  # 元
            'contract_code': payment.contract.contract_code if payment.contract else '',
            'contract_sequence': payment.contract.contract_sequence if payment.contract else '',
            'contract_name': payment.contract.contract_name if payment.contract else '',
            'party_b': payment.contract.party_b if payment.contract else '',
            'project_code': payment.contract.project.project_code if payment.contract and payment.contract.project else '',
            'project_name': payment.contract.project.project_name if payment.contract and payment.contract.project else '',
        })
    
    # 按付款日期倒序排列
    from datetime import date as date_type
    details.sort(key=lambda x: x['payment_date'] or date_type.min, reverse=True)
    
    return details


def get_settlement_details(year=None, project_codes=None):
    """
    获取结算统计的详细数据列表
    
    按主合同去重,返回已结算的合同列表及差异分析
    
    Args:
        year: 统计年份,None表示全部年份
        project_codes: 项目编码列表,None表示全部项目
        
    Returns:
        list: 结算详情数据列表,包含差异分析
    """
    from payment.models import Payment
    from contract.models import Contract
    from project.enums import FilePositioning
    
    # 从Payment表中查询已结算的记录
    queryset = Payment.objects.filter(
        is_settled=True,
        settlement_amount__isnull=False
    ).select_related(
        'contract', 
        'contract__project', 
        'contract__parent_contract'
    ).only(
        'payment_code', 'settlement_amount', 'payment_date',
        'contract__contract_code', 'contract__contract_name',
        'contract__contract_amount', 'contract__file_positioning',
        'contract__party_b', 'contract__signing_date',
        'contract__project__project_code', 'contract__project__project_name',
        'contract__parent_contract__contract_code'
    )
    
    # 年份筛选
    if year is not None:
        queryset = queryset.filter(payment_date__year=year)
    
    # 项目筛选
    if project_codes:
        queryset = queryset.filter(contract__project__project_code__in=project_codes)
    
    # 按主合同分组,避免重复
    settlement_by_contract = {}
    
    for payment in queryset:
        if not payment.contract:
            continue
        
        # 确定主合同
        if payment.contract.file_positioning == FilePositioning.MAIN_CONTRACT.value:
            main_contract = payment.contract
            main_contract_code = payment.contract.contract_code
        elif payment.contract.parent_contract:
            main_contract = payment.contract.parent_contract
            main_contract_code = payment.contract.parent_contract.contract_code
        else:
            continue
        
        # 每个主合同只记录一次
        if main_contract_code not in settlement_by_contract:
            settlement_by_contract[main_contract_code] = {
                'contract': main_contract,
                'settlement_amount': payment.settlement_amount or Decimal('0'),
                'payment_date': payment.payment_date,
            }
    
    # 构建详情列表
    details = []
    for contract_code, data in settlement_by_contract.items():
        contract = data['contract']
        settlement_amount = data['settlement_amount']
        
        # 获取合同总额(主合同+补充协议)
        contract_amount = contract.get_contract_with_supplements_amount()
        
        # 计算差异
        variance = settlement_amount - contract_amount
        variance_rate = float(variance / contract_amount * 100) if contract_amount > 0 else 0
        
        details.append({
            'contract_sequence': contract.contract_sequence or '',  # 使用合同序号
            'contract_name': contract.contract_name,
            'party_b': contract.party_b or '',
            'signing_date': contract.signing_date,
            'contract_amount': float(contract_amount),  # 元
            'settlement_amount': float(settlement_amount),  # 元
            'variance': float(variance),  # 元
            'variance_rate': round(variance_rate, 2),  # 百分比
            'payment_date': data['payment_date'],
            'project_code': contract.project.project_code if contract.project else '',
            'project_name': contract.project.project_name if contract.project else '',
        })
    
    # 按差异金额绝对值倒序排列
    details.sort(key=lambda x: abs(x['variance']), reverse=True)
    
    return details