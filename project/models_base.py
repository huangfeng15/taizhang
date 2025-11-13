from django.db import models


class AuditBaseModel(models.Model):
    """
    审计字段基类（仅包含时间字段）。
    - 目的：消除各模型重复声明 created_at/updated_at；
    - 抽象类：不创建独立表；
    - 不改动业务逻辑：字段名/语义保持一致；
    """

    created_at = models.DateTimeField('创建时间', auto_now_add=True, help_text='记录创建时自动填充')
    updated_at = models.DateTimeField('更新时间', auto_now=True, help_text='每次更新时自动填充')

    class Meta:
        abstract = True

