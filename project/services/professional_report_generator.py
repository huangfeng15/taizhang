"""
专业报告生成器
支持周报、月报、季报、年报，以及单个/多个项目的独立报告
生成符合专业咨询机构标准的Word文档
"""
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from django.db.models import Sum, Count, Q
from django.utils import timezone

from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement
from project.models import Project
from project.services.statistics import (
    get_procurement_statistics,
    get_contract_statistics,
    get_payment_statistics,
    get_settlement_statistics
)
from project.services.archive_monitor import ArchiveMonitorService
from project.services.update_monitor import UpdateMonitorService
from project.services.completeness import get_completeness_overview
from project.services.ranking import (
    get_procurement_on_time_ranking,
    get_procurement_cycle_ranking,
    get_archive_timeliness_ranking,
    get_comprehensive_ranking
)


class ProfessionalReportGenerator:
    """专业报告生成器基类"""
    
    def __init__(self, start_date: date, end_date: date, project_codes: Optional[List[str]] = None):
        """
        初始化报告生成器
        
        Args:
            start_date: 统计开始日期
            end_date: 统计结束日期
            project_codes: 项目编码列表，None表示全部项目
        """
        self.start_date = start_date
        self.end_date = end_date
        self.project_codes = project_codes or []
        self.is_single_project = len(self.project_codes) == 1
        self.is_multi_project = len(self.project_codes) > 1
        self.is_all_projects = not project_codes
        self.report_type = 'general'
        self.report_title = '工作报告'
        
    def generate_report_data(self) -> Dict[str, Any]:
        """
        生成完整的报告数据
        
        Returns:
            dict: 包含所有报告数据的字典
        """
        year = self.end_date.year if self.end_date else None
        
        # 基础信息
        report_data = {
            'meta': self._get_report_meta(),
            'summary': self._get_executive_summary(),
            'projects_overview': self._get_projects_overview(),
            'procurement': get_procurement_statistics(year, self.project_codes if self.project_codes else None),
            'contract': get_contract_statistics(year, self.project_codes if self.project_codes else None),
            'payment': get_payment_statistics(year, self.project_codes if self.project_codes else None),
            'settlement': get_settlement_statistics(year, self.project_codes if self.project_codes else None),
            'archive_monitoring': self._get_archive_monitoring(),
            'completeness': self._get_completeness_analysis(),
            'ranking': self._get_ranking_analysis(),
            'recommendations': self._get_recommendations(),
        }
        
        # 单项目报告增加项目特定信息
        if self.is_single_project:
            report_data['project_details'] = self._get_single_project_details()
        
        return report_data
    
    def _get_report_meta(self) -> Dict[str, Any]:
        """获取报告元信息"""
        project_info = {}
        if self.is_single_project:
            project = Project.objects.filter(project_code=self.project_codes[0]).first()
            if project:
                project_info = {
                    'project_code': project.project_code,
                    'project_name': project.project_name,
                    'project_manager': project.project_manager or '未指定',
                    'project_status': project.status,
                }
        elif self.is_multi_project:
            projects = Project.objects.filter(project_code__in=self.project_codes)
            project_info = {
                'project_count': projects.count(),
                'project_names': [p.project_name for p in projects],
            }
        
        return {
            'generated_at': timezone.now(),
            'period_start': self.start_date,
            'period_end': self.end_date,
            'report_type': self.report_type,
            'report_title': self.report_title,
            'report_scope': '单项目' if self.is_single_project else ('多项目' if self.is_multi_project else '全部项目'),
            'project_info': project_info,
        }
    
    def _get_executive_summary(self) -> Dict[str, Any]:
        """生成执行摘要"""
        year = self.end_date.year if self.end_date else None
        procurement_stats = get_procurement_statistics(year, self.project_codes if self.project_codes else None)
        contract_stats = get_contract_statistics(year, self.project_codes if self.project_codes else None)
        payment_stats = get_payment_statistics(year, self.project_codes if self.project_codes else None)
        settlement_stats = get_settlement_statistics(year, self.project_codes if self.project_codes else None)
        
        archive_service = ArchiveMonitorService(year=year, project_codes=self.project_codes if self.project_codes else None)
        archive_overview = archive_service.get_archive_overview()
        
        total_projects = 1 if self.is_single_project else (
            len(self.project_codes) if self.is_multi_project else Project.objects.count()
        )
        
        return {
            'total_projects': total_projects,
            'total_procurements': procurement_stats['total_count'],
            'total_contracts': contract_stats['total_count'],
            'total_payments': payment_stats['total_count'],
            'total_settlements': settlement_stats['total_count'],
            'total_budget': procurement_stats['total_budget'],
            'total_winning': procurement_stats['total_winning'],
            'total_contract_amount': contract_stats['total_amount'],
            'total_payment_amount': payment_stats['total_amount'],
            'total_settlement_amount': settlement_stats['total_amount'],
            'savings_rate': procurement_stats['savings_rate'],
            'archive_rate': archive_overview['overall_rate'],
            'archive_timely_rate': archive_overview.get('overall_timely_rate', 0),
            'payment_rate': payment_stats.get('payment_rate', 0),
        }
    
    def _get_projects_overview(self) -> Dict[str, Any]:
        """获取项目概览"""
        if self.is_single_project:
            project = Project.objects.filter(project_code=self.project_codes[0]).first()
            if not project:
                return {}
            
            return {
                'project': {
                    'code': project.project_code,
                    'name': project.project_name,
                    'description': project.description or '',
                    'manager': project.project_manager or '未指定',
                    'status': project.status,
                    'created_at': project.created_at,
                },
                'procurement_count': Procurement.objects.filter(project=project).count(),
                'contract_count': Contract.objects.filter(project=project).count(),
                'total_contract_amount': Contract.objects.filter(project=project).aggregate(
                    total=Sum('contract_amount'))['total'] or Decimal('0'),
            }
        else:
            queryset = Project.objects.all()
            if self.project_codes:
                queryset = queryset.filter(project_code__in=self.project_codes)
            
            projects_data = []
            for project in queryset:
                projects_data.append({
                    'code': project.project_code,
                    'name': project.project_name,
                    'status': project.status,
                    'procurement_count': Procurement.objects.filter(project=project).count(),
                    'contract_count': Contract.objects.filter(project=project).count(),
                })
            
            return {
                'total_count': queryset.count(),
                'projects': projects_data,
            }
    
    def _get_archive_monitoring(self) -> Dict[str, Any]:
        """归档监控分析"""
        year = self.end_date.year if self.end_date else None
        service = ArchiveMonitorService(year=year, project_codes=self.project_codes if self.project_codes else None)
        overview = service.get_archive_overview()
        overdue_list = service.get_overdue_list()
        
        return {
            'overview': overview,
            'overdue_count': len(overdue_list),
            'overdue_severe': sum(1 for item in overdue_list if item['severity'] == 'severe'),
            'overdue_moderate': sum(1 for item in overdue_list if item['severity'] == 'moderate'),
            'overdue_mild': sum(1 for item in overdue_list if item['severity'] == 'mild'),
            'overdue_items': overdue_list[:20],
        }
    
    def _get_completeness_analysis(self) -> Dict[str, Any]:
        """完整性分析"""
        year = self.end_date.year if self.end_date else None
        return get_completeness_overview(year=year, project_codes=self.project_codes if self.project_codes else None)
    
    def _get_ranking_analysis(self) -> Dict[str, Any]:
        """排名分析"""
        year = self.end_date.year if self.end_date else None
        
        return {
            'procurement_on_time': get_procurement_on_time_ranking('project', year)[:10],
            'procurement_cycle': get_procurement_cycle_ranking('project', year)[:10],
            'archive_timeliness': get_archive_timeliness_ranking('project', year)[:10],
            'comprehensive': get_comprehensive_ranking(year)[:10],
        }
    
    def _get_recommendations(self) -> List[str]:
        """管理建议"""
        recommendations = []
        
        year = self.end_date.year if self.end_date else None
        procurement_stats = get_procurement_statistics(year, self.project_codes if self.project_codes else None)
        
        if procurement_stats['avg_cycle_days'] > 45:
            recommendations.append(
                f"采购平均周期为{procurement_stats['avg_cycle_days']:.1f}天，"
                "建议优化采购流程，提高审批效率，缩短采购周期。"
            )
        
        if procurement_stats['savings_rate'] < 5:
            recommendations.append(
                f"采购节约率为{procurement_stats['savings_rate']:.2f}%，"
                "建议加强成本控制，通过充分竞争降低采购成本。"
            )
        
        archive_service = ArchiveMonitorService(year=year, project_codes=self.project_codes if self.project_codes else None)
        archive_overview = archive_service.get_archive_overview()
        
        if archive_overview['overall_rate'] < 90:
            recommendations.append(
                f"资料归档率为{archive_overview['overall_rate']:.1f}%，"
                "建议建立归档提醒机制，确保资料及时归档。"
            )
        
        if not recommendations:
            recommendations.append("各项指标表现良好，建议继续保持当前管理水平。")
        
        return recommendations
    
    def _get_single_project_details(self) -> Dict[str, Any]:
        """获取单个项目的详细信息（仅用于单项目报告）"""
        if not self.is_single_project:
            return {}
        
        project = Project.objects.filter(project_code=self.project_codes[0]).first()
        if not project:
            return {}
        
        procurements = Procurement.objects.filter(project=project)
        contracts = Contract.objects.filter(project=project)
        payments = Payment.objects.filter(contract__project=project)
        
        total_contract_amount = contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
        total_paid = payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
        payment_progress = (float(total_paid) / float(total_contract_amount) * 100) if total_contract_amount > 0 else 0
        
        settled_contracts = Contract.objects.filter(
            project=project,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
        ).filter(
            Q(settlement__isnull=False) |
            Q(payments__is_settled=True)
        ).distinct().count()
        
        total_main_contracts = Contract.objects.filter(
            project=project,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
        ).count()
        
        settlement_rate = (settled_contracts / total_main_contracts * 100) if total_main_contracts > 0 else 0
        
        return {
            'progress': {
                'payment_progress': payment_progress,
                'settlement_rate': settlement_rate,
                'procurement_count': procurements.count(),
                'contract_count': contracts.count(),
                'payment_count': payments.count(),
            },
            'financial_summary': {
                'total_contract_amount': float(total_contract_amount),
                'total_paid': float(total_paid),
                'remaining_amount': float(total_contract_amount - total_paid),
            },
        }


