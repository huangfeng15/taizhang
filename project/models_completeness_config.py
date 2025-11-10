"""
完整率字段配置模型
用于管理采购和合同完整率统计的字段配置
"""
from django.db import models


class CompletenessFieldConfig(models.Model):
    """完整率字段配置"""

    MODEL_CHOICES = [
        ('procurement', '采购'),
        ('contract', '合同'),
    ]

    model_type = models.CharField(
        '模型类型',
        max_length=20,
        choices=MODEL_CHOICES,
        help_text='采购或合同'
    )

    field_name = models.CharField(
        '字段名称',
        max_length=100,
        help_text='模型中的字段名'
    )

    field_label = models.CharField(
        '字段标签',
        max_length=200,
        help_text='字段的中文显示名称'
    )

    is_enabled = models.BooleanField(
        '是否启用',
        default=True,
        help_text='是否纳入完整率统计'
    )

    sort_order = models.IntegerField(
        '排序',
        default=0,
        help_text='显示顺序，数字越小越靠前'
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '完整率字段配置'
        verbose_name_plural = '完整率字段配置'
        ordering = ['model_type', 'sort_order', 'field_name']
        unique_together = [['model_type', 'field_name']]
        indexes = [
            models.Index(fields=['model_type', 'is_enabled']),
        ]

    def __str__(self):
        return f"{self.get_model_type_display()} - {self.field_label}"
