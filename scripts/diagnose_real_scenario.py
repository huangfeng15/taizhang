#!/usr/bin/env python
"""
诊断真实场景中的付款序号重复问题
"""
from bisect import bisect_left, bisect_right, insort
from datetime import date

def simulate_real_import_scenario():
    """模拟真实的导入场景：数据库中已有付款，再次导入相同的数据"""
    print("=" * 60)
    print("真实场景模拟：重复导入相同的付款数据")
    print("=" * 60)
    
    # 场景：数据库中已有3笔付款
    existing_dates = [
        date(2025, 1, 1),
        date(2025, 2, 1),
        date(2025, 3, 1),
    ]
    
    existing_payments = [
        {'code': 'TEST-FK-001', 'date': date(2025, 1, 1), 'amount': 1000},
        {'code': 'TEST-FK-002', 'date': date(2025, 2, 1), 'amount': 2000},
        {'code': 'TEST-FK-003', 'date': date(2025, 3, 1), 'amount': 3000},
    ]
    
    print(f"\n数据库中已有的付款:")
    for p in existing_payments:
        print(f"  {p['code']}: {p['date']} - {p['amount']}元")
    
    # 用户再次导入包含3月份的数据（可能是因为修正了金额）
    new_payments = [
        {'date': date(2025, 3, 1), 'amount': 3500},  # 修正后的金额
    ]
    
    print(f"\n本次尝试导入的付款:")
    for p in new_payments:
        print(f"  {p['date']}: {p['amount']}元")
    
    # 使用现有逻辑计算序号
    assigned_dates = []
    generated_codes = []
    
    print(f"\n使用现有逻辑计算序号:")
    for idx, record in enumerate(new_payments, 1):
        payment_date = record['date']
        
        existing_before = bisect_left(existing_dates, payment_date)
        existing_same = bisect_right(existing_dates, payment_date) - existing_before
        new_before = bisect_left(assigned_dates, payment_date)
        new_same = bisect_right(assigned_dates, payment_date) - new_before
        
        seq = existing_before + existing_same + new_same + 1
        
        insort(assigned_dates, payment_date)
        payment_code = f"TEST-FK-{seq:03d}"
        generated_codes.append(payment_code)
        
        print(f"\n  第{idx}笔付款:")
        print(f"    日期: {payment_date}")
        print(f"    existing_before = {existing_before}")
        print(f"    existing_same = {existing_same}")
        print(f"    new_before = {new_before}")
        print(f"    new_same = {new_same}")
        print(f"    计算: seq = {existing_before} + {existing_same} + {new_same} + 1 = {seq}")
        print(f"    生成编号: {payment_code}")
    
    print(f"\n生成的付款编号: {generated_codes}")
    
    # 检查是否与已有编号冲突
    existing_codes = [p['code'] for p in existing_payments]
    conflicts = [code for code in generated_codes if code in existing_codes]
    
    if conflicts:
        print(f"\n❌ 发现编号冲突！")
        print(f"  冲突的编号: {conflicts}")
        print(f"  这些编号已经存在于数据库中")
    else:
        print(f"\n✓ 没有编号冲突")

def simulate_multiple_contracts():
    """模拟同时导入多个合同的付款数据"""
    print("\n" + "=" * 60)
    print("场景2：批量导入时，在查询现有付款之后、插入之前，")
    print("另一个进程也在导入相同合同的付款")
    print("=" * 60)
    
    # 模拟：进程A和进程B同时导入同一个合同的不同付款
    contract_identifier = "TEST"
    
    # 数据库中已有
    existing_dates = [date(2025, 1, 1)]
    existing_codes = ['TEST-FK-001']
    
    print(f"\n初始状态 - 数据库中已有:")
    print(f"  {existing_codes[0]}: {existing_dates[0]}")
    
    # 进程A要导入的数据
    process_a_payments = [
        {'date': date(2025, 2, 1), 'amount': 2000},
    ]
    
    # 进程B要导入的数据  
    process_b_payments = [
        {'date': date(2025, 3, 1), 'amount': 3000},
    ]
    
    print(f"\n进程A要导入: {process_a_payments[0]['date']} - {process_a_payments[0]['amount']}元")
    print(f"进程B要导入: {process_b_payments[0]['date']} - {process_b_payments[0]['amount']}元")
    
    # 两个进程都查询到相同的existing_dates
    print(f"\n两个进程都读取到相同的现有付款数据")
    
    # 进程A计算序号
    print(f"\n进程A计算序号:")
    assigned_dates_a = []
    for record in process_a_payments:
        payment_date = record['date']
        existing_before = bisect_left(existing_dates, payment_date)
        existing_same = bisect_right(existing_dates, payment_date) - existing_before
        new_before = bisect_left(assigned_dates_a, payment_date)
        new_same = bisect_right(assigned_dates_a, payment_date) - new_before
        seq = existing_before + existing_same + new_same + 1
        code_a = f"{contract_identifier}-FK-{seq:03d}"
        print(f"  生成编号: {code_a}")
    
    # 进程B计算序号（基于相同的existing_dates）
    print(f"\n进程B计算序号:")
    assigned_dates_b = []
    for record in process_b_payments:
        payment_date = record['date']
        existing_before = bisect_left(existing_dates, payment_date)
        existing_same = bisect_right(existing_dates, payment_date) - existing_before
        new_before = bisect_left(assigned_dates_b, payment_date)
        new_same = bisect_right(assigned_dates_b, payment_date) - new_before
        seq = existing_before + existing_same + new_same + 1
        code_b = f"{contract_identifier}-FK-{seq:03d}"
        print(f"  生成编号: {code_b}")
    
    print(f"\n结果: 两个进程可能生成不同的编号，不会冲突")
    print(f"但如果它们尝试插入相同日期的付款，就可能产生相同的编号")

if __name__ == '__main__':
    simulate_real_import_scenario()
    simulate_multiple_contracts()
    
    print("\n" + "=" * 60)
    print("关键发现")
    print("=" * 60)
    print("""
真正的问题场景：
1. 用户导入了付款数据（比如3月份的付款）
2. 发现金额有误，修改Excel后重新导入
3. 导入程序计算出相同的编号（TEST-FK-003）
4. 尝试插入时触发 UNIQUE constraint failed

根本原因：
序号计算逻辑本身是正确的，但是：
- 如果以 update 模式导入，应该更新现有记录而不是创建新记录
- 如果以 skip 模式导入，应该跳过已存在的编号
- 批量创建时没有检查编号是否已存在

之前的修复（检查重复编号）是对的！
但还需要确保序号计算在所有情况下都是一致的。
    """)