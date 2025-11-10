"""更新问题检测器 - 遵循单一职责原则（SRP）"""
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Q
from .config import UPDATE_RULES


class UpdateProblemDetector:
    """更新问题检测器"""

    def __init__(self, time_dimension='current_month', year_filter=None):
        """
        初始化检测器
        time_dimension: 'current_month', 'last_month', 'current_year'
        year_filter: 指定年度筛选（优先级高于time_dimension）
        """
        self.today = timezone.now().date()
        self.time_dimension = time_dimension
        self.year_filter = year_filter
        self.start_date, self.end_date = self._calculate_date_range()

    def _calculate_date_range(self):
        """计算时间范围"""
        today = self.today

        # 如果指定了年度筛选，优先使用年度范围
        if self.year_filter:
            start_date = date(self.year_filter, 1, 1)
            end_date = date(self.year_filter, 12, 31)
            # 如果是当前年度，结束日期不超过今天
            if self.year_filter == today.year:
                end_date = min(end_date, today)
            return start_date, end_date

        # 否则使用时间维度
        if self.time_dimension == 'current_month':
            # 本月：本月1日至今
            start_date = date(today.year, today.month, 1)
            end_date = today
        elif self.time_dimension == 'last_month':
            # 上月：上月1日至上月最后一天
            first_day_this_month = date(today.year, today.month, 1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            start_date = date(last_day_last_month.year, last_day_last_month.month, 1)
            end_date = last_day_last_month
        elif self.time_dimension == 'current_year':
            # 本年度：1月1日至今
            start_date = date(today.year, 1, 1)
            end_date = today
        else:
            start_date = date(today.year, today.month, 1)
            end_date = today

        return start_date, end_date

    def _calculate_update_deadline(self, business_date):
        """计算更新截止日期（次月月底）"""
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

    def detect_problems(self, filters=None, return_url=None, show_all=False):
        """
        检测更新问题并返回问题列表

        Args:
            filters: 筛选条件
            return_url: 返回URL
            show_all: 是否显示所有记录（包括已按时完成的）
        """
        filters = filters or {}
        problems = []

        # 检测各模块更新问题
        problems.extend(self._detect_procurement_updates(filters, return_url))
        problems.extend(self._detect_contract_updates(filters, return_url))
        problems.extend(self._detect_payment_updates(filters, return_url))
        problems.extend(self._detect_settlement_updates(filters, return_url))

        # 分类：即将到期、已延迟、已完成
        upcoming = []
        delayed = []
        completed = []

        for problem in problems:
            days_remaining = problem['days_remaining']
            if days_remaining < 0:
                delayed.append(problem)
            elif days_remaining <= 3:
                upcoming.append(problem)
            else:
                # 剩余天数>3天的都是已完成（准时）的事件
                completed.append(problem)

        # 按剩余天数排序
        upcoming.sort(key=lambda x: x['days_remaining'])
        delayed.sort(key=lambda x: x['days_remaining'])
        completed.sort(key=lambda x: x['days_remaining'], reverse=True)

        result = {'upcoming': upcoming, 'delayed': delayed, 'completed': completed}

        return result

    def _detect_procurement_updates(self, filters, return_url=None):
        """检测采购更新问题"""
        from procurement.models import Procurement
        from urllib.parse import urlencode

        rule = UPDATE_RULES['procurement']
        queryset = Procurement.objects.select_related('project').filter(
            result_publicity_release_date__gte=self.start_date,
            result_publicity_release_date__lte=self.end_date
        )

        if filters.get('project'):
            queryset = queryset.filter(project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(procurement_officer=filters['responsible_person'])

        problems = []
        for item in queryset:
            business_date = item.result_publicity_release_date
            if not business_date:
                continue

            update_deadline = self._calculate_update_deadline(business_date)
            days_remaining = (update_deadline - self.today).days

            # 构建编辑URL，添加return_url参数
            edit_url = f'/procurement/{item.procurement_code}/'
            if return_url:
                edit_url += f'?{urlencode({"return_url": return_url})}'

            problems.append({
                'project_name': item.project.project_name if item.project else '',
                'module': 'procurement',
                'module_label': rule['label'],
                'code': item.procurement_code,
                'name': item.project_name,
                'responsible_person': item.procurement_officer or '',
                'business_date': business_date,
                'update_deadline': update_deadline,
                'days_remaining': days_remaining,
                'edit_url': edit_url
            })

        return problems

    def _detect_contract_updates(self, filters, return_url=None):
        """检测合同更新问题"""
        from contract.models import Contract
        from urllib.parse import urlencode

        rule = UPDATE_RULES['contract']
        queryset = Contract.objects.select_related('project').filter(
            signing_date__gte=self.start_date,
            signing_date__lte=self.end_date
        )

        if filters.get('project'):
            queryset = queryset.filter(project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(contract_officer=filters['responsible_person'])

        problems = []
        for item in queryset:
            business_date = item.signing_date
            if not business_date:
                continue

            update_deadline = self._calculate_update_deadline(business_date)
            days_remaining = (update_deadline - self.today).days

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
                'update_deadline': update_deadline,
                'days_remaining': days_remaining,
                'edit_url': edit_url
            })

        return problems

    def _detect_payment_updates(self, filters, return_url=None):
        """检测付款更新问题"""
        from payment.models import Payment
        from urllib.parse import urlencode

        rule = UPDATE_RULES['payment']
        queryset = Payment.objects.select_related('contract__project').filter(
            payment_date__gte=self.start_date,
            payment_date__lte=self.end_date
        )

        if filters.get('project'):
            queryset = queryset.filter(contract__project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(contract__contract_officer=filters['responsible_person'])

        problems = []
        for item in queryset:
            business_date = item.payment_date
            if not business_date:
                continue

            update_deadline = self._calculate_update_deadline(business_date)
            days_remaining = (update_deadline - self.today).days

            # 构建编辑URL，添加return_url参数
            edit_url = f'/payment/{item.payment_code}/'
            if return_url:
                edit_url += f'?{urlencode({"return_url": return_url})}'

            problems.append({
                'project_name': item.contract.project.project_name if item.contract and item.contract.project else '',
                'module': 'payment',
                'module_label': rule['label'],
                'code': item.payment_code,
                'name': item.contract.contract_name if item.contract else '',
                'responsible_person': item.contract.contract_officer if item.contract else '',
                'business_date': business_date,
                'update_deadline': update_deadline,
                'days_remaining': days_remaining,
                'edit_url': edit_url
            })

        return problems

    def _detect_settlement_updates(self, filters, return_url=None):
        """检测结算更新问题"""
        from settlement.models import Settlement
        from urllib.parse import urlencode

        rule = UPDATE_RULES['settlement']
        queryset = Settlement.objects.select_related('main_contract__project').filter(
            completion_date__gte=self.start_date,
            completion_date__lte=self.end_date
        )

        if filters.get('project'):
            queryset = queryset.filter(main_contract__project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(main_contract__contract_officer=filters['responsible_person'])

        problems = []
        for item in queryset:
            business_date = item.completion_date
            if not business_date:
                continue

            update_deadline = self._calculate_update_deadline(business_date)
            days_remaining = (update_deadline - self.today).days

            # 构建编辑URL，添加return_url参数
            edit_url = f'/settlement/{item.settlement_code}/'
            if return_url:
                edit_url += f'?{urlencode({"return_url": return_url})}'

            problems.append({
                'project_name': item.main_contract.project.project_name if item.main_contract and item.main_contract.project else '',
                'module': 'settlement',
                'module_label': rule['label'],
                'code': item.settlement_code,
                'name': item.main_contract.contract_name if item.main_contract else '',
                'responsible_person': item.main_contract.contract_officer if item.main_contract else '',
                'business_date': business_date,
                'update_deadline': update_deadline,
                'days_remaining': days_remaining,
                'edit_url': edit_url
            })

        return problems

    def get_statistics(self, problems):
        """获取统计数据"""
        upcoming_count = len(problems['upcoming'])
        delayed_count = len(problems['delayed'])
        completed_count = len(problems.get('completed', []))

        # 总事件数 = 即将到期 + 已延迟 + 已完成（准时）
        total_events = upcoming_count + delayed_count + completed_count

        # 准时事件 = 即将到期 + 已完成（准时）
        on_time_count = upcoming_count + completed_count

        # 准时率 = 准时事件 / 总事件数
        on_time_rate = (on_time_count / total_events * 100) if total_events > 0 else 100

        return {
            'total_events': total_events,
            'on_time_count': on_time_count,
            'delayed_count': delayed_count,
            'upcoming_count': upcoming_count,
            'on_time_rate': round(on_time_rate, 1)
        }
