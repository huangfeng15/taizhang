"""
采购管理模块 - 数据模型
"""
from django.db import models
from project.validators import validate_code_field, validate_and_clean_code
from project.helptext import get_help_text
from project.enums import (
    ProcurementMethod, ProcurementCategory, QualificationReviewMethod,
    BidEvaluationMethod, BidAwardingMethod, get_enum_choices
)


from project.models_base import AuditBaseModel

class BaseModel(AuditBaseModel):
    """
    抽象基类 - 所有业务模型继承此类
    包含通用的审计字段（由 AuditBaseModel 提供）与操作用户字段
    """

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

    def save(self, *args, **kwargs):
        """保存前统一执行完整校验和数据清洗"""
        # 自动清洗所有字符串字段：去除前后空白、换行符等
        self._clean_string_fields()
        self.full_clean()
        super().save(*args, **kwargs)
    
    def _clean_string_fields(self):
        """
        清洗所有字符串字段，去除：
        1. 前后空白字符（空格、制表符等）
        2. 换行符、回车符
        3. 其他不可见字符
        """
        for field in self._meta.get_fields():
            # 只处理CharField和TextField
            if isinstance(field, (models.CharField, models.TextField)):
                field_name = field.name
                value = getattr(self, field_name, None)
                
                if value and isinstance(value, str):
                    # 1. 去除前后空白
                    cleaned = value.strip()
                    # 2. 替换所有类型的换行符为空格
                    cleaned = cleaned.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
                    # 3. 合并多个连续空格为单个空格
                    import re
                    cleaned = re.sub(r'\s+', ' ', cleaned)
                    # 4. 再次去除前后空白（处理替换后可能产生的空白）
                    cleaned = cleaned.strip()
                    
                    # 只在值确实改变时才设置
                    if cleaned != value:
                        setattr(self, field_name, cleaned)


