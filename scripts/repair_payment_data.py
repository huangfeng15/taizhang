"""
付款数据修复工具
用于修复因导入错误导致的数据不一致问题
"""
import django
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from payment.models import Payment
from contract.models import Contract
from django.db import transaction
from django.utils import timezone
from collections import defaultdict


class PaymentDataRepairer:
    """付款数据修复器"""
    
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.issues = []
        self.fixes = []
    
    def diagnose(self):
        """诊断数据问题"""
        print("=" * 80)
        print("付款数据诊断")
        print("=" * 80)
        
        # 1. 检查编号不连续的合同
        self._check_payment_sequence()
        
        # 2. 检查重复编号
        self._check_duplicate_codes()
        
        # 3. 检查孤立的付款记录
        self._check_orphaned_payments()
        
        # 4. 检查数据完整性
        self._check_data_integrity()
        
        return self.issues
    
    def _check_payment_sequence(self):
        """检查付款编号序列"""
        print("\n1. 检查付款编号序列...")
        
        contracts_with_gaps = []
        contracts = Contract.objects.filter(payments__isnull=False).distinct()
        
        for contract in contracts:
            payments = list(contract.payments.all().order_by('payment_date', 'created_at'))
            identifier = contract.contract_sequence or contract.contract_code
            
            expected_codes = {f"{identifier}-FK-{i:03d}" for i in range(1, len(payments) + 1)}
            actual_codes = {p.payment_code for p in payments}
            
            missing = expected_codes - actual_codes
            extra = actual_codes - expected_codes
            
            if missing or extra:
                issue = {
                    'type': 'sequence_gap',
                    'contract': contract,
                    'identifier': identifier,
                    'total_payments': len(payments),
                    'missing_codes': missing,
                    'extra_codes': extra,
                }
                self.issues.append(issue)
                contracts_with_gaps.append(contract)
        
        if contracts_with_gaps:
            print(f"   [警告] 发现 {len(contracts_with_gaps)} 个合同的付款编号不连续")
        else:
            print(f"   ✓ 所有合同的付款编号都是连续的")
    
    def _check_duplicate_codes(self):
        """检查重复的付款编号"""
        print("\n2. 检查重复付款编号...")
        
        from django.db.models import Count
        
        duplicates = (Payment.objects
                     .values('payment_code')
                     .annotate(count=Count('payment_code'))
                     .filter(count__gt=1))
        
        if duplicates:
            print(f"   [警告] 发现 {len(duplicates)} 个重复的付款编号")
            for dup in duplicates:
                self.issues.append({
                    'type': 'duplicate_code',
                    'payment_code': dup['payment_code'],
                    'count': dup['count'],
                })
        else:
            print(f"   ✓ 未发现重复的付款编号")
    
    def _check_orphaned_payments(self):
        """检查孤立的付款记录（合同不存在）"""
        print("\n3. 检查孤立付款记录...")
        
        orphaned = Payment.objects.filter(contract__isnull=True)
        count = orphaned.count()
        
        if count > 0:
            print(f"   [警告] 发现 {count} 条孤立的付款记录（合同不存在）")
            self.issues.append({
                'type': 'orphaned',
                'count': count,
            })
        else:
            print(f"   ✓ 未发现孤立的付款记录")
    
    def _check_data_integrity(self):
        """检查数据完整性"""
        print("\n4. 检查数据完整性...")
        
        issues_found = []
        
        # 检查金额为0或负数
        invalid_amount = Payment.objects.filter(payment_amount__lte=0)
        if invalid_amount.exists():
            count = invalid_amount.count()
            issues_found.append(f"付款金额<=0: {count}条")
            self.issues.append({
                'type': 'invalid_amount',
                'count': count,
            })
        
        # 检查已结算但无结算金额
        invalid_settlement = Payment.objects.filter(is_settled=True, settlement_amount__isnull=True)
        if invalid_settlement.exists():
            count = invalid_settlement.count()
            issues_found.append(f"已结算但无结算金额: {count}条")
            self.issues.append({
                'type': 'invalid_settlement',
                'count': count,
            })
        
        if issues_found:
            print(f"   [警告] 数据完整性问题:")
            for issue in issues_found:
                print(f"      - {issue}")
        else:
            print(f"   ✓ 数据完整性检查通过")
    
    def repair_sequence_gaps(self):
        """修复编号序列间隙"""
        print("\n" + "=" * 80)
        print("修复付款编号序列")
        print("=" * 80)
        
        sequence_issues = [i for i in self.issues if i['type'] == 'sequence_gap']
        
        if not sequence_issues:
            print("无需修复")
            return
        
        print(f"\n需要修复 {len(sequence_issues)} 个合同的付款编号")
        
        if self.dry_run:
            print("\n【模拟模式】不会实际修改数据\n")
        
        for issue in sequence_issues:
            contract = issue['contract']
            identifier = issue['identifier']
            
            print(f"\n处理合同: {identifier}")
            print(f"  当前付款数: {issue['total_payments']}")
            
            if issue['missing_codes']:
                print(f"  缺失编号: {sorted(issue['missing_codes'])[:5]}...")
            if issue['extra_codes']:
                print(f"  额外编号: {sorted(issue['extra_codes'])[:5]}...")
            
            if not self.dry_run:
                self._renumber_payments(contract)
                print(f"  ✓ 已重新编号")
                self.fixes.append({
                    'contract': identifier,
                    'action': 'renumbered',
                })
    
    def _renumber_payments(self, contract):
        """重新为合同的付款编号"""
        with transaction.atomic():
            payments = list(contract.payments.all().order_by('payment_date', 'created_at'))
            identifier = contract.contract_sequence or contract.contract_code
            
            for i, payment in enumerate(payments, start=1):
                new_code = f"{identifier}-FK-{i:03d}"
                if payment.payment_code != new_code:
                    payment.payment_code = new_code
                    payment.updated_at = timezone.now()
                    payment.save(update_fields=['payment_code', 'updated_at'])
    
    def generate_report(self):
        """生成修复报告"""
        print("\n" + "=" * 80)
        print("修复报告")
        print("=" * 80)
        
        print(f"\n发现问题总数: {len(self.issues)}")
        
        if self.fixes:
            print(f"\n已修复问题: {len(self.fixes)}")
            for fix in self.fixes[:10]:
                print(f"  - 合同 {fix['contract']}: {fix['action']}")
            if len(self.fixes) > 10:
                print(f"  ... 还有 {len(self.fixes) - 10} 项修复")
        elif self.issues and not self.dry_run:
            print("\n未执行任何修复操作")
        
        if self.issues:
            print("\n建议:")
            print("  1. 如果数据问题严重，建议备份数据库后再执行修复")
            print("  2. 可以先使用 --dry-run 模式查看修复效果")
            print("  3. 修复后建议重新导入数据验证")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='付款数据修复工具')
    parser.add_argument('--dry-run', action='store_true', help='模拟模式，不实际修改数据')
    parser.add_argument('--repair', action='store_true', help='执行修复操作')
    args = parser.parse_args()
    
    repairer = PaymentDataRepairer(dry_run=not args.repair)
    
    # 诊断
    issues = repairer.diagnose()
    
    # 修复
    if args.repair or args.dry_run:
        repairer.repair_sequence_gaps()
    
    # 报告
    repairer.generate_report()
    
    print("\n" + "=" * 80)
    print("完成")
    print("=" * 80)


if __name__ == '__main__':
    main()