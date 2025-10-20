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
        help_text='例如: HT2025001-FK-001'
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
        """业务规则：累计付款不超过合同金额的120%"""
        if not self.contract.contract_amount:
            return
        
        from django.db.models import Sum
        
        # 计算已有的累计付款
        total_paid = Payment.objects.filter(
            contract=self.contract
        ).aggregate(total=Sum('payment_amount'))['total'] or 0
        
        # 如果是更新，需要排除旧记录
        if self.pk:
            try:
                old_amount = Payment.objects.get(pk=self.pk).payment_amount
                total_paid -= old_amount
            except Payment.DoesNotExist:
                # 新建记录时不需要排除旧值
                pass
        
        # 加上新付款
        total_paid += self.payment_amount
        
        # 验证不超过120%
        from decimal import Decimal
        max_allowed = self.contract.contract_amount * Decimal('1.2')
        if total_paid > max_allowed:
            raise ValidationError(
                f'累计付款 {total_paid}元 超过合同金额 '
                f'{self.contract.contract_amount}元 的120%上限 '
                f'{max_allowed}元'
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)