"""
采购管理模块 - 数据模型
"""
from django.db import models
from django.core.exceptions import ValidationError


class BaseModel(models.Model):
    """
    抽象基类 - 所有业务模型继承此类
    包含通用的审计字段
    """
    created_at = models.DateTimeField(
        '创建时间',
        auto_now_add=True,
        help_text='记录创建时自动设置'
    )
    
    updated_at = models.DateTimeField(
        '更新时间',
        auto_now=True,
        help_text='每次更新时自动更新'
    )
    
    created_by = models.CharField(
        '创建人',
        max_length=50,
        blank=True,
        help_text='创建该记录的用户'
    )
    
    updated_by = models.CharField(
        '更新人',
        max_length=50,
        blank=True,
        help_text='最后更新该记录的用户'
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']


class Procurement(BaseModel):
    """采购管理 - 记录采购项目的全生命周期"""
    
    # ===== 主键 =====
    procurement_code = models.CharField(
        '招采编号',
        max_length=50,
        primary_key=True,
        help_text='例如: GC2025001'
    )
    
    # ===== 必填字段 =====
    project_name = models.CharField(
        '采购项目名称',
        max_length=200,
        blank=False,
        help_text='采购项目的正式名称'
    )
    
    # ===== 基本信息 =====
    procurement_unit = models.CharField(
        '采购单位',
        max_length=200,
        blank=True,
        help_text='发起采购的部门或单位'
    )
    
    winning_unit = models.CharField(
        '中标单位',
        max_length=200,
        blank=True,
        help_text='最终确定的中标供应商'
    )
    
    winning_contact = models.CharField(
        '中标单位联系人及方式',
        max_length=200,
        blank=True,
        help_text='例如: 张三 13800138000'
    )
    
    # ===== 采购方式与类别 =====
    procurement_method = models.CharField(
        '采购方式',
        max_length=50,
        blank=True,
        help_text='例如: 竞争性谈判、招标、询价等'
    )
    
    CATEGORY_CHOICES = [
        ('工程', '工程'),
        ('货物', '货物'),
        ('服务', '服务'),
    ]
    procurement_category = models.CharField(
        '采购类别',
        max_length=20,
        choices=CATEGORY_CHOICES,
        blank=True,
        help_text='采购标的类型'
    )
    
    # ===== 金额信息 =====
    budget_amount = models.DecimalField(
        '采购预算金额(元)',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='项目预算金额'
    )
    
    control_price = models.DecimalField(
        '采购控制价(元)',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='采购控制价上限'
    )
    
    winning_amount = models.DecimalField(
        '中标金额(元)',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='最终中标价格'
    )
    
    # ===== 时间信息 =====
    planned_end_date = models.DateField(
        '计划结束采购时间',
        null=True,
        blank=True,
        help_text='计划采购完成日期'
    )
    
    notice_issue_date = models.DateField(
        '中标通知书发放日期',
        null=True,
        blank=True,
        help_text='发放中标通知书的日期'
    )
    
    # ===== 人员信息 =====
    procurement_officer = models.CharField(
        '采购经办人',
        max_length=50,
        blank=True,
        help_text='负责该采购的经办人名称'
    )
    
    demand_department = models.CharField(
        '需求部门',
        max_length=100,
        blank=True,
        help_text='需求方部门名称'
    )
    
    class Meta:
        verbose_name = '采购信息'
        verbose_name_plural = '采购信息'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['procurement_code']),
            models.Index(fields=['winning_unit']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.procurement_code} - {self.project_name}"