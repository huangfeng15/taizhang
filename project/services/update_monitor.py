"""
更新监控服务
监控各模块数据的更新时效性
"""
from django.db.models import F, Q
from django.utils import timezone
from datetime import timedelta
from project.models import Project
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement


def get_project_update_status(warning_days=40):
    """
    获取各项目各模块最近更新状态
    
    Args:
        warning_days: 超过多少天未更新则预警，默认40天
    
    Returns:
        dict: 包含各项目的更新状态信息
    """
    today = timezone.now().date()
    warning_date = today - timedelta(days=warning_days)
    
    # 获取所有项目
    projects = Project.objects.all()
    
    project_status_list = []
    total_warning_count = 0
    
    for project in projects:
        project_info = {
            'project_code': project.project_code,
            'project_name': project.project_name,
            'modules': {},
            'has_warning': False
        }
        
        # 检查项目本身的更新状态
        project_days = (today - project.updated_at.date()).days if project.updated_at is not None else None
        project_info['modules']['项目信息'] = {
            'last_update': project.updated_at.date() if project.updated_at is not None else None,
            'days_ago': project_days,
            'is_warning': project_days and project_days > warning_days,
            'count': 1
        }
        if project_days and project_days > warning_days:
            project_info['has_warning'] = True
            total_warning_count += 1
        
        # 检查采购模块
        procurements = project.procurements.all()
        if procurements.exists():
            latest_procurement = procurements.order_by('-updated_at').first()
            days_ago = None
            last_update = None
            if latest_procurement and latest_procurement.updated_at is not None:
                days_ago = (today - latest_procurement.updated_at.date()).days
                last_update = latest_procurement.updated_at.date()
            project_info['modules']['采购'] = {
                'last_update': last_update,
                'days_ago': days_ago,
                'is_warning': days_ago and days_ago > warning_days,
                'count': procurements.count()
            }
            if days_ago and days_ago > warning_days:
                project_info['has_warning'] = True
                total_warning_count += 1
        
        # 检查合同模块
        contracts = project.contracts.all()
        if contracts.exists():
            latest_contract = contracts.order_by('-updated_at').first()
            days_ago = None
            last_update = None
            if latest_contract and latest_contract.updated_at is not None:
                days_ago = (today - latest_contract.updated_at.date()).days
                last_update = latest_contract.updated_at.date()
            project_info['modules']['合同'] = {
                'last_update': last_update,
                'days_ago': days_ago,
                'is_warning': days_ago and days_ago > warning_days,
                'count': contracts.count()
            }
            if days_ago and days_ago > warning_days:
                project_info['has_warning'] = True
                total_warning_count += 1
        
        # 检查付款模块（通过合同关联）
        payments = Payment.objects.filter(contract__project=project)
        if payments.exists():
            latest_payment = payments.order_by('-updated_at').first()
            days_ago = (today - latest_payment.updated_at.date()).days if latest_payment and latest_payment.updated_at is not None else None
            project_info['modules']['付款'] = {
                'last_update': latest_payment.updated_at.date() if latest_payment and latest_payment.updated_at is not None else None,
                'days_ago': days_ago,
                'is_warning': days_ago and days_ago > warning_days,
                'count': payments.count()
            }
            if days_ago and days_ago > warning_days:
                project_info['has_warning'] = True
                total_warning_count += 1
        
        # 检查结算模块（通过主合同关联）
        settlements = Settlement.objects.filter(main_contract__project=project)
        if settlements.exists():
            latest_settlement = settlements.order_by('-updated_at').first()
            days_ago = (today - latest_settlement.updated_at.date()).days if latest_settlement and latest_settlement.updated_at is not None else None
            project_info['modules']['结算'] = {
                'last_update': latest_settlement.updated_at.date() if latest_settlement and latest_settlement.updated_at is not None else None,
                'days_ago': days_ago,
                'is_warning': days_ago and days_ago > warning_days,
                'count': settlements.count()
            }
            if days_ago and days_ago > warning_days:
                project_info['has_warning'] = True
                total_warning_count += 1
        
        project_status_list.append(project_info)
    
    # 统计信息
    summary = {
        'total_projects': projects.count(),
        'warning_count': total_warning_count,
        'warning_days': warning_days,
        'check_date': today
    }
    
    return {
        'summary': summary,
        'projects': project_status_list
    }


