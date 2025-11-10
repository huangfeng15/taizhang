"""
结算管理模块 - 数据模型
"""
from django.db import models
from django.core.exceptions import ValidationError
from procurement.models import BaseModel
from project.validators import validate_code_field, validate_and_clean_code
from project.enums import FilePositioning


class Settlement(BaseModel):
    """结算管理 - 记录主合同（含所有补充协议）的最终结算"""
    
    # ===== 主键 =====
    settlement_code = models.CharField(
        '结算编号',
        max_length=50,
        primary_key=True,
        validators=[validate_code_field],
        help_text='结算编号不能包含 / \\ ? # 等URL特殊字符，例如: JS2025001'
    )
    
    # ===== 关联 =====
    main_contract = models.OneToOneField(
        'contract.Contract',
        on_delete=models.PROTECT,
        verbose_name='关联主合同',
        related_name='settlement',
        limit_choices_to={'file_positioning': FilePositioning.MAIN_CONTRACT.value},
        help_text='只能关联主合同。主合同+所有补充协议+解除协议共用这一条结算记录'
    )
    
    # ===== 结算信息 =====
    final_amount = models.DecimalField(
        '最终结算金额(元)',
        max_digits=15,
        decimal_places=2,
        help_text='主合同+所有补充协议的累计最终结算金额'
    )
    
    completion_date = models.DateField(
        '完成日期',
        null=True,
        blank=True,
        help_text='结算完成的日期'
    )
    
    remarks = models.TextField(
        '结算备注',
        blank=True,
        help_text='可说明包含哪些补充协议或解除协议的结算情况'
    )
    
    class Meta:
        verbose_name = '结算信息'
        verbose_name_plural = '结算信息'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['settlement_code']),
            models.Index(fields=['main_contract']),
            models.Index(fields=['completion_date']),
        ]
    
    def __str__(self):
        return f"{self.settlement_code} - {self.final_amount}元"
    
    def clean(self):
        """业务规则验证"""
        # 验证和清理编号字段
        if self.settlement_code:
            self.settlement_code = validate_and_clean_code(
                self.settlement_code,
                '结算编号'
            )
        
        # 业务规则：只能关联主合同
        if self.main_contract and self.main_contract.file_positioning != FilePositioning.MAIN_CONTRACT.value:
            raise ValidationError('结算记录只能关联主合同，不能关联补充协议或解除协议')
    
    
    def get_total_contract_amount(self):
        """计算主合同+所有补充协议的合同总额"""
        from django.db.models import Sum
        
        # 主合同金额
        total = self.main_contract.contract_amount or 0
        
        # 加上所有补充协议金额
        supplements_total = self.main_contract.supplements.aggregate(
            total=Sum('contract_amount')
        )['total'] or 0
        
        return total + supplements_total