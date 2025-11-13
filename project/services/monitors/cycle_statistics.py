"""
工作周期统计服务
负责计算项目和个人的工作周期统计数据（采购周期、合同周期）
"""
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q, F, ExpressionWrapper, fields
from django.db.models.functions import ExtractYear, ExtractMonth
from procurement.models import Procurement
from contract.models import Contract
from project.enums import FilePositioning
from .config import CYCLE_RULES


class CycleStatisticsService:
    """工作周期统计服务类（遵循SRP原则）"""

    def __init__(self):
        self.procurement_rule = CYCLE_RULES['procurement']
        self.contract_rule = CYCLE_RULES['contract']

    def get_projects_cycle_overview(self, year_filter=None, project_filter=None, procurement_method=None):
        """
        获取项目维度的工作周期概览
        
        Args:
            year_filter: str - 年度筛选（'all' 或具体年份）
            project_filter: str or None - 项目编码筛选
            procurement_method: str or None - 采购方式筛选
        
        Returns:
            dict: {
                'summary': {汇总统计},
                'projects': [{项目列表}]
            }
        """
        from project.models import Project
        
        # 获取项目列表
        projects_qs = Project.objects.all()
        if project_filter:
            projects_qs = projects_qs.filter(project_code=project_filter)
        
        projects_data = []
        total_procurement_count = 0
        total_procurement_completed = 0
        total_contract_count = 0
        total_contract_completed = 0
        excluded_procurement_count = 0  # 缺少结果公示时间的采购数量
        
        for project in projects_qs:
            # 计算该项目的采购周期统计
            procurement_stats = self._calculate_procurement_cycle_statistics(
                project_code=project.project_code,
                year_filter=year_filter,
                procurement_method=procurement_method
            )
            
            # 计算该项目的合同周期统计
            contract_stats = self._calculate_contract_cycle_statistics(
                project_code=project.project_code,
                year_filter=year_filter
            )
            
            # 获取采购和合同的总数（包括未完成的）
            procurement_total = self._get_procurement_total_count(
                project_code=project.project_code,
                year_filter=year_filter,
                procurement_method=procurement_method
            )
            contract_total = self._get_contract_total_count(
                project_code=project.project_code,
                year_filter=year_filter
            )
            
            # 计算综合完成率
            total_items = procurement_total + contract_total
            completed_items = procurement_stats['count'] + contract_stats['count']
            overall_completion_rate = round(completed_items / total_items * 100, 1) if total_items > 0 else 0
            
            projects_data.append({
                'project_code': project.project_code,
                'project_name': project.project_name,
                'procurement_count': procurement_total,
                'procurement_completed': procurement_stats['count'],
                'procurement_avg_cycle': procurement_stats['avg_cycle'],
                'procurement_on_time_rate': procurement_stats['on_time_rate'],
                'contract_count': contract_total,
                'contract_completed': contract_stats['count'],
                'contract_avg_cycle': contract_stats['avg_cycle'],
                'contract_on_time_rate': contract_stats['on_time_rate'],
                'overall_completion_rate': overall_completion_rate,
                'excluded_count': procurement_stats.get('excluded_count', 0)
            })
            
            # 累加到汇总数据
            total_procurement_count += procurement_total
            total_procurement_completed += procurement_stats['count']
            total_contract_count += contract_total
            total_contract_completed += contract_stats['count']
            excluded_procurement_count += procurement_stats.get('excluded_count', 0)
        
        # 按综合完成率降序排序
        projects_data.sort(key=lambda x: x['overall_completion_rate'], reverse=True)
        
        # 计算汇总统计
        total_all = total_procurement_count + total_contract_count
        completed_all = total_procurement_completed + total_contract_completed
        overall_rate = round(completed_all / total_all * 100, 1) if total_all > 0 else 0
        
        summary = {
            'project_count': len(projects_data),
            'procurement_total': total_procurement_count,
            'procurement_completed': total_procurement_completed,
            'contract_total': total_contract_count,
            'contract_completed': total_contract_completed,
            'overall_completion_rate': overall_rate,
            'excluded_procurement_count': excluded_procurement_count
        }
        
        return {
            'summary': summary,
            'projects': projects_data
        }

    def get_persons_cycle_overview(self, year_filter=None, project_filter=None, procurement_method=None):
        """
        获取个人维度的工作周期概览
        
        Args:
            year_filter: str - 年度筛选
            project_filter: str or None - 项目筛选（影响经办人范围）
            procurement_method: str or None - 采购方式筛选
        
        Returns:
            dict: {
                'summary': {汇总统计},
                'persons': [{经办人列表}]
            }
        """
        # 获取所有经办人名单
        person_names = set()
        
        # 采购经办人
        procurement_qs = Procurement.objects.filter(procurement_officer__isnull=False)
        if year_filter and year_filter != 'all':
            procurement_qs = procurement_qs.filter(requirement_approval_date__year=int(year_filter))
        if project_filter:
            procurement_qs = procurement_qs.filter(project_id=project_filter)
        if procurement_method and procurement_method != 'all':
            procurement_qs = procurement_qs.filter(procurement_method=procurement_method)
        person_names.update(procurement_qs.values_list('procurement_officer', flat=True).distinct())
        
        # 合同经办人
        contract_qs = Contract.objects.filter(
            contract_officer__isnull=False,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
        )
        if year_filter and year_filter != 'all':
            contract_qs = contract_qs.filter(signing_date__year=int(year_filter))
        if project_filter:
            contract_qs = contract_qs.filter(project_id=project_filter)
        person_names.update(contract_qs.values_list('contract_officer', flat=True).distinct())
        
        persons_data = []
        total_procurement_count = 0
        total_procurement_completed = 0
        total_contract_count = 0
        total_contract_completed = 0
        excluded_procurement_count = 0
        
        for person_name in person_names:
            # 计算该经办人的采购周期统计
            procurement_stats = self._calculate_procurement_cycle_statistics(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter,
                procurement_method=procurement_method
            )
            
            # 计算该经办人的合同周期统计
            contract_stats = self._calculate_contract_cycle_statistics(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter
            )
            
            # 获取总数（包括未完成的）
            procurement_total = self._get_procurement_total_count(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter,
                procurement_method=procurement_method
            )
            contract_total = self._get_contract_total_count(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter
            )
            
            # 计算负责的项目数
            project_count = self._get_person_project_count(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter
            )
            
            # 计算综合完成率
            total_items = procurement_total + contract_total
            completed_items = procurement_stats['count'] + contract_stats['count']
            overall_completion_rate = round(completed_items / total_items * 100, 1) if total_items > 0 else 0
            
            persons_data.append({
                'handler_name': person_name,
                'procurement_count': procurement_total,
                'procurement_completed': procurement_stats['count'],
                'procurement_avg_cycle': procurement_stats['avg_cycle'],
                'procurement_on_time_rate': procurement_stats['on_time_rate'],
                'contract_count': contract_total,
                'contract_completed': contract_stats['count'],
                'contract_avg_cycle': contract_stats['avg_cycle'],
                'contract_on_time_rate': contract_stats['on_time_rate'],
                'overall_completion_rate': overall_completion_rate,
                'project_count': project_count,
                'excluded_count': procurement_stats.get('excluded_count', 0)
            })
            
            # 累加到汇总数据
            total_procurement_count += procurement_total
            total_procurement_completed += procurement_stats['count']
            total_contract_count += contract_total
            total_contract_completed += contract_stats['count']
            excluded_procurement_count += procurement_stats.get('excluded_count', 0)
        
        # 按综合完成率降序排序
        persons_data.sort(key=lambda x: x['overall_completion_rate'], reverse=True)
        
        # 计算汇总统计
        total_all = total_procurement_count + total_contract_count
        completed_all = total_procurement_completed + total_contract_completed
        overall_rate = round(completed_all / total_all * 100, 1) if total_all > 0 else 0
        
        summary = {
            'person_count': len(persons_data),
            'procurement_total': total_procurement_count,
            'procurement_completed': total_procurement_completed,
            'contract_total': total_contract_count,
            'contract_completed': total_contract_completed,
            'overall_completion_rate': overall_rate,
            'excluded_procurement_count': excluded_procurement_count
        }
        
        return {
            'summary': summary,
            'persons': persons_data
        }

    def _calculate_procurement_cycle_statistics(self, project_code=None, person_name=None,
                                                year_filter=None, global_project=None, procurement_method=None):
        """计算采购周期统计"""
        queryset = Procurement.objects.filter(
            requirement_approval_date__isnull=False,
            result_publicity_release_date__isnull=False
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
        if procurement_method and procurement_method != 'all':
            queryset = queryset.filter(procurement_method=procurement_method)

        # 计算工作周期
        queryset = queryset.annotate(
            work_cycle=ExpressionWrapper(
                F('result_publicity_release_date') - F('requirement_approval_date'),
                output_field=fields.DurationField()
            )
        )

        # 统计数据
        total_count = queryset.count()
        if total_count == 0:
            # 统计被排除的记录数（缺少结果公示时间）
            excluded_qs = Procurement.objects.filter(
                requirement_approval_date__isnull=False,
                result_publicity_release_date__isnull=True
            )
            if project_code:
                excluded_qs = excluded_qs.filter(project_id=project_code)
            if person_name:
                excluded_qs = excluded_qs.filter(procurement_officer=person_name)
            if global_project:
                excluded_qs = excluded_qs.filter(project_id=global_project)
            if year_filter and year_filter != 'all':
                excluded_qs = excluded_qs.filter(requirement_approval_date__year=int(year_filter))
            if procurement_method and procurement_method != 'all':
                excluded_qs = excluded_qs.filter(procurement_method=procurement_method)
            
            return {'avg_cycle': 0, 'on_time_rate': 0, 'count': 0, 'excluded_count': excluded_qs.count()}

        # 平均周期（转换为天数）
        avg_cycle_timedelta = queryset.aggregate(avg=Avg('work_cycle'))['avg']
        avg_cycle = avg_cycle_timedelta.days if avg_cycle_timedelta else 0

        # 及时完成率（根据采购方式的规定周期）
        on_time_count = 0
        for item in queryset:
            cycle_days = item.work_cycle.days if item.work_cycle else 0
            deadline = self.procurement_rule['deadline_map'].get(
                item.procurement_method,
                self.procurement_rule['default_deadline']
            )
            if cycle_days <= deadline:
                on_time_count += 1
        
        on_time_rate = round(on_time_count / total_count * 100, 1) if total_count > 0 else 0

        # 统计被排除的记录数
        excluded_qs = Procurement.objects.filter(
            requirement_approval_date__isnull=False,
            result_publicity_release_date__isnull=True
        )
        if project_code:
            excluded_qs = excluded_qs.filter(project_id=project_code)
        if person_name:
            excluded_qs = excluded_qs.filter(procurement_officer=person_name)
        if global_project:
            excluded_qs = excluded_qs.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            excluded_qs = excluded_qs.filter(requirement_approval_date__year=int(year_filter))
        if procurement_method and procurement_method != 'all':
            excluded_qs = excluded_qs.filter(procurement_method=procurement_method)

        return {
            'avg_cycle': avg_cycle,
            'on_time_rate': on_time_rate,
            'count': total_count,
            'excluded_count': excluded_qs.count()
        }

    def _calculate_contract_cycle_statistics(self, project_code=None, person_name=None,
                                            year_filter=None, global_project=None):
        """计算合同周期统计"""
        queryset = Contract.objects.filter(
            procurement__result_publicity_release_date__isnull=False,
            signing_date__isnull=False,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
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

        # 计算工作周期
        queryset = queryset.annotate(
            work_cycle=ExpressionWrapper(
                F('signing_date') - F('procurement__result_publicity_release_date'),
                output_field=fields.DurationField()
            )
        )

        # 统计数据
        total_count = queryset.count()
        if total_count == 0:
            return {'avg_cycle': 0, 'on_time_rate': 0, 'count': 0}

        # 平均周期（转换为天数）
        avg_cycle_timedelta = queryset.aggregate(avg=Avg('work_cycle'))['avg']
        avg_cycle = avg_cycle_timedelta.days if avg_cycle_timedelta else 0

        # 及时完成率
        deadline = self.contract_rule['deadline_days']
        on_time_count = queryset.filter(
            work_cycle__lte=timedelta(days=deadline)
        ).count()
        on_time_rate = round(on_time_count / total_count * 100, 1) if total_count > 0 else 0

        return {
            'avg_cycle': avg_cycle,
            'on_time_rate': on_time_rate,
            'count': total_count
        }

    def _calculate_trend(self, model, project_code=None, person_name=None,
                        year_filter=None, global_project=None, procurement_method=None,
                        start_field='', end_field='', person_field=None):
        """
        计算工作周期趋势
        
        Args:
            model: 模型类（Procurement 或 Contract）
            project_code: 项目编码
            person_name: 经办人姓名
            year_filter: 年份筛选
            global_project: 全局项目筛选
            procurement_method: 采购方式筛选
            start_field: 开始日期字段名
            end_field: 结束日期字段名
            person_field: 经办人字段名
        
        Returns:
            list: [{'period': '2024-H1', 'avg_cycle': 25.5}, ...]
        """
        queryset = model.objects.filter(
            **{f'{start_field}__isnull': False, f'{end_field}__isnull': False}
        )

        # 合同仅统计主合同
        if model == Contract:
            queryset = queryset.filter(file_positioning=FilePositioning.MAIN_CONTRACT.value)

        # 应用筛选
        if project_code:
            queryset = queryset.filter(project_id=project_code)
        if person_name and person_field:
            queryset = queryset.filter(**{person_field: person_name})
        if global_project:
            queryset = queryset.filter(project_id=global_project)
        if procurement_method and procurement_method != 'all' and model == Procurement:
            queryset = queryset.filter(procurement_method=procurement_method)

        # 计算工作周期
        queryset = queryset.annotate(
            work_cycle=ExpressionWrapper(
                F(end_field) - F(start_field),
                output_field=fields.DurationField()
            ),
            business_year=ExtractYear(start_field),
            business_month=ExtractMonth(start_field)
        )

        # 判断分组方式
        if year_filter and year_filter != 'all':
            # 单年度：按月分组
            queryset = queryset.filter(**{f'{start_field}__year': int(year_filter)})
            trend_data = self._group_by_month(queryset)
        else:
            # 全年度：按半年分组
            trend_data = self._group_by_half_year(queryset)

        return trend_data

    def _group_by_month(self, queryset):
        """委托公共实现，保持对外行为不变（DRY）。"""
        from .utils.time_grouping import group_by_month
        return group_by_month(queryset, cycle_field='work_cycle')

    def _group_by_half_year(self, queryset):
        """委托公共实现，保持对外行为不变（DRY）。"""
        from .utils.time_grouping import group_by_half_year
        return group_by_half_year(queryset, cycle_field='work_cycle')

    def get_project_trend_and_problems(self, project_code, year_filter=None, procurement_method=None, show_all=False):
        """
        获取单个项目的趋势图和超期记录
        
        Args:
            project_code: 项目编码
            year_filter: 年度筛选
            procurement_method: 采购方式筛选
            show_all: 是否显示所有记录
        
        Returns:
            dict: {
                'procurement_trend': [...],
                'contract_trend': [...],
                'problems': {...},
                'summary': {...},
                'records': {...}
            }
        """
        from .cycle_problem_detector import CycleProblemDetector
        
        # 计算趋势数据
        procurement_trend = self._calculate_trend(
            model=Procurement,
            project_code=project_code,
            year_filter=year_filter,
            procurement_method=procurement_method,
            start_field='requirement_approval_date',
            end_field='result_publicity_release_date'
        )
        
        contract_trend = self._calculate_trend(
            model=Contract,
            project_code=project_code,
            year_filter=year_filter,
            start_field='procurement__result_publicity_release_date',
            end_field='signing_date'
        )

        # 统计概要
        p_stats = self._calculate_procurement_cycle_statistics(
            project_code=project_code,
            year_filter=year_filter,
            procurement_method=procurement_method
        )
        c_stats = self._calculate_contract_cycle_statistics(
            project_code=project_code,
            year_filter=year_filter
        )
        p_total = self._get_procurement_total_count(
            project_code=project_code,
            year_filter=year_filter,
            procurement_method=procurement_method
        )
        c_total = self._get_contract_total_count(
            project_code=project_code,
            year_filter=year_filter
        )
        total_items = p_total + c_total
        completed_items = p_stats['count'] + c_stats['count']
        overall_rate = round(completed_items / total_items * 100, 1) if total_items > 0 else 0

        summary = {
            'procurement': {
                'count_total': p_total,
                'count_completed': p_stats['count'],
                'avg_cycle': p_stats['avg_cycle'],
                'on_time_rate': p_stats['on_time_rate'],
                'excluded_count': p_stats.get('excluded_count', 0)
            },
            'contract': {
                'count_total': c_total,
                'count_completed': c_stats['count'],
                'avg_cycle': c_stats['avg_cycle'],
                'on_time_rate': c_stats['on_time_rate'],
            },
            'overall_completion_rate': overall_rate,
        }

        # 详细记录
        records = {
            'procurements': self._get_procurement_cycle_records(
                project_code=project_code,
                year_filter=year_filter,
                procurement_method=procurement_method,
                limit=200
            ),
            'contracts': self._get_contract_cycle_records(
                project_code=project_code,
                year_filter=year_filter,
                limit=200
            ),
        }
        
        # 获取超期记录
        detector = CycleProblemDetector()
        filters = {'project': project_code}
        if year_filter and year_filter != 'all':
            filters['year_filter'] = int(year_filter)
        if procurement_method and procurement_method != 'all':
            filters['procurement_method'] = procurement_method
        
        problems = detector.detect_problems(filters=filters, show_all=show_all)
        
        return {
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'problems': problems,
            'summary': summary,
            'records': records,
        }

    def get_person_trend_and_problems(self, person_name, year_filter=None, project_filter=None, 
                                     procurement_method=None, show_all=False):
        """
        获取单个经办人的趋势图和超期记录
        
        Args:
            person_name: 经办人姓名
            year_filter: 年度筛选
            project_filter: 项目筛选
            procurement_method: 采购方式筛选
            show_all: 是否显示所有记录
        
        Returns:
            dict: {
                'procurement_trend': [...],
                'contract_trend': [...],
                'problems': {...},
                'summary': {...},
                'records': {...}
            }
        """
        from .cycle_problem_detector import CycleProblemDetector
        
        # 计算趋势数据
        procurement_trend = self._calculate_trend(
            model=Procurement,
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
            procurement_method=procurement_method,
            start_field='requirement_approval_date',
            end_field='result_publicity_release_date',
            person_field='procurement_officer'
        )
        
        contract_trend = self._calculate_trend(
            model=Contract,
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
            start_field='procurement__result_publicity_release_date',
            end_field='signing_date',
            person_field='contract_officer'
        )

        # 统计概要
        p_stats = self._calculate_procurement_cycle_statistics(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
            procurement_method=procurement_method
        )
        c_stats = self._calculate_contract_cycle_statistics(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter
        )
        p_total = self._get_procurement_total_count(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
            procurement_method=procurement_method
        )
        c_total = self._get_contract_total_count(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter
        )
        total_items = p_total + c_total
        completed_items = p_stats['count'] + c_stats['count']
        overall_rate = round(completed_items / total_items * 100, 1) if total_items > 0 else 0

        summary = {
            'procurement': {
                'count_total': p_total,
                'count_completed': p_stats['count'],
                'avg_cycle': p_stats['avg_cycle'],
                'on_time_rate': p_stats['on_time_rate'],
                'excluded_count': p_stats.get('excluded_count', 0)
            },
            'contract': {
                'count_total': c_total,
                'count_completed': c_stats['count'],
                'avg_cycle': c_stats['avg_cycle'],
                'on_time_rate': c_stats['on_time_rate'],
            },
            'overall_completion_rate': overall_rate,
        }

        # 详细记录
        records = {
            'procurements': self._get_procurement_cycle_records(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter,
                procurement_method=procurement_method,
                limit=200
            ),
            'contracts': self._get_contract_cycle_records(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter,
                limit=200
            ),
        }
        
        # 获取超期记录
        detector = CycleProblemDetector()
        filters = {'responsible_person': person_name}
        if year_filter and year_filter != 'all':
            filters['year_filter'] = int(year_filter)
        if project_filter:
            filters['project'] = project_filter
        if procurement_method and procurement_method != 'all':
            filters['procurement_method'] = procurement_method
        
        problems = detector.detect_problems(filters=filters, show_all=show_all)
        
        return {
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'problems': problems,
            'summary': summary,
            'records': records,
        }

    def _get_procurement_cycle_records(self, project_code=None, person_name=None,
                                       year_filter=None, global_project=None,
                                       procurement_method=None, limit=200):
        """获取采购工作周期记录明细"""
        qs = Procurement.objects.select_related('project').filter(
            requirement_approval_date__isnull=False
        )

        if project_code:
            qs = qs.filter(project_id=project_code)
        if person_name:
            qs = qs.filter(procurement_officer=person_name)
        if global_project:
            qs = qs.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            qs = qs.filter(requirement_approval_date__year=int(year_filter))
        if procurement_method and procurement_method != 'all':
            qs = qs.filter(procurement_method=procurement_method)

        qs = qs.order_by('-requirement_approval_date')[:limit]

        today = timezone.now().date()
        records = []
        for item in qs:
            start_date = item.requirement_approval_date
            end_date = item.result_publicity_release_date
            
            # 获取该采购方式的规定周期
            deadline_days = self.procurement_rule['deadline_map'].get(
                item.procurement_method,
                self.procurement_rule['default_deadline']
            )
            
            cycle_days = None
            overdue_days = 0
            on_time = None

            if start_date and end_date:
                cycle_days = (end_date - start_date).days
                on_time = cycle_days <= deadline_days
                if cycle_days > deadline_days:
                    overdue_days = cycle_days - deadline_days

            records.append({
                'module': 'procurement',
                'code': getattr(item, 'procurement_code', ''),
                'name': getattr(item, 'project_name', ''),
                'procurement_method': getattr(item, 'procurement_method', ''),
                'responsible_person': getattr(item, 'procurement_officer', '') or '',
                'start_date': start_date,
                'end_date': end_date,
                'deadline_days': deadline_days,
                'cycle_days': cycle_days,
                'on_time': on_time,
                'overdue_days': overdue_days,
            })

        return records

    def _get_contract_cycle_records(self, project_code=None, person_name=None,
                                    year_filter=None, global_project=None, limit=200):
        """获取合同工作周期记录明细（仅主合同）"""
        qs = Contract.objects.select_related('project', 'procurement').filter(
            file_positioning=FilePositioning.MAIN_CONTRACT.value,
            procurement__result_publicity_release_date__isnull=False
        )

        if project_code:
            qs = qs.filter(project_id=project_code)
        if person_name:
            qs = qs.filter(contract_officer=person_name)
        if global_project:
            qs = qs.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            qs = qs.filter(signing_date__year=int(year_filter))

        qs = qs.order_by('-signing_date')[:limit]

        today = timezone.now().date()
        deadline_days = self.contract_rule['deadline_days']
        records = []
        for item in qs:
            start_date = item.procurement.result_publicity_release_date if item.procurement else None
            end_date = item.signing_date
            
            cycle_days = None
            overdue_days = 0
            on_time = None

            if start_date and end_date:
                cycle_days = (end_date - start_date).days
                on_time = cycle_days <= deadline_days
                if cycle_days > deadline_days:
                    overdue_days = cycle_days - deadline_days

            records.append({
                'module': 'contract',
                'code': getattr(item, 'contract_code', ''),
                'contract_sequence': getattr(item, 'contract_sequence', '') or '',
                'name': getattr(item, 'contract_name', ''),
                'responsible_person': getattr(item, 'contract_officer', '') or '',
                'start_date': start_date,
                'end_date': end_date,
                'deadline_days': deadline_days,
                'cycle_days': cycle_days,
                'on_time': on_time,
                'overdue_days': overdue_days if overdue_days > 0 else 0,
            })

        return records

    def _get_procurement_total_count(self, project_code=None, person_name=None,
                                     year_filter=None, global_project=None, procurement_method=None):
        """获取采购总数（包括未完成的）"""
        queryset = Procurement.objects.filter(requirement_approval_date__isnull=False)
        
        if project_code:
            queryset = queryset.filter(project_id=project_code)
        if person_name:
            queryset = queryset.filter(procurement_officer=person_name)
        if global_project:
            queryset = queryset.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(requirement_approval_date__year=int(year_filter))
        if procurement_method and procurement_method != 'all':
            queryset = queryset.filter(procurement_method=procurement_method)
        
        return queryset.count()

    def _get_contract_total_count(self, project_code=None, person_name=None,
                                  year_filter=None, global_project=None):
        """获取合同总数（包括未完成的，仅主合同）"""
        queryset = Contract.objects.filter(
            procurement__result_publicity_release_date__isnull=False,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
        )
        
        if project_code:
            queryset = queryset.filter(project_id=project_code)
        if person_name:
            queryset = queryset.filter(contract_officer=person_name)
        if global_project:
            queryset = queryset.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(signing_date__year=int(year_filter))
        
        return queryset.count()

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

    # ===== 多序列趋势（多人/多项目/项目内经办人） =====
    def _sort_halfyear_labels(self, labels):
        from .utils.time_grouping import sort_halfyear_labels
        return sort_halfyear_labels(labels)
    
    def _sort_month_labels(self, labels):
        from .utils.time_grouping import sort_month_labels
        return sort_month_labels(labels)

    def _align_series(self, trend_list, labels):
        from .utils.time_grouping import align_series
        return align_series(trend_list, labels)

    def get_person_list(self, year_filter=None, global_project=None, procurement_method=None):
        """
        获取经办人列表（用于下拉选择器），委托公共实现，行为不变。
        """
        from .utils.persons import get_person_list as _get_persons
        return _get_persons(year_filter=year_filter, global_project=global_project, procurement_method=procurement_method)

    def get_persons_multi_trend(self, year_filter=None, project_filter=None, procurement_method=None, top_n=10):
        """
        获取多人趋势：按经办人分别计算采购/合同的趋势，多条折线合并显示。
        只显示至少有一个人有数据的时间段。
        返回: {
          'labels': [...],
          'procurement': [{'name': '张三', 'data': [...]}, ...],
          'contract': [{'name': '张三', 'data': [...]}, ...]
        }
        """
        # 选人（按业务量排序取前N名）
        person_list = self.get_person_list(year_filter=year_filter, global_project=project_filter, procurement_method=procurement_method)
        person_names = [p['name'] for p in person_list[:top_n]]

        # 逐人计算趋势并汇总标签（只收集有数据的标签）
        all_labels = set()
        per_person_trend = {'procurement': {}, 'contract': {}}
        for name in person_names:
            t_p = self._calculate_trend(
                model=Procurement,
                person_name=name,
                year_filter=year_filter,
                global_project=project_filter,
                procurement_method=procurement_method,
                start_field='requirement_approval_date',
                end_field='result_publicity_release_date',
                person_field='procurement_officer'
            )
            t_c = self._calculate_trend(
                model=Contract,
                person_name=name,
                year_filter=year_filter,
                global_project=project_filter,
                start_field='procurement__result_publicity_release_date',
                end_field='signing_date',
                person_field='contract_officer'
            )
            # 只添加有数据的标签
            for it in t_p:
                if it.get('count', 0) > 0:
                    all_labels.add(it['period'])
            for it in t_c:
                if it.get('count', 0) > 0:
                    all_labels.add(it['period'])
            per_person_trend['procurement'][name] = t_p
            per_person_trend['contract'][name] = t_c

        # 统一标签顺序（只包含有数据的标签）
        if year_filter and year_filter != 'all':
            # 单年度：只显示有数据的月份
            labels = self._sort_month_labels(all_labels)
        else:
            # 多年度：只显示有数据的半年
            labels = self._sort_halfyear_labels(all_labels)

        # 对齐成折线数组
        result = {'labels': labels, 'procurement': [], 'contract': []}
        for name in person_names:
            result['procurement'].append({
                'name': name,
                'data': self._align_series(per_person_trend['procurement'].get(name, []), labels)
            })
            result['contract'].append({
                'name': name,
                'data': self._align_series(per_person_trend['contract'].get(name, []), labels)
            })
        return result

    def get_projects_multi_trend(self, year_filter=None, procurement_method=None, top_n=10):
        """
        获取多项目趋势：按项目分别计算采购/合同的趋势，多条折线合并显示（取前N个项目）。
        只显示至少有一个项目有数据的时间段。
        """
        from project.models import Project
        projects = list(Project.objects.all())
        # 简化：依据合同+采购总量排序
        scored = []
        for p in projects:
            p_total = self._get_procurement_total_count(project_code=p.project_code, year_filter=year_filter, procurement_method=procurement_method)
            c_total = self._get_contract_total_count(project_code=p.project_code, year_filter=year_filter)
            scored.append((p, p_total + c_total))
        scored.sort(key=lambda x: x[1], reverse=True)
        top_projects = [p.project_code for p, _ in scored[:top_n]]

        # 计算趋势并汇总（只收集有数据的标签）
        all_labels = set()
        per_project_trend = {'procurement': {}, 'contract': {}}
        for code in top_projects:
            t_p = self._calculate_trend(
                model=Procurement,
                project_code=code,
                year_filter=year_filter,
                procurement_method=procurement_method,
                start_field='requirement_approval_date',
                end_field='result_publicity_release_date'
            )
            t_c = self._calculate_trend(
                model=Contract,
                project_code=code,
                year_filter=year_filter,
                start_field='procurement__result_publicity_release_date',
                end_field='signing_date'
            )
            # 只添加有数据的标签
            for it in t_p:
                if it.get('count', 0) > 0:
                    all_labels.add(it['period'])
            for it in t_c:
                if it.get('count', 0) > 0:
                    all_labels.add(it['period'])
            per_project_trend['procurement'][code] = t_p
            per_project_trend['contract'][code] = t_c

        # 统一标签顺序（只包含有数据的标签）
        if year_filter and year_filter != 'all':
            labels = self._sort_month_labels(all_labels)
        else:
            labels = self._sort_halfyear_labels(all_labels)

        result = {'labels': labels, 'procurement': [], 'contract': []}
        for code in top_projects:
            result['procurement'].append({
                'name': code,
                'data': self._align_series(per_project_trend['procurement'].get(code, []), labels)
            })
            result['contract'].append({
                'name': code,
                'data': self._align_series(per_project_trend['contract'].get(code, []), labels)
            })
        return result

    def get_project_officers_multi_trend(self, project_code, year_filter=None, procurement_method=None, top_n=10):
        """
        获取单个项目下经办人维度的趋势：
        - 采购tab：各采购经办人的采购趋势
        - 合同tab：各合同经办人的合同趋势
        """
        # 选人：该项目内前N名经办人
        p_qs = Procurement.objects.filter(project_id=project_code)
        if procurement_method and procurement_method != 'all':
            p_qs = p_qs.filter(procurement_method=procurement_method)
        p_names = list(p_qs.values_list('procurement_officer', flat=True).distinct())
        
        c_names = list(
            Contract.objects.filter(project_id=project_code, file_positioning=FilePositioning.MAIN_CONTRACT.value)
            .values_list('contract_officer', flat=True).distinct()
        )
        # 去空
        p_names = [x for x in p_names if x]
        c_names = [x for x in c_names if x]

        # 排序（依据业务量）
        def sort_by_volume(names, is_proc):
            scored = []
            for n in names:
                if is_proc:
                    cnt = self._get_procurement_total_count(person_name=n, year_filter=year_filter, global_project=project_code, procurement_method=procurement_method)
                else:
                    cnt = self._get_contract_total_count(person_name=n, year_filter=year_filter, global_project=project_code)
                scored.append((n, cnt))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [n for n, _ in scored[:top_n]]

        p_names = sort_by_volume(p_names, True)
        c_names = sort_by_volume(c_names, False)

        all_labels = set()
        p_trends = {}
        c_trends = {}
        for n in p_names:
            t = self._calculate_trend(
                model=Procurement,
                person_name=n,
                year_filter=year_filter,
                global_project=project_code,
                procurement_method=procurement_method,
                start_field='requirement_approval_date',
                end_field='result_publicity_release_date',
                person_field='procurement_officer'
            )
            # 只添加有数据的标签
            for it in t:
                if it.get('count', 0) > 0:
                    all_labels.add(it['period'])
            p_trends[n] = t
        for n in c_names:
            t = self._calculate_trend(
                model=Contract,
                person_name=n,
                year_filter=year_filter,
                global_project=project_code,
                start_field='procurement__result_publicity_release_date',
                end_field='signing_date',
                person_field='contract_officer'
            )
            # 只添加有数据的标签
            for it in t:
                if it.get('count', 0) > 0:
                    all_labels.add(it['period'])
            c_trends[n] = t

        # 统一标签顺序（只包含有数据的标签）
        if year_filter and year_filter != 'all':
            labels = self._sort_month_labels(all_labels)
        else:
            labels = self._sort_halfyear_labels(all_labels)
        result = {'labels': labels, 'procurement': [], 'contract': []}
        for n in p_names:
            result['procurement'].append({'name': n, 'data': self._align_series(p_trends.get(n, []), labels)})
        for n in c_names:
            result['contract'].append({'name': n, 'data': self._align_series(c_trends.get(n, []), labels)})
        return result