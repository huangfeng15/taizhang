"""
齐全性检查服务
检查数据的完整性和关联关系
按照指标体系需求文档设计，展示采购和合同字段的齐全率
"""
from django.db.models import Q, Count
from project.models import Project
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement
from project.enums import FilePositioning, ContractSource


def check_procurement_field_completeness(year=None, project_codes=None):
    """
    检查采购字段齐全性
    按照需求文档，检查26个关键字段的填写情况
    
    Args:
        year: 年份筛选(None表示全部年份)
        project_codes: 项目编码列表(None表示全部项目)
    
    Returns:
        dict: 采购字段齐全性统计
    """
    # 定义需要检查的26个字段
    required_fields = [
        'procurement_code',  # 招采编号
        'project_name',  # 采购项目名称
        'procurement_unit',  # 采购单位
        'winning_bidder',  # 中标单位
        'winning_contact',  # 中标单位联系人及方式
        'procurement_method',  # 采购方式
        'procurement_category',  # 采购类别
        'budget_amount',  # 采购预算金额(元)
        'control_price',  # 采购控制价（元）
        'winning_amount',  # 中标金额（元）
        'planned_completion_date',  # 计划结束采购时间
        'candidate_publicity_end_date',  # 候选人公示结束时间
        'result_publicity_release_date',  # 结果公示发布时间
        'notice_issue_date',  # 中标通知书发放日期
        'procurement_officer',  # 采购经办人
        'demand_department',  # 需求部门
        'demand_contact',  # 申请人联系电话（需求部门）
        'requirement_approval_date',  # 采购需求书审批完成日期（OA）
        'procurement_platform',  # 采购平台
        'qualification_review_method',  # 资格审查方式
        'bid_evaluation_method',  # 评标谈判方式
        'bid_awarding_method',  # 定标方法
        'announcement_release_date',  # 公告发布时间
        'registration_deadline',  # 报名截止时间
        'bid_opening_date',  # 开标时间
        'evaluation_committee',  # 评标委员会成员
    ]
    
    # 应用筛选条件 - 使用select_related和only优化查询
    all_procurements = Procurement.objects.select_related('project').only(
        'procurement_code', 'project_name', 'procurement_unit', 'winning_bidder',
        'winning_contact', 'procurement_method', 'procurement_category', 'budget_amount',
        'control_price', 'winning_amount', 'planned_completion_date', 'candidate_publicity_end_date',
        'result_publicity_release_date', 'notice_issue_date', 'procurement_officer', 'demand_department',
        'demand_contact', 'requirement_approval_date', 'procurement_platform', 'qualification_review_method',
        'bid_evaluation_method', 'bid_awarding_method', 'announcement_release_date', 'registration_deadline',
        'bid_opening_date', 'evaluation_committee', 'project__project_code'
    )
    if year:
        all_procurements = all_procurements.filter(result_publicity_release_date__year=year)
    if project_codes:
        all_procurements = all_procurements.filter(project__project_code__in=project_codes)
    total_count = all_procurements.count()
    
    if total_count == 0:
        return {
            'total_count': 0,
            'completeness_rate': 0.0,
            'field_count': len(required_fields),
            'field_stats': [],
            'incomplete_records': [],
            'incomplete_count': 0
        }
    
    # 统计每个字段的填写情况
    field_stats = []
    for field_name in required_fields:
        filled_count = 0
        for procurement in all_procurements:
            value = getattr(procurement, field_name, None)
            # 判断字段是否已填写（非空且不是空字符串）
            if value is not None and value != '':
                filled_count += 1
        
        fill_rate = (filled_count / total_count) * 100 if total_count > 0 else 0
        field_stats.append({
            'field_name': field_name,
            'field_label': Procurement._meta.get_field(field_name).verbose_name,
            'filled_count': filled_count,
            'fill_rate': round(fill_rate, 2)
        })
    
    # 计算每条采购记录的齐全率
    incomplete_records = []
    for procurement in all_procurements:
        filled_fields = 0
        missing_fields = []
        
        for field_name in required_fields:
            value = getattr(procurement, field_name, None)
            if value is not None and value != '':
                filled_fields += 1
            else:
                field_label = Procurement._meta.get_field(field_name).verbose_name
                missing_fields.append(field_label)
        
        completeness = (filled_fields / len(required_fields)) * 100
        
        # 只记录齐全率低于100%的记录
        if completeness < 100:
            incomplete_records.append({
                'code': procurement.procurement_code,
                'name': procurement.project_name,
                'completeness': round(completeness, 2),
                'filled_count': filled_fields,
                'total_fields': len(required_fields),
                'missing_fields': missing_fields[:5],  # 只显示前5个缺失字段
                'missing_count': len(missing_fields)
            })
    
    # 按齐全率排序，最低的在前
    incomplete_records.sort(key=lambda x: x['completeness'])
    
    # 计算总体齐全率
    total_filled = sum(stat['filled_count'] for stat in field_stats)
    total_cells = total_count * len(required_fields)
    overall_completeness = (total_filled / total_cells) * 100 if total_cells > 0 else 100.0
    
    return {
        'total_count': total_count,
        'completeness_rate': round(overall_completeness, 2),
        'field_count': len(required_fields),
        'field_stats': field_stats,
        'incomplete_records': incomplete_records[:50],  # 只返回前50条
        'incomplete_count': len(incomplete_records)
    }


