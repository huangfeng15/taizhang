from django.core.management.base import BaseCommand
from django.db import connection
from project.models import Project
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement
from supplier_eval.models import SupplierEvaluation


class Command(BaseCommand):
    help = '清空所有数据表的数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='确认清空数据，避免误操作',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.ERROR('请添加 --confirm 参数确认清空数据操作')
            )
            self.stdout.write('示例: python manage.py clear_all_data --confirm')
            return

        self.stdout.write('开始清空数据库...')

        try:
            # 先清空有外键约束的表
            self.stdout.write('正在处理外键约束...')
            
            # 清空付款记录
            count = Payment.objects.count()
            if count > 0:
                self.stdout.write(f'正在清空付款记录 ({count} 条记录)...')
                Payment.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('付款记录 已清空'))
            
            # 清空结算信息
            count = Settlement.objects.count()
            if count > 0:
                self.stdout.write(f'正在清空结算信息 ({count} 条记录)...')
                Settlement.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('结算信息 已清空'))
            
            # 清空供应商评价
            count = SupplierEvaluation.objects.count()
            if count > 0:
                self.stdout.write(f'正在清空供应商评价 ({count} 条记录)...')
                SupplierEvaluation.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('供应商评价 已清空'))
            
            # 处理合同的父合同外键约束
            self.stdout.write('正在处理合同的外键约束...')
            with connection.cursor() as cursor:
                # 先解除所有合同的父合同关系
                cursor.execute("UPDATE contract_contract SET parent_contract_id = NULL")
                self.stdout.write(self.style.SUCCESS('已解除合同的父合同关系'))
            
            # 现在可以安全清空合同
            count = Contract.objects.count()
            if count > 0:
                self.stdout.write(f'正在清空合同信息 ({count} 条记录)...')
                Contract.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('合同信息 已清空'))
            
            # 清空采购信息
            count = Procurement.objects.count()
            if count > 0:
                self.stdout.write(f'正在清空采购信息 ({count} 条记录)...')
                Procurement.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('采购信息 已清空'))
            
            # 清空项目信息
            count = Project.objects.count()
            if count > 0:
                self.stdout.write(f'正在清空项目信息 ({count} 条记录)...')
                Project.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('项目信息 已清空'))

            # 重置自增ID序列
            self.stdout.write('重置自增ID序列...')
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM sqlite_sequence")
            
            self.stdout.write(self.style.SUCCESS('数据库清空完成！'))
            self.stdout.write(self.style.WARNING('注意：所有数据已被永久删除，无法恢复！'))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'清空数据时发生错误: {str(e)}')
            )