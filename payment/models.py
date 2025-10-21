"""
付款管理模块 - 数据模型
"""
from django.db import models
from django.core.exceptions import ValidationError
from procurement.models import BaseModel


class Payment(BaseModel):
    """付款管理 - 记录每一笔付款交易"""
    
    # ===== 主键 =====
    payment_code = models.CharField(
        '付款编号',
        max_length=50,
        primary_key=True,
        blank=True,
        help_text='例如: HT2025001-FK-001，如果为空将自动生成'
    )
    
    # ===== 关联 =====
    contract = models.ForeignKey(
        'contract.Contract',
        on_delete=models.PROTECT,
        verbose_name='关联合同',
        related_name='payments',
        help_text='该笔付款对应的合同'
    )
    
    # ===== 付款信息 =====
    payment_amount = models.DecimalField(
        '实付金额(元)',
        max_digits=15,
        decimal_places=2,
        help_text='本次实际支付金额'
    )
    
    payment_date = models.DateField(
        '付款日期',
        help_text='实际支付的日期',
        db_index=True
    )
    
    # ===== 结算信息 =====
    settlement_amount = models.DecimalField(
        '结算价(元)',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='合同的结算价格，如果已办理结算则填写'
    )
    
    is_settled = models.BooleanField(
        '是否办理结算',
        default=False,
        help_text='标识该笔付款是否已办理结算'
    )
    
    class Meta:
        verbose_name = '付款信息'
        verbose_name_plural = '付款信息'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_code']),
            models.Index(fields=['contract']),
            models.Index(fields=['payment_date']),
        ]
    
    def __str__(self):
        return f"{self.payment_code} - {self.payment_amount}元"
    
    def clean(self):
        """数据验证"""
        # 移除了120%上限的业务规则限制
        pass
    
    def _generate_payment_code(self):
        """
        生成付款编号：合同序号-FK-序号
        序号按付款日期排序，最早的付款为001，之后依次类推
        """
        if not self.contract:
            raise ValidationError('生成付款编号需要关联合同')
        
        if not self.payment_date:
            raise ValidationError('生成付款编号需要提供付款日期')
        
        # 使用合同序号，如果没有则使用合同编号
        contract_identifier = self.contract.contract_sequence or self.contract.contract_code
        
        # 查询该合同下所有付款记录，按付款日期排序
        existing_payments = Payment.objects.filter(
            contract=self.contract
        ).order_by('payment_date', 'created_at')
        
        # 计算当前付款在按日期排序后的序号
        sequence = 1
        for payment in existing_payments:
            # 如果是更新操作且是当前记录，跳过
            if self.pk and payment.pk == self.pk:
                continue
            # 如果现有付款日期早于或等于当前付款日期，序号+1
            if payment.payment_date < self.payment_date:
                sequence += 1
            elif payment.payment_date == self.payment_date and payment.created_at < self.created_at:
                # 同一天的付款，按创建时间排序
                sequence += 1
        
        return f"{contract_identifier}-FK-{sequence:03d}"
    
    def save(self, *args, **kwargs):
        # 如果付款编号为空，自动生成
        if not self.payment_code:
            self.payment_code = self._generate_payment_code()
        
        self.full_clean()
        super().save(*args, **kwargs)