def get_module_update_overview(warning_days=40):
    """
    获取各模块整体更新概览
    
    Args:
        warning_days: 超过多少天未更新则预警，默认40天
    
    Returns:
        dict: 各模块的更新统计信息
    """
    today = timezone.now().date()
    warning_date = today - timedelta(days=warning_days)
    
    modules_overview = {}
    
    # 项目模块
    projects = Project.objects.all()
    project_warnings = projects.filter(updated_at__date__lt=warning_date).count()
    modules_overview['项目'] = {
        'total': projects.count(),
        'warning': project_warnings,
        'normal': projects.count() - project_warnings
    }
    
    # 采购模块
    procurements = Procurement.objects.all()
    procurement_warnings = procurements.filter(updated_at__date__lt=warning_date).count()
    modules_overview['采购'] = {
        'total': procurements.count(),
        'warning': procurement_warnings,
        'normal': procurements.count() - procurement_warnings
    }
    
    # 合同模块
    contracts = Contract.objects.all()
    contract_warnings = contracts.filter(updated_at__date__lt=warning_date).count()
    modules_overview['合同'] = {
        'total': contracts.count(),
        'warning': contract_warnings,
        'normal': contracts.count() - contract_warnings
    }
    
    # 付款模块
    payments = Payment.objects.all()
    payment_warnings = payments.filter(updated_at__date__lt=warning_date).count()
    modules_overview['付款'] = {
        'total': payments.count(),
        'warning': payment_warnings,
        'normal': payments.count() - payment_warnings
    }
    
    # 结算模块
    settlements = Settlement.objects.all()
    settlement_warnings = settlements.filter(updated_at__date__lt=warning_date).count()
    modules_overview['结算'] = {
        'total': settlements.count(),
        'warning': settlement_warnings,
        'normal': settlements.count() - settlement_warnings
    }
    
    return {
        'modules': modules_overview,
        'warning_days': warning_days,
        'check_date': today
    }


def get_outdated_records(module_name, warning_days=40, limit=50):
    """
    获取指定模块的过期记录列表
    
    Args:
        module_name: 模块名称（项目/采购/合同/付款/结算）
        warning_days: 超过多少天未更新则预警
        limit: 返回记录数量限制
    
    Returns:
        list: 过期记录列表
    """
    today = timezone.now().date()
    warning_date = today - timedelta(days=warning_days)
    
    model_map = {
        '项目': Project,
        '采购': Procurement,
        '合同': Contract,
        '付款': Payment,
        '结算': Settlement
    }
    
    if module_name not in model_map:
        return []
    
    Model = model_map[module_name]
    records = Model.objects.filter(
        updated_at__date__lt=warning_date
    ).order_by('updated_at')[:limit]
    
    result = []
    for record in records:
        days_ago = (today - record.updated_at.date()).days if record.updated_at is not None else None
        
        # 根据不同模型获取名称和编号
        if module_name == '项目':
            code = record.project_code
            name = record.project_name
        elif module_name == '采购':
            code = record.procurement_code
            name = record.project_name
        elif module_name == '合同':
            code = record.contract_code
            name = record.contract_name
        elif module_name == '付款':
            code = record.payment_code
            name = f"付款 {record.payment_amount}元"
        elif module_name == '结算':
            code = record.settlement_code
            name = f"结算 {record.final_amount}元"
        else:
            code = str(record.pk)
            name = str(record)
        
        result.append({
            'code': code,
            'name': name,
            'last_update': record.updated_at.date() if record.updated_at is not None else None,
            'days_ago': days_ago,
            'updated_by': record.updated_by if hasattr(record, 'updated_by') else ''
        })
    
    return result