"""
周报管理模块 - 数据模型
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from project.models_base import AuditBaseModel
from project.validators import validate_code_field, validate_and_clean_code


class ProcurementStage(models.TextChoices):
    """采购阶段枚举"""
    PLANNING = '1_planning', '完成采购计划立项'
    REQUIREMENT = '2_requirement', '完成采购需求'
    DOCUMENT = '3_document', '完成采购文件及规则编制'
    CONTROL_PRICE = '4_control_price', '完成采购请示及控制价'
    PUBLICITY = '5_publicity', '完成结果公示'
    CONTRACT = '6_contract', '完成采购合同签订'
    ARCHIVE = '7_archive', '完成采购及采购合同归档'


class WeeklyReportStatus(models.TextChoices):
    """周报状态枚举"""
    DRAFT = 'draft', '草稿'
    SUBMITTED = 'submitted', '已提交'


class WeeklyReport(AuditBaseModel):
    """周报主表 - 管理周报的基本信息"""
    
    # ===== 主键 =====
    report_code = models.CharField(
        '周报编号',
        max_length=50,
        primary_key=True,
        validators=[validate_code_field],
        help_text='周报编号格式: WR2025W01 (WR+年份+W+周数)'
    )
    
    # ===== 基本信息 =====
    year = models.IntegerField(
        '年份',
        help_text='周报所属年份'
    )
    
    week = models.IntegerField(
        '周数',
        help_text='周报所属周数(1-53)'
    )
    
    recorder = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='记录人',
        related_name='weekly_reports',
        help_text='负责填写周报的用户'
    )
    
    status = models.CharField(
        '状态',
        max_length=20,
        choices=WeeklyReportStatus.choices,
        default=WeeklyReportStatus.DRAFT.value,
        help_text='周报状态'
    )
    
    submit_date = models.DateTimeField(
        '提交时间',
        null=True,
        blank=True,
        help_text='周报提交的时间'
    )
    
    remarks = models.TextField(
        '备注',
        blank=True,
        help_text='周报相关备注信息'
    )
    
    class Meta:
        verbose_name = '周报'
        verbose_name_plural = '周报'
        ordering = ['-year', '-week']
        unique_together = [['year', 'week', 'recorder']]
        indexes = [
            models.Index(fields=['report_code']),
            models.Index(fields=['year', 'week']),
            models.Index(fields=['recorder', 'status']),
            models.Index(fields=['submit_date']),
        ]
    
    def clean(self):
        """数据验证"""
        errors = {}
        
        # 验证和清理编号字段
        if self.report_code:
            try:
                self.report_code = validate_and_clean_code(
                    self.report_code,
                    '周报编号'
                )
            except ValidationError as e:
                errors['report_code'] = e.message
        
        # 验证周数范围
        if self.week and (self.week < 1 or self.week > 53):
            errors['week'] = '周数必须在1-53之间'
        
        # 验证年份范围
        if self.year and (self.year < 2000 or self.year > 2100):
            errors['year'] = '年份必须在2000-2100之间'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """保存前执行完整验证"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.report_code} - {self.year}年第{self.week}周"


