"""齐全性检查器 - 遵循单一职责原则（SRP）"""
from django.db.models import Q


class CompletenessChecker:
    """齐全性检查器"""

    # 核心字段定义
    PROCUREMENT_CORE_FIELDS = [
        'winning_bidder', 'winning_amount', 'winning_contact',
        'evaluation_committee', 'payment_method'
    ]

    CONTRACT_CORE_FIELDS = [
        'party_b_contact_person', 'party_b_handler'
    ]

    def check_problems(self, filters=None, return_url=None, show_all=False):
        """
        检查齐全性问题并返回问题列表

        Args:
            filters: 筛选条件
            return_url: 返回URL
            show_all: 是否显示所有记录（包括完整的）
        """
        filters = filters or {}

        # 检查采购不完整记录
        procurement_incomplete, procurement_complete = self._check_procurement_completeness(filters, return_url, show_all)

        # 检查合同不完整记录
        contract_incomplete, contract_complete = self._check_contract_completeness(filters, return_url, show_all)

        # 检查关联异常
        relation_anomalies = self._check_relation_anomalies(filters, return_url)

        result = {
            'procurement_incomplete': procurement_incomplete,
            'contract_incomplete': contract_incomplete,
            'relation_anomalies': relation_anomalies
        }

        if show_all:
            result['procurement_complete'] = procurement_complete
            result['contract_complete'] = contract_complete

        return result

    def _check_procurement_completeness(self, filters, return_url=None, show_all=False):
        """检查采购完整性"""
        from procurement.models import Procurement
        from urllib.parse import urlencode

        queryset = Procurement.objects.select_related('project').all()

        # 应用年度筛选
        if filters.get('year_filter'):
            queryset = queryset.filter(result_publicity_release_date__year=filters['year_filter'])

        # 应用项目筛选
        if filters.get('project'):
            queryset = queryset.filter(project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(procurement_officer=filters['responsible_person'])

        incomplete_list = []
        complete_list = []

        for item in queryset:
            missing_fields = []
            for field in self.PROCUREMENT_CORE_FIELDS:
                value = getattr(item, field, None)
                if not value:
                    missing_fields.append(self._get_field_label('procurement', field))

            total_fields = len(self.PROCUREMENT_CORE_FIELDS)
            filled_fields = total_fields - len(missing_fields)
            completeness_rate = (filled_fields / total_fields * 100)

            # 构建编辑URL，添加return_url参数
            edit_url = f'/procurement/{item.procurement_code}/'
            if return_url:
                edit_url += f'?{urlencode({"return_url": return_url})}'

            record = {
                'code': item.procurement_code,
                'project_name': item.project.project_name if item.project else '',
                'name': item.project_name,
                'responsible_person': item.procurement_officer or '',
                'completeness_rate': round(completeness_rate, 1),
                'edit_url': edit_url
            }

            if missing_fields:
                record['missing_fields'] = '、'.join(missing_fields)
                incomplete_list.append(record)
            elif show_all:
                record['missing_fields'] = '无'
                complete_list.append(record)

        return incomplete_list, complete_list

    def _check_contract_completeness(self, filters, return_url=None, show_all=False):
        """检查合同完整性"""
        from contract.models import Contract
        from urllib.parse import urlencode

        queryset = Contract.objects.select_related('project').all()

        # 应用年度筛选
        if filters.get('year_filter'):
            queryset = queryset.filter(signing_date__year=filters['year_filter'])

        # 应用项目筛选
        if filters.get('project'):
            queryset = queryset.filter(project_id=filters['project'])
        if filters.get('responsible_person'):
            queryset = queryset.filter(contract_officer=filters['responsible_person'])

        incomplete_list = []
        complete_list = []

        for item in queryset:
            missing_fields = []
            for field in self.CONTRACT_CORE_FIELDS:
                value = getattr(item, field, None)
                if not value:
                    missing_fields.append(self._get_field_label('contract', field))

            total_fields = len(self.CONTRACT_CORE_FIELDS)
            filled_fields = total_fields - len(missing_fields)
            completeness_rate = (filled_fields / total_fields * 100)

            # 构建编辑URL，添加return_url参数
            edit_url = f'/contract/{item.contract_code}/'
            if return_url:
                edit_url += f'?{urlencode({"return_url": return_url})}'

            record = {
                'sequence': item.contract_sequence or '',
                'code': item.contract_code,
                'name': item.contract_name,
                'responsible_person': item.contract_officer or '',
                'completeness_rate': round(completeness_rate, 1),
                'edit_url': edit_url
            }

            if missing_fields:
                record['missing_fields'] = '、'.join(missing_fields)
                incomplete_list.append(record)
            elif show_all:
                record['missing_fields'] = '无'
                complete_list.append(record)

        return incomplete_list, complete_list

    def _check_relation_anomalies(self, filters, return_url=None):
        """检查关联异常"""
        from contract.models import Contract
        from payment.models import Payment
        from urllib.parse import urlencode

        anomalies = []

        # 检查补充协议未关联主合同
        supplements_without_parent = Contract.objects.filter(
            file_positioning='补充协议',
            parent_contract__isnull=True
        )

        # 应用年度筛选
        if filters.get('year_filter'):
            supplements_without_parent = supplements_without_parent.filter(signing_date__year=filters['year_filter'])

        # 应用项目筛选
        if filters.get('project'):
            supplements_without_parent = supplements_without_parent.filter(project_id=filters['project'])

        for item in supplements_without_parent:
            # 构建编辑URL，添加return_url参数
            edit_url = f'/contract/{item.contract_code}/'
            if return_url:
                edit_url += f'?{urlencode({"return_url": return_url})}'

            anomalies.append({
                'anomaly_type': '未关联主合同',
                'sequence': item.contract_sequence or '',
                'code': item.contract_code,
                'name': item.contract_name,
                'description': '补充协议未关联主合同',
                'edit_url': edit_url
            })

        # 检查付款超额（付款总额 > 合同金额）
        contracts_with_payments = Contract.objects.filter(
            file_positioning='主合同'
        ).prefetch_related('payments')

        # 应用年度筛选
        if filters.get('year_filter'):
            contracts_with_payments = contracts_with_payments.filter(signing_date__year=filters['year_filter'])

        # 应用项目筛选
        if filters.get('project'):
            contracts_with_payments = contracts_with_payments.filter(project_id=filters['project'])

        for contract in contracts_with_payments:
            if contract.contract_amount:
                total_payment = sum(p.payment_amount for p in contract.payments.all() if p.payment_amount)
                if total_payment > contract.contract_amount:
                    # 构建编辑URL，添加return_url参数
                    edit_url = f'/contract/{contract.contract_code}/'
                    if return_url:
                        edit_url += f'?{urlencode({"return_url": return_url})}'

                    anomalies.append({
                        'anomaly_type': '付款超额',
                        'sequence': contract.contract_sequence or '',
                        'code': contract.contract_code,
                        'name': contract.contract_name,
                        'description': f'付款总额({total_payment:.2f}元)超过合同金额({contract.contract_amount:.2f}元)',
                        'edit_url': edit_url
                    })

        return anomalies

    def _get_field_label(self, model_type, field_name):
        """获取字段中文标签"""
        field_labels = {
            'procurement': {
                'winning_bidder': '中标人',
                'winning_amount': '中标金额',
                'winning_contact': '中标人联系方式',
                'evaluation_committee': '评标委员会',
                'payment_method': '付款方式'
            },
            'contract': {
                'party_b_contact_person': '乙方联系人',
                'party_b_handler': '乙方经办人'
            }
        }
        return field_labels.get(model_type, {}).get(field_name, field_name)

    def get_statistics(self, problems, filters=None):
        """
        获取统计数据

        Args:
            problems: 问题列表
            filters: 筛选条件（包含year_filter和project）
        """
        filters = filters or {}
        procurement_count = len(problems['procurement_incomplete'])
        contract_count = len(problems['contract_incomplete'])
        anomaly_count = len(problems['relation_anomalies'])

        # 计算齐全率（应用筛选条件）
        from procurement.models import Procurement
        from contract.models import Contract

        procurement_qs = Procurement.objects.all()
        contract_qs = Contract.objects.all()

        # 应用年度筛选
        if filters.get('year_filter'):
            year = filters['year_filter']
            procurement_qs = procurement_qs.filter(result_publicity_release_date__year=year)
            contract_qs = contract_qs.filter(signing_date__year=year)

        # 应用项目筛选
        if filters.get('project'):
            project_code = filters['project']
            procurement_qs = procurement_qs.filter(project_id=project_code)
            contract_qs = contract_qs.filter(project_id=project_code)

        total_procurement = procurement_qs.count()
        total_contract = contract_qs.count()

        procurement_rate = ((total_procurement - procurement_count) / total_procurement * 100) if total_procurement > 0 else 100
        contract_rate = ((total_contract - contract_count) / total_contract * 100) if total_contract > 0 else 100

        return {
            'procurement_incomplete_count': procurement_count,
            'contract_incomplete_count': contract_count,
            'anomaly_count': anomaly_count,
            'procurement_rate': round(procurement_rate, 1),
            'contract_rate': round(contract_rate, 1)
        }
