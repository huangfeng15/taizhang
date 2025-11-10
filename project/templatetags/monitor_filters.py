"""监控模板过滤器"""
from django import template

register = template.Library()


@register.filter
def lookup(dictionary, key):
    """字典查找过滤器"""
    return dictionary.get(key, [])


@register.filter
def abs_value(value):
    """返回数值的绝对值"""
    try:
        return abs(int(value))
    except (ValueError, TypeError):
        return value
