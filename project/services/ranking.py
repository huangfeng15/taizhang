"""
业务排名服务模块
根据指标体系需求文档第6章实现
提供项目和个人在采购、归档、合同、结算等维度的业务排名功能
"""
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, fields, Sum, Min, Max, Value, DecimalField
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta
from procurement.models import Procurement
from contract.models import Contract
from settlement.models import Settlement
from payment.models import Payment
from project.models import Project


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


# ==================== 6.3 采购模块业务排名 ====================

def get_procurement_on_time_ranking(rank_type='project', year=None):
    """
    6.3.1 采购计划准时完成率排名
    
    指标定义：
    准时完成率 = 按时或提前完成的采购数 ÷ 总采购数 × 100%
    按时标准：平台中标结果公示完成日期 ≤ 采购计划完成日期
    
    Args:
        rank_type: 'project' 或 'person'
        year: 指定年份
        
    Returns:
        list: 排名列表
    """
    # 优化查询 - 使用select_related和only
    queryset = Procurement.objects.select_related('project').only(
        'procurement_code', 'project_name', 'procurement_officer',
        'planned_completion_date', 'result_publicity_release_date',
        'project__project_code', 'project__project_name'
    )
    
    # 年份筛选 - 基于result_publicity_release_date
    if year:
        queryset = queryset.filter(result_publicity_release_date__year=year)
    
    # 只统计有计划完成日期和实际公示日期的记录
    queryset = queryset.filter(
        planned_completion_date__isnull=False,
        result_publicity_release_date__isnull=False
    )
    
    if rank_type == 'project':
        # 获取所有项目
        all_projects = Project.objects.all()
        project_data = {}
        
        # 统计有数据的项目
        rankings = queryset.values('project__project_code', 'project__project_name').annotate(
            total_count=Count('procurement_code'),
            # 按时完成：result_publicity_release_date <= planned_completion_date
            on_time_count=Count('procurement_code', filter=Q(
                result_publicity_release_date__lte=F('planned_completion_date')
            )),
            # 计算平均提前天数（负数表示延期）
            avg_advance_days=Avg(
                ExpressionWrapper(
                    F('planned_completion_date') - F('result_publicity_release_date'),
                    output_field=fields.DurationField()
                )
            )
        ).order_by('-on_time_count', '-total_count')
        
        # 构建项目数据字典
        for item in rankings:
            project_data[item['project__project_code']] = item
        
        result = []
        rank_idx = 1
        
        # 遍历所有项目，确保包含没有数据的项目
        for project in all_projects:
            code = project.project_code
            item = project_data.get(code, {
                'total_count': 0,
                'on_time_count': 0,
                'avg_advance_days': None
            })
            
            total = item['total_count']
            on_time = item['on_time_count']
            on_time_rate = (on_time / total * 100) if total > 0 else 0
            
            # 计算平均提前天数
            avg_days = item['avg_advance_days']
            if avg_days:
                advance_days = avg_days.days
                if advance_days > 0:
                    advance_text = f"提前{advance_days}天"
                elif advance_days < 0:
                    advance_text = f"延期{abs(advance_days)}天"
                else:
                    advance_text = "按时"
            else:
                advance_text = "-"
            
            result.append({
                'rank': rank_idx,
                'name': project.project_name or '未分配项目',
                'project_code': project.project_code,
                'total_count': total,
                'on_time_count': on_time,
                'on_time_rate': round(on_time_rate, 1),
                'advance_text': advance_text,
                'medal': get_medal(rank_idx)
            })
            rank_idx += 1
        
        # 按准时率重新排序
        result.sort(key=lambda x: (-x['on_time_rate'], -x['total_count']))
        
        # 重新分配排名
        for idx, item in enumerate(result, 1):
            item['rank'] = idx
            item['medal'] = get_medal(idx)
    else:
        # 按采购经办人排名
        rankings = queryset.values('procurement_officer').annotate(
            total_count=Count('procurement_code'),
            on_time_count=Count('procurement_code', filter=Q(
                result_publicity_release_date__lte=F('planned_completion_date')
            )),
            avg_advance_days=Avg(
                ExpressionWrapper(
                    F('planned_completion_date') - F('result_publicity_release_date'),
                    output_field=fields.DurationField()
                )
            )
        ).order_by('-on_time_count', '-total_count')
        
        result = []
        for idx, item in enumerate(rankings, 1):
            total = item['total_count']
            on_time = item['on_time_count']
            on_time_rate = (on_time / total * 100) if total > 0 else 0
            
            avg_days = item['avg_advance_days']
            if avg_days:
                advance_days = avg_days.days
                if advance_days > 0:
                    advance_text = f"提前{advance_days}天"
                elif advance_days < 0:
                    advance_text = f"延期{abs(advance_days)}天"
                else:
                    advance_text = "按时"
            else:
                advance_text = "-"
            
            result.append({
                'rank': idx,
                'name': item['procurement_officer'] or '未指定',
                'total_count': total,
                'on_time_count': on_time,
                'on_time_rate': round(on_time_rate, 1),
                'advance_text': advance_text,
                'medal': get_medal(idx)
            })
    
    return result


