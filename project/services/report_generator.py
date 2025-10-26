"""
报表生成服务
用于生成周报、月报、季报、年报
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Max, Min, Q
from django.utils import timezone

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
    导出报表为Excel格式
    
    Args:
        report_data: 报表数据字典
        file_path: 导出文件路径
    
    Returns:
        str: 导出的文件路径
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    
    wb = Workbook()
    ws = wb.active
    ws.title = "报表汇总"
    
    # 设置标题
    ws['A1'] = report_data.get('title', '工作报表')
    ws['A1'].font = Font(size=16, bold=True)
    ws['A1'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A1:D1')
    
    # 基本信息
    row = 3
    ws[f'A{row}'] = '统计周期：'
    ws[f'B{row}'] = f"{report_data['period_start']} 至 {report_data['period_end']}"
    row += 1
    ws[f'A{row}'] = '生成时间：'
    ws[f'B{row}'] = report_data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')
    row += 2
    
    # 汇总数据
    ws[f'A{row}'] = '数据汇总'
    ws[f'A{row}'].font = Font(size=14, bold=True)
    row += 1
    
    summary = report_data['summary']
    ws[f'A{row}'] = '采购项目数'
    ws[f'B{row}'] = summary['total_procurement_count']
    row += 1
    ws[f'A{row}'] = '合同签订数'
    ws[f'B{row}'] = summary['total_contract_count']
    row += 1
    ws[f'A{row}'] = '付款笔数'
    ws[f'B{row}'] = summary['total_payment_count']
    row += 1
    ws[f'A{row}'] = '结算笔数'
    ws[f'B{row}'] = summary['total_settlement_count']
    row += 2
    
    ws[f'A{row}'] = '中标金额（元）'
    ws[f'B{row}'] = summary['total_winning_amount']
    row += 1
    ws[f'A{row}'] = '合同金额（元）'
    ws[f'B{row}'] = summary['total_contract_amount']
    row += 1
    ws[f'A{row}'] = '付款金额（元）'
    ws[f'B{row}'] = summary['total_payment_amount']
    row += 1
    ws[f'A{row}'] = '结算金额（元）'
    ws[f'B{row}'] = summary['total_settlement_amount']
    
    # 调整列宽
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 30
    
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
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    
    doc = Document()
    
    # 设置文档默认字体为中文
    doc.styles['Normal'].font.name = '宋体'
    doc.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    doc.styles['Normal'].font.size = Pt(12)
    
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
    
    # 一、摘要部分
    summary_heading = doc.add_heading('一、工作概况', level=1)
    summary_heading.runs[0].font.size = Pt(16)
    summary_heading.runs[0].font.color.rgb = RGBColor(0, 51, 102)
    summary_heading.runs[0].font.name = '黑体'
    summary_heading.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    
    summary = report_data['summary']
    summary_text = doc.add_paragraph()
    summary_text.add_run(
        f"本期内，项目采购与成本管理工作稳步推进。共完成采购项目 {summary['total_procurement_count']} 个，"
        f"签订合同 {summary['total_contract_count']} 份，处理付款业务 {summary['total_payment_count']} 笔，"
        f"完成结算 {summary['total_settlement_count']} 笔。中标总金额 {summary['total_winning_amount']:.2f} 元，"
        f"合同总金额 {summary['total_contract_amount']:.2f} 元，付款总金额 {summary['total_payment_amount']:.2f} 元，"
        f"结算总金额 {summary['total_settlement_amount']:.2f} 元。"
    ).font.size = Pt(12)
    
    # 二、数据汇总表
    doc.add_heading('二、核心数据汇总', level=1).runs[0].font.size = Pt(16)
    doc.add_heading('2.1 业务量统计', level=2).runs[0].font.size = Pt(14)
    
    # 创建业务量表格
    table1 = doc.add_table(rows=5, cols=3)
    table1.style = 'Light Grid Accent 1'
    
    # 表头
    header_cells = table1.rows[0].cells
    header_cells[0].text = '业务类型'
    header_cells[1].text = '数量'
    header_cells[2].text = '单位'
    
    # 设置表头样式
    for cell in header_cells:
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(11)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # 数据行
    data_rows = [
        ('采购项目', summary['total_procurement_count'], '个'),
        ('合同签订', summary['total_contract_count'], '份'),
        ('付款笔数', summary['total_payment_count'], '笔'),
        ('结算笔数', summary['total_settlement_count'], '笔'),
    ]
    
    for i, (label, value, unit) in enumerate(data_rows, start=1):
        cells = table1.rows[i].cells
        cells[0].text = label
        cells[1].text = str(value)
        cells[2].text = unit
        for cell in cells:
            cell.paragraphs[0].runs[0].font.size = Pt(11)
    
    doc.add_paragraph()
    
    # 金额统计表
    doc.add_heading('2.2 金额统计', level=2).runs[0].font.size = Pt(14)
    
    table2 = doc.add_table(rows=5, cols=3)
    table2.style = 'Light Grid Accent 1'
    
    # 表头
    header_cells2 = table2.rows[0].cells
    header_cells2[0].text = '金额类型'
    header_cells2[1].text = '金额（元）'
    header_cells2[2].text = '占比'
    
    for cell in header_cells2:
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(11)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # 计算总金额用于占比
    total_amount = (summary['total_winning_amount'] + summary['total_contract_amount'] + 
                   summary['total_payment_amount'] + summary['total_settlement_amount'])
    
    amount_rows = [
        ('中标金额', summary['total_winning_amount']),
        ('合同金额', summary['total_contract_amount']),
        ('付款金额', summary['total_payment_amount']),
        ('结算金额', summary['total_settlement_amount']),
    ]
    
    for i, (label, amount) in enumerate(amount_rows, start=1):
        cells = table2.rows[i].cells
        cells[0].text = label
        cells[1].text = f"{amount:,.2f}"
        ratio = (amount / total_amount * 100) if total_amount > 0 else 0
        cells[2].text = f"{ratio:.1f}%"
        for cell in cells:
            cell.paragraphs[0].runs[0].font.size = Pt(11)
    
    # 三、采购业务分析
    doc.add_paragraph()
    doc.add_heading('三、采购业务分析', level=1).runs[0].font.size = Pt(16)
    
    procurement = report_data['procurement_data']
    
    if procurement['total_count'] > 0:
        proc_para = doc.add_paragraph()
        proc_para.add_run(
            f"本期共完成采购项目 {procurement['total_count']} 个，预算总金额 {procurement['total_budget']:,.2f} 元，"
            f"中标总金额 {procurement['total_winning']:,.2f} 元，平均中标金额 {procurement['avg_winning']:,.2f} 元。"
        ).font.size = Pt(12)
        
        if procurement['by_method']:
            doc.add_heading('3.1 采购方式分布', level=2).runs[0].font.size = Pt(14)
            
            method_table = doc.add_table(rows=len(procurement['by_method']) + 1, cols=4)
            method_table.style = 'Light Grid Accent 1'
            
            # 表头
            header = method_table.rows[0].cells
            header[0].text = '采购方式'
            header[1].text = '项目数'
            header[2].text = '中标金额（元）'
            header[3].text = '占比'
            
            for cell in header:
                cell.paragraphs[0].runs[0].font.bold = True
                cell.paragraphs[0].runs[0].font.size = Pt(11)
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            for i, method in enumerate(procurement['by_method'], start=1):
                cells = method_table.rows[i].cells
                cells[0].text = method['procurement_method'] or '未分类'
                cells[1].text = str(method['count'])
                cells[2].text = f"{method['total_amount']:,.2f}" if method['total_amount'] else '0.00'
                cells[3].text = f"{method['amount_ratio']:.1f}%"
                for cell in cells:
                    cell.paragraphs[0].runs[0].font.size = Pt(11)
    else:
        doc.add_paragraph('本期无采购业务。').style = 'Intense Quote'
    
    # 四、合同管理分析
    doc.add_paragraph()
    doc.add_heading('四、合同管理分析', level=1).runs[0].font.size = Pt(16)
    
    contract = report_data['contract_data']
    
    if contract['total_count'] > 0:
        contract_para = doc.add_paragraph()
        contract_para.add_run(
            f"本期共签订合同 {contract['total_count']} 份，合同总金额 {contract['total_amount']:,.2f} 元，"
            f"平均合同金额 {contract['avg_amount']:,.2f} 元。"
        ).font.size = Pt(12)
        
        if contract['by_type']:
            doc.add_heading('4.1 合同类型分布', level=2).runs[0].font.size = Pt(14)
            
            type_table = doc.add_table(rows=len(contract['by_type']) + 1, cols=3)
            type_table.style = 'Light Grid Accent 1'
            
            header = type_table.rows[0].cells
            header[0].text = '合同类型'
            header[1].text = '合同数'
            header[2].text = '合同金额（元）'
            
            for cell in header:
                cell.paragraphs[0].runs[0].font.bold = True
                cell.paragraphs[0].runs[0].font.size = Pt(11)
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            for i, ctype in enumerate(contract['by_type'], start=1):
                cells = type_table.rows[i].cells
                cells[0].text = ctype['file_positioning'] or '未分类'
                cells[1].text = str(ctype['count'])
                cells[2].text = f"{ctype['total_amount']:,.2f}" if ctype['total_amount'] else '0.00'
                for cell in cells:
                    cell.paragraphs[0].runs[0].font.size = Pt(11)
    else:
        doc.add_paragraph('本期无合同签订。').style = 'Intense Quote'
    
    # 五、付款业务分析
    doc.add_paragraph()
    doc.add_heading('五、付款业务分析', level=1).runs[0].font.size = Pt(16)
    
    payment = report_data['payment_data']
    
    if payment['total_count'] > 0:
        payment_para = doc.add_paragraph()
        payment_para.add_run(
            f"本期共处理付款业务 {payment['total_count']} 笔，付款总金额 {payment['total_amount']:,.2f} 元，"
            f"平均付款金额 {payment['avg_amount']:,.2f} 元。"
        ).font.size = Pt(12)
        
        if payment['top_projects']:
            doc.add_heading('5.1 付款TOP10项目', level=2).runs[0].font.size = Pt(14)
            
            pay_table = doc.add_table(rows=min(len(payment['top_projects']) + 1, 11), cols=4)
            pay_table.style = 'Light Grid Accent 1'
            
            header = pay_table.rows[0].cells
            header[0].text = '排名'
            header[1].text = '项目编码'
            header[2].text = '项目名称'
            header[3].text = '付款金额（元）'
            
            for cell in header:
                cell.paragraphs[0].runs[0].font.bold = True
                cell.paragraphs[0].runs[0].font.size = Pt(11)
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            for i, proj in enumerate(payment['top_projects'][:10], start=1):
                cells = pay_table.rows[i].cells
                cells[0].text = str(i)
                cells[1].text = proj['contract__project__project_code'] or ''
                cells[2].text = proj['contract__project__project_name'] or ''
                cells[3].text = f"{proj['total_payment']:,.2f}" if proj['total_payment'] else '0.00'
                for cell in cells:
                    cell.paragraphs[0].runs[0].font.size = Pt(10)
    else:
        doc.add_paragraph('本期无付款业务。').style = 'Intense Quote'
    
    # 六、结算业务分析
    doc.add_paragraph()
    doc.add_heading('六、结算业务分析', level=1).runs[0].font.size = Pt(16)
    
    settlement = report_data['settlement_data']
    
    if settlement['settled_count'] > 0:
        settle_para = doc.add_paragraph()
        settle_para.add_run(
            f"本期共完成结算 {settlement['settled_count']} 笔，结算总金额 {settlement['settled_amount']:,.2f} 元，"
            f"平均结算金额 {settlement['avg_settlement']:,.2f} 元。"
        ).font.size = Pt(12)
    else:
        doc.add_paragraph('本期无结算业务。').style = 'Intense Quote'
    
    # 七、工作总结
    doc.add_paragraph()
    doc.add_heading('七、工作总结与建议', level=1).runs[0].font.size = Pt(16)
    
    conclusion_para = doc.add_paragraph()
    conclusion_text = conclusion_para.add_run(
        "本期项目采购与成本管理工作整体运行平稳，各项业务指标符合预期。"
        "下一步工作中，建议继续加强成本控制，优化采购流程，提高资金使用效率，"
        "确保项目顺利推进。同时，应加强合同管理和付款审核，防范财务风险，"
        "提升管理水平和服务质量。"
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
