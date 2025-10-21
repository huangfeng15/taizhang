"""
测试结算数量统计
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from project.models import Project
from payment.models import Payment
from settlement.models import Settlement
from contract.models import Contract
from django.db.models import Q

# 获取第一个项目测试
project = Project.objects.first()
if not project:
    print("数据库中没有项目")
    exit()

print(f"\n===== 项目: {project.project_name} =====")
print(f"项目编码: {project.project_code}\n")

# 1. Settlement表统计
settlement_count_from_settlement = Settlement.objects.filter(
    main_contract__project=project
).count()
print(f"【Settlement表】统计结算数量: {settlement_count_from_settlement}")

# 2. Payment表中is_settled=True的合同数量(去重)
payment_settled_contracts = Payment.objects.filter(
    contract__project=project,
    is_settled=True
).values('contract').distinct().count()
print(f"【Payment表】is_settled=True的合同数: {payment_settled_contracts}")

# 3. Payment表中settlement_amount不为空的合同数量(去重)
payment_has_settlement_amount = Payment.objects.filter(
    contract__project=project,
    settlement_amount__isnull=False
).values('contract').distinct().count()
print(f"【Payment表】有settlement_amount的合同数: {payment_has_settlement_amount}")

# 4. 综合统计(两种方式的并集)
combined_settlement_count = Contract.objects.filter(
    Q(project=project) & (
        Q(settlement__isnull=False) |  # 在Settlement表中有记录
        Q(payments__is_settled=True) |  # Payment中标记为已结算
        Q(payments__settlement_amount__isnull=False)  # Payment中有结算价
    )
).distinct().count()
print(f"【综合统计】结算数量: {combined_settlement_count}")

# 详细列出已结算的合同
print("\n===== 已结算合同详情 =====")
settled_contracts = Contract.objects.filter(
    Q(project=project) & (
        Q(settlement__isnull=False) |
        Q(payments__is_settled=True) |
        Q(payments__settlement_amount__isnull=False)
    )
).distinct()

for contract in settled_contracts:
    print(f"\n合同: {contract.contract_code} - {contract.contract_name}")
    print(f"  合同类型: {contract.contract_type}")
    
    # 检查Settlement表
    has_settlement = hasattr(contract, 'settlement') and contract.settlement is not None
    print(f"  Settlement表有记录: {has_settlement}")
    
    # 检查Payment表
    has_is_settled = Payment.objects.filter(contract=contract, is_settled=True).exists()
    has_settlement_amount = Payment.objects.filter(contract=contract, settlement_amount__isnull=False).exists()
    print(f"  Payment中is_settled=True: {has_is_settled}")
    print(f"  Payment中有settlement_amount: {has_settlement_amount}")

print("\n===== 总结 =====")
print(f"当前统计方式(仅Settlement表): {settlement_count_from_settlement}")
print(f"建议统计方式(综合两表): {combined_settlement_count}")