def get_procurement_cycle_ranking(rank_type='project', year=None, method=None):
    """
    6.3.2 采购周期效率排名
    
    指标定义：
    采购周期 = 平台中标结果公示完成日期 - 采购需求书审批完成日期
    
    Args:
        rank_type: 'project' 或 'person'
        year: 指定年份
        method: 采购方式筛选
        
    Returns:
        list: 排名列表（按平均周期升序，周期越短排名越高）
    """
    # 优化查询 - 使用select_related和only
    queryset = Procurement.objects.select_related('project').only(
        'procurement_code', 'project_name', 'procurement_officer',
        'procurement_method', 'requirement_approval_date',
        'result_publicity_release_date',
        'project__project_code', 'project__project_name'
    )
    
    if year:
        queryset = queryset.filter(result_publicity_release_date__year=year)
    
    if method:
        queryset = queryset.filter(procurement_method=method)
    
    # 只统计有需求审批日期和公示日期的记录
    queryset = queryset.filter(
        requirement_approval_date__isnull=False,
        result_publicity_release_date__isnull=False
    )
    
    if rank_type == 'project':
        # 获取所有项目
        all_projects = Project.objects.all()
        project_data = {}
        
        # 统计有数据的项目
        rankings = queryset.values('project__project_code', 'project__project_name').annotate(
            total_count=Count('procurement_code'),
            avg_cycle=Avg(
                ExpressionWrapper(
                    F('result_publicity_release_date') - F('requirement_approval_date'),
                    output_field=fields.DurationField()
                )
            )
        ).order_by('avg_cycle')  # 升序：周期越短排名越高
        
        # 构建项目数据字典
        for item in rankings:
            project_data[item['project__project_code']] = item
        
        result = []
        rank_idx = 1
        
        # 遍历所有项目，确保包含没有数据的项目
        for project in all_projects:
            code = project.project_code
            item = project_data.get(code, {
                'total_count': 0,
                'avg_cycle': None
            })
            
            avg_days = item['avg_cycle'].days if item['avg_cycle'] else 0
            
            result.append({
                'rank': rank_idx,
                'name': project.project_name or '未分配项目',
                'project_code': project.project_code,
                'total_count': item['total_count'],
                'avg_cycle_days': avg_days,
                'medal': get_medal(rank_idx)
            })
            rank_idx += 1
        
        # 按平均周期排序（没有数据的项目排在后面）
        result.sort(key=lambda x: (x['avg_cycle_days'] == 0, x['avg_cycle_days']))
        
        # 重新分配排名
        for idx, item in enumerate(result, 1):
            item['rank'] = idx
            item['medal'] = get_medal(idx)
    else:
        rankings = queryset.values('procurement_officer').annotate(
            total_count=Count('procurement_code'),
            avg_cycle=Avg(
                ExpressionWrapper(
                    F('result_publicity_release_date') - F('requirement_approval_date'),
                    output_field=fields.DurationField()
                )
            )
        ).order_by('avg_cycle')
        
        result = []
        for idx, item in enumerate(rankings, 1):
            avg_days = item['avg_cycle'].days if item['avg_cycle'] else 0
            
            result.append({
                'rank': idx,
                'name': item['procurement_officer'] or '未指定',
                'total_count': item['total_count'],
                'avg_cycle_days': avg_days,
                'medal': get_medal(idx)
            })
    
    return result


