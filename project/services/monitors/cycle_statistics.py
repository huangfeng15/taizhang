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
        
        # 采购经办人 - 排除NULL和空字符串
        procurement_qs = Procurement.objects.filter(
            procurement_officer__isnull=False
        ).exclude(procurement_officer='')
        if year_filter and year_filter != 'all':
            # 与采购列表保持一致：按结果公示发布时间过滤年度
            procurement_qs = procurement_qs.filter(result_publicity_release_date__year=int(year_filter))
        if project_filter:
            procurement_qs = procurement_qs.filter(project_id=project_filter)
        if procurement_method and procurement_method != 'all':
            procurement_qs = procurement_qs.filter(procurement_method=procurement_method)
        person_names.update(procurement_qs.values_list('procurement_officer', flat=True).distinct())
        
        # 合同经办人 - 排除NULL和空字符串
        contract_qs = Contract.objects.filter(
            contract_officer__isnull=False,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
        ).exclude(contract_officer='')
        if year_filter and year_filter != 'all':
            contract_qs = contract_qs.filter(signing_date__year=int(year_filter))
        if project_filter:
            contract_qs = contract_qs.filter(project_id=project_filter)
        person_names.update(contract_qs.values_list('contract_officer', flat=True).distinct())
        
        # 额外保障：过滤掉可能的空白字符串
        person_names = {name.strip() for name in person_names if name and name.strip()}
        
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

    def get_procurement_completeness_detail(self, year_filter=None, project_filter=None,
                                            procurement_method=None):
        """
        获取采购周期统计的纳入/排除明细，用于前端展示数据完整性说明。

        说明：
        - 年度维度与采购管理列表保持一致：
          已完成记录按「结果公示发布时间」归属年度；
          未完成记录（尚未公示）按「需求书审批完成日期」归属年度。
        """
        queryset = Procurement.objects.select_related('project')

        # 项目与采购方式筛选（与 overview 保持一致）
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        if procurement_method and procurement_method != 'all':
            queryset = queryset.filter(procurement_method=procurement_method)

        # 年度筛选：已完成按结果公示时间，未完成按需求书审批日期
        if year_filter and year_filter != 'all':
            year_int = int(year_filter)
            queryset = queryset.filter(
                Q(result_publicity_release_date__year=year_int)
                | Q(
                    result_publicity_release_date__isnull=True,
                    requirement_approval_date__year=year_int,
                )
            )

        included_qs = queryset.filter(
            requirement_approval_date__isnull=False,
            result_publicity_release_date__isnull=False,
        )
        missing_start_qs = queryset.filter(
            requirement_approval_date__isnull=True,
            result_publicity_release_date__isnull=False,
        )
        missing_end_qs = queryset.filter(
            requirement_approval_date__isnull=False,
            result_publicity_release_date__isnull=True,
        )

        included_count = included_qs.count()
        missing_start_count = missing_start_qs.count()
        missing_end_count = missing_end_qs.count()

        # 为避免一次性返回过多记录，这里对每类明细做上限控制
        limit = 200

        def _serialize_record(item, reason):
            return {
                'code': getattr(item, 'procurement_code', ''),
                'name': getattr(item, 'project_name', ''),
                'project_code': getattr(item.project, 'project_code', '') if item.project_id else '',
                'project_name': getattr(item.project, 'project_name', '') if item.project_id else '',
                'procurement_method': getattr(item, 'procurement_method', '') or '',
                'responsible_person': getattr(item, 'procurement_officer', '') or '',
                'start_date': item.requirement_approval_date,
                'end_date': item.result_publicity_release_date,
                'reason': reason,
            }

        included = [
            _serialize_record(p, '字段完整，已纳入统计')
            for p in included_qs[:limit]
        ]
        missing_start = [
            _serialize_record(p, '缺少需求书审批完成日期（OA），未纳入统计')
            for p in missing_start_qs[:limit]
        ]
        missing_end = [
            _serialize_record(p, '缺少结果公示发布时间，未纳入统计')
            for p in missing_end_qs[:limit]
        ]

        return {
            'procurement': {
                'included_count': included_count,
                'missing_start_count': missing_start_count,
                'missing_end_count': missing_end_count,
                'total_excluded_count': missing_start_count + missing_end_count,
                'included': included,
                'missing_start': missing_start,
                'missing_end': missing_end,
            }
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
            # 与趋势图及采购列表保持一致：按结果公示发布时间过滤年度
            queryset = queryset.filter(result_publicity_release_date__year=int(year_filter))
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
                # 对于尚未公示结果的记录，仍按需求书审批日期归属年度
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
            # 对于尚未公示结果的记录，仍按需求书审批日期归属年度
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
        计算工作周期趋势（散点数据）
        
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
            list: [{'date': '2025-05-15', 'cycle_days': 35, 'code': 'CG-001', 'name': '...'}, ...]
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
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(**{f'{end_field}__year': int(year_filter)})

        # 计算工作周期并获取散点数据
        queryset = queryset.annotate(
            work_cycle=ExpressionWrapper(
                F(end_field) - F(start_field),
                output_field=fields.DurationField()
            )
        ).select_related('project')

        # 转换为散点数据格式
        scatter_data = []
        seen_ids = set()  # 使用集合追踪已处理的记录ID，防止重复
        
        for item in queryset:
            # 获取记录的唯一标识符（主键）
            record_id = item.pk
            
            # 如果这条记录已经被处理过，跳过
            if record_id in seen_ids:
                continue
            seen_ids.add(record_id)
            
            # 正确获取结束日期字段值
            if '__' in end_field:
                # 处理关联字段（如 procurement__result_publicity_release_date）
                parts = end_field.split('__')
                end_date_value = item
                for part in parts:
                    end_date_value = getattr(end_date_value, part, None)
                    if end_date_value is None:
                        break
            else:
                # 直接字段
                end_date_value = getattr(item, end_field, None)
            
            if not end_date_value:
                continue
                
            cycle_days = item.work_cycle.days if item.work_cycle else 0
            
            # 获取业务编码和名称，规范化经办人名称
            if model == Procurement:
                code = getattr(item, 'procurement_code', '')
                name = getattr(item, 'project_name', '')
                person_raw = getattr(item, 'procurement_officer', '')
            else:  # Contract
                code = getattr(item, 'contract_code', '')
                name = getattr(item, 'contract_name', '')
                person_raw = getattr(item, 'contract_officer', '')
            
            # 规范化经办人名称：去除前后空白
            person = person_raw.strip() if person_raw else ''
            
            scatter_data.append({
                'date': end_date_value.isoformat(),
                'cycle_days': cycle_days,
                'code': code,
                'name': name,
                'person': person,  # 使用规范化后的名称
                'project_code': item.project_id if hasattr(item, 'project_id') else '',
                'record_id': record_id  # 添加唯一标识符，便于前端调试
            })

        # 按日期排序
        scatter_data.sort(key=lambda x: x['date'])
        return scatter_data

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
            # 当按人查询时，必须确保经办人字段匹配且非空
            qs = qs.filter(
                procurement_officer=person_name
            ).exclude(procurement_officer='')
        if global_project:
            qs = qs.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            # 与采购列表保持一致：按结果公示发布时间过滤年度
            qs = qs.filter(result_publicity_release_date__year=int(year_filter))
        if procurement_method and procurement_method != 'all':
            qs = qs.filter(procurement_method=procurement_method)

        # 排序规则与采购管理列表保持一致：先按结果公示发布时间，再按开标日期和创建时间
        qs = qs.order_by('-result_publicity_release_date', '-bid_opening_date', '-created_at')[:limit]

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
            # 当按人查询时，必须确保经办人字段匹配且非空
            qs = qs.filter(
                contract_officer=person_name
            ).exclude(contract_officer='')
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
            # 与采购列表保持一致：按结果公示发布时间过滤年度
            queryset = queryset.filter(result_publicity_release_date__year=int(year_filter))
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
            # 与采购列表保持一致：按结果公示发布时间过滤年度
            procurement_qs = procurement_qs.filter(result_publicity_release_date__year=int(year_filter))
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
        获取多人趋势：按经办人分别计算采购/合同的散点数据
        返回: {
          'procurement': [{'name': '张三', 'points': [{date, cycle_days, ...}]}, ...],
          'contract': [{'name': '张三', 'points': [{date, cycle_days, ...}]}, ...]
        }
        
        注意：确保每个经办人只出现一次
        """
        # 选人（按业务量排序取前N名）
        person_list = self.get_person_list(year_filter=year_filter, global_project=project_filter, procurement_method=procurement_method)
        person_names = [p['name'] for p in person_list[:top_n]]

        # 逐人计算散点数据
        result = {'procurement': [], 'contract': []}
        
        # 用于跟踪已添加的人名，防止重复
        added_proc_names = set()
        added_cont_names = set()
        
        for name in person_names:
            # 采购数据
            if name not in added_proc_names:
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
                if t_p:
                    result['procurement'].append({
                        'name': name,
                        'points': t_p
                    })
                    added_proc_names.add(name)
            
            # 合同数据
            if name not in added_cont_names:
                t_c = self._calculate_trend(
                    model=Contract,
                    person_name=name,
                    year_filter=year_filter,
                    global_project=project_filter,
                    start_field='procurement__result_publicity_release_date',
                    end_field='signing_date',
                    person_field='contract_officer'
                )
                if t_c:
                    result['contract'].append({
                        'name': name,
                        'points': t_c
                    })
                    added_cont_names.add(name)
        
        return result

    def get_projects_multi_trend(self, year_filter=None, procurement_method=None, top_n=10):
        """
        获取多项目趋势：按项目分别计算采购/合同的散点数据（取前N个项目）
        
        注意：确保每个项目只出现一次
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

        # 计算散点数据
        result = {'procurement': [], 'contract': []}
        
        # 用于跟踪已添加的项目，防止重复
        added_proc_projects = set()
        added_cont_projects = set()
        
        for code in top_projects:
            # 采购数据
            if code not in added_proc_projects:
                t_p = self._calculate_trend(
                    model=Procurement,
                    project_code=code,
                    year_filter=year_filter,
                    procurement_method=procurement_method,
                    start_field='requirement_approval_date',
                    end_field='result_publicity_release_date'
                )
                if t_p:
                    result['procurement'].append({
                        'name': code,
                        'points': t_p
                    })
                    added_proc_projects.add(code)
            
            # 合同数据
            if code not in added_cont_projects:
                t_c = self._calculate_trend(
                    model=Contract,
                    project_code=code,
                    year_filter=year_filter,
                    start_field='procurement__result_publicity_release_date',
                    end_field='signing_date'
                )
                if t_c:
                    result['contract'].append({
                        'name': code,
                        'points': t_c
                    })
                    added_cont_projects.add(code)
        
        return result

    def get_project_officers_multi_trend(self, project_code, year_filter=None, procurement_method=None, top_n=10):
        """
        获取单个项目下经办人维度的散点数据：
        - 采购tab：各采购经办人的采购散点
        - 合同tab：各合同经办人的合同散点
        
        注意：确保每个经办人只出现一次，通过规范化名称去重
        """
        # 选人：该项目内前N名经办人
        p_qs = Procurement.objects.filter(project_id=project_code)
        if procurement_method and procurement_method != 'all':
            p_qs = p_qs.filter(procurement_method=procurement_method)
        p_names_raw = list(p_qs.values_list('procurement_officer', flat=True).distinct())
        
        c_names_raw = list(
            Contract.objects.filter(project_id=project_code, file_positioning=FilePositioning.MAIN_CONTRACT.value)
            .values_list('contract_officer', flat=True).distinct()
        )
        
        # 规范化并去重：去除空白、统一格式
        def normalize_names(names):
            """规范化名称列表：去空、去除前后空白、去重"""
            normalized = set()
            for name in names:
                if name:
                    cleaned = name.strip()
                    if cleaned:
                        normalized.add(cleaned)
            return list(normalized)
        
        p_names = normalize_names(p_names_raw)
        c_names = normalize_names(c_names_raw)

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

        result = {'procurement': [], 'contract': []}
        
        # 用于跟踪已添加的人名，防止重复
        added_proc_names = set()
        added_cont_names = set()
        
        for n in p_names:
            # 二次确认：确保不会添加重复的人名
            if n in added_proc_names:
                continue
                
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
            if t:
                result['procurement'].append({'name': n, 'points': t})
                added_proc_names.add(n)
        
        for n in c_names:
            # 二次确认：确保不会添加重复的人名
            if n in added_cont_names:
                continue
                
            t = self._calculate_trend(
                model=Contract,
                person_name=n,
                year_filter=year_filter,
                global_project=project_code,
                start_field='procurement__result_publicity_release_date',
                end_field='signing_date',
                person_field='contract_officer'
            )
            if t:
                result['contract'].append({'name': n, 'points': t})
                added_cont_names.add(n)
        
        return result
