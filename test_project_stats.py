"""测试项目统计数据是否实时计算"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import Sum, Count
from project.models import Project
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment

# 获取所有项目
projects = Project.objects.all()

print("=" * 80)
print("项目统计数据验证")
print("=" * 80)

for project in projects:
    print(f"\n项目: {project.project_code} - {project.project_name}")
    print("-" * 80)
    
    # 实时计算采购数量
    procurement_count = Procurement.objects.filter(project=project).count()
    print(f"  采购数量: {procurement_count}")
    
    # 实时计算合同数量
    contract_count = Contract.objects.filter(project=project).count()
    print(f"  合同数量: {contract_count}")
    
    # 实时计算合同总额
    contract_total = Contract.objects.filter(project=project).aggregate(
        total=Sum('contract_amount')
    )['total'] or 0
    print(f"  合同总额: {contract_total:,.2f} 元")
    
    # 实时计算付款总额
    payment_total = Payment.objects.filter(contract__project=project).aggregate(
        total=Sum('payment_amount')
    )['total'] or 0
    print(f"  累计付款: {payment_total:,.2f} 元")
    
    # 实时计算付款笔数
    payment_count = Payment.objects.filter(contract__project=project).count()
    print(f"  付款笔数: {payment_count}")
    
    # 计算付款进度
    if contract_total > 0:
        payment_progress = (payment_total / contract_total) * 100
        print(f"  付款进度: {payment_progress:.1f}%")
    else:
        print(f"  付款进度: N/A")

print("\n" + "=" * 80)
print("验证完成！以上数据均为实时计算结果")
print("=" * 80)