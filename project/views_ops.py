import csv
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, date
from io import StringIO, BytesIO
from pathlib import Path
from urllib.parse import quote
from django.utils.http import content_disposition_header

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods, require_POST

from .models import Project
from contract.models import Contract
from procurement.models import Procurement
from payment.models import Payment
from project.models_operation_log import OperationLog
from project.utils.operation_log_helpers import get_client_ip
from project.services.export_service import (
    generate_project_excel,
    import_project_excel,
    ProjectDataImportError,
)
from project.tasks import generate_project_export_zip_async

from .views_helpers import _get_page_size, _resolve_global_filters

def _format_import_summary(stats: dict) -> str:
    return (
        f"已删除采购 {stats.get('procurements_deleted', 0)} 条，合同 {stats.get('contracts_deleted', 0)} 条，付款 {stats.get('payments_deleted', 0)} 条\n"
        f"本次导入新增采购 {stats.get('procurements_created', 0)} 条，合同 {stats.get('contracts_created', 0)} 条，付款 {stats.get('payments_created', 0)} 条"
    )


def _format_import_failure(stats: dict) -> str:
    error_count = len(stats.get('errors', []))
    message_lines = [
        f"导入失败，共 {error_count} 条错误。",
        _format_import_summary(stats),
        "错误详情：",
    ]
    for err in stats.get('errors', [])[:10]:
        message_lines.append(err)
    remaining = error_count - 10
    if remaining > 0:
        message_lines.append(f"... 其余 {remaining} 条错误已省略")
    return "\n".join(message_lines)


from project.decorators import require_permission


