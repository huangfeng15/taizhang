"""
供应商履约评价模块 - 数据模型
"""
from django.db import models
from procurement.models import BaseModel


class SupplierEvaluation(BaseModel):
    """供应商履约评价 - 记录供应商在项目中的表现"""
    
    # ===== 主键 =====
    evaluation_code = models.CharField(
        '评价编号',
        max_length=50,
        primary_key=True,
        help_text='例如: PJ2025001-001'
    )
    
    # ===== 关联 =====
    contract = models.ForeignKey(
        'contract.Contract',
        on_delete=models.PROTECT,
        verbose_name='关联合同',
        related_name='evaluations',
        help_text='该评价对应的合同'
    )
    
    # ===== 供应商信息 =====
    supplier_name = models.CharField(
        '供应商名称',
        max_length=200,
        help_text='被评价的供应商名称'
    )
    
    # ===== 评价信息 =====
    evaluation_period = models.CharField(
        '评价日期区间',
        max_length=100,
        blank=True,
        help_text='例如: 2025年1月至2025年3月'
    )
    
    evaluator = models.CharField(
        '评价人员',
        max_length=50,
        blank=True,
        help_text='填写评价的人员名称'
    )
    
    score = models.DecimalField(
        '评分',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='满分100分'
    )
    
    EVAL_TYPE_CHOICES = [
        ('末次评价', '末次评价'),
        ('履约过程评价', '履约过程评价'),
    ]
    evaluation_type = models.CharField(
        '评价类型',
        max_length=20,
        choices=EVAL_TYPE_CHOICES,
        blank=True,
        help_text='区分末次评价和过程评价'
    )
    
    class Meta:
        verbose_name = '供应商评价'
        verbose_name_plural = '供应商评价'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['evaluation_code']),
            models.Index(fields=['contract']),
            models.Index(fields=['supplier_name']),
        ]
    
    def __str__(self):
        return f"{self.evaluation_code} - {self.supplier_name}"