"""工作周期问题检测器 - 遵循单一职责原则（SRP）"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from .config import CYCLE_RULES, SEVERITY_CONFIG


class CycleProblemDetector:
    """工作周期问题检测器"""

    def __init__(self):
        self.today = timezone.now().date()
        self.procurement_rule = CYCLE_RULES['procurement']
        self.contract_rule = CYCLE_RULES['contract']

    def detect_problems(self, filters=None, return_url=None, show_all=False):
        """
        检测工作周期问题并返回问题列表

        Args:
            filters: 筛选条件
            return_url: 返回URL
            show_all: 是否显示所有记录（包括已完成的）
        """
        filters = filters or {}
        problems = []

        # 检测采购周期问题
        problems.extend(self._detect_procurement_cycle_problems(filters, return_url, show_all))

        # 检测合同周期问题
        problems.extend(self._detect_contract_cycle_problems(filters, return_url, show_all))

        # 按超期天数排序
        problems.sort(key=lambda x: (-x['overdue_days'] if x['overdue_days'] > 0 else 999))

        return self._group_by_severity(problems, show_all)

    def _detect_procurement_cycle_problems(self, filters, return_url=None, show_all=False):
        """检测采购周期问题"""
        from procurement.models import Procurement
        from urllib.parse import urlencode

        rule = self.procurement_rule

        # 根据show_all决定查询条件
        if show_all:
            queryset = Procurement.objects.select_related('project').filter(
                requirement_approval_date__isnull=False
            )
        else:
            queryset = Procurement.objects.select_related('project').filter(
                requirement_approval_date__isnull=False,
                result_publicity_release_date__isnull=True
            )

        # 应用年度筛选
        if filters.get('year_filter'):
            queryset = queryset.filter(requirement_approval_date__year=filters['year_filter'])

        # 应用项目筛选
        if filters.get('project'):
            queryset = queryset.filter(project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(procurement_officer=filters['responsible_person'])
        if filters.get('procurement_method'):
            queryset = queryset.filter(procurement_method=filters['procurement_method'])

        problems = []
        for item in queryset:
            start_date = item.requirement_approval_date
            end_date = item.result_publicity_release_date
            
            if not start_date:
                continue

            # 获取该采购方式的规定周期
            deadline_days = rule['deadline_map'].get(
                item.procurement_method,
                rule['default_deadline']
            )
            
            # 计算实际周期和超期天数
            if end_date:
                # 已完成
                cycle_days = (end_date - start_date).days
                overdue_days = max(cycle_days - deadline_days, 0)
            else:
                # 未完成，计算从开始日期到今天的天数
                cycle_days = (self.today - start_date).days
                overdue_days = max(cycle_days - deadline_days, 0)

            # 构建编辑URL
            edit_url = f'/procurement/{item.procurement_code}/'
            if return_url:
                edit_url += f'?{urlencode({"return_url": return_url})}'

            problems.append({
                'project_name': item.project.project_name if item.project else '',
                'module': 'procurement',
                'module_label': rule['label'],
                'code': item.procurement_code,
                'name': item.project_name,
                'procurement_method': item.procurement_method or '',
                'responsible_person': item.procurement_officer or '',
                'start_date': start_date,
                'end_date': end_date,
                'deadline_days': deadline_days,
                'cycle_days': cycle_days,
                'overdue_days': overdue_days,
                'severity': self._calculate_severity(overdue_days, rule['severity_thresholds']),
                'edit_url': edit_url,
                'is_completed': end_date is not None
            })

        return problems

    def _detect_contract_cycle_problems(self, filters, return_url=None, show_all=False):
        """检测合同周期问题"""
        from contract.models import Contract
        from urllib.parse import urlencode

        rule = self.contract_rule

        # 根据show_all决定查询条件
        if show_all:
            queryset = Contract.objects.select_related('project', 'procurement').filter(
                file_positioning='主合同',
                procurement__result_publicity_release_date__isnull=False
            )
        else:
            queryset = Contract.objects.select_related('project', 'procurement').filter(
                file_positioning='主合同',
                procurement__result_publicity_release_date__isnull=False,
                signing_date__isnull=True
            )

        # 应用年度筛选
        if filters.get('year_filter'):
            queryset = queryset.filter(procurement__result_publicity_release_date__year=filters['year_filter'])

        # 应用项目筛选
        if filters.get('project'):
            queryset = queryset.filter(project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(contract_officer=filters['responsible_person'])

        problems = []
        for item in queryset:
            start_date = item.procurement.result_publicity_release_date if item.procurement else None
            end_date = item.signing_date
            
            if not start_date:
                continue

            deadline_days = rule['deadline_days']
            
            # 计算实际周期和超期天数
            if end_date:
                # 已完成
                cycle_days = (end_date - start_date).days
                overdue_days = max(cycle_days - deadline_days, 0)
            else:
                # 未完成，计算从开始日期到今天的天数
                cycle_days = (self.today - start_date).days
                overdue_days = max(cycle_days - deadline_days, 0)

            # 构建编辑URL
            edit_url = f'/contract/{item.contract_code}/'
            if return_url:
                edit_url += f'?{urlencode({"return_url": return_url})}'

            problems.append({
                'project_name': item.project.project_name if item.project else '',
                'module': 'contract',
                'module_label': rule['label'],
                'code': item.contract_code,
                'name': item.contract_name,
                'responsible_person': item.contract_officer or '',
                'start_date': start_date,
                'end_date': end_date,
                'deadline_days': deadline_days,
                'cycle_days': cycle_days,
                'overdue_days': overdue_days,
                'severity': self._calculate_severity(overdue_days, rule['severity_thresholds']),
                'edit_url': edit_url,
                'is_completed': end_date is not None
            })

        return problems

    def _calculate_severity(self, overdue_days, thresholds):
        """计算严重程度"""
        if overdue_days >= thresholds['severe']:
            return 'severe'
        elif overdue_days >= thresholds['moderate']:
            return 'moderate'
        elif overdue_days >= thresholds['mild']:
            return 'minor'
        else:
            return 'pending'

    def _group_by_severity(self, problems, show_all=False):
        """按严重程度分组"""
        grouped = {
            'severe': [],
            'moderate': [],
            'minor': [],
            'pending': []
        }

        # 如果显示所有记录，添加"已完成"分组
        if show_all:
            grouped['completed'] = []

        for problem in problems:
            # 如果已完成，放入"已完成"分组
            if show_all and problem.get('is_completed'):
                grouped['completed'].append(problem)
            else:
                severity = problem['severity']
                grouped[severity].append(problem)

        return grouped

    def get_statistics(self, problems, filters=None):
        """
        获取统计数据

        Args:
            problems: 问题列表（按严重程度分组）
            filters: 筛选条件（包含year_filter、project和procurement_method）
        """
        filters = filters or {}

        # 计算问题总数（排除已完成的）
        total_problems = (
            len(problems.get('severe', [])) +
            len(problems.get('moderate', [])) +
            len(problems.get('minor', [])) +
            len(problems.get('pending', []))
        )

        # 计算总体完成率和及时完成率
        from procurement.models import Procurement
        from contract.models import Contract

        # 构建基础查询集（应用年度和项目筛选）
        procurement_qs = Procurement.objects.filter(requirement_approval_date__isnull=False)
        contract_qs = Contract.objects.filter(
            file_positioning='主合同',
            procurement__result_publicity_release_date__isnull=False
        )

        # 应用年度筛选
        if filters.get('year_filter'):
            year = filters['year_filter']
            procurement_qs = procurement_qs.filter(requirement_approval_date__year=year)
            contract_qs = contract_qs.filter(procurement__result_publicity_release_date__year=year)

        # 应用项目筛选
        if filters.get('project'):
            project_code = filters['project']
            procurement_qs = procurement_qs.filter(project_id=project_code)
            contract_qs = contract_qs.filter(project_id=project_code)

        # 应用采购方式筛选
        if filters.get('procurement_method'):
            procurement_method = filters['procurement_method']
            procurement_qs = procurement_qs.filter(procurement_method=procurement_method)

        # 计算总记录数
        total_records = (
            procurement_qs.count() +
            contract_qs.count()
        )

        # 计算已完成记录数
        completed_records = (
            procurement_qs.exclude(result_publicity_release_date__isnull=True).count() +
            contract_qs.exclude(signing_date__isnull=True).count()
        )

        # 计算完成率
        completion_rate = (completed_records / total_records * 100) if total_records > 0 else 0

        # 计算及时完成率（已完成且未逾期的记录）
        overdue_count = len(problems.get('severe', [])) + len(problems.get('moderate', [])) + len(problems.get('minor', []))
        overdue_completed = sum(1 for p in problems.get('severe', []) + problems.get('moderate', []) + problems.get('minor', []) if p.get('is_completed'))
        timely_completed = completed_records - overdue_completed
        timely_rate = (timely_completed / total_records * 100) if total_records > 0 else 0

        return {
            'total_problems': total_problems,
            'severe_count': len(problems.get('severe', [])),
            'moderate_count': len(problems.get('moderate', [])),
            'minor_count': len(problems.get('minor', [])),
            'pending_count': len(problems.get('pending', [])),
            'completion_rate': round(completion_rate, 1),
            'timely_rate': round(timely_rate, 1)
        }