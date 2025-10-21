#!/usr/bin/env python
"""
数据库查询工具 - 支持命令行参数执行SQL查询
"""

import os
import sys
import django
import argparse

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def execute_query(sql, params=None):
    """执行SQL查询并返回结果"""
    cursor = connection.cursor()
    
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        # 判断是否为查询语句
        if sql.strip().upper().startswith(('SELECT', 'PRAGMA', 'EXPLAIN')):
            # 获取列名
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
            else:
                columns = []
                rows = []
            
            return {
                'columns': columns,
                'rows': rows,
                'count': len(rows)
            }
        else:
            # 非查询语句，返回影响的行数
            connection.commit()
            return {
                'affected_rows': cursor.rowcount,
                'message': '操作成功'
            }
            
    except Exception as e:
        connection.rollback()
        return {
            'error': str(e)
        }

def format_output(result, format_type='table'):
    """格式化输出结果"""
    if 'error' in result:
        print(f"错误: {result['error']}")
        return
    
    if 'affected_rows' in result:
        print(f"成功影响 {result['affected_rows']} 行")
        print(result['message'])
        return
    
    if not result['rows']:
        print("查询结果为空")
        return
    
    columns = result['columns']
    rows = result['rows']
    
    if format_type == 'table':
        # 表格格式输出
        # 计算每列最大宽度
        col_widths = [len(col) for col in columns]
        for row in rows:
            for i, value in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(value)) if value is not None else 4)
        
        # 打印分隔线
        separator = '+' + '+'.join('-' * (width + 2) for width in col_widths) + '+'
        print(separator)
        
        # 打印列名
        header = '|' + '|'.join(f' {col:<{col_widths[i]}} ' for i, col in enumerate(columns)) + '|'
        print(header)
        print(separator)
        
        # 打印数据行
        for row in rows:
            row_str = '|' + '|'.join(f' {str(value) if value is not None else "NULL":<{col_widths[i]}} ' for i, value in enumerate(row)) + '|'
            print(row_str)
        
        print(separator)
        print(f"\n共 {result['count']} 行记录")
        
    elif format_type == 'csv':
        # CSV格式输出
        print(','.join(columns))
        for row in rows:
            print(','.join(str(value) if value is not None else '' for value in row))
            
    elif format_type == 'json':
        # JSON格式输出
        import json
        data = []
        for row in rows:
            data.append(dict(zip(columns, row)))
        print(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser(description='数据库查询工具')
    parser.add_argument('sql', nargs='?', help='要执行的SQL语句')
    parser.add_argument('-f', '--file', help='从文件读取SQL语句')
    parser.add_argument('--format', choices=['table', 'csv', 'json'], default='table', 
                       help='输出格式 (默认: table)')
    parser.add_argument('--list-tables', action='store_true', help='列出所有表')
    parser.add_argument('--describe', metavar='TABLE', help='描述表结构')
    parser.add_argument('--count', metavar='TABLE', help='统计表记录数')
    
    args = parser.parse_args()
    
    # 处理特殊命令
    if args.list_tables:
        sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        result = execute_query(sql)
        format_output(result, args.format)
        return
    
    if args.describe:
        sql = f"PRAGMA table_info({args.describe});"
        result = execute_query(sql)
        format_output(result, args.format)
        return
    
    if args.count:
        sql = f"SELECT COUNT(*) FROM {args.count};"
        result = execute_query(sql)
        if 'rows' in result and result['rows']:
            print(f"表 {args.count} 共有 {result['rows'][0][0]} 条记录")
        else:
            print("查询失败")
        return
    
    # 获取SQL语句
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                sql = f.read().strip()
        except Exception as e:
            print(f"读取文件失败: {e}")
            return
    elif args.sql:
        sql = args.sql
    else:
        # 交互式输入
        print("请输入SQL语句 (输入 'exit' 退出):")
        while True:
            try:
                sql = input("SQL> ").strip()
                if sql.lower() in ['exit', 'quit']:
                    break
                if not sql:
                    continue
                
                result = execute_query(sql)
                format_output(result, args.format)
                print()
            except KeyboardInterrupt:
                print("\n再见!")
                break
        return
    
    # 执行SQL
    if sql:
        result = execute_query(sql)
        format_output(result, args.format)
    else:
        print("未提供SQL语句")

if __name__ == '__main__':
    main()