"""
供应商履约评价模块 - 数据模型
"""
from decimal import Decimal
from django.db import models
from procurement.models import BaseModel


class SupplierEvaluation(BaseModel):
    """供应商履约评价 - 记录供应商在项目中的表现（扩展版本，对应CSV模板）"""
    
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
        help_text='该评价对应的合同（对应CSV的"合同序号"列）',
        db_index=True
    )
    
    # ===== 供应商信息 =====
    supplier_name = models.CharField(
        '供应商名称',
        max_length=200,
        db_index=True,
        help_text='被评价的供应商名称，从合同自动获取'
    )
    
    # ===== 现有评价字段（保留兼容）=====
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
        help_text='满分100分（兼容旧字段）'
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
    
    # ===== 新增字段（对应CSV列）=====
    # CSV列：履约综合评价得分（可导入或自动计算）
    comprehensive_score = models.DecimalField(
        '履约综合评价得分',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True,
        help_text='可从CSV导入，或根据末次评价和过程评价自动计算（末次60% + 过程40%）'
    )
    
    # CSV列：末次评价得分（权重60%）
    last_evaluation_score = models.DecimalField(
        '末次评价得分',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True,
        help_text='权重60%，用于计算综合评分'
    )
    
    # CSV列：年度评价得分（动态支持任意年份）
    annual_scores = models.JSONField(
        '年度评价得分',
        default=dict,
        blank=True,
        help_text='格式: {"2019": 85.5, "2020": 88.0, ...}，支持任意年份动态扩展'
    )

    # CSV列：不定期评价得分（动态支持任意次数）
    irregular_scores = models.JSONField(
        '不定期评价得分',
        default=dict,
        blank=True,
        help_text='格式: {"1": 90.0, "2": 85.0, ...}，支持任意次数动态扩展'
    )
    
    # CSV列：备注
    remarks = models.TextField(
        '备注',
        blank=True,
        help_text='其他说明信息'
    )
    
    class Meta(BaseModel.Meta):  # type: ignore[misc]
        verbose_name = '供应商履约评价'
        verbose_name_plural = '供应商履约评价'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['evaluation_code']),
            models.Index(fields=['contract']),
            models.Index(fields=['supplier_name']),
            models.Index(fields=['comprehensive_score']),
            models.Index(fields=['last_evaluation_score']),
        ]
    
    def __str__(self):
        return f"{self.evaluation_code} - {self.supplier_name}"
    
    def save(self, *args, **kwargs):
        """保存时自动计算综合评分和生成评价编号（如果未提供）"""
        # 自动获取供应商名称
        if self.contract and not self.supplier_name:
            self.supplier_name = self.contract.party_b
        
        # 自动生成评价编号（如果未提供）
        if not self.evaluation_code and self.contract:
            self.evaluation_code = f"PJ{self.contract.contract_code}"
        
        # 如果CSV没有提供综合评分，则自动计算
        if not self.comprehensive_score and self.last_evaluation_score:
            self.comprehensive_score = self.calculate_comprehensive_score()
        
        super().save(*args, **kwargs)
    
    def calculate_comprehensive_score(self):
        """
        计算综合评分
        公式：末次评价 × 60% + 过程评价平均 × 40%
        过程评价包括：所有年度评价 + 所有不定期评价

        Returns:
            Decimal: 综合评分（保留2位小数），如果无法计算则返回None
        """
        if not self.last_evaluation_score:
            return None

        # 收集过程评价得分
        process_scores = []

        # 年度评价得分（从JSONField动态获取）
        if self.annual_scores:
            process_scores.extend([
                float(score) for score in self.annual_scores.values()
                if score is not None
            ])

        # 不定期评价得分（从JSONField动态获取）
        if self.irregular_scores:
            process_scores.extend([
                float(score) for score in self.irregular_scores.values()
                if score is not None
            ])

        # 如果没有过程评价，综合得分 = 末次评价
        if not process_scores:
            return self.last_evaluation_score

        # 计算过程评价平均分
        process_avg = sum(process_scores) / len(process_scores)

        # 综合得分 = 末次评价 × 0.6 + 过程评价平均 × 0.4
        comprehensive = (
            Decimal(str(self.last_evaluation_score)) * Decimal('0.6') +
            Decimal(str(process_avg)) * Decimal('0.4')
        )

        return round(comprehensive, 2)
    
    def get_score_level(self):
        """
        获取评分等级
        
        Returns:
            str: 评分等级（优秀/良好/合格/不合格）
        """
        if not self.comprehensive_score:
            return '未评分'
        
        score = float(self.comprehensive_score)
        if score >= 90:
            return '优秀'
        elif score >= 80:
            return '良好'
        elif score >= 70:
            return '合格'
        else:
            return '不合格'
    
    def get_process_scores(self):
        """
        获取所有过程评价得分（用于展示）

        Returns:
            dict: 年度和不定期评价得分字典
        """
        return {
            '年度评价': self.annual_scores or {},
            '不定期评价': {
                f'第{k}次': v for k, v in (self.irregular_scores or {}).items()
            }
        }

    # ===== 年度评分动态管理方法 =====
    def get_annual_score(self, year: int):
        """
        获取指定年份的评分

        Args:
            year: 年份（如2019）

        Returns:
            float: 评分，如果不存在则返回None
        """
        if not self.annual_scores:
            return None
        return self.annual_scores.get(str(year))

    def set_annual_score(self, year: int, score: float):
        """
        设置指定年份的评分

        Args:
            year: 年份（如2019）
            score: 评分（0-100）
        """
        if not self.annual_scores:
            self.annual_scores = {}
        self.annual_scores[str(year)] = float(score)

    def get_irregular_score(self, index: int):
        """
        获取指定次数的不定期评价得分

        Args:
            index: 次数（如1表示第一次）

        Returns:
            float: 评分，如果不存在则返回None
        """
        if not self.irregular_scores:
            return None
        return self.irregular_scores.get(str(index))

    def set_irregular_score(self, index: int, score: float):
        """
        设置指定次数的不定期评价得分

        Args:
            index: 次数（如1表示第一次）
            score: 评分（0-100）
        """
        if not self.irregular_scores:
            self.irregular_scores = {}
        self.irregular_scores[str(index)] = float(score)

    def get_all_annual_years(self):
        """
        获取所有已评价的年份列表（排序）

        Returns:
            list: 年份列表，如[2019, 2020, 2023]
        """
        if not self.annual_scores:
            return []
        return sorted([int(year) for year in self.annual_scores.keys()])

    def get_annual_scores_display(self):
        """
        获取年度评分的展示字符串

        Returns:
            str: 格式化的年度评分字符串，如"2019年:85分 | 2020年:88分"
        """
        if not self.annual_scores:
            return '-'
        years = self.get_all_annual_years()
        return ' | '.join([
            f'{year}年:{self.annual_scores[str(year)]}分'
            for year in years
        ])


