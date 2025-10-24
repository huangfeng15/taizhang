#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查数据库中的统计数据
"""
import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
import datetime

def main():
    print('=== 数据统计 ===')
    print(f'采购总数: {Procurement.objects.count()}')
    print(f'合同总数: {Contract.objects.count()}')
    print(f'付款总数: {Payment.objects.count()}')
    
    print('\n=== 采购年份分布（按结果公示发布时间） ===')
    for year in range(2019, datetime.datetime.now().year + 1):
        count = Procurement.objects.filter(result_publicity_release_date__year=year).count()
        if count > 0:
            print(f'{year}年: {count}条')
    
    print('\n=== 合同年份分布（按签订日期） ===')
    for year in range(2019, datetime.datetime.now().year + 1):
        count = Contract.objects.filter(signing_date__year=year).count()
        if count > 0:
            print(f'{year}年: {count}条')
    
    print('\n=== 付款年份分布（按付款日期） ===')
    for year in range(2019, datetime.datetime.now().year + 1):
        count = Payment.objects.filter(payment_date__year=year).count()
        if count > 0:
            print(f'{year}年: {count}条')
    
    # 检查是否有数据但没有年份
    print('\n=== 数据完整性检查 ===')
    proc_no_date = Procurement.objects.filter(result_publicity_release_date__isnull=True).count()
    if proc_no_date > 0:
        print(f'警告: {proc_no_date}条采购记录缺少结果公示发布时间')
    
    contract_no_date = Contract.objects.filter(signing_date__isnull=True).count()
    if contract_no_date > 0:
        print(f'警告: {contract_no_date}条合同记录缺少签订日期')
    
    payment_no_date = Payment.objects.filter(payment_date__isnull=True).count()
    if payment_no_date > 0:
        print(f'警告: {payment_no_date}条付款记录缺少付款日期')

if __name__ == '__main__':
    main()