@login_required
@require_permission('project.view_project')
@require_http_methods(["GET", "POST", "DELETE", "PUT"])
def database_management(request):
    """数据库管理：备份、恢复、清理、下载。"""
    default_db = settings.DATABASES.get('default', {})
    engine = default_db.get('ENGINE', '')
    db_name = default_db.get('NAME')
    db_path = None

    if engine.endswith('sqlite3') and db_name:
        db_path = Path(db_name)
        if not db_path.is_absolute():
            db_path = Path(settings.BASE_DIR) / db_name
        db_path = db_path.resolve()

    backups_dir = Path(settings.BASE_DIR) / 'backups' / 'database'
    backups_dir.mkdir(parents=True, exist_ok=True)

    def _format_size(num_bytes: int) -> str:
        size = float(num_bytes)
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        for unit in units:
            if size < 1024 or unit == units[-1]:
                return f'{size:.2f} {unit}'
            size /= 1024
        return f'{num_bytes} B'

    def _collect_db_stat(path: Path):
        if not path or not path.exists():
            return None
        stat = path.stat()
        # 将文件时间戳转换为aware datetime
        modified_at = timezone.make_aware(datetime.fromtimestamp(stat.st_mtime))
        return {
            'path': str(path),
            'name': path.name,  # 添加文件名字段
            'size_bytes': stat.st_size,
            'modified_at': modified_at,
            'size_display': _format_size(stat.st_size),
            'modified_display': modified_at.strftime('%Y-%m-%d %H:%M:%S'),
        }

    if request.method == "DELETE":
        try:
            data = json.loads(request.body)
            file_name = data.get('file_name')
            if not file_name:
                return JsonResponse({'success': False, 'message': '未指定要删除的备份文件'}, status=400)
            backup_file = backups_dir / file_name
            if not backup_file.exists():
                return JsonResponse({'success': False, 'message': '备份文件不存在'}, status=404)
            backup_file.unlink()
            return JsonResponse({'success': True, 'message': f'备份文件 {file_name} 已删除'})
        except Exception as exc:
            return JsonResponse({'success': False, 'message': f'删除失败：{exc}'}, status=500)

    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            old_name = data.get('old_name')
            new_name = data.get('new_name', '').strip()
            if not old_name or not new_name:
                return JsonResponse({'success': False, 'message': '请提供原文件名和新文件名'}, status=400)
            import re
            clean_name = re.sub(r'[<>:"/\\|?*]', '_', new_name).strip('. ')
            if not clean_name:
                return JsonResponse({'success': False, 'message': '新文件名无效'}, status=400)
            if not clean_name.lower().endswith('.sqlite3'):
                clean_name += '.sqlite3'
            old_file = backups_dir / old_name
            new_file = backups_dir / clean_name
            if not old_file.exists():
                return JsonResponse({'success': False, 'message': '原备份文件不存在'}, status=404)
            if new_file.exists():
                return JsonResponse({'success': False, 'message': f'文件名已存在：{clean_name}'}, status=400)
            old_file.rename(new_file)
            return JsonResponse({'success': True, 'message': f'备份文件已重命名为：{clean_name}'})
        except Exception as exc:
            return JsonResponse({'success': False, 'message': f'重命名失败：{exc}'}, status=500)

    if request.method == "POST":
        action = request.POST.get('action')
        try:
            if action == 'clear':
                call_command('clearsessions')
                messages.success(request, '会话数据已清理')
            elif action == 'backup':
                if not db_path or not db_path.exists():
                    messages.error(request, '未找到数据库文件，无法备份')
                else:
                    # 获取用户输入的备份名称
                    backup_name = request.POST.get('backup_name', '').strip()
                    if not backup_name:
                        messages.error(request, '请输入备份名称')
                    else:
                        # 清理文件名中的非法字符
                        import re
                        clean_name = re.sub(r'[<>:"/\\|?*]', '_', backup_name).strip('. ')
                        if not clean_name:
                            messages.error(request, '备份名称无效')
                        else:
                            # 添加时间戳以避免重名
                            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                            if not clean_name.lower().endswith('.sqlite3'):
                                backup_file = backups_dir / f'{clean_name}_{ts}.sqlite3'
                            else:
                                # 如果用户输入已包含.sqlite3，在扩展名前插入时间戳
                                base_name = clean_name[:-8]  # 移除.sqlite3
                                backup_file = backups_dir / f'{base_name}_{ts}.sqlite3'
                            shutil.copy2(db_path, backup_file)
                            messages.success(request, f'数据库已备份到：{backup_file.name}')
            elif action == 'restore':
                file_name = request.POST.get('file_name', '').strip()
                if not file_name:
                    return JsonResponse({
                        'success': False,
                        'message': '请选择要恢复的备份文件'
                    }, status=400)
                
                src_file = backups_dir / file_name
                if not src_file.exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'备份文件不存在：{file_name}'
                    }, status=404)
                
                if not db_path:
                    return JsonResponse({
                        'success': False,
                        'message': '无法定位数据库文件'
                    }, status=500)
                
                try:
                    shutil.copy2(src_file, db_path)
                    # 返回JSON响应而不是使用messages
                    return JsonResponse({
                        'success': True,
                        'message': f'数据库已从备份"{file_name}"恢复成功'
                    })
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'message': f'恢复失败：{str(e)}'
                    }, status=500)
            else:
                messages.error(request, '不支持的操作')
        except Exception as exc:
            messages.error(request, f'操作失败：{exc}')

    db_stat = _collect_db_stat(db_path) if db_path else None
    backups = []
    for file in backups_dir.glob('*.sqlite3'):
        info = _collect_db_stat(file)
        if info:
            backups.append(info)
    backups.sort(key=lambda x: x['modified_at'], reverse=True)

    # SQLite3 数据库支持文件级备份
    supports_file_ops = engine.endswith('sqlite3') and db_path is not None
    
    # 获取所有项目用于导入功能
    projects = Project.objects.all().order_by('project_name')
    
    context = {
        'db_stat': db_stat,
        'backups': backups,
        'engine': engine,
        'db_path': str(db_path) if db_path else None,
        'supports_file_ops': supports_file_ops,
        'projects': projects
    }
    return render(request, 'database_management.html', context)


