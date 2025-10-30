"""
高级报告生成器
专为年度总结报告、部门总结报告等详细Word文档设计
支持深度数据分析、多维度统计、趋势分析等
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from django.db.models import Sum, Count, Avg, Max, Min, Q, F
from django.utils import timezone

from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement
from project.models import Project
from project.enums import FilePositioning


class AdvancedReportGenerator:
    """高级报告生成器基类 - 支持深度数据分析"""
    
    def __init__(self, start_date: date, end_date: date, project_codes: Optional[List[str]] = None):
        """
        初始化高级报告生成器
        
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
        self.report_type = 'comprehensive'
        self.report_title = '综合工作报告'
        
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """
        生成综合报告数据（超详细版）
        
        Returns:
            dict: 包含所有详细报告数据的字典
        """
        return {
            'meta': self._get_report_meta(),
            'executive_summary': self._get_executive_summary(),
            'organizational_overview': self._get_organizational_overview(),
            'projects_analysis': self._get_projects_deep_analysis(),
            'procurement_comprehensive': self._get_procurement_comprehensive_analysis(),
            'contract_comprehensive': self._get_contract_comprehensive_analysis(),
            'payment_comprehensive': self._get_payment_comprehensive_analysis(),
            'settlement_comprehensive': self._get_settlement_comprehensive_analysis(),
            'financial_analysis': self._get_financial_analysis(),
            'risk_assessment': self._get_risk_assessment(),
            'performance_indicators': self._get_performance_indicators(),
            'trend_analysis': self._get_trend_analysis(),
            'comparative_analysis': self._get_comparative_analysis(),
            'recommendations': self._get_detailed_recommendations(),
            'appendix': self._get_appendix_data(),
        }
    
    def _get_report_meta(self) -> Dict[str, Any]:
        """获取报告元信息"""
        meta = {
            'generated_at': timezone.now(),
            'period_start': self.start_date,
            'period_end': self.end_date,
            'report_type': self.report_type,
            'report_title': self.report_title,
            'report_scope': self._determine_scope(),
            'reporting_unit': '项目采购与成本管理部门',
            'confidentiality_level': '内部使用',
        }
        
        # 添加项目相关信息
        if self.is_single_project:
            project = Project.objects.filter(project_code=self.project_codes[0]).first()
            if project:
                meta['project_info'] = {
                    'project_code': project.project_code,
                    'project_name': project.project_name,
                    'project_manager': project.project_manager or '未指定',
                    'project_status': project.status,
                    'project_description': project.description or '',
                }
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
        """确定报告范围描述"""
        if self.is_single_project:
            return '单项目'
        elif self.is_multi_project:
            return f'多项目（{len(self.project_codes)}个）'
        else:
            return '全部项目'
    
    def _get_executive_summary(self) -> Dict[str, Any]:
        """生成执行摘要 - 高管视角的关键信息"""
        # 获取核心数据
        procurements = self._get_procurement_queryset()
        contracts = self._get_contract_queryset()
        payments = self._get_payment_queryset()
        settlements = self._get_settlement_queryset()
        
        # 统计核心指标
        procurement_count = procurements.count()
        contract_count = contracts.count()
        payment_count = payments.count()
        settlement_count = settlements.count()
        
        total_budget = procurements.aggregate(total=Sum('budget_amount'))['total'] or Decimal('0')
        total_winning = procurements.aggregate(total=Sum('winning_amount'))['total'] or Decimal('0')
        total_contract = contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
        total_payment = payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
        total_settlement = settlements.aggregate(total=Sum('final_amount'))['total'] or Decimal('0')
        
        # 计算衍生指标
        savings_amount = total_budget - total_winning
        savings_rate = (savings_amount / total_budget * 100) if total_budget > 0 else 0
        payment_rate = (total_payment / total_contract * 100) if total_contract > 0 else 0
        
        return {
            'period_description': self._get_period_description(),
            'scope_description': self._get_scope_description(),
            'core_achievements': {
                'procurement_count': procurement_count,
                'contract_count': contract_count,
                'payment_count': payment_count,
                'settlement_count': settlement_count,
            },
            'financial_summary': {
                'total_budget': float(total_budget),
                'total_winning': float(total_winning),
                'savings_amount': float(savings_amount),
                'savings_rate': float(savings_rate),
                'total_contract': float(total_contract),
                'total_payment': float(total_payment),
                'payment_rate': float(payment_rate),
                'total_settlement': float(total_settlement),
            },
            'highlights': self._get_highlights(),
            'challenges': self._get_challenges(),
        }
    
    def _get_period_description(self) -> str:
        """获取期间描述"""
        days = (self.end_date - self.start_date).days + 1
        months = days / 30
        
        if days <= 7:
            return f"本周（{self.start_date}至{self.end_date}，共{days}天）"
        elif days <= 31:
            return f"本月（{self.start_date}至{self.end_date}，共{days}天）"
        elif days <= 93:
            return f"本季度（{self.start_date}至{self.end_date}，共{int(months)}个月）"
        else:
            return f"本年度（{self.start_date}至{self.end_date}，共{int(months)}个月）"
    
    def _get_scope_description(self) -> str:
        """获取范围描述"""
        if self.is_single_project:
            project = Project.objects.filter(project_code=self.project_codes[0]).first()
            if project:
                return f"本报告聚焦于{project.project_name}（项目编码：{project.project_code}）"
            return f"本报告聚焦于指定项目（项目编码：{self.project_codes[0]}）"
        elif self.is_multi_project:
            return f"本报告涵盖{len(self.project_codes)}个重点项目"
        else:
            total_projects = Project.objects.count()
            return f"本报告涵盖所有在管项目（共{total_projects}个）"
    
    def _get_highlights(self) -> List[str]:
        """获取亮点成就 - 增强版，基于数据智能生成"""
        highlights = []
        
        # 1. 采购成本控制亮点
        procurements = self._get_procurement_queryset()
        procurement_count = procurements.count()
        total_budget = procurements.aggregate(total=Sum('budget_amount'))['total'] or Decimal('0')
        total_winning = procurements.aggregate(total=Sum('winning_amount'))['total'] or Decimal('0')
        
        if total_budget > 0:
            savings = total_budget - total_winning
            savings_rate = (savings / total_budget * 100)
            if savings_rate >= 15:
                highlights.append(
                    f"✓ 采购成本控制成效卓越：完成采购{procurement_count}项，预算总额{float(total_budget):,.2f}万元，"
                    f"实际中标{float(total_winning):,.2f}万元，节约率高达{savings_rate:.1f}%，"
                    f"累计节约资金{float(savings):,.2f}万元，成本控制能力显著"
                )
            elif savings_rate >= 10:
                highlights.append(
                    f"✓ 采购成本控制成效显著：节约率达到{savings_rate:.1f}%，为单位节约资金{float(savings):,.2f}万元"
                )
            elif savings_rate >= 5:
                highlights.append(
                    f"✓ 采购预算执行合理：节约率{savings_rate:.1f}%，实现了成本的有效控制"
                )
        
        # 2. 业务量亮点
        contracts = self._get_contract_queryset()
        contract_count = contracts.count()
        payments = self._get_payment_queryset()
        payment_count = payments.count()
        
        if procurement_count + contract_count + payment_count >= 50:
            highlights.append(
                f"✓ 业务处理高效有序：期内完成采购{procurement_count}项、签订合同{contract_count}份、"
                f"处理付款{payment_count}笔，工作量饱满，流程规范"
            )
        elif contract_count >= 20:
            highlights.append(
                f"✓ 合同管理规范有序：期内签订合同{contract_count}份，合同台账清晰完整，履约管理到位"
            )
        
        # 3. 付款效率亮点
        if payments.exists():
            avg_days = self._calculate_average_payment_cycle()
            total_payment = payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
            
            if avg_days and avg_days <= 10:
                highlights.append(
                    f"✓ 资金支付高效及时：平均付款周期仅{avg_days:.0f}天，累计支付{float(total_payment):,.2f}万元，"
                    f"有效保障了供应商权益和项目进度"
                )
            elif avg_days and avg_days <= 20:
                highlights.append(
                    f"✓ 资金支付效率良好：平均付款周期{avg_days:.0f}天，支付流程规范高效"
                )
        
        # 4. 归档管理亮点
        archive_rate = self._calculate_archive_rate()
        if archive_rate >= 95:
            highlights.append(
                f"✓ 资料归档管理优秀：归档率高达{archive_rate:.1f}%，档案管理规范完整，为后续审计和查阅提供了有力保障"
            )
        elif archive_rate >= 85:
            highlights.append(
                f"✓ 资料归档管理规范：归档率达到{archive_rate:.1f}%，确保了资料的完整性和可追溯性"
            )
        
        # 5. 采购方式多样化亮点
        method_count = procurements.values('procurement_method').distinct().count()
        if method_count >= 4:
            highlights.append(
                f"✓ 采购方式灵活多样：采用{method_count}种采购方式，因项目制宜，既保证了公开公平，又提高了效率"
            )
        
        # 6. 结算效率亮点
        settlements = self._get_settlement_queryset()
        settlement_count = settlements.count()
        if settlement_count >= 5:
            # 计算审减金额（合同金额 - 结算金额）
            total_reduction = Decimal('0')
            for settlement in settlements:
                if settlement.main_contract:
                    contract_amount = settlement.get_total_contract_amount()
                    total_reduction += (contract_amount - settlement.final_amount)
            
            if total_reduction > 0:
                highlights.append(
                    f"✓ 结算审核严格规范：完成结算{settlement_count}笔，通过审核核减不合理费用{float(total_reduction):,.2f}万元，"
                    f"有效控制了工程成本"
                )
        
        # 7. 大额项目管理亮点
        large_contracts = contracts.filter(contract_amount__gte=100).count()
        if large_contracts >= 3:
            highlights.append(
                f"✓ 重大项目管理有力：成功签订{large_contracts}个百万元以上大额合同，项目管理能力强"
            )
        
        return highlights or ["本期各项工作稳步推进，业务流程规范有序"]
    
    def _get_challenges(self) -> List[str]:
        """获取面临的挑战 - 增强版，智能识别问题"""
        challenges = []
        
        # 1. 采购周期问题
        procurements = self._get_procurement_queryset()
        total_procurements = procurements.count()
        
        overdue_procurements = procurements.filter(
            planned_completion_date__lt=F('result_publicity_release_date')
        ).count()
        
        if overdue_procurements > 0:
            overdue_rate = (overdue_procurements / total_procurements * 100) if total_procurements > 0 else 0
            if overdue_rate >= 30:
                challenges.append(
                    f"• 采购周期管理亟需改进：{overdue_procurements}项采购超期完成（占比{overdue_rate:.1f}%），"
                    f"建议优化采购流程、加强进度管控，缩短采购周期"
                )
            elif overdue_rate >= 15:
                challenges.append(
                    f"• 部分采购项目超期：{overdue_procurements}项采购超过计划完成时间，需加强过程监控"
                )
        
        # 2. 归档管理问题
        archive_rate = self._calculate_archive_rate()
        if archive_rate < 70:
            unarchived_count = int((1 - archive_rate/100) * (total_procurements + self._get_contract_queryset().count()))
            challenges.append(
                f"• 归档管理存在较大不足：归档率仅{archive_rate:.1f}%，约{unarchived_count}项业务资料未及时归档，"
                f"存在资料丢失风险，需建立定期提醒和考核机制"
            )
        elif archive_rate < 85:
            challenges.append(
                f"• 资料归档有待加强：归档率{archive_rate:.1f}%，需提高归档及时性，确保资料完整"
            )
        
        # 3. 付款进度问题
        contracts = self._get_contract_queryset()
        payments = self._get_payment_queryset()
        total_contract = contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
        total_payment = payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
        
        if total_contract > 0:
            payment_rate = (total_payment / total_contract * 100)
            unpaid_amount = total_contract - total_payment
            
            if payment_rate < 40:
                challenges.append(
                    f"• 付款进度明显滞后：累计付款进度仅{payment_rate:.1f}%，尚有{float(unpaid_amount):,.2f}万元待支付，"
                    f"可能影响供应商信心和项目进度，需加强资金筹措和支付计划"
                )
            elif payment_rate < 60:
                challenges.append(
                    f"• 付款进度需要加快：当前付款进度{payment_rate:.1f}%，建议优化资金安排，加快支付节奏"
                )
        
        # 4. 平均付款周期问题
        avg_cycle = self._calculate_average_payment_cycle()
        if avg_cycle and avg_cycle > 30:
            challenges.append(
                f"• 付款周期偏长：平均付款周期达{avg_cycle:.0f}天，超出合理范围，"
                f"建议简化审批流程，提高资金支付效率"
            )
        elif avg_cycle and avg_cycle > 20:
            challenges.append(
                f"• 付款效率有待提升：平均付款周期{avg_cycle:.0f}天，建议优化支付流程"
            )
        
        # 5. 采购节约率问题
        total_budget = procurements.aggregate(total=Sum('budget_amount'))['total'] or Decimal('0')
        total_winning = procurements.aggregate(total=Sum('winning_amount'))['total'] or Decimal('0')
        
        if total_budget > 0:
            savings_rate = ((total_budget - total_winning) / total_budget * 100)
            if savings_rate < 3:
                challenges.append(
                    f"• 成本节约空间有限：采购节约率仅{savings_rate:.1f}%，"
                    f"建议加强市场调研和供应商管理，提升议价能力"
                )
        
        # 6. 供应商集中度风险
        supplier_stats = procurements.values('winning_bidder').annotate(
            total=Sum('winning_amount')
        ).order_by('-total')
        
        if supplier_stats.exists():
            top_supplier_amount = supplier_stats[0]['total'] or Decimal('0')
            concentration_rate = (top_supplier_amount / total_winning * 100) if total_winning > 0 else 0
            
            if concentration_rate > 40:
                challenges.append(
                    f"• 供应商集中度较高：单一供应商占比{concentration_rate:.1f}%，存在供应链风险，"
                    f"建议拓展供应商资源，降低依赖度"
                )
        
        # 7. 结算进度问题
        settlements = self._get_settlement_queryset()
        settlement_count = settlements.count()
        contract_count = contracts.count()
        
        if contract_count > 0:
            settlement_rate = (settlement_count / contract_count * 100)
            if settlement_rate < 30 and contract_count >= 10:
                challenges.append(
                    f"• 结算工作相对滞后：结算完成率{settlement_rate:.1f}%，需加快结算审核进度，"
                    f"及时完成项目闭环管理"
                )
        
        return challenges or ["当前各项工作运行平稳，未发现重大风险和挑战"]
    
    def _get_organizational_overview(self) -> Dict[str, Any]:
        """组织概览 - 部门/单位的组织架构和职责"""
        return {
            'department_name': '项目采购与成本管理部门',
            'mission': '负责项目采购活动的组织实施、合同管理、成本控制及资金支付管理',
            'core_responsibilities': [
                '采购需求管理与采购计划编制',
                '采购活动组织实施（招标、询价、谈判等）',
                '合同签订、履约管理及变更管理',
                '资金支付审核与执行',
                '成本分析与结算管理',
                '供应商关系管理与评价',
                '采购档案管理',
            ],
            'team_structure': self._get_team_structure(),
            'work_principles': [
                '依法合规：严格执行《招标投标法》等法律法规',
                '公开透明：确保采购过程公开公平公正',
                '成本控制：合理控制采购成本，提高资金使用效益',
                '规范管理：建立健全管理制度，规范业务流程',
                '效率优先：优化流程，提高采购效率',
            ],
        }
    
    def _get_team_structure(self) -> Dict[str, Any]:
        """团队结构分析"""
        # 统计采购经办人
        procurements = self._get_procurement_queryset()
        officers = procurements.values('procurement_officer').annotate(
            count=Count('procurement_code')
        ).order_by('-count')
        
        return {
            'procurement_officers': [
                {'name': item['procurement_officer'] or '未指定', 'count': item['count']}
                for item in officers[:10]
            ],
            'total_officers': officers.count(),
        }
    
    def _get_projects_deep_analysis(self) -> Dict[str, Any]:
        """项目深度分析"""
        if self.is_single_project:
            return self._get_single_project_analysis()
        else:
            return self._get_multi_projects_analysis()
    
    def _get_single_project_analysis(self) -> Dict[str, Any]:
        """单个项目的深度分析"""
        project = Project.objects.filter(project_code=self.project_codes[0]).first()
        if not project:
            return {}
        
        # 项目全生命周期数据
        procurements = Procurement.objects.filter(project=project)
        contracts = Contract.objects.filter(project=project)
        payments = Payment.objects.filter(contract__project=project)
        settlements = Settlement.objects.filter(main_contract__project=project)
        
        return {
            'basic_info': {
                'code': project.project_code,
                'name': project.project_name,
                'manager': project.project_manager or '未指定',
                'status': project.status,
                'description': project.description or '暂无描述',
                'created_at': project.created_at,
            },
            'lifecycle_stats': {
                'total_procurements': procurements.count(),
                'total_contracts': contracts.count(),
                'total_payments': payments.count(),
                'total_settlements': settlements.count(),
            },
            'financial_overview': self._get_project_financial_overview(project),
            'timeline_analysis': self._get_project_timeline(project),
            'risk_points': self._get_project_risks(project),
        }
    
    def _get_multi_projects_analysis(self) -> Dict[str, Any]:
        """多项目对比分析"""
        queryset = Project.objects.all()
        if self.project_codes:
            queryset = queryset.filter(project_code__in=self.project_codes)
        
        projects_data = []
        for project in queryset:
            procurements = Procurement.objects.filter(project=project)
            contracts = Contract.objects.filter(project=project)
            
            total_contract = contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
            total_payment = Payment.objects.filter(contract__project=project).aggregate(
                total=Sum('payment_amount'))['total'] or Decimal('0')
            
            projects_data.append({
                'code': project.project_code,
                'name': project.project_name,
                'status': project.status,
                'procurement_count': procurements.count(),
                'contract_count': contracts.count(),
                'contract_amount': float(total_contract),
                'payment_amount': float(total_payment),
                'payment_rate': (float(total_payment) / float(total_contract) * 100) if total_contract > 0 else 0,
            })
        
        # 按合同金额排序
        projects_data.sort(key=lambda x: x['contract_amount'], reverse=True)
        
        return {
            'total_count': len(projects_data),
            'projects': projects_data,
            'summary': {
                'total_procurement': sum(p['procurement_count'] for p in projects_data),
                'total_contract': sum(p['contract_count'] for p in projects_data),
                'total_amount': sum(p['contract_amount'] for p in projects_data),
                'total_payment': sum(p['payment_amount'] for p in projects_data),
            }
        }
    
    # === 辅助查询方法 ===
    
    def _get_procurement_queryset(self):
        """获取采购查询集"""
        qs = Procurement.objects.filter(
            result_publicity_release_date__gte=self.start_date,
            result_publicity_release_date__lte=self.end_date
        )
        if self.project_codes:
            qs = qs.filter(project__project_code__in=self.project_codes)
        return qs
    
    def _get_contract_queryset(self):
        """获取合同查询集"""
        qs = Contract.objects.filter(
            signing_date__gte=self.start_date,
            signing_date__lte=self.end_date
        )
        if self.project_codes:
            qs = qs.filter(project__project_code__in=self.project_codes)
        return qs
    
    def _get_payment_queryset(self):
        """获取付款查询集"""
        qs = Payment.objects.filter(
            payment_date__gte=self.start_date,
            payment_date__lte=self.end_date
        )
        if self.project_codes:
            qs = qs.filter(contract__project__project_code__in=self.project_codes)
        return qs
    
    def _get_settlement_queryset(self):
        """获取结算查询集"""
        qs = Settlement.objects.filter(
            completion_date__gte=self.start_date,
            completion_date__lte=self.end_date
        )
        if self.project_codes:
            qs = qs.filter(main_contract__project__project_code__in=self.project_codes)
        return qs
    
    # === 计算方法 ===
    
    def _calculate_average_payment_cycle(self) -> Optional[float]:
        """计算平均付款周期（从合同签订到付款的平均天数）"""
        payments = self._get_payment_queryset().select_related('contract')
        
        total_days = 0
        count = 0
        
        for payment in payments:
            if payment.contract and payment.contract.signing_date:
                days = (payment.payment_date - payment.contract.signing_date).days
                if days >= 0:
                    total_days += days
                    count += 1
        
        return (total_days / count) if count > 0 else None
    
    def _calculate_archive_rate(self) -> float:
        """计算归档率"""
        procurements = self._get_procurement_queryset()
        contracts = self._get_contract_queryset()
        
        total = procurements.count() + contracts.count()
        if total == 0:
            return 100.0
        
        archived = procurements.filter(archive_date__isnull=False).count() + \
                   contracts.filter(archive_date__isnull=False).count()
        
        return (archived / total * 100)
    
    def _get_project_financial_overview(self, project) -> Dict[str, Any]:
        """项目财务概览"""
        contracts = Contract.objects.filter(project=project)
        payments = Payment.objects.filter(contract__project=project)
        
        total_contract = contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
        total_paid = payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
        
        return {
            'contract_amount': float(total_contract),
            'paid_amount': float(total_paid),
            'remaining_amount': float(total_contract - total_paid),
            'payment_progress': (float(total_paid) / float(total_contract) * 100) if total_contract > 0 else 0,
        }
    
    def _get_project_timeline(self, project) -> List[Dict[str, Any]]:
        """项目时间线"""
        timeline = []
        
        # 采购事件
        procurements = Procurement.objects.filter(project=project).order_by('result_publicity_release_date')
        for p in procurements[:10]:
            timeline.append({
                'date': p.result_publicity_release_date,
                'type': '采购',
                'description': f"{p.project_name} 完成采购，中标金额{float(p.winning_amount or 0):,.2f}万元"
            })
        
        # 合同事件
        contracts = Contract.objects.filter(project=project).order_by('signing_date')
        for c in contracts[:10]:
            timeline.append({
                'date': c.signing_date,
                'type': '合同',
                'description': f"签订{c.contract_name}，合同金额{float(c.contract_amount or 0):,.2f}万元"
            })
        
        # 按日期排序
        timeline.sort(key=lambda x: x['date'] if x['date'] else date.min)
        
        return timeline
    
    def _get_project_risks(self, project) -> List[str]:
        """项目风险点"""
        risks = []
        
        # 检查逾期归档
        procurements = Procurement.objects.filter(project=project, archive_date__isnull=True)
        if procurements.count() > 0:
            risks.append(f"存在{procurements.count()}项采购资料未归档")
        
        # 检查付款进度
        financial = self._get_project_financial_overview(project)
        if financial['payment_progress'] < 30:
            risks.append(f"付款进度较低({financial['payment_progress']:.1f}%)，可能影响供应商关系")
        
        return risks or ["暂无明显风险点"]
    
    # === 综合分析方法（占位符，需要完整实现）===
    
    def _get_procurement_comprehensive_analysis(self) -> Dict[str, Any]:
        """采购综合分析 - 完整版"""
        procurements = self._get_procurement_queryset()
        
        # 基础统计
        total_count = procurements.count()
        total_budget = procurements.aggregate(total=Sum('budget_amount'))['total'] or Decimal('0')
        total_winning = procurements.aggregate(total=Sum('winning_amount'))['total'] or Decimal('0')
        savings = total_budget - total_winning
        savings_rate = (savings / total_budget * 100) if total_budget > 0 else 0
        
        # 按采购方式统计
        by_method = {}
        for method_value, method_name in [
            ('公开招标', '公开招标'),
            ('邀请招标', '邀请招标'),
            ('竞争性谈判', '竞争性谈判'),
            ('竞争性磋商', '竞争性磋商'),
            ('询价', '询价'),
            ('单一来源', '单一来源'),
        ]:
            qs = procurements.filter(procurement_method=method_value)
            count = qs.count()
            if count > 0:
                by_method[method_name] = {
                    'count': count,
                    'budget': float(qs.aggregate(total=Sum('budget_amount'))['total'] or 0),
                    'winning': float(qs.aggregate(total=Sum('winning_amount'))['total'] or 0),
                    'percentage': (count / total_count * 100) if total_count > 0 else 0,
                }
        
        # 按采购类型统计
        by_type = {}
        for type_value, type_name in [
            ('货物', '货物类'),
            ('服务', '服务类'),
            ('工程', '工程类'),
        ]:
            qs = procurements.filter(procurement_type=type_value)
            count = qs.count()
            if count > 0:
                by_type[type_name] = {
                    'count': count,
                    'budget': float(qs.aggregate(total=Sum('budget_amount'))['total'] or 0),
                    'winning': float(qs.aggregate(total=Sum('winning_amount'))['total'] or 0),
                    'percentage': (count / total_count * 100) if total_count > 0 else 0,
                }
        
        # Top 10 大额采购
        top_procurements = procurements.order_by('-winning_amount')[:10]
        top_list = [{
            'code': p.procurement_code,
            'name': p.project_name,
            'method': p.procurement_method or '未知',
            'winning_bidder': p.winning_bidder or '未知',
            'budget': float(p.budget_amount or 0),
            'winning': float(p.winning_amount or 0),
            'savings': float((p.budget_amount or 0) - (p.winning_amount or 0)),
            'savings_rate': (((p.budget_amount or 0) - (p.winning_amount or 0)) / p.budget_amount * 100) if p.budget_amount and p.budget_amount > 0 else 0,
        } for p in top_procurements]
        
        # 采购周期分析
        cycle_data = []
        for p in procurements:
            if p.planned_completion_date and p.result_publicity_release_date:
                days = (p.result_publicity_release_date - p.planned_completion_date).days
                cycle_data.append(days)
        
        avg_cycle = sum(cycle_data) / len(cycle_data) if cycle_data else 0
        max_cycle = max(cycle_data) if cycle_data else 0
        min_cycle = min(cycle_data) if cycle_data else 0
        overdue_count = len([d for d in cycle_data if d > 0])
        
        # 供应商集中度分析
        supplier_stats = procurements.values('winning_bidder').annotate(
            count=Count('procurement_code'),
            total_amount=Sum('winning_amount')
        ).order_by('-total_amount')[:10]
        
        top_suppliers = [{
            'name': item['winning_bidder'] or '未知',
            'count': item['count'],
            'amount': float(item['total_amount'] or 0),
            'percentage': (float(item['total_amount'] or 0) / float(total_winning) * 100) if total_winning > 0 else 0,
        } for item in supplier_stats]
        
        return {
            'overview': {
                'total_count': total_count,
                'total_budget': float(total_budget),
                'total_winning': float(total_winning),
                'total_savings': float(savings),
                'savings_rate': float(savings_rate),
            },
            'by_method': by_method,
            'by_type': by_type,
            'top_procurements': top_list,
            'cycle_analysis': {
                'average_days': avg_cycle,
                'max_days': max_cycle,
                'min_days': min_cycle,
                'overdue_count': overdue_count,
                'overdue_rate': (overdue_count / len(cycle_data) * 100) if cycle_data else 0,
            },
            'supplier_concentration': {
                'top_suppliers': top_suppliers,
                'total_suppliers': procurements.values('winning_bidder').distinct().count(),
            },
        }
    
    def _get_contract_comprehensive_analysis(self) -> Dict[str, Any]:
        """合同综合分析 - 完整版"""
        contracts = self._get_contract_queryset()
        
        # 基础统计
        total_count = contracts.count()
        total_amount = contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
        
        # 按文件定位（合同类型）统计
        by_type = {}
        for positioning in FilePositioning:
            qs = contracts.filter(file_positioning=positioning.value)
            count = qs.count()
            if count > 0:
                by_type[positioning.label] = {
                    'count': count,
                    'amount': float(qs.aggregate(total=Sum('contract_amount'))['total'] or 0),
                    'percentage': (count / total_count * 100) if total_count > 0 else 0,
                }
        
        # 按甲方统计
        party_a_stats = contracts.values('party_a').annotate(
            count=Count('contract_code'),
            total=Sum('contract_amount')
        ).order_by('-total')[:10]
        
        by_party_a = [{
            'name': item['party_a'] or '未知',
            'count': item['count'],
            'amount': float(item['total'] or 0),
        } for item in party_a_stats]
        
        # 按乙方统计
        party_b_stats = contracts.values('party_b').annotate(
            count=Count('contract_code'),
            total=Sum('contract_amount')
        ).order_by('-total')[:10]
        
        by_party_b = [{
            'name': item['party_b'] or '未知',
            'count': item['count'],
            'amount': float(item['total'] or 0),
        } for item in party_b_stats]
        
        # Top 10 大额合同
        top_contracts = contracts.order_by('-contract_amount')[:10]
        top_list = [{
            'code': c.contract_code,
            'name': c.contract_name,
            'party_a': c.party_a or '未知',
            'party_b': c.party_b or '未知',
            'amount': float(c.contract_amount or 0),
            'signing_date': c.signing_date,
            'type': FilePositioning(c.file_positioning).label if c.file_positioning else '未知',
        } for c in top_contracts]
        
        # 签订效率分析（从采购到签订的周期）
        efficiency_data = []
        for contract in contracts.select_related('project'):
            if contract.signing_date:
                # 查找相关采购
                related_procurement = Procurement.objects.filter(
                    project=contract.project,
                    winning_bidder=contract.party_b
                ).first()
                
                if related_procurement and related_procurement.result_publicity_release_date:
                    days = (contract.signing_date - related_procurement.result_publicity_release_date).days
                    if days >= 0:
                        efficiency_data.append(days)
        
        avg_signing_cycle = sum(efficiency_data) / len(efficiency_data) if efficiency_data else 0
        
        # 履约状态分析（基于付款情况）
        contracts_with_payment = 0
        fully_paid_contracts = 0
        
        for contract in contracts:
            payments = Payment.objects.filter(contract=contract)
            if payments.exists():
                contracts_with_payment += 1
                total_paid = payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
                if contract.contract_amount and total_paid >= contract.contract_amount:
                    fully_paid_contracts += 1
        
        return {
            'overview': {
                'total_count': total_count,
                'total_amount': float(total_amount),
                'avg_amount': float(total_amount / total_count) if total_count > 0 else 0,
            },
            'by_type': by_type,
            'by_party_a': by_party_a,
            'by_party_b': by_party_b,
            'top_contracts': top_list,
            'efficiency_analysis': {
                'avg_signing_cycle_days': avg_signing_cycle,
                'total_analyzed': len(efficiency_data),
            },
            'performance_status': {
                'contracts_with_payment': contracts_with_payment,
                'fully_paid_contracts': fully_paid_contracts,
                'payment_rate': (contracts_with_payment / total_count * 100) if total_count > 0 else 0,
                'completion_rate': (fully_paid_contracts / total_count * 100) if total_count > 0 else 0,
            },
        }
    
    def _get_payment_comprehensive_analysis(self) -> Dict[str, Any]:
        """付款综合分析 - 完整版"""
        payments = self._get_payment_queryset()
        
        # 基础统计
        total_count = payments.count()
        total_amount = payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
        
        # 计算合同总额（用于计算付款进度）
        contract_ids = payments.values_list('contract_id', flat=True).distinct()
        related_contracts = Contract.objects.filter(id__in=contract_ids)
        total_contract_amount = related_contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
        
        # 按付款类型统计
        by_type = {}
        payment_types = payments.values('payment_type').annotate(
            count=Count('payment_code'),
            total=Sum('payment_amount')
        ).order_by('-total')
        
        for item in payment_types:
            type_name = item['payment_type'] or '未指定'
            by_type[type_name] = {
                'count': item['count'],
                'amount': float(item['total'] or 0),
                'percentage': (item['count'] / total_count * 100) if total_count > 0 else 0,
            }
        
        # Top 10 大额付款
        top_payments = payments.select_related('contract').order_by('-payment_amount')[:10]
        top_list = [{
            'code': p.payment_code,
            'contract_code': p.contract.contract_code if p.contract else '未知',
            'contract_name': p.contract.contract_name if p.contract else '未知',
            'party_b': p.contract.party_b if p.contract else '未知',
            'amount': float(p.payment_amount or 0),
            'payment_date': p.payment_date,
        } for p in top_payments]
        
        # 付款周期分析
        cycle_data = []
        for payment in payments.select_related('contract'):
            if payment.contract and payment.contract.signing_date and payment.payment_date:
                days = (payment.payment_date - payment.contract.signing_date).days
                if days >= 0:
                    cycle_data.append(days)
        
        avg_cycle = sum(cycle_data) / len(cycle_data) if cycle_data else 0
        max_cycle = max(cycle_data) if cycle_data else 0
        min_cycle = min(cycle_data) if cycle_data else 0
        
        # 资金使用效率
        total_days = (self.end_date - self.start_date).days + 1
        daily_avg = float(total_amount) / total_days if total_days > 0 else 0
        
        # 收款方集中度
        payee_stats = payments.values('payee').annotate(
            count=Count('payment_code'),
            total=Sum('payment_amount')
        ).order_by('-total')[:10]
        
        top_payees = [{
            'name': item['payee'] or '未知',
            'count': item['count'],
            'amount': float(item['total'] or 0),
            'percentage': (float(item['total'] or 0) / float(total_amount) * 100) if total_amount > 0 else 0,
        } for item in payee_stats]
        
        return {
            'overview': {
                'total_count': total_count,
                'total_amount': float(total_amount),
                'total_contract_amount': float(total_contract_amount),
                'payment_progress': (float(total_amount) / float(total_contract_amount) * 100) if total_contract_amount > 0 else 0,
                'avg_payment': float(total_amount / total_count) if total_count > 0 else 0,
            },
            'by_type': by_type,
            'top_payments': top_list,
            'cycle_analysis': {
                'average_days': avg_cycle,
                'max_days': max_cycle,
                'min_days': min_cycle,
                'total_analyzed': len(cycle_data),
            },
            'efficiency_metrics': {
                'daily_average': daily_avg,
                'period_days': total_days,
            },
            'payee_concentration': {
                'top_payees': top_payees,
                'total_payees': payments.values('payee').distinct().count(),
            },
        }
    
    def _get_settlement_comprehensive_analysis(self) -> Dict[str, Any]:
        """结算综合分析 - 完整版"""
        settlements = self._get_settlement_queryset()
        
        # 基础统计
        total_count = settlements.count()
        total_final = settlements.aggregate(total=Sum('final_amount'))['total'] or Decimal('0')
        
        # 计算初始金额（合同金额+补充协议金额）
        total_initial = Decimal('0')
        for settlement in settlements:
            if settlement.main_contract:
                total_initial += settlement.get_total_contract_amount()
        
        # 审减金额和审减率
        audit_reduction = total_initial - total_final
        audit_reduction_rate = (audit_reduction / total_initial * 100) if total_initial > 0 else 0
        
        # 结算完成情况分析
        completed_settlements = settlements.filter(completion_date__isnull=False).count()
        completion_rate = (completed_settlements / total_count * 100) if total_count > 0 else 0
        
        # 结算周期分析（从合同签订到结算完成）
        cycle_data = []
        for settlement in settlements.select_related('main_contract'):
            if settlement.completion_date and settlement.main_contract and settlement.main_contract.signing_date:
                days = (settlement.completion_date - settlement.main_contract.signing_date).days
                if days >= 0:
                    cycle_data.append(days)
        
        avg_cycle = sum(cycle_data) / len(cycle_data) if cycle_data else 0
        max_cycle = max(cycle_data) if cycle_data else 0
        min_cycle = min(cycle_data) if cycle_data else 0
        
        # Top 10 大额结算
        top_settlements = settlements.select_related('main_contract').order_by('-final_amount')[:10]
        top_list = []
        for s in top_settlements:
            initial_amount = s.get_total_contract_amount() if s.main_contract else Decimal('0')
            final_amount = s.final_amount or Decimal('0')
            reduction = initial_amount - final_amount
            top_list.append({
                'code': s.settlement_code,
                'contract_code': s.main_contract.contract_code if s.main_contract else '未知',
                'contract_name': s.main_contract.contract_name if s.main_contract else '未知',
                'initial_amount': float(initial_amount),
                'final_amount': float(final_amount),
                'reduction': float(reduction),
                'reduction_rate': (float(reduction) / float(initial_amount) * 100) if initial_amount > 0 else 0,
                'completion_date': s.completion_date,
            })
        
        # 与合同金额对比
        contract_ids = settlements.values_list('main_contract_id', flat=True).distinct()
        related_contracts = Contract.objects.filter(id__in=contract_ids)
        total_contract_amount = related_contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
        
        settlement_vs_contract = (total_final / total_contract_amount * 100) if total_contract_amount > 0 else 0
        
        return {
            'overview': {
                'total_count': total_count,
                'total_initial_amount': float(total_initial),
                'total_final_amount': float(total_final),
                'total_audit_reduction': float(audit_reduction),
                'audit_reduction_rate': float(audit_reduction_rate),
                'completed_count': completed_settlements,
                'completion_rate': completion_rate,
            },
            'cycle_analysis': {
                'average_days': avg_cycle,
                'max_days': max_cycle,
                'min_days': min_cycle,
                'total_analyzed': len(cycle_data),
            },
            'top_settlements': top_list,
            'contract_comparison': {
                'total_contract_amount': float(total_contract_amount),
                'settlement_vs_contract_rate': settlement_vs_contract,
            },
            'efficiency_assessment': {
                'avg_reduction_per_settlement': float(audit_reduction / total_count) if total_count > 0 else 0,
                'total_savings': float(audit_reduction),
            },
        }
    
    def _get_financial_analysis(self) -> Dict[str, Any]:
        """财务分析"""
        return {
            'budget_execution': '预算执行分析',
            'cost_control': '成本控制分析',
            'cash_flow': '现金流分析',
        }
    
    def _get_risk_assessment(self) -> Dict[str, Any]:
        """风险评估"""
        return {
            'identified_risks': ['风险1', '风险2'],
            'risk_level': '中等',
            'mitigation_measures': ['措施1', '措施2'],
        }
    
    def _get_performance_indicators(self) -> Dict[str, Any]:
        """绩效指标"""
        return {
            'efficiency': '效率指标',
            'quality': '质量指标',
            'satisfaction': '满意度指标',
        }
    
    def _get_trend_analysis(self) -> Dict[str, Any]:
        """趋势分析 - 完整版"""
        from dateutil.relativedelta import relativedelta
        from collections import defaultdict
        
        # 月度趋势分析
        monthly_data = defaultdict(lambda: {
            'procurement_count': 0,
            'procurement_amount': Decimal('0'),
            'contract_count': 0,
            'contract_amount': Decimal('0'),
            'payment_count': 0,
            'payment_amount': Decimal('0'),
            'settlement_count': 0,
            'settlement_amount': Decimal('0'),
        })
        
        # 采购月度数据
        procurements = self._get_procurement_queryset()
        for p in procurements:
            if p.result_publicity_release_date:
                month_key = p.result_publicity_release_date.strftime('%Y-%m')
                monthly_data[month_key]['procurement_count'] += 1
                monthly_data[month_key]['procurement_amount'] += (p.winning_amount or Decimal('0'))
        
        # 合同月度数据
        contracts = self._get_contract_queryset()
        for c in contracts:
            if c.signing_date:
                month_key = c.signing_date.strftime('%Y-%m')
                monthly_data[month_key]['contract_count'] += 1
                monthly_data[month_key]['contract_amount'] += (c.contract_amount or Decimal('0'))
        
        # 付款月度数据
        payments = self._get_payment_queryset()
        for p in payments:
            if p.payment_date:
                month_key = p.payment_date.strftime('%Y-%m')
                monthly_data[month_key]['payment_count'] += 1
                monthly_data[month_key]['payment_amount'] += (p.payment_amount or Decimal('0'))
        
        # 结算月度数据
        settlements = self._get_settlement_queryset()
        for s in settlements:
            if s.completion_date:
                month_key = s.completion_date.strftime('%Y-%m')
                monthly_data[month_key]['settlement_count'] += 1
                monthly_data[month_key]['settlement_amount'] += (s.final_amount or Decimal('0'))
        
        # 转换为列表并排序
        monthly_trend = []
        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            monthly_trend.append({
                'month': month_key,
                'procurement_count': data['procurement_count'],
                'procurement_amount': float(data['procurement_amount']),
                'contract_count': data['contract_count'],
                'contract_amount': float(data['contract_amount']),
                'payment_count': data['payment_count'],
                'payment_amount': float(data['payment_amount']),
                'settlement_count': data['settlement_count'],
                'settlement_amount': float(data['settlement_amount']),
            })
        
        # 季度趋势分析
        quarterly_data = defaultdict(lambda: {
            'procurement_count': 0,
            'procurement_amount': Decimal('0'),
            'contract_count': 0,
            'contract_amount': Decimal('0'),
            'payment_count': 0,
            'payment_amount': Decimal('0'),
        })
        
        for month_key, data in monthly_data.items():
            year, month = month_key.split('-')
            quarter = (int(month) - 1) // 3 + 1
            quarter_key = f"{year}-Q{quarter}"
            
            quarterly_data[quarter_key]['procurement_count'] += data['procurement_count']
            quarterly_data[quarter_key]['procurement_amount'] += data['procurement_amount']
            quarterly_data[quarter_key]['contract_count'] += data['contract_count']
            quarterly_data[quarter_key]['contract_amount'] += data['contract_amount']
            quarterly_data[quarter_key]['payment_count'] += data['payment_count']
            quarterly_data[quarter_key]['payment_amount'] += data['payment_amount']
        
        quarterly_trend = []
        for quarter_key in sorted(quarterly_data.keys()):
            data = quarterly_data[quarter_key]
            quarterly_trend.append({
                'quarter': quarter_key,
                'procurement_count': data['procurement_count'],
                'procurement_amount': float(data['procurement_amount']),
                'contract_count': data['contract_count'],
                'contract_amount': float(data['contract_amount']),
                'payment_count': data['payment_count'],
                'payment_amount': float(data['payment_amount']),
            })
        
        # 趋势描述
        trend_description = self._generate_trend_description(monthly_trend)
        
        # 高峰和低谷识别
        if monthly_trend:
            peak_month = max(monthly_trend, key=lambda x: x['contract_amount'])
            valley_month = min(monthly_trend, key=lambda x: x['contract_amount'])
        else:
            peak_month = valley_month = None
        
        return {
            'monthly_trend': monthly_trend,
            'quarterly_trend': quarterly_trend,
            'trend_description': trend_description,
            'peak_period': {
                'month': peak_month['month'] if peak_month else None,
                'contract_amount': peak_month['contract_amount'] if peak_month else 0,
            } if peak_month else None,
            'valley_period': {
                'month': valley_month['month'] if valley_month else None,
                'contract_amount': valley_month['contract_amount'] if valley_month else 0,
            } if valley_month else None,
        }
    
    def _generate_trend_description(self, monthly_trend: List[Dict]) -> str:
        """生成趋势描述文本"""
        if not monthly_trend or len(monthly_trend) < 2:
            return "数据不足，无法分析趋势"
        
        # 计算趋势
        first_half = monthly_trend[:len(monthly_trend)//2]
        second_half = monthly_trend[len(monthly_trend)//2:]
        
        first_avg = sum(m['contract_amount'] for m in first_half) / len(first_half) if first_half else 0
        second_avg = sum(m['contract_amount'] for m in second_half) / len(second_half) if second_half else 0
        
        if second_avg > first_avg * 1.1:
            return f"整体呈上升趋势，后期平均合同金额较前期增长{((second_avg/first_avg - 1) * 100):.1f}%"
        elif second_avg < first_avg * 0.9:
            return f"整体呈下降趋势，后期平均合同金额较前期下降{((1 - second_avg/first_avg) * 100):.1f}%"
        else:
            return "整体保持平稳，波动较小"
    
    def _get_comparative_analysis(self) -> Dict[str, Any]:
        """对比分析 - 完整版（同比、环比）"""
        from dateutil.relativedelta import relativedelta
        
        # 同比分析（Year-over-Year）
        yoy_data = self._get_year_over_year_comparison()
        
        # 环比分析（Month-over-Month）
        mom_data = self._get_month_over_month_comparison()
        
        return {
            'year_over_year': yoy_data,
            'month_over_month': mom_data,
            'summary': self._generate_comparison_summary(yoy_data, mom_data),
        }
    
    def _get_year_over_year_comparison(self) -> Dict[str, Any]:
        """同比分析（与去年同期对比）"""
        from dateutil.relativedelta import relativedelta
        
        # 计算去年同期的日期范围
        last_year_start = self.start_date - relativedelta(years=1)
        last_year_end = self.end_date - relativedelta(years=1)
        
        # 当期数据
        current_procurements = self._get_procurement_queryset()
        current_contracts = self._get_contract_queryset()
        current_payments = self._get_payment_queryset()
        
        # 去年同期数据
        last_year_procurements = Procurement.objects.filter(
            result_publicity_release_date__gte=last_year_start,
            result_publicity_release_date__lte=last_year_end
        )
        last_year_contracts = Contract.objects.filter(
            signing_date__gte=last_year_start,
            signing_date__lte=last_year_end
        )
        last_year_payments = Payment.objects.filter(
            payment_date__gte=last_year_start,
            payment_date__lte=last_year_end
        )
        
        if self.project_codes:
            last_year_procurements = last_year_procurements.filter(project__project_code__in=self.project_codes)
            last_year_contracts = last_year_contracts.filter(project__project_code__in=self.project_codes)
            last_year_payments = last_year_payments.filter(contract__project__project_code__in=self.project_codes)
        
        # 统计对比
        comparisons = {
            'procurement': self._compare_periods(
                current_procurements, last_year_procurements, 'winning_amount'
            ),
            'contract': self._compare_periods(
                current_contracts, last_year_contracts, 'contract_amount'
            ),
            'payment': self._compare_periods(
                current_payments, last_year_payments, 'payment_amount'
            ),
        }
        
        return {
            'period_comparison': f"{self.start_date.year}年 vs {last_year_start.year}年同期",
            'has_data': last_year_procurements.exists() or last_year_contracts.exists() or last_year_payments.exists(),
            'procurement_yoy': comparisons['procurement'],
            'contract_yoy': comparisons['contract'],
            'payment_yoy': comparisons['payment'],
        }
    
    def _get_month_over_month_comparison(self) -> Dict[str, Any]:
        """环比分析（与上月对比）"""
        from dateutil.relativedelta import relativedelta
        from calendar import monthrange
        
        # 如果时间跨度不是单月，则不进行环比分析
        days_span = (self.end_date - self.start_date).days + 1
        if days_span > 35:
            return {
                'applicable': False,
                'reason': '时间跨度超过1个月，不适用环比分析'
            }
        
        # 计算上月的日期范围
        last_month_end = self.start_date - timedelta(days=1)
        last_month_start = date(last_month_end.year, last_month_end.month, 1)
        
        # 当月数据
        current_procurements = self._get_procurement_queryset()
        current_contracts = self._get_contract_queryset()
        current_payments = self._get_payment_queryset()
        
        # 上月数据
        last_month_procurements = Procurement.objects.filter(
            result_publicity_release_date__gte=last_month_start,
            result_publicity_release_date__lte=last_month_end
        )
        last_month_contracts = Contract.objects.filter(
            signing_date__gte=last_month_start,
            signing_date__lte=last_month_end
        )
        last_month_payments = Payment.objects.filter(
            payment_date__gte=last_month_start,
            payment_date__lte=last_month_end
        )
        
        if self.project_codes:
            last_month_procurements = last_month_procurements.filter(project__project_code__in=self.project_codes)
            last_month_contracts = last_month_contracts.filter(project__project_code__in=self.project_codes)
            last_month_payments = last_month_payments.filter(contract__project__project_code__in=self.project_codes)
        
        # 统计对比
        comparisons = {
            'procurement': self._compare_periods(
                current_procurements, last_month_procurements, 'winning_amount'
            ),
            'contract': self._compare_periods(
                current_contracts, last_month_contracts, 'contract_amount'
            ),
            'payment': self._compare_periods(
                current_payments, last_month_payments, 'payment_amount'
            ),
        }
        
        return {
            'applicable': True,
            'period_comparison': f"{self.start_date.strftime('%Y年%m月')} vs {last_month_start.strftime('%Y年%m月')}",
            'has_data': last_month_procurements.exists() or last_month_contracts.exists() or last_month_payments.exists(),
            'procurement_mom': comparisons['procurement'],
            'contract_mom': comparisons['contract'],
            'payment_mom': comparisons['payment'],
        }
    
    def _compare_periods(self, current_qs, previous_qs, amount_field: str) -> Dict[str, Any]:
        """对比两个时期的数据"""
        current_count = current_qs.count()
        previous_count = previous_qs.count()
        
        current_amount = current_qs.aggregate(total=Sum(amount_field))['total'] or Decimal('0')
        previous_amount = previous_qs.aggregate(total=Sum(amount_field))['total'] or Decimal('0')
        
        # 计算增长率
        count_growth = ((current_count - previous_count) / previous_count * 100) if previous_count > 0 else 0
        amount_growth = ((current_amount - previous_amount) / previous_amount * 100) if previous_amount > 0 else 0
        
        return {
            'current': {
                'count': current_count,
                'amount': float(current_amount),
            },
            'previous': {
                'count': previous_count,
                'amount': float(previous_amount),
            },
            'growth': {
                'count': count_growth,
                'amount': amount_growth,
                'count_abs': current_count - previous_count,
                'amount_abs': float(current_amount - previous_amount),
            },
            'trend': 'up' if amount_growth > 5 else ('down' if amount_growth < -5 else 'stable'),
        }
    
    def _generate_comparison_summary(self, yoy_data: Dict, mom_data: Dict) -> str:
        """生成对比分析总结"""
        summaries = []
        
        # 同比总结
        if yoy_data.get('has_data'):
            contract_growth = yoy_data['contract_yoy']['growth']['amount']
            if abs(contract_growth) >= 10:
                direction = "增长" if contract_growth > 0 else "下降"
                summaries.append(
                    f"与去年同期相比，合同金额{direction}{abs(contract_growth):.1f}%"
                )
        
        # 环比总结
        if mom_data.get('applicable') and mom_data.get('has_data'):
            contract_growth = mom_data['contract_mom']['growth']['amount']
            if abs(contract_growth) >= 10:
                direction = "增长" if contract_growth > 0 else "下降"
                summaries.append(
                    f"环比上月，合同金额{direction}{abs(contract_growth):.1f}%"
                )
        
        return '；'.join(summaries) if summaries else "数据对比平稳，无明显波动"
    
    def _get_detailed_recommendations(self) -> List[Dict[str, Any]]:
        """智能生成详细建议 - 基于数据分析自动生成"""
        recommendations = []
        
        # 获取挑战列表（已识别的问题）
        challenges = self._get_challenges()
        
        # 1. 基于采购周期问题生成建议
        procurements = self._get_procurement_queryset()
        overdue_procurements = procurements.filter(
            planned_completion_date__lt=F('result_publicity_release_date')
        ).count()
        
        if overdue_procurements > 0:
            total_procurements = procurements.count()
            overdue_rate = (overdue_procurements / total_procurements * 100) if total_procurements > 0 else 0
            
            recommendations.append({
                'category': '采购周期管理',
                'priority': '高' if overdue_rate >= 30 else '中',
                'problem': f'{overdue_procurements}项采购超期完成，超期率{overdue_rate:.1f}%',
                'description': '建议：(1) 优化采购计划编制，合理预估采购周期；(2) 建立采购进度月报制度，及时发现和解决问题；(3) 加强与招标代理机构的沟通协调；(4) 对重复超期的项目进行专项分析',
                'expected_benefit': f'预计可将超期率降至10%以下，节约时间成本约{overdue_procurements * 5}个工作日',
                'implementation_difficulty': '中等',
            })
        
        # 2. 基于归档率问题生成建议
        archive_rate = self._calculate_archive_rate()
        if archive_rate < 85:
            recommendations.append({
                'category': '归档管理',
                'priority': '高' if archive_rate < 70 else '中',
                'problem': f'资料归档率仅{archive_rate:.1f}%，低于85%的目标值',
                'description': '建议：(1) 建立归档清单制度，明确归档时间节点和责任人；(2) 设置系统自动提醒功能，逾期未归档进行预警；(3) 将归档率纳入个人绩效考核；(4) 定期开展归档专项检查',
                'expected_benefit': f'预计可将归档率提升至95%以上，降低资料丢失风险',
                'implementation_difficulty': '简单',
            })
        
        # 3. 基于付款进度问题生成建议
        contracts = self._get_contract_queryset()
        payments = self._get_payment_queryset()
        total_contract = contracts.aggregate(total=Sum('contract_amount'))['total'] or Decimal('0')
        total_payment = payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
        
        if total_contract > 0:
            payment_rate = (total_payment / total_contract * 100)
            if payment_rate < 60:
                unpaid_amount = total_contract - total_payment
                
                recommendations.append({
                    'category': '资金支付管理',
                    'priority': '高' if payment_rate < 40 else '中',
                    'problem': f'付款进度{payment_rate:.1f}%，尚有{float(unpaid_amount):,.2f}万元待支付',
                    'description': '建议：(1) 编制年度/季度资金支付计划，确保资金来源；(2) 优化审批流程，缩短审批周期；(3) 建立付款台账，及时掌握付款需求；(4) 加强与财务部门的协调沟通',
                    'expected_benefit': '预计可将付款进度提升20-30个百分点，改善供应商关系',
                    'implementation_difficulty': '较难（涉及资金筹措）',
                })
        
        # 4. 基于付款周期问题生成建议
        avg_cycle = self._calculate_average_payment_cycle()
        if avg_cycle and avg_cycle > 20:
            recommendations.append({
                'category': '付款效率提升',
                'priority': '中' if avg_cycle <= 30 else '高',
                'problem': f'平均付款周期{avg_cycle:.0f}天，超出合理范围（15-20天）',
                'description': '建议：(1) 简化内部审批流程，推行电子化审批；(2) 建立紧急付款绿色通道；(3) 明确各环节审批时限；(4) 定期分析付款延误原因并改进',
                'expected_benefit': f'预计可将平均周期缩短至20天以内，提高资金使用效率',
                'implementation_difficulty': '中等',
            })
        
        # 5. 基于节约率问题生成建议
        total_budget = procurements.aggregate(total=Sum('budget_amount'))['total'] or Decimal('0')
        total_winning = procurements.aggregate(total=Sum('winning_amount'))['total'] or Decimal('0')
        
        if total_budget > 0:
            savings_rate = ((total_budget - total_winning) / total_budget * 100)
            if savings_rate < 5:
                recommendations.append({
                    'category': '成本控制',
                    'priority': '中',
                    'problem': f'采购节约率仅{savings_rate:.1f}%，成本控制空间有限',
                    'description': '建议：(1) 加强市场调研，准确编制采购预算；(2) 拓展供应商资源，增加竞争性；(3) 建立供应商库，定期评价和优化；(4) 加强合同谈判培训，提升议价能力；(5) 推行集中采购，发挥规模优势',
                    'expected_benefit': '预计可将节约率提升至8-10%，年节约资金数十万元',
                    'implementation_difficulty': '中等',
                })
        
        # 6. 基于供应商集中度问题生成建议
        supplier_stats = procurements.values('winning_bidder').annotate(
            total=Sum('winning_amount')
        ).order_by('-total')
        
        if supplier_stats.exists():
            top_supplier_amount = supplier_stats[0]['total'] or Decimal('0')
            concentration_rate = (top_supplier_amount / total_winning * 100) if total_winning > 0 else 0
            
            if concentration_rate > 40:
                recommendations.append({
                    'category': '供应链风险管理',
                    'priority': '中',
                    'problem': f'单一供应商占比{concentration_rate:.1f}%，集中度过高',
                    'description': '建议：(1) 拓展供应商资源，建立备选供应商库；(2) 对大额采购推行"不少于3家"的竞争性原则；(3) 加强供应商履约评价，及时调整合作名单；(4) 对关键物资建立双供应商机制',
                    'expected_benefit': '降低供应链中断风险，提高议价能力',
                    'implementation_difficulty': '中等',
                })
        
        # 7. 基于结算进度问题生成建议
        settlements = self._get_settlement_queryset()
        settlement_count = settlements.count()
        contract_count = contracts.count()
        
        if contract_count > 0:
            settlement_rate = (settlement_count / contract_count * 100)
            if settlement_rate < 30 and contract_count >= 10:
                recommendations.append({
                    'category': '结算管理',
                    'priority': '中',
                    'problem': f'结算完成率{settlement_rate:.1f}%，进度相对滞后',
                    'description': '建议：(1) 建立结算台账，明确各项目结算时间节点；(2) 加强与施工/供货单位的协调，及时收集结算资料；(3) 提前介入工程验收，同步推进结算工作；(4) 对长期未结算项目进行专项清理',
                    'expected_benefit': '加快资金闭环管理，及时释放项目资金占用',
                    'implementation_difficulty': '中等',
                })
        
        # 8. 通用改进建议（如果没有发现明显问题）
        if not recommendations:
            recommendations.append({
                'category': '持续改进',
                'priority': '中',
                'problem': '当前业务运行平稳，但仍有优化空间',
                'description': '建议：(1) 推进采购管理信息化建设，提高工作效率；(2) 加强业务人员培训，提升专业能力；(3) 完善内控制度，防范廉政风险；(4) 建立数据分析机制，定期开展业务分析',
                'expected_benefit': '提升管理水平，预防潜在风险',
                'implementation_difficulty': '中等',
            })
        
        return recommendations
    
    def _get_appendix_data(self) -> Dict[str, Any]:
        """附录数据"""
        return {
            'data_sources': '数据来源说明',
            'methodology': '分析方法说明',
            'glossary': '术语表',
        }


# === 年度报告生成器 ===

class AnnualComprehensiveReportGenerator(AdvancedReportGenerator):
    """年度综合报告生成器"""
    
    def __init__(self, year: int, project_codes: Optional[List[str]] = None):
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        super().__init__(start_date, end_date, project_codes)
        self.year = year
        self.report_type = 'annual_comprehensive'
        self.report_title = f'{year}年度工作总结报告'


# === 部门报告生成器 ===

class DepartmentReportGenerator(AdvancedReportGenerator):
    """部门总结报告生成器"""
    
    def __init__(self, start_date: date, end_date: date, department_name: str = '采购部门'):
        super().__init__(start_date, end_date, project_codes=None)
        self.department_name = department_name
        self.report_type = 'department'
        
        # 根据时间范围确定报告标题
        days = (end_date - start_date).days + 1
        if days <= 31:
            self.report_title = f'{department_name}{start_date.year}年{start_date.month}月工作总结'
        elif days <= 93:
            quarter = (start_date.month - 1) // 3 + 1
            self.report_title = f'{department_name}{start_date.year}年第{quarter}季度工作总结'
        else:
            self.report_title = f'{department_name}{start_date.year}年度工作总结'