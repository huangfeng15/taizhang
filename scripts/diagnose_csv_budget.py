#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断CSV文件中的预算金额字段
"""
import csv
import sys
import os
import chardet

def detect_encoding(file_path):
    """检测文件编码"""
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)
    result = chardet.detect(raw_data)
    return result['encoding'], result['confidence']

def diagnose_csv(file_path):
    """诊断CSV文件"""
    print(f"=" * 80)
    print(f"诊断文件: {file_path}")
    print(f"=" * 80)
    
    # 检测编码
    encoding, confidence = detect_encoding(file_path)
    print(f"\n文件编码: {encoding} (置信度: {confidence:.2%})")
    
    # 尝试不同的编码读取
    encodings_to_try = [encoding, 'utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030']
    
    for enc in encodings_to_try:
        try:
            print(f"\n尝试使用编码: {enc}")
            with open(file_path, 'r', encoding=enc) as f:
                reader = csv.DictReader(f)
                
                # 打印列名
                print(f"\n找到 {len(reader.fieldnames)} 个列:")
                for i, col in enumerate(reader.fieldnames, 1):
                    print(f"  {i}. [{col}]")
                
                # 检查是否有预算金额列
                budget_columns = [col for col in reader.fieldnames if '预算' in col or '金额' in col]
                print(f"\n找到 {len(budget_columns)} 个可能的预算金额列:")
                for col in budget_columns:
                    print(f"  - [{col}]")
                
                # 读取前5行数据
                print(f"\n前5行数据:")
                for row_num, row in enumerate(reader, start=2):
                    if row_num > 6:  # 只显示前5行
                        break
                    
                    print(f"\n第 {row_num} 行:")
                    
                    # 显示预算相关字段
                    for col in budget_columns:
                        value = row.get(col, '')
                        print(f"  {col}: [{value}] (类型: {type(value).__name__}, 长度: {len(str(value))})")
                        
                        # 显示字符的十六进制表示
                        if value:
                            hex_repr = ' '.join(f'{ord(c):04x}' for c in str(value)[:20])
                            print(f"    十六进制: {hex_repr}")
                
                print(f"\n✓ 成功使用编码 {enc} 读取文件")
                return True
                
        except Exception as e:
            print(f"  ✗ 编码 {enc} 失败: {str(e)}")
            continue
    
    print(f"\n所有编码尝试都失败了!")
    return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python diagnose_csv_budget.py <csv文件路径>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        sys.exit(1)
    
    diagnose_csv(file_path)