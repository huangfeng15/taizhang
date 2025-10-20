# 项目采购与成本管理系统 — 数据模型详细设计

**文档版本：** v1.0  
**编写日期：** 2025-10-20  
**关联规范：** [技术文档](../specs/技术文档-简化版.md) | [需求文档](../specs/需求文档.md)

---

## 1. 核心设计原则

### 1.1 业务编号作为主键

- **核心原则：** 所有模块的业务编号（如采购编号、合同编号）作为数据库主键
- **理由：**
  1. 避免自增ID泄露业务规模
  2. 业务编号本身就是唯一标识，具有业务意义
  3. 便于数据溯源和审计
  4. 与历史Excel数据无缝对接
- **实现：** `models.CharField(..., primary_key=True)`

### 1.2 字段可空性设计

- **必填字段：** 仅"项目名称"和"合同名称"
- **其他字段：** 全部允许为空（`blank=True, null=True`）
- **理由：** 考虑数据迁移阶段，历史数据可能不完整

### 1.3 数据完整性保护

- **关键关系：** 使用 `ForeignKey(..., on_delete=models.PROTECT)`
- **理由：** 防止删除关联记录导致数据孤立
- **示例：** 不能删除已关联合同的采购记录

### 1.4 审计字段

所有模型均继承以下审计字段：
```python
created_at = models.DateTimeField('创建时间', auto_now_add=True)
updated_at = models.DateTimeField('更新时间', auto_now=True)
created_by = models.CharField('创建人', max_length=50, blank=True)
updated_by = models.CharField('更新人', max_length=50, blank=True)
```

---

## 2. 模块一：采购管理 (Procurement)

### 2.1 模型定义

```python
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
        blank=False,  # 必填
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
```

### 2.2 Admin配置

```python
@admin.register(Procurement)
class ProcurementAdmin(admin.ModelAdmin):
    list_display = [
        'procurement_code', 'project_name', 'winning_unit',
        'winning_amount', 'procurement_officer', 'created_at'
    ]
    search_fields = [
        'procurement_code', 'project_name', 'winning_unit',
        'procurement_officer', 'demand_department'
    ]
    list_filter = [
        'procurement_category', 'procurement_method',
        'created_at', 'notice_issue_date'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    fieldsets = (
        ('基本信息', {
            'fields': ('procurement_code', 'project_name', 'procurement_unit')
        }),
        ('中标信息', {
            'fields': ('winning_unit', 'winning_contact', 'winning_amount')
        }),
        ('采购详情', {
            'fields': (
                'procurement_method', 'procurement_category',
                'budget_amount', 'control_price'
            )
        }),
        ('时间信息', {
            'fields': ('planned_end_date', 'notice_issue_date')
        }),
        ('人员信息', {
            'fields': ('procurement_officer', 'demand_department')
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
```

---

## 3. 模块二：合同管理 (Contract)

### 3.1 模型定义

```python
class Contract(BaseModel):
    """合同管理 - 管理采购合同及其补充协议"""
    
    # ===== 主键 =====
    contract_code = models.CharField(
        '合同编号',
        max_length=50,
        primary_key=True,
        help_text='例如: HT2025001'
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
    
    duration = models.CharField(
        '合同工期/服务期限',
        max_length=100,
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
            # 如果来源不一致，进行同步
            if self.contract_source != self.parent_contract.contract_source:
                self.contract_source = self.parent_contract.contract_source
            # 同步采购关联
            if self.procurement != self.parent_contract.procurement:
                self.procurement = self.parent_contract.procurement
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()  # 保存前强制验证
        super().save(*args, **kwargs)
```

### 3.2 Admin配置

```python
@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = [
        'contract_code', 'contract_name', 'contract_type', 'contract_source',
        'party_b', 'contract_amount', 'signing_date'
    ]
    search_fields = [
        'contract_code', 'contract_name', 'party_a', 'party_b'
    ]
    list_filter = [
        'contract_type', 'contract_source', 'signing_date', 'created_at'
    ]
    autocomplete_fields = ['procurement', 'parent_contract']
    date_hierarchy = 'signing_date'
    list_per_page = 50
    
    def get_list_filter(self, request):
        """动态过滤器"""
        filters = list(super().get_list_filter(request))
        # 添加自定义过滤器：是否关联采购
        filters.append(('procurement', admin.EmptyFieldListFilter))
        return filters
    
    fieldsets = (
        ('基本信息', {
            'fields': ('contract_code', 'contract_name', 'contract_type', 'contract_source')
        }),
        ('关联信息', {
            'fields': ('parent_contract', 'procurement'),
            'description': '采购合同必须关联采购项目；直接签订合同无需关联采购'
        }),
        ('合同方信息', {
            'fields': ('party_a', 'party_b')
        }),
        ('金额与时间', {
            'fields': ('contract_amount', 'signing_date', 'duration')
        }),
        ('其他信息', {
            'fields': ('contract_officer', 'payment_method'),
            'classes': ('collapse',)
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
```

---

## 4. 模块三：付款管理 (Payment)

### 4.1 模型定义