class Procurement(BaseModel):
    """采购管理 - 记录采购项目的全生命周期"""

    # ===== 主键 =====
    procurement_code = models.CharField(
        '招采编号',
        max_length=50,
        primary_key=True,
        validators=[validate_code_field],
        help_text='招采编号不能包含 / \\ ? # 等URL特殊字符，例如: GC2025001'
    )

    # ===== 项目关联 =====
    project = models.ForeignKey(
        'project.Project',
        on_delete=models.PROTECT,
        verbose_name='关联项目',
        null=True,
        blank=True,
        related_name='procurements',
        help_text='该采购所属的项目'
    )

    # ===== 基本信息 =====
    project_name = models.CharField(
        '采购项目名称',
        max_length=200,
        blank=False,
        help_text='采购项目的正式名称'
    )

    procurement_unit = models.CharField(
        '采购单位',
        max_length=200,
        blank=True,
        help_text='发起采购的部门或单位'
    )

    procurement_category = models.CharField(
        '采购类别',
        max_length=100,
        blank=True,
        choices=get_enum_choices(ProcurementCategory),
        help_text=f'采购类别，可选值：{", ".join([c.label for c in ProcurementCategory])}'
    )

    procurement_platform = models.CharField(
        '采购平台',
        max_length=100,
        blank=True,
        help_text='例如: 深圳市阳光采购平台'
    )

    procurement_method = models.CharField(
        '采购方式',
        max_length=50,
        blank=True,
        choices=get_enum_choices(ProcurementMethod),
        help_text=get_help_text('procurement', 'procurement_method')
    )

    qualification_review_method = models.CharField(
        '资格审查方式',
        max_length=100,
        blank=True,
        choices=get_enum_choices(QualificationReviewMethod),
        help_text='例如: 资格预审、资格后审'
    )

    bid_evaluation_method = models.CharField(
        '评标谈判方式',
        max_length=50,
        blank=True,
        choices=get_enum_choices(BidEvaluationMethod),
        help_text='例如: 综合评分法、竞争性谈判'
    )

    bid_awarding_method = models.CharField(
        '定标方法',
        max_length=50,
        blank=True,
        choices=get_enum_choices(BidAwardingMethod),
        help_text='例如: 票决法、最低价法'
    )

    # ===== 金额信息 =====
    budget_amount = models.DecimalField(
        '采购预算金额(元)',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='项目采购预算金额'
    )

    control_price = models.DecimalField(
        '采购控制价（元）',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='采购控制价上限'
    )

    winning_amount = models.DecimalField(
        '中标金额（元）',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='最终中标金额'
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

    demand_contact = models.CharField(
        '申请人联系电话（需求部门）',
        max_length=200,
        blank=True,
        help_text=get_help_text('procurement', 'demand_contact')
    )

    # ===== 中标信息 =====
    winning_bidder = models.CharField(
        '中标单位',
        max_length=200,
        blank=True,
        help_text='最终确定的中标供应商'
    )

    winning_contact = models.CharField(
        '中标单位联系人及方式',
        max_length=200,
        blank=True,
        help_text=get_help_text('procurement', 'winning_contact')
    )

    # ===== 时间信息 =====
    planned_completion_date = models.DateField(
        '计划结束采购时间',
        null=True,
        blank=True,
        help_text='计划采购完成日期'
    )

    requirement_approval_date = models.DateField(
        '采购需求书审批完成日期（OA）',
        null=True,
        blank=True,
        help_text='OA系统中需求书审批完成的日期'
    )

    announcement_release_date = models.DateField(
        '公告发布时间',
        null=True,
        blank=True,
        help_text='采购公告在平台发布的日期'
    )

    registration_deadline = models.DateField(
        '报名截止时间',
        null=True,
        blank=True,
        help_text='报名截止日期'
    )

    bid_opening_date = models.DateField(
        '开标时间',
        null=True,
        blank=True,
        help_text='开标的日期'
    )

    candidate_publicity_end_date = models.DateField(
        '候选人公示结束时间',
        null=True,
        blank=True,
        help_text='候选人公示期的结束日期'
    )

    result_publicity_release_date = models.DateField(
        '结果公示发布时间',
        null=True,
        blank=True,
        help_text='结果公示发布的日期'
    )

    notice_issue_date = models.DateField(
        '中标通知书发放日期',
        null=True,
        blank=True,
        help_text='发放中标通知书的日期'
    )

    archive_date = models.DateField(
        '资料归档日期',
        null=True,
        blank=True,
        help_text='相关资料归档的日期'
    )

    # ===== 评审委员会 =====
    evaluation_committee = models.TextField(
        '评标委员会成员',
        blank=True,
        help_text='评标委员会成员名单，多个成员用逗号分隔'
    )

    # ===== 担保信息 =====
    bid_guarantee = models.CharField(
        '投标担保形式及金额（元）',
        max_length=200,
        blank=True,
        help_text='例如: 银行保函 500000.00 或 保证金 48000.00'
    )

    bid_guarantee_return_date = models.DateField(
        '投标担保退回日期',
        null=True,
        blank=True,
        help_text='退还投标担保的日期'
    )

    performance_guarantee = models.CharField(
        '履约担保形式及金额（元）',
        max_length=200,
        blank=True,
        help_text='例如: 银行保函 450000.00'
    )

    # ===== 其他信息 =====
    candidate_publicity_issue = models.TextField(
        '候选人公示期质疑情况',
        blank=True,
        help_text='记录公示期内质疑的受理与处理情况'
    )

    non_bidding_explanation = models.TextField(
        '应招未招说明（由公开转单一或邀请的情况）',
        blank=True,
        help_text='如从公开招标调整为单一来源或邀请招标需说明原因'
    )
    
    # ===== 周报系统相关字段 =====
    current_stage = models.CharField(
        '当前阶段',
        max_length=20,
        blank=True,
        help_text='采购项目当前所处的生命周期阶段(1-7)'
    )
    
    stage_history = models.JSONField(
        '阶段历史',
        default=dict,
        blank=True,
        help_text='记录各阶段的进入时间和完成情况'
    )
    
    is_from_weekly_report = models.BooleanField(
        '来自周报',
        default=False,
        help_text='标识该采购记录是否从周报系统转入'
    )
    
    weekly_report_sync_date = models.DateTimeField(
        '周报同步时间',
        null=True,
        blank=True,
        help_text='从周报系统同步到台账的时间'
    )

    class Meta(BaseModel.Meta):
        verbose_name = '采购信息'
        verbose_name_plural = '采购信息'
        ordering = ['-created_at']
        indexes = [
            # 单字段索引
            models.Index(fields=['procurement_code']),
            models.Index(fields=['winning_bidder']),
            models.Index(fields=['bid_opening_date']),
            models.Index(fields=['result_publicity_release_date']),
            models.Index(fields=['created_at']),
            models.Index(fields=['procurement_officer']),
            models.Index(fields=['archive_date']),
            # 组合索引（配合统计/监控查询，提升过滤与排序性能）
            models.Index(fields=['project', 'procurement_officer']),
            models.Index(fields=['winning_bidder', 'bid_opening_date']),
            models.Index(fields=['procurement_method', 'budget_amount']),
        ]

    def clean(self):
        """业务规则验证"""
        super().clean()

        # 验证和清理编号字段
        if self.procurement_code:
            self.procurement_code = validate_and_clean_code(
                self.procurement_code,
                '招采编号'
            )

    def __str__(self):
        return f"{self.procurement_code} - {self.project_name}"
