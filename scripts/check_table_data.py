import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

# 业务表列表
business_tables = [
    'contract_contract',
    'payment_payment',
    'settlement_settlement',
    'supplier_eval_supplierevaluation',
    'procurement_procurement'
]

# 获取数据库游标
cursor = connection.cursor()

print('业务数据表统计：\n')
total_records = 0

for table in business_tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table};")
    count = cursor.fetchone()[0]
    total_records += count
    
    # 中文表名映射
    table_names = {
        'contract_contract': '合同表',
        'payment_payment': '付款表',
        'settlement_settlement': '结算表',
        'supplier_eval_supplierevaluation': '供应商评价表',
        'procurement_procurement': '采购表'
    }
    
    status = '✓ 有数据' if count > 0 else '✗ 空表'
    print(f'{table_names[table]:15} ({table}): {count:6} 条记录  {status}')

print(f'\n总计: {total_records} 条业务数据记录')