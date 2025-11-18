"""操作日志中间件"""
import json
from django.utils.deprecation import MiddlewareMixin
from project.models_operation_log import OperationLog
from project.utils.operation_log_helpers import get_client_ip


class OperationLogMiddleware(MiddlewareMixin):
    """记录用户操作日志的中间件"""

    def process_response(self, request, response):
        """在响应返回后记录操作日志"""
        # 仅记录POST/PUT/PATCH请求(修改和新增操作)
        if request.method not in ["POST", "PUT", "PATCH"]:
            return response

        # 仅记录成功的请求(2xx状态码)
        if not (200 <= response.status_code < 300):
            return response

        # 跳过未认证用户
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return response

        # 跳过超级用户
        if request.user.is_superuser:
            return response

        # 跳过特定路径(登录、登出、静态文件等)
        # 注意：这里不再一刀切跳过 /api/，以便记录通过 API 修改项目/采购/合同/付款的数据变更
        skip_paths = ["/accounts/", "/static/", "/media/", "/admin/"]
        if any(request.path.startswith(path) for path in skip_paths):
            return response

        # 解析操作类型和对象
        operation_type, object_type, object_id = self._parse_operation(request)
        if not operation_type or not object_type:
            return response

        # 提取字段级变更信息
        changes = self._extract_changes(request, operation_type=operation_type)
        # 对于更新操作，如果没有任何字段发生变化，则不记录日志，避免噪声
        if operation_type == "update" and not changes:
            return response

        # 异步记录日志(使用try-except避免日志记录失败影响主请求)
        try:
            object_repr = self._get_object_repr(object_type, object_id)
            description = self._generate_description(
                request.user.username,
                operation_type,
                object_type,
                object_repr,
                changes,
            )

            OperationLog.objects.create(
                user=request.user,
                operation_type=operation_type,
                object_type=object_type,
                object_id=object_id or "",
                object_repr=object_repr,
                description=description,
                ip_address=self._get_client_ip(request),
                changes=changes,
            )
        except Exception:
            # 静默失败,不影响主请求
            pass

        return response

    def _parse_operation(self, request):
        """解析操作类型和对象"""
        path = request.path

        # 先解析对象类型，确保只处理关心的业务对象
        if "/project" in path:
            object_type = "project"
        elif "/procurement" in path:
            object_type = "procurement"
        elif "/contract" in path:
            object_type = "contract"
        elif "/payment" in path:
            object_type = "payment"
        else:
            return None, None, None

        # 再根据路径和 HTTP 方法判断操作类型
        # 优先识别编辑/快速更新路径，避免简单 POST 误判为“新增”
        if "/edit/" in path or "/quick-update/" in path or request.method in ["PUT", "PATCH"]:
            operation_type = "update"
        elif "/create/" in path or request.method == "POST":
            operation_type = "create"
        else:
            return None, None, None

        # 根据对象类型与请求数据提取对象 ID
        object_id = self._extract_object_id(path, request, object_type)

        return operation_type, object_type, object_id

    def _extract_object_id(self, path, request, object_type):
        """提取操作对象ID。

        - 对于编辑操作，优先从路径中获取(例如 /contracts/<code>/edit/)。
        - 对于新增操作，若路径中无ID，则从表单 POST 数据中读取主键字段。
        """
        # 优先从 URL 中解析(适用于 /<module>/<code>/edit/ 这类路径)
        parts = [p for p in path.split("/") if p and p not in ["edit", "create"]]
        if parts:
            # 像 /contracts/<code>/edit/ 这类路径，最后一段通常是业务主键
            candidate = parts[-1]
            # 避免在 /contracts/create/ 这类路径中把 "contracts" 误当成 ID
            if candidate and candidate not in ["projects", "contracts", "procurements", "payments"]:
                return candidate

        # 对于新增请求，从表单字段中提取主键
        if request.method == "POST":
            code_field_map = {
                "project": "project_code",
                "procurement": "procurement_code",
                "contract": "contract_code",
                "payment": "payment_code",
            }
            field_name = code_field_map.get(object_type)
            if field_name and field_name in request.POST:
                return request.POST.get(field_name)

        return None

    def _get_object_repr(self, object_type, object_id):
        """获取对象的字符串表示"""
        if not object_id:
            return ""

        try:
            if object_type == "project":
                from project.models import Project

                obj = Project.objects.get(project_code=object_id)
            elif object_type == "procurement":
                from procurement.models import Procurement

                obj = Procurement.objects.get(procurement_code=object_id)
            elif object_type == "contract":
                from contract.models import Contract

                obj = Contract.objects.get(contract_code=object_id)
            elif object_type == "payment":
                from payment.models import Payment

                obj = Payment.objects.get(payment_code=object_id)
            else:
                return ""
            return str(obj)
        except Exception:
            return object_id

    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        return get_client_ip(request)

    def _generate_description(self, username, operation_type, object_type, object_repr, changes):
        """生成详细的中文操作描述"""
        operation_text = "新增" if operation_type == "create" else "修改"
        object_text = {
            "project": "项目",
            "procurement": "采购",
            "contract": "合同",
            "payment": "付款",
        }.get(object_type, object_type)

        # 基础描述
        desc = f"用户 {username} {operation_text}了{object_text}"

        # 添加对象信息
        if object_repr:
            desc += f": {object_repr}"

        # 添加关键字段变更信息(仅对更新操作追加详细 diff)
        if operation_type == "update" and changes:
            detailed_lines = self._format_changes_description(changes)
            if detailed_lines:
                desc += "\n" + detailed_lines

        return desc

    def _format_changes_description(self, changes):
        """将变更内容格式化为多行中文描述。"""
        # 字段展示名映射表(可按需扩展)
        field_names = {
            # 项目字段
            "project_name": "项目名称",
            "project_code": "项目编号",
            "project_type": "项目类型",
            "budget_amount": "预算金额",
            # 采购字段
            "procurement_code": "采购编号",
            "procurement_method": "采购方式",
            "winning_bidder": "中标单位",
            "bid_amount": "中标金额",
            # 合同字段
            "contract_code": "合同编号",
            "contract_name": "合同名称",
            "contract_amount": "合同金额",
            "contract_type": "合同类型",
            "party_b": "乙方",
            # 付款字段
            "payment_code": "付款编号",
            "payment_amount": "付款金额",
            "payment_date": "付款日期",
        }

        if not isinstance(changes, dict):
            return ""

        lines = []
        # 结构化 diff: {field: {"old": ..., "new": ...}}
        for field, value in changes.items():
            label = field_names.get(field, field)
            if isinstance(value, dict) and "old" in value and "new" in value:
                old_val = value.get("old")
                new_val = value.get("new")
                lines.append(f"变更字段【{label}】: {old_val} -> {new_val}")
            else:
                # 回退到仅展示字段名(兼容旧数据或非结构化changes)
                lines.append(f"变更字段【{label}】")

        return "\n".join(lines)

    def _extract_changes(self, request, operation_type: str | None = None):
        """提取变更内容"""
        # 1. 优先使用视图提前计算好的字段级 diff
        meta = getattr(request, "operation_log_meta", None)
        if isinstance(meta, dict) and "changes" in meta:
            return meta.get("changes") or None

        # 2. 回退到原始请求数据(仅用于新增等场景，无字段级旧值信息)
        try:
            if request.content_type == "application/json":
                return json.loads(request.body)
            return dict(request.POST)
        except Exception:
            return None