class ProcurementProgress(AuditBaseModel):
    """采购进度追踪 - 记录采购项目的生命周期进展"""
    
    # ===== 主键 =====
    progress_code = models.CharField(
        '进度编号',
        max_length=50,
        primary_key=True,
        validators=[validate_code_field],
        help_text='进度编号格式: PP2025001'
    )
    
    # ===== 关联信息 =====
    weekly_report = models.ForeignKey(
        WeeklyReport,
        on_delete=models.CASCADE,
        verbose_name='关联周报',
        related_name='progress_items',
        help_text='该进度记录所属的周报'
    )
    
    procurement = models.ForeignKey(
        'procurement.Procurement',
        on_delete=models.PROTECT,
        verbose_name='关联采购',
        null=True,
        blank=True,
        related_name='progress_records',
        help_text='转入台账后关联的采购记录'
    )
    
    # ===== 项目基本信息(冗余存储,便于未转入前查询) =====
    project_name = models.CharField(
        '采购项目名称',
        max_length=200,
        help_text='采购项目的正式名称'
    )
    
    project_code = models.CharField(
        '项目编号',
        max_length=50,
        blank=True,
        help_text='项目编号(如有)'
    )
    
    # ===== 阶段信息 =====
    current_stage = models.CharField(
        '当前阶段',
        max_length=20,
        choices=ProcurementStage.choices,
        help_text='采购项目当前所处阶段'
    )
    
    previous_stage = models.CharField(
        '上一阶段',
        max_length=20,
        choices=ProcurementStage.choices,
        null=True,
        blank=True,
        help_text='采购项目上一个阶段'
    )
    
    stage_data = models.JSONField(
        '阶段数据',
        default=dict,
        blank=True,
        help_text='存储各阶段的详细数据(JSON格式)'
    )
    
    # ===== 归档状态 =====
    is_archived = models.BooleanField(
        '是否已归档',
        default=False,
        help_text='标识该采购项目是否已完成归档'
    )
    
    archived_date = models.DateTimeField(
        '归档时间',
        null=True,
        blank=True,
        help_text='采购项目归档的时间'
    )
    
    synced_to_ledger = models.BooleanField(
        '是否已同步到台账',
        default=False,
        help_text='标识是否已转入现有台账系统'
    )
    
    synced_date = models.DateTimeField(
        '同步时间',
        null=True,
        blank=True,
        help_text='同步到台账的时间'
    )
    
    # ===== 补录信息 =====
    missing_fields = models.JSONField(
        '缺失字段',
        default=list,
        blank=True,
        help_text='需要补录的字段列表'
    )
    
    has_missing_info = models.BooleanField(
        '存在缺失信息',
        default=False,
        help_text='标识是否存在需要补录的信息'
    )
    
    remarks = models.TextField(
        '备注',
        blank=True,
        help_text='进度相关备注信息'
    )
    
    class Meta:
        verbose_name = '采购进度'
        verbose_name_plural = '采购进度'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['progress_code']),
            models.Index(fields=['weekly_report', 'current_stage']),
            models.Index(fields=['project_name']),
            models.Index(fields=['is_archived', 'synced_to_ledger']),
            models.Index(fields=['procurement']),
        ]
    
    def clean(self):
        """数据验证"""
        errors = {}
        
        # 验证和清理编号字段
        if self.progress_code:
            try:
                self.progress_code = validate_and_clean_code(
                    self.progress_code,
                    '进度编号'
                )
            except ValidationError as e:
                errors['progress_code'] = e.message
        
        # 验证归档状态
        if self.is_archived and not self.archived_date:
            errors['archived_date'] = '已归档的记录必须填写归档时间'
        
        # 验证同步状态
        if self.synced_to_ledger:
            if not self.synced_date:
                errors['synced_date'] = '已同步的记录必须填写同步时间'
            if not self.procurement:
                errors['procurement'] = '已同步的记录必须关联采购记录'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """保存前执行完整验证"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.progress_code} - {self.project_name} ({self.get_current_stage_display()})"
    
    def get_stage_order(self):
        """获取当前阶段的顺序号"""
        stage_order = {
            ProcurementStage.PLANNING.value: 1,
            ProcurementStage.REQUIREMENT.value: 2,
            ProcurementStage.DOCUMENT.value: 3,
            ProcurementStage.CONTROL_PRICE.value: 4,
            ProcurementStage.PUBLICITY.value: 5,
            ProcurementStage.CONTRACT.value: 6,
            ProcurementStage.ARCHIVE.value: 7,
        }
        return stage_order.get(self.current_stage, 0)
    
    def can_transition_to(self, target_stage):
        """检查是否可以转换到目标阶段"""
        current_order = self.get_stage_order()
        target_order = {
            ProcurementStage.PLANNING.value: 1,
            ProcurementStage.REQUIREMENT.value: 2,
            ProcurementStage.DOCUMENT.value: 3,
            ProcurementStage.CONTROL_PRICE.value: 4,
            ProcurementStage.PUBLICITY.value: 5,
            ProcurementStage.CONTRACT.value: 6,
            ProcurementStage.ARCHIVE.value: 7,
        }.get(target_stage, 0)
        
        # 只能向前推进,不能后退
        return target_order > current_order


class WeeklyReportReminder(models.Model):
    """周报提醒记录 - 管理周报填写提醒"""
    
    # ===== 主键 =====
    reminder_code = models.CharField(
        '提醒编号',
        max_length=50,
        primary_key=True,
        validators=[validate_code_field],
        help_text='提醒编号格式: RMD2025001'
    )
    
    # ===== 提醒信息 =====
    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='目标用户',
        related_name='reminders',
        help_text='接收提醒的用户'
    )
    
    reminder_date = models.DateTimeField(
        '提醒时间',
        auto_now_add=True,
        help_text='提醒发送的时间'
    )
    
    content = models.TextField(
        '提醒内容',
        help_text='提醒的具体内容'
    )
    
    reminder_type = models.CharField(
        '提醒类型',
        max_length=50,
        default='weekly_report',
        choices=[
            ('weekly_report', '周报填写'),
            ('missing_info', '信息补录'),
            ('archive', '归档提醒'),
            ('sync', '同步提醒'),
        ],
        help_text='提醒类型'
    )
    
    # ===== 关联信息 =====
    related_report = models.ForeignKey(
        WeeklyReport,
        on_delete=models.CASCADE,
        verbose_name='关联周报',
        null=True,
        blank=True,
        related_name='reminders',
        help_text='关联的周报记录'
    )
    
    related_progress = models.ForeignKey(
        ProcurementProgress,
        on_delete=models.CASCADE,
        verbose_name='关联进度',
        null=True,
        blank=True,
        related_name='reminders',
        help_text='关联的进度记录'
    )
    
    # ===== 状态信息 =====
    is_read = models.BooleanField(
        '是否已读',
        default=False,
        help_text='标识用户是否已读该提醒'
    )
    
    read_date = models.DateTimeField(
        '已读时间',
        null=True,
        blank=True,
        help_text='用户读取提醒的时间'
    )
    
    is_handled = models.BooleanField(
        '是否已处理',
        default=False,
        help_text='标识提醒事项是否已处理'
    )
    
    handled_date = models.DateTimeField(
        '处理时间',
        null=True,
        blank=True,
        help_text='提醒事项处理的时间'
    )
    
    class Meta:
        verbose_name = '周报提醒'
        verbose_name_plural = '周报提醒'
        ordering = ['-reminder_date']
        indexes = [
            models.Index(fields=['reminder_code']),
            models.Index(fields=['target_user', 'is_read']),
            models.Index(fields=['reminder_date']),
            models.Index(fields=['reminder_type']),
        ]
    
    def clean(self):
        """数据验证"""
        if self.reminder_code:
            self.reminder_code = validate_and_clean_code(
                self.reminder_code,
                '提醒编号'
            )
    
    def save(self, *args, **kwargs):
        """保存前执行完整验证"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        type_display = dict([
            ('weekly_report', '周报填写'),
            ('missing_info', '信息补录'),
            ('archive', '归档提醒'),
            ('sync', '同步提醒'),
        ]).get(self.reminder_type, self.reminder_type)
        return f"{self.reminder_code} - {self.target_user.username} ({type_display})"
    
    def mark_as_read(self):
        """标记为已读"""
        from django.utils import timezone
        self.is_read = True
        self.read_date = timezone.now()
        self.save()
    
    def mark_as_handled(self):
        """标记为已处理"""
        from django.utils import timezone
        self.is_handled = True
        self.handled_date = timezone.now()
        self.save()
