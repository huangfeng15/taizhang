"""
通用验证器模块
用于验证各类编号字段，确保不包含URL不安全字符
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# URL不安全字符模式（除了空白和换行符外的特殊字符）
# 这些字符会导致URL路径解析错误
URL_UNSAFE_CHARS_PATTERN = r'[/\\?#\[\]@!$&\'()*+,;=<>{}|^`"%]'


def validate_code_field(value):
    """
    验证编号字段，确保不包含URL不安全字符
    
    允许的字符：
    - 字母（a-z, A-Z）
    - 数字（0-9）
    - 中文字符
    - 连字符 (-)
    - 下划线 (_)
    - 点 (.)
    - 空格（会被自动清理）
    
    禁止的字符（会导致URL解析错误）：
    / \\ ? # [ ] @ ! $ & ' ( ) * + , ; = < > { } | ^ ` " %
    
    Args:
        value: 要验证的字段值
        
    Raises:
        ValidationError: 当字段包含URL不安全字符时
    """
    if not value:
        return
    
    # 转换为字符串
    value_str = str(value)
    
    # 检查是否包含URL不安全字符
    unsafe_matches = re.findall(URL_UNSAFE_CHARS_PATTERN, value_str)
    if unsafe_matches:
        # 获取唯一的不安全字符
        unsafe_chars = sorted(set(unsafe_matches))
        raise ValidationError(
            _('编号不能包含以下特殊字符：%(chars)s。这些字符可能导致URL解析错误。') % {
                'chars': ' '.join(unsafe_chars)
            },
            code='invalid_code_format'
        )


def clean_whitespace(value):
    """
    清理多余的空白字符和换行符
    将多个连续空白字符替换为单个空格
    
    Args:
        value: 要清理的字符串
        
    Returns:
        str: 清理后的字符串
    """
    if not value:
        return value
    return ' '.join(str(value).split())


def validate_and_clean_code(value, field_name='编号'):
    """
    验证并清理编号字段的便捷函数
    
    Args:
        value: 要验证和清理的值
        field_name: 字段名称，用于错误消息
        
    Returns:
        str: 清理并验证后的值
        
    Raises:
        ValidationError: 当包含不允许的字符时
    """
    if not value:
        return value
    
    try:
        cleaned = clean_whitespace(value)
        validate_code_field(cleaned)
        return cleaned
    except ValidationError as e:
        # 添加字段名称到错误消息
        raise ValidationError(
            _(f'{field_name}验证失败：{e.message}'),
            code=e.code
        )


def check_url_safe_string(value):
    """
    检查字符串是否为URL安全的
    
    Args:
        value: 要检查的字符串
        
    Returns:
        tuple: (is_safe: bool, unsafe_chars: list)
    """
    if not value:
        return True, []
    
    value_str = str(value)
    unsafe_matches = re.findall(URL_UNSAFE_CHARS_PATTERN, value_str)
    
    if unsafe_matches:
        return False, sorted(set(unsafe_matches))
    return True, []