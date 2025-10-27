#!/usr/bin/env python
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment

def check_data():
    print("=== 数据库检查 ===")
    print(f'采购记录总数: {Procurement.objects.count()}')
    print(f'合同记录总数: {Contract.objects.count()}')
    print(f'付款记录总数: {Payment.objects.count()}')
    
    print("\n=== 采购记录 ===")
    for p in Procurement.objects.all()[:5]:
        print(f'采购: {p.procurement_code} - {p.project_name}')
        
        # 检查关联合同
        contracts = Contract.objects.filter(procurement=p)
        print(f'  关联合同数量: {contracts.count()}')
        
        for contract in contracts:
            print(f'    合同: {contract.contract_code} - {contract.contract_name}')
            
            # 检查付款记录
            payments = Payment.objects.filter(contract=contract)
            print(f'      付款记录数量: {payments.count()}')
            
            total_payment = payments.aggregate(total=Sum('payment_amount'))['total'] or 0
            print(f'      累计付款: {total_payment}')
    
    print("\n=== 直接检查付款记录 ===")
    for payment in Payment.objects.all()[:5]:
        print(f'付款: {payment.payment_code} - {payment.payment_amount} - 合同: {payment.contract.contract_name if payment.contract else "无"}')

if __name__ == '__main__':
    from django.db.models import Sum
    check_data()