"""
归档统计服务
负责计算项目和个人的归档周期统计数据
"""
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count, Q, F, ExpressionWrapper, fields
from django.db.models.functions import ExtractYear, ExtractMonth
from procurement.models import Procurement
from contract.models import Contract
from project.enums import FilePositioning
from .config import ARCHIVE_RULES


class ArchiveStatisticsService:
    """归档统计服务类（遵循SRP原则）"""

    def __init__(self):
        self.procurement_deadline = ARCHIVE_RULES['procurement']['deadline_days']
        self.contract_deadline = ARCHIVE_RULES['contract']['deadline_days']

    def get_project_statistics(self, project_code, year_filter=None, global_project=None):
        """
        获取项目归档统计

        Args:
            project_code: 项目编码
            year_filter: 年份筛选（'all' 或具体年份）
            global_project: 全局项目筛选（项目视图下会被project_code覆盖）

        Returns:
            dict: {
                'procurement_avg_cycle': 采购平均归档周期,
                'contract_avg_cycle': 合同平均归档周期,
                'procurement_on_time_rate': 采购及时归档率,
                'contract_on_time_rate': 合同及时归档率,
                'procurement_trend': 采购趋势数据,
                'contract_trend': 合同趋势数据
            }
        """
        # 采购统计
        procurement_stats = self._calculate_procurement_statistics(
            project_code=project_code,
            year_filter=year_filter
        )

        # 合同统计
        contract_stats = self._calculate_contract_statistics(
            project_code=project_code,
            year_filter=year_filter
        )

        # 趋势数据
        procurement_trend = self._calculate_trend(
            model=Procurement,
            project_code=project_code,
            year_filter=year_filter,
            date_field='result_publicity_release_date',
            archive_field='archive_date'
        )

        contract_trend = self._calculate_trend(
            model=Contract,
            project_code=project_code,
            year_filter=year_filter,
            date_field='signing_date',
            archive_field='archive_date'
        )

        return {
            'procurement_avg_cycle': procurement_stats['avg_cycle'],
            'contract_avg_cycle': contract_stats['avg_cycle'],
            'procurement_on_time_rate': procurement_stats['on_time_rate'],
            'contract_on_time_rate': contract_stats['on_time_rate'],
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'procurement_count': procurement_stats['count'],
            'contract_count': contract_stats['count']
        }

    def get_person_statistics(self, person_name, year_filter=None, global_project=None):
        """
        获取个人归档统计

        Args:
            person_name: 经办人姓名
            year_filter: 年份筛选
            global_project: 全局项目筛选

        Returns:
            dict: 同 get_project_statistics
        """
        # 采购统计
        procurement_stats = self._calculate_procurement_statistics(
            person_name=person_name,
            year_filter=year_filter,
            global_project=global_project
        )

        # 合同统计
        contract_stats = self._calculate_contract_statistics(
            person_name=person_name,
            year_filter=year_filter,
            global_project=global_project
        )

        # 趋势数据
        procurement_trend = self._calculate_trend(
            model=Procurement,
            person_name=person_name,
            year_filter=year_filter,
            global_project=global_project,
            date_field='result_publicity_release_date',
            archive_field='archive_date',
            person_field='procurement_officer'
        )

        contract_trend = self._calculate_trend(
            model=Contract,
            person_name=person_name,
            year_filter=year_filter,
            global_project=global_project,
            date_field='signing_date',
            archive_field='archive_date',
            person_field='contract_officer'
        )

        return {
            'procurement_avg_cycle': procurement_stats['avg_cycle'],
            'contract_avg_cycle': contract_stats['avg_cycle'],
            'procurement_on_time_rate': procurement_stats['on_time_rate'],
            'contract_on_time_rate': contract_stats['on_time_rate'],
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'procurement_count': procurement_stats['count'],
            'contract_count': contract_stats['count']
        }

    def _calculate_procurement_statistics(self, project_code=None, person_name=None,
                                         year_filter=None, global_project=None):
        """计算采购归档统计"""
        queryset = Procurement.objects.filter(
            result_publicity_release_date__isnull=False,
            archive_date__isnull=False
        ).select_related('project')

        # 应用筛选
        if project_code:
            queryset = queryset.filter(project_id=project_code)
        if person_name:
            queryset = queryset.filter(procurement_officer=person_name)
        if global_project:
            queryset = queryset.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(result_publicity_release_date__year=int(year_filter))

        # 计算归档周期
        queryset = queryset.annotate(
            archive_cycle=ExpressionWrapper(
                F('archive_date') - F('result_publicity_release_date'),
                output_field=fields.DurationField()
            )
        )

        # 统计数据
        total_count = queryset.count()
        if total_count == 0:
            return {'avg_cycle': 0, 'on_time_rate': 0, 'count': 0}

        # 平均周期（转换为天数）
        avg_cycle_timedelta = queryset.aggregate(avg=Avg('archive_cycle'))['avg']
        avg_cycle = avg_cycle_timedelta.days if avg_cycle_timedelta else 0

        # 及时归档率
        on_time_count = queryset.filter(
            archive_cycle__lte=timedelta(days=self.procurement_deadline)
        ).count()
        on_time_rate = round(on_time_count / total_count * 100, 1) if total_count > 0 else 0

        return {
            'avg_cycle': avg_cycle,
            'on_time_rate': on_time_rate,
            'count': total_count
        }

    def _calculate_contract_statistics(self, project_code=None, person_name=None,
                                       year_filter=None, global_project=None):
        """计算合同归档统计"""
        queryset = Contract.objects.filter(
            signing_date__isnull=False,
            archive_date__isnull=False,
            file_positioning=FilePositioning.MAIN_CONTRACT.value  # 仅统计主合同
        ).select_related('project')

        # 应用筛选
        if project_code:
            queryset = queryset.filter(project_id=project_code)
        if person_name:
            queryset = queryset.filter(contract_officer=person_name)
        if global_project:
            queryset = queryset.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(signing_date__year=int(year_filter))

        # 计算归档周期
        queryset = queryset.annotate(
            archive_cycle=ExpressionWrapper(
                F('archive_date') - F('signing_date'),
                output_field=fields.DurationField()
            )
        )

        # 统计数据
        total_count = queryset.count()
        if total_count == 0:
            return {'avg_cycle': 0, 'on_time_rate': 0, 'count': 0}

        # 平均周期（转换为天数）
        avg_cycle_timedelta = queryset.aggregate(avg=Avg('archive_cycle'))['avg']
        avg_cycle = avg_cycle_timedelta.days if avg_cycle_timedelta else 0

        # 及时归档率
        on_time_count = queryset.filter(
            archive_cycle__lte=timedelta(days=self.contract_deadline)
        ).count()
        on_time_rate = round(on_time_count / total_count * 100, 1) if total_count > 0 else 0

        return {
            'avg_cycle': avg_cycle,
            'on_time_rate': on_time_rate,
            'count': total_count
        }

    def _calculate_trend(self, model, project_code=None, person_name=None,
                        year_filter=None, global_project=None,
                        date_field='', archive_field='', person_field=None):
        """
        计算归档周期趋势

        Args:
            model: 模型类（Procurement 或 Contract）
            project_code: 项目编码
            person_name: 经办人姓名
            year_filter: 年份筛选
            global_project: 全局项目筛选
            date_field: 业务日期字段名
            archive_field: 归档日期字段名
            person_field: 经办人字段名

        Returns:
            list: [{'period': '2024-H1', 'avg_cycle': 25.5}, ...]
        """
        queryset = model.objects.filter(
            **{f'{date_field}__isnull': False, f'{archive_field}__isnull': False}
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

        # 计算归档周期
        queryset = queryset.annotate(
            archive_cycle=ExpressionWrapper(
                F(archive_field) - F(date_field),
                output_field=fields.DurationField()
            ),
            business_year=ExtractYear(date_field),
            business_month=ExtractMonth(date_field)
        )

        # 判断分组方式
        if year_filter and year_filter != 'all':
            # 单年度：按月分组
            queryset = queryset.filter(**{f'{date_field}__year': int(year_filter)})
            trend_data = self._group_by_month(queryset)
        else:
            # 全年度：按半年分组
            trend_data = self._group_by_half_year(queryset)

        return trend_data

    def _group_by_month(self, queryset):
        """委托公共实现，保持对外行为不变（DRY）。"""
        from .utils.time_grouping import group_by_month
        return group_by_month(queryset, cycle_field='archive_cycle')

    def _group_by_half_year(self, queryset):
        """委托公共实现，保持对外行为不变（DRY）。"""
        from .utils.time_grouping import group_by_half_year
        return group_by_half_year(queryset, cycle_field='archive_cycle')

    def get_person_list(self, year_filter=None, global_project=None):
        """
        获取经办人列表（用于下拉选择器），委托公共实现，行为不变。
        """
        from .utils.persons import get_person_list as _get_persons
        return _get_persons(year_filter=year_filter, global_project=global_project)

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

    def get_persons_multi_trend(self, year_filter=None, project_filter=None, top_n=10):
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
        person_list = self.get_person_list(year_filter=year_filter, global_project=project_filter)
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
                date_field='result_publicity_release_date',
                archive_field='archive_date',
                person_field='procurement_officer'
            )
            t_c = self._calculate_trend(
                model=Contract,
                person_name=name,
                year_filter=year_filter,
                global_project=project_filter,
                date_field='signing_date',
                archive_field='archive_date',
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

    def get_projects_multi_trend(self, year_filter=None, top_n=10):
        """
        获取多项目趋势：按项目分别计算采购/合同的趋势，多条折线合并显示（取前N个项目）。
        只显示至少有一个项目有数据的时间段。
        """
        from project.models import Project
        projects = list(Project.objects.all())
        # 简化：依据合同+采购总量排序
        scored = []
        for p in projects:
            p_total = self._get_procurement_total_count(project_code=p.project_code, year_filter=year_filter)
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
                date_field='result_publicity_release_date',
                archive_field='archive_date'
            )
            t_c = self._calculate_trend(
                model=Contract,
                project_code=code,
                year_filter=year_filter,
                date_field='signing_date',
                archive_field='archive_date'
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

    def get_project_officers_multi_trend(self, project_code, year_filter=None, top_n=10):
        """
        获取单个项目下经办人维度的趋势：
        - 采购tab：各采购经办人的采购趋势
        - 合同tab：各合同经办人的合同趋势
        """
        # 选人：该项目内前N名经办人
        p_names = list(
            Procurement.objects.filter(project_id=project_code)
            .values_list('procurement_officer', flat=True).distinct()
        )
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
                    cnt = self._get_procurement_total_count(person_name=n, year_filter=year_filter, global_project=project_code)
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
                date_field='result_publicity_release_date',
                archive_field='archive_date',
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
                date_field='signing_date',
                archive_field='archive_date',
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

    def get_projects_archive_overview(self, year_filter=None, project_filter=None):
        """
        获取项目维度的归档概览
        
        Args:
            year_filter: str - 年度筛选（'all' 或具体年份）
            project_filter: str or None - 项目编码筛选
        
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
        total_procurement_archived = 0
        total_contract_count = 0
        total_contract_archived = 0
        
        for project in projects_qs:
            # 计算该项目的采购统计
            procurement_stats = self._calculate_procurement_statistics(
                project_code=project.project_code,
                year_filter=year_filter
            )
            
            # 计算该项目的合同统计
            contract_stats = self._calculate_contract_statistics(
                project_code=project.project_code,
                year_filter=year_filter
            )
            
            # 获取采购和合同的总数（包括未归档的）
            procurement_total = self._get_procurement_total_count(
                project_code=project.project_code,
                year_filter=year_filter
            )
            contract_total = self._get_contract_total_count(
                project_code=project.project_code,
                year_filter=year_filter
            )
            
            # 计算综合归档率
            total_items = procurement_total + contract_total
            archived_items = procurement_stats['count'] + contract_stats['count']
            overall_archive_rate = round(archived_items / total_items * 100, 1) if total_items > 0 else 0
            
            projects_data.append({
                'project_code': project.project_code,
                'project_name': project.project_name,
                'procurement_count': procurement_total,
                'procurement_archived': procurement_stats['count'],
                'procurement_avg_cycle': procurement_stats['avg_cycle'],
                'procurement_on_time_rate': procurement_stats['on_time_rate'],
                'contract_count': contract_total,
                'contract_archived': contract_stats['count'],
                'contract_avg_cycle': contract_stats['avg_cycle'],
                'contract_on_time_rate': contract_stats['on_time_rate'],
                'overall_archive_rate': overall_archive_rate
            })
            
            # 累加到汇总数据
            total_procurement_count += procurement_total
            total_procurement_archived += procurement_stats['count']
            total_contract_count += contract_total
            total_contract_archived += contract_stats['count']
        
        # 按综合归档率降序排序
        projects_data.sort(key=lambda x: x['overall_archive_rate'], reverse=True)
        
        # 计算汇总统计
        total_all = total_procurement_count + total_contract_count
        archived_all = total_procurement_archived + total_contract_archived
        overall_rate = round(archived_all / total_all * 100, 1) if total_all > 0 else 0
        
        summary = {
            'project_count': len(projects_data),
            'procurement_total': total_procurement_count,
            'procurement_archived': total_procurement_archived,
            'contract_total': total_contract_count,
            'contract_archived': total_contract_archived,
            'overall_archive_rate': overall_rate
        }
        
        return {
            'summary': summary,
            'projects': projects_data
        }

    def get_persons_archive_overview(self, year_filter=None, project_filter=None):
        """
        获取个人维度的归档概览
        
        Args:
            year_filter: str - 年度筛选
            project_filter: str or None - 项目筛选（影响经办人范围）
        
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
            procurement_qs = procurement_qs.filter(result_publicity_release_date__year=int(year_filter))
        if project_filter:
            procurement_qs = procurement_qs.filter(project_id=project_filter)
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
        total_procurement_archived = 0
        total_contract_count = 0
        total_contract_archived = 0
        
        for person_name in person_names:
            # 计算该经办人的采购统计
            procurement_stats = self._calculate_procurement_statistics(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter
            )
            
            # 计算该经办人的合同统计
            contract_stats = self._calculate_contract_statistics(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter
            )
            
            # 获取总数（包括未归档的）
            procurement_total = self._get_procurement_total_count(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter
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
            
            # 计算综合归档率
            total_items = procurement_total + contract_total
            archived_items = procurement_stats['count'] + contract_stats['count']
            overall_archive_rate = round(archived_items / total_items * 100, 1) if total_items > 0 else 0
            
            persons_data.append({
                'handler_name': person_name,
                'procurement_count': procurement_total,
                'procurement_archived': procurement_stats['count'],
                'procurement_avg_cycle': procurement_stats['avg_cycle'],
                'procurement_on_time_rate': procurement_stats['on_time_rate'],
                'contract_count': contract_total,
                'contract_archived': contract_stats['count'],
                'contract_avg_cycle': contract_stats['avg_cycle'],
                'contract_on_time_rate': contract_stats['on_time_rate'],
                'overall_archive_rate': overall_archive_rate,
                'project_count': project_count
            })
            
            # 累加到汇总数据
            total_procurement_count += procurement_total
            total_procurement_archived += procurement_stats['count']
            total_contract_count += contract_total
            total_contract_archived += contract_stats['count']
        
        # 按综合归档率降序排序
        persons_data.sort(key=lambda x: x['overall_archive_rate'], reverse=True)
        
        # 计算汇总统计
        total_all = total_procurement_count + total_contract_count
        archived_all = total_procurement_archived + total_contract_archived
        overall_rate = round(archived_all / total_all * 100, 1) if total_all > 0 else 0
        
        summary = {
            'person_count': len(persons_data),
            'procurement_total': total_procurement_count,
            'procurement_archived': total_procurement_archived,
            'contract_total': total_contract_count,
            'contract_archived': total_contract_archived,
            'overall_archive_rate': overall_rate
        }
        
        return {
            'summary': summary,
            'persons': persons_data
        }

    def get_all_persons_trend_and_problems(self, year_filter=None, project_filter=None, show_all=False):
        """
        获取所有经办人的汇总趋势图和超期记录（用于个人视图主页面）
        
        Args:
            year_filter: 年度筛选
            project_filter: 项目筛选
        
        Returns:
            dict: {
                'procurement_trend': [...],  # 所有经办人的采购平均周期
                'contract_trend': [...],     # 所有经办人的合同平均周期
                'problems': {...}            # 所有经办人的超期记录汇总
            }
        """
        from .archive_problem_detector import ArchiveProblemDetector
        
        # 计算所有经办人的汇总趋势
        procurement_trend = self._calculate_trend(
            model=Procurement,
            year_filter=year_filter,
            global_project=project_filter,
            date_field='result_publicity_release_date',
            archive_field='archive_date'
        )
        
        contract_trend = self._calculate_trend(
            model=Contract,
            year_filter=year_filter,
            global_project=project_filter,
            date_field='signing_date',
            archive_field='archive_date'
        )
        
        # 获取超期记录
        detector = ArchiveProblemDetector()
        filters = {}
        if year_filter and year_filter != 'all':
            filters['year_filter'] = int(year_filter)
        if project_filter:
            filters['project'] = project_filter
        
        problems = detector.detect_problems(filters=filters, show_all=show_all)
        
        return {
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'problems': problems
        }

    def get_project_trend_and_problems(self, project_code, year_filter=None, show_all=False):
        """
        获取单个项目的趋势图和超期记录
        
        Args:
            project_code: 项目编码
            year_filter: 年度筛选
        
        Returns:
            dict: {
                'procurement_trend': [...],
                'contract_trend': [...],
                'problems': {...}
            }
        """
        from .archive_problem_detector import ArchiveProblemDetector
        
        # 计算趋势数据
        procurement_trend = self._calculate_trend(
            model=Procurement,
            project_code=project_code,
            year_filter=year_filter,
            date_field='result_publicity_release_date',
            archive_field='archive_date'
        )
        
        contract_trend = self._calculate_trend(
            model=Contract,
            project_code=project_code,
            year_filter=year_filter,
            date_field='signing_date',
            archive_field='archive_date'
        )

        # 统计概要（含总数与及时率）
        p_stats = self._calculate_procurement_statistics(
            project_code=project_code,
            year_filter=year_filter,
        )
        c_stats = self._calculate_contract_statistics(
            project_code=project_code,
            year_filter=year_filter,
        )
        p_total = self._get_procurement_total_count(
            project_code=project_code,
            year_filter=year_filter,
        )
        c_total = self._get_contract_total_count(
            project_code=project_code,
            year_filter=year_filter,
        )
        total_items = p_total + c_total
        archived_items = p_stats['count'] + c_stats['count']
        overall_rate = round(archived_items / total_items * 100, 1) if total_items > 0 else 0

        summary = {
            'procurement': {
                'count_total': p_total,
                'count_archived': p_stats['count'],
                'avg_cycle': p_stats['avg_cycle'],
                'on_time_rate': p_stats['on_time_rate'],
            },
            'contract': {
                'count_total': c_total,
                'count_archived': c_stats['count'],
                'avg_cycle': c_stats['avg_cycle'],
                'on_time_rate': c_stats['on_time_rate'],
            },
            'overall_archive_rate': overall_rate,
        }

        # 详细记录（上限限制避免过大负载）
        records = {
            'procurements': self._get_procurement_records(
                project_code=project_code,
                year_filter=year_filter,
                limit=200,
            ),
            'contracts': self._get_contract_records(
                project_code=project_code,
                year_filter=year_filter,
                limit=200,
            ),
        }
        
        # 获取超期记录
        detector = ArchiveProblemDetector()
        filters = {'project': project_code}
        if year_filter and year_filter != 'all':
            filters['year_filter'] = int(year_filter)
        
        problems = detector.detect_problems(filters=filters, show_all=show_all)
        
        return {
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'problems': problems,
            'summary': summary,
            'records': records,
        }

    def get_person_trend_and_problems(self, person_name, year_filter=None, project_filter=None, show_all=False):
        """
        获取单个经办人的趋势图和超期记录（用于查看详情时）
        
        Args:
            person_name: 经办人姓名
            year_filter: 年度筛选
            project_filter: 项目筛选
        
        Returns:
            dict: {
                'procurement_trend': [...],
                'contract_trend': [...],
                'problems': {...}
            }
        """
        from .archive_problem_detector import ArchiveProblemDetector
        
        # 计算趋势数据
        procurement_trend = self._calculate_trend(
            model=Procurement,
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
            date_field='result_publicity_release_date',
            archive_field='archive_date',
            person_field='procurement_officer'
        )
        
        contract_trend = self._calculate_trend(
            model=Contract,
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
            date_field='signing_date',
            archive_field='archive_date',
            person_field='contract_officer'
        )

        # 统计概要（含总数与及时率）
        p_stats = self._calculate_procurement_statistics(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
        )
        c_stats = self._calculate_contract_statistics(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
        )
        p_total = self._get_procurement_total_count(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
        )
        c_total = self._get_contract_total_count(
            person_name=person_name,
            year_filter=year_filter,
            global_project=project_filter,
        )
        total_items = p_total + c_total
        archived_items = p_stats['count'] + c_stats['count']
        overall_rate = round(archived_items / total_items * 100, 1) if total_items > 0 else 0

        summary = {
            'procurement': {
                'count_total': p_total,
                'count_archived': p_stats['count'],
                'avg_cycle': p_stats['avg_cycle'],
                'on_time_rate': p_stats['on_time_rate'],
            },
            'contract': {
                'count_total': c_total,
                'count_archived': c_stats['count'],
                'avg_cycle': c_stats['avg_cycle'],
                'on_time_rate': c_stats['on_time_rate'],
            },
            'overall_archive_rate': overall_rate,
        }

        # 详细记录（上限限制避免过大负载）
        records = {
            'procurements': self._get_procurement_records(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter,
                limit=200,
            ),
            'contracts': self._get_contract_records(
                person_name=person_name,
                year_filter=year_filter,
                global_project=project_filter,
                limit=200,
            ),
        }
        
        # 获取超期记录
        detector = ArchiveProblemDetector()
        filters = {'responsible_person': person_name}
        if year_filter and year_filter != 'all':
            filters['year_filter'] = int(year_filter)
        if project_filter:
            filters['project'] = project_filter
        
        problems = detector.detect_problems(filters=filters, show_all=show_all)
        
        return {
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'problems': problems,
            'summary': summary,
            'records': records,
        }

    def _get_procurement_records(self, project_code=None, person_name=None,
                                 year_filter=None, global_project=None,
                                 limit=200):
        """获取采购归档记录明细（包含已归档与未归档，按业务日期倒序，限制条数）"""
        qs = Procurement.objects.select_related('project').all()

        if project_code:
            qs = qs.filter(project_id=project_code)
        if person_name:
            qs = qs.filter(procurement_officer=person_name)
        if global_project:
            qs = qs.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            qs = qs.filter(result_publicity_release_date__year=int(year_filter))

        qs = qs.order_by('-result_publicity_release_date')[:limit]

        today = timezone.now().date()
        records = []
        for item in qs:
            business_date = item.result_publicity_release_date
            archive_date = item.archive_date
            deadline_days = self.procurement_deadline
            archive_deadline = (business_date + timedelta(days=deadline_days)) if business_date else None
            cycle_days = None
            overdue_days = 0
            on_time = None

            if business_date and archive_date:
                cycle_days = (archive_date - business_date).days
                on_time = cycle_days <= deadline_days
                if archive_deadline:
                    overdue_days = max((archive_date - archive_deadline).days, 0)
            elif business_date and archive_deadline:
                overdue_days = max((today - archive_deadline).days, 0)

            records.append({
                'module': 'procurement',
                'code': getattr(item, 'procurement_code', ''),
                'name': getattr(item, 'project_name', ''),
                'responsible_person': getattr(item, 'procurement_officer', '') or '',
                'business_date': business_date,
                'archive_deadline': archive_deadline,
                'archive_date': archive_date,
                'cycle_days': cycle_days,
                'on_time': on_time,
                'overdue_days': overdue_days,
            })

        return records

    def _get_contract_records(self, project_code=None, person_name=None,
                               year_filter=None, global_project=None,
                               limit=200):
        """获取合同归档记录明细（仅主合同；包含已归档与未归档，按签订日期倒序，限制条数）"""
        qs = Contract.objects.select_related('project').filter(
            file_positioning=FilePositioning.MAIN_CONTRACT.value
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
        records = []
        for item in qs:
            business_date = item.signing_date
            archive_date = item.archive_date
            deadline_days = self.contract_deadline
            archive_deadline = (business_date + timedelta(days=deadline_days)) if business_date else None
            cycle_days = None
            overdue_days = 0
            on_time = None

            if business_date and archive_date:
                cycle_days = (archive_date - business_date).days
                on_time = cycle_days <= deadline_days
                if archive_deadline:
                    overdue_days = max((archive_date - archive_deadline).days, 0)
            elif business_date and archive_deadline:
                overdue_days = max((today - archive_deadline).days, 0)

            records.append({
                'module': 'contract',
                'code': getattr(item, 'contract_code', ''),
                'contract_sequence': getattr(item, 'contract_sequence', '') or '',
                'name': getattr(item, 'contract_name', ''),
                'responsible_person': getattr(item, 'contract_officer', '') or '',
                'business_date': business_date,
                'archive_deadline': archive_deadline,
                'archive_date': archive_date,
                'cycle_days': cycle_days,
                'on_time': on_time,
                'overdue_days': overdue_days if overdue_days > 0 else 0,
            })

        return records

    def _get_procurement_total_count(self, project_code=None, person_name=None,
                                     year_filter=None, global_project=None):
        """获取采购总数（包括未归档的）"""
        queryset = Procurement.objects.filter(result_publicity_release_date__isnull=False)
        
        if project_code:
            queryset = queryset.filter(project_id=project_code)
        if person_name:
            queryset = queryset.filter(procurement_officer=person_name)
        if global_project:
            queryset = queryset.filter(project_id=global_project)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(result_publicity_release_date__year=int(year_filter))
        
        return queryset.count()

    def _get_contract_total_count(self, project_code=None, person_name=None,
                                  year_filter=None, global_project=None):
        """获取合同总数（包括未归档的，仅主合同）"""
        queryset = Contract.objects.filter(
            signing_date__isnull=False,
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
