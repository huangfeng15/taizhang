"""
报表生成服务
用于生成周报、月报、季报、年报
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Max, Min, Q
from django.utils import timezone
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement
from project.models import Project


class BaseReportGenerator:
    """报表生成基类"""
    
    def __init__(self, start_date, end_date, project_codes=None):
        """
        初始化报表生成器
        
        Args:
            start_date: 统计开始日期
            end_date: 统计结束日期
        """
        self.start_date = start_date
        self.end_date = end_date
        self.project_codes = project_codes
    
    def generate_data(self):
        """
        生成报表数据
        
        Returns:
            dict: 包含所有报表数据的字典
        """
        return {
            'period_start': self.start_date,
            'period_end': self.end_date,
            'generated_at': timezone.now(),
            'procurement_data': self._get_procurement_data(),
            'contract_data': self._get_contract_data(),
            'payment_data': self._get_payment_data(),
            'settlement_data': self._get_settlement_data(),
            'summary': self._get_summary()
        }
    
    def _get_procurement_data(self):
        """获取采购数据"""
        queryset = Procurement.objects.filter(
            result_publicity_release_date__gte=self.start_date,
            result_publicity_release_date__lte=self.end_date
        )
        if self.project_codes:
            queryset = queryset.filter(project__project_code__in=self.project_codes)
        
        total_count = queryset.count()
        total_budget = queryset.aggregate(Sum('budget_amount'))['budget_amount__sum'] or Decimal('0')
        total_winning = queryset.aggregate(Sum('winning_amount'))['winning_amount__sum'] or Decimal('0')
        
        # 按采购方式统计
        by_method = list(queryset.values('procurement_method').annotate(
            count=Count('procurement_code'),
            total_amount=Sum('winning_amount')
        ).order_by('-total_amount'))
        
        # 计算占比
        for item in by_method:
            item['count_ratio'] = (item['count'] / total_count * 100) if total_count > 0 else 0
            item['amount_ratio'] = (item['total_amount'] / total_winning * 100) if total_winning > 0 else 0
        
        return {
            'total_count': total_count,
            'total_budget': float(total_budget),
            'total_winning': float(total_winning),
            'by_method': by_method,
            'avg_winning': float(total_winning / total_count) if total_count > 0 else 0
        }
    
    def _get_contract_data(self):
        """获取合同数据"""
        queryset = Contract.objects.filter(
            signing_date__gte=self.start_date,
            signing_date__lte=self.end_date
        )
        if self.project_codes:
            queryset = queryset.filter(project__project_code__in=self.project_codes)
        
        total_count = queryset.count()
        total_amount = queryset.aggregate(Sum('contract_amount'))['contract_amount__sum'] or Decimal('0')
        
        # 按合同类型统计
        by_type = list(queryset.values('file_positioning').annotate(
            count=Count('contract_code'),
            total_amount=Sum('contract_amount')
        ).order_by('-count'))
        
        # 按合同来源统计
        by_source = list(queryset.values('contract_source').annotate(
            count=Count('contract_code'),
            total_amount=Sum('contract_amount')
        ).order_by('-total_amount'))
        
        return {
            'total_count': total_count,
            'total_amount': float(total_amount),
            'by_type': by_type,
            'by_source': by_source,
            'avg_amount': float(total_amount / total_count) if total_count > 0 else 0
        }
    
    def _get_payment_data(self):
        """获取付款数据"""
        queryset = Payment.objects.filter(
            payment_date__gte=self.start_date,
            payment_date__lte=self.end_date
        )
        if self.project_codes:
            queryset = queryset.filter(contract__project__project_code__in=self.project_codes)
        
        total_count = queryset.count()
        total_amount = queryset.aggregate(Sum('payment_amount'))['payment_amount__sum'] or Decimal('0')
        
        # TOP10项目
        top_projects = list(queryset.values(
            'contract__project__project_code',
            'contract__project__project_name'
        ).annotate(
            total_payment=Sum('payment_amount'),
            payment_count=Count('payment_code')
        ).order_by('-total_payment')[:10])
        
        return {
            'total_count': total_count,
            'total_amount': float(total_amount),
            'avg_amount': float(total_amount / total_count) if total_count > 0 else 0,
            'top_projects': top_projects
        }
    
    def _get_settlement_data(self):
        """获取结算数据"""
        queryset = Settlement.objects.filter(
            completion_date__gte=self.start_date,
            completion_date__lte=self.end_date
        )
        if self.project_codes:
            queryset = queryset.filter(main_contract__project__project_code__in=self.project_codes)
        
        settled_count = queryset.count()
        settled_amount = queryset.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0')
        
        return {
            'settled_count': settled_count,
            'settled_amount': float(settled_amount),
            'avg_settlement': float(settled_amount / settled_count) if settled_count > 0 else 0
        }
    
    def _get_summary(self):
        """生成汇总数据"""
        procurement = self._get_procurement_data()
        contract = self._get_contract_data()
        payment = self._get_payment_data()
        settlement = self._get_settlement_data()
        
        return {
            'total_procurement_count': procurement['total_count'],
            'total_contract_count': contract['total_count'],
            'total_payment_count': payment['total_count'],
            'total_settlement_count': settlement['settled_count'],
            'total_winning_amount': procurement['total_winning'],
            'total_contract_amount': contract['total_amount'],
            'total_payment_amount': payment['total_amount'],
            'total_settlement_amount': settlement['settled_amount']
        }


class WeeklyReportGenerator(BaseReportGenerator):
    """周报生成器"""
    
    def __init__(self, target_date=None, project_codes=None):
        """
        初始化周报生成器
        
        Args:
            target_date: 目标日期，默认为当前日期所在周
        """
        if target_date is None:
            target_date = date.today()
        
        # 计算本周的开始日期（周一）和结束日期（周日）
        weekday = target_date.weekday()
        start_date = target_date - timedelta(days=weekday)
        end_date = start_date + timedelta(days=6)
        
        super().__init__(start_date, end_date, project_codes=project_codes)
        self.week_number = target_date.isocalendar()[1]
        self.year = target_date.year
    
    def generate_data(self):
        """生成周报数据"""
        data = super().generate_data()
        data['report_type'] = 'weekly'
        data['week_number'] = self.week_number
        data['year'] = self.year
        data['title'] = f'{self.year}年第{self.week_number}周工作周报'
        return data


class MonthlyReportGenerator(BaseReportGenerator):
    """月报生成器"""
    
    def __init__(self, year=None, month=None, project_codes=None):
        """
        初始化月报生成器
        
        Args:
            year: 年份，默认为当前年份
            month: 月份，默认为当前月份
        """
        if year is None or month is None:
            today = date.today()
            year = year or today.year
            month = month or today.month
        
        # 计算本月的开始和结束日期
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year, 12, 31)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        super().__init__(start_date, end_date, project_codes=project_codes)
        self.year = year
        self.month = month
    
    def generate_data(self):
        """生成月报数据"""
        data = super().generate_data()
        data['report_type'] = 'monthly'
        data['year'] = self.year
        data['month'] = self.month
        data['title'] = f'{self.year}年{self.month}月工作月报'
        return data


class QuarterlyReportGenerator(BaseReportGenerator):
    """季报生成器"""
    
    def __init__(self, year=None, quarter=None, project_codes=None):
        """
        初始化季报生成器
        
        Args:
            year: 年份，默认为当前年份
            quarter: 季度(1-4)，默认为当前季度
        """
        if year is None or quarter is None:
            today = date.today()
            year = year or today.year
            quarter = quarter or ((today.month - 1) // 3 + 1)
        
        # 计算季度的开始和结束日期
        start_month = (quarter - 1) * 3 + 1
        start_date = date(year, start_month, 1)
        
        end_month = start_month + 2
        if end_month == 12:
            end_date = date(year, 12, 31)
        else:
            end_date = date(year, end_month + 1, 1) - timedelta(days=1)
        
        super().__init__(start_date, end_date, project_codes=project_codes)
        self.year = year
        self.quarter = quarter
    
    def generate_data(self):
        """生成季报数据"""
        data = super().generate_data()
        data['report_type'] = 'quarterly'
        data['year'] = self.year
        data['quarter'] = self.quarter
        data['title'] = f'{self.year}年第{self.quarter}季度工作报告'
        return data


class AnnualReportGenerator(BaseReportGenerator):
    """年报生成器"""
    
    def __init__(self, year=None, project_codes=None):
        """
        初始化年报生成器
        
        Args:
            year: 年份，默认为当前年份
        """
        if year is None:
            year = date.today().year
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        super().__init__(start_date, end_date, project_codes=project_codes)
        self.year = year
    
    def generate_data(self):
        """生成年报数据"""
        data = super().generate_data()
        data['report_type'] = 'annual'
        data['year'] = self.year
        data['title'] = f'{self.year}年度工作总结报告'
        
        # 年报增加月度趋势数据
        data['monthly_trend'] = self._get_monthly_trend()
        
        return data
    
    def _get_monthly_trend(self):
        """获取月度趋势数据"""
        trend = []
        for month in range(1, 13):
            start_date = date(self.year, month, 1)
            if month == 12:
                end_date = date(self.year, 12, 31)
            else:
                end_date = date(self.year, month + 1, 1) - timedelta(days=1)
            
            # 统计该月数据
            procurement_count = Procurement.objects.filter(
                result_publicity_release_date__gte=start_date,
                result_publicity_release_date__lte=end_date
            ).count()
            
            contract_count = Contract.objects.filter(
                signing_date__gte=start_date,
                signing_date__lte=end_date
            ).count()
            
            payment_amount = Payment.objects.filter(
                payment_date__gte=start_date,
                payment_date__lte=end_date
            ).aggregate(Sum('payment_amount'))['payment_amount__sum'] or Decimal('0')
            
            trend.append({
                'month': month,
                'procurement_count': procurement_count,
                'contract_count': contract_count,
                'payment_amount': float(payment_amount)
            })
        
        return trend


def export_to_excel(report_data, file_path):
    """
    导出报表为专业美化的Excel格式
    
    Args:
        report_data: 报表数据字典
        file_path: 导出文件路径
    
    Returns:
        str: 导出的文件路径
    """
    from openpyxl.styles import Border, Side
    
    wb = Workbook()
    ws = wb.active
    if ws:
        ws.title = "报表汇总"
    
    # 定义颜色和样式
    title_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    subheader_fill = PatternFill(start_color="D6DCE4", end_color="D6DCE4", fill_type="solid")
    data_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    highlight_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    
    white_font = Font(size=16, bold=True, color="FFFFFF")
    header_font = Font(size=12, bold=True, color="FFFFFF")
    subheader_font = Font(size=11, bold=True, color="000000")
    data_font = Font(size=10, color="000000")
    number_font = Font(size=10, bold=True, color="C00000")
    
    thin_border = Border(
        left=Side(style='thin', color='000000'),
        right=Side(style='thin', color='000000'),
        top=Side(style='thin', color='000000'),
        bottom=Side(style='thin', color='000000')
    )
    
    # 标题行
    ws.merge_cells('A1:F1')
    ws['A1'] = report_data.get('title', '工作报表')
    ws['A1'].font = white_font
    ws['A1'].fill = title_fill
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws['A1'].border = thin_border
    ws.row_dimensions[1].height = 30
    
    # 基本信息
    row = 3
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = '📅 报告信息'
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center', vertical='center')
    ws[f'A{row}'].border = thin_border
    
    ws.merge_cells(f'C{row}:F{row}')
    ws[f'C{row}'].border = thin_border
    ws.row_dimensions[row].height = 25
    
    row += 1
    ws[f'A{row}'] = '统计周期'
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'A{row}'].border = thin_border
    ws[f'A{row}'].alignment = Alignment(horizontal='left', vertical='center')
    
    ws.merge_cells(f'B{row}:F{row}')
    ws[f'B{row}'] = f"{report_data['period_start']} 至 {report_data['period_end']}"
    ws[f'B{row}'].font = data_font
    ws[f'B{row}'].border = thin_border
    ws[f'B{row}'].alignment = Alignment(horizontal='left', vertical='center')
    
    row += 1
    ws[f'A{row}'] = '生成时间'
    ws[f'A{row}'].font = subheader_font
    ws[f'A{row}'].fill = subheader_fill
    ws[f'A{row}'].border = thin_border
    ws[f'A{row}'].alignment = Alignment(horizontal='left', vertical='center')
    
    ws.merge_cells(f'B{row}:F{row}')
    ws[f'B{row}'] = report_data['generated_at'].strftime('%Y年%m月%d日 %H:%M:%S')
    ws[f'B{row}'].font = data_font
    ws[f'B{row}'].border = thin_border
    ws[f'B{row}'].alignment = Alignment(horizontal='left', vertical='center')
    
    row += 2
    
    # 数据汇总标题
    ws.merge_cells(f'A{row}:F{row}')
    ws[f'A{row}'] = '📊 数据汇总'
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].alignment = Alignment(horizontal='center', vertical='center')
    ws[f'A{row}'].border = thin_border
    ws.row_dimensions[row].height = 25
    
    row += 1
    
    # 表头
    headers = ['指标类别', '指标名称', '数值', '单位', '占比', '备注']
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col_idx)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border
    ws.row_dimensions[row].height = 22
    
    row += 1
    summary = report_data['summary']
    
    # 业务数量统计
    data_rows = [
        ('业务数量', '采购项目数', summary['total_procurement_count'], '个', '', '已完成采购项目总数'),
        ('业务数量', '合同签订数', summary['total_contract_count'], '份', '', '已签订合同总数'),
        ('业务数量', '付款笔数', summary['total_payment_count'], '笔', '', '已处理付款业务总数'),
        ('业务数量', '结算笔数', summary['total_settlement_count'], '笔', '', '已完成结算总数'),
        ('', '', '', '', '', ''),  # 空行
        ('资金统计', '中标金额', summary['total_winning_amount'], '元', '100%', '采购项目中标总金额'),
        ('资金统计', '合同金额', summary['total_contract_amount'], '元', '', '所有合同金额总和'),
        ('资金统计', '付款金额', summary['total_payment_amount'], '元', f"{(summary['total_payment_amount']/summary['total_contract_amount']*100):.1f}%" if summary['total_contract_amount'] > 0 else '0%', '累计付款总金额'),
        ('资金统计', '结算金额', summary['total_settlement_amount'], '元', '', '已结算项目金额总和'),
    ]
    
    for data_row in data_rows:
        if not data_row[0]:  # 空行
            row += 1
            continue
            
        for col_idx, value in enumerate(data_row, start=1):
            cell = ws.cell(row=row, column=col_idx)
            cell.value = value
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center' if col_idx in [1, 2, 4, 5] else 'right', vertical='center')
            
            if col_idx == 1:  # 类别列
                cell.font = subheader_font
                cell.fill = subheader_fill
            elif col_idx == 3 and isinstance(value, (int, float)):  # 数值列
                cell.font = number_font
                cell.number_format = '#,##0.00'
            else:
                cell.font = data_font
        
        ws.row_dimensions[row].height = 20
        row += 1
    
    # 调整列宽
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 8
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 25
    
    # 冻结首行
    ws.freeze_panes = 'A8'
    
    # 保存文件
    wb.save(file_path)
    return file_path



def export_to_word(report_data, file_path):
    """
    导出报表为专业Word文档格式
    
    Args:
        report_data: 报表数据字典
        file_path: 导出文件路径
    
    Returns:
        str: 导出的文件路径
    """
    
    doc = Document()
    
    # 设置文档默认字体为中文
    doc.styles['Normal'].font.name = '宋体'
    doc.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    doc.styles['Normal'].font.size = Pt(12)
    
    # 判断报告类型，以便在整个函数中使用
    report_type = report_data.get('report_type', 'monthly')
    is_project_report = report_type == 'project'
    
    # 标题
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title.add_run(report_data.get('title', '工作报表'))
    title_run.font.size = Pt(22)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0, 51, 102)
    title_run.font.name = '黑体'
    title_run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    
    # 添加空行
    doc.add_paragraph()
    
    # 基本信息
    info_para = doc.add_paragraph()
    info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info_run = info_para.add_run(
        f"统计周期：{report_data['period_start']} 至 {report_data['period_end']}\n"
        f"生成时间：{report_data['generated_at'].strftime('%Y年%m月%d日 %H:%M:%S')}"
    )
    info_run.font.size = Pt(11)
    info_run.font.color.rgb = RGBColor(102, 102, 102)
    
    doc.add_paragraph()
    
    # 一、工作概况
    summary_heading = doc.add_heading('一、工作概况', level=1)
    summary_heading.runs[0].font.size = Pt(16)
    summary_heading.runs[0].font.color.rgb = RGBColor(0, 51, 102)
    summary_heading.runs[0].font.name = '黑体'
    summary_heading.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    
    summary = report_data['summary']
    
    # 项目报告：强调项目全生命周期管理
    summary_text = doc.add_paragraph()
    if is_project_report:
        # 开篇文字
        intro_run = summary_text.add_run(
            "本项目自启动以来，项目采购与成本管理工作有序推进，各项业务环节紧密衔接，管理流程规范高效。"
            "截至报告期末，项目在采购、合同、付款及结算等关键环节均取得了显著进展。具体而言："
        )
        intro_run.font.size = Pt(12)
        
        # 添加数据段落，突出关键指标
        data_para = doc.add_paragraph()
        data_para.add_run("在采购环节，项目已完成采购项目").font.size = Pt(12)
        
        count_run = data_para.add_run(f" {summary['total_procurement_count']} ")
        count_run.font.size = Pt(12)
        count_run.font.bold = True
        count_run.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("个，项目中标总金额").font.size = Pt(12)
        
        amount_run = data_para.add_run(f" {summary['total_winning_amount']:,.2f} ")
        amount_run.font.size = Pt(12)
        amount_run.font.bold = True
        amount_run.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("元；在合同管理环节，累计签订合同").font.size = Pt(12)
        
        contract_run = data_para.add_run(f" {summary['total_contract_count']} ")
        contract_run.font.size = Pt(12)
        contract_run.font.bold = True
        contract_run.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("份，合同总金额").font.size = Pt(12)
        
        contract_amt_run = data_para.add_run(f" {summary['total_contract_amount']:,.2f} ")
        contract_amt_run.font.size = Pt(12)
        contract_amt_run.font.bold = True
        contract_amt_run.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("元；在资金支付环节，处理付款业务").font.size = Pt(12)
        
        payment_run = data_para.add_run(f" {summary['total_payment_count']} ")
        payment_run.font.size = Pt(12)
        payment_run.font.bold = True
        payment_run.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("笔，累计付款金额").font.size = Pt(12)
        
        payment_amt_run = data_para.add_run(f" {summary['total_payment_amount']:,.2f} ")
        payment_amt_run.font.size = Pt(12)
        payment_amt_run.font.bold = True
        payment_amt_run.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("元；在结算环节，完成结算").font.size = Pt(12)
        
        settle_run = data_para.add_run(f" {summary['total_settlement_count']} ")
        settle_run.font.size = Pt(12)
        settle_run.font.bold = True
        settle_run.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("笔，结算总金额").font.size = Pt(12)
        
        settle_amt_run = data_para.add_run(f" {summary['total_settlement_amount']:,.2f} ")
        settle_amt_run.font.size = Pt(12)
        settle_amt_run.font.bold = True
        settle_amt_run.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("元。").font.size = Pt(12)
        
        # 计算项目执行进度
        if summary['total_contract_amount'] > 0:
            payment_ratio = (summary['total_payment_amount'] / summary['total_contract_amount']) * 100
            settlement_ratio = (summary['total_settlement_count'] / summary['total_contract_count'] * 100) if summary['total_contract_count'] > 0 else 0
            
            progress_para = doc.add_paragraph()
            progress_para.add_run(
                f"从资金执行情况来看，项目付款进度为{payment_ratio:.1f}%，结算完成比例为{settlement_ratio:.1f}%。"
                f"项目整体运行{('顺利' if payment_ratio >= 60 else '正常')}，"
                f"资金支付与合同执行保持同步推进。"
            ).font.size = Pt(12)
    else:
        # 时间区间报告：强调时期内的业务动态
        intro_para = doc.add_paragraph()
        intro_para.add_run(
            "本报告期内，项目采购与成本管理各项工作稳步推进，业务流程规范有序。"
            "通过精细化管理和过程控制，各业务环节衔接顺畅，工作效率持续提升。"
            "期间取得的主要工作成果如下："
        ).font.size = Pt(12)
        
        # 数据段落
        data_para = doc.add_paragraph()
        data_para.add_run("采购业务方面，本期共完成采购项目").font.size = Pt(12)
        
        proc_count = data_para.add_run(f" {summary['total_procurement_count']} ")
        proc_count.font.size = Pt(12)
        proc_count.font.bold = True
        proc_count.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("个，本期中标总金额").font.size = Pt(12)
        
        proc_amt = data_para.add_run(f" {summary['total_winning_amount']:,.2f} ")
        proc_amt.font.size = Pt(12)
        proc_amt.font.bold = True
        proc_amt.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("元；合同管理方面，本期签订合同").font.size = Pt(12)
        
        cont_count = data_para.add_run(f" {summary['total_contract_count']} ")
        cont_count.font.size = Pt(12)
        cont_count.font.bold = True
        cont_count.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("份，合同总金额").font.size = Pt(12)
        
        cont_amt = data_para.add_run(f" {summary['total_contract_amount']:,.2f} ")
        cont_amt.font.size = Pt(12)
        cont_amt.font.bold = True
        cont_amt.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("元；资金支付方面，本期处理付款业务").font.size = Pt(12)
        
        pay_count = data_para.add_run(f" {summary['total_payment_count']} ")
        pay_count.font.size = Pt(12)
        pay_count.font.bold = True
        pay_count.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("笔，付款总金额").font.size = Pt(12)
        
        pay_amt = data_para.add_run(f" {summary['total_payment_amount']:,.2f} ")
        pay_amt.font.size = Pt(12)
        pay_amt.font.bold = True
        pay_amt.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("元；结算管理方面，本期完成结算").font.size = Pt(12)
        
        sett_count = data_para.add_run(f" {summary['total_settlement_count']} ")
        sett_count.font.size = Pt(12)
        sett_count.font.bold = True
        sett_count.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("笔，结算总金额").font.size = Pt(12)
        
        sett_amt = data_para.add_run(f" {summary['total_settlement_amount']:,.2f} ")
        sett_amt.font.size = Pt(12)
        sett_amt.font.bold = True
        sett_amt.font.color.rgb = RGBColor(192, 0, 0)
        
        data_para.add_run("元。").font.size = Pt(12)
        
        # 业务评价段落
        eval_para = doc.add_paragraph()
        eval_para.add_run(
            "从业务规模和执行质量来看，本期采购与合同签订工作量充足，反映了项目建设的持续推进；"
            "资金支付节奏稳健有序，体现了良好的资金计划性和支付管控能力；"
            "结算工作的及时完成为项目的财务核算和成本分析提供了可靠依据。"
            "总体而言，各项业务指标均在合理区间内运行，显示出良好的项目管理水平和执行能力。"
        ).font.size = Pt(12)
    
    # 二、采购业务分析
    doc.add_paragraph()
    doc.add_heading('二、采购业务分析', level=1).runs[0].font.size = Pt(16)
    procurement = report_data['procurement_data']
    
    if procurement['total_count'] > 0:
        # 采购工作背景和重要性
        proc_intro = doc.add_paragraph()
        proc_intro.add_run(
            "采购工作是项目成本控制的源头环节，是确保项目质量、控制项目成本、防范廉政风险的重要抓手。"
            f"{('本报告期内' if not is_project_report else '项目实施过程中')}，"
            "采购管理部门始终坚持依法依规、公开透明的原则，严格执行《中华人民共和国招标投标法》"
            "及相关法律法规要求，全面规范采购活动。通过建立健全采购管理制度体系，优化采购业务流程，"
            "加强采购过程监督管理，强化采购结果应用分析，不断提升采购管理的规范化、科学化、信息化水平，"
            "确保了采购工作的合规性、公正性和高效性，为项目建设提供了有力保障。"
        ).font.size = Pt(12)
        
        doc.add_paragraph()
        
        # 采购规模数据段落
        proc_data = doc.add_paragraph()
        proc_data.add_run(
            f"从采购规模和完成情况来看，{('本期' if not is_project_report else '项目累计')}共完成采购项目"
        ).font.size = Pt(12)
        
        count_run = proc_data.add_run(f" {procurement['total_count']} ")
        count_run.font.size = Pt(12)
        count_run.font.bold = True
        count_run.font.color.rgb = RGBColor(0, 112, 192)
        
        proc_data.add_run(
            "个，采购项目涵盖了工程建设、货物采购、服务外包等多个领域，"
            "充分满足了项目建设的多元化需求。采购预算总金额"
        ).font.size = Pt(12)
        
        budget_run = proc_data.add_run(f" {procurement['total_budget']:,.2f} ")
        budget_run.font.size = Pt(12)
        budget_run.font.bold = True
        budget_run.font.color.rgb = RGBColor(0, 112, 192)
        
        proc_data.add_run(
            "元，预算编制充分考虑了市场价格水平、项目技术要求、质量标准以及实际需求等多方面因素，"
            "经过了详细的市场调研和充分的科学论证。中标总金额"
        ).font.size = Pt(12)
        
        winning_run = proc_data.add_run(f" {procurement['total_winning']:,.2f} ")
        winning_run.font.size = Pt(12)
        winning_run.font.bold = True
        winning_run.font.color.rgb = RGBColor(0, 112, 192)
        
        proc_data.add_run(
            "元，中标价格合理，符合市场行情，充分体现了公开竞争、择优选择的原则。"
        ).font.size = Pt(12)

        # 成本控制分析
        if procurement['total_budget'] > 0 and procurement['total_winning'] > 0:
            savings_rate = (1 - procurement['total_winning'] / procurement['total_budget']) * 100
            
            doc.add_paragraph()
            doc.add_heading('成本控制成效', level=2).runs[0].font.size = Pt(14)
            
            savings_intro = doc.add_paragraph()
            savings_intro.add_run(
                "成本控制是采购管理的核心目标，直接关系到项目投资效益和资金使用效率。"
                "本期采购工作始终将成本控制放在突出位置，通过一系列行之有效的措施，取得了显著成效。"
                "在采购前期，组织专业人员深入开展市场调研，广泛收集市场供应信息和价格信息，"
                "准确把握市场价格走势和供求关系，为预算编制和采购决策提供了科学依据。"
                "在采购过程中，严格执行招标采购程序，通过公开透明的竞争机制，"
                "吸引更多优质供应商参与竞争，形成了充分竞争的市场格局。"
                "在评标定标环节，建立科学合理的评标体系，综合考虑价格、质量、服务、信誉等多方面因素，"
                "既注重价格合理性，又兼顾质量可靠性，实现了综合效益的最大化。"
            ).font.size = Pt(12)
            
            doc.add_paragraph()
            savings_result = doc.add_paragraph()
            savings_result.add_run(
                "经过统计分析，本期采购资金节约率达到"
            ).font.size = Pt(12)
            
            rate_run = savings_result.add_run(f" {savings_rate:.1f}% ")
            rate_run.font.size = Pt(12)
            rate_run.font.bold = True
            rate_run.font.color.rgb = RGBColor(0, 176, 80)
            
            if savings_rate >= 10:
                savings_result.add_run(
                    "，成本控制效果显著。这一成绩的取得，有效降低了项目采购成本，"
                    "提高了资金使用效益，为项目节约了大量建设资金，"
                    "充分体现了采购管理工作的专业性和有效性。"
                ).font.size = Pt(12)
            elif savings_rate >= 5:
                savings_result.add_run(
                    "，成本控制效果良好。在保证采购质量的前提下实现了成本的有效控制，"
                    "体现了采购工作在质量与成本之间的合理平衡，"
                    "达到了预期的成本控制目标。"
                ).font.size = Pt(12)
            else:
                savings_result.add_run(
                    "。虽然节约率不高，但考虑到项目的特殊性要求和严格的质量标准，"
                    "这一结果仍然体现了采购工作在确保质量的前提下对成本的合理控制。"
                ).font.size = Pt(12)

        # 采购方式分析
        if procurement['by_method']:
            doc.add_paragraph()
            doc.add_heading('采购方式分析', level=2).runs[0].font.size = Pt(14)
            
            method_intro = doc.add_paragraph()
            method_intro.add_run(
                "采购方式的选择是采购管理的重要环节，直接影响采购活动的合规性、竞争性和有效性。"
                "根据《中华人民共和国招标投标法》《政府采购法》以及单位内部采购管理制度的规定，"
                "采购方式的确定应当综合考虑采购项目的性质、规模、技术复杂程度、市场供应情况、"
                "时间要求等多方面因素。本期采购工作中，采购管理部门严格按照法律法规和制度规定，"
                "科学合理地确定采购方式，既保证了采购活动的合规性和竞争性，"
                "又兼顾了采购效率和采购效果。从本期采购方式的分布情况看："
            ).font.size = Pt(12)
            
            doc.add_paragraph()
            for method in procurement['by_method']:
                method_name = method['procurement_method'] or '未分类'
                count = method['count']
                amount = method['total_amount'] or 0
                amount_ratio = method['amount_ratio']
                
                method_para = doc.add_paragraph()
                method_para.add_run(f"【{method_name}】").font.size = Pt(12)
                method_para.runs[0].font.bold = True
                
                method_para.add_run(f"  本期采用该方式完成采购项目").font.size = Pt(12)
                
                m_count = method_para.add_run(f" {count} ")
                m_count.font.size = Pt(12)
                m_count.font.bold = True
                m_count.font.color.rgb = RGBColor(0, 112, 192)
                
                method_para.add_run("个，中标金额").font.size = Pt(12)
                
                m_amt = method_para.add_run(f" {amount:,.2f} ")
                m_amt.font.size = Pt(12)
                m_amt.font.bold = True
                m_amt.font.color.rgb = RGBColor(0, 112, 192)
                
                method_para.add_run("元，占总中标金额的").font.size = Pt(12)
                
                m_ratio = method_para.add_run(f" {amount_ratio:.1f}% ")
                m_ratio.font.size = Pt(12)
                m_ratio.font.bold = True
                m_ratio.font.color.rgb = RGBColor(0, 112, 192)
                
                method_para.add_run(
                    "。该采购方式根据项目特点和采购需求科学确定，"
                    "在确保采购活动合规性的同时，充分发挥了市场竞争机制的作用，"
                    "实现了采购效率与采购效果的有机统一。"
                ).font.size = Pt(12)
    else:
        doc.add_paragraph('本期无采购业务。').style = 'Intense Quote'

    # 三、合同管理分析
    doc.add_paragraph()
    doc.add_heading('三、合同管理分析', level=1).runs[0].font.size = Pt(16)
    contract = report_data['contract_data']
    
    if contract['total_count'] > 0:
        contract_para = doc.add_paragraph()
        contract_para.add_run(
            f"合同管理方面，{('本期内' if not is_project_report else '项目累计')}共签订合同{contract['total_count']}份，"
            f"合同总金额{contract['total_amount']:,.2f}元，平均单份合同金额为{contract['avg_amount']:,.2f}元。"
        ).font.size = Pt(12)
        
        if contract['by_source']:
            source_para = doc.add_paragraph('从合同来源看，', style='List Bullet')
            for source in contract['by_source']:
                source_name = source['contract_source'] or '未明确'
                count = source['count']
                total_amount = source['total_amount'] or 0
                source_para.add_run(f"来源为“{source_name}”的合同共{count}份，金额{total_amount:,.2f}元；")
            source_para.runs[-1].text = source_para.runs[-1].text.rstrip('；') + '。'

        if contract['by_type']:
            type_para = doc.add_paragraph('从合同类型（文件定位）看，', style='List Bullet')
            for ctype in contract['by_type']:
                type_name = ctype['file_positioning'] or '未分类'
                count = ctype['count']
                type_para.add_run(f"{type_name}{count}份；")
            type_para.runs[-1].text = type_para.runs[-1].text.rstrip('；') + '。'
    else:
        doc.add_paragraph('本期无合同签订。').style = 'Intense Quote'
    
    # 四、付款业务分析
    doc.add_paragraph()
    doc.add_heading('四、付款业务分析', level=1).runs[0].font.size = Pt(16)
    payment = report_data['payment_data']
    
    if payment['total_count'] > 0:
        payment_para = doc.add_paragraph()
        payment_para.add_run(
            f"资金支付方面，{('本期内' if not is_project_report else '项目累计')}共处理付款业务{payment['total_count']}笔，"
            f"付款总金额{payment['total_amount']:,.2f}元，平均每笔付款金额{payment['avg_amount']:,.2f}元。"
        ).font.size = Pt(12)
        
        if payment['top_projects'] and not is_project_report:
            doc.add_heading('主要付款项目分布', level=2).runs[0].font.size = Pt(14)
            top_para = doc.add_paragraph(
                '本期付款金额最高的项目包括：'
            )
            for i, proj in enumerate(payment['top_projects'][:3], start=1):
                proj_name = proj.get('contract__project__project_name', '未知项目')
                proj_amount = proj.get('total_payment', 0)
                top_para.add_run(f"“{proj_name}”（{proj_amount:,.2f}元）")
                if i < 3 and i < len(payment['top_projects']):
                    top_para.add_run("、")
            top_para.add_run("。这些项目是本期资金支出的主要方向。")
    else:
        doc.add_paragraph('本期无付款业务。').style = 'Intense Quote'
    
    # 五、结算业务分析
    doc.add_paragraph()
    doc.add_heading('五、结算业务分析', level=1).runs[0].font.size = Pt(16)
    
    settlement = report_data['settlement_data']
    
    if settlement['settled_count'] > 0:
        settle_para = doc.add_paragraph()
        settle_para.add_run(
            f"结算管理方面，{('本期内' if not is_project_report else '项目累计')}共完成结算{settlement['settled_count']}笔，"
            f"结算总金额{settlement['settled_amount']:,.2f}元，平均每笔结算金额{settlement['avg_settlement']:,.2f}元。"
            "结算工作的顺利完成，为项目的最终关闭和财务核算提供了重要依据。"
        ).font.size = Pt(12)
    else:
        doc.add_paragraph('本期无结算业务。').style = 'Intense Quote'
    
    # 六、工作总结与建议
    doc.add_paragraph()
    doc.add_heading('六、工作总结与建议', level=1).runs[0].font.size = Pt(16)
    
    conclusion_para = doc.add_paragraph()
    
    if is_project_report:
        conclusion_text = conclusion_para.add_run(
            "综上所述，本项目在采购、合同、资金支付和结算等环节管理有序，整体进展符合预期。"
            "建议下一步重点关注项目收尾阶段的各项工作，确保所有合同均完成结算，"
            "并做好项目资料的全面归档，为项目的最终评估奠定坚实基础。"
        )
    else:
        conclusion_text = conclusion_para.add_run(
            "本报告期内，项目采购与成本管理工作整体运行平稳，各项业务指标符合预期。"
            "建议在后续工作中，继续保持对采购成本的严格控制，优化合同签订与履行流程，"
            "并加强对资金支付计划性的管理，以进一步提升项目管理效率和资金使用效益。"
        )
    conclusion_text.font.size = Pt(12)
    
    # 添加页脚
    doc.add_paragraph()
    doc.add_paragraph()
    footer_para = doc.add_paragraph()
    footer_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer_run = footer_para.add_run(
        f"\n报告生成时间：{report_data['generated_at'].strftime('%Y年%m月%d日')}"
    )
    footer_run.font.size = Pt(10)
    footer_run.font.color.rgb = RGBColor(128, 128, 128)
    
    # 保存文档
    doc.save(file_path)
    return file_path
