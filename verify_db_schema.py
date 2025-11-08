"""验证 SupplierEvaluation 表结构"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def check_table_schema():
    with connection.cursor() as cursor:
        # 获取表结构
        cursor.execute("PRAGMA table_info(supplier_eval_supplierevaluation);")
        columns = cursor.fetchall()
        
        print("=== supplier_eval_supplierevaluation 表结构 ===")
        print(f"{'ID':<5} {'字段名':<35} {'类型':<15} {'非空':<8} {'默认值':<15} {'主键'}")
        print("-" * 100)
        
        for col in columns:
            cid, name, type_, notnull, dflt_value, pk = col
            print(f"{cid:<5} {name:<35} {type_:<15} {notnull:<8} {str(dflt_value):<15} {pk}")
        
        # 检查 comprehensive_score 字段是否存在
        column_names = [col[1] for col in columns]
        
        print("\n=== 关键字段检查 ===")
        required_fields = [
            'comprehensive_score',
            'last_evaluation_score',
            'score_2019', 'score_2020', 'score_2021',
            'score_2022', 'score_2023', 'score_2024', 'score_2025',
            'irregular_evaluation_1', 'irregular_evaluation_2',
            'remarks'
        ]
        
        for field in required_fields:
            status = "✓ 存在" if field in column_names else "✗ 缺失"
            print(f"{field:<35} {status}")

if __name__ == '__main__':
    check_table_schema()