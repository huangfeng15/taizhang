"""
测试创建新付款记录时的编号生成
"""
import os
import django
from datetime import date
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from contract.models import Contract
from payment.models import Payment


def test_new_payment_creation():
    """测试新付款记录的编号生成"""
    print("=" * 80)
    print("测试新付款记录编号生成")
    print("=" * 80)
    
    # 查找有付款记录的合同
    contracts_with_payments = Contract.objects.filter(payments__isnull=False).distinct()
    
    if not contracts_with_payments.exists():
        print("\n[注意] 没有找到有付款记录的合同，使用第一个合同进行测试")
        contract = Contract.objects.first()
        if not contract:
            print("[错误] 数据库中没有合同记录")
            return
    else:
        contract = contracts_with_payments.first()
    
    print(f"\n[OK] 测试合同: {contract.contract_code}")
    print(f"  合同序号: {contract.contract_sequence or '(未设置)'}")
    print(f"  合同名称: {contract.contract_name}")
    
    # 显示现有付款记录
    existing_payments = Payment.objects.filter(contract=contract).order_by('payment_date', 'created_at')
    print(f"\n现有付款记录数: {existing_payments.count()}")
    
    if existing_payments.exists():
        print("\n现有付款记录：")
        for i, p in enumerate(existing_payments, 1):
            print(f"  {i}. {p.payment_code} - {p.payment_date} - {p.payment_amount:,.2f}元")
    
    # 测试不同日期的付款编号生成
    print("\n" + "=" * 80)
    print("模拟生成新付款编号（不实际保存到数据库）")
    print("=" * 80)
    
    contract_identifier = contract.contract_sequence or contract.contract_code
    
    test_scenarios = [
        ("最早日期", date(2024, 1, 1)),
        ("中间日期", date(2025, 6, 15)),
        ("最晚日期", date(2026, 12, 31)),
    ]
    
    for scenario_name, test_date in test_scenarios:
        print(f"\n场景: {scenario_name} ({test_date})")
        
        # 计算该日期下的序号
        sequence = 1
        for payment in existing_payments:
            if payment.payment_date < test_date:
                sequence += 1
            elif payment.payment_date == test_date:
                # 同一天，假设新付款会排在后面
                sequence += 1
        
        expected_code = f"{contract_identifier}-FK-{sequence:03d}"
        print(f"  预期编号: {expected_code}")
        print(f"  序号位置: 第 {sequence} 笔付款")
    
    print("\n" + "=" * 80)
    print("关键说明")
    print("=" * 80)
    print("\n1. 新逻辑使用 '合同序号-FK-序号' 格式")
    print("   - 如果合同有序号（contract_sequence），使用序号")
    print("   - 如果没有序号，则使用合同编号（contract_code）")
    print("\n2. 序号按付款日期排序")
    print("   - 最早的付款日期为 001")
    print("   - 同一天的多笔付款按创建时间排序")
    print("\n3. 现有数据不会自动更新")
    print("   - 旧的付款记录保持原有编号不变")
    print("   - 新创建的付款记录使用新格式")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == '__main__':
    test_new_payment_creation()