def get_procurement_quantity_ranking(rank_type='project', year=None):
    """
    6.3.3 采购完成数量排名
    
    指标定义：
    月均完成数量 = 统计周期内完成的采购总数 ÷ 月数
    完成标准：已完成平台中标结果公示的采购项目
    
    Args:
        rank_type: 'project' 或 'person'
        year: 指定年份
        
    Returns:
        list: 排名列表（按月均完成数量降序）
    """
    # 优化查询 - 使用select_related和only
    queryset = Procurement.objects.select_related('project').only(
        'procurement_code', 'project_name', 'procurement_officer',
        'result_publicity_release_date', 'winning_amount',
        'project__project_code', 'project__project_name'
    ).filter(result_publicity_release_date__isnull=False)
    
    if year:
        queryset = queryset.filter(result_publicity_release_date__year=year)
        months = 12
    else:
        # 计算实际跨度月数
        dates = queryset.aggregate(
            min_date=Min('result_publicity_release_date'),
            max_date=Max('result_publicity_release_date')
        )
        if dates['min_date'] and dates['max_date']:
            delta = dates['max_date'] - dates['min_date']
            months = max(1, delta.days / 30)
        else:
            months = 1
    
    if rank_type == 'project':
        # 获取所有项目
        all_projects = Project.objects.all()
        project_data = {}
        
        # 统计有数据的项目
        rankings = queryset.values('project__project_code', 'project__project_name').annotate(
            total_count=Count('procurement_code'),
            total_amount=Sum('winning_amount')
        ).order_by('-total_count')
        
        # 构建项目数据字典
        for item in rankings:
            project_data[item['project__project_code']] = item
        
        result = []
        rank_idx = 1
        
        # 遍历所有项目，确保包含没有数据的项目
        for project in all_projects:
            code = project.project_code
            item = project_data.get(code, {
                'total_count': 0,
                'total_amount': 0
            })
            
            total = item['total_count']
            monthly_avg = total / months
            
            result.append({
                'rank': rank_idx,
                'name': project.project_name or '未分配项目',
                'project_code': project.project_code,
                'total_count': total,
                'monthly_avg': round(monthly_avg, 2),
                'total_amount': item['total_amount'] or 0,
                'medal': get_medal(rank_idx)
            })
            rank_idx += 1
        
        # 按总数量重新排序
        result.sort(key=lambda x: (-x['total_count'], -x['total_amount']))
        
        # 重新分配排名
        for idx, item in enumerate(result, 1):
            item['rank'] = idx
            item['medal'] = get_medal(idx)
    else:
        rankings = queryset.values('procurement_officer').annotate(
            total_count=Count('procurement_code'),
            total_amount=Sum('winning_amount')
        ).order_by('-total_count')
        
        result = []
        for idx, item in enumerate(rankings, 1):
            total = item['total_count']
            monthly_avg = total / months
            
            result.append({
                'rank': idx,
                'name': item['procurement_officer'] or '未指定',
                'total_count': total,
                'monthly_avg': round(monthly_avg, 2),
                'total_amount': item['total_amount'] or 0,
                'medal': get_medal(idx)
            })
    
    return result


# ==================== 6.4 归档模块业务排名 ====================

