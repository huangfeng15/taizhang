"""
归档统计服务
负责计算项目和个人的归档周期统计数据
"""
from datetime import datetime, timedelta
from django.db.models import Avg, Count, Q, F, ExpressionWrapper, fields
from django.db.models.functions import ExtractYear, ExtractMonth
from procurement.models import Procurement
from contract.models import Contract
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
            file_positioning='main_contract'  # 仅统计主合同
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
            queryset = queryset.filter(file_positioning='main_contract')

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
        """按月分组统计"""
        trend_data = []

        for month in range(1, 13):
            month_data = queryset.filter(business_month=month)
            count = month_data.count()

            if count > 0:
                avg_cycle_timedelta = month_data.aggregate(avg=Avg('archive_cycle'))['avg']
                avg_cycle = avg_cycle_timedelta.days if avg_cycle_timedelta else 0
            else:
                avg_cycle = None  # 无数据时返回None，前端可以断开折线

            trend_data.append({
                'period': f'{month}月',
                'avg_cycle': avg_cycle,
                'count': count
            })

        return trend_data

    def _group_by_half_year(self, queryset):
        """按半年分组统计"""
        trend_data = []

        # 获取数据的年份范围
        years = queryset.values_list('business_year', flat=True).distinct().order_by('business_year')

        for year in years:
            # 上半年（1-6月）
            h1_data = queryset.filter(business_year=year, business_month__lte=6)
            h1_count = h1_data.count()

            if h1_count > 0:
                h1_avg_timedelta = h1_data.aggregate(avg=Avg('archive_cycle'))['avg']
                h1_avg_cycle = h1_avg_timedelta.days if h1_avg_timedelta else 0
            else:
                h1_avg_cycle = None

            trend_data.append({
                'period': f'{year}-H1',
                'avg_cycle': h1_avg_cycle,
                'count': h1_count
            })

            # 下半年（7-12月）
            h2_data = queryset.filter(business_year=year, business_month__gt=6)
            h2_count = h2_data.count()

            if h2_count > 0:
                h2_avg_timedelta = h2_data.aggregate(avg=Avg('archive_cycle'))['avg']
                h2_avg_cycle = h2_avg_timedelta.days if h2_avg_timedelta else 0
            else:
                h2_avg_cycle = None

            trend_data.append({
                'period': f'{year}-H2',
                'avg_cycle': h2_avg_cycle,
                'count': h2_count
            })

        return trend_data

    def get_person_list(self, year_filter=None, global_project=None):
        """
        获取经办人列表（用于下拉选择器）

        Returns:
            list: [{'name': '张三', 'count': 10}, ...]
        """
        # 采购经办人
        procurement_officers = Procurement.objects.values('procurement_officer').annotate(
            count=Count('procurement_code')
        ).filter(procurement_officer__isnull=False)

        # 合同经办人
        contract_officers = Contract.objects.values('contract_officer').annotate(
            count=Count('contract_code')
        ).filter(contract_officer__isnull=False)

        # 应用筛选
        if year_filter and year_filter != 'all':
            procurement_officers = procurement_officers.filter(
                result_publicity_release_date__year=int(year_filter)
            )
            contract_officers = contract_officers.filter(
                signing_date__year=int(year_filter)
            )

        if global_project:
            procurement_officers = procurement_officers.filter(project_id=global_project)
            contract_officers = contract_officers.filter(project_id=global_project)

        # 合并去重
        person_dict = {}

        for item in procurement_officers:
            name = item['procurement_officer']
            person_dict[name] = person_dict.get(name, 0) + item['count']

        for item in contract_officers:
            name = item['contract_officer']
            person_dict[name] = person_dict.get(name, 0) + item['count']

        # 转换为列表并排序
        person_list = [
            {'name': name, 'count': count}
            for name, count in person_dict.items()
        ]
        person_list.sort(key=lambda x: x['count'], reverse=True)

        return person_list
