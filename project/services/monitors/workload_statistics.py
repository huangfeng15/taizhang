"""工作量统计服务 - 遵循单一职责原则（SRP）"""
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count
from .config import WORKLOAD_CONFIG


class WorkloadStatistics:
    """工作量统计服务"""

    def __init__(self, time_dimension='recent_month', dimension_type='person'):
        """
        初始化统计服务
        time_dimension: 'recent_month', 'last_month', 'current_year'
        dimension_type: 'person', 'project'
        """
        self.time_dimension = time_dimension
        self.dimension_type = dimension_type
        self.start_date, self.end_date = self._calculate_date_range()

    def _calculate_date_range(self):
        """计算时间范围"""
        today = timezone.now().date()

        if self.time_dimension == 'recent_month':
            # 最近一个月：30天前至今
            start_date = today - timedelta(days=30)
            end_date = today
        elif self.time_dimension == 'last_month':
            # 上一个月：上月1日至上月最后一天
            first_day_this_month = date(today.year, today.month, 1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            start_date = date(last_day_last_month.year, last_day_last_month.month, 1)
            end_date = last_day_last_month
        elif self.time_dimension == 'current_year':
            # 今年累计：1月1日至今
            start_date = date(today.year, 1, 1)
            end_date = today
        else:
            start_date = today - timedelta(days=30)
            end_date = today

        return start_date, end_date

    def get_workload_ranking(self):
        """获取工作量排名"""
        if self.dimension_type == 'person':
            return self._get_person_workload()
        else:
            return self._get_project_workload()

    def _get_person_workload(self):
        """按个人统计工作量"""
        from procurement.models import Procurement
        from contract.models import Contract
        from payment.models import Payment
        from settlement.models import Settlement

        person_stats = {}

        # 统计采购
        procurements = Procurement.objects.filter(
            result_publicity_release_date__gte=self.start_date,
            result_publicity_release_date__lte=self.end_date
        ).select_related('project')

        for item in procurements:
            person = item.procurement_officer or '未指定'
            if person not in person_stats:
                person_stats[person] = {'procurement': [], 'contract': [], 'payment': [], 'settlement': []}
            person_stats[person]['procurement'].append({
                'code': item.procurement_code,
                'project_name': item.project.project_name if item.project else '',
                'name': item.project_name,
                'date': item.result_publicity_release_date,
                'url': f'/procurement/{item.procurement_code}/'
            })

        # 统计合同
        contracts = Contract.objects.filter(
            signing_date__gte=self.start_date,
            signing_date__lte=self.end_date
        ).select_related('project')

        for item in contracts:
            person = item.contract_officer or '未指定'
            if person not in person_stats:
                person_stats[person] = {'procurement': [], 'contract': [], 'payment': [], 'settlement': []}
            person_stats[person]['contract'].append({
                'sequence': item.contract_sequence or '',
                'code': item.contract_code,
                'name': item.contract_name,
                'date': item.signing_date,
                'amount': item.contract_amount,
                'url': f'/contract/{item.contract_code}/'
            })

        # 统计付款
        payments = Payment.objects.filter(
            payment_date__gte=self.start_date,
            payment_date__lte=self.end_date
        ).select_related('contract')

        for item in payments:
            person = item.contract.contract_officer if item.contract else '未指定'
            if person not in person_stats:
                person_stats[person] = {'procurement': [], 'contract': [], 'payment': [], 'settlement': []}
            person_stats[person]['payment'].append({
                'code': item.payment_code,
                'contract_sequence': item.contract.contract_sequence if item.contract else '',
                'contract_name': item.contract.contract_name if item.contract else '',
                'date': item.payment_date,
                'amount': item.payment_amount,
                'url': f'/payment/{item.payment_code}/'
            })

        # 统计结算
        settlements = Settlement.objects.filter(
            completion_date__gte=self.start_date,
            completion_date__lte=self.end_date
        ).select_related('main_contract')

        for item in settlements:
            person = item.main_contract.contract_officer if item.main_contract else '未指定'
            if person not in person_stats:
                person_stats[person] = {'procurement': [], 'contract': [], 'payment': [], 'settlement': []}
            person_stats[person]['settlement'].append({
                'code': item.settlement_code,
                'contract_code': item.main_contract.contract_code if item.main_contract else '',
                'contract_name': item.main_contract.contract_name if item.main_contract else '',
                'date': item.completion_date,
                'amount': item.final_amount,
                'url': f'/settlement/{item.settlement_code}/'
            })

        # 计算总数并排序
        ranking = []
        for person, data in person_stats.items():
            total = (len(data['procurement']) + len(data['contract']) +
                    len(data['payment']) + len(data['settlement']))
            ranking.append({
                'name': person,
                'procurement_count': len(data['procurement']),
                'contract_count': len(data['contract']),
                'payment_count': len(data['payment']),
                'settlement_count': len(data['settlement']),
                'total': total,
                'details': data
            })

        ranking.sort(key=lambda x: x['total'], reverse=True)
        return ranking

    def _get_project_workload(self):
        """按项目统计工作量"""
        from procurement.models import Procurement
        from contract.models import Contract
        from payment.models import Payment
        from settlement.models import Settlement

        project_stats = {}

        # 统计采购
        procurements = Procurement.objects.filter(
            result_publicity_release_date__gte=self.start_date,
            result_publicity_release_date__lte=self.end_date
        ).select_related('project')

        for item in procurements:
            project_name = item.project.project_name if item.project else '未关联项目'
            if project_name not in project_stats:
                project_stats[project_name] = {'procurement': [], 'contract': [], 'payment': [], 'settlement': []}
            project_stats[project_name]['procurement'].append({
                'code': item.procurement_code,
                'name': item.project_name,
                'person': item.procurement_officer or '',
                'date': item.result_publicity_release_date,
                'url': f'/procurement/{item.procurement_code}/'
            })

        # 统计合同
        contracts = Contract.objects.filter(
            signing_date__gte=self.start_date,
            signing_date__lte=self.end_date
        ).select_related('project')

        for item in contracts:
            project_name = item.project.project_name if item.project else '未关联项目'
            if project_name not in project_stats:
                project_stats[project_name] = {'procurement': [], 'contract': [], 'payment': [], 'settlement': []}
            project_stats[project_name]['contract'].append({
                'sequence': item.contract_sequence or '',
                'code': item.contract_code,
                'name': item.contract_name,
                'person': item.contract_officer or '',
                'date': item.signing_date,
                'amount': item.contract_amount,
                'url': f'/contract/{item.contract_code}/'
            })

        # 统计付款
        payments = Payment.objects.filter(
            payment_date__gte=self.start_date,
            payment_date__lte=self.end_date
        ).select_related('contract__project')

        for item in payments:
            project_name = item.contract.project.project_name if item.contract and item.contract.project else '未关联项目'
            if project_name not in project_stats:
                project_stats[project_name] = {'procurement': [], 'contract': [], 'payment': [], 'settlement': []}
            project_stats[project_name]['payment'].append({
                'code': item.payment_code,
                'contract_name': item.contract.contract_name if item.contract else '',
                'person': item.contract.contract_officer if item.contract else '',
                'date': item.payment_date,
                'amount': item.payment_amount,
                'url': f'/payment/{item.payment_code}/'
            })

        # 统计结算
        settlements = Settlement.objects.filter(
            completion_date__gte=self.start_date,
            completion_date__lte=self.end_date
        ).select_related('main_contract__project')

        for item in settlements:
            project_name = item.main_contract.project.project_name if item.main_contract and item.main_contract.project else '未关联项目'
            if project_name not in project_stats:
                project_stats[project_name] = {'procurement': [], 'contract': [], 'payment': [], 'settlement': []}
            project_stats[project_name]['settlement'].append({
                'code': item.settlement_code,
                'contract_name': item.main_contract.contract_name if item.main_contract else '',
                'person': item.main_contract.contract_officer if item.main_contract else '',
                'date': item.completion_date,
                'amount': item.final_amount,
                'url': f'/settlement/{item.settlement_code}/'
            })

        # 计算总数并排序
        ranking = []
        for project_name, data in project_stats.items():
            total = (len(data['procurement']) + len(data['contract']) +
                    len(data['payment']) + len(data['settlement']))
            ranking.append({
                'name': project_name,
                'procurement_count': len(data['procurement']),
                'contract_count': len(data['contract']),
                'payment_count': len(data['payment']),
                'settlement_count': len(data['settlement']),
                'total': total,
                'details': data
            })

        ranking.sort(key=lambda x: x['total'], reverse=True)
        return ranking
