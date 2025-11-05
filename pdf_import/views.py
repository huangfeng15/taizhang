"""
PDF导入视图函数
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
import uuid
import os
from pathlib import Path

from .models import PDFImportSession
from procurement.models import Procurement
from .utils.pdf_filter import PDFFileFilter


@login_required
def upload_pdf(request):
    """
    步骤1: PDF文件上传页面
    支持文件夹选择或多文件上传
    """
    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('pdf_files')
        
        if not uploaded_files:
            messages.error(request, '请选择PDF文件或文件夹')
            return render(request, 'pdf_import/upload.html')
        
        # 创建会话
        session_id = str(uuid.uuid4())
        session = PDFImportSession.objects.create(
            session_id=session_id,
            created_by=request.user,
            status=PDFImportSession.STATUS_EXTRACTING
        )
        
        # 保存上传的文件
        upload_dir = Path(settings.MEDIA_ROOT) / 'pdf_uploads' / session_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 第一阶段：保存所有PDF文件
        all_pdf_files = []
        for pdf_file in uploaded_files:
            # 只处理PDF文件
            if not pdf_file.name.lower().endswith('.pdf'):
                continue
            
            file_path = upload_dir / pdf_file.name
            with open(file_path, 'wb+') as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)
            
            all_pdf_files.append({
                'name': pdf_file.name,
                'path': str(file_path),
                'size': pdf_file.size
            })
        
        if not all_pdf_files:
            messages.error(request, '未找到有效的PDF文件')
            session.delete()
            return render(request, 'pdf_import/upload.html')
        
        # 第二阶段：智能过滤 - 仅保留包含特定编号的PDF文件
        allowed_files, filtered_files = PDFFileFilter.filter_pdf_files(all_pdf_files)
        
        # 显示过滤结果
        total_count = len(all_pdf_files)
        allowed_count = len(allowed_files)
        filtered_count = len(filtered_files)
        
        # 生成过滤摘要
        filter_summary = PDFFileFilter.get_filter_summary(
            total_count,
            allowed_count,
            filtered_count
        )
        
        # 如果没有符合条件的文件
        if not allowed_files:
            messages.warning(
                request,
                f'❌ 未找到符合条件的PDF文件！\n\n'
                f'{filter_summary}\n\n'
                f'💡 系统仅处理包含以下编号的PDF文件：\n'
                f'{PDFFileFilter.get_allowed_numbers_display()}'
            )
            session.delete()
            # 删除已上传的文件
            import shutil
            if upload_dir.exists():
                shutil.rmtree(upload_dir)
            return render(request, 'pdf_import/upload.html')
        
        # 如果有文件被过滤，显示信息提示
        if filtered_count > 0:
            filtered_names = [f['name'] for f in filtered_files[:5]]  # 最多显示5个
            more_text = f' 等 {filtered_count} 个文件' if filtered_count > 5 else ''
            messages.info(
                request,
                f'ℹ️ 已自动过滤 {filtered_count} 个不符合条件的文件：\n'
                f'{", ".join(filtered_names)}{more_text}\n\n'
                f'✅ 将处理 {allowed_count} 个符合条件的文件'
            )
        else:
            messages.success(
                request,
                f'✅ 所有 {allowed_count} 个文件均符合处理条件！'
            )
        
        # 保存允许处理的文件列表到会话
        session.pdf_files = allowed_files
        session.save()
        
        # 重定向到提取页面
        return redirect('pdf_import:extract', session_id=session_id)
    
    return render(request, 'pdf_import/upload.html')


@login_required
def extract_data(request, session_id):
    """
    步骤2: 数据提取处理
    调用PDF识别和字段提取模块
    """
    session = get_object_or_404(PDFImportSession, session_id=session_id)
    
    if session.status != PDFImportSession.STATUS_EXTRACTING:
        return redirect('pdf_import:preview', session_id=session_id)
    
    try:
        from .core.pdf_detector import PDFDetector
        from .core.field_extractor import FieldExtractor
        
        detector = PDFDetector()
        extractor = FieldExtractor()
        
        # 1. 识别PDF类型
        pdf_files_by_type = {}
        for pdf_info in session.pdf_files:
            pdf_path = pdf_info['path']
            
            # 检测PDF类型
            pdf_type, confidence, method = detector.detect(pdf_path)
            
            # 更新PDF信息
            pdf_info['detected_type'] = pdf_type
            pdf_info['confidence'] = confidence
            pdf_info['method'] = method
            
            # 按类型分组
            if pdf_type != 'unknown':
                pdf_files_by_type[pdf_type] = pdf_path
        
        # 2. 提取字段（从所有PDF合并）
        extracted_data = extractor.extract_all_from_pdfs(pdf_files_by_type)
        
        # 3. 标记需要确认的字段
        requires_confirmation = []
        for field_name, value in extracted_data.items():
            # 这里可以添加更复杂的逻辑来判断哪些字段需要确认
            # 例如：枚举值映射、低置信度字段等
            pass
        
        # 4. 更新会话
        session.extracted_data = extracted_data
        session.requires_confirmation = requires_confirmation
        session.status = PDFImportSession.STATUS_PENDING_REVIEW
        session.save()
        
        # 显示提取成功消息
        extracted_count = len([v for v in extracted_data.values() if v])
        messages.success(request, f'成功提取 {extracted_count} 个字段！')
        
        return redirect('pdf_import:preview', session_id=session_id)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"数据提取错误: {error_detail}")
        messages.error(request, f'数据提取失败: {str(e)}')
        session.status = PDFImportSession.STATUS_EXPIRED
        session.save()
        return redirect('pdf_import:upload')


@login_required
def preview_data(request, session_id):
    """
    步骤3: 数据预览和编辑
    """
    from .forms import ProcurementConfirmForm
    
    session = get_object_or_404(PDFImportSession, session_id=session_id)
    
    if session.status not in [PDFImportSession.STATUS_PENDING_REVIEW, PDFImportSession.STATUS_CONFIRMED]:
        return redirect('pdf_import:upload')
    
    if request.method == 'POST':
        # 处理表单提交
        form = ProcurementConfirmForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 保存采购信息
                    procurement = form.save(commit=False)
                    # 添加创建人信息
                    procurement.created_by = request.user.username if hasattr(request.user, 'username') else 'system'
                    procurement.save()
                    
                    # 更新会话状态
                    session.procurement = procurement
                    session.status = PDFImportSession.STATUS_SAVED
                    session.save()
                    
                    messages.success(
                        request,
                        f'✅ 成功导入采购信息！招采编号：{procurement.procurement_code}'
                    )
                    return redirect('pdf_import:success', session_id=session_id)
                    
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"保存数据错误: {error_detail}")
                messages.error(request, f'❌ 保存失败: {str(e)}')
        else:
            # 表单验证失败 - 显示详细错误
            error_count = len(form.errors)
            messages.error(
                request,
                f'❌ 表单验证失败，发现 {error_count} 个错误，请查看下方详细信息并修正'
            )
    else:
        # GET请求：显示提取的数据
        # 预处理金额字段，移除逗号
        initial_data = session.extracted_data.copy() if session.extracted_data else {}
        
        # 处理金额字段
        amount_fields = ['budget_amount', 'control_price', 'winning_amount']
        for field in amount_fields:
            if field in initial_data and initial_data[field]:
                # 移除逗号，保留数字和小数点
                import re
                cleaned = re.sub(r'[￥¥元,]', '', str(initial_data[field]))
                initial_data[field] = cleaned.strip()
        
        form = ProcurementConfirmForm(initial=initial_data)
    
    context = {
        'session': session,
        'form': form,
        'pdf_files': session.pdf_files,
        'extracted_data': session.extracted_data,
        'requires_confirmation': session.requires_confirmation,
    }
    
    return render(request, 'pdf_import/preview.html', context)


@login_required
def save_success(request, session_id):
    """
    步骤4: 保存成功页面
    """
    session = get_object_or_404(PDFImportSession, session_id=session_id)
    
    context = {
        'session': session,
        'procurement': session.procurement,
    }
    
    return render(request, 'pdf_import/success.html', context)


@login_required
def list_drafts(request):
    """
    列出用户的草稿会话
    """
    drafts = PDFImportSession.objects.filter(
        created_by=request.user,
        status__in=[
            PDFImportSession.STATUS_PENDING_REVIEW,
            PDFImportSession.STATUS_CONFIRMED
        ]
    ).order_by('-updated_at')
    
    context = {
        'drafts': drafts,
    }
    
    return render(request, 'pdf_import/drafts.html', context)


@login_required
def resume_draft(request, session_id):
    """
    恢复草稿继续编辑
    """
    session = get_object_or_404(
        PDFImportSession,
        session_id=session_id,
        created_by=request.user
    )
    
    # 延长过期时间
    session.extend_expiry(hours=72)
    
    return redirect('pdf_import:preview', session_id=session_id)


@login_required
def delete_draft(request, session_id):
    """
    删除草稿
    """
    session = get_object_or_404(
        PDFImportSession,
        session_id=session_id,
        created_by=request.user
    )
    
    session.delete()
    messages.success(request, '草稿已删除')
    
    return redirect('pdf_import:drafts')