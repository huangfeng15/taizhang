"""
业务枚举统一定义
所有业务枚举集中在此管理，供模型、表单、筛选器、模板等使用
遵循 DRY 原则，避免枚举在多处重复定义
"""
from django.db import models


class ProcurementMethod(models.TextChoices):
    """采购方式枚举"""
    PUBLIC_BIDDING = '公开招标', '公开招标'
    INVITED_BIDDING = '邀请招标', '邀请招标'
    PUBLIC_INQUIRY = '公开询价', '公开询价'
    INVITED_INQUIRY = '邀请询价', '邀请询价'
    PUBLIC_AUCTION = '公开竞价', '公开竞价'
    INVITED_AUCTION = '邀请竞价', '邀请竞价'
    PUBLIC_COMPARISON = '公开比选', '公开比选'
    INVITED_COMPARISON = '邀请比选', '邀请比选'
    SINGLE_SOURCE = '单一来源采购', '单一来源采购'
    PUBLIC_COMPETITIVE_NEGOTIATION = '公开竞争性谈判', '公开竞争性谈判'
    PUBLIC_COMPETITIVE_CONSULTATION = '公开竞争性磋商', '公开竞争性磋商'
    INVITED_COMPETITIVE_NEGOTIATION = '邀请竞争性谈判', '邀请竞争性谈判'
    INVITED_COMPETITIVE_CONSULTATION = '邀请竞争性磋商', '邀请竞争性磋商'
    DIRECT_PROCUREMENT = '直接采购', '直接采购'
    STRATEGIC_PROCUREMENT = '战采应用', '战采应用'


class ContractSource(models.TextChoices):
    """合同来源枚举"""
    PROCUREMENT = '采购合同', '采购合同'
    DIRECT = '直接签订', '直接签订'


class FilePositioning(models.TextChoices):
    """文件定位枚举"""
    MAIN_CONTRACT = '主合同', '主合同'
    SUPPLEMENT = '补充协议', '补充协议'
    TERMINATION = '解除协议', '解除协议'
    FRAMEWORK = '框架协议', '框架协议'


class ProcurementCategory(models.TextChoices):
    """采购类别枚举"""
    GOODS = '货物', '货物'
    SERVICES = '服务', '服务'
    ENGINEERING = '工程', '工程'


class QualificationReviewMethod(models.TextChoices):
    """资格审查方式枚举"""
    PRE_QUALIFICATION = '资格预审', '资格预审'
    POST_QUALIFICATION = '资格后审', '资格后审'


class BidEvaluationMethod(models.TextChoices):
    """评标方式枚举"""
    COMPREHENSIVE_SCORING = '综合评分法', '综合评分法'
    COMPETITIVE_NEGOTIATION = '竞争性谈判', '竞争性谈判'
    LOWEST_PRICE = '最低价法', '最低价法'


class BidAwardingMethod(models.TextChoices):
    """定标方法枚举"""
    VOTING = '票决法', '票决法'
    LOWEST_PRICE = '最低价法', '最低价法'
    COMPREHENSIVE_EVALUATION = '综合评价法', '综合评价法'


# 枚举辅助函数
def get_enum_choices(enum_class):
    """
    获取枚举的 choices 列表
    
    Args:
        enum_class: Django TextChoices 枚举类
    
    Returns:
        choices 列表，格式: [(value, label), ...]
    """
    return [(choice.value, choice.label) for choice in enum_class]


def get_enum_display_dict(enum_class):
    """
    获取枚举的显示字典
    
    Args:
        enum_class: Django TextChoices 枚举类
    
    Returns:
        字典，格式: {value: label, ...}
    """
    return {choice.value: choice.label for choice in enum_class}


def get_enum_values(enum_class):
    """
    获取枚举的所有值列表
    
    Args:
        enum_class: Django TextChoices 枚举类
    
    Returns:
        值列表，格式: [value1, value2, ...]
    """
    return [choice.value for choice in enum_class]


def get_enum_labels(enum_class):
    """
    获取枚举的所有显示标签列表
    
    Args:
        enum_class: Django TextChoices 枚举类
    
    Returns:
        标签列表，格式: [label1, label2, ...]
    """
    return [choice.label for choice in enum_class]


def get_enum_labels_text(enum_class, separator='、'):
    """
    获取枚举的所有显示标签，用指定分隔符连接
    
    Args:
        enum_class: Django TextChoices 枚举类
        separator: 分隔符，默认为顿号
    
    Returns:
        连接后的字符串，例如: "公开招标、邀请招标、竞争性谈判"
    """
    return separator.join(get_enum_labels(enum_class))