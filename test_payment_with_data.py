"""
测试有付款记录的合同
"""
import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from contract.models import Contract
from payment.models import Payment


def test_with_existing_payments():
    """测试有付款记录的合同"""
    print("=" * 80)
    print("查找有付款记录的合同")
    print("=" * 80)
    
    # 查找有付款记录的合同
    contracts_with_payments = Contract.objects.filter(payments__isnull=False).distinct()
    
    if not contracts_with_payments.exists():
        print("\n[注意] 数据库中没有包含付款记录的合同")
        print("建议：先在系统中添加一些付款记录后再测试")
        return
    
    # 取第一个有付款的合同
    contract = contracts_with_payments.first()
    print(f"\n[OK] 找到合同: {contract.contract_code}")
    print(f"  合同序号: {contract.contract_sequence or '(未设置，将使用合同编号)'}")
    print(f"  合同名称: {contract.contract_name}")
    
    # 获取该合同的所有付款，按付款日期排序
    payments = Payment.objects.filter(contract=contract).order_by('payment_date', 'created_at')
    
    print(f"\n该合同共有 {payments.count()} 笔付款记录：")
    print("-" * 80)
    
    for i, payment in enumerate(payments, 1):
        print(f"{i}. 付款编号: {payment.payment_code}")
        print(f"   付款日期: {payment.payment_date}")
        print(f"   付款金额: {payment.payment_amount:,.2f} 元")
        print(f"   创建时间: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    # 验证编号格式
    print("\n" + "=" * 80)
    print("验证编号是否按付款日期排序")
    print("=" * 80)
    
    contract_identifier = contract.contract_sequence or contract.contract_code
    expected_prefix = f"{contract_identifier}-FK-"
    
    print(f"\n预期编号前缀: {expected_prefix}")
    
    # 检查编号序列
    previous_date = None
    sequence_correct = True
    
    for i, payment in enumerate(payments, 1):
        expected_seq = f"{i:03d}"
        actual_code = payment.payment_code
        
        if actual_code.startswith(expected_prefix):
            actual_seq = actual_code.split('-FK-')[1] if '-FK-' in actual_code else "???"
            if actual_seq == expected_seq:
                status = "[OK]"
            else:
                status = "[注意]"
                sequence_correct = False
            print(f"{status} {actual_code} (预期序号: {expected_seq}, 实际: {actual_seq})")
        else:
            print(f"[注意] {actual_code} (格式不符合预期)")
            sequence_correct = False
        
        print(f"      付款日期: {payment.payment_date}")
        
        # 验证日期是否递增
        if previous_date and payment.payment_date < previous_date:
            print(f"      [警告] 付款日期不是递增的！")
            sequence_correct = False
        
        previous_date = payment.payment_date
        print()
    
    if sequence_correct:
        print("[OK] 所有付款编号序列正确，且按付款日期排序")
    else:
        print("[注意] 付款编号序列或排序存在问题")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == '__main__':
    test_with_existing_payments()