def check_contract_field_completeness(year=None, project_codes=None):
    """
    检查合同字段齐全性
    按照需求文档，检查17个关键字段的填写情况
    
    Args:
        year: 年份筛选(None表示全部年份)
        project_codes: 项目编码列表(None表示全部项目)
    
    Returns:
        dict: 合同字段齐全性统计
    """
    # 定义需要检查的17个字段
    required_fields = [
        'contract_sequence',  # 合同序号
        'contract_code',  # 合同编号
        'contract_name',  # 合同名称
        'contract_officer',  # 合同签订经办人
        'file_positioning',  # 合同类型
        'party_a',  # 甲方
        'party_b',  # 乙方
        'contract_amount',  # 含税签约合同价（元）
        'signing_date',  # 合同签订日期
        'party_a_legal_representative',  # 甲方法定代表人及联系方式
        'party_a_contact_person',  # 甲方联系人及联系方式
        'party_a_manager',  # 甲方负责人及联系方式
        'party_b_legal_representative',  # 乙方法定代表人及联系方式
        'party_b_contact_person',  # 乙方联系人及联系方式
        'party_b_manager',  # 乙方负责人及联系方式
        'duration',  # 合同工期/服务期限
        'payment_method',  # 支付方式
    ]
    
    # 应用筛选条件 - 使用select_related和only优化查询
    all_contracts = Contract.objects.select_related('project').only(
        'contract_sequence', 'contract_code', 'contract_name', 'contract_officer',
        'file_positioning', 'party_a', 'party_b', 'contract_amount', 'signing_date',
        'party_a_legal_representative', 'party_a_contact_person', 'party_a_manager',
        'party_b_legal_representative', 'party_b_contact_person', 'party_b_manager',
        'duration', 'payment_method', 'project__project_code'
    )
    if year:
        all_contracts = all_contracts.filter(signing_date__year=year)
    if project_codes:
        all_contracts = all_contracts.filter(project__project_code__in=project_codes)
    total_count = all_contracts.count()
    
    if total_count == 0:
        return {
            'total_count': 0,
            'completeness_rate': 0.0,
            'field_count': len(required_fields),
            'field_stats': [],
            'incomplete_records': [],
            'incomplete_count': 0
        }
    
    # 统计每个字段的填写情况
    field_stats = []
    for field_name in required_fields:
        filled_count = 0
        for contract in all_contracts:
            value = getattr(contract, field_name, None)
            # 判断字段是否已填写（非空且不是空字符串）
            if value is not None and value != '':
                filled_count += 1
        
        fill_rate = (filled_count / total_count) * 100 if total_count > 0 else 0
        field_stats.append({
            'field_name': field_name,
            'field_label': Contract._meta.get_field(field_name).verbose_name,
            'filled_count': filled_count,
            'fill_rate': round(fill_rate, 2)
        })
    
    # 计算每条合同记录的齐全率
    incomplete_records = []
    for contract in all_contracts:
        filled_fields = 0
        missing_fields = []
        
        for field_name in required_fields:
            value = getattr(contract, field_name, None)
            if value is not None and value != '':
                filled_fields += 1
            else:
                field_label = Contract._meta.get_field(field_name).verbose_name
                missing_fields.append(field_label)
        
        completeness = (filled_fields / len(required_fields)) * 100
        
        # 只记录齐全率低于100%的记录
        if completeness < 100:
            incomplete_records.append({
                'code': contract.contract_code,
                'name': contract.contract_name,
                'completeness': round(completeness, 2),
                'filled_count': filled_fields,
                'total_fields': len(required_fields),
                'missing_fields': missing_fields[:5],  # 只显示前5个缺失字段
                'missing_count': len(missing_fields)
            })
    
    # 按齐全率排序，最低的在前
    incomplete_records.sort(key=lambda x: x['completeness'])
    
    # 计算总体齐全率
    total_filled = sum(stat['filled_count'] for stat in field_stats)
    total_cells = total_count * len(required_fields)
    overall_completeness = (total_filled / total_cells) * 100 if total_cells > 0 else 100.0
    
    return {
        'total_count': total_count,
        'completeness_rate': round(overall_completeness, 2),
        'field_count': len(required_fields),
        'field_stats': field_stats,
        'incomplete_records': incomplete_records[:50],  # 只返回前50条
        'incomplete_count': len(incomplete_records)
    }


