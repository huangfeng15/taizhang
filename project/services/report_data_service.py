"""
统一的报表数据服务
遵循SRP原则：只负责数据获取，不涉及格式化
遵循DRY原则：复用现有的statistics服务，避免重复查询逻辑
"""
from datetime import date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone

from project.models import Project
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement

# 复用现有的统计服务
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


class ReportDataService:
    """
    报表数据服务 - 统一的数据获取接口
    遵循SOLID原则：单一职责、依赖倒置
    """

    def __init__(self, start_date: date, end_date: date, project_codes: Optional[List[str]] = None):
        """
        初始化数据服务

        Args:
            start_date: 统计开始日期
            end_date: 统计结束日期
            project_codes: 项目编码列表，None表示全部项目
        """
        self.start_date = start_date
        self.end_date = end_date
        self.project_codes = project_codes or []
        self.year = end_date.year if end_date else None

        # 判断报表范围
        self.is_single_project = len(self.project_codes) == 1
        self.is_multi_project = len(self.project_codes) > 1
        self.is_all_projects = not project_codes

    def get_all_statistics(self) -> Dict[str, Any]:
        """
        获取所有业务模块的统计数据
        复用statistics.py服务，遵循DRY原则

        Returns:
            dict: 包含所有统计数据的字典
        """
        return {
            'procurement': self.get_procurement_statistics(),
            'contract': self.get_contract_statistics(),
            'payment': self.get_payment_statistics(),
            'settlement': self.get_settlement_statistics(),
        }

    def get_procurement_statistics(self) -> Dict[str, Any]:
        """获取采购统计数据"""
        return get_procurement_statistics(
            self.year,
            self.project_codes if self.project_codes else None
        )

    def get_contract_statistics(self) -> Dict[str, Any]:
        """获取合同统计数据"""
        return get_contract_statistics(
            self.year,
            self.project_codes if self.project_codes else None
        )

    def get_payment_statistics(self) -> Dict[str, Any]:
        """获取付款统计数据"""
        return get_payment_statistics(
            self.year,
            self.project_codes if self.project_codes else None
        )

    def get_settlement_statistics(self) -> Dict[str, Any]:
        """获取结算统计数据"""
        return get_settlement_statistics(
            self.year,
            self.project_codes if self.project_codes else None
        )

    def get_projects_overview(self) -> Dict[str, Any]:
        """获取项目概览数据"""
        if self.is_all_projects:
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(project_code__in=self.project_codes)

        total_count = projects.count()

        # 按状态统计
        by_status = {}
        for status_value, status_label in Project.STATUS_CHOICES:
            count = projects.filter(status=status_value).count()
            if count > 0:
                by_status[status_label] = {
                    'count': count,
                    'ratio': (count / total_count * 100) if total_count > 0 else 0
                }

        return {
            'total_count': total_count,
            'by_status': by_status,
            'projects_list': [
                {
                    'code': p.project_code,
                    'name': p.project_name,
                    'manager': p.project_manager or '未指定',
                    'status': p.get_status_display(),
                }
                for p in projects
            ]
        }

    def get_archive_monitoring(self) -> Dict[str, Any]:
        """获取归档监控数据"""
        monitor_service = ArchiveMonitorService()
        return monitor_service.get_archive_statistics(
            year=self.year,
            project_codes=self.project_codes if self.project_codes else None
        )

    def get_update_monitoring(self) -> Dict[str, Any]:
        """获取更新监控数据"""
        monitor_service = UpdateMonitorService()
        return monitor_service.get_update_statistics(
            year=self.year,
            project_codes=self.project_codes if self.project_codes else None
        )

    def get_completeness_analysis(self) -> Dict[str, Any]:
        """获取数据完整性分析"""
        return get_completeness_overview(
            year=self.year,
            project_codes=self.project_codes if self.project_codes else None
        )

    def get_ranking_analysis(self) -> Dict[str, Any]:
        """获取排名分析数据"""
        return {
            'procurement_on_time': get_procurement_on_time_ranking(
                year=self.year,
                project_codes=self.project_codes if self.project_codes else None
            ),
            'procurement_cycle': get_procurement_cycle_ranking(
                year=self.year,
                project_codes=self.project_codes if self.project_codes else None
            ),
            'archive_timeliness': get_archive_timeliness_ranking(
                year=self.year,
                project_codes=self.project_codes if self.project_codes else None
            ),
            'comprehensive': get_comprehensive_ranking(
                year=self.year,
                project_codes=self.project_codes if self.project_codes else None
            ),
        }

    def get_procurement_details(self) -> list:
        """获取采购详情列表（封装自 statistics 模块，保持对外接口稳定）"""
        from project.services.statistics import get_procurement_details
        return get_procurement_details(self.year, self.project_codes if self.project_codes else None)

    def get_contract_details(self) -> list:
        """获取合同详情列表"""
        from project.services.statistics import get_contract_details
        return get_contract_details(self.year, self.project_codes if self.project_codes else None)

    def get_payment_details(self) -> list:
        """获取付款详情列表"""
        from project.services.statistics import get_payment_details
        return get_payment_details(self.year, self.project_codes if self.project_codes else None)

    def get_settlement_details(self) -> list:
        """获取结算详情列表"""
        from project.services.statistics import get_settlement_details
        return get_settlement_details(self.year, self.project_codes if self.project_codes else None)

    def get_executive_summary(self) -> Dict[str, Any]:
        """获取执行摘要数据"""
        stats = self.get_all_statistics()

        return {
            'period_start': self.start_date,
            'period_end': self.end_date,
            'total_procurement': stats['procurement'].get('total_count', 0),
            'total_contract': stats['contract'].get('total_count', 0),
            'total_payment': stats['payment'].get('total_count', 0),
            'total_settlement': stats['settlement'].get('total_count', 0),
            'total_procurement_amount': stats['procurement'].get('total_winning_amount', 0),
            'total_contract_amount': stats['contract'].get('total_amount', 0),
            'total_payment_amount': stats['payment'].get('total_amount', 0),
            'total_settlement_amount': stats['settlement'].get('total_amount', 0),
        }

    def get_single_project_details(self) -> Optional[Dict[str, Any]]:
        """获取单个项目的详细信息"""
        if not self.is_single_project:
            return None

        project = Project.objects.filter(project_code=self.project_codes[0]).first()
        if not project:
            return None

        return {
            'project_code': project.project_code,
            'project_name': project.project_name,
            'project_manager': project.project_manager or '未指定',
            'project_status': project.get_status_display(),
            'project_description': project.description or '',
            'created_at': project.created_at,
            'updated_at': project.updated_at,
        }

    def get_report_meta(self, report_type: str = 'general', report_title: str = '工作报告') -> Dict[str, Any]:
        """
        获取报告元信息

        Args:
            report_type: 报告类型 (general/professional/comprehensive)
            report_title: 报告标题

        Returns:
            dict: 报告元信息
        """
        meta = {
            'generated_at': timezone.now(),
            'period_start': self.start_date,
            'period_end': self.end_date,
            'report_type': report_type,
            'report_title': report_title,
            'report_scope': self._determine_scope(),
            'reporting_unit': '项目采购与成本管理部门',
            'confidentiality_level': '内部使用',
        }

        # 添加项目相关信息
        if self.is_single_project:
            project_details = self.get_single_project_details()
            if project_details:
                meta['project_info'] = project_details
        elif self.is_multi_project:
            projects = Project.objects.filter(project_code__in=self.project_codes)
            meta['project_info'] = {
                'project_count': projects.count(),
                'project_list': [
                    {'code': p.project_code, 'name': p.project_name}
                    for p in projects
                ],
            }

        return meta

    def _determine_scope(self) -> str:
        """确定报表范围"""
        if self.is_all_projects:
            return '全部项目'
        elif self.is_single_project:
            project = Project.objects.filter(project_code=self.project_codes[0]).first()
            return f'单项目：{project.project_name}' if project else '单项目'
        else:
            return f'多项目（{len(self.project_codes)}个）'

    def get_financial_analysis(self) -> Dict[str, Any]:
        """获取财务分析数据（用于综合报告）"""
        stats = self.get_all_statistics()

        # 计算各项财务指标
        total_budget = stats['procurement'].get('total_budget_amount', 0)
        total_winning = stats['procurement'].get('total_winning_amount', 0)
        total_contract = stats['contract'].get('total_amount', 0)
        total_payment = stats['payment'].get('total_amount', 0)
        total_settlement = stats['settlement'].get('total_amount', 0)

        # 计算节约率
        savings_rate = 0
        if total_budget > 0:
            savings_rate = ((total_budget - total_winning) / total_budget * 100)

        # 计算付款率
        payment_rate = 0
        if total_contract > 0:
            payment_rate = (total_payment / total_contract * 100)

        # 计算结算率
        settlement_rate = 0
        if total_contract > 0:
            settlement_rate = (total_settlement / total_contract * 100)

        return {
            'total_budget': float(total_budget),
            'total_winning': float(total_winning),
            'total_contract': float(total_contract),
            'total_payment': float(total_payment),
            'total_settlement': float(total_settlement),
            'savings_amount': float(total_budget - total_winning),
            'savings_rate': round(savings_rate, 2),
            'payment_rate': round(payment_rate, 2),
            'settlement_rate': round(settlement_rate, 2),
        }

    def get_recommendations(self) -> List[str]:
        """
        基于数据生成管理建议

        Returns:
            list: 建议列表
        """
        recommendations = []

        # 获取完整性数据
        completeness = self.get_completeness_analysis()

        # 检查数据完整性
        if completeness.get('overall_completeness', 100) < 90:
            recommendations.append('建议加强数据录入管理，提高数据完整性')

        # 检查归档进度
        archive_data = self.get_archive_monitoring()
        if archive_data.get('overall_progress', 100) < 80:
            recommendations.append('建议加快归档进度，确保资料及时归档')

        # 检查付款进度
        payment_stats = self.get_payment_statistics()
        if payment_stats.get('total_count', 0) > 0:
            avg_days = payment_stats.get('avg_payment_days', 0)
            if avg_days > 30:
                recommendations.append('建议优化付款流程，缩短付款周期')

        # 如果没有特别建议，添加通用建议
        if not recommendations:
            recommendations.append('继续保持良好的管理水平，持续优化业务流程')

        return recommendations
