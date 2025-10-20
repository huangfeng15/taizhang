"""
将Excel文件转换为CSV格式的脚本
"""
import pandas as pd
import os
import sys

def convert_excel_to_csv(excel_path, output_dir='data/imports'):
    """
    将Excel文件转换为CSV格式
    
    Args:
        excel_path: Excel文件路径
        output_dir: 输出目录
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取Excel文件
    print(f'正在读取: {excel_path}')
    
    # 获取所有sheet名称
    xl_file = pd.ExcelFile(excel_path)
    print(f'发现 {len(xl_file.sheet_names)} 个工作表: {xl_file.sheet_names}')
    
    # 读取第一个sheet（通常是数据表）
    df = pd.read_excel(excel_path, sheet_name=0)
    
    # 生成输出文件名
    base_name = os.path.splitext(os.path.basename(excel_path))[0]
    output_path = os.path.join(output_dir, f'{base_name}.csv')
    
    # 保存为CSV
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f'[OK] 已转换: {output_path}')
    print(f'  - 行数: {len(df)}')
    print(f'  - 列数: {len(df.columns)}')
    print(f'  - 列名: {list(df.columns)[:5]}...' if len(df.columns) > 5 else f'  - 列名: {list(df.columns)}')
    
    return output_path

if __name__ == '__main__':
    # 定义要转换的文件
    files = [
        '各项目台账/采购.xlsx',
        '各项目台账/合同.xlsx',
        '各项目台账/付款.xlsx',
    ]
    
    print('=' * 60)
    print('Excel 转 CSV 转换工具')
    print('=' * 60)
    
    for file_path in files:
        try:
            if not os.path.exists(file_path):
                print(f'[ERROR] 文件不存在: {file_path}')
                continue
            
            convert_excel_to_csv(file_path)
            print()
        except Exception as e:
            print(f'[ERROR] 转换失败 {file_path}: {str(e)}')
            print()
    
    print('=' * 60)
    print('转换完成!')
    print('=' * 60)