def check_contract_completeness():
    """
    检查合同数据关联齐全性（保留原有功能用于关联检查）
    
    Returns:
        dict: 包含各类齐全性检查结果
    """
    issues = []
    
    # 检查1: 补充协议未关联主合同
    from project.enums import FilePositioning
    supplements_without_parent = Contract.objects.filter(
        file_positioning=FilePositioning.SUPPLEMENT.value,
        parent_contract__isnull=True
    )
    if supplements_without_parent.exists():
        issues.append({
            'type': 'error',
            'category': '补充协议关联',
            'description': '补充协议必须关联主合同',
            'count': supplements_without_parent.count(),
            'records': [
                {
                    'code': c.contract_code,
                    'name': c.contract_name,
                    'issue': '未关联主合同'
                }
                for c in supplements_without_parent[:20]
            ]
        })
    
    # 检查2: 解除协议未关联主合同
    terminations_without_parent = Contract.objects.filter(
        file_positioning=FilePositioning.TERMINATION.value,
        parent_contract__isnull=True
    )
    if terminations_without_parent.exists():
        issues.append({
            'type': 'error',
            'category': '解除协议关联',
            'description': '解除协议必须关联主合同',
            'count': terminations_without_parent.count(),
            'records': [
                {
                    'code': c.contract_code,
                    'name': c.contract_name,
                    'issue': '未关联主合同'
                }
                for c in terminations_without_parent[:20]
            ]
        })
    
    # 检查3: 采购合同未关联采购项目
    from project.enums import ContractSource
    procurement_contracts_without_procurement = Contract.objects.filter(
        contract_source=ContractSource.PROCUREMENT.value,
        procurement__isnull=True
    )
    if procurement_contracts_without_procurement.exists():
        issues.append({
            'type': 'error',
            'category': '采购合同关联',
            'description': '采购合同必须关联采购项目',
            'count': procurement_contracts_without_procurement.count(),
            'records': [
                {
                    'code': c.contract_code,
                    'name': c.contract_name,
                    'issue': '未关联采购项目'
                }
                for c in procurement_contracts_without_procurement[:20]
            ]
        })
    
    # 检查4: 主合同不应关联其他合同
    main_contracts_with_parent = Contract.objects.filter(
        file_positioning=FilePositioning.MAIN_CONTRACT.value,
        parent_contract__isnull=False
    )
    if main_contracts_with_parent.exists():
        issues.append({
            'type': 'error',
            'category': '主合同关联',
            'description': '主合同不应关联其他合同',
            'count': main_contracts_with_parent.count(),
            'records': [
                {
                    'code': c.contract_code,
                    'name': c.contract_name,
                    'issue': f'错误关联了合同: {c.parent_contract.contract_code}'
                }
                for c in main_contracts_with_parent[:20]
            ]
        })
    
    # 检查5: 直接签订合同不应关联采购项目
    direct_contracts_with_procurement = Contract.objects.filter(
        contract_source=ContractSource.DIRECT.value,
        procurement__isnull=False
    )
    if direct_contracts_with_procurement.exists():
        issues.append({
            'type': 'warning',
            'category': '直接签订合同关联',
            'description': '直接签订合同不应关联采购项目',
            'count': direct_contracts_with_procurement.count(),
            'records': [
                {
                    'code': c.contract_code,
                    'name': c.contract_name,
                    'issue': f'错误关联了采购: {c.procurement.procurement_code}'
                }
                for c in direct_contracts_with_procurement[:20]
            ]
        })
    
    # 统计信息
    total_contracts = Contract.objects.count()
    total_issues = sum(issue['count'] for issue in issues)
    
    summary = {
        'total_contracts': total_contracts,
        'total_issues': total_issues,
        'error_count': sum(issue['count'] for issue in issues if issue['type'] == 'error'),
        'warning_count': sum(issue['count'] for issue in issues if issue['type'] == 'warning'),
        'health_rate': round((1 - total_issues / total_contracts) * 100, 2) if total_contracts > 0 else 100
    }
    
    return {
        'summary': summary,
        'issues': issues
    }