```python
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
            return  # 合同未设定金额，跳过检查
        
        from django.db.models import Sum
        
        # 计算已有的累计付款
        total_paid = Payment.objects.filter(
            contract=self.contract
        ).aggregate(total=Sum('payment_amount'))['total'] or 0
        
        # 如果是更新，需要排除旧记录
        if self.pk:
            old_amount = Payment.objects.get(pk=self.pk).payment_amount
            total_paid -= old_amount
        
        # 加上新付款
        total_paid += self.payment_amount
        
        # 验证不超过120%
        max_allowed = self.contract.contract_amount * 1.2
        if total_paid > max_allowed:
            raise ValidationError(
                f'累计付款 {total_paid}元 超过合同金额 '
                f'{self.contract.contract_amount}元 的120%上限 '
                f'{max_allowed}元'
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

### 4.2 Admin配置

```python
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_code', 'contract', 'payment_amount', 'payment_date'
    ]
    search_fields = [
        'payment_code', 'contract__contract_code', 'contract__contract_name'
    ]
    list_filter = ['payment_date', 'created_at']
    autocomplete_fields = ['contract']
    date_hierarchy = 'payment_date'
    list_per_page = 50
    
    fieldsets = (
        ('基本信息', {
            'fields': ('payment_code', 'contract')
        }),
        ('付款详情', {
            'fields': ('payment_amount', 'payment_date')
        }),
        ('审计信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
```

---

## 5. 模块四：结算管理 (Settlement)

### 5.1 模型定义

```python
class Settlement(BaseModel):
    """结算管理 - 记录主合同（含所有补充协议）的最终结算"""
    
    # ===== 主键 =====
    settlement_code = models.CharField(
        '结算编号',
        max_length=50,
        primary_key=True,
        help_text='例如: JS2025001'
    )
    
    # ===== 关联 =====
    main_contract = models.OneToOneField(
        'contract.Contract',
        on_delete=models.PROTECT,
        verbose_name='关联主合同',
        related_name='settlement',
        limit_choices_to={'contract_type': '主合同'},
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
        ]
    
    def __str__(self):
        return f"{self.settlement_code} - {self.final_amount}元"
    
    def clean(self):
        """业务规则：只能关联主合同"""
        from django.core.exceptions import ValidationError
        if self.main_contract and self.main_contract.contract_type != '主合同':
            raise ValidationError('结算记录只能关联主合同，不能关联补充协议或解除协议')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
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
```

---

## 6. 模块五：供应商履约评价 (SupplierEvaluation)

### 6.1 模型定义

```python
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
```

---

## 7. 基础模型（抽象类）

```python
from django.db import models

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
```

---

## 8. 数据关系总结

```
┌─────────────────────────────────────────┐
│          Procurement (采购)              │
│  PK: procurement_code (招采编号)         │
├─────────────────────────────────────────┤
│ - project_name ✓ (必填)                  │
│ - procurement_method, category           │
│ - budget_amount, winning_amount          │
│ - procurement_officer, demand_department │
└────────────────┬────────────────────────┘
                 │
            1:N   │
                 │
     ┌────────────▼──────────────────────────┐
     │      Contract (合同)                   │
     │  PK: contract_code (合同编号)          │
     ├───────────────────────────────────────┤
     │ - contract_name ✓ (必填)               │
     │ - contract_type (主/补充/解除)         │
     │ - parent_contract (ForeignKey自关联)   │ ◄── 补充协议关联主合同
     │ - party_a, party_b                    │
     │ - contract_amount, signing_date       │
     └──┬─────────────┬──────────────────┬───┘
        │             │                  │
     1:N│          1:N│               1:1│
        │             │          (仅主合同)
        ▼             ▼                  ▼
     Payment    SupplierEval       Settlement
     (付款)      (评价)            (结算)
                                  关联：主合同
                         备注：主合同+所有补充
                            协议+解除协议共用
                            一条结算记录
```

**关键业务逻辑说明：**
- **合同来源分类：**
  - 采购合同：通过采购流程产生的合同，必须关联采购项目
  - 直接签订：不经过采购流程直接签订的合同，无需关联采购项目（极少数情况）
- **关联规则：**
  - Settlement.main_contract 仅能关联contract_type='主合同'的Contract
  - 补充协议和解除协议通过parent_contract指向主合同，但不直接关联Settlement
  - 补充协议自动继承主合同的contract_source和procurement关联
- **统计维度：**
  - 可按contract_source字段区分统计采购合同和直接签订合同
  - 可通过procurement字段是否为空筛选关联/不关联采购的合同
- 查询某个主合同的结算时，可通过get_total_contract_amount()方法自动计算主合同+所有补充协议的总金额

---

## 9. 数据类型速查表

| 字段类型 | Django类型 | 用途 | 例子 |
|---------|-----------|------|------|
| **编号** | `CharField(primary_key=True)` | 业务编号作PK | `GC2025001` |
| **名称/文本** | `CharField(max_length=X)` | 短文本（<255字符） | `采购项目名称` |
| **长文本** | `TextField()` | 长文本（无长度限制） | `支付方式详情` |
| **金额** | `DecimalField(max_digits=15, decimal_places=2)` | 精确货币值 | `99999999.99` |
| **日期** | `DateField()` | 日期（不含时间） | `2025-10-20` |
| **枚举** | `CharField(choices=[...])` | 固定选项 | `工程/货物/服务` |
| **外键** | `ForeignKey(Model)` | 1:N关联 | 合同→采购 |
| **一对一** | `OneToOneField(Model)` | 1:1关联 | 合同→结算 |
| **自关联** | `ForeignKey('self')` | 同表关联 | 合同→父合同 |
| **审计** | `DateTimeField(auto_now_add/auto_now)` | 时间戳 | `2025-10-20 12:34:56` |

---

**下一步：** 此文档完成，可以进入Code模式开始实施模型编写。