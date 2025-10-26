import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from settlement.models import Settlement
from payment.models import Payment
from contract.models import Contract

print("=" * 60)
print("结算数据诊断报告")
print("=" * 60)

# 1. 检查Settlement表
settlements = Settlement.objects.all()
print(f"\n1. Settlement表总记录数: {settlements.count()}")
if settlements.exists():
    print("   前5条记录:")
    for s in settlements[:5]:
        print(f"   - 编号: {s.settlement_code}")
        print(f"     金额: {s.final_amount}")
        print(f"     完成日期: {s.completion_date}")
        print(f"     关联合同: {s.main_contract.contract_code if s.main_contract else 'None'}")
        print()
else:
    print("   ⚠️  Settlement表中没有任何记录！")

# 2. 检查Payment表中标记为已结算的记录
payments_settled = Payment.objects.filter(is_settled=True)
print(f"\n2. Payment表中标记为已结算的记录数: {payments_settled.count()}")
if payments_settled.exists():
    print("   前5条记录:")
    for p in payments_settled[:5]:
        print(f"   - 付款编号: {p.payment_code}")
        print(f"     结算金额: {p.settlement_amount}")
        print(f"     关联合同: {p.contract.contract_code if p.contract else 'None'}")
        print()

# 3. 检查Payment表中有结算金额的记录
payments_with_amount = Payment.objects.filter(settlement_amount__isnull=False)
print(f"\n3. Payment表中有结算金额的记录数: {payments_with_amount.count()}")
if payments_with_amount.exists():
    print("   前5条记录:")
    for p in payments_with_amount[:5]:
        print(f"   - 付款编号: {p.payment_code}")
        print(f"     结算金额: {p.settlement_amount}")
        print(f"     是否结算: {p.is_settled}")
        print()

# 4. 检查主合同关联情况
main_contracts = Contract.objects.filter(file_positioning='主合同')
print(f"\n4. 主合同总数: {main_contracts.count()}")
contracts_with_settlement = 0
for contract in main_contracts[:10]:
    try:
        if hasattr(contract, 'settlement') and contract.settlement:
            contracts_with_settlement += 1
            print(f"   ✓ 合同 {contract.contract_code} 有结算记录")
    except Settlement.DoesNotExist:
        pass

print(f"   前10个主合同中有结算记录的: {contracts_with_settlement}")

# 5. 测试统计函数
print("\n5. 测试get_settlement_statistics函数")
from project.services.statistics import get_settlement_statistics

# 测试不带参数
stats_all = get_settlement_statistics()
print(f"   不带参数调用:")
print(f"   - 总数量: {stats_all.get('total_count', 0)}")
print(f"   - 总金额: {stats_all.get('total_amount', 0)}")

# 测试带年份参数
stats_2024 = get_settlement_statistics(year=2024)
print(f"\n   2024年:")
print(f"   - 总数量: {stats_2024.get('total_count', 0)}")
print(f"   - 总金额: {stats_2024.get('total_amount', 0)}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)