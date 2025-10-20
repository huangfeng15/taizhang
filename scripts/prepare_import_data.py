"""
准备导入数据 - 清理CSV文件并创建标准格式
"""
import pandas as pd
import os

def clean_procurement_csv():
    """清理采购CSV文件"""
    print('正在处理采购数据...')
    df = pd.read_csv('data/imports/采购.csv', skiprows=1, encoding='utf-8-sig')
    
    # 重命名列以匹配导入脚本期望的列名
    column_mapping = {
        '招采编号': '招采编号',
        '采购项目名称': '采购项目名称',
        '采购单位': '采购单位',
        ' 中标单位': '中标单位',  # 注意前面有空格
        '中标单位联系人及方式': '中标单位联系人及方式',
        '采购方式': '采购方式',
        '采购类别': '采购类别',
        '采购预算金额(元)': '采购预算金额(元)',
        '采购控制价（元）': '采购控制价(元)',
        '中标金额（元）': '中标金额(元)',
        '计划结束采购时间': '计划结束采购时间',
        '中标通知书发放日期': '中标通知书发放日期',
        '采购经办人': '采购经办人',
        '需求部门': '需求部门',
    }
    
    # 只保留需要的列
    columns_to_keep = list(column_mapping.keys())
    df = df[columns_to_keep]
    df = df.rename(columns=column_mapping)
    
    # 保存清理后的文件
    output_path = 'data/imports/procurement_clean.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f'[OK] 采购数据已清理: {output_path}')
    print(f'  - 记录数: {len(df)}')
    return output_path

def clean_contract_csv():
    """清理合同CSV文件"""
    print('\n正在处理合同数据...')
    df = pd.read_csv('data/imports/合同.csv', skiprows=1, encoding='utf-8-sig')
    
    # 重命名列
    column_mapping = {
        '招采编号': '关联采购编号',
        '合同编号': '合同编号',
        '合同名称': '合同名称',
        '合同签订经办人': '合同签订经办人',
        '合同类型': '合同类型',
        '甲方': '甲方',
        '乙方': '乙方',
        '含税签约合同价（元）': '含税签约合同价(元)',
        '合同签订日期': '合同签订日期',
        '合同工期/服务期限': '合同工期/服务期限',
        '支付方式': '支付方式',
    }
    
    # 只保留需要的列
    columns_to_keep = list(column_mapping.keys())
    df = df[columns_to_keep]
    df = df.rename(columns=column_mapping)
    
    # 将合同类型统一映射为"主合同"（因为所有导入的都是主合同）
    df['合同类型'] = '主合同'
    
    # 截断过长的工期/服务期限字段（限制为100字符）
    df['合同工期/服务期限'] = df['合同工期/服务期限'].apply(
        lambda x: str(x)[:100] if pd.notna(x) else ''
    )
    
    # 截断过长的支付方式字段
    df['支付方式'] = df['支付方式'].apply(
        lambda x: str(x)[:500] if pd.notna(x) else ''
    )
    
    # 添加合同来源列 - 根据是否有关联采购编号判断
    df['合同来源'] = df['关联采购编号'].apply(
        lambda x: '采购合同' if pd.notna(x) and str(x).strip() and str(x).strip() != '/' else '直接签订'
    )
    
    # 保存清理后的文件
    output_path = 'data/imports/contract_clean.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f'[OK] 合同数据已清理: {output_path}')
    print(f'  - 记录数: {len(df)}')
    print(f'  - 采购合同: {len(df[df["合同来源"] == "采购合同"])}')
    print(f'  - 直接签订: {len(df[df["合同来源"] == "直接签订"])}')
    return output_path

def clean_payment_csv():
    """清理付款CSV文件 - 从宽表转换为长表"""
    print('\n正在处理付款数据...')
    df = pd.read_csv('data/imports/付款.csv', skiprows=3, encoding='utf-8-sig')
    
    # 获取合同编号列和金额列
    contract_col = df.columns[1]  # 第二列是合同编号
    print(f'合同编号列: {contract_col}')
    
    # 找出所有包含金额的月份列(从第44列开始的12个月)
    # 根据实际文件结构,付款金额在特定列
    amount_cols = df.columns[44:56]  # 2025年1-12月的付款列
    print(f'金额列: {list(amount_cols)}')
    
    # 创建长表记录列表
    records = []
    for idx, row in df.iterrows():
        contract_code = str(row[contract_col]).strip()
        if not contract_code or contract_code == 'nan':
            continue
        
        # 遍历每个月份的付款
        for month_idx, col in enumerate(amount_cols, start=1):
            amount = row[col]
            if pd.notna(amount) and amount != '' and amount != 0:
                # 生成付款编号
                payment_code = f"{contract_code}-FK-{month_idx:03d}"
                payment_date = f"2025-{month_idx:02d}-01"
                
                records.append({
                    '付款编号': payment_code,
                    '关联合同编号': contract_code,
                    '实付金额(元)': amount,
                    '付款日期': payment_date,
                })
    
    # 创建DataFrame
    payment_df = pd.DataFrame(records)
    
    # 保存清理后的文件
    output_path = 'data/imports/payment_clean.csv'
    payment_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f'[OK] 付款数据已清理: {output_path}')
    print(f'  - 记录数: {len(payment_df)}')
    return output_path

if __name__ == '__main__':
    print('=' * 60)
    print('数据清理工具')
    print('=' * 60)
    
    try:
        clean_procurement_csv()
        clean_contract_csv()
        clean_payment_csv()
        
        print('\n' + '=' * 60)
        print('数据清理完成!')
        print('=' * 60)
    except Exception as e:
        print(f'\n[ERROR] 清理失败: {str(e)}')
        import traceback
        traceback.print_exc()