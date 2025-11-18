"""操作日志模型"""
from django.db import models
from django.contrib.auth.models import User
from project.models_base import AuditBaseModel


class OperationLog(models.Model):
    """操作日志 - 记录用户的修改和新增操作"""
    
    OPERATION_TYPE_CHOICES = [
        ('create', '新增'),
        ('update', '修改'),
    ]
    
    OBJECT_TYPE_CHOICES = [
        ('project', '项目'),
        ('procurement', '采购'),
        ('contract', '合同'),
        ('payment', '付款'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='操作用户',
        help_text='执行操作的用户'
    )
    
    operation_type = models.CharField(
        '操作类型',
        max_length=10,
        choices=OPERATION_TYPE_CHOICES,
        help_text='新增或修改'
    )
    
    object_type = models.CharField(
        '操作对象类型',
        max_length=20,
        choices=OBJECT_TYPE_CHOICES,
        help_text='项目、采购、合同或付款'
    )
    
    object_id = models.CharField(
        '操作对象ID',
        max_length=100,
        help_text='被操作对象的主键'
    )
    
    object_repr = models.CharField(
        '对象描述',
        max_length=200,
        blank=True,
        help_text='对象的字符串表示'
    )
    
    description = models.TextField(
        '操作描述',
        blank=True,
        help_text='详细的操作描述,便于追溯'
    )
    
    ip_address = models.GenericIPAddressField(
        'IP地址',
        null=True,
        blank=True,
        help_text='操作来源IP'
    )
    
    changes = models.JSONField(
        '变更内容',
        null=True,
        blank=True,
        help_text='修改操作的变更详情(JSON格式)'
    )
    
    created_at = models.DateTimeField(
        '操作时间',
        auto_now_add=True,
        help_text='操作发生的时间'
    )
    
    class Meta:
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user']),
            models.Index(fields=['object_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} {self.get_operation_type_display()} {self.get_object_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"