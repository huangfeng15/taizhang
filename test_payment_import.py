"""
测试付款导入统计功能
"""
from contract.models import Contract
from payment.models import Payment

print("=" * 60)
print("付款数据统计测试")
print("=" * 60)

# 统计总付款数
total_payments = Payment.objects.count()
print(f"\n总付款记录数: {total_payments}")

# 统计有合同序号的付款
payments_with_sequence = Payment.objects.filter(
    contract__contract_sequence__isnull=False
).exclude(contract__contract_sequence='').count()

print(f"有合同序号的付款: {payments_with_sequence}")
print(f"无合同序号的付款: {total_payments - payments_with_sequence}")

# 显示前5条付款的合同序号
print("\n前5条付款记录的合同序号:")
print("-" * 60)
for p in Payment.objects.select_related('contract').order_by('-payment_date')[:5]:
    seq = p.contract.contract_sequence or "未设置"
    print(f"付款: {p.payment_code}")
    print(f"  合同编号: {p.contract.contract_code}")
    print(f"  合同序号: {seq}")
    print(f"  付款金额: ¥{p.payment_amount}")
    print(f"  付款日期: {p.payment_date}")
    print()

# 按合同统计付款数量
print("按合同统计付款数量 (前10个):")
print("-" * 60)
from django.db.models import Count, Sum
contract_stats = Contract.objects.annotate(
    payment_count=Count('payments'),
    total_paid=Sum('payments__payment_amount')
).filter(payment_count__gt=0).order_by('-payment_count')[:10]

for c in contract_stats:
    seq = c.contract_sequence or "未设置"
    print(f"合同序号: {seq}")
    print(f"  合同编号: {c.contract_code}")
    print(f"  付款笔数: {c.payment_count}")
    print(f"  累计付款: ¥{c.total_paid or 0}")
    print()

print("=" * 60)
print("测试完成")
print("=" * 60)