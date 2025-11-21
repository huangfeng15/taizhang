"""
采购方式字段配置模型
用于管理不同采购方式的必填字段配置
"""
from django.db import models
from project.models_base import AuditBaseModel


class ProcurementMethodFieldConfig(AuditBaseModel):
    """采购方式字段配置"""

    # 采购方式类型常量
    STRATEGIC_PROCUREMENT = 'strategic_procurement'
    DIRECT_COMMISSION = 'direct_commission'
    SINGLE_SOURCE = 'single_source'
    OTHER_METHODS = 'other_methods'

    METHOD_TYPE_CHOICES = [
        (STRATEGIC_PROCUREMENT, '战采结果应用'),
        (DIRECT_COMMISSION, '直接采购'),
        (SINGLE_SOURCE, '单一来源采购'),
        (OTHER_METHODS, '其他采购方式'),
    ]

    method_type = models.CharField(
        '采购方式类型',
        max_length=50,
        choices=METHOD_TYPE_CHOICES,
        help_text='采购方式分类：战采结果应用、直接采购、单一来源采购、其他采购方式'
    )

    field_name = models.CharField(
        '字段名称',
        max_length=100,
        help_text='采购模型中的字段名'
    )

    field_label = models.CharField(
        '字段标签',
        max_length=200,
        help_text='字段的中文显示名称'
    )

    is_required = models.BooleanField(
        '是否必填',
        default=True,
        help_text='该字段对此采购方式是否为必填'
    )

    sort_order = models.IntegerField(
        '排序',
        default=0,
        help_text='显示顺序，数字越小越靠前'
    )

    # 审计字段由 AuditBaseModel 提供：created_at / updated_at

    class Meta:
        verbose_name = '采购方式字段配置'
        verbose_name_plural = '采购方式字段配置'
        ordering = ['method_type', 'sort_order', 'field_name']
        unique_together = [['method_type', 'field_name']]
        indexes = [
            models.Index(fields=['method_type', 'is_required']),
        ]

    def __str__(self):
        return f"{self.get_method_type_display()} - {self.field_label}"

    @classmethod
    def get_required_fields(cls, method_type):
        """获取指定采购方式类型的必填字段列表"""
        configs = cls.objects.filter(
            method_type=method_type,
            is_required=True
        ).order_by('sort_order', 'field_name')
        return [config.field_name for config in configs]

    @classmethod
    def get_all_fields_by_method(cls, method_type):
        """获取指定采购方式类型的所有字段配置"""
        return cls.objects.filter(
            method_type=method_type
        ).order_by('sort_order', 'field_name')