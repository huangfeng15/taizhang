"""操作日志中间件"""
import json
from django.utils.deprecation import MiddlewareMixin
from project.models_operation_log import OperationLog


class OperationLogMiddleware(MiddlewareMixin):
    """记录用户操作日志的中间件"""
    
    def process_response(self, request, response):
        """在响应返回后记录操作日志"""
        # 仅记录POST/PUT/PATCH请求(修改和新增操作)
        if request.method not in ['POST', 'PUT', 'PATCH']:
            return response
        
        # 仅记录成功的请求(2xx状态码)
        if not (200 <= response.status_code < 300):
            return response
        
        # 跳过未认证用户
        if not request.user.is_authenticated:
            return response
        
        # 跳过超级用户
        if request.user.is_superuser:
            return response
        
        # 跳过特定路径(登录、登出、静态文件等)
        skip_paths = ['/accounts/', '/static/', '/media/', '/admin/', '/api/']
        if any(request.path.startswith(path) for path in skip_paths):
            return response
        
        # 解析操作类型和对象
        operation_type, object_type, object_id = self._parse_operation(request)
        if not operation_type or not object_type:
            return response
        
        # 异步记录日志(使用try-except避免日志记录失败影响主请求)
        try:
            object_repr = self._get_object_repr(object_type, object_id)
            description = self._generate_description(
                request.user.username,
                operation_type,
                object_type,
                object_repr,
                request
            )
            
            OperationLog.objects.create(
                user=request.user,
                operation_type=operation_type,
                object_type=object_type,
                object_id=object_id or '',
                object_repr=object_repr,
                description=description,
                ip_address=self._get_client_ip(request),
                changes=self._extract_changes(request)
            )
        except Exception:
            pass  # 静默失败,不影响主请求
        
        return response
    
    def _parse_operation(self, request):
        """解析操作类型和对象"""
        path = request.path
        
        # 根据路径判断操作类型和对象类型
        if '/create/' in path or request.method == 'POST':
            operation_type = 'create'
        elif '/edit/' in path or request.method in ['PUT', 'PATCH']:
            operation_type = 'update'
        else:
            return None, None, None
        
        # 解析对象类型
        if '/project' in path:
            object_type = 'project'
        elif '/procurement' in path:
            object_type = 'procurement'
        elif '/contract' in path:
            object_type = 'contract'
        elif '/payment' in path:
            object_type = 'payment'
        else:
            return None, None, None
        
        # 从路径中提取对象ID
        object_id = self._extract_object_id(path)
        
        return operation_type, object_type, object_id
    
    def _extract_object_id(self, path):
        """从路径中提取对象ID"""
        parts = [p for p in path.split('/') if p and p not in ['edit', 'create']]
        return parts[-1] if parts else None
    
    def _get_object_repr(self, object_type, object_id):
        """获取对象的字符串表示"""
        if not object_id:
            return ''
        
        try:
            if object_type == 'project':
                from project.models import Project
                obj = Project.objects.get(project_code=object_id)
            elif object_type == 'procurement':
                from procurement.models import Procurement
                obj = Procurement.objects.get(procurement_code=object_id)
            elif object_type == 'contract':
                from contract.models import Contract
                obj = Contract.objects.get(contract_code=object_id)
            elif object_type == 'payment':
                from payment.models import Payment
                obj = Payment.objects.get(payment_code=object_id)
            else:
                return ''
            return str(obj)
        except Exception:
            return object_id
    
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    def _generate_description(self, username, operation_type, object_type, object_repr, request):
        """生成详细的中文操作描述"""
        operation_text = '新增' if operation_type == 'create' else '修改'
        object_text = {
            'project': '项目',
            'procurement': '采购',
            'contract': '合同',
            'payment': '付款'
        }.get(object_type, object_type)
        
        # 基础描述
        desc = f"用户 {username} {operation_text}了{object_text}"
        
        # 添加对象信息
        if object_repr:
            desc += f": {object_repr}"
        
        # 添加关键字段变更信息
        if operation_type == 'update':
            changes = self._extract_changes(request)
            if changes:
                changed_fields = self._get_changed_fields_description(changes, object_type)
                if changed_fields:
                    desc += f"\n变更字段: {changed_fields}"
        
        return desc
    
    def _get_changed_fields_description(self, changes, object_type):
        """获取变更字段的中文描述"""
        field_names = {
            # 项目字段
            'project_name': '项目名称',
            'project_code': '项目编号',
            'project_type': '项目类型',
            'budget_amount': '预算金额',
            # 采购字段
            'procurement_code': '采购编号',
            'procurement_method': '采购方式',
            'winning_bidder': '中标单位',
            'bid_amount': '中标金额',
            # 合同字段
            'contract_code': '合同编号',
            'contract_name': '合同名称',
            'contract_amount': '合同金额',
            'party_b': '乙方',
            # 付款字段
            'payment_code': '付款编号',
            'payment_amount': '付款金额',
            'payment_date': '付款日期',
        }
        
        changed = []
        for key in changes.keys():
            if key in field_names:
                changed.append(field_names[key])
        
        return '、'.join(changed) if changed else ''
    
    def _extract_changes(self, request):
        """提取变更内容"""
        try:
            if request.content_type == 'application/json':
                return json.loads(request.body)
            return dict(request.POST)
        except Exception:
            return None