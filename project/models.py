from __future__ import annotations
from typing import TYPE_CHECKING
from django.db import models
from project.models_base import AuditBaseModel
from project.validators import validate_code_field, validate_and_clean_code
from project.enums import ProjectStatus
from project.models_completeness_config import CompletenessFieldConfig

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from procurement.models import Procurement
    from contract.models import Contract


class Project(AuditBaseModel):
    """项目管理 - 用于归类和组织多个采购、合同等业务数据"""
    
    # ===== 主键 =====
    project_code = models.CharField(
        '项目编码',
        max_length=50,
        primary_key=True,
        validators=[validate_code_field],
        help_text='项目编码不能包含 / \\ ? # 等URL特殊字符，例如: PRJ2025001'
    )
    
    # ===== 必填字段 =====
    project_name = models.CharField(
        '项目名称',
        max_length=200,
        help_text='项目的正式名称'
    )
    
    # ===== 项目信息 =====
    description = models.TextField(
        '项目描述',
        blank=True,
        help_text='项目的详细描述'
    )
    
    project_manager = models.CharField(
        '项目负责人',
        max_length=50,
        blank=True,
        help_text='负责该项目的人员'
    )
    status = models.CharField(
        '项目状态',
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.IN_PROGRESS.value,
        help_text='项目当前状态'
    )
    
    remarks = models.TextField(
        '备注',
        blank=True,
        help_text='项目相关的其他备注信息'
    )
    
    # ===== 审计字段 =====
    # 审计字段由 AuditBaseModel 提供（DRY）
    if TYPE_CHECKING:
        # 类型提示：Django 反向关联
        procurements: QuerySet[Procurement]
        contracts: QuerySet[Contract]
    
    class Meta:
        verbose_name = '项目信息'
        verbose_name_plural = '项目信息'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project_code']),
            models.Index(fields=['project_name']),
            models.Index(fields=['status']),
        ]
    
    def clean(self):
        """数据验证"""
        # 验证和清理编号字段
        if self.project_code:
            self.project_code = validate_and_clean_code(
                self.project_code,
                '项目编码'
            )
    
    def save(self, *args, **kwargs):
        """保存前执行完整验证"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.project_code} - {self.project_name}"
    
    def get_procurement_count(self):
        """获取关联的采购数量"""
        return self.procurements.count()
    
    def get_contract_count(self):
        """获取关联的合同数量"""
        return self.contracts.count()
    
    def get_total_contract_amount(self):
        """获取关联合同的总金额"""
        from django.db.models import Sum
        total = self.contracts.aggregate(
            total=Sum('contract_amount')
        )['total'] or 0
        return total