@csrf_protect
@require_POST
def restore_database_no_auth(request):
    """数据库恢复接口（无需登录验证）
    
    为了避免会话过期导致的登录跳转问题，提供一个不需要登录验证的恢复接口。
    仅支持POST请求，需要提供CSRF token。
    """
    try:
        file_name = request.POST.get('file_name', '').strip()
        if not file_name:
            return JsonResponse({
                'success': False,
                'message': '请选择要恢复的备份文件'
            }, status=400)
        
        # 获取数据库配置
        default_db = settings.DATABASES.get('default', {})
        engine = default_db.get('ENGINE', '')
        db_name = default_db.get('NAME')
        
        # 仅支持SQLite数据库
        if not engine.endswith('sqlite3') or not db_name:
            return JsonResponse({
                'success': False,
                'message': '当前数据库引擎不支持文件级恢复'
            }, status=400)
        
        # 获取数据库文件路径
        db_path = Path(db_name)
        if not db_path.is_absolute():
            db_path = Path(settings.BASE_DIR) / db_name
        db_path = db_path.resolve()
        
        # 获取备份文件路径
        backups_dir = Path(settings.BASE_DIR) / 'backups' / 'database'
        src_file = backups_dir / file_name
        
        if not src_file.exists():
            return JsonResponse({
                'success': False,
                'message': f'备份文件不存在：{file_name}'
            }, status=404)
        
        # 执行恢复操作
        try:
            shutil.copy2(src_file, db_path)
            return JsonResponse({
                'success': True,
                'message': f'数据库已从备份"{file_name}"恢复成功'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'恢复失败：{str(e)}'
            }, status=500)
    
    except Exception as exc:
        return JsonResponse({
            'success': False,
            'message': f'操作失败：{str(exc)}'
        }, status=500)


@login_required
@require_http_methods(['GET'])
def download_import_template(request):
    """下载导入模板（包含字段说明）。
    
    模块名称规范：
    - project: 项目
    - procurement: 采购
    - contract: 合同
    - payment: 付款
    - supplier_eval: 供应商评价
    """
    module = request.GET.get('module', 'project')
    mode = request.GET.get('mode', 'long')

    # 直接从 template_generator 导入配置，避免循环导入
    from project.template_generator import get_import_template_config
    
    module_config = get_import_template_config().get(module)
    if not module_config:
        return HttpResponse('不支持的导入模块', status=400)
    template_config = module_config.get(mode)
    if not template_config:
        return HttpResponse('当前模块暂不支持该模板类型', status=400)

    headers = template_config['headers']
    note_column = template_config.get('note_column', '模板说明')

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for note in template_config.get('notes', []):
        note_text = str(note).strip()
        row = [note_text if header == note_column else '' for header in headers]
        writer.writerow(row)
    csv_bytes = buffer.getvalue().encode('utf-8-sig')
    
    filename = template_config["filename"]
    
    # 使用更兼容的Content-Disposition头，支持中文文件名
    response = HttpResponse(csv_bytes, content_type='text/csv; charset=utf-8')
    
    # 使用RFC 5987编码，兼容更多浏览器
    encoded_filename = quote(filename.encode('utf-8'))
    response['Content-Disposition'] = (
        f'attachment; '
        f'filename="{filename}"; '
        f"filename*=UTF-8''{encoded_filename}"
    )
    response['Content-Length'] = str(len(csv_bytes))
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    response['X-Content-Type-Options'] = 'nosniff'
    
    return response