def get_archive_timeliness_ranking(rank_type='project', year=None):
    """
    6.4.1 归档及时率排名
    
    指标定义：
    归档及时率 = 及时归档数 ÷ 应归档总数 × 100%
    
    及时标准：
    - 采购资料：归档日期 ≤ 平台公示完成日期 + 40天
    - 合同资料：归档日期 ≤ 合同签订日期 + 30天
    
    Args:
        rank_type: 'project' 或 'person'
        year: 指定年份
        
    Returns:
        list: 排名列表
    """
    if rank_type == 'project':
        result = []
        projects = Project.objects.all()
        
        for project in projects:
            # 采购归档统计
            proc_qs = Procurement.objects.filter(project=project, result_publicity_release_date__isnull=False)
            if year:
                proc_qs = proc_qs.filter(result_publicity_release_date__year=year)
            
            proc_total = proc_qs.count()
            proc_timely = proc_qs.filter(
                archive_date__isnull=False,
                archive_date__lte=F('result_publicity_release_date') + timedelta(days=40)
            ).count()
            
            # 合同归档统计
            contract_qs = Contract.objects.filter(project=project, signing_date__isnull=False)
            if year:
                contract_qs = contract_qs.filter(signing_date__year=year)
            
            contract_total = contract_qs.count()
            contract_timely = contract_qs.filter(
                archive_date__isnull=False,
                archive_date__lte=F('signing_date') + timedelta(days=30)
            ).count()
            
            total = proc_total + contract_total
            timely = proc_timely + contract_timely
            
            if total > 0:
                timely_rate = (timely / total * 100)
                
                # 计算平均归档周期
                proc_avg = proc_qs.filter(archive_date__isnull=False).aggregate(
                    avg=Avg(ExpressionWrapper(
                        F('archive_date') - F('result_publicity_release_date'),
                        output_field=fields.DurationField()
                    ))
                )['avg']
                
                contract_avg = contract_qs.filter(archive_date__isnull=False).aggregate(
                    avg=Avg(ExpressionWrapper(
                        F('archive_date') - F('signing_date'),
                        output_field=fields.DurationField()
                    ))
                )['avg']
                
                avg_cycle_days = 0
                if proc_avg and contract_avg:
                    avg_cycle_days = (proc_avg.days + contract_avg.days) / 2
                elif proc_avg:
                    avg_cycle_days = proc_avg.days
                elif contract_avg:
                    avg_cycle_days = contract_avg.days
                
                result.append({
                    'name': project.project_name,
                    'project_code': project.project_code,
                    'total_count': total,
                    'timely_count': timely,
                    'timely_rate': round(timely_rate, 1),
                    'avg_cycle_days': int(avg_cycle_days),
                    'procurement': {'total': proc_total, 'timely': proc_timely},
                    'contract': {'total': contract_total, 'timely': contract_timely}
                })
        
        # 按及时率排序
        result.sort(key=lambda x: x['timely_rate'], reverse=True)
        
        # 添加排名和奖牌
        for idx, item in enumerate(result, 1):
            item['rank'] = idx
            item['medal'] = get_medal(idx)
        
        return result
    else:
        # 按个人排名（采购经办人和合同经办人）
        result = []
        # TODO: 实现按个人的归档及时率排名
        return result


