"""
同步结算信息到付款记录的管理命令

用途：
1. 初次部署时同步历史数据
2. 修复数据不一致问题
3. 手动触发批量同步

使用方法：
    python manage.py sync_settlement_to_payments
    python manage.py sync_settlement_to_payments --dry-run  # 仅预览，不实际修改
    python manage.py sync_settlement_to_payments --contract=HT2025001  # 只同步指定合同
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from settlement.models import Settlement
from payment.models import Payment


class Command(BaseCommand):
    help = '同步结算信息到相关付款记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅预览同步结果，不实际修改数据库',
        )
        parser.add_argument(
            '--contract',
            type=str,
            help='只同步指定合同编号的付款记录',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        contract_code = options.get('contract')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('*** 预览模式：不会实际修改数据 ***\n'))
        
        # 获取所有有结算价的结算记录
        settlements_query = Settlement.objects.filter(final_amount__isnull=False)
        
        if contract_code:
            settlements_query = settlements_query.filter(
                main_contract__contract_code=contract_code
            )
        
        settlements = settlements_query.select_related('main_contract')
        
        if not settlements.exists():
            self.stdout.write(self.style.WARNING('没有找到需要同步的结算记录'))
            return
        
        self.stdout.write(f'找到 {settlements.count()} 条结算记录需要同步\n')
        
        total_updated = 0
        total_contracts = 0
        
        for settlement in settlements:
            main_contract = settlement.main_contract
            
            if not main_contract:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ 结算记录 {settlement.settlement_code} 没有关联合同，跳过'
                    )
                )
                continue
            
            # 获取主合同及所有补充协议的编号
            contract_codes = [main_contract.contract_code]
            supplement_codes = list(
                main_contract.supplements.values_list('contract_code', flat=True)
            )
            contract_codes.extend(supplement_codes)
            
            # 查找所有相关付款记录
            related_payments = Payment.objects.filter(
                contract__contract_code__in=contract_codes
            )
            
            payment_count = related_payments.count()
            
            if payment_count == 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'  合同 {main_contract.contract_code} 没有付款记录，跳过'
                    )
                )
                continue
            
            self.stdout.write(
                f'  合同 {main_contract.contract_code}:'
            )
            self.stdout.write(
                f'    - 结算价: {settlement.final_amount} 元'
            )
            self.stdout.write(
                f'    - 完成日期: {settlement.completion_date or "未设置"}'
            )
            self.stdout.write(
                f'    - 关联付款记录: {payment_count} 条'
            )
            
            if supplement_codes:
                self.stdout.write(
                    f'    - 包含补充协议: {", ".join(supplement_codes)}'
                )
            
            if not dry_run:
                # 实际更新数据
                with transaction.atomic():
                    updated_count = related_payments.update(
                        is_settled=True,
                        settlement_completion_date=settlement.completion_date,
                        settlement_archive_date=settlement.created_at.date() if settlement.created_at else None,
                        settlement_amount=settlement.final_amount
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'    ✓ 已更新 {updated_count} 条付款记录'
                        )
                    )
                    total_updated += updated_count
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'    [预览] 将更新 {payment_count} 条付款记录'
                    )
                )
                total_updated += payment_count
            
            total_contracts += 1
            self.stdout.write('')  # 空行分隔
        
        # 输出汇总信息
        self.stdout.write('=' * 60)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[预览] 共涉及 {total_contracts} 个合同，'
                    f'将更新 {total_updated} 条付款记录\n'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    '提示：去掉 --dry-run 参数即可实际执行同步\n'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ 同步完成！共处理 {total_contracts} 个合同，'
                    f'更新 {total_updated} 条付款记录\n'
                )
            )