@login_required
@require_POST
def import_data(request):
    """通用数据导入接口（增强统计反馈）。
    
    模块名称规范：
    - project: 项目
    - procurement: 采购
    - contract: 合同
    - payment: 付款
    - supplier_eval: 供应商评价
    """
    # 权限检查：确保用户已登录且有权限
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'message': '未找到上传文件'}, status=400)
        uploaded_file = request.FILES['file']
        module = request.POST.get('module', 'project')
        
        # 支持CSV和XLSX格式
        file_extension = uploaded_file.name.lower().split('.')[-1]
        if file_extension not in ['csv', 'xlsx', 'xls']:
            return JsonResponse({'success': False, 'message': '仅支持CSV和Excel文件格式(.csv, .xlsx, .xls)'})

        # 保存上传文件到临时文件
        suffix = f'.{file_extension}'
        with tempfile.NamedTemporaryFile(mode='wb', suffix=suffix, delete=False) as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name

        try:
            # 如果是Excel文件，先转换为CSV
            if file_extension in ['xlsx', 'xls']:
                # 使用pandas读取Excel文件
                try:
                    df = pd.read_excel(tmp_file_path, dtype=str)
                    # 创建临时CSV文件
                    csv_tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig')
                    csv_tmp_path = csv_tmp_file.name
                    csv_tmp_file.close()
                    
                    # 将Excel转换为CSV
                    df.to_csv(csv_tmp_path, index=False, encoding='utf-8-sig')
                    
                    # 删除原Excel临时文件，使用CSV文件路径
                    os.unlink(tmp_file_path)
                    tmp_file_path = csv_tmp_path
                    detected_encoding = 'utf-8-sig'
                except Exception as e:
                    return JsonResponse({'success': False, 'message': f'Excel文件读取失败: {str(e)}'})
            else:
                # CSV文件，检测编码
                import chardet
                with open(tmp_file_path, 'rb') as f:
                    raw_data = f.read(10000)
                    result = chardet.detect(raw_data)
                    detected_encoding = result.get('encoding', 'utf-8-sig')
                    if detected_encoding and result.get('confidence', 0) > 0.7:
                        encoding_map = {'GB2312': 'gbk', 'ISO-8859-1': 'latin1', 'ascii': 'utf-8'}
                        detected_encoding = encoding_map.get(detected_encoding, detected_encoding)
                    else:
                        detected_encoding = 'utf-8-sig'
            
            # 读取CSV文件获取列数
            import csv as _csv
            with open(tmp_file_path, 'r', encoding=detected_encoding) as f:
                reader = _csv.reader(f)
                header = next(reader)
                column_count = len(header)
            
            # 供应商评价使用专用的导入命令（带JSON输出）
            if module == 'supplier_eval':
                out = StringIO()
                call_command(
                    'import_supplier_eval_v2',
                    tmp_file_path,
                    '--encoding', detected_encoding,
                    '--update',
                    '--json-output',
                    stdout=out, stderr=out
                )
                output = out.getvalue()
            else:
                # 其他模块使用通用导入命令
                import_mode = 'long'
                # 付款模块支持宽表模式
                if module == 'payment' and column_count > 10:
                    import_mode = 'wide'

                out = StringIO()
                call_command(
                    'import_excel',
                    tmp_file_path,
                    '--module', module,
                    '--mode', import_mode,
                    '--conflict-mode', 'update',
                    '--encoding', detected_encoding,
                    '--json-output',
                    stdout=out, stderr=out
                )
                output = out.getvalue()

            import re
            def clean_ansi(text: str) -> str:
                ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
                return ansi_escape.sub('', text)

            cleaned_output = clean_ansi(output)

            # 提取命令输出中的JSON摘要（命令已支持 --json-output）
            summary = None
            for line in cleaned_output.split('\n'):
                text = line.strip()
                if text.startswith('{') and text.endswith('}'):
                    try:
                        summary = json.loads(text)
                    except Exception:
                        continue
            if not summary:
                # 兼容旧版本命令：无法解析JSON时，回退为原始输出
                return JsonResponse({'success': True, 'message': '导入任务已提交', 'stats': {}, 'raw': cleaned_output})

            # 规范化统计字段，满足前端展示需要
            s = summary.get('stats', {})
            stats = {
                'total_rows': int(s.get('total_rows', 0)),
                'valid_rows': int(s.get('success_rows', 0)),
                'empty_rows': int(s.get('empty_rows', 0)) if isinstance(s.get('empty_rows', 0), (int, float)) else 0,
                'template_rows': int(s.get('template_rows', 0)) if isinstance(s.get('template_rows', 0), (int, float)) else 0,
                'success_rows': int(s.get('success_rows', 0)),
                'created': int(s.get('created', 0)),
                'updated': int(s.get('updated', 0)),
                'skipped': int(s.get('skipped', 0)),
                'error_rows': int(s.get('error_rows', 0)),
                'actual_imported': int(s.get('created', 0)) + int(s.get('updated', 0)),
            }

            errors = summary.get('errors', []) or []
            has_more_errors = bool(summary.get('has_more_errors'))

            # 友好提示
            if stats['error_rows'] > 0:
                message_type = 'warning'
                message = (
                    f"导入完成：新增 {stats['created']}，更新 {stats['updated']}，"
                    f"跳过 {stats['skipped']}，失败 {stats['error_rows']}。"
                )
            else:
                message_type = 'success'
                message = (
                    f"导入完成：新增 {stats['created']}，更新 {stats['updated']}，"
                    f"跳过 {stats['skipped']}。"
                )

            return JsonResponse({
                'success': True,
                'message': message,
                'message_type': message_type,
                'stats': stats,
                'errors': errors,
                'has_more_errors': has_more_errors,
                'raw': cleaned_output,
            })
        finally:
            try:
                os.unlink(tmp_file_path)
            except Exception:
                pass
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'导入失败: {str(e)}'}, status=400)


