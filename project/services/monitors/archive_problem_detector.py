"""归档问题检测器 - 遵循单一职责原则（SRP）"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from .config import ARCHIVE_RULES, SEVERITY_CONFIG


class ArchiveProblemDetector:
    """归档问题检测器"""

    def __init__(self):
        self.today = timezone.now().date()

    def detect_problems(self, filters=None, return_url=None, show_all=False):
        """
        检测归档问题并返回问题列表

        Args:
            filters: 筛选条件
            return_url: 返回URL
            show_all: 是否显示所有记录（包括已归档的）
        """
        filters = filters or {}
        problems = []

        # 检测采购归档问题
        problems.extend(self._detect_procurement_problems(filters, return_url, show_all))

        # 检测合同归档问题
        problems.extend(self._detect_contract_problems(filters, return_url, show_all))

        # 检测结算归档问题
        problems.extend(self._detect_settlement_problems(filters, return_url, show_all))

        # 按严重程度排序
        problems.sort(key=lambda x: (-x['overdue_days'] if x['overdue_days'] > 0 else 999))

        return self._group_by_severity(problems, show_all)

    def _detect_procurement_problems(self, filters, return_url=None, show_all=False):
        """检测采购归档问题"""
        from procurement.models import Procurement
        from urllib.parse import urlencode

        rule = ARCHIVE_RULES['procurement']

        # 根据show_all决定查询条件
        if show_all:
            queryset = Procurement.objects.select_related('project').all()
        else:
            queryset = Procurement.objects.select_related('project').filter(
                archive_date__isnull=True
            )

        # 应用年度筛选
        if filters.get('year_filter'):
            queryset = queryset.filter(result_publicity_release_date__year=filters['year_filter'])

        # 应用项目筛选
        if filters.get('project'):
            queryset = queryset.filter(project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(procurement_officer=filters['responsible_person'])

        problems = []
        for item in queryset:
            business_date = item.result_publicity_release_date
            if not business_date:
                continue

            archive_deadline = business_date + timedelta(days=rule['deadline_days'])
            overdue_days = (self.today - archive_deadline).days

            # 构建编辑URL，添加return_url参数
            edit_url = f'/procurement/{item.procurement_code}/'
            if return_url:
                edit_url += f'?{urlencode({"return_url": return_url})}'

            problems.append({
                'project_name': item.project.project_name if item.project else '',
                'module': 'procurement',
                'module_label': rule['label'],
                'code': item.procurement_code,
                'name': item.project_name,  # Procurement模型的字段是project_name
                'responsible_person': item.procurement_officer or '',
                'business_date': business_date,
                'archive_deadline': archive_deadline,
                'archive_date': item.archive_date,
                'overdue_days': overdue_days,
                'severity': self._calculate_severity(overdue_days, rule['severity_thresholds']),
                'edit_url': edit_url
            })

        return problems

    def _detect_contract_problems(self, filters, return_url=None, show_all=False):
        """检测合同归档问题"""
        from contract.models import Contract
        from urllib.parse import urlencode

        rule = ARCHIVE_RULES['contract']

        # 根据show_all决定查询条件
        if show_all:
            queryset = Contract.objects.select_related('project').filter(
                file_positioning='主合同'
            )
        else:
            queryset = Contract.objects.select_related('project').filter(
                archive_date__isnull=True,
                file_positioning='主合同'
            )

        # 应用年度筛选
        if filters.get('year_filter'):
            queryset = queryset.filter(signing_date__year=filters['year_filter'])

        # 应用项目筛选
        if filters.get('project'):
            queryset = queryset.filter(project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(contract_officer=filters['responsible_person'])

        problems = []
        for item in queryset:
            business_date = item.signing_date
            if not business_date:
                continue

            archive_deadline = business_date + timedelta(days=rule['deadline_days'])
            overdue_days = (self.today - archive_deadline).days

            # 构建编辑URL，添加return_url参数
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
                'business_date': business_date,
                'archive_deadline': archive_deadline,
                'archive_date': item.archive_date,
                'overdue_days': overdue_days,
                'severity': self._calculate_severity(overdue_days, rule['severity_thresholds']),
                'edit_url': edit_url
            })

        return problems

    def _detect_settlement_problems(self, filters, return_url=None, show_all=False):
        """检测结算归档问题 - 注意：结算通过关联的主合同的archive_date判断"""
        from settlement.models import Settlement
        from urllib.parse import urlencode

        rule = ARCHIVE_RULES['settlement']

        # 根据show_all决定查询条件
        if show_all:
            queryset = Settlement.objects.select_related('main_contract__project').all()
        else:
            queryset = Settlement.objects.select_related('main_contract__project').filter(
                main_contract__archive_date__isnull=True
            )

        # 应用年度筛选
        if filters.get('year_filter'):
            queryset = queryset.filter(completion_date__year=filters['year_filter'])

        # 应用项目筛选
        if filters.get('project'):
            queryset = queryset.filter(main_contract__project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(main_contract__contract_officer=filters['responsible_person'])

        problems = []
        for item in queryset:
            business_date = item.completion_date
            if not business_date:
                continue

            archive_deadline = business_date + timedelta(days=rule['deadline_days'])
            overdue_days = (self.today - archive_deadline).days

            # 构建编辑URL，添加return_url参数
            edit_url = f'/settlement/{item.settlement_code}/'
            if return_url:
                edit_url += f'?{urlencode({"return_url": return_url})}'

            problems.append({
                'project_name': item.main_contract.project.project_name if item.main_contract and item.main_contract.project else '',
                'module': 'settlement',
                'module_label': rule['label'],
                'code': item.main_contract.contract_code if item.main_contract else '',
                'name': item.main_contract.contract_name if item.main_contract else '',
                'responsible_person': item.main_contract.contract_officer if item.main_contract else '',
                'business_date': business_date,
                'archive_deadline': archive_deadline,
                'archive_date': item.main_contract.archive_date if item.main_contract else None,
                'overdue_days': overdue_days,
                'severity': self._calculate_severity(overdue_days, rule['severity_thresholds']),
                'edit_url': edit_url
            })

        return problems

    def _calculate_severity(self, overdue_days, thresholds):
        """计算严重程度"""
        if overdue_days >= thresholds[0]:
            return 'severe'
        elif overdue_days >= thresholds[1]:
            return 'moderate'
        elif overdue_days >= thresholds[2]:
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
            # 如果已归档，放入"已完成"分组
            if show_all and problem.get('archive_date'):
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
            filters: 筛选条件（包含year_filter和project）
        """
        filters = filters or {}

        # 计算问题总数（排除已完成的）
        total_problems = (
            len(problems.get('severe', [])) +
            len(problems.get('moderate', [])) +
            len(problems.get('minor', [])) +
            len(problems.get('pending', []))
        )

        # 计算总体归档率和及时归档率
        from procurement.models import Procurement
        from contract.models import Contract
        from settlement.models import Settlement

        # 构建基础查询集（应用年度和项目筛选）
        procurement_qs = Procurement.objects.all()
        contract_qs = Contract.objects.filter(file_positioning='主合同')
        settlement_qs = Settlement.objects.all()

        # 应用年度筛选
        if filters.get('year_filter'):
            year = filters['year_filter']
            procurement_qs = procurement_qs.filter(result_publicity_release_date__year=year)
            contract_qs = contract_qs.filter(signing_date__year=year)
            settlement_qs = settlement_qs.filter(completion_date__year=year)

        # 应用项目筛选
        if filters.get('project'):
            project_code = filters['project']
            procurement_qs = procurement_qs.filter(project_id=project_code)
            contract_qs = contract_qs.filter(project_id=project_code)
            settlement_qs = settlement_qs.filter(main_contract__project_id=project_code)

        # 计算总记录数
        total_records = (
            procurement_qs.count() +
            contract_qs.count() +
            settlement_qs.count()
        )

        # 计算已归档记录数
        archived_records = (
            procurement_qs.exclude(archive_date__isnull=True).count() +
            contract_qs.exclude(archive_date__isnull=True).count() +
            settlement_qs.exclude(main_contract__archive_date__isnull=True).count()
        )

        # 计算归档率
        archive_rate = (archived_records / total_records * 100) if total_records > 0 else 0

        # 计算及时归档率（已归档且未逾期的记录）
        # 逾期记录 = 严重 + 中等 + 轻微（这些都是已经超过截止日期的）
        overdue_count = len(problems.get('severe', [])) + len(problems.get('moderate', [])) + len(problems.get('minor', []))
        # 及时归档 = 已归档 - 逾期已归档
        # 注意：problems中的逾期记录可能包含未归档的，需要统计已归档但逾期的
        overdue_archived = sum(1 for p in problems.get('severe', []) + problems.get('moderate', []) + problems.get('minor', []) if p.get('archive_date'))
        timely_archived = archived_records - overdue_archived
        timely_rate = (timely_archived / total_records * 100) if total_records > 0 else 0

        return {
            'total_problems': total_problems,
            'severe_count': len(problems.get('severe', [])),
            'moderate_count': len(problems.get('moderate', [])),
            'minor_count': len(problems.get('minor', [])),
            'pending_count': len(problems.get('pending', [])),
            'archive_rate': round(archive_rate, 1),
            'timely_rate': round(timely_rate, 1)
        }