def check_project_completeness():
    """
    检查项目关联完整性
    
    Returns:
        dict: 项目关联检查结果
    """
    issues = []
    
    # 检查1: 采购项目未关联项目
    procurements_without_project = Procurement.objects.filter(
        project__isnull=True
    )
    if procurements_without_project.exists():
        issues.append({
            'type': 'warning',
            'category': '采购项目关联',
            'description': '采购项目建议关联到项目',
            'count': procurements_without_project.count(),
            'records': [
                {
                    'code': p.procurement_code,
                    'name': p.project_name,
                    'issue': '未关联项目'
                }
                for p in procurements_without_project[:20]
            ]
        })
    
    # 检查2: 合同未关联项目
    contracts_without_project = Contract.objects.filter(
        project__isnull=True
    )
    if contracts_without_project.exists():
        issues.append({
            'type': 'warning',
            'category': '合同项目关联',
            'description': '合同建议关联到项目',
            'count': contracts_without_project.count(),
            'records': [
                {
                    'code': c.contract_code,
                    'name': c.contract_name,
                    'issue': '未关联项目'
                }
                for c in contracts_without_project[:20]
            ]
        })
    
    # 检查3: 空项目（没有任何采购或合同）
    empty_projects = []
    for project in Project.objects.all():
        procurement_count = project.procurements.count()
        contract_count = project.contracts.count()
        if procurement_count == 0 and contract_count == 0:
            empty_projects.append({
                'code': project.project_code,
                'name': project.project_name,
                'issue': '项目下无采购或合同数据'
            })
    
    if empty_projects:
        issues.append({
            'type': 'info',
            'category': '空项目',
            'description': '项目下没有关联的采购或合同',
            'count': len(empty_projects),
            'records': empty_projects[:20]
        })
    
    total_projects = Project.objects.count()
    total_procurements = Procurement.objects.count()
    total_contracts = Contract.objects.count()
    
    summary = {
        'total_projects': total_projects,
        'total_procurements': total_procurements,
        'total_contracts': total_contracts,
        'procurements_without_project': procurements_without_project.count(),
        'contracts_without_project': contracts_without_project.count(),
        'empty_projects': len(empty_projects)
    }
    
    return {
        'summary': summary,
        'issues': issues
    }


