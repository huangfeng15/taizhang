import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

# 获取数据库游标
cursor = connection.cursor()

# 查询所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# 输出结果
print(f'数据库表总数: {len(tables)}')
print('\n表列表:')
for i, table in enumerate(tables, 1):
    print(f'{i}. {table[0]}')