@login_required
@require_POST
def batch_delete_contracts(request):
    from django.db.models import ProtectedError
    try:
        data = json.loads(request.body)
        contract_codes = data.get('ids', [])
        if not contract_codes:
            return JsonResponse({'success': False, 'message': '未选择要删除的合同'})
        try:
            qs = Contract.objects.filter(contract_code__in=contract_codes)
            targets = list(qs)
            deleted_count = qs.delete()[0]

            # 为非超级用户记录删除操作日志(日志写入失败不影响主流程)
            if deleted_count and request.user.is_authenticated and not request.user.is_superuser:
                try:
                    ip = get_client_ip(request)
                    logs = [
                        OperationLog(
                            user=request.user,
                            operation_type="delete",
                            object_type="contract",
                            object_id=obj.contract_code,
                            object_repr=str(obj),
                            description=f"用户 {request.user.username} 删除了合同: {obj}",
                            ip_address=ip,
                            changes=None,
                        )
                        for obj in targets
                    ]
                    OperationLog.objects.bulk_create(logs)
                except Exception:
                    pass

            return JsonResponse({'success': True, 'message': f'成功删除 {deleted_count} 条合同', 'deleted_count': deleted_count})
        except ProtectedError:
            return JsonResponse({
                'success': False,
                'message': '无法删除该合同，因为已有付款记录关联到此合同。\n\n建议操作：\n1. 先删除关联的付款记录\n2. 然后再删除该合同\n\n如需帮助，请联系系统管理员。'
            })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败: {str(e)}'})


@login_required
@require_POST
def batch_delete_payments(request):
    from django.db.models import ProtectedError
    try:
        data = json.loads(request.body)
        payment_codes = data.get('ids', [])
        if not payment_codes:
            return JsonResponse({'success': False, 'message': '未选择要删除的付款记录'})
        try:
            qs = Payment.objects.filter(payment_code__in=payment_codes)
            targets = list(qs)
            deleted_count = qs.delete()[0]

            # 为非超级用户记录删除操作日志(日志写入失败不影响主流程)
            if deleted_count and request.user.is_authenticated and not request.user.is_superuser:
                try:
                    ip = get_client_ip(request)
                    logs = [
                        OperationLog(
                            user=request.user,
                            operation_type="delete",
                            object_type="payment",
                            object_id=obj.payment_code,
                            object_repr=str(obj),
                            description=f"用户 {request.user.username} 删除了付款记录: {obj}",
                            ip_address=ip,
                            changes=None,
                        )
                        for obj in targets
                    ]
                    OperationLog.objects.bulk_create(logs)
                except Exception:
                    pass

            return JsonResponse({'success': True, 'message': f'成功删除 {deleted_count} 条付款记录', 'deleted_count': deleted_count})
        except ProtectedError:
            return JsonResponse({
                'success': False,
                'message': '无法删除该付款记录，因为存在关联的数据引用。\n\n建议操作：\n1. 检查是否有其他记录依赖此付款\n2. 先处理关联数据后再删除\n\n如需帮助，请联系系统管理员。'
            })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败: {str(e)}'})


