"""
付款数据验证器
提供数据完整性检查和验证功能
"""
from django.core.exceptions import ValidationError
from decimal import Decimal


class PaymentDataValidator:
    """付款数据验证器"""
    
    @staticmethod
    def validate_payment_data(payment_data):
        """
        验证付款数据的完整性
        
        Args:
            payment_data: 付款数据字典，包含以下字段：
                - contract: 合同对象
                - payment_amount: 付款金额
                - payment_date: 付款日期
                - settlement_amount: 结算金额（可选）
                - is_settled: 是否已结算
        
        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []
        
        # 必填字段检查
        if not payment_data.get('contract'):
            errors.append('缺少关联合同')
        
        if payment_data.get('payment_amount') is None:
            errors.append('缺少付款金额')
        
        if not payment_data.get('payment_date'):
            errors.append('缺少付款日期')
        
        # 结算逻辑检查
        if payment_data.get('is_settled'):
            if payment_data.get('settlement_amount') is None:
                errors.append('已标记为已结算但缺少结算金额')
        
        # 业务规则检查
        if payment_data.get('settlement_amount') and payment_data.get('payment_amount'):
            settlement_amount = Decimal(str(payment_data['settlement_amount']))
            payment_amount = Decimal(str(payment_data['payment_amount']))
            
            # 警告：付款金额超过结算金额
            if payment_amount > settlement_amount:
                errors.append(
                    f'警告：付款金额({payment_amount})超过结算金额({settlement_amount})'
                )
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_batch_uniqueness(payment_codes):
        """
        验证批量付款编号的唯一性
        
        Args:
            payment_codes: 付款编号列表
        
        Returns:
            tuple: (is_valid, duplicates)
        """
        from collections import Counter
        
        counter = Counter(payment_codes)
        duplicates = {code: count for code, count in counter.items() if count > 1}
        
        return len(duplicates) == 0, duplicates
    
    @staticmethod
    def validate_contract_payment_sequence(contract, new_payments):
        """
        验证合同的付款序列完整性
        
        Args:
            contract: 合同对象
            new_payments: 新增付款列表
        
        Returns:
            tuple: (is_valid, warnings)
        """
        from payment.models import Payment
        
        warnings = []
        
        # 获取现有付款
        existing_payments = list(
            Payment.objects.filter(contract=contract)
            .order_by('payment_date', 'created_at')
        )
        
        # 合并新旧付款
        all_payments = existing_payments + new_payments
        all_payments.sort(key=lambda p: (p.payment_date, getattr(p, 'created_at', None)))
        
        # 检查编号连续性
        identifier = contract.contract_sequence or contract.contract_code
        expected_codes = [f"{identifier}-FK-{i:03d}" for i in range(1, len(all_payments) + 1)]
        actual_codes = [p.payment_code for p in all_payments if p.payment_code]
        
        missing_codes = set(expected_codes) - set(actual_codes)
        if missing_codes:
            warnings.append(f'存在缺失的付款编号: {sorted(missing_codes)}')
        
        return len(warnings) == 0, warnings