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
            # 使用新的Word报表生成器
            try:
                from project.services.reports import WordReportGenerator
                
                # 计算日期范围
                if report_type == 'weekly':
                    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else date.today()
                    days_since_monday = target_date.weekday()
                    start_date = target_date - timedelta(days=days_since_monday)
                    end_date = start_date + timedelta(days=6)
                elif report_type == 'monthly':
                    start_date = date(year, month, 1)
                    if month == 12:
                        end_date = date(year, 12, 31)
                    else:
                        end_date = date(year, month + 1, 1) - timedelta(days=1)
                elif report_type == 'quarterly':
                    start_month = (quarter - 1) * 3 + 1
                    start_date = date(year, start_month, 1)
                    end_month = start_month + 2
                    if end_month == 12:
                        end_date = date(year, 12, 31)
                    else:
                        end_date = date(year, end_month + 1, 1) - timedelta(days=1)
                else:  # annual
                    start_date = date(year, 1, 1)
                    end_date = date(year, 12, 31)
                
                # 创建报表生成器
                generator = WordReportGenerator(
                    start_date=start_date,
                    end_date=end_date,
                    project_codes=project_codes
                )
                
                # 生成临时文件
                tmp_fd, tmp_path = tempfile.mkstemp(suffix='.docx')
                os.close(tmp_fd)
                
                try:
                    # 生成报表
                    if report_type == 'weekly':
                        generator.generate_weekly_report(tmp_path)
                    else:
                        generator.generate_monthly_report(tmp_path)
                    
                    # 读取并返回
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
                finally:
                    if os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass
            except Exception as e:
                messages.error(request, f'生成Word文档失败: {str(e)}')
                import traceback
                print(traceback.format_exc())
                return redirect('generate_report')
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

        # 使用新的Word报表生成器
        from project.services.reports import WordReportGenerator
        
        # 计算日期范围
        if report_type == 'weekly':
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else date.today()
            days_since_monday = target_date.weekday()
            start_date = target_date - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=6)
        elif report_type == 'monthly':
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year, 12, 31)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
        elif report_type == 'quarterly':
            start_month = (quarter - 1) * 3 + 1
            start_date = date(year, start_month, 1)
            end_month = start_month + 2
            if end_month == 12:
                end_date = date(year, 12, 31)
            else:
                end_date = date(year, end_month + 1, 1) - timedelta(days=1)
        else:  # annual
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
        
        # 创建报表生成器
        word_generator = WordReportGenerator(
            start_date=start_date,
            end_date=end_date,
            project_codes=project_codes
        )
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        try:
            # 生成报表
            if report_type == 'weekly':
                word_generator.generate_weekly_report(tmp_path)
                report_title = f'{year}年第{target_date.isocalendar()[1]}周专业报告'
            elif report_type == 'monthly':
                word_generator.generate_monthly_report(tmp_path)
                report_title = f'{year}年{month}月专业报告'
            elif report_type == 'quarterly':
                word_generator.generate_monthly_report(tmp_path)  # 季报使用月报格式
                report_title = f'{year}年第{quarter}季度专业报告'
            else:
                word_generator.generate_monthly_report(tmp_path)  # 年报使用月报格式
                report_title = f'{year}年度专业报告'
            
            with open(tmp_path, 'rb') as f:
                word_content = f.read()
            filename = f"{report_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            response = HttpResponse(
                word_content,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            )
            from urllib.parse import quote
            encoded_filename = quote(filename.encode('utf-8'))
            response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
            return response
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        messages.error(request, f'生成报告失败: {str(e)}')


@require_http_methods(['GET', 'POST'])
def generate_word_report(request):
    """生成Word监控报表（新版本）"""
    from datetime import date, timedelta
    from project.services.reports import WordReportGenerator
    from project.constants import get_current_year, get_year_range
    
    if request.method == 'GET':
        # 显示表单
        current_year = get_current_year()
        current_month = datetime.now().month
        
        context = {
            'page_title': 'Word监控报表生成',
            'current_year': current_year,
            'current_month': current_month,
            'available_years': get_year_range(include_future=True),
            'available_months': list(range(1, 13)),
            'projects': Project.objects.all().order_by('project_name'),
            'today': date.today().isoformat()
        }
        return render(request, 'reports/word_report_form.html', context)
    
    # POST: 生成报表
    try:
        report_type = request.POST.get('report_type', 'monthly')
        project_codes = request.POST.getlist('projects')
        # 过滤空值
        project_codes = [p for p in project_codes if p] or None
        
        # 计算日期范围
        if report_type == 'weekly':
            # 周报：基于目标日期计算所在周的起止日期
            target_date_str = request.POST.get('target_date')
            if target_date_str:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            else:
                target_date = date.today()
            
            # 计算周一和周日
            days_since_monday = target_date.weekday()
            start_date = target_date - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=6)
        else:  # monthly
            # 月报
            year = int(request.POST.get('year', get_current_year()))
            month = int(request.POST.get('month', datetime.now().month))
            
            start_date = date(year, month, 1)
            # 计算月末日期
            if month == 12:
                end_date = date(year, 12, 31)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # 创建报表生成器
        generator = WordReportGenerator(
            start_date=start_date,
            end_date=end_date,
            project_codes=project_codes
        )
        
        # 生成临时文件
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # 生成报表
            if report_type == 'weekly':
                generator.generate_weekly_report(tmp_path)
                report_name = f'监控周报_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}'
            else:
                generator.generate_monthly_report(tmp_path)
                report_name = f'监控月报_{start_date.year}年{start_date.month}月'
            
            # 读取并返回文件
            with open(tmp_path, 'rb') as f:
                content = f.read()
            
            filename = f'{report_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx'
            response = HttpResponse(
                content,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            # 使用URL编码确保中文文件名正确显示
            from urllib.parse import quote
            encoded_filename = quote(filename.encode('utf-8'))
            response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
            return response
            
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
    
    except Exception as e:
        messages.error(request, f'生成报表失败: {str(e)}')
        import traceback
        print(traceback.format_exc())  # 记录详细错误信息
        return redirect('generate_word_report')
        return redirect('generate_professional_report')
