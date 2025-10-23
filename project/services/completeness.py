"""
齐全性检查服务
检查数据的完整性和关联关系
"""
from django.db.models import Q, Count
from project.models import Project
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement


def check_contract_completeness():
    """
    检查合同数据齐全性
    
    Returns:
        dict: 包含各类齐全性检查结果
    """
    issues = []
    
    # 检查1: 补充协议未关联主合同
    supplements_without_parent = Contract.objects.filter(
        contract_type='补充协议',
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
        contract_type='解除协议',
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
    procurement_contracts_without_procurement = Contract.objects.filter(
        contract_source='采购合同',
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
        contract_type='主合同',
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
        contract_source='直接签订',
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
    for contract in Contract.objects.filter(contract_type='主合同'):
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
    for contract in Contract.objects.filter(contract_type='主合同'):
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
    
    total_contracts = Contract.objects.filter(contract_type='主合同').count()
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


def get_completeness_overview():
    """
    获取整体齐全性检查概览
    
    Returns:
        dict: 所有检查的汇总结果
    """
    contract_result = check_contract_completeness()
    project_result = check_project_completeness()
    payment_result = check_payment_settlement_completeness()
    
    # 汇总所有问题
    all_issues = (
        contract_result['issues'] + 
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
        'contract_check': contract_result,
        'project_check': project_result,
        'payment_check': payment_result
    }
    
    return overview