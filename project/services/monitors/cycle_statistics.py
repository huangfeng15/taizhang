"""
工作周期统计服务
负责计算项目和个人的工作周期统计数据（采购周期 + 合同周期）
"""
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q, F, ExpressionWrapper, fields, Case, When, Value, IntegerField
from django.db.models.functions import ExtractYear, ExtractMonth
from procurement.models import Procurement
from contract.models import Contract
from project.enums import FilePositioning, ContractSource
from .config import CYCLE_RULES


class CycleStatisticsService:
    """工作周期统计服务类（遵循SRP原则）"""

    def __init__(self):
        self.procurement_rules = CYCLE_RULES['procurement']
        self.contract_rules = CYCLE_RULES['contract']

    def get_procurement_deadline(self, procurement_method):
        """根据采购方式获取规定周期天数"""
        return self.procurement_rules['deadline_map'].get(
            procurement_method,
            self.procurement_rules['default_deadline']
        )

    def get_projects_cycle_overview(self, year_filter=None, project_filter=None, procurement_methods=None, group_by=None):
        """
        获取项目维度的周期概览
        
        Args:
            year_filter: str - 年度筛选（'all' 表示全部）
            project_filter: str or None - 项目编码筛选
            procurement_methods: list[str] or None - 采购方式筛选
            group_by: Optional[str] - 若为 'procurement_method'，返回按方式分组统计
        
        Returns:
            dict: {
                'summary': {...},
                'projects': [...],
                'by_method': [...] (可选)
            }
        """
        from project.models import Project
        
        projects_qs = Project.objects.all()
        if project_filter:
            projects_qs = projects_qs.filter(project_code=project_filter)
        
        projects_data = []
        total_procurement_count = 0
        total_procurement_on_time = 0
        total_contract_count = 0
        total_contract_on_time = 0
        
        for project in projects_qs:
            procurement_stats = self._calculate_procurement_cycle_statistics(
                project_code=project.project_code,
                year_filter=year_filter,
                global_project=None,
                procurement_methods=procurement_methods
            )
            contract_stats = self._calculate_contract_cycle_statistics(
                project_code=project.project_code,
                year_filter=year_filter
            )
            
            total_items = procurement_stats['count'] + contract_stats['count']
            on_time_items = (
                int(procurement_stats['count'] * procurement_stats['on_time_rate'] / 100) +
                int(contract_stats['count'] * contract_stats['on_time_rate'] / 100)
            )
            overall_on_time_rate = round(on_time_items / total_items * 100, 1) if total_items > 0 else 0
            
            projects_data.append({
                'project_code': project.project_code,
                'project_name': project.project_name,
                'procurement_count': procurement_stats['count'],
                'procurement_avg_cycle': procurement_stats['avg_cycle'],
                'procurement_on_time_rate': procurement_stats['on_time_rate'],
                'contract_count': contract_stats['count'],
                'contract_avg_cycle': contract_stats['avg_cycle'],
                'contract_on_time_rate': contract_stats['on_time_rate'],
                'overall_on_time_rate': overall_on_time_rate
            })
            
            total_procurement_count += procurement_stats['count']
            total_procurement_on_time += int(procurement_stats['count'] * procurement_stats['on_time_rate'] / 100)
            total_contract_count += contract_stats['count']
            total_contract_on_time += int(contract_stats['count'] * contract_stats['on_time_rate'] / 100)
        
        projects_data.sort(key=lambda x: x['overall_on_time_rate'], reverse=True)
        
        total_all = total_procurement_count + total_contract_count
        on_time_all = total_procurement_on_time + total_contract_on_time
        overall_rate = round(on_time_all / total_all * 100, 1) if total_all > 0 else 0
        
        summary = {
            'project_count': len(projects_data),
            'procurement_total': total_procurement_count,
            'contract_total': total_contract_count,
            'overall_on_time_rate': overall_rate
        }
        
        result = {
            'summary': summary,
            'projects': projects_data
        }
        
        if group_by == 'procurement_method':
            result['by_method'] = self.get_procurement_by_method_breakdown(
                year_filter=year_filter,
                project_filter=project_filter,
                methods=procurement_methods
            )
        
        return result

    def get_persons_cycle_overview(self, year_filter=None, project_filter=None, procurement_methods=None, group_by=None):
        """
        获取人员维度的周期概览
        
        Args:
            year_filter: str - 年度筛选（'all' 表示全部）
            project_filter: str or None - 项目筛选，影响经办人范围
            procurement_methods: list[str] or None - 采购方式筛选
            group_by: Optional[str] - 若为 'procurement_method'，返回按方式分组统计
        
        Returns:
            dict: {
                'summary': {...},
                'persons': [...],
                'by_method': [...] (可选)
            }
        """
        # 获取所有相关经办人
        person_names = set()
        
        procurement_qs = Procurement.objects.filter(
            procurement_officer__isnull=False,
            requirement_approval_date__isnull=False,
            result_publicity_release_date__isnull=False
        )
        if year_filter and year_filter != 'all':
            procurement_qs = procurement_qs.filter(requirement_approval_date__year=int(year_filter))
        if project_filter:
            procurement_qs = procurement_qs.filter(project_id=project_filter)
        person_names.update(procurement_qs.values_list('procurement_officer', flat=True).distinct())
        
        contract_qs = Contract.objects.filter(
            contract_officer__isnull=False,
            contract_source=ContractSource.PROCUREMENT.value,
            procurement__result_publicity_release_date__isnull=False,
            signing_date__isnull=False
        )
        if year_filter and year_filter != 'all':
            contract_qs = contract_qs.filter(signing_date__year=int(year_filter))
        if project_filter:
            contract_qs = contract_qs.filter(project_id=project_filter)
        person_names.update(contract_qs.values_list('contract_officer', flat=True).distinct())
        
        persons_data = []
        total_procurement_count = 0
        total_procurement_on_time = 0
        total_contract_count = 0
        total_contract_on_time = 0
        
        for person_name in person_names:
            p_stats = self._calculate_procurement_cycle_statistics(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter,
                procurement_methods=procurement_methods
            )
            c_stats = self._calculate_contract_cycle_statistics(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter
            )
            
            project_count = self._get_person_project_count(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter
            )
            
            total_items = p_stats['count'] + c_stats['count']
            on_time_items = (
                int(p_stats['count'] * p_stats['on_time_rate'] / 100) +
                int(c_stats['count'] * c_stats['on_time_rate'] / 100)
            )
            overall_on_time_rate = round(on_time_items / total_items * 100, 1) if total_items > 0 else 0
            
            persons_data.append({
                'person_name': person_name,
                'procurement_count': p_stats['count'],
                'procurement_avg_cycle': p_stats['avg_cycle'],
                'procurement_on_time_rate': p_stats['on_time_rate'],
                'contract_count': c_stats['count'],
                'contract_avg_cycle': c_stats['avg_cycle'],
                'contract_on_time_rate': c_stats['on_time_rate'],
                'overall_on_time_rate': overall_on_time_rate,
                'project_count': project_count
            })
            
            total_procurement_count += p_stats['count']
            total_procurement_on_time += int(p_stats['count'] * p_stats['on_time_rate'] / 100)
            total_contract_count += c_stats['count']
            total_contract_on_time += int(c_stats['count'] * c_stats['on_time_rate'] / 100)
        
        persons_data.sort(key=lambda x: x['overall_on_time_rate'], reverse=True)
        
        total_all = total_procurement_count + total_contract_count
        on_time_all = total_procurement_on_time + total_contract_on_time
        overall_rate = round(on_time_all / total_all * 100, 1) if total_all > 0 else 0
        
        summary = {
            'person_count': len(persons_data),
            'procurement_total': total_procurement_count,
            'contract_total': total_contract_count,
            'overall_on_time_rate': overall_rate
        }
        
        result = {
            'summary': summary,
            'persons': persons_data
        }
        if group_by == 'procurement_method':
            result['by_method'] = self.get_procurement_by_method_breakdown(
                year_filter=year_filter,
                project_filter=project_filter,
                methods=procurement_methods
            )
        return result

    def get_project_cycle_detail(self, project_code, year_filter=None, procurement_methods=None, group_by=None):
        """
        获取单个项目的周期详情
        
        Returns:
            dict: {
                'procurement_trend': [...],
                'contract_trend': [...],
                'overdue_records': {...},
                'ongoing_records': {...},
                'by_method': [...] (可选)
            }
        """
        procurement_trend = self._calculate_cycle_trend(
            model=Procurement,
            project_code=project_code,
            year_filter=year_filter,
            cycle_type='procurement'
        )
        
        contract_trend = self._calculate_cycle_trend(
            model=Contract,
            project_code=project_code,
            year_filter=year_filter,
            cycle_type='contract'
        )
        
        p_stats = self._calculate_procurement_cycle_statistics(
            project_code=project_code,
            year_filter=year_filter,
            procurement_methods=procurement_methods
        )
        c_stats = self._calculate_contract_cycle_statistics(
            project_code=project_code,
            year_filter=year_filter
        )
        
        summary = {
            'procurement': {
                'count': p_stats['count'],
                'avg_cycle': p_stats['avg_cycle'],
                'on_time_rate': p_stats['on_time_rate'],
            },
            'contract': {
                'count': c_stats['count'],
                'avg_cycle': c_stats['avg_cycle'],
                'on_time_rate': c_stats['on_time_rate'],
            },
        }
        
        overdue_records = self._get_overdue_records(
            project_code=project_code,
            year_filter=year_filter
        )
        ongoing_records = self._get_ongoing_records(
            project_code=project_code,
            year_filter=year_filter
        )
        
        result = {
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'summary': summary,
            'overdue_records': overdue_records,
            'ongoing_records': ongoing_records
        }
        if group_by == 'procurement_method':
            result['by_method'] = self.get_procurement_by_method_breakdown(
                year_filter=year_filter,
                project_filter=project_code,
                methods=procurement_methods
            )
        return result

    def get_person_cycle_detail(self, person_name, year_filter=None, project_filter=None, procurement_methods=None, group_by=None):
        """获取单个经办人的周期详情"""
        procurement_trend = self._calculate_cycle_trend(
            model=Procurement,
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
            cycle_type='procurement'
        )
        
        contract_trend = self._calculate_cycle_trend(
            model=Contract,
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
            cycle_type='contract'
        )
        
        p_stats = self._calculate_procurement_cycle_statistics(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
            procurement_methods=procurement_methods
        )
        c_stats = self._calculate_contract_cycle_statistics(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter
        )
        
        summary = {
            'procurement': {
                'count': p_stats['count'],
                'avg_cycle': p_stats['avg_cycle'],
                'on_time_rate': p_stats['on_time_rate'],
            },
            'contract': {
                'count': c_stats['count'],
                'avg_cycle': c_stats['avg_cycle'],
                'on_time_rate': c_stats['on_time_rate'],
            },
        }
        
        overdue_records = self._get_overdue_records(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter
        )
        ongoing_records = self._get_ongoing_records(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter
        )
        
        result = {
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'summary': summary,
            'overdue_records': overdue_records,
            'ongoing_records': ongoing_records
        }
        if group_by == 'procurement_method':
            result['by_method'] = self.get_procurement_by_method_breakdown(
                year_filter=year_filter,
                project_filter=project_filter,
                methods=procurement_methods
            )
        return result

    def _calculate_procurement_cycle_statistics(self, project_code=None, person_name=None,
                                                year_filter=None, global_project=None,
                                                procurement_methods=None):
        """采购周期统计（可按采购方式过滤）"""
        queryset = Procurement.objects.filter(
            requirement_approval_date__isnull=False,
            result_publicity_release_date__isnull=False  # 只统计已完成的
        ).select_related('project')
        
        # 应用筛选
        if project_code:
            queryset = queryset.filter(project_id=project_code)
        if person_name:
            queryset = queryset.filter(procurement_officer=person_name)
        if global_project:
            queryset = queryset.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(requirement_approval_date__year=int(year_filter))
        if procurement_methods:
            methods = [m for m in procurement_methods if m and m != '未标注']
            q_obj = Q()
            if methods:
                q_obj |= Q(procurement_method__in=methods)
            if '未标注' in procurement_methods:
                q_obj |= Q(procurement_method__isnull=True) | Q(procurement_method__exact='')
            queryset = queryset.filter(q_obj)
        
        # 计算时长
        queryset = queryset.annotate(
            cycle_days_duration=ExpressionWrapper(
                F('result_publicity_release_date') - F('requirement_approval_date'),
                output_field=fields.DurationField()
            )
        )
        
        # 统计汇总
        total_count = queryset.count()
        if total_count == 0:
            return {'avg_cycle': 0, 'on_time_rate': 0, 'count': 0}
        
        # 平均周期（按天）
        avg_cycle_timedelta = queryset.aggregate(avg=Avg('cycle_days_duration'))['avg']
        avg_cycle = round(avg_cycle_timedelta.days, 1) if avg_cycle_timedelta else 0
        
        # 达标率：根据各记录的采购方式对应阈值判断
        on_time_count = 0
        for item in queryset:
            cycle_days = (item.result_publicity_release_date - item.requirement_approval_date).days
            deadline = self.get_procurement_deadline(item.procurement_method)
            if cycle_days <= deadline:
                on_time_count += 1
        
        on_time_rate = round(on_time_count / total_count * 100, 1) if total_count > 0 else 0
        
        return {
            'avg_cycle': avg_cycle,
            'on_time_rate': on_time_rate,
            'count': total_count
        }

    def _calculate_contract_cycle_statistics(self, project_code=None, person_name=None,
                                            year_filter=None, global_project=None):
        """计算采购合同周期统计"""
        queryset = Contract.objects.filter(
            contract_source=ContractSource.PROCUREMENT.value,  # 仅采购合同
            procurement__isnull=False,  # 必须关联采购
            procurement__result_publicity_release_date__isnull=False,  # 采购必须有公示日期
            signing_date__isnull=False  # 必须已签订
        ).select_related('project', 'procurement')
        
        # 应用筛选
        if project_code:
            queryset = queryset.filter(project_id=project_code)
        if person_name:
            queryset = queryset.filter(contract_officer=person_name)
        if global_project:
            queryset = queryset.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(signing_date__year=int(year_filter))
        
        # 计算周期
        queryset = queryset.annotate(
            cycle_days_duration=ExpressionWrapper(
                F('signing_date') - F('procurement__result_publicity_release_date'),
                output_field=fields.DurationField()
            )
        )
        
        # 统计数据
        total_count = queryset.count()
        if total_count == 0:
            return {'avg_cycle': 0, 'on_time_rate': 0, 'count': 0}
        
        # 平均周期（转换为天数）
        avg_cycle_timedelta = queryset.aggregate(avg=Avg('cycle_days_duration'))['avg']
        avg_cycle = round(avg_cycle_timedelta.days, 1) if avg_cycle_timedelta else 0
        
        # 及时率（统一15天）
        deadline = self.contract_rules['deadline_days']
        on_time_count = queryset.filter(
            cycle_days_duration__lte=timedelta(days=deadline)
        ).count()
        on_time_rate = round(on_time_count / total_count * 100, 1) if total_count > 0 else 0
        
        return {
            'avg_cycle': avg_cycle,
            'on_time_rate': on_time_rate,
            'count': total_count
        }

    def _calculate_cycle_trend(self, model, project_code=None, person_name=None,
                              year_filter=None, global_project=None, cycle_type='procurement'):
        """
        计算周期趋势
        
        Args:
            model: 模型类（Procurement 或 Contract）
            cycle_type: 'procurement' 或 'contract'
        
        Returns:
            list: [{'period': '2024-H1', 'avg_cycle': 25.5}, ...]
        """
        if cycle_type == 'procurement':
            queryset = model.objects.filter(
                requirement_approval_date__isnull=False,
                result_publicity_release_date__isnull=False
            )
            
            # 应用筛选
            if project_code:
                queryset = queryset.filter(project_id=project_code)
            if person_name:
                queryset = queryset.filter(procurement_officer=person_name)
            if global_project:
                queryset = queryset.filter(project_id=global_project)
            
            # 计算周期
            queryset = queryset.annotate(
                cycle_days_duration=ExpressionWrapper(
                    F('result_publicity_release_date') - F('requirement_approval_date'),
                    output_field=fields.DurationField()
                ),
                business_year=ExtractYear('requirement_approval_date'),
                business_month=ExtractMonth('requirement_approval_date')
            )
            
        else:  # contract
            queryset = model.objects.filter(
                contract_source=ContractSource.PROCUREMENT.value,
                procurement__isnull=False,
                procurement__result_publicity_release_date__isnull=False,
                signing_date__isnull=False
            )
            
            # 应用筛选
            if project_code:
                queryset = queryset.filter(project_id=project_code)
            if person_name:
                queryset = queryset.filter(contract_officer=person_name)
            if global_project:
                queryset = queryset.filter(project_id=global_project)
            
            # 计算周期
            queryset = queryset.annotate(
                cycle_days_duration=ExpressionWrapper(
                    F('signing_date') - F('procurement__result_publicity_release_date'),
                    output_field=fields.DurationField()
                ),
                business_year=ExtractYear('signing_date'),
                business_month=ExtractMonth('signing_date')
            )
        
        # 判断分组方式
        if year_filter and year_filter != 'all':
            # 单年度：按月分组
            queryset = queryset.filter(business_year=int(year_filter))
            trend_data = self._group_by_month(queryset)
        else:
            # 全年度：按半年分组
            trend_data = self._group_by_half_year(queryset)
        
        return trend_data

    def _group_by_month(self, queryset):
        """按月分组统计 - 只返回有数据的月份"""
        trend_data = []
        
        for month in range(1, 13):
            month_data = queryset.filter(business_month=month)
            count = month_data.count()
            
            if count > 0:
                avg_cycle_timedelta = month_data.aggregate(avg=Avg('cycle_days_duration'))['avg']
                avg_cycle = round(avg_cycle_timedelta.days, 1) if avg_cycle_timedelta else 0
                
                trend_data.append({
                    'month': month,
                    'period': f'{month}月',
                    'avg_cycle': avg_cycle,
                    'count': count
                })
        
        return trend_data

    def _group_by_half_year(self, queryset):
        """按半年分组统计 - 只返回有数据的半年"""
        trend_data = []
        
        # 获取数据的年份范围
        years = queryset.values_list('business_year', flat=True).distinct().order_by('business_year')
        
        for year in years:
            # 上半年（1-6月）
            h1_data = queryset.filter(business_year=year, business_month__lte=6)
            h1_count = h1_data.count()
            
            if h1_count > 0:
                h1_avg_timedelta = h1_data.aggregate(avg=Avg('cycle_days_duration'))['avg']
                h1_avg_cycle = round(h1_avg_timedelta.days, 1) if h1_avg_timedelta else 0
                
                trend_data.append({
                    'year': year,
                    'half': 1,
                    'period': f'{year}上半年',
                    'avg_cycle': h1_avg_cycle,
                    'count': h1_count
                })
            
            # 下半年（7-12月）
            h2_data = queryset.filter(business_year=year, business_month__gt=6)
            h2_count = h2_data.count()
            
            if h2_count > 0:
                h2_avg_timedelta = h2_data.aggregate(avg=Avg('cycle_days_duration'))['avg']
                h2_avg_cycle = round(h2_avg_timedelta.days, 1) if h2_avg_timedelta else 0
                
                trend_data.append({
                    'year': year,
                    'half': 2,
                    'period': f'{year}下半年',
                    'avg_cycle': h2_avg_cycle,
                    'count': h2_count
                })
        
        return trend_data

    def _get_overdue_records(self, project_code=None, person_name=None,
                            year_filter=None, global_project=None):
        """获取超期记录（按严重程度分组）"""
        overdue_records = {
            'severe': {'procurement': [], 'contract': []},
            'moderate': {'procurement': [], 'contract': []},
            'mild': {'procurement': [], 'contract': []}
        }
        
        # 采购超期记录
        procurement_qs = Procurement.objects.filter(
            requirement_approval_date__isnull=False,
            result_publicity_release_date__isnull=False
        ).select_related('project')
        
        if project_code:
            procurement_qs = procurement_qs.filter(project_id=project_code)
        if person_name:
            procurement_qs = procurement_qs.filter(procurement_officer=person_name)
        if global_project:
            procurement_qs = procurement_qs.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            procurement_qs = procurement_qs.filter(requirement_approval_date__year=int(year_filter))
        
        for item in procurement_qs:
            cycle_days = (item.result_publicity_release_date - item.requirement_approval_date).days
            deadline = self.get_procurement_deadline(item.procurement_method)
            overdue_days = cycle_days - deadline
            
            if overdue_days > 0:
                severity = self._get_severity(overdue_days, 'procurement')
                overdue_records[severity]['procurement'].append({
                    'code': item.procurement_code,
                    'name': item.project_name,
                    'officer': item.procurement_officer,
                    'start_date': item.requirement_approval_date,
                    'end_date': item.result_publicity_release_date,
                    'cycle_days': cycle_days,
                    'deadline_days': deadline,
                    'overdue_days': overdue_days
                })
        
        # 合同超期记录
        contract_qs = Contract.objects.filter(
            contract_source=ContractSource.PROCUREMENT.value,
            procurement__isnull=False,
            procurement__result_publicity_release_date__isnull=False,
            signing_date__isnull=False
        ).select_related('project', 'procurement')
        
        if project_code:
            contract_qs = contract_qs.filter(project_id=project_code)
        if person_name:
            contract_qs = contract_qs.filter(contract_officer=person_name)
        if global_project:
            contract_qs = contract_qs.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            contract_qs = contract_qs.filter(signing_date__year=int(year_filter))
        
        deadline = self.contract_rules['deadline_days']
        for item in contract_qs:
            cycle_days = (item.signing_date - item.procurement.result_publicity_release_date).days
            overdue_days = cycle_days - deadline
            
            if overdue_days > 0:
                severity = self._get_severity(overdue_days, 'contract')
                overdue_records[severity]['contract'].append({
                    'code': item.contract_code,
                    'name': item.contract_name,
                    'officer': item.contract_officer,
                    'start_date': item.procurement.result_publicity_release_date,
                    'end_date': item.signing_date,
                    'cycle_days': cycle_days,
                    'deadline_days': deadline,
                    'overdue_days': overdue_days
                })
        
        return overdue_records

    def _get_ongoing_records(self, project_code=None, person_name=None,
                            year_filter=None, global_project=None):
        """获取进行中的记录（未完成但未超期）"""
        today = timezone.now().date()
        ongoing_records = {'procurement': [], 'contract': []}
        
        # 进行中的采购（有需求审批但未公示）
        procurement_qs = Procurement.objects.filter(
            requirement_approval_date__isnull=False,
            result_publicity_release_date__isnull=True
        ).select_related('project')
        
        if project_code:
            procurement_qs = procurement_qs.filter(project_id=project_code)
        if person_name:
            procurement_qs = procurement_qs.filter(procurement_officer=person_name)
        if global_project:
            procurement_qs = procurement_qs.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            procurement_qs = procurement_qs.filter(requirement_approval_date__year=int(year_filter))
        
        for item in procurement_qs:
            used_days = (today - item.requirement_approval_date).days
            deadline = self.get_procurement_deadline(item.procurement_method)
            remaining_days = deadline - used_days
            
            ongoing_records['procurement'].append({
                'code': item.procurement_code,
                'name': item.project_name,
                'officer': item.procurement_officer,
                'start_date': item.requirement_approval_date,
                'used_days': used_days,
                'remaining_days': remaining_days,
                'status': '即将超期' if remaining_days < 0 else '正常进行'
            })
        
        # 进行中的合同（采购已公示但合同未签订）
        contract_qs = Contract.objects.filter(
            contract_source=ContractSource.PROCUREMENT.value,
            procurement__isnull=False,
            procurement__result_publicity_release_date__isnull=False,
            signing_date__isnull=True
        ).select_related('project', 'procurement')
        
        if project_code:
            contract_qs = contract_qs.filter(project_id=project_code)
        if person_name:
            contract_qs = contract_qs.filter(contract_officer=person_name)
        if global_project:
            contract_qs = contract_qs.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            contract_qs = contract_qs.filter(procurement__result_publicity_release_date__year=int(year_filter))
        
        deadline = self.contract_rules['deadline_days']
        for item in contract_qs:
            used_days = (today - item.procurement.result_publicity_release_date).days
            remaining_days = deadline - used_days
            
            ongoing_records['contract'].append({
                'code': item.contract_code,
                'name': item.contract_name,
                'officer': item.contract_officer,
                'start_date': item.procurement.result_publicity_release_date,
                'used_days': used_days,
                'remaining_days': remaining_days,
                'status': '即将超期' if remaining_days < 0 else '正常进行'
            })
        
        return ongoing_records

    def _get_severity(self, overdue_days, cycle_type):
        """根据超期天数判断严重程度"""
        thresholds = CYCLE_RULES[cycle_type]['severity_thresholds']
        
        if overdue_days >= thresholds['severe']:
            return 'severe'
        elif overdue_days >= thresholds['moderate']:
            return 'moderate'
        else:
            return 'mild'

    def _get_person_project_count(self, person_name, year_filter=None, global_project=None):
        """获取经办人负责的项目数"""
        project_ids = set()
        
        # 从采购中获取项目
        procurement_qs = Procurement.objects.filter(procurement_officer=person_name)
        if year_filter and year_filter != 'all':
            procurement_qs = procurement_qs.filter(requirement_approval_date__year=int(year_filter))
        if global_project:
            procurement_qs = procurement_qs.filter(project_id=global_project)
        project_ids.update(procurement_qs.values_list('project_id', flat=True).distinct())
        
        # 从合同中获取项目
        contract_qs = Contract.objects.filter(contract_officer=person_name)
        if year_filter and year_filter != 'all':
            contract_qs = contract_qs.filter(signing_date__year=int(year_filter))
        if global_project:
            contract_qs = contract_qs.filter(project_id=global_project)
        project_ids.update(contract_qs.values_list('project_id', flat=True).distinct())
        
        return len(project_ids)

    def get_procurement_by_method_breakdown(self, year_filter=None, project_filter=None, person_name=None, methods=None):
        """
        按采购方式维度的采购周期统计（平均天数、样本量、达标率）。
        为保持实现简单（KISS），在Python侧一趟遍历完成分组与达标计算，避免复杂SQL。
        """
        queryset = Procurement.objects.filter(
            requirement_approval_date__isnull=False,
            result_publicity_release_date__isnull=False
        ).select_related('project')

        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        if person_name:
            queryset = queryset.filter(procurement_officer=person_name)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(requirement_approval_date__year=int(year_filter))
        if methods:
            non_null_methods = [m for m in methods if m and m != '未标注']
            q_obj = Q()
            if non_null_methods:
                q_obj |= Q(procurement_method__in=non_null_methods)
            if '未标注' in methods:
                q_obj |= Q(procurement_method__isnull=True) | Q(procurement_method__exact='')
            queryset = queryset.filter(q_obj)

        groups = {}
        for item in queryset:
            method = item.procurement_method or '未标注'
            if method == '':
                method = '未标注'
            cycle_days = (item.result_publicity_release_date - item.requirement_approval_date).days
            g = groups.setdefault(method, {'method': method, 'count': 0, 'total_days': 0, 'on_time': 0})
            g['count'] += 1
            g['total_days'] += cycle_days
            deadline = self.get_procurement_deadline(method)
            if cycle_days <= deadline:
                g['on_time'] += 1

        results = []
        for method, g in groups.items():
            avg_cycle = round(g['total_days'] / g['count'], 1) if g['count'] > 0 else 0
            on_time_rate = round(g['on_time'] / g['count'] * 100, 1) if g['count'] > 0 else 0
            results.append({
                'method': method,
                'count': g['count'],
                'avg_cycle': avg_cycle,
                'on_time_rate': on_time_rate,
                'deadline': self.get_procurement_deadline(method)
            })

        results.sort(key=lambda x: x['count'], reverse=True)
        return results
