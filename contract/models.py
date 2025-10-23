"""
合同管理模块 - 数据模型
"""
from django.db import models
from django.core.exceptions import ValidationError
from procurement.models import BaseModel
from project.validators import validate_code_field, validate_and_clean_code


class Contract(BaseModel):
    """合同管理 - 管理采购合同及其补充协议"""
    
    # ===== 主键 =====
    contract_code = models.CharField(
        '合同编号',
        max_length=50,
        primary_key=True,
        validators=[validate_code_field],
        help_text='合同编号不能包含 / \\ ? # 等URL特殊字符，例如: HT2025001'
    )
    
    # ===== 项目关联 =====
    project = models.ForeignKey(
        'project.Project',
        on_delete=models.PROTECT,
        verbose_name='关联项目',
        null=True,
        blank=True,
        related_name='contracts',
        help_text='该合同所属的项目'
    )
    
    # ===== 必填字段 =====
    contract_name = models.CharField(
        '合同名称',
        max_length=200,
        blank=False,
        help_text='合同的正式名称'
    )
    
    # ===== 合同类型与关联 =====
    CONTRACT_TYPE_CHOICES = [
        ('主合同', '主合同'),
        ('补充协议', '补充协议'),
        ('解除协议', '解除协议'),
    ]
    contract_type = models.CharField(
        '合同类型',
        max_length=20,
        choices=CONTRACT_TYPE_CHOICES,
        default='主合同',
        help_text='区分主合同和补充协议'
    )
    
    # ===== 合同来源分类 =====
    CONTRACT_SOURCE_CHOICES = [
        ('采购合同', '采购合同'),
        ('直接签订', '直接签订'),
    ]
    contract_source = models.CharField(
        '合同来源',
        max_length=20,
        choices=CONTRACT_SOURCE_CHOICES,
        default='采购合同',
        help_text='标识合同是否来源于采购项目'
    )
    
    parent_contract = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        verbose_name='关联主合同',
        null=True,
        blank=True,
        related_name='supplements',
        help_text='若为补充协议，则必须关联主合同'
    )
    
    procurement = models.ForeignKey(
        'procurement.Procurement',
        on_delete=models.PROTECT,
        verbose_name='关联采购',
        null=True,
        blank=True,
        related_name='contracts',
        help_text='当合同来源为"采购合同"时必填；当来源为"直接签订"时可为空'
    )
    
    # ===== 合同序号 =====
    contract_sequence = models.CharField(
        '合同序号',
        max_length=50,
        null=True,
        blank=True,
        validators=[validate_code_field],
        help_text='合同的序号，不能包含URL特殊字符，支持字符串格式如 BHHY-NH-001'
    )
    
    # ===== 合同方信息 =====
    party_a = models.CharField(
        '甲方',
        max_length=200,
        blank=True,
        help_text='合同甲方（通常为我司）'
    )
    
    party_b = models.CharField(
        '乙方',
        max_length=200,
        blank=True,
        help_text='合同乙方（供应商）'
    )
    
    party_b_contact = models.CharField(
        '乙方负责人及联系方式',
        max_length=200,
        blank=True,
        help_text='例如: 李经理 13900139000'
    )
    
    party_b_contact_in_contract = models.CharField(
        '合同文本内乙方联系人及方式',
        max_length=200,
        blank=True,
        help_text='合同文本中记录的乙方联系方式'
    )
    
    # ===== 金额与时间 =====
    contract_amount = models.DecimalField(
        '含税签约合同价(元)',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='签订时的合同总价（含税）'
    )
    
    signing_date = models.DateField(
        '合同签订日期',
        null=True,
        blank=True,
        help_text='合同正式签署的日期',
        db_index=True
    )
    
    duration = models.TextField(
        '合同工期/服务期限',
        blank=True,
        help_text='例如: 2025年1月1日至2025年12月31日'
    )
    
    # ===== 其他信息 =====
    contract_officer = models.CharField(
        '合同签订经办人',
        max_length=50,
        blank=True,
        help_text='负责签订的经办人'
    )
    
    payment_method = models.TextField(
        '支付方式',
        blank=True,
        help_text='例如: 预付30%、完工后验收支付70%'
    )
    
    performance_guarantee_return_date = models.DateField(
        '履约担保退回时间',
        null=True,
        blank=True,
        help_text='履约担保退回的日期'
    )
    
    archive_date = models.DateField(
        '资料归档日期',
        null=True,
        blank=True,
        help_text='合同资料归档的日期'
    )
    
    class Meta:
        verbose_name = '合同信息'
        verbose_name_plural = '合同信息'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contract_code']),
            models.Index(fields=['party_b']),
            models.Index(fields=['signing_date']),
        ]
    
    def __str__(self):
        return f"{self.contract_code} - {self.contract_name}"
    
    def clean(self):
        """业务规则验证"""
        errors = {}
        
        # 验证和清理编号字段
        if self.contract_code:
            try:
                self.contract_code = validate_and_clean_code(
                    self.contract_code,
                    '合同编号'
                )
            except ValidationError as e:
                errors['contract_code'] = e.message
        
        if self.contract_sequence:
            try:
                self.contract_sequence = validate_and_clean_code(
                    self.contract_sequence,
                    '合同序号'
                )
            except ValidationError as e:
                errors['contract_sequence'] = e.message
        
        # 规则1: 补充协议必须关联主合同
        if self.contract_type == '补充协议' and not self.parent_contract:
            errors['parent_contract'] = '补充协议必须关联主合同'
        
        # 规则2: 主合同不能关联其他合同
        if self.contract_type == '主合同' and self.parent_contract:
            errors['parent_contract'] = '主合同不能关联其他合同'
        
        # 规则3: 解除协议必须关联主合同
        if self.contract_type == '解除协议' and not self.parent_contract:
            errors['parent_contract'] = '解除协议必须关联主合同'
        
        # 规则4: 采购合同必须关联采购项目
        if self.contract_source == '采购合同' and not self.procurement:
            errors['procurement'] = '采购合同必须关联采购项目'
        
        # 规则5: 直接签订合同不能关联采购项目
        if self.contract_source == '直接签订' and self.procurement:
            errors['procurement'] = '直接签订合同不应关联采购项目'
        
        # 规则6: 补充协议继承主合同的来源类型和采购关联
        if self.contract_type in ['补充协议', '解除协议'] and self.parent_contract:
            if self.contract_source != self.parent_contract.contract_source:
                self.contract_source = self.parent_contract.contract_source
            if self.procurement != self.parent_contract.procurement:
                self.procurement = self.parent_contract.procurement
        
        if errors:
            raise ValidationError(errors)
    
    
    def get_total_paid_amount(self):
        """获取累计付款金额"""
        from django.db.models import Sum
        total = self.payments.aggregate(total=Sum('payment_amount'))['total'] or 0
        return total
    
    def get_payment_count(self):
        """获取付款笔数"""
        return self.payments.count()
    
    def get_payment_ratio(self):
        """
        获取付款比例
        规则:
        - 如果有结算价, 使用结算价作为分母
        - 否则使用(合同价 + 补充协议金额)作为分母
        """
        from django.db.models import Sum
        
        total_paid = self.get_total_paid_amount()
        
        # 获取基准金额(分母)
        base_amount = 0
        
        # 如果是主合同，检查是否有结算
        if self.contract_type == '主合同':
            try:
                if hasattr(self, 'settlement') and self.settlement and self.settlement.final_amount:
                    # 有结算价，使用结算价
                    base_amount = self.settlement.final_amount
                else:
                    # 没有结算价，使用合同价 + 补充协议金额
                    base_amount = self.contract_amount or 0
                    supplements_total = self.supplements.aggregate(
                        total=Sum('contract_amount')
                    )['total'] or 0
                    base_amount += supplements_total
            except:
                # 如果获取settlement失败，使用合同价 + 补充协议金额
                base_amount = self.contract_amount or 0
                supplements_total = self.supplements.aggregate(
                    total=Sum('contract_amount')
                )['total'] or 0
                base_amount += supplements_total
        else:
            # 补充协议或解除协议，使用自身合同价
            base_amount = self.contract_amount or 0
        
        # 计算比例
        if base_amount > 0:
            return (total_paid / base_amount) * 100
        return 0
    
    def get_contract_with_supplements_amount(self):
        """获取主合同+补充协议的总金额"""
        from django.db.models import Sum
        
        if self.contract_type == '主合同':
            total = self.contract_amount or 0
            supplements_total = self.supplements.aggregate(
                total=Sum('contract_amount')
            )['total'] or 0
            return total + supplements_total
        else:
            # 如果不是主合同，返回父合同的总金额
            if self.parent_contract:
                return self.parent_contract.get_contract_with_supplements_amount()
            return self.contract_amount or 0