class SupplierInterview(BaseModel):
    """供应商约谈记录模型"""
    
    # 主键（自动生成）
    id = models.AutoField(
        primary_key=True,
        verbose_name='约谈记录ID'
    )
    
    # ===== 基本信息 =====
    supplier_name = models.CharField(
        '供应商名称',
        max_length=200,
        db_index=True,
        help_text='被约谈的供应商名称'
    )
    
    # 外键关联（可选，因为可能是未签约供应商）
    contract = models.ForeignKey(
        'contract.Contract',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interviews',
        verbose_name='关联合同',
        help_text='如因合同问题约谈，则关联具体合同'
    )
    
    # ===== 约谈类型 =====
    INTERVIEW_TYPE_CHOICES = [
        ('违约约谈', '违约约谈'),
        ('履约沟通', '履约沟通'),
        ('商务洽谈', '商务洽谈'),
        ('投标前沟通', '投标前沟通'),
        ('其他', '其他'),
    ]
    interview_type = models.CharField(
        '约谈类型',
        max_length=20,
        choices=INTERVIEW_TYPE_CHOICES,
        default='履约沟通',
        db_index=True,
        help_text='约谈的类型分类'
    )
    
    # ===== 约谈信息 =====
    interview_date = models.DateField(
        '约谈日期',
        db_index=True,
        help_text='约谈发生的日期'
    )
    
    interviewer = models.CharField(
        '约谈人',
        max_length=100,
        help_text='我方参与约谈的人员'
    )
    
    supplier_representative = models.CharField(
        '供应商代表',
        max_length=100,
        blank=True,
        help_text='供应商方参与约谈的人员'
    )
    
    # ===== 详细内容 =====
    reason = models.TextField(
        '约谈原因',
        help_text='详细说明约谈的原因'
    )
    
    content = models.TextField(
        '约谈内容',
        help_text='约谈的详细过程和讨论内容'
    )
    
    rectification_requirements = models.TextField(
        '整改要求',
        blank=True,
        help_text='对供应商提出的整改要求（违约约谈时填写）'
    )
    
    result = models.TextField(
        '处理结果',
        blank=True,
        help_text='约谈后的处理结果和后续跟进情况'
    )
    
    # ===== 状态管理 =====
    STATUS_CHOICES = [
        ('待整改', '待整改'),
        ('整改中', '整改中'),
        ('已完成', '已完成'),
        ('仅记录', '仅记录'),
    ]
    status = models.CharField(
        '跟进状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='仅记录',
        db_index=True,
        help_text='约谈后的跟进状态'
    )
    
    # ===== 供应商类型标识 =====
    has_contract = models.BooleanField(
        '是否已签约供应商',
        default=True,
        db_index=True,
        help_text='区分已签约供应商和潜在供应商'
    )
    
    # ===== 附件说明 =====
    attachments = models.TextField(
        '附件说明',
        blank=True,
        help_text='相关文件、照片等附件的说明'
    )
    
    class Meta(BaseModel.Meta):  # type: ignore[misc]
        verbose_name = '供应商约谈记录'
        verbose_name_plural = '供应商约谈记录'
        ordering = ['-interview_date', '-created_at']
        indexes = [
            models.Index(fields=['supplier_name']),
            models.Index(fields=['interview_date']),
            models.Index(fields=['interview_type']),
            models.Index(fields=['status']),
            models.Index(fields=['has_contract']),
        ]
    
    def __str__(self):
        return f"{self.interview_date} - {self.supplier_name} - {self.interview_type}"
    
    def is_breach_interview(self):
        """判断是否为违约约谈"""
        return self.interview_type == '违约约谈'
    
    def needs_followup(self):
        """判断是否需要跟进"""
        return self.status in ['待整改', '整改中']
    
    def get_status_color(self):
        """获取状态对应的Bootstrap颜色类"""
        status_colors = {
            '待整改': 'danger',
            '整改中': 'warning',
            '已完成': 'success',
            '仅记录': 'secondary',
        }
        return status_colors.get(self.status, 'secondary')
    
    def get_type_badge_color(self):
        """获取约谈类型对应的Bootstrap徽章颜色"""
        type_colors = {
            '违约约谈': 'danger',
            '履约沟通': 'primary',
            '商务洽谈': 'info',
            '投标前沟通': 'success',
            '其他': 'secondary',
        }
        return type_colors.get(self.interview_type, 'secondary')