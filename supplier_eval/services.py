"""
供应商管理模块 - 业务逻辑服务层
提供供应商分析、统计等业务逻辑
"""
from decimal import Decimal
from django.db.models import Count, Sum, Q, Avg
from django.db.models.functions import Coalesce
from contract.models import Contract
from supplier_eval.models import SupplierEvaluation, SupplierInterview


class SupplierAnalysisService:
    """供应商分析服务 - 提供供应商相关的统计和分析功能"""
    
    @staticmethod
    def get_supplier_summary(supplier_name=None):
        """
        获取供应商汇总统计
        
        Args:
            supplier_name (str, optional): 供应商名称，支持模糊查询。如果为None则返回所有供应商
        
        Returns:
            list: 供应商汇总数据列表，每项包含:
                - party_b (str): 供应商名称
                - total_contracts (int): 承接合同总数
                - ongoing_contracts (int): 在执行合同数
                - total_amount (Decimal): 合同总金额(含补充协议)
                - total_paid (Decimal): 累计付款金额
                - avg_score (Decimal): 平均履约评分
                - evaluation_count (int): 评价记录数
        
        Example:
            >>> service = SupplierAnalysisService()
            >>> result = service.get_supplier_summary('某供应商')
            >>> print(result[0]['total_contracts'])
            10
        """
        # 基础查询：主合同和框架协议（不含补充协议和解除协议）
        contracts = Contract.objects.filter(
            file_positioning__in=['主合同', '框架协议']
        )
        
        # 如果指定供应商名称，进行模糊查询
        if supplier_name:
            contracts = contracts.filter(party_b__icontains=supplier_name)
        
        # 按供应商分组统计
        summary = contracts.values('party_b').annotate(
            total_contracts=Count('contract_code', distinct=True),  # 使用distinct避免重复计数
            ongoing_contracts=Count(
                'contract_code',
                distinct=True,  # 使用distinct避免重复计数
                filter=Q(settlement__isnull=True) & ~Q(payments__is_settled=True)  # 未结算的合同（排除Settlement表和Payment表中标记为已结算的）
            )
        ).order_by('-total_contracts')
        
        # 补充计算每个供应商的合同总金额和累计付款
        result = []
        for item in summary:
            supplier = item['party_b']
            
            # 获取该供应商的所有主合同和框架协议
            supplier_contracts = Contract.objects.filter(
                party_b=supplier,
                file_positioning__in=['主合同', '框架协议']
            )
            
            # 计算合同总金额(包含补充协议)
            total_amount = Decimal('0')
            total_paid = Decimal('0')
            
            for contract in supplier_contracts:
                # 使用模型方法获取含补充协议的总金额
                total_amount += contract.get_contract_with_supplements_amount() or Decimal('0')
                # 获取累计付款
                total_paid += contract.get_total_paid_amount() or Decimal('0')
            
            # 获取该供应商的评价统计
            evaluations = SupplierEvaluation.objects.filter(
                supplier_name__icontains=supplier,
                comprehensive_score__isnull=False
            )
            
            avg_score = evaluations.aggregate(
                avg=Avg('comprehensive_score')
            )['avg']
            
            evaluation_count = evaluations.count()
            
            # 组装结果
            result.append({
                'party_b': supplier,
                'total_contracts': item['total_contracts'],
                'ongoing_contracts': item['ongoing_contracts'],
                'total_amount': total_amount,
                'total_paid': total_paid,
                'avg_score': round(avg_score, 2) if avg_score else None,
                'evaluation_count': evaluation_count,
            })
        
        return result
    
    @staticmethod
    def get_supplier_contracts(supplier_name, contract_status=None):
        """
        获取供应商承接的所有合同详情
        
        Args:
            supplier_name (str): 供应商名称(模糊匹配)
            contract_status (str, optional): 合同状态筛选
                - 'ongoing': 仅在执行合同
                - 'settled': 仅已结算合同
                - None: 所有合同
        
        Returns:
            list: 合同详情列表，每项包含:
                - contract (Contract): 合同对象
                - contract_total_amount (Decimal): 合同总金额(含补充协议)
                - payment_ratio (float): 付款比例(%)
                - is_ongoing (bool): 是否在执行中
                - total_paid (Decimal): 累计付款金额
                - payment_count (int): 付款笔数
                - supplement_count (int): 补充协议数量
                - has_evaluation (bool): 是否有履约评价
        
        Example:
            >>> service = SupplierAnalysisService()
            >>> contracts = service.get_supplier_contracts('某供应商', 'ongoing')
            >>> for item in contracts:
            ...     print(f"{item['contract'].contract_code}: {item['payment_ratio']}%")
        """
        # 基础查询：主合同和框架协议
        contracts = Contract.objects.filter(
            party_b__icontains=supplier_name,
            file_positioning__in=['主合同', '框架协议']
        ).select_related('settlement').prefetch_related('supplements', 'payments', 'evaluations')
        
        # 状态筛选
        if contract_status == 'ongoing':
            contracts = contracts.filter(settlement__isnull=True)
        elif contract_status == 'settled':
            contracts = contracts.filter(settlement__isnull=False)
        
        # 按签订日期倒序
        contracts = contracts.order_by('-signing_date')
        
        result = []
        for contract in contracts:
            # 计算合同总金额(含补充协议)
            contract_total_amount = contract.get_contract_with_supplements_amount()
            
            # 获取付款信息
            total_paid = contract.get_total_paid_amount()
            payment_count = contract.get_payment_count()
            payment_ratio = contract.get_payment_ratio()
            
            # 判断是否在执行中
            # 检查两个条件：1. Settlement表中没有记录  2. Payment表中没有标记为已结算的记录
            has_settlement_record = hasattr(contract, 'settlement') and contract.settlement is not None  # type: ignore[attr-defined]
            has_settled_payment = contract.payments.filter(is_settled=True).exists()  # type: ignore[attr-defined]
            is_ongoing = not (has_settlement_record or has_settled_payment)
            
            # 补充协议数量
            supplement_count = contract.supplements.count()  # type: ignore[attr-defined]
            
            # 是否有履约评价
            has_evaluation = contract.evaluations.exists()  # type: ignore[attr-defined]
            
            result.append({
                'contract': contract,
                'contract_total_amount': contract_total_amount,
                'payment_ratio': payment_ratio,
                'is_ongoing': is_ongoing,
                'total_paid': total_paid,
                'payment_count': payment_count,
                'supplement_count': supplement_count,
                'has_evaluation': has_evaluation,
            })
        
        return result
    
    @staticmethod
    def get_evaluation_statistics(supplier_name=None):
        """
        获取履约评价统计数据
        
        Args:
            supplier_name (str, optional): 供应商名称，如果指定则仅统计该供应商
        
        Returns:
            dict: 评价统计数据:
                - total (int): 评价总数
                - excellent (int): 优秀(≥90分)
                - good (int): 良好(≥80分)
                - qualified (int): 合格(≥70分)
                - unqualified (int): 不合格(<70分)
                - avg_score (Decimal): 平均综合评分
                - avg_last_score (Decimal): 平均末次评分
                - score_distribution (list): 分数段分布
                    [{'range': '90-100', 'count': 10, 'percentage': 20.0}, ...]
        
        Example:
            >>> service = SupplierAnalysisService()
            >>> stats = service.get_evaluation_statistics()
            >>> print(f"优秀率: {stats['excellent']/stats['total']*100:.1f}%")
        """
        # 基础查询
        evaluations = SupplierEvaluation.objects.filter(
            comprehensive_score__isnull=False
        )
        
        # 如果指定供应商，进行筛选
        if supplier_name:
            evaluations = evaluations.filter(supplier_name__icontains=supplier_name)
        
        total = evaluations.count()
        
        # 如果没有评价数据，返回空统计
        if total == 0:
            return {
                'total': 0,
                'excellent': 0,
                'good': 0,
                'qualified': 0,
                'unqualified': 0,
                'avg_score': None,
                'avg_last_score': None,
                'score_distribution': [],
            }
        
        # 按评分等级统计
        excellent = evaluations.filter(comprehensive_score__gte=90).count()
        good = evaluations.filter(
            comprehensive_score__gte=80,
            comprehensive_score__lt=90
        ).count()
        qualified = evaluations.filter(
            comprehensive_score__gte=70,
            comprehensive_score__lt=80
        ).count()
        unqualified = evaluations.filter(comprehensive_score__lt=70).count()
        
        # 计算平均分
        aggregates = evaluations.aggregate(
            avg_score=Avg('comprehensive_score'),
            avg_last_score=Avg('last_evaluation_score')
        )
        
        avg_score = aggregates['avg_score']
        avg_last_score = aggregates['avg_last_score']
        
        # 分数段分布(每10分一档)
        score_ranges = [
            (0, 60, '0-59'),
            (60, 70, '60-69'),
            (70, 80, '70-79'),
            (80, 90, '80-89'),
            (90, 101, '90-100'),
        ]
        
        score_distribution = []
        for min_score, max_score, label in score_ranges:
            count = evaluations.filter(
                comprehensive_score__gte=min_score,
                comprehensive_score__lt=max_score
            ).count()
            
            percentage = (count / total * 100) if total > 0 else 0
            
            score_distribution.append({
                'range': label,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        return {
            'total': total,
            'excellent': excellent,
            'good': good,
            'qualified': qualified,
            'unqualified': unqualified,
            'avg_score': round(avg_score, 2) if avg_score else None,
            'avg_last_score': round(avg_last_score, 2) if avg_last_score else None,
            'score_distribution': score_distribution,
        }
    
    @staticmethod
    def get_interview_statistics(supplier_name=None):
        """
        获取约谈记录统计数据
        
        Args:
            supplier_name (str, optional): 供应商名称，如果指定则仅统计该供应商
        
        Returns:
            dict: 约谈统计数据:
                - total (int): 约谈记录总数
                - breach_count (int): 违约约谈数量
                - pending_count (int): 待跟进数量(待整改+整改中)
                - completed_count (int): 已完成数量
                - type_distribution (dict): 约谈类型分布
                - status_distribution (dict): 跟进状态分布
                - recent_interviews (list): 最近10条约谈记录
        
        Example:
            >>> service = SupplierAnalysisService()
            >>> stats = service.get_interview_statistics('某供应商')
            >>> print(f"违约约谈: {stats['breach_count']}次")
        """
        # 基础查询
        interviews = SupplierInterview.objects.all()
        
        # 如果指定供应商，进行筛选
        if supplier_name:
            interviews = interviews.filter(supplier_name__icontains=supplier_name)
        
        total = interviews.count()
        
        # 违约约谈数量
        breach_count = interviews.filter(interview_type='违约约谈').count()
        
        # 待跟进数量
        pending_count = interviews.filter(status__in=['待整改', '整改中']).count()
        
        # 已完成数量
        completed_count = interviews.filter(status='已完成').count()
        
        # 约谈类型分布
        type_distribution = {}
        for choice_value, choice_label in SupplierInterview.INTERVIEW_TYPE_CHOICES:
            count = interviews.filter(interview_type=choice_value).count()
            type_distribution[choice_label] = count
        
        # 跟进状态分布
        status_distribution = {}
        for choice_value, choice_label in SupplierInterview.STATUS_CHOICES:
            count = interviews.filter(status=choice_value).count()
            status_distribution[choice_label] = count
        
        # 最近10条约谈记录
        recent_interviews = list(
            interviews.order_by('-interview_date', '-created_at')[:10]
        )
        
        return {
            'total': total,
            'breach_count': breach_count,
            'pending_count': pending_count,
            'completed_count': completed_count,
            'type_distribution': type_distribution,
            'status_distribution': status_distribution,
            'recent_interviews': recent_interviews,
        }
    
    @staticmethod
    def get_supplier_detail(supplier_name):
        """
        获取供应商的完整详细信息(汇总)
        
        Args:
            supplier_name (str): 供应商名称(精确匹配)
        
        Returns:
            dict: 供应商详细信息:
                - summary (dict): 基本汇总信息
                - contracts (list): 合同列表
                - evaluations (list): 评价记录
                - interviews (list): 约谈记录
                - evaluation_stats (dict): 评价统计
                - interview_stats (dict): 约谈统计
        
        Example:
            >>> service = SupplierAnalysisService()
            >>> detail = service.get_supplier_detail('某供应商')
            >>> print(detail['summary']['total_contracts'])
        """
        # 获取汇总信息
        summary_list = SupplierAnalysisService.get_supplier_summary(supplier_name)
        summary = summary_list[0] if summary_list else None
        
        # 获取合同列表
        contracts = SupplierAnalysisService.get_supplier_contracts(supplier_name)
        
        # 获取评价记录
        evaluations = list(
            SupplierEvaluation.objects.filter(
                supplier_name__icontains=supplier_name
            ).select_related('contract').order_by('-created_at')
        )
        
        # 获取约谈记录
        interviews = list(
            SupplierInterview.objects.filter(
                supplier_name__icontains=supplier_name
            ).select_related('contract').order_by('-interview_date')
        )
        
        # 获取统计数据
        evaluation_stats = SupplierAnalysisService.get_evaluation_statistics(supplier_name)
        interview_stats = SupplierAnalysisService.get_interview_statistics(supplier_name)
        
        return {
            'supplier_name': supplier_name,
            'summary': summary,
            'contracts': contracts,
            'evaluations': evaluations,
            'interviews': interviews,
            'evaluation_stats': evaluation_stats,
            'interview_stats': interview_stats,
        }