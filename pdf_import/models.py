"""
PDF导入数据模型
"""
import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PDFImportSession(models.Model):
    """
    PDF导入会话模型
    用于临时存储PDF导入过程中的数据，支持草稿保存和恢复
    """
    
    # 会话状态选项
    STATUS_EXTRACTING = 'extracting'
    STATUS_PENDING_REVIEW = 'pending_review'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_SAVED = 'saved'
    STATUS_EXPIRED = 'expired'
    
    STATUS_CHOICES = [
        (STATUS_EXTRACTING, '提取中'),
        (STATUS_PENDING_REVIEW, '待确认'),
        (STATUS_CONFIRMED, '已确认'),
        (STATUS_SAVED, '已保存'),
        (STATUS_EXPIRED, '已过期'),
    ]
    
    # 主键：唯一会话ID
    session_id = models.CharField(
        '会话ID',
        max_length=50,
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # 创建人
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='创建人',
        related_name='pdf_import_sessions'
    )
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    # PDF文件信息（JSON存储）
    # 格式：[{
    #     'name': '2-23.采购请示.pdf',
    #     'path': '/media/pdf_import/xxx/...',
    #     'size': 1024000,
    #     'detected_type': 'procurement_request',
    #     'confidence': 0.95
    # }]
    pdf_files = models.JSONField(
        'PDF文件列表',
        default=list,
        blank=True,
        help_text='上传的PDF文件信息列表'
    )
    
    # 提取的数据（JSON存储）
    # 格式：{'project_name': 'XX小区物业服务', 'budget_amount': '1234567.89', ...}
    extracted_data = models.JSONField(
        '提取的数据',
        default=dict,
        blank=True,
        help_text='从PDF中提取的字段数据'
    )
    
    # 验证结果（JSON存储）
    validation_result = models.JSONField(
        '验证结果',
        default=dict,
        blank=True,
        help_text='数据验证结果和错误信息'
    )
    
    # 需要人工确认的字段（JSON存储）
    # 格式：[{
    #     'field': 'procurement_category',
    #     'extracted_value': '地产营销',
    #     'mapped_value': '服务',
    #     'reason': 'PDF别名映射'
    # }]
    requires_confirmation = models.JSONField(
        '需确认字段',
        default=list,
        blank=True,
        help_text='需要用户确认的字段列表'
    )
    
    # 会话状态
    status = models.CharField(
        '状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_EXTRACTING,
        db_index=True
    )
    
    # 过期时间（默认24小时，保存草稿延长至72小时）
    expires_at = models.DateTimeField(
        '过期时间',
        db_index=True,
        help_text='会话过期时间，过期后自动清理'
    )
    
    # 关联的采购记录（保存成功后）
    procurement = models.ForeignKey(
        'procurement.Procurement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='关联采购记录',
        related_name='pdf_import_sessions'
    )
    
    class Meta:
        verbose_name = 'PDF导入会话'
        verbose_name_plural = 'PDF导入会话'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """保存时自动设置过期时间"""
        if not self.expires_at:
            # 默认24小时过期
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """检查会话是否过期"""
        return timezone.now() > self.expires_at
    
    def extend_expiry(self, hours=72):
        """延长会话过期时间（保存草稿时使用）"""
        self.expires_at = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=['expires_at', 'updated_at'])
    
    def get_pdf_count(self):
        """获取PDF文件数量"""
        return len(self.pdf_files) if self.pdf_files else 0
    
    def get_extracted_field_count(self):
        """获取已提取字段数量"""
        return len([v for v in self.extracted_data.values() if v]) if self.extracted_data else 0
    
    def __str__(self):
        return f"{self.session_id} - {self.get_status_display()} ({self.created_by.username})"