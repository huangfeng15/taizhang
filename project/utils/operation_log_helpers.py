"""操作日志相关的通用辅助函数"""
from typing import Any, Dict, Iterable

from django.db.models import Model
from django.forms import ModelForm


def capture_model_changes(
    instance: Model,
    form: ModelForm,
    tracked_fields: Iterable[str] | None = None,
):
    """根据表单与原始实例计算字段级变更。

    返回 (待保存的实例, changes_dict)。
    changes_dict 结构为: {field_name: {"old": old_str, "new": new_str}}。
    """
    if tracked_fields is None:
        tracked_fields = form.fields.keys()

    # 记录原始值
    original_values: Dict[str, Any] = {}
    for field_name in tracked_fields:
        original_values[field_name] = getattr(instance, field_name, None)

    # 应用表单变更但暂不保存到数据库
    obj = form.save(commit=False)

    changes: Dict[str, Dict[str, Any]] = {}
    for field_name in tracked_fields:
        old_value = original_values.get(field_name)
        new_value = getattr(obj, field_name, None)
        if old_value != new_value:
            changes[field_name] = {
                "old": _serialize_value(old_value),
                "new": _serialize_value(new_value),
            }

    return obj, changes


def _serialize_value(value: Any) -> Any:
    """将字段值序列化为便于存储/展示的形式。"""
    if value is None:
        return None
    return str(value)


def get_client_ip(request) -> str | None:
    """统一的客户端 IP 提取逻辑, 供中间件和视图复用。"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
