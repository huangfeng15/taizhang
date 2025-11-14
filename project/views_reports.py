from datetime import datetime, date
import os
import tempfile

from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from project.constants import get_current_year, get_year_range
from project.views_helpers import _resolve_global_filters
from .models import Project


def generate_report(request):
    """报表生成页面：周报、月报、季报、年报。"""
    from project.services.report_generator import (
        WeeklyReportGenerator,
        MonthlyReportGenerator,
        QuarterlyReportGenerator,
        AnnualReportGenerator,
        export_to_excel,
    )

    if request.method == 'GET':
        current_year = get_current_year()
        current_month = datetime.now().month
        current_quarter = (current_month - 1) // 3 + 1

        global_filters = _resolve_global_filters(request)
        all_projects = Project.objects.all().order_by('project_name')

        context = {
            'page_title': '报表生成',
            'current_year': current_year,
            'current_month': current_month,
            'current_quarter': current_quarter,
            'available_years': get_year_range(include_future=True),
            'available_months': list(range(1, 13)),
            'available_quarters': [1, 2, 3, 4],
            'selected_projects': all_projects,
            'global_selected_year': global_filters['year_value'],
            'global_selected_project': global_filters['project'],
        }
        return render(request, 'reports/form.html', context)

    try:
        report_type = request.POST.get('report_type', 'monthly')
        export_format = request.POST.get('export_format', 'preview')

        project_param = request.POST.get('project', '').strip()
        project_code_param = request.POST.get('project_code', '').strip()

        if report_type == 'project':
            project_codes = [project_code_param] if project_code_param else None
        else:
            project_codes = [project_param] if project_param else None

        year = int(request.POST.get('year', get_current_year()))
        month = int(request.POST.get('month', datetime.now().month))
        quarter = int(request.POST.get('quarter', 1))

        if report_type == 'project':
            generator = AnnualReportGenerator(year, project_codes=project_codes)
        elif report_type == 'weekly':
            target_date_str = request.POST.get('target_date')
            target_date = (
                datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else date.today()
            )
            generator = WeeklyReportGenerator(target_date, project_codes=project_codes)
        elif report_type == 'monthly':
            generator = MonthlyReportGenerator(year, month, project_codes=project_codes)
        elif report_type == 'quarterly':
            generator = QuarterlyReportGenerator(year, quarter, project_codes=project_codes)
        elif report_type == 'annual':
            generator = AnnualReportGenerator(year, project_codes=project_codes)
        else:
            return JsonResponse({'success': False, 'message': '不支持的报表类型'}, status=400)

        report_data = generator.generate_data()

        if export_format == 'word':
            try:
                from project.services.report_generator import export_to_word
            except ImportError:
                messages.error(request, 'Word导出不可用，请安装 python-docx')
                return redirect('generate_report')

            tmp_fd, tmp_path = tempfile.mkstemp(suffix='.docx')
            os.close(tmp_fd)
            try:
                export_to_word(report_data, tmp_path)
                if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                    raise Exception('Word文件生成失败')
                with open(tmp_path, 'rb') as f:
                    word_content = f.read()
                safe_title = report_data.get('title', '工作报告').replace('/', '-').replace('\\', '-')
                filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                response = HttpResponse(
                    word_content,
                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                )
                from urllib.parse import quote
                encoded = quote(filename.encode('utf-8'))
                response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'{encoded}'
                return response
            except Exception as e:
                messages.error(request, f'生成Word文档失败: {str(e)}')
                return redirect('generate_report')
            finally:
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except Exception:
                    pass
        elif export_format == 'excel':
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            try:
                export_to_excel(report_data, tmp_path)
                with open(tmp_path, 'rb') as f:
                    excel_content = f.read()
                filename = f"{report_data['title']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                response = HttpResponse(
                    excel_content,
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        else:
            context = {'page_title': '报表预览', 'report_data': report_data, 'report_type': report_type}
            return render(request, 'reports/preview.html', context)
    except Exception as e:
        messages.error(request, f'生成报表失败: {str(e)}')
        return redirect('generate_report')


def report_preview(request):
    """报表预览（GET）。"""
    from project.services.report_generator import (
        WeeklyReportGenerator,
        MonthlyReportGenerator,
        QuarterlyReportGenerator,
        AnnualReportGenerator,
    )
    try:
        report_type = request.GET.get('report_type', 'monthly')
        year = int(request.GET.get('year', get_current_year()))
        month = int(request.GET.get('month', datetime.now().month))
        quarter = int(request.GET.get('quarter', 1))
        project_param = request.GET.get('project', '').strip()
        project_codes = [project_param] if project_param else None

        if report_type == 'weekly':
            target_date_str = request.GET.get('target_date')
            target_date = (
                datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else date.today()
            )
            generator = WeeklyReportGenerator(target_date, project_codes=project_codes)
        elif report_type == 'monthly':
            generator = MonthlyReportGenerator(year, month, project_codes=project_codes)
        elif report_type == 'quarterly':
            generator = QuarterlyReportGenerator(year, quarter, project_codes=project_codes)
        elif report_type == 'annual':
            generator = AnnualReportGenerator(year, project_codes=project_codes)
        else:
            messages.error(request, '不支持的报表类型')
            return redirect('generate_report')

        report_data = generator.generate_data()
        context = {'page_title': '报表预览', 'report_data': report_data, 'report_type': report_type}
        return render(request, 'reports/preview.html', context)
    except Exception as e:
        messages.error(request, f'生成报表失败: {str(e)}')
        return redirect('generate_report')


