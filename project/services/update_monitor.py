"""
更新监控服务
监控各模块数据的更新时效性
按照指标体系需求文档第3章设计
"""
from django.db.models import F, Q, Max
from django.utils import timezone
from datetime import timedelta
from project.models import Project
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement


def get_project_update_status(warning_days=40, project_codes=None, only_active=True):
    """
    获取各项目各模块最近更新状态
    按照需求文档3.2.1设计：展示表格形式，含颜色标识
    
    Args:
        warning_days: 超过多少天未更新则预警，默认40天
        project_codes: 要筛选的项目编码列表，None表示全部
        only_active: 是否仅显示进行中的项目，默认True
    
    Returns:
        dict: 包含各项目的更新状态信息
    """
    today = timezone.now().date()
    mild_warning_days = 30  # 30-40天：黄色预警
    
    # 获取项目
    projects = Project.objects.all()
    if project_codes:
        projects = projects.filter(project_code__in=project_codes)
    if only_active:
        projects = projects.filter(status='进行中')
    
    project_status_list = []
    warning_projects = 0
    normal_projects = 0
    
    for project in projects:
        project_info = {
            'project_code': project.project_code,
            'project_name': project.project_name,
            'project_status': project.status,
            'modules': {},
            'overall_status': 'normal',  # normal/warning/error
            'warning_count': 0
        }
        
        module_warnings = 0
        
        # 检查采购模块
        procurements = project.procurements.all()
        if procurements.exists():
            latest = procurements.order_by('-updated_at').first()
            days_ago = (today - latest.updated_at.date()).days if latest and latest.updated_at else None
            
            # 确定状态
            status = 'normal'
            if days_ago is not None:
                if days_ago > warning_days:
                    status = 'error'  # 红色
                    module_warnings += 1
                elif days_ago > mild_warning_days:
                    status = 'warning'  # 黄色
            
            project_info['modules']['采购'] = {
                'last_update': latest.updated_at.date() if latest and latest.updated_at else None,
                'days_ago': days_ago,
                'status': status,
                'count': procurements.count(),
                'latest_code': latest.procurement_code if latest else None
            }
        else:
            project_info['modules']['采购'] = {
                'last_update': None,
                'days_ago': None,
                'status': 'no_data',
                'count': 0,
                'latest_code': None
            }
        
        # 检查合同模块
        contracts = project.contracts.all()
        if contracts.exists():
            latest = contracts.order_by('-updated_at').first()
            days_ago = (today - latest.updated_at.date()).days if latest and latest.updated_at else None
            
            status = 'normal'
            if days_ago is not None:
                if days_ago > warning_days:
                    status = 'error'
                    module_warnings += 1
                elif days_ago > mild_warning_days:
                    status = 'warning'
            
            project_info['modules']['合同'] = {
                'last_update': latest.updated_at.date() if latest and latest.updated_at else None,
                'days_ago': days_ago,
                'status': status,
                'count': contracts.count(),
                'latest_code': latest.contract_code if latest else None
            }
        else:
            project_info['modules']['合同'] = {
                'last_update': None,
                'days_ago': None,
                'status': 'no_data',
                'count': 0,
                'latest_code': None
            }
        
        # 检查付款模块
        payments = Payment.objects.filter(contract__project=project)
        if payments.exists():
            latest = payments.order_by('-created_at').first()  # 付款按创建时间
            days_ago = (today - latest.created_at.date()).days if latest and latest.created_at else None
            
            status = 'normal'
            if days_ago is not None:
                if days_ago > warning_days:
                    status = 'error'
                    module_warnings += 1
                elif days_ago > mild_warning_days:
                    status = 'warning'
            
            project_info['modules']['付款'] = {
                'last_update': latest.created_at.date() if latest and latest.created_at else None,
                'days_ago': days_ago,
                'status': status,
                'count': payments.count(),
                'latest_code': latest.payment_code if latest else None
            }
        else:
            project_info['modules']['付款'] = {
                'last_update': None,
                'days_ago': None,
                'status': 'no_data',
                'count': 0,
                'latest_code': None
            }
        
        # 检查结算模块
        settlements = Settlement.objects.filter(main_contract__project=project)
        if settlements.exists():
            latest = settlements.order_by('-updated_at').first()
            days_ago = (today - latest.updated_at.date()).days if latest and latest.updated_at else None
            
            status = 'normal'
            if days_ago is not None:
                if days_ago > warning_days:
                    status = 'error'
                    module_warnings += 1
                elif days_ago > mild_warning_days:
                    status = 'warning'
            
            project_info['modules']['结算'] = {
                'last_update': latest.updated_at.date() if latest and latest.updated_at else None,
                'days_ago': days_ago,
                'status': status,
                'count': settlements.count(),
                'latest_code': latest.settlement_code if latest else None
            }
        else:
            project_info['modules']['结算'] = {
                'last_update': None,
                'days_ago': None,
                'status': 'no_data',
                'count': 0,
                'latest_code': None
            }
        
        # 确定整体状态
        project_info['warning_count'] = module_warnings
        if module_warnings > 0:
            project_info['overall_status'] = 'warning'
            warning_projects += 1
        else:
            normal_projects += 1
        
        project_status_list.append(project_info)
    
    # 统计信息
    summary = {
        'total_projects': projects.count(),
        'normal_projects': normal_projects,
        'warning_projects': warning_projects,
        'warning_days': warning_days,
        'mild_warning_days': mild_warning_days,
        'check_date': today
    }
    
    return {
        'summary': summary,
        'projects': project_status_list
    }


def get_module_update_overview(warning_days=40):
    """
    获取各模块整体更新概览
    简化版，用于总体统计
    
    Args:
        warning_days: 超过多少天未更新则预警，默认40天
    
    Returns:
        list: 各模块的更新统计信息列表
    """
    today = timezone.now().date()
    warning_date = today - timedelta(days=warning_days)
    
    modules_overview = []
    
    # 采购模块
    procurements = Procurement.objects.all()
    procurement_outdated = procurements.filter(updated_at__date__lt=warning_date).count()
    modules_overview.append({
        'module_name': '采购',
        'module_code': 'procurement',
        'total_count': procurements.count(),
        'outdated_count': procurement_outdated,
        'normal_count': procurements.count() - procurement_outdated,
        'update_rate': round((procurements.count() - procurement_outdated) / procurements.count() * 100, 1) if procurements.count() > 0 else 100
    })
    
    # 合同模块
    contracts = Contract.objects.all()
    contract_outdated = contracts.filter(updated_at__date__lt=warning_date).count()
    modules_overview.append({
        'module_name': '合同',
        'module_code': 'contract',
        'total_count': contracts.count(),
        'outdated_count': contract_outdated,
        'normal_count': contracts.count() - contract_outdated,
        'update_rate': round((contracts.count() - contract_outdated) / contracts.count() * 100, 1) if contracts.count() > 0 else 100
    })
    
    # 付款模块
    payments = Payment.objects.all()
    payment_outdated = payments.filter(created_at__date__lt=warning_date).count()
    modules_overview.append({
        'module_name': '付款',
        'module_code': 'payment',
        'total_count': payments.count(),
        'outdated_count': payment_outdated,
        'normal_count': payments.count() - payment_outdated,
        'update_rate': round((payments.count() - payment_outdated) / payments.count() * 100, 1) if payments.count() > 0 else 100
    })
    
    # 结算模块
    settlements = Settlement.objects.all()
    settlement_outdated = settlements.filter(updated_at__date__lt=warning_date).count()
    modules_overview.append({
        'module_name': '结算',
        'module_code': 'settlement',
        'total_count': settlements.count(),
        'outdated_count': settlement_outdated,
        'normal_count': settlements.count() - settlement_outdated,
        'update_rate': round((settlements.count() - settlement_outdated) / settlements.count() * 100, 1) if settlements.count() > 0 else 100
    })
    
    return modules_overview


def get_data_activity_analysis(days_range=30):
    """
    获取数据活跃度分析
    按照需求文档3.2.2设计：评估项目数据的更新活跃程度
    
    Args:
        days_range: 统计最近多少天的数据，默认30天
    
    Returns:
        dict: 数据活跃度统计信息
    """
    today = timezone.now().date()
    start_date = today - timedelta(days=days_range)
    
    # 统计各模块在时间段内的更新次数
    procurement_updates = Procurement.objects.filter(updated_at__date__gte=start_date).count()
    contract_updates = Contract.objects.filter(updated_at__date__gte=start_date).count()
    payment_updates = Payment.objects.filter(created_at__date__gte=start_date).count()
    settlement_updates = Settlement.objects.filter(updated_at__date__gte=start_date).count()
    
    total_updates = procurement_updates + contract_updates + payment_updates + settlement_updates
    
    # 识别沉默项目（不同时间段无更新）
    silent_30 = Project.objects.filter(updated_at__date__lt=today - timedelta(days=30), status='进行中').count()
    silent_60 = Project.objects.filter(updated_at__date__lt=today - timedelta(days=60), status='进行中').count()
    silent_90 = Project.objects.filter(updated_at__date__lt=today - timedelta(days=90), status='进行中').count()
    
    return {
        'days_range': days_range,
        'total_updates': total_updates,
        'daily_avg_updates': round(total_updates / days_range, 1) if days_range > 0 else 0,
        'module_updates': {
            '采购': procurement_updates,
            '合同': contract_updates,
            '付款': payment_updates,
            '结算': settlement_updates
        },
        'silent_projects': {
            '30天无更新': silent_30,
            '60天无更新': silent_60,
            '90天以上无更新': silent_90
        }
    }


def get_outdated_records(module_name, warning_days=40, limit=50):
    """
    获取指定模块的过期记录列表（保留原功能）
    
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
    
    # 付款模块使用created_at，其他使用updated_at
    if module_name == '付款':
        records = Model.objects.filter(created_at__date__lt=warning_date).order_by('created_at')[:limit]
    else:
        records = Model.objects.filter(updated_at__date__lt=warning_date).order_by('updated_at')[:limit]
    
    result = []
    for record in records:
        # 获取更新时间
        if module_name == '付款':
            update_time = record.created_at
        else:
            update_time = record.updated_at
            
        days_ago = (today - update_time.date()).days if update_time is not None else None
        
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
            'last_update': update_time.date() if update_time is not None else None,
            'days_ago': days_ago,
            'updated_by': record.updated_by if hasattr(record, 'updated_by') else ''
        })
    
    return result