@login_required
@require_POST
def batch_delete_procurements(request):
    from django.db.models import ProtectedError
    try:
        data = json.loads(request.body)
        procurement_codes = data.get('ids', [])
        if not procurement_codes:
            return JsonResponse({'success': False, 'message': '未选择要删除的采购项目'})
        try:
            qs = Procurement.objects.filter(procurement_code__in=procurement_codes)
            targets = list(qs)
            deleted_count = qs.delete()[0]

            # 为非超级用户记录删除操作日志(日志写入失败不影响主流程)
            if deleted_count and request.user.is_authenticated and not request.user.is_superuser:
                try:
                    ip = get_client_ip(request)
                    logs = [
                        OperationLog(
                            user=request.user,
                            operation_type="delete",
                            object_type="procurement",
                            object_id=obj.procurement_code,
                            object_repr=str(obj),
                            description=f"用户 {request.user.username} 删除了采购项目: {obj}",
                            ip_address=ip,
                            changes=None,
                        )
                        for obj in targets
                    ]
                    OperationLog.objects.bulk_create(logs)
                except Exception:
                    pass

            return JsonResponse({'success': True, 'message': f'成功删除 {deleted_count} 个采购项目', 'deleted_count': deleted_count})
        except ProtectedError:
            return JsonResponse({
                'success': False,
                'message': '无法删除该采购项目，因为已有合同关联到此采购。\n\n建议操作：\n1. 先删除关联的合同记录\n2. 然后再删除该采购项目\n\n如需帮助，请联系系统管理员。'
            })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败: {str(e)}'})


@login_required
@require_POST
def batch_delete_projects(request):
    from django.db.models import ProtectedError
    try:
        data = json.loads(request.body)
        project_codes = data.get('ids', [])
        if not project_codes:
            return JsonResponse({'success': False, 'message': '未选择要删除的项目'})
        try:
            qs = Project.objects.filter(project_code__in=project_codes)
            targets = list(qs)
            deleted_count = qs.delete()[0]

            # 为非超级用户记录删除操作日志(日志写入失败不影响主流程)
            if deleted_count and request.user.is_authenticated and not request.user.is_superuser:
                try:
                    ip = get_client_ip(request)
                    logs = [
                        OperationLog(
                            user=request.user,
                            operation_type="delete",
                            object_type="project",
                            object_id=obj.project_code,
                            object_repr=str(obj),
                            description=f"用户 {request.user.username} 删除了项目: {obj}",
                            ip_address=ip,
                            changes=None,
                        )
                        for obj in targets
                    ]
                    OperationLog.objects.bulk_create(logs)
                except Exception:
                    pass

            return JsonResponse({'success': True, 'message': f'成功删除 {deleted_count} 个项目', 'deleted_count': deleted_count})
        except ProtectedError:
            return JsonResponse({
                'success': False,
                'message': '无法删除该项目，因为已有采购或合同关联到此项目。\n\n建议操作：\n1. 先删除项目下的所有采购和合同\n2. 然后再删除该项目\n\n如需帮助，请联系系统管理员。'
            })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败: {str(e)}'})