def get_archive_speed_ranking(rank_type='project', year=None):
    """
    6.4.2 归档速度排名
    
    指标定义：
    采购归档周期 = 归档日期 - 平台公示完成日期
    合同归档周期 = 归档日期 - 合同签订日期
    平均归档周期 = 所有归档周期的平均值
    
    Args:
        rank_type: 'project' 或 'person'
        year: 指定年份
        
    Returns:
        list: 排名列表（按平均归档周期升序，周期越短排名越高）
    """
    if rank_type == 'project':
        result = []
        projects = Project.objects.all()
        
        for project in projects:
            # 采购归档
            proc_qs = Procurement.objects.filter(
                project=project,
                archive_date__isnull=False,
                result_publicity_release_date__isnull=False
            )
            if year:
                proc_qs = proc_qs.filter(result_publicity_release_date__year=year)
            
            # 合同归档
            contract_qs = Contract.objects.filter(
                project=project,
                archive_date__isnull=False,
                signing_date__isnull=False
            )
            if year:
                contract_qs = contract_qs.filter(signing_date__year=year)
            
            total_count = proc_qs.count() + contract_qs.count()
            
            # 计算平均归档周期（即使没有数据也要包含）
            avg_cycle_days = 0
            if total_count > 0:
                proc_avg = proc_qs.aggregate(
                    avg=Avg(ExpressionWrapper(
                        F('archive_date') - F('result_publicity_release_date'),
                        output_field=fields.DurationField()
                    ))
                )['avg']
                
                contract_avg = contract_qs.aggregate(
                    avg=Avg(ExpressionWrapper(
                        F('archive_date') - F('signing_date'),
                        output_field=fields.DurationField()
                    ))
                )['avg']
                
                if proc_avg and contract_avg:
                    avg_cycle_days = (proc_avg.days + contract_avg.days) / 2
                elif proc_avg:
                    avg_cycle_days = proc_avg.days
                elif contract_avg:
                    avg_cycle_days = contract_avg.days
            
            # 包含所有项目，包括没有归档数据的项目
            result.append({
                'name': project.project_name,
                'project_code': project.project_code,
                'total_count': total_count,
                'avg_cycle_days': int(avg_cycle_days)
            })
        
        # 按平均周期排序（没有数据的项目排在后面）
        result.sort(key=lambda x: (x['avg_cycle_days'] == 0, x['avg_cycle_days']))
        
        # 添加排名和奖牌
        for idx, item in enumerate(result, 1):
            item['rank'] = idx
            item['medal'] = get_medal(idx)
        
        return result
    else:
        result = []
        # TODO: 实现按个人的归档速度排名
        return result


# ==================== 综合排名函数（兼容旧视图）====================

def get_procurement_ranking(rank_type='project', year=None):
    """综合采购排名 - 优先采用计划准时完成率排名"""
    return get_procurement_on_time_ranking(rank_type, year)


def get_archive_ranking(rank_type='project', year=None):
    """综合归档排名 - 使用归档及时率排名"""
    return get_archive_timeliness_ranking(rank_type, year)


def get_contract_ranking(rank_type='project', year=None):
    """
    合同签订业务排名
    
    Args:
        rank_type: 排名类型 'project'(按项目)
        year: 指定年份
        
    Returns:
        list: 排名列表，包含排名、名称、合同数量、合同金额等
    """
    # 优化查询 - 使用select_related和only
    queryset = Contract.objects.select_related('project').only(
        'contract_code', 'contract_name', 'file_positioning',
        'contract_amount', 'signing_date',
        'project__project_code', 'project__project_name'
    )
    
    if year:
        queryset = queryset.filter(signing_date__year=year)
    
    if rank_type == 'project':
        # 获取所有项目
        all_projects = Project.objects.all()
        project_data = {}
        
        # 统计有数据的项目
        rankings = queryset.values('project__project_code', 'project__project_name').annotate(
            total_count=Count('contract_code'),
            total_amount=Coalesce(Sum('contract_amount'), Value(0), output_field=DecimalField())
        ).order_by('-total_count')
        
        # 构建项目数据字典
        for item in rankings:
            project_data[item['project__project_code']] = item
        
        result = []
        rank_idx = 1
        
        # 遍历所有项目，确保包含没有数据的项目
        for project in all_projects:
            code = project.project_code
            item = project_data.get(code, {
                'total_count': 0,
                'total_amount': 0
            })
            
            result.append({
                'rank': rank_idx,
                'name': project.project_name or '未分配项目',
                'project_code': project.project_code,
                'total_count': item['total_count'],
                'total_amount': item['total_amount'],
                'medal': get_medal(rank_idx)
            })
            rank_idx += 1
        
        # 按总数量重新排序
        result.sort(key=lambda x: (-x['total_count'], -x['total_amount']))
        
        # 重新分配排名
        for idx, item in enumerate(result, 1):
            item['rank'] = idx
            item['medal'] = get_medal(idx)
        
        return result
    
    return []