class WeeklyReportGenerator(ProfessionalReportGenerator):
    """周报生成器"""
    
    def __init__(self, target_date: Optional[date] = None, project_codes: Optional[List[str]] = None):
        if target_date is None:
            target_date = date.today()
        
        weekday = target_date.weekday()
        start_date = target_date - timedelta(days=weekday)
        end_date = start_date + timedelta(days=6)
        
        super().__init__(start_date, end_date, project_codes)
        self.week_number = target_date.isocalendar()[1]
        self.year = target_date.year
        self.report_type = 'weekly'
        self.report_title = f'{self.year}年第{self.week_number}周工作周报'


class MonthlyReportGenerator(ProfessionalReportGenerator):
    """月报生成器"""
    
    def __init__(self, year: Optional[int] = None, month: Optional[int] = None, 
                 project_codes: Optional[List[str]] = None):
        if year is None or month is None:
            today = date.today()
            year = year or today.year
            month = month or today.month
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year, 12, 31)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        super().__init__(start_date, end_date, project_codes)
        self.year = year
        self.month = month
        self.report_type = 'monthly'
        self.report_title = f'{year}年{month}月工作月报'


class QuarterlyReportGenerator(ProfessionalReportGenerator):
    """季报生成器"""
    
    def __init__(self, year: Optional[int] = None, quarter: Optional[int] = None,
                 project_codes: Optional[List[str]] = None):
        if year is None or quarter is None:
            today = date.today()
            year = year or today.year
            quarter = quarter or ((today.month - 1) // 3 + 1)
        
        start_month = (quarter - 1) * 3 + 1
        start_date = date(year, start_month, 1)
        
        end_month = start_month + 2
        if end_month == 12:
            end_date = date(year, 12, 31)
        else:
            end_date = date(year, end_month + 1, 1) - timedelta(days=1)
        
        super().__init__(start_date, end_date, project_codes)
        self.year = year
        self.quarter = quarter
        self.report_type = 'quarterly'
        self.report_title = f'{year}年第{quarter}季度工作报告'


class AnnualReportGenerator(ProfessionalReportGenerator):
    """年报生成器"""
    
    def __init__(self, year: Optional[int] = None, project_codes: Optional[List[str]] = None):
        if year is None:
            year = date.today().year
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        super().__init__(start_date, end_date, project_codes)
        self.year = year
        self.report_type = 'annual'
        self.report_title = f'{year}年度工作总结报告'