@login_required
@require_http_methods(['GET', 'POST'])
def export_project_data(request):
    """导出项目数据为Excel或ZIP。"""
    if request.method == 'GET':
        global_filters = _resolve_global_filters(request)
        projects = Project.objects.all()

        # 按全局项目筛选（支持多选 global_project）
        project_codes = global_filters.get('project_list') or []
        if project_codes:
            projects = projects.filter(project_code__in=project_codes)

        # 全局年度仅用于默认业务时间范围，不再直接过滤项目列表，
        # 避免因为项目创建时间与业务发生时间不一致导致导出混乱。
        year_filter = global_filters.get('year_filter')
        business_start_date = ''
        business_end_date = ''
        if year_filter is not None:
            business_start_date = f"{year_filter}-01-01"
            business_end_date = f"{year_filter}-12-31"

        projects = projects.order_by('project_name')
        context = {
            'projects': projects,
            'page_title': '导出项目数据',
            'business_start_date': business_start_date,
            'business_end_date': business_end_date,
        }
        return render(request, 'export_project_selection.html', context)

    try:
        project_codes = request.POST.getlist('project_codes')
        if not project_codes:
            return JsonResponse({'success': False, 'message': '请至少选择一个项目'}, status=400)
        projects = Project.objects.filter(project_code__in=project_codes)
        if not projects.exists():
            return JsonResponse({'success': False, 'message': '未找到选中的项目'}, status=404)

        # 解析业务发生时间筛选区间（前端为 YYYY-MM-DD 格式的日期输入）
        business_start_date_str = request.POST.get('business_start_date') or ''
        business_end_date_str = request.POST.get('business_end_date') or ''
        business_start_date: date | None = None
        business_end_date: date | None = None

        try:
            if business_start_date_str:
                business_start_date = date.fromisoformat(business_start_date_str)
            if business_end_date_str:
                business_end_date = date.fromisoformat(business_end_date_str)
        except ValueError:
            return JsonResponse(
                {
                    'success': False,
                    'message': '业务发生时间格式不正确，请使用有效的日期（例如：2025-01-01）。',
                },
                status=400,
            )

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if len(projects) == 1:
            # 单项目导出为xlsx
            project = projects.first()
            if project is None:
                return JsonResponse({'success': False, 'message': '项目不存在'}, status=404)
            excel_file = generate_project_excel(
                project,
                request.user,
                business_start_date=business_start_date,
                business_end_date=business_end_date,
            )

            # 生成清晰的中文文件名，但限制长度避免问题
            project_name_clean = project.project_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            # 如果项目名太长，使用缩写
            if len(project_name_clean) > 30:
                project_name_clean = project_name_clean[:27] + "..."

            filename_utf8 = f"{project_name_clean}_{timestamp}.xlsx"
            filename_ascii = f"project_{timestamp}.xlsx"  # ASCII回退名称

            response = HttpResponse(
                excel_file.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )

            # 使用双文件名策略：ASCII回退 + UTF-8中文名
            # 现代浏览器会优先使用filename*参数并自动解码显示中文
            encoded_filename = quote(filename_utf8.encode('utf-8'))
            response['Content-Disposition'] = (
                f'attachment; '
                f'filename="{filename_ascii}"; '
                f"filename*=UTF-8''{encoded_filename}"
            )
            return response

        # 多项目导出为zip
        # 当项目数量较大时，改为异步导出，避免长时间阻塞请求
        if len(projects) > 50:
            generate_project_export_zip_async.delay(
                list(projects.values_list('project_code', flat=True)),
                request.user.id,
                False,
                business_start_date,
                business_end_date,
            )
            return JsonResponse(
                {
                    'success': True,
                    'message': '导出任务已提交到后台队列，完成后将通过邮件通知您。',
                }
            )

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for project in projects:
                excel_file = generate_project_excel(
                    project,
                    request.user,
                    business_start_date=business_start_date,
                    business_end_date=business_end_date,
                )
                # ZIP内部的文件名使用中文（ZIP格式本身支持UTF-8）
                filename = f"{project.project_name}_{timestamp}.xlsx"
                zip_file.writestr(filename, excel_file.getvalue())

        zip_buffer.seek(0)

        # ZIP文件名也使用双文件名策略
        zip_filename_utf8 = f"项目数据导出_{timestamp}.zip"
        zip_filename_ascii = f"projects_export_{timestamp}.zip"

        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        # 使用双文件名策略：ASCII回退 + UTF-8中文名
        encoded_zip_filename = quote(zip_filename_utf8.encode('utf-8'))
        response['Content-Disposition'] = (
            f'attachment; '
            f'filename="{zip_filename_ascii}"; '
            f"filename*=UTF-8''{encoded_zip_filename}"
        )
        return response
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'导出失败: {str(e)}'}, status=500)


@login_required
@csrf_protect
@require_POST
def import_project_data(request):
    """导入项目数据（从导出的Excel文件）"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'message': '未找到上传文件'}, status=400)
        
        uploaded_file = request.FILES['file']
        project_code = request.POST.get('project_code', '').strip()
        
        if not project_code:
            return JsonResponse({'success': False, 'message': '请指定项目编码'}, status=400)
        
        # 验证文件格式
        if not (uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls')):
            return JsonResponse({'success': False, 'message': '仅支持Excel文件格式(.xlsx或.xls)'}, status=400)
        
        # 验证项目是否存在
        try:
            project = Project.objects.get(project_code=project_code)
        except Project.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'项目不存在：{project_code}'}, status=404)
        
        # 读取文件到内存
        file_content = BytesIO(uploaded_file.read())
        
        # ִ�е���
        try:
            stats = import_project_excel(file_content, project_code, request.user)
        except ProjectDataImportError as exc:
            message = _format_import_failure(exc.stats)
            return JsonResponse({
                'success': False,
                'message': message,
                'stats': exc.stats
            }, status=400)
        
        success_message = "����ɹ���\n" + _format_import_summary(stats)
        return JsonResponse({
            'success': True,
            'message': success_message,
            'stats': stats
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'导入失败: {str(e)}'}, status=500)
