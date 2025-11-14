"""
更新监控统计服务
参照归档监控页面的成功设计模式，实现双视图架构的更新监控统计功能
"""
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.db.models import Count, Q, F, ExpressionWrapper, fields, Avg
from django.db.models.functions import ExtractYear, ExtractMonth
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement
from project.enums import FilePositioning


class UpdateStatisticsService:
    """更新监控统计服务类（参照ArchiveStatisticsService的设计模式）"""

    def __init__(self, start_date=None):
        """
        初始化更新规则（次月月底准时规则）
        
        Args:
            start_date: 起始日期，只统计该日期之后的业务数据
        """
        self.today = timezone.now().date()
        self.start_date = start_date

    def _calculate_update_deadline(self, business_date):
        """
        计算更新截止日期（次月月底）
        参照update_problem_detector的实现
        """
        if not business_date:
            return None
            
        if business_date.month == 12:
            next_month = date(business_date.year + 1, 1, 1)
        else:
            next_month = date(business_date.year, business_date.month + 1, 1)

        # 次月最后一天
        if next_month.month == 12:
            deadline = date(next_month.year, 12, 31)
        else:
            deadline = date(next_month.year, next_month.month + 1, 1) - timedelta(days=1)

        return deadline

    def get_projects_update_overview(self, year_filter=None, project_filter=None, start_date=None):
        """
        获取项目维度的更新监控概览
        【完全参照归档监控的get_projects_archive_overview方法】
        
        Args:
            year_filter: str - 年度筛选（'all' 或具体年份）
            project_filter: str or None - 项目编码筛选
            start_date: date - 起始日期筛选
        
        Returns:
            dict: {
                'summary': {汇总统计},
                'projects': [{项目列表}]
            }
        """
        # 更新起始日期
        if start_date:
            self.start_date = start_date
        from project.models import Project
        
        # 获取项目列表
        projects_qs = Project.objects.all()
        if project_filter:
            projects_qs = projects_qs.filter(project_code=project_filter)
        
        projects_data = []
        
        # 汇总统计初始化
        total_stats = {
            'procurement': {'total': 0, 'updated': 0, 'on_time': 0},
            'contract': {'total': 0, 'updated': 0, 'on_time': 0},
            'payment': {'total': 0, 'updated': 0, 'on_time': 0},
            'settlement': {'total': 0, 'updated': 0, 'on_time': 0},
        }
        
        for project in projects_qs:
            # 计算该项目各模块的更新统计
            procurement_stats = self._calculate_module_update_stats(
                module='procurement',
                project_code=project.project_code,
                year_filter=year_filter
            )
            contract_stats = self._calculate_module_update_stats(
                module='contract',
                project_code=project.project_code,
                year_filter=year_filter
            )
            payment_stats = self._calculate_module_update_stats(
                module='payment',
                project_code=project.project_code,
                year_filter=year_filter
            )
            settlement_stats = self._calculate_module_update_stats(
                module='settlement',
                project_code=project.project_code,
                year_filter=year_filter
            )
            
            # 计算综合准时率
            total_count = (procurement_stats['total'] + contract_stats['total'] + 
                          payment_stats['total'] + settlement_stats['total'])
            on_time_count = (procurement_stats['on_time'] + contract_stats['on_time'] + 
                           payment_stats['on_time'] + settlement_stats['on_time'])
            overall_on_time_rate = round(on_time_count / total_count * 100, 1) if total_count > 0 else 0
            
            projects_data.append({
                'project_code': project.project_code,
                'project_name': project.project_name,
                'procurement_count': procurement_stats['total'],
                'procurement_updated': procurement_stats['updated'],
                'procurement_on_time_rate': procurement_stats['on_time_rate'],
                'procurement_avg_days': procurement_stats['avg_days'],
                'contract_count': contract_stats['total'],
                'contract_updated': contract_stats['updated'],
                'contract_on_time_rate': contract_stats['on_time_rate'],
                'contract_avg_days': contract_stats['avg_days'],
                'payment_count': payment_stats['total'],
                'payment_updated': payment_stats['updated'],
                'payment_on_time_rate': payment_stats['on_time_rate'],
                'payment_avg_days': payment_stats['avg_days'],
                'settlement_count': settlement_stats['total'],
                'settlement_updated': settlement_stats['updated'],
                'settlement_on_time_rate': settlement_stats['on_time_rate'],
                'settlement_avg_days': settlement_stats['avg_days'],
                'overall_on_time_rate': overall_on_time_rate
            })
            
            # 累加到汇总统计
            for module_name, stats in [
                ('procurement', procurement_stats),
                ('contract', contract_stats),
                ('payment', payment_stats),
                ('settlement', settlement_stats)
            ]:
                total_stats[module_name]['total'] += stats['total']
                total_stats[module_name]['updated'] += stats['updated']
                total_stats[module_name]['on_time'] += stats['on_time']
        
        # 按综合准时率降序排序
        projects_data.sort(key=lambda x: x['overall_on_time_rate'], reverse=True)
        
        # 计算汇总统计
        summary = self._build_summary(total_stats, len(projects_data))
        
        return {
            'summary': summary,
            'projects': projects_data
        }

    def get_persons_update_overview(self, year_filter=None, project_filter=None, start_date=None):
        """
        获取个人维度的更新监控概览
        【完全参照归档监控的get_persons_archive_overview方法】
        
        Args:
            year_filter: str - 年度筛选
            project_filter: str or None - 项目筛选（影响经办人范围）
            start_date: date - 起始日期筛选
        
        Returns:
            dict: {
                'summary': {汇总统计},
                'persons': [{经办人列表}]
            }
        """
        # 更新起始日期
        if start_date:
            self.start_date = start_date
        # 获取所有经办人名单
        person_names = self._get_all_persons(year_filter, project_filter)
        
        persons_data = []
        
        # 汇总统计初始化
        total_stats = {
            'procurement': {'total': 0, 'updated': 0, 'on_time': 0},
            'contract': {'total': 0, 'updated': 0, 'on_time': 0},
            'payment': {'total': 0, 'updated': 0, 'on_time': 0},
            'settlement': {'total': 0, 'updated': 0, 'on_time': 0},
        }
        
        for person_name in person_names:
            # 计算该经办人各模块的更新统计
            procurement_stats = self._calculate_module_update_stats(
                module='procurement',
                person_name=person_name,
                year_filter=year_filter,
                project_filter=project_filter
            )
            contract_stats = self._calculate_module_update_stats(
                module='contract',
                person_name=person_name,
                year_filter=year_filter,
                project_filter=project_filter
            )
            payment_stats = self._calculate_module_update_stats(
                module='payment',
                person_name=person_name,
                year_filter=year_filter,
                project_filter=project_filter
            )
            settlement_stats = self._calculate_module_update_stats(
                module='settlement',
                person_name=person_name,
                year_filter=year_filter,
                project_filter=project_filter
            )
            
            # 计算负责的项目数
            project_count = self._get_person_project_count(
                person_name, year_filter, project_filter
            )
            
            # 计算综合准时率
            total_count = (procurement_stats['total'] + contract_stats['total'] + 
                          payment_stats['total'] + settlement_stats['total'])
            on_time_count = (procurement_stats['on_time'] + contract_stats['on_time'] + 
                           payment_stats['on_time'] + settlement_stats['on_time'])
            overall_on_time_rate = round(on_time_count / total_count * 100, 1) if total_count > 0 else 0
            
            persons_data.append({
                'person_name': person_name,
                'procurement_count': procurement_stats['total'],
                'procurement_updated': procurement_stats['updated'],
                'procurement_on_time_rate': procurement_stats['on_time_rate'],
                'procurement_avg_days': procurement_stats['avg_days'],
                'contract_count': contract_stats['total'],
                'contract_updated': contract_stats['updated'],
                'contract_on_time_rate': contract_stats['on_time_rate'],
                'contract_avg_days': contract_stats['avg_days'],
                'payment_count': payment_stats['total'],
                'payment_updated': payment_stats['updated'],
                'payment_on_time_rate': payment_stats['on_time_rate'],
                'payment_avg_days': payment_stats['avg_days'],
                'settlement_count': settlement_stats['total'],
                'settlement_updated': settlement_stats['updated'],
                'settlement_on_time_rate': settlement_stats['on_time_rate'],
                'settlement_avg_days': settlement_stats['avg_days'],
                'overall_on_time_rate': overall_on_time_rate,
                'project_count': project_count,
                'business_total': total_count
            })
            
            # 累加到汇总统计
            for module_name, stats in [
                ('procurement', procurement_stats),
                ('contract', contract_stats),
                ('payment', payment_stats),
                ('settlement', settlement_stats)
            ]:
                total_stats[module_name]['total'] += stats['total']
                total_stats[module_name]['updated'] += stats['updated']
                total_stats[module_name]['on_time'] += stats['on_time']
        
        # 按综合准时率降序排序
        persons_data.sort(key=lambda x: x['overall_on_time_rate'], reverse=True)
        
        # 计算汇总统计
        summary = self._build_summary(total_stats, len(persons_data), is_person_view=True)
        
        return {
            'summary': summary,
            'persons': persons_data
        }

    def _calculate_module_update_stats(self, module, project_code=None, person_name=None,
                                      year_filter=None, project_filter=None):
        """
        计算单个模块的更新统计
        
        Returns:
            dict: {
                'total': 总数,
                'updated': 已更新数,
                'on_time': 准时数,
                'on_time_rate': 准时率,
                'avg_days': 平均更新天数
            }
        """
        # 根据模块获取对应的模型和字段配置
        config = self._get_module_config(module)
        if not config:
            return self._empty_stats()
        
        # 构建查询集
        queryset = config['model'].objects.filter(
            **{f"{config['business_date_field']}__isnull": False}
        )
        
        # 应用起始日期筛选（优先级最高）
        if self.start_date:
            queryset = queryset.filter(**{f"{config['business_date_field']}__gte": self.start_date})
        
        # 应用筛选条件
        if project_code:
            queryset = queryset.filter(**{config['project_field']: project_code})
        if person_name and config.get('person_field'):
            queryset = queryset.filter(**{config['person_field']: person_name})
        if project_filter:
            queryset = queryset.filter(**{config['project_field']: project_filter})
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(**{f"{config['business_date_field']}__year": int(year_filter)})
        
        # 合同只统计主合同
        if module == 'contract':
            queryset = queryset.filter(file_positioning=FilePositioning.MAIN_CONTRACT.value)
        
        total_count = queryset.count()
        if total_count == 0:
            return self._empty_stats()
        
        # 计算更新天数和准时情况
        on_time_count = 0
        update_days_list = []
        
        for item in queryset:
            business_date = getattr(item, config['business_date_field'])
            update_date = getattr(item, config['update_date_field'], None)
            
            if not business_date:
                continue
                
            # 计算截止日期
            deadline = self._calculate_update_deadline(business_date)
            if not deadline:
                continue
            
            # 如果有更新日期，使用更新日期；否则使用创建日期
            if not update_date:
                update_date = getattr(item, 'created_at', None)
                if update_date:
                    update_date = update_date.date()
            elif hasattr(update_date, 'date'):
                update_date = update_date.date()
            
            if update_date:
                # 计算更新天数
                update_days = (update_date - business_date).days
                update_days_list.append(update_days)
                
                # 判断是否准时（更新日期 <= 截止日期）
                if update_date <= deadline:
                    on_time_count += 1
        
        # 计算统计数据
        updated_count = len(update_days_list)
        on_time_rate = round(on_time_count / updated_count * 100, 1) if updated_count > 0 else 0
        avg_days = round(sum(update_days_list) / len(update_days_list), 1) if update_days_list else 0
        
        return {
            'total': total_count,
            'updated': updated_count,
            'on_time': on_time_count,
            'on_time_rate': on_time_rate,
            'avg_days': avg_days
        }

    def _calculate_module_update_trend(self, module, project_code=None, person_name=None,
                                      year_filter=None, project_filter=None):
        """计算单个模块的更新周期趋势数据。

        返回形式与归档监控的趋势数据保持一致，例如：
        [{'month': 1, 'period': '1月', 'avg_cycle': 3.5, 'count': 10}, ...]
        """
        config = self._get_module_config(module)
        if not config:
            return []

        model = config["model"]
        business_field = config["business_date_field"]
        update_field = config["update_date_field"]

        # 基础查询：只统计有业务日期的记录
        queryset = model.objects.filter(**{f"{business_field}__isnull": False})

        # 应用起始日期筛选（保持与统计概览一致）
        if self.start_date:
            queryset = queryset.filter(**{f"{business_field}__gte": self.start_date})

        # 维度筛选
        if project_code:
            queryset = queryset.filter(**{config["project_field"]: project_code})
        if person_name and config.get("person_field"):
            queryset = queryset.filter(**{config["person_field"]: person_name})
        if project_filter:
            queryset = queryset.filter(**{config["project_field"]: project_filter})

        # 合同仅统计主合同
        if module == "contract":
            queryset = queryset.filter(file_positioning=FilePositioning.MAIN_CONTRACT.value)

        # 仅统计已经有更新日期的数据
        queryset = queryset.filter(**{f"{update_field}__isnull": False})
        if not queryset.exists():
            return []

        # 标注业务年份、月份以及“更新周期”
        queryset = queryset.annotate(
            update_cycle=ExpressionWrapper(
                F(update_field) - F(business_field),
                output_field=fields.DurationField(),
            ),
            business_year=ExtractYear(business_field),
            business_month=ExtractMonth(business_field),
        )

        # 根据 year_filter 选择按月或按半年度分组
        from .utils.time_grouping import group_by_month, group_by_half_year

        if year_filter and year_filter != "all":
            queryset = queryset.filter(**{f"{business_field}__year": int(year_filter)})
            return group_by_month(queryset, cycle_field="update_cycle")

        return group_by_half_year(queryset, cycle_field="update_cycle")

    def _get_module_config(self, module):
        """获取模块配置"""
        configs = {
            'procurement': {
                'model': Procurement,
                'business_date_field': 'result_publicity_release_date',
                'update_date_field': 'updated_at',
                'project_field': 'project_id',
                'person_field': 'procurement_officer'
            },
            'contract': {
                'model': Contract,
                'business_date_field': 'signing_date',
                'update_date_field': 'updated_at',
                'project_field': 'project_id',
                'person_field': 'contract_officer'
            },
            'payment': {
                'model': Payment,
                'business_date_field': 'payment_date',
                'update_date_field': 'updated_at',
                'project_field': 'contract__project_id',
                'person_field': None  # 支付没有直接的经办人字段
            },
            'settlement': {
                'model': Settlement,
                'business_date_field': 'completion_date',
                'update_date_field': 'updated_at',
                'project_field': 'main_contract__project_id',
                'person_field': None  # 结算没有直接的经办人字段
            }
        }
        return configs.get(module)

    def _empty_stats(self):
        """返回空统计"""
        return {
            'total': 0,
            'updated': 0,
            'on_time': 0,
            'on_time_rate': 0,
            'avg_days': 0
        }

    def _build_summary(self, total_stats, count, is_person_view=False):
        """构建汇总统计

        total_stats 结构为各模块 {'total', 'updated', 'on_time'} 的汇总，
        这里统一按“按时条数 / 总条数”计算综合准时率，
        保证与项目/经办人明细中的口径一致。
        """
        all_total = sum(stats['total'] for stats in total_stats.values())
        all_updated = sum(stats['updated'] for stats in total_stats.values())
        all_on_time = sum(stats['on_time'] for stats in total_stats.values())

        overall_on_time_rate = (
            round(all_on_time / all_total * 100, 1) if all_total > 0 else 0
        )

        summary = {
            'project_count' if not is_person_view else 'person_count': count,
            'procurement_stats': {
                'total': total_stats['procurement']['total'],
                'updated': total_stats['procurement']['updated'],
                'update_rate': round(
                    total_stats['procurement']['updated'] / total_stats['procurement']['total'] * 100, 1
                ) if total_stats['procurement']['total'] > 0 else 0,
            },
            'contract_stats': {
                'total': total_stats['contract']['total'],
                'updated': total_stats['contract']['updated'],
                'update_rate': round(
                    total_stats['contract']['updated'] / total_stats['contract']['total'] * 100, 1
                ) if total_stats['contract']['total'] > 0 else 0,
            },
            'payment_stats': {
                'total': total_stats['payment']['total'],
                'updated': total_stats['payment']['updated'],
                'update_rate': round(
                    total_stats['payment']['updated'] / total_stats['payment']['total'] * 100, 1
                ) if total_stats['payment']['total'] > 0 else 0,
            },
            'settlement_stats': {
                'total': total_stats['settlement']['total'],
                'updated': total_stats['settlement']['updated'],
                'update_rate': round(
                    total_stats['settlement']['updated'] / total_stats['settlement']['total'] * 100, 1
                ) if total_stats['settlement']['total'] > 0 else 0,
            },
            'overall_on_time_rate': overall_on_time_rate,
            # 暂留平均周期字段，后续如需可基于趋势数据统一计算
            'average_cycle': 0,
        }

        return summary

    def _get_all_persons(self, year_filter=None, project_filter=None):
        """获取所有经办人名单"""
        person_names = set()
        
        # 采购经办人
        procurement_qs = Procurement.objects.filter(procurement_officer__isnull=False)
        if self.start_date:
            procurement_qs = procurement_qs.filter(result_publicity_release_date__gte=self.start_date)
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
        if self.start_date:
            contract_qs = contract_qs.filter(signing_date__gte=self.start_date)
        if year_filter and year_filter != 'all':
            contract_qs = contract_qs.filter(signing_date__year=int(year_filter))
        if project_filter:
            contract_qs = contract_qs.filter(project_id=project_filter)
        person_names.update(contract_qs.values_list('contract_officer', flat=True).distinct())
        
        return sorted(person_names)

    def _get_person_project_count(self, person_name, year_filter=None, project_filter=None):
        """获取经办人负责的项目数"""
        project_ids = set()
        
        # 从采购中获取项目
        procurement_qs = Procurement.objects.filter(procurement_officer=person_name)
        if self.start_date:
            procurement_qs = procurement_qs.filter(result_publicity_release_date__gte=self.start_date)
        if year_filter and year_filter != 'all':
            procurement_qs = procurement_qs.filter(result_publicity_release_date__year=int(year_filter))
        if project_filter:
            procurement_qs = procurement_qs.filter(project_id=project_filter)
        project_ids.update(procurement_qs.values_list('project_id', flat=True).distinct())
        
        # 从合同中获取项目
        contract_qs = Contract.objects.filter(contract_officer=person_name)
        if self.start_date:
            contract_qs = contract_qs.filter(signing_date__gte=self.start_date)
        if year_filter and year_filter != 'all':
            contract_qs = contract_qs.filter(signing_date__year=int(year_filter))
        if project_filter:
            contract_qs = contract_qs.filter(project_id=project_filter)
        project_ids.update(contract_qs.values_list('project_id', flat=True).distinct())
        
        return len(project_ids)

    def get_project_trend_and_problems(self, project_code, year_filter=None, show_all=False):
        """获取单个项目的趋势图和延迟记录

        返回结构尽量与归档监控保持一致，同时保留更新监控特有的热力图数据：
            {
                'heatmap_data': {...},
                'procurement_trend': [...],
                'contract_trend': [...],
                'payment_trend': [...],
                'settlement_trend': [...],
                'problems': {...},
                'summary': {...},
            }
        """
        from .update_problem_detector import UpdateProblemDetector
        from project.services.update_monitor import UpdateMonitorService

        # 1. 计算各模块的更新周期趋势
        procurement_trend = self._calculate_module_update_trend(
            module='procurement',
            project_code=project_code,
            year_filter=year_filter,
        )
        contract_trend = self._calculate_module_update_trend(
            module='contract',
            project_code=project_code,
            year_filter=year_filter,
        )
        payment_trend = self._calculate_module_update_trend(
            module='payment',
            project_code=project_code,
            year_filter=year_filter,
        )
        settlement_trend = self._calculate_module_update_trend(
            module='settlement',
            project_code=project_code,
            year_filter=year_filter,
        )

        # 2. 构建热力图数据（复用原有 UpdateMonitorService 快照能力）
        monitor_service = UpdateMonitorService()
        year = int(year_filter) if year_filter and year_filter != 'all' else None
        start_date = date(2020, 1, 1)
        snapshot = monitor_service.build_snapshot(year=year, start_date=start_date)

        project_data = None
        for proj in snapshot.get('projects', []):
            if proj['projectCode'] == project_code:
                project_data = proj
                break

        # 3. 统计概要（与列表“项目更新统计明细”的口径完全一致）
        summary = self._build_project_summary(project_code, year_filter)

        # 4. 获取超期记录
        detector_year = int(year_filter) if year_filter and year_filter != 'all' else None
        detector = UpdateProblemDetector(year_filter=detector_year)
        filters = {'project': project_code}

        # 若设置了起始日期，则按起始日期重算检测范围
        if self.start_date:
            detector = UpdateProblemDetector(year_filter=None)
            detector.start_date = self.start_date
            detector.end_date = detector.today

        problems = detector.detect_problems(filters=filters, show_all=show_all)

        return {
            'heatmap_data': project_data,  # 热力图数据
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'payment_trend': payment_trend,
            'settlement_trend': settlement_trend,
            'problems': problems,
            'summary': summary,
        }

    def get_all_persons_trend_and_problems(self, year_filter=None, project_filter=None, show_all=False):
        """获取所有经办人的汇总趋势图和延迟记录（用于个人视图主页面）

        Returns:
            dict: {
                'procurement_trend': [...],
                'contract_trend': [...],
                'payment_trend': [...],
                'settlement_trend': [...],
                'problems': {...},
            }
        """
        from .update_problem_detector import UpdateProblemDetector

        # 获取超期记录
        detector_year = int(year_filter) if year_filter and year_filter != 'all' else None
        detector = UpdateProblemDetector(year_filter=detector_year)
        filters = {}
        if project_filter:
            filters['project'] = project_filter
        problems = detector.detect_problems(filters=filters, show_all=show_all)

        # 汇总所有经办人的趋势（按项目过滤）
        procurement_trend = self._calculate_module_update_trend(
            module='procurement',
            year_filter=year_filter,
            project_filter=project_filter,
        )
        contract_trend = self._calculate_module_update_trend(
            module='contract',
            year_filter=year_filter,
            project_filter=project_filter,
        )
        payment_trend = self._calculate_module_update_trend(
            module='payment',
            year_filter=year_filter,
            project_filter=project_filter,
        )
        settlement_trend = self._calculate_module_update_trend(
            module='settlement',
            year_filter=year_filter,
            project_filter=project_filter,
        )

        return {
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'payment_trend': payment_trend,
            'settlement_trend': settlement_trend,
            'problems': problems,
        }

    def get_person_trend_and_problems(self, person_name, year_filter=None, project_filter=None, show_all=False):
        """获取单个经办人的趋势图和延迟记录（用于查看详情时）

        Returns:
            dict: {
                'procurement_trend': [...],
                'contract_trend': [...],
                'payment_trend': [...],
                'settlement_trend': [...],
                'problems': {...},
                'summary': {...},
            }
        """
        from .update_problem_detector import UpdateProblemDetector

        # 统计概要（经办人维度）
        summary = self._build_person_summary(person_name, year_filter, project_filter)

        # 获取超期记录
        detector_year = int(year_filter) if year_filter and year_filter != 'all' else None
        detector = UpdateProblemDetector(year_filter=detector_year)
        filters = {'responsible_person': person_name}
        if project_filter:
            filters['project'] = project_filter

        # 如设置起始日期，则按起始日期重算检测范围
        if self.start_date:
            detector = UpdateProblemDetector(year_filter=None)
            detector.start_date = self.start_date
            detector.end_date = detector.today

        problems = detector.detect_problems(filters=filters, show_all=show_all)

        # 经办人维度的更新趋势
        procurement_trend = self._calculate_module_update_trend(
            module='procurement',
            person_name=person_name,
            year_filter=year_filter,
            project_filter=project_filter,
        )
        contract_trend = self._calculate_module_update_trend(
            module='contract',
            person_name=person_name,
            year_filter=year_filter,
            project_filter=project_filter,
        )
        payment_trend = self._calculate_module_update_trend(
            module='payment',
            person_name=person_name,
            year_filter=year_filter,
            project_filter=project_filter,
        )
        settlement_trend = self._calculate_module_update_trend(
            module='settlement',
            person_name=person_name,
            year_filter=year_filter,
            project_filter=project_filter,
        )

        return {
            'procurement_trend': procurement_trend,
            'contract_trend': contract_trend,
            'payment_trend': payment_trend,
            'settlement_trend': settlement_trend,
            'problems': problems,
            'summary': summary,
        }

    def _build_project_summary(self, project_code, year_filter=None):
        """构建项目统计概要"""
        procurement_stats = self._calculate_module_update_stats(
            module='procurement',
            project_code=project_code,
            year_filter=year_filter
        )
        contract_stats = self._calculate_module_update_stats(
            module='contract',
            project_code=project_code,
            year_filter=year_filter
        )
        payment_stats = self._calculate_module_update_stats(
            module='payment',
            project_code=project_code,
            year_filter=year_filter
        )
        settlement_stats = self._calculate_module_update_stats(
            module='settlement',
            project_code=project_code,
            year_filter=year_filter
        )

        total = (
            procurement_stats['total'] + contract_stats['total'] +
            payment_stats['total'] + settlement_stats['total']
        )
        updated = (
            procurement_stats['updated'] + contract_stats['updated'] +
            payment_stats['updated'] + settlement_stats['updated']
        )
        on_time = (
            procurement_stats['on_time'] + contract_stats['on_time'] +
            payment_stats['on_time'] + settlement_stats['on_time']
        )

        return {
            'procurement': procurement_stats,
            'contract': contract_stats,
            'payment': payment_stats,
            'settlement': settlement_stats,
            # 综合准时率：按项目维度将各模块“按时条数/总条数”汇总
            'overall_update_rate': round(on_time / total * 100, 1) if total > 0 else 0,
            # 如有需要未来可以补充 overall_on_time_rate 等其它维度
        }

    def _build_person_summary(self, person_name, year_filter=None, project_filter=None):
        """构建经办人统计概要"""
        procurement_stats = self._calculate_module_update_stats(
            module='procurement',
            person_name=person_name,
            year_filter=year_filter,
            project_filter=project_filter
        )
        contract_stats = self._calculate_module_update_stats(
            module='contract',
            person_name=person_name,
            year_filter=year_filter,
            project_filter=project_filter
        )
        payment_stats = self._calculate_module_update_stats(
            module='payment',
            person_name=person_name,
            year_filter=year_filter,
            project_filter=project_filter
        )
        settlement_stats = self._calculate_module_update_stats(
            module='settlement',
            person_name=person_name,
            year_filter=year_filter,
            project_filter=project_filter
        )

        total = (
            procurement_stats['total'] + contract_stats['total'] +
            payment_stats['total'] + settlement_stats['total']
        )
        updated = (
            procurement_stats['updated'] + contract_stats['updated'] +
            payment_stats['updated'] + settlement_stats['updated']
        )
        on_time = (
            procurement_stats['on_time'] + contract_stats['on_time'] +
            payment_stats['on_time'] + settlement_stats['on_time']
        )

        return {
            'procurement': procurement_stats,
            'contract': contract_stats,
            'payment': payment_stats,
            'settlement': settlement_stats,
            # 综合准时率：按经办人维度汇总
            'overall_update_rate': round(on_time / total * 100, 1) if total > 0 else 0,
        }