def check_payment_settlement_completeness():
    """
    检查付款和结算数据完整性
    
    Returns:
        dict: 付款结算检查结果
    """
    issues = []
    
    # 检查1: 付款超过合同金额
    overpaid_contracts = []
    for contract in Contract.objects.filter(file_positioning=FilePositioning.MAIN_CONTRACT.value):
        total_paid = contract.get_total_paid_amount()
        contract_with_supplements = contract.get_contract_with_supplements_amount()
        
        # 如果有结算，使用结算价
        try:
            if hasattr(contract, 'settlement') and contract.settlement:
                base_amount = contract.settlement.final_amount
            else:
                base_amount = contract_with_supplements
        except:
            base_amount = contract_with_supplements
        
        if total_paid > base_amount and base_amount > 0:
            overpaid_contracts.append({
                'code': contract.contract_code,
                'name': contract.contract_name,
                'contract_amount': float(base_amount),
                'paid_amount': float(total_paid),
                'overpaid': float(total_paid - base_amount),
                'issue': f'付款超出 {float(total_paid - base_amount):.2f}元'
            })
    
    if overpaid_contracts:
        issues.append({
            'type': 'error',
            'category': '付款超额',
            'description': '付款金额超过合同金额（含补充协议/结算价）',
            'count': len(overpaid_contracts),
            'records': overpaid_contracts[:20]
        })
    
    # 检查2: 结算金额与合同金额差异过大（超过10%）
    settlement_mismatch = []
    for settlement in Settlement.objects.all():
        contract_total = settlement.get_total_contract_amount()
        settlement_amount = settlement.final_amount
        
        if contract_total > 0:
            diff_rate = abs(settlement_amount - contract_total) / contract_total
            if diff_rate > 0.1:  # 超过10%
                settlement_mismatch.append({
                    'code': settlement.settlement_code,
                    'contract': settlement.main_contract.contract_code,
                    'contract_amount': float(contract_total),
                    'settlement_amount': float(settlement_amount),
                    'diff_rate': round(diff_rate * 100, 2),
                    'issue': f'差异率 {round(diff_rate * 100, 2)}%'
                })
    
    if settlement_mismatch:
        issues.append({
            'type': 'warning',
            'category': '结算差异',
            'description': '结算金额与合同金额差异超过10%',
            'count': len(settlement_mismatch),
            'records': settlement_mismatch[:20]
        })
    
    # 检查3: 主合同没有付款记录
    main_contracts_without_payment = []
    for contract in Contract.objects.filter(file_positioning=FilePositioning.MAIN_CONTRACT.value):
        if contract.get_payment_count() == 0:
            main_contracts_without_payment.append({
                'code': contract.contract_code,
                'name': contract.contract_name,
                'contract_amount': float(contract.contract_amount) if contract.contract_amount else 0,
                'issue': '暂无付款记录'
            })
    
    if main_contracts_without_payment:
        issues.append({
            'type': 'info',
            'category': '无付款记录',
            'description': '主合同暂无付款记录',
            'count': len(main_contracts_without_payment),
            'records': main_contracts_without_payment[:20]
        })
    
    total_contracts = Contract.objects.filter(file_positioning=FilePositioning.MAIN_CONTRACT.value).count()
    total_payments = Payment.objects.count()
    total_settlements = Settlement.objects.count()
    
    summary = {
        'total_main_contracts': total_contracts,
        'total_payments': total_payments,
        'total_settlements': total_settlements,
        'overpaid_contracts': len(overpaid_contracts),
        'settlement_mismatch': len(settlement_mismatch),
        'contracts_without_payment': len(main_contracts_without_payment)
    }
    
    return {
        'summary': summary,
        'issues': issues
    }


def get_completeness_overview(year=None, project_codes=None):
    """
    获取整体齐全性检查概览
    包含字段齐全性和关联完整性检查
    
    Args:
        year: 年份筛选(None表示全部年份)
        project_codes: 项目编码列表(None表示全部项目)
    
    Returns:
        dict: 所有检查的汇总结果
    """
    # 字段齐全性检查
    procurement_field_result = check_procurement_field_completeness(year, project_codes)
    contract_field_result = check_contract_field_completeness(year, project_codes)
    
    # 关联完整性检查
    contract_relation_result = check_contract_completeness()
    project_result = check_project_completeness()
    payment_result = check_payment_settlement_completeness()
    
    # 汇总所有问题
    all_issues = (
        contract_relation_result['issues'] + 
        project_result['issues'] + 
        payment_result['issues']
    )
    
    total_error_count = sum(issue['count'] for issue in all_issues if issue['type'] == 'error')
    total_warning_count = sum(issue['count'] for issue in all_issues if issue['type'] == 'warning')
    total_info_count = sum(issue['count'] for issue in all_issues if issue['type'] == 'info')
    
    overview = {
        'total_issues': len(all_issues),
        'error_count': total_error_count,
        'warning_count': total_warning_count,
        'info_count': total_info_count,
        # 字段齐全性
        'procurement_field_check': procurement_field_result,
        'contract_field_check': contract_field_result,
        # 关联完整性
        'contract_check': contract_relation_result,
        'project_check': project_result,
        'payment_check': payment_result
    }
    
    return overview


