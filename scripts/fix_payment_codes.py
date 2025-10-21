"""
修复已导入的付款记录编号
将旧格式的付款编号更新为新格式（按付款日期排序）
"""
import os
import sys
import django
from datetime import datetime

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from payment.models import Payment
from contract.models import Contract
from django.db import transaction


def fix_payment_codes(dry_run=True):
    """
    修复付款编号
    
    Args:
        dry_run: 如果为True，只显示将要执行的操作，不实际修改数据库
    """
    print("=" * 80)
    print("付款编号修复工具")
    print("=" * 80)
    
    if dry_run:
        print("\n[预览模式] 不会实际修改数据库")
    else:
        print("\n[执行模式] 将实际修改数据库")
        print("警告：此操作将修改所有付款记录的编号！")
        print("开始执行修复...")
    
    print("\n开始扫描付款记录...")
    
    # 获取所有合同
    contracts = Contract.objects.all().order_by('contract_code')
    
    total_contracts = contracts.count()
    total_payments = 0
    updated_payments = 0
    
    print(f"\n找到 {total_contracts} 个合同")
    
    # 按合同处理付款记录
    for contract_idx, contract in enumerate(contracts, 1):
        # 获取该合同的所有付款记录，按付款日期排序
        payments = Payment.objects.filter(contract=contract).order_by('payment_date', 'created_at')
        
        if not payments.exists():
            continue
        
        print(f"\n[{contract_idx}/{total_contracts}] 处理合同: {contract.contract_code}")
        print(f"  合同序号: {contract.contract_sequence or '(未设置)'}")
        print(f"  付款记录数: {payments.count()}")
        
        # 使用合同序号或合同编号
        contract_identifier = contract.contract_sequence or contract.contract_code
        
        # 为每笔付款生成新编号
        for seq, payment in enumerate(payments, 1):
            old_code = payment.payment_code
            new_code = f"{contract_identifier}-FK-{seq:03d}"
            
            total_payments += 1
            
            if old_code != new_code:
                updated_payments += 1
                print(f"  [{seq}] {payment.payment_date}")
                print(f"      旧编号: {old_code}")
                print(f"      新编号: {new_code}")
                print(f"      金额: {payment.payment_amount:,.2f}元")
                
                # 如果不是预览模式，执行更新
                if not dry_run:
                    try:
                        with transaction.atomic():
                            # 直接更新数据库，避免触发save方法的验证
                            Payment.objects.filter(payment_code=old_code).update(payment_code=new_code)
                            print(f"      [OK] 已更新")
                    except Exception as e:
                        print(f"      [错误] 更新失败: {str(e)}")
            else:
                print(f"  [{seq}] {payment.payment_date} - {old_code} (无需更新)")
    
    # 打印摘要
    print("\n" + "=" * 80)
    print("修复摘要")
    print("=" * 80)
    print(f"扫描的合同数: {total_contracts}")
    print(f"扫描的付款记录数: {total_payments}")
    print(f"需要更新的记录数: {updated_payments}")
    
    if dry_run:
        print("\n这是预览模式，未实际修改数据库")
        print("要执行实际修复，请运行: python scripts/fix_payment_codes.py --execute")
    else:
        print(f"\n[完成] 已成功更新 {updated_payments} 条付款记录的编号")
    
    print("=" * 80)


if __name__ == '__main__':
    import sys
    
    # 设置UTF-8编码输出
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # 检查命令行参数
    if '--execute' in sys.argv or '-e' in sys.argv:
        print("\n警告：即将执行实际修复操作！")
        print("建议先备份数据库！")
        fix_payment_codes(dry_run=False)
    else:
        print("\n这是预览模式，查看将要执行的操作")
        print("要执行实际修复，请添加 --execute 参数")
        print("\n示例: python scripts/fix_payment_codes.py --execute")
        print()
        fix_payment_codes(dry_run=True)