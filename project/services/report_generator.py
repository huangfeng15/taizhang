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
    
    def __init__(self, start_date, end_date):
        """
        初始化报表生成器
        
        Args:
            start_date: 统计开始日期
            end_date: 统计结束日期
        """
        self.start_date = start_date
        self.end_date = end_date
    
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
        
        total_count = queryset.count()
        total_budget = queryset.aggregate(Sum('budget_amount'))['budget_amount__sum'] or Decimal('0')
        total_winning = queryset.aggregate(Sum('winning_amount'))['winning_amount__sum'] or Decimal('0')
        
        # 按采购方式统计
        by_method = list(queryset.values('procurement_method').annotate(
            count=Count('id'),
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
        
        total_count = queryset.count()
        total_amount = queryset.aggregate(Sum('contract_amount'))['contract_amount__sum'] or Decimal('0')
        
        # 按合同类型统计
        by_type = list(queryset.values('file_positioning').annotate(
            count=Count('id'),
            total_amount=Sum('contract_amount')
        ).order_by('-count'))
        
        # 按合同来源统计
        by_source = list(queryset.values('contract_source').annotate(
            count=Count('id'),
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
        
        total_count = queryset.count()
        total_amount = queryset.aggregate(Sum('payment_amount'))['payment_amount__sum'] or Decimal('0')
        
        # TOP10项目
        top_projects = list(queryset.values(
            'contract__project__project_code',
            'contract__project__project_name'
        ).annotate(
            total_payment=Sum('payment_amount'),
            payment_count=Count('id')
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
    
    def __init__(self, target_date=None):
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
        
        super().__init__(start_date, end_date)
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
    
    def __init__(self, year=None, month=None):
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
        
        super().__init__(start_date, end_date)
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
    
    def __init__(self, year=None, quarter=None):
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
        
        super().__init__(start_date, end_date)
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
    
    def __init__(self, year=None):
        """
        初始化年报生成器
        
        Args:
            year: 年份，默认为当前年份
        """
        if year is None:
            year = date.today().year
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        super().__init__(start_date, end_date)
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