def get_project_completeness_ranking(year=None, project_codes=None):
    """
    获取项目字段完整性排行榜
    按采购和合同齐全率综合排名
    
    Args:
        year: 年份筛选(None表示全部年份)
        project_codes: 项目编码列表(None表示全部项目)
    
    Returns:
        list: 项目排行榜数据
    """
    from project.models import Project
    
    # 获取项目列表
    projects = Project.objects.all()
    if project_codes:
        projects = projects.filter(project_code__in=project_codes)
    
    rankings = []
    
    for project in projects:
        # 获取该项目的采购记录
        procurements = Procurement.objects.filter(project=project)
        if year:
            procurements = procurements.filter(result_publicity_release_date__year=year)
        
        # 获取该项目的合同记录
        contracts = Contract.objects.filter(project=project)
        if year:
            contracts = contracts.filter(signing_date__year=year)
        
        # 计算采购齐全率
        procurement_rate = 0
        procurement_count = procurements.count()
        if procurement_count > 0:
            # 采购字段定义
            procurement_fields = [
                'procurement_code', 'project_name', 'procurement_unit', 'winning_bidder',
                'winning_contact', 'procurement_method', 'procurement_category', 'budget_amount',
                'control_price', 'winning_amount', 'planned_completion_date', 'candidate_publicity_end_date',
                'result_publicity_release_date', 'notice_issue_date', 'procurement_officer', 'demand_department',
                'demand_contact', 'requirement_approval_date', 'procurement_platform', 'qualification_review_method',
                'bid_evaluation_method', 'bid_awarding_method', 'announcement_release_date', 'registration_deadline',
                'bid_opening_date', 'evaluation_committee'
            ]
            
            total_cells = procurement_count * len(procurement_fields)
            filled_cells = 0
            
            for proc in procurements:
                for field_name in procurement_fields:
                    value = getattr(proc, field_name, None)
                    if value is not None and value != '':
                        filled_cells += 1
            
            procurement_rate = round((filled_cells / total_cells) * 100, 2) if total_cells > 0 else 0
        
        # 计算合同齐全率
        contract_rate = 0
        contract_count = contracts.count()
        if contract_count > 0:
            # 合同字段定义
            contract_fields = [
                'contract_sequence', 'contract_code', 'contract_name', 'contract_officer',
                'file_positioning', 'party_a', 'party_b', 'contract_amount', 'signing_date',
                'party_a_legal_representative', 'party_a_contact_person', 'party_a_manager',
                'party_b_legal_representative', 'party_b_contact_person', 'party_b_manager',
                'duration', 'payment_method'
            ]
            
            total_cells = contract_count * len(contract_fields)
            filled_cells = 0
            
            for contract in contracts:
                for field_name in contract_fields:
                    value = getattr(contract, field_name, None)
                    if value is not None and value != '':
                        filled_cells += 1
            
            contract_rate = round((filled_cells / total_cells) * 100, 2) if total_cells > 0 else 0
        
        # 计算综合齐全率（采购和合同的平均值）
        if procurement_count > 0 and contract_count > 0:
            overall_rate = round((procurement_rate + contract_rate) / 2, 2)
        elif procurement_count > 0:
            overall_rate = procurement_rate
        elif contract_count > 0:
            overall_rate = contract_rate
        else:
            overall_rate = 0
        
        # 只有当项目有数据时才加入排行榜
        if procurement_count > 0 or contract_count > 0:
            rankings.append({
                'project_code': project.project_code,
                'project_name': project.project_name,
                'procurement_rate': procurement_rate,
                'contract_rate': contract_rate,
                'overall_rate': overall_rate,
                'procurement_count': procurement_count,
                'contract_count': contract_count,
            })
    
    # 按综合齐全率降序排序
    rankings.sort(key=lambda x: x['overall_rate'], reverse=True)
    
    # 添加排名
    for i, item in enumerate(rankings, 1):
        item['rank'] = i
    
    return rankings