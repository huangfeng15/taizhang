#!/usr/bin/env python
"""
诊断付款序号计算逻辑问题
"""
from bisect import bisect_left, bisect_right, insort
from datetime import date

def simulate_seq_calculation_bug():
    """模拟现有逻辑的序号计算问题"""
    print("=" * 60)
    print("模拟付款序号计算 - 现有逻辑（有BUG）")
    print("=" * 60)
    
    # 假设数据库中已有的付款日期
    existing_dates = [
        date(2025, 1, 1),
        date(2025, 2, 1),
    ]
    print(f"\n数据库已有付款日期: {existing_dates}")
    
    # 假设本次要导入的付款（同一个合同，相同日期的多笔付款）
    new_payments = [
        {'date': date(2025, 3, 1), 'amount': 1000},
        {'date': date(2025, 3, 1), 'amount': 2000},  # 相同日期
        {'date': date(2025, 3, 1), 'amount': 3000},  # 相同日期
    ]
    
    print(f"\n本次导入的付款:")
    for p in new_payments:
        print(f"  - {p['date']}: {p['amount']}元")
    
    # 模拟现有的序号计算逻辑
    assigned_dates = []
    generated_codes = []
    
    print(f"\n开始计算序号（现有逻辑）:")
    for idx, record in enumerate(new_payments, 1):
        payment_date = record['date']
        
        existing_before = bisect_left(existing_dates, payment_date)
        existing_same = bisect_right(existing_dates, payment_date) - existing_before
        new_before = bisect_left(assigned_dates, payment_date)
        new_same = bisect_right(assigned_dates, payment_date) - new_before
        
        # 这里的计算有问题！
        seq = existing_before + existing_same + new_same + 1
        
        insort(assigned_dates, payment_date)
        payment_code = f"TEST-FK-{seq:03d}"
        generated_codes.append(payment_code)
        
        print(f"\n  第{idx}笔付款:")
        print(f"    日期: {payment_date}")
        print(f"    existing_before = {existing_before} (数据库中早于该日期的付款数)")
        print(f"    existing_same = {existing_same} (数据库中相同日期的付款数)")
        print(f"    new_before = {new_before} (本批次中早于该日期的付款数)")
        print(f"    new_same = {new_same} (本批次中相同日期且已分配的付款数)")
        print(f"    计算: seq = {existing_before} + {existing_same} + {new_same} + 1 = {seq}")
        print(f"    生成编号: {payment_code}")
    
    print(f"\n生成的付款编号列表: {generated_codes}")
    
    # 检查是否有重复
    if len(generated_codes) != len(set(generated_codes)):
        print(f"\n❌ 发现重复编号！")
        from collections import Counter
        counter = Counter(generated_codes)
        for code, count in counter.items():
            if count > 1:
                print(f"  编号 {code} 重复了 {count} 次")
    else:
        print(f"\n✓ 没有重复编号")

def simulate_correct_calculation():
    """演示正确的序号计算逻辑"""
    print("\n" + "=" * 60)
    print("正确的付款序号计算逻辑")
    print("=" * 60)
    
    # 假设数据库中已有的付款日期
    existing_dates = [
        date(2025, 1, 1),
        date(2025, 2, 1),
    ]
    print(f"\n数据库已有付款日期: {existing_dates}")
    
    # 假设本次要导入的付款
    new_payments = [
        {'date': date(2025, 3, 1), 'amount': 1000},
        {'date': date(2025, 3, 1), 'amount': 2000},
        {'date': date(2025, 3, 1), 'amount': 3000},
    ]
    
    print(f"\n本次导入的付款:")
    for p in new_payments:
        print(f"  - {p['date']}: {p['amount']}元")
    
    # 正确的逻辑：合并所有日期后重新排序
    all_dates = existing_dates + [p['date'] for p in new_payments]
    all_dates.sort()
    
    print(f"\n合并后的所有付款日期: {all_dates}")
    
    # 为每个新付款分配序号
    generated_codes = []
    
    print(f"\n开始计算序号（正确逻辑）:")
    for idx, record in enumerate(new_payments, 1):
        payment_date = record['date']
        
        # 计算这笔付款在全部付款中的位置
        # 找到所有小于等于该日期的付款数量
        seq = sum(1 for d in all_dates if d <= payment_date)
        
        # 如果同一日期有多笔，需要为后续的付款递增序号
        # 简化处理：找到该日期之前已分配的序号
        already_assigned = len([c for c in generated_codes])
        seq = len(existing_dates) + already_assigned + 1
        
        payment_code = f"TEST-FK-{seq:03d}"
        generated_codes.append(payment_code)
        
        print(f"\n  第{idx}笔付款:")
        print(f"    日期: {payment_date}")
        print(f"    序号: {seq}")
        print(f"    生成编号: {payment_code}")
    
    print(f"\n生成的付款编号列表: {generated_codes}")
    
    # 检查是否有重复
    if len(generated_codes) != len(set(generated_codes)):
        print(f"\n❌ 发现重复编号！")
    else:
        print(f"\n✓ 没有重复编号")

if __name__ == '__main__':
    simulate_seq_calculation_bug()
    simulate_correct_calculation()
    
    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    print("""
问题原因：
在计算序号时，公式 `seq = existing_before + existing_same + new_same + 1`
对于同一日期的多笔付款，会导致 new_same 每次都从0开始计数，
结果是同一日期的多笔付款会生成相同的序号。

正确做法：
应该使用简单的累加逻辑：
seq = len(existing_dates) + len(already_assigned) + 1

或者更准确地说：
1. 获取数据库中该合同的所有现有付款数量
2. 加上本批次中已处理的付款数量
3. 加1得到当前付款的序号
    """)