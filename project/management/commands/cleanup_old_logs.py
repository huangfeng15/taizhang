"""清理超过7天的操作日志"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from project.models_operation_log import OperationLog


class Command(BaseCommand):
    help = '清理超过7天的操作日志'

    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timedelta(days=7)
        deleted_count, _ = OperationLog.objects.filter(created_at__lt=cutoff_date).delete()
        self.stdout.write(
            self.style.SUCCESS(f'成功清理 {deleted_count} 条操作日志')
        )