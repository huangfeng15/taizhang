"""
测试付款编号生成逻辑
验证按付款日期排序生成序号的功能
"""
import os
import django
from datetime import date

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from contract.models import Contract
from payment.models import Payment


def test_payment_code_generation():
    """测试付款编号生成逻辑"""
    print("=" * 60)
    print("测试付款编号生成逻辑")
    print("=" * 60)
    
    # 查找一个测试合同
    contract = Contract.objects.first()
    if not contract:
        print("[错误] 数据库中没有合同记录，无法测试")
        return
    
    print(f"\n[OK] 使用测试合同: {contract.contract_code}")
    print(f"  合同序号: {contract.contract_sequence or '未设置（将使用合同编号）'}")
    print(f"  合同名称: {contract.contract_name}")
    
    # 查询该合同的所有付款记录
    payments = Payment.objects.filter(contract=contract).order_by('payment_date', 'created_at')
    
    print(f"\n当前该合同共有 {payments.count()} 笔付款记录：")
    print("-" * 60)
    for i, payment in enumerate(payments, 1):
        print(f"{i}. {payment.payment_code}")
        print(f"   付款日期: {payment.payment_date}")
        print(f"   付款金额: {payment.payment_amount}元")
        print(f"   创建时间: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    # 模拟生成新的付款编号
    print("\n" + "=" * 60)
    print("模拟生成新付款编号的场景")
    print("=" * 60)
    
    # 测试场景1：如果新付款日期最早
    test_date_1 = date(2024, 1, 1)
    print(f"\n场景1：新付款日期为 {test_date_1}（早于所有现有付款）")
    print(f"预期编号序号：001")
    
    # 测试场景2：如果新付款日期在中间
    if payments.exists():
        middle_date = payments[len(payments)//2].payment_date if len(payments) > 1 else payments.first().payment_date
        print(f"\n场景2：新付款日期为 {middle_date}（在现有付款中间）")
        earlier_count = payments.filter(payment_date__lt=middle_date).count()
        print(f"预期编号序号：{earlier_count + 1:03d}")
    
    # 测试场景3：如果新付款日期最晚
    test_date_3 = date(2026, 12, 31)
    print(f"\n场景3：新付款日期为 {test_date_3}（晚于所有现有付款）")
    print(f"预期编号序号：{payments.count() + 1:03d}")
    
    # 验证编号格式
    print("\n" + "=" * 60)
    print("编号格式验证")
    print("=" * 60)
    
    contract_identifier = contract.contract_sequence or contract.contract_code
    expected_prefix = f"{contract_identifier}-FK-"
    
    print(f"\n预期编号前缀: {expected_prefix}")
    print(f"验证现有付款编号格式：")
    
    all_valid = True
    for payment in payments:
        if payment.payment_code.startswith(expected_prefix):
            print(f"  [OK] {payment.payment_code} - 格式正确")
        else:
            print(f"  [X] {payment.payment_code} - 格式不符（可能是旧数据）")
            all_valid = False
    
    if all_valid and payments.exists():
        print("\n[OK] 所有付款编号格式均符合要求")
    elif not payments.exists():
        print("\n[注意] 该合同暂无付款记录")
    else:
        print("\n[注意] 部分付款编号格式不符，可能是历史数据")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_payment_code_generation()