def report_export(request):
    """报表导出（GET 导出 Excel）。"""
    from project.services.report_generator import (
        WeeklyReportGenerator,
        MonthlyReportGenerator,
        QuarterlyReportGenerator,
        AnnualReportGenerator,
        export_to_excel,
    )
    try:
        report_type = request.GET.get('report_type', 'monthly')
        year = int(request.GET.get('year', get_current_year()))
        month = int(request.GET.get('month', datetime.now().month))
        quarter = int(request.GET.get('quarter', 1))
        project_param = request.GET.get('project', '').strip()
        project_codes = [project_param] if project_param else None

        if report_type == 'weekly':
            target_date_str = request.GET.get('target_date')
            target_date = (
                datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else date.today()
            )
            generator = WeeklyReportGenerator(target_date, project_codes=project_codes)
        elif report_type == 'monthly':
            generator = MonthlyReportGenerator(year, month, project_codes=project_codes)
        elif report_type == 'quarterly':
            generator = QuarterlyReportGenerator(year, quarter, project_codes=project_codes)
        elif report_type == 'annual':
            generator = AnnualReportGenerator(year, project_codes=project_codes)
        else:
            messages.error(request, '不支持的报表类型')
            return redirect('generate_report')

        report_data = generator.generate_data()

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        try:
            export_to_excel(report_data, tmp_path)
            with open(tmp_path, 'rb') as f:
                excel_content = f.read()
            filename = f"{report_data['title']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            response = HttpResponse(
                excel_content,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        messages.error(request, f'导出报表失败: {str(e)}')
        return redirect('generate_report')


@require_http_methods(['GET', 'POST'])
def generate_professional_report(request):
    """专业报告生成与导出（Word）。"""
    from project.services.report_generator import (
        WeeklyReportGenerator,
        MonthlyReportGenerator,
        QuarterlyReportGenerator,
        AnnualReportGenerator,
    )
    from project.services.export_service import (
        export_to_word_professional,
        export_to_word,
        export_to_excel,
    )
    if request.method == 'GET':
        current_year = get_current_year()
        current_month = datetime.now().month
        current_quarter = (current_month - 1) // 3 + 1
        global_filters = _resolve_global_filters(request)
        projects = Project.objects.all().order_by('project_name')

        context = {
            'page_title': '专业报告生成',
            'current_year': current_year,
            'current_month': current_month,
            'current_quarter': current_quarter,
            'available_years': get_year_range(include_future=True),
            'available_months': list(range(1, 13)),
            'available_quarters': [1, 2, 3, 4],
            'projects': projects,
            'selected_projects': global_filters['project_list'],
            'global_selected_year': global_filters['year_value'],
            'global_selected_project': global_filters['project'],
        }
        return render(request, 'reports/professional_form.html', context)

    try:
        project_codes = request.POST.getlist('projects')
        if not project_codes:
            project_param = request.POST.get('project', '').strip()
            project_codes = [project_param] if project_param else None
        else:
            project_codes = [p for p in project_codes if p] or None

        report_type = request.POST.get('report_type', 'monthly')
        year = int(request.POST.get('year', get_current_year()))
        month = int(request.POST.get('month', datetime.now().month))
        quarter = int(request.POST.get('quarter', 1))

        if report_type == 'weekly':
            target_date_str = request.POST.get('target_date')
            target_date = (
                datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else date.today()
            )
            generator = WeeklyReportGenerator(target_date, project_codes=project_codes)
        elif report_type == 'monthly':
            generator = MonthlyReportGenerator(year, month, project_codes=project_codes)
        elif report_type == 'quarterly':
            generator = QuarterlyReportGenerator(year, quarter, project_codes=project_codes)
        elif report_type == 'annual':
            generator = AnnualReportGenerator(year, project_codes=project_codes)
        else:
            return JsonResponse({'success': False, 'message': '不支持的报表类型'}, status=400)

        report_data = generator.generate_report_data()

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        try:
            export_to_word_professional(report_data, tmp_path)
            with open(tmp_path, 'rb') as f:
                word_content = f.read()
            meta = report_data.get('meta', {})
            report_title = meta.get('report_title', '工作报告')
            filename = f"{report_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            response = HttpResponse(
                word_content,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        messages.error(request, f'生成报告失败: {str(e)}')
        return redirect('generate_professional_report')