def get_settlement_ranking(rank_type='project'):
    """
    结算完成业务排名
    
    Args:
        rank_type: 排名类型 'project'(按项目)
        
    Returns:
        list: 排名列表，包含排名、名称、结算数量、结算金额等
    """
    queryset = Settlement.objects.all()
    
    if rank_type == 'project':
        # 获取所有项目
        all_projects = Project.objects.all()
        project_data = {}
        
        # 统计有数据的项目
        rankings = queryset.values('main_contract__project__project_code', 'main_contract__project__project_name').annotate(
            total_count=Count('settlement_code'),
            total_amount=Coalesce(Sum('final_amount'), Value(0), output_field=DecimalField())
        ).order_by('-total_count')
        
        # 构建项目数据字典
        for item in rankings:
            project_data[item['main_contract__project__project_code']] = item
        
        result = []
        rank_idx = 1
        
        # 遍历所有项目，确保包含没有数据的项目
        for project in all_projects:
            code = project.project_code
            item = project_data.get(code, {
                'total_count': 0,
                'total_amount': 0
            })
            
            result.append({
                'rank': rank_idx,
                'name': project.project_name or '未分配项目',
                'project_code': project.project_code,
                'total_count': item['total_count'],
                'total_amount': item['total_amount'],
                'medal': get_medal(rank_idx)
            })
            rank_idx += 1
        
        # 按总数量重新排序
        result.sort(key=lambda x: (-x['total_count'], -x['total_amount']))
        
        # 重新分配排名
        for idx, item in enumerate(result, 1):
            item['rank'] = idx
            item['medal'] = get_medal(idx)
        
        return result
    
    return []


def get_comprehensive_ranking(year=None):
    """
    6.6 综合业务排名
    
    综合绩效得分 = 采购准时完成率 × 30%
                  + 采购周期效率得分 × 20%
                  + 归档及时率 × 30%
                  + 数据齐全率 × 20%
    
    Args:
        year: 指定年份
        
    Returns:
        list: 综合排名列表
    """
    projects = Project.objects.all()
    result = []
    
    # 获取各项排名数据
    procurement_on_time_data = {item['project_code']: item for item in get_procurement_on_time_ranking('project', year)}
    procurement_cycle_data = {item['project_code']: item for item in get_procurement_cycle_ranking('project', year)}
    archive_data = {item['project_code']: item for item in get_archive_timeliness_ranking('project', year)}
    
    for project in projects:
        code = project.project_code
        
        # 采购准时完成率得分（0-100）
        proc_on_time_score = procurement_on_time_data.get(code, {}).get('on_time_rate', 0)
        
        # 采购周期效率得分（需要计算相对得分）
        proc_cycle_item = procurement_cycle_data.get(code, {})
        proc_cycle_days = proc_cycle_item.get('avg_cycle_days', 0)
        # 假设基准周期为45天，周期越短得分越高
        if proc_cycle_days > 0:
            proc_cycle_score = max(0, (1 - proc_cycle_days / 45) * 100)
        else:
            proc_cycle_score = 0
        
        # 归档及时率得分（0-100）
        archive_score = archive_data.get(code, {}).get('timely_rate', 0)
        
        # 数据齐全率得分（暂时使用100，待实现数据齐全性检查）
        data_quality_score = 100
        
        # 综合得分计算
        comprehensive_score = (
            proc_on_time_score * 0.3 +
            proc_cycle_score * 0.2 +
            archive_score * 0.3 +
            data_quality_score * 0.2
        )
        
        # 统计所有项目，包括没有业务数据的项目
        result.append({
            'name': project.project_name,
            'project_code': project.project_code,
            'comprehensive_score': round(comprehensive_score, 2),
            'procurement_score': round(proc_on_time_score, 1),
            'procurement_cycle_score': round(proc_cycle_score, 1),
            'archive_score': round(archive_score, 1),
            'data_quality_score': round(data_quality_score, 1)
        })
    
    # 按综合得分排序
    result.sort(key=lambda x: x['comprehensive_score'], reverse=True)
    
    # 添加排名和奖牌
    for idx, item in enumerate(result, 1):
        item['rank'] = idx
        item['medal'] = get_medal(idx)
    
    return result
        
    