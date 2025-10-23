"""
绩效排名服务模块
提供项目和个人在采购、归档等维度的绩效排名功能
"""
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, fields, Sum
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta
from procurement.models import Procurement
from contract.models import Contract
from settlement.models import Settlement
from project.models import Project


def get_procurement_ranking(rank_type='project', year=None):
    """
    获取采购绩效排名
    
    Args:
        rank_type: 排名类型 'project'(按项目) 或 'person'(按采购人)
        year: 指定年份，None表示全部
        
    Returns:
        list: 排名列表，包含排名、名称、完成数量、准时率、平均周期等信息
    """
    queryset = Procurement.objects.all()
    
    # 年份筛选
    if year:
        queryset = queryset.filter(result_publicity_release_date__year=year)
    
    # 按类型分组
    if rank_type == 'project':
        # 按项目排名
        rankings = queryset.values('project__project_name').annotate(
            total_count=Count('procurement_code'),
            completed_count=Count('procurement_code', filter=Q(archive_date__isnull=False)),
            on_time_count=Count('procurement_code', filter=Q(
                archive_date__isnull=False,
                archive_date__lte=F('result_publicity_release_date') + timedelta(days=90)
            )),
            avg_cycle_days=Avg(
                ExpressionWrapper(
                    F('archive_date') - F('result_publicity_release_date'),
                    output_field=fields.DurationField()
                ),
                filter=Q(archive_date__isnull=False)
            )
        ).order_by('-completed_count')
        
        # 计算准时率并格式化数据
        result = []
        for idx, item in enumerate(rankings, 1):
            completed = item['completed_count']
            on_time_rate = (item['on_time_count'] / completed * 100) if completed > 0 else 0
            avg_days = item['avg_cycle_days'].days if item['avg_cycle_days'] else 0
            
            result.append({
                'rank': idx,
                'name': item['project__project_name'] or '未分配项目',
                'total_count': item['total_count'],
                'completed_count': completed,
                'on_time_rate': round(on_time_rate, 1),
                'avg_cycle_days': avg_days,
                'medal': get_medal(idx)
            })
    else:
        # 按采购人排名
        rankings = queryset.values('procurement_officer').annotate(
            total_count=Count('procurement_code'),
            completed_count=Count('procurement_code', filter=Q(archive_date__isnull=False)),
            on_time_count=Count('procurement_code', filter=Q(
                archive_date__isnull=False,
                archive_date__lte=F('result_publicity_release_date') + timedelta(days=90)
            ))
        ).order_by('-completed_count')
        
        result = []
        for idx, item in enumerate(rankings, 1):
            completed = item['completed_count']
            on_time_rate = (item['on_time_count'] / completed * 100) if completed > 0 else 0
            
            result.append({
                'rank': idx,
                'name': item['procurement_officer'] or '未指定',
                'total_count': item['total_count'],
                'completed_count': completed,
                'on_time_rate': round(on_time_rate, 1),
                'medal': get_medal(idx)
            })
    
    return result


def get_archive_ranking(rank_type='project', year=None):
    """
    获取归档绩效排名
    
    Args:
        rank_type: 排名类型 'project'(按项目) 或 'person'(按归档人)
        year: 指定年份，None表示全部
        
    Returns:
        list: 排名列表，包含排名、名称、归档数量、归档率、平均归档时长等
    """
    # 统计采购归档
    procurement_qs = Procurement.objects.all()
    if year:
        procurement_qs = procurement_qs.filter(result_publicity_release_date__year=year)
    
    # 统计合同归档
    contract_qs = Contract.objects.all()
    if year:
        contract_qs = contract_qs.filter(signing_date__year=year)
    
    # 统计结算归档
    settlement_qs = Settlement.objects.all()
    if year:
        settlement_qs = settlement_qs.filter(completion_date__year=year)
    
    if rank_type == 'project':
        # 按项目统计归档情况
        result = []
        projects = Project.objects.all()
        
        for project in projects:
            # 采购归档统计
            proc_total = procurement_qs.filter(project=project).count()
            proc_archived = procurement_qs.filter(project=project, archive_date__isnull=False).count()
            
            # 合同归档统计
            contract_total = contract_qs.filter(project=project).count()
            contract_archived = contract_qs.filter(project=project, archive_date__isnull=False).count()
            
            # 结算归档统计（Settlement通过main_contract关联project）
            settlement_total = settlement_qs.filter(main_contract__project=project).count()
            # Settlement模型没有archive_date字段
            settlement_archived = 0
            
            total = proc_total + contract_total + settlement_total
            archived = proc_archived + contract_archived + settlement_archived
            
            if total > 0:
                archive_rate = archived / total * 100
                result.append({
                    'name': project.project_name,
                    'total_count': total,
                    'archived_count': archived,
                    'archive_rate': round(archive_rate, 1),
                    'procurement': {'total': proc_total, 'archived': proc_archived},
                    'contract': {'total': contract_total, 'archived': contract_archived},
                    'settlement': {'total': settlement_total, 'archived': settlement_archived}
                })
        
        # 按归档率排序
        result.sort(key=lambda x: x['archive_rate'], reverse=True)
        
        # 添加排名和奖牌
        for idx, item in enumerate(result, 1):
            item['rank'] = idx
            item['medal'] = get_medal(idx)
    else:
        # 按归档人排名（这里简化处理，实际可能需要更复杂的逻辑）
        result = []
        # TODO: 实现按归档人的排名逻辑
    
    return result


def get_contract_ranking(rank_type='project', year=None):
    """
    获取合同签订绩效排名
    
    Args:
        rank_type: 排名类型 'project'(按项目)
        year: 指定年份，None表示全部
        
    Returns:
        list: 排名列表，包含排名、名称、合同数量、合同金额等
    """
    queryset = Contract.objects.all()
    
    if year:
        queryset = queryset.filter(signing_date__year=year)
    
    if rank_type == 'project':
        rankings = queryset.values('project__project_name').annotate(
            total_count=Count('contract_code'),
            total_amount=Coalesce(Sum('contract_amount'), 0)
        ).order_by('-total_count')
        
        result = []
        for idx, item in enumerate(rankings, 1):
            result.append({
                'rank': idx,
                'name': item['project__project_name'] or '未分配项目',
                'total_count': item['total_count'],
                'total_amount': item['total_amount'],
                'medal': get_medal(idx)
            })
        
        return result
    
    return []


def get_settlement_ranking(rank_type='project'):
    """
    获取结算完成绩效排名
    
    Args:
        rank_type: 排名类型 'project'(按项目)
        
    Returns:
        list: 排名列表，包含排名、名称、结算数量、结算金额等
    """
    queryset = Settlement.objects.all()
    
    if rank_type == 'project':
        rankings = queryset.values('main_contract__project__project_name').annotate(
            total_count=Count('settlement_code'),
            total_amount=Coalesce(Sum('final_amount'), 0)
        ).order_by('-total_count')
        
        result = []
        for idx, item in enumerate(rankings, 1):
            result.append({
                'rank': idx,
                'name': item['main_contract__project__project_name'] or '未分配项目',
                'total_count': item['total_count'],
                'total_amount': item['total_amount'],
                'medal': get_medal(idx)
            })
        
        return result
    
    return []


def get_medal(rank):
    """
    根据排名返回奖牌图标
    
    Args:
        rank: 排名数字
        
    Returns:
        str: 奖牌图标或空字符串
    """
    medals = {
        1: '🥇',
        2: '🥈',
        3: '🥉'
    }
    return medals.get(rank, '')


def get_comprehensive_ranking(year=None):
    """
    获取综合绩效排名（综合考虑采购、归档、合同等多个维度）
    
    Args:
        year: 指定年份，None表示全部
        
    Returns:
        list: 综合排名列表
    """
    projects = Project.objects.all()
    result = []
    
    for project in projects:
        # 采购完成率
        proc_total = Procurement.objects.filter(project=project).count()
        proc_completed = Procurement.objects.filter(
            project=project, 
            archive_date__isnull=False
        ).count()
        proc_rate = (proc_completed / proc_total * 100) if proc_total > 0 else 0
        
        # 归档完成率
        items_total = (
            Procurement.objects.filter(project=project).count() +
            Contract.objects.filter(project=project).count() +
            Settlement.objects.filter(main_contract__project=project).count()
        )
        items_archived = (
            Procurement.objects.filter(project=project, archive_date__isnull=False).count() +
            Contract.objects.filter(project=project, archive_date__isnull=False).count()
            # Settlement模型没有archive_date字段，暂时不统计
        )
        archive_rate = (items_archived / items_total * 100) if items_total > 0 else 0
        
        # 合同签订数量
        contract_count = Contract.objects.filter(project=project).count()
        
        # 结算完成数量
        settlement_count = Settlement.objects.filter(main_contract__project=project).count()
        
        # 综合得分（可以根据实际需求调整权重）
        score = (
            proc_rate * 0.3 +
            archive_rate * 0.4 +
            contract_count * 0.15 +
            settlement_count * 0.15
        )
        
        if items_total > 0:  # 只统计有业务的项目
            result.append({
                'name': project.project_name,
                'procurement_rate': round(proc_rate, 1),
                'archive_rate': round(archive_rate, 1),
                'contract_count': contract_count,
                'settlement_count': settlement_count,
                'score': round(score, 2)
            })
    
    # 按综合得分排序
    result.sort(key=lambda x: x['score'], reverse=True)
    
    # 添加排名和奖牌
    for idx, item in enumerate(result, 1):
        item['rank'] = idx
        item['medal'] = get_medal(idx)
    
    return result