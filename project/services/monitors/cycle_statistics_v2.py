"""
工作周期统计服务 V2.0
完全按照需求方案文档重构
遵循 KISS、YAGNI、DRY、SOLID 原则
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from django.utils import timezone
from django.db.models import (
    Avg, Count, Q, F, ExpressionWrapper, fields, 
    Case, When, Value, IntegerField, Min, Max
)
from django.db.models.functions import ExtractYear, ExtractMonth
from decimal import Decimal

from procurement.models import Procurement
from contract.models import Contract
from project.enums import ContractSource
from .config import CYCLE_RULES


class CycleStatisticsServiceV2:
    """
    工作周期统计服务 V2.0
    
    核心职责：
    1. 计算采购周期和合同周期统计
    2. 提供数据质量检查
    3. 支持多维度筛选和分组
    4. 生成趋势分析数据
    """
    
    def __init__(self):
        """初始化配置"""
        self.procurement_rules = CYCLE_RULES['procurement']
        self.contract_rules = CYCLE_RULES['contract']
        self.sla_procurement_default = self.procurement_rules['default_deadline']
        self.sla_contract = self.contract_rules['deadline_days']
    
    # ==================== 公共接口方法 ====================
    
    def get_overview_statistics(
        self,
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        procurement_methods: Optional[List[str]] = None,
        time_dimension: str = 'requirement_approval'  # requirement_approval | result_publicity | contract_signing
    ) -> Dict[str, Any]:
        """
        获取总览统计数据
        
        Args:
            year_filter: 年度筛选（'all' 或具体年份）
            project_filter: 项目编码筛选
            procurement_methods: 采购方式筛选列表
            time_dimension: 时间维度（需求审批/公示/合同签订）
            
        Returns:
            {
                'procurement_cycle_avg': 平均采购周期,
                'procurement_cycle_p50': P50,
                'procurement_cycle_p90': P90,
                'procurement_count': 项目数,
                'procurement_overdue_cnt': 超期数,
                'procurement_overdue_rate': 超期率,
                'contract_cycle_avg': 平均合同周期,
                'contract_cycle_p50': P50,
                'contract_cycle_p90': P90,
                'contract_count': 项目数,
                'contract_overdue_cnt': 超期数,
                'contract_overdue_rate': 超期率,
                'dq_missing_endpoints': 缺失端点数,
                'dq_anomaly_projects': 异常项目数,
                'data_time': 数据时间
            }
        """
        # 采购周期统计
        proc_stats = self._calculate_procurement_statistics(
            year_filter=year_filter,
            project_filter=project_filter,
            procurement_methods=procurement_methods,
            time_dimension=time_dimension
        )
        
        # 合同周期统计
        contract_stats = self._calculate_contract_statistics(
            year_filter=year_filter,
            project_filter=project_filter,
            time_dimension=time_dimension
        )
        
        # 数据质量统计
        dq_stats = self._calculate_data_quality_statistics(
            year_filter=year_filter,
            project_filter=project_filter,
            time_dimension=time_dimension
        )
        
        return {
            # 采购周期指标
            'procurement_cycle_avg': proc_stats['avg_cycle'],
            'procurement_cycle_p50': proc_stats['p50'],
            'procurement_cycle_p90': proc_stats['p90'],
            'procurement_count': proc_stats['count'],
            'procurement_overdue_cnt': proc_stats['overdue_count'],
            'procurement_overdue_rate': proc_stats['overdue_rate'],
            
            # 合同周期指标
            'contract_cycle_avg': contract_stats['avg_cycle'],
            'contract_cycle_p50': contract_stats['p50'],
            'contract_cycle_p90': contract_stats['p90'],
            'contract_count': contract_stats['count'],
            'contract_overdue_cnt': contract_stats['overdue_count'],
            'contract_overdue_rate': contract_stats['overdue_rate'],
            
            # 数据质量指标
            'dq_missing_endpoints': dq_stats['missing_endpoints'],
            'dq_anomaly_projects': dq_stats['anomaly_projects'],
            
            # 元数据
            'data_time': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'batch_no': datetime.now().strftime('%Y%m%d-%H%M')
        }
    
    def get_trend_data(
        self,
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        procurement_methods: Optional[List[str]] = None,
        time_dimension: str = 'requirement_approval'
    ) -> Dict[str, List[Dict]]:
        """
        获取趋势数据
        
        Returns:
            {
                'procurement_trend': [{period, avg_cycle, p50, p90, count}, ...],
                'contract_trend': [{period, avg_cycle, p50, p90, count}, ...]
            }
        """
        proc_trend = self._calculate_procurement_trend(
            year_filter=year_filter,
            project_filter=project_filter,
            procurement_methods=procurement_methods,
            time_dimension=time_dimension
        )
        
        contract_trend = self._calculate_contract_trend(
            year_filter=year_filter,
            project_filter=project_filter,
            time_dimension=time_dimension
        )
        
        return {
            'procurement_trend': proc_trend,
            'contract_trend': contract_trend
        }
    
    def get_dimension_breakdown(
        self,
        dimension: str,  # department | procurement_method | project_type | amount_range | supplier | year | owner
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取维度拆解数据
        
        Args:
            dimension: 拆解维度
            year_filter: 年度筛选
            project_filter: 项目筛选
            top_n: 返回Top N
            
        Returns:
            [{dimension_value, count, avg_cycle, p50, p90, on_time_rate}, ...]
        """
        if dimension == 'procurement_method':
            return self._breakdown_by_procurement_method(
                year_filter=year_filter,
                project_filter=project_filter,
                top_n=top_n
            )
        # 其他维度可以后续扩展
        return []
    
    def get_detail_records(
        self,
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        person_filter: Optional[str] = None,
        procurement_methods: Optional[List[str]] = None,
        show_overdue_only: bool = False,
        time_dimension: str = 'requirement_approval'
    ) -> List[Dict[str, Any]]:
        """
        获取明细记录
        
        Returns:
            [{
                project_id, project_name, section_id,
                demand_approval_time, result_publish_time, contract_sign_date,
                procurement_cycle_days, contract_cycle_days,
                procurement_method, amount, currency, tax_included,
                department, owner, supplier, status,
                is_overdue_proc, is_overdue_cont,
                sla_proc_days, sla_cont_days, remark
            }, ...]
        """
        records = []
        
        # 构建查询集
        queryset = self._build_procurement_queryset(
            year_filter=year_filter,
            project_filter=project_filter,
            person_filter=person_filter,
            procurement_methods=procurement_methods,
            time_dimension=time_dimension,
            require_complete=False  # 包含未完成的记录
        )
        
        for proc in queryset:
            # 计算采购周期
            proc_cycle_days = None
            if proc.requirement_approval_date and proc.result_publicity_release_date:
                proc_cycle_days = (proc.result_publicity_release_date - proc.requirement_approval_date).days
            
            # 获取关联合同
            contract = proc.contracts.filter(
                contract_source=ContractSource.PROCUREMENT.value,
                signing_date__isnull=False
            ).order_by('signing_date').first()
            
            contract_cycle_days = None
            contract_sign_date = None
            if contract and proc.result_publicity_release_date:
                contract_sign_date = contract.signing_date
                contract_cycle_days = (contract.signing_date - proc.result_publicity_release_date).days
            
            # 判断状态
            status = '正常'
            if not proc.requirement_approval_date or not proc.result_publicity_release_date:
                status = '缺失端点'
            
            # 判断是否超期
            sla_proc = self.get_procurement_deadline(proc.procurement_method)
            is_overdue_proc = proc_cycle_days is not None and proc_cycle_days > sla_proc
            is_overdue_cont = contract_cycle_days is not None and contract_cycle_days > self.sla_contract
            
            # 筛选：仅显示超期
            if show_overdue_only and not (is_overdue_proc or is_overdue_cont):
                continue
            
            records.append({
                'project_id': proc.project_id or '',
                'project_name': proc.project_name,
                'section_id': '',
                'demand_approval_time': proc.requirement_approval_date,
                'result_publish_time': proc.result_publicity_release_date,
                'contract_sign_date': contract_sign_date,
                'procurement_cycle_days': proc_cycle_days,
                'contract_cycle_days': contract_cycle_days,
                'procurement_method': proc.procurement_method or '未标注',
                'amount': contract.contract_amount if contract else None,
                'currency': 'CNY',
                'tax_included': 'Y',
                'department': proc.demand_department or '',
                'owner': proc.procurement_officer or '',
                'supplier': proc.winning_bidder or '',
                'status': status,
                'is_overdue_proc': is_overdue_proc,
                'is_overdue_cont': is_overdue_cont,
                'sla_proc_days': sla_proc,
                'sla_cont_days': self.sla_contract,
                'remark': ''
            })
        
        return records
    
    # ==================== 内部计算方法 ====================
    
    def get_procurement_deadline(self, procurement_method: Optional[str]) -> int:
        """根据采购方式获取规定周期天数"""
        if not procurement_method:
            return self.sla_procurement_default
        return self.procurement_rules['deadline_map'].get(
            procurement_method,
            self.sla_procurement_default
        )
    
    def _build_procurement_queryset(
        self,
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        person_filter: Optional[str] = None,
        procurement_methods: Optional[List[str]] = None,
        time_dimension: str = 'requirement_approval',
        require_complete: bool = True
    ):
        """构建采购查询集"""
        queryset = Procurement.objects.select_related('project')
        
        # 基础过滤：必须有需求审批日期
        queryset = queryset.filter(requirement_approval_date__isnull=False)
        
        # 完整性过滤
        if require_complete:
            queryset = queryset.filter(result_publicity_release_date__isnull=False)
        
        # 年度筛选
        if year_filter and year_filter != 'all':
            year_int = int(year_filter)
            if time_dimension == 'requirement_approval':
                queryset = queryset.filter(requirement_approval_date__year=year_int)
            elif time_dimension == 'result_publicity':
                queryset = queryset.filter(result_publicity_release_date__year=year_int)
        
        # 项目筛选
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        
        # 经办人筛选
        if person_filter:
            queryset = queryset.filter(procurement_officer=person_filter)
        
        # 采购方式筛选
        if procurement_methods:
            q_obj = Q()
            non_null_methods = [m for m in procurement_methods if m and m != '未标注']
            if non_null_methods:
                q_obj |= Q(procurement_method__in=non_null_methods)
            if '未标注' in procurement_methods:
                q_obj |= Q(procurement_method__isnull=True) | Q(procurement_method__exact='')
            queryset = queryset.filter(q_obj)
        
        # 排除测试/作废/流标/撤项（根据需求可配置）
        # queryset = queryset.exclude(...)
        
        return queryset
    
    def _calculate_procurement_statistics(
        self,
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        person_filter: Optional[str] = None,
        procurement_methods: Optional[List[str]] = None,
        time_dimension: str = 'requirement_approval'
    ) -> Dict[str, Any]:
        """计算采购周期统计"""
        queryset = self._build_procurement_queryset(
            year_filter=year_filter,
            project_filter=project_filter,
            person_filter=person_filter,
            procurement_methods=procurement_methods,
            time_dimension=time_dimension,
            require_complete=True
        )
        
        count = queryset.count()
        if count == 0:
            return {
                'avg_cycle': 0,
                'p50': 0,
                'p90': 0,
                'count': 0,
                'overdue_count': 0,
                'overdue_rate': 0.0
            }
        
        # 计算周期天数
        cycle_days_list = []
        overdue_count = 0
        
        for proc in queryset:
            cycle_days = (proc.result_publicity_release_date - proc.requirement_approval_date).days
            cycle_days_list.append(cycle_days)
            
            # 判断是否超期
            deadline = self.get_procurement_deadline(proc.procurement_method)
            if cycle_days > deadline:
                overdue_count += 1
        
        # 计算统计指标
        cycle_days_list.sort()
        avg_cycle = round(sum(cycle_days_list) / len(cycle_days_list), 1)
        p50 = self._calculate_percentile(cycle_days_list, 50)
        p90 = self._calculate_percentile(cycle_days_list, 90)
        overdue_rate = round(overdue_count / count * 100, 1)
        
        return {
            'avg_cycle': avg_cycle,
            'p50': p50,
            'p90': p90,
            'count': count,
            'overdue_count': overdue_count,
            'overdue_rate': overdue_rate
        }
    
    def _calculate_contract_statistics(
        self,
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        person_filter: Optional[str] = None,
        time_dimension: str = 'requirement_approval'
    ) -> Dict[str, Any]:
        """计算合同周期统计"""
        queryset = Contract.objects.filter(
            contract_source=ContractSource.PROCUREMENT.value,
            procurement__isnull=False,
            procurement__result_publicity_release_date__isnull=False,
            signing_date__isnull=False
        ).select_related('procurement', 'project')
        
        # 年度筛选
        if year_filter and year_filter != 'all':
            year_int = int(year_filter)
            if time_dimension == 'contract_signing':
                queryset = queryset.filter(signing_date__year=year_int)
            else:
                queryset = queryset.filter(procurement__result_publicity_release_date__year=year_int)
        
        # 项目筛选
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        
        # 经办人筛选
        if person_filter:
            queryset = queryset.filter(contract_officer=person_filter)
        
        count = queryset.count()
        if count == 0:
            return {
                'avg_cycle': 0,
                'p50': 0,
                'p90': 0,
                'count': 0,
                'overdue_count': 0,
                'overdue_rate': 0.0
            }
        
        # 计算周期天数
        cycle_days_list = []
        overdue_count = 0
        
        for contract in queryset:
            cycle_days = (contract.signing_date - contract.procurement.result_publicity_release_date).days
            cycle_days_list.append(cycle_days)
            
            if cycle_days > self.sla_contract:
                overdue_count += 1
        
        # 计算统计指标
        cycle_days_list.sort()
        avg_cycle = round(sum(cycle_days_list) / len(cycle_days_list), 1)
        p50 = self._calculate_percentile(cycle_days_list, 50)
        p90 = self._calculate_percentile(cycle_days_list, 90)
        overdue_rate = round(overdue_count / count * 100, 1)
        
        return {
            'avg_cycle': avg_cycle,
            'p50': p50,
            'p90': p90,
            'count': count,
            'overdue_count': overdue_count,
            'overdue_rate': overdue_rate
        }
    
    def _calculate_data_quality_statistics(
        self,
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        time_dimension: str = 'requirement_approval'
    ) -> Dict[str, int]:
        """计算数据质量统计"""
        # 缺失端点：有需求审批但无公示日期
        missing_queryset = Procurement.objects.filter(
            requirement_approval_date__isnull=False,
            result_publicity_release_date__isnull=True
        )
        
        if year_filter and year_filter != 'all':
            year_int = int(year_filter)
            missing_queryset = missing_queryset.filter(requirement_approval_date__year=year_int)
        
        if project_filter:
            missing_queryset = missing_queryset.filter(project_id=project_filter)
        
        missing_count = missing_queryset.count()
        
        # 异常项目：多公示/多合同等（简化实现）
        anomaly_count = 0
        
        return {
            'missing_endpoints': missing_count,
            'anomaly_projects': anomaly_count
        }
    
    def _calculate_procurement_trend(
        self,
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        procurement_methods: Optional[List[str]] = None,
        time_dimension: str = 'requirement_approval'
    ) -> List[Dict[str, Any]]:
        """计算采购周期趋势"""
        queryset = self._build_procurement_queryset(
            year_filter=year_filter,
            project_filter=project_filter,
            procurement_methods=procurement_methods,
            time_dimension=time_dimension,
            require_complete=True
        )
        
        # 按月或半年分组
        if year_filter and year_filter != 'all':
            return self._group_by_month(queryset, 'procurement')
        else:
            return self._group_by_half_year(queryset, 'procurement')
    
    def _calculate_contract_trend(
        self,
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        time_dimension: str = 'requirement_approval'
    ) -> List[Dict[str, Any]]:
        """计算合同周期趋势"""
        queryset = Contract.objects.filter(
            contract_source=ContractSource.PROCUREMENT.value,
            procurement__isnull=False,
            procurement__result_publicity_release_date__isnull=False,
            signing_date__isnull=False
        ).select_related('procurement')
        
        if year_filter and year_filter != 'all':
            year_int = int(year_filter)
            queryset = queryset.filter(signing_date__year=year_int)
        
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        
        # 按月或半年分组
        if year_filter and year_filter != 'all':
            return self._group_by_month(queryset, 'contract')
        else:
            return self._group_by_half_year(queryset, 'contract')
    
    def _breakdown_by_procurement_method(
        self,
        year_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """按采购方式拆解"""
        queryset = self._build_procurement_queryset(
            year_filter=year_filter,
            project_filter=project_filter,
            require_complete=True
        )
        
        # 分组统计
        method_stats = {}
        for proc in queryset:
            method = proc.procurement_method or '未标注'
            cycle_days = (proc.result_publicity_release_date - proc.requirement_approval_date).days
            deadline = self.get_procurement_deadline(proc.procurement_method)
            
            if method not in method_stats:
                method_stats[method] = {
                    'method': method,
                    'cycles': [],
                    'overdue_count': 0,
                    'deadline': deadline
                }
            
            method_stats[method]['cycles'].append(cycle_days)
            if cycle_days > deadline:
                method_stats[method]['overdue_count'] += 1
        
        # 计算统计指标
        results = []
        for method, stats in method_stats.items():
            cycles = sorted(stats['cycles'])
            count = len(cycles)
            avg_cycle = round(sum(cycles) / count, 1)
            p50 = self._calculate_percentile(cycles, 50)
            p90 = self._calculate_percentile(cycles, 90)
            on_time_rate = round((count - stats['overdue_count']) / count * 100, 1)
            
            results.append({
                'method': method,
                'count': count,
                'avg_cycle': avg_cycle,
                'p50': p50,
                'p90': p90,
                'on_time_rate': on_time_rate,
                'deadline': stats['deadline']
            })
        
        # 按数量排序并返回Top N
        results.sort(key=lambda x: x['count'], reverse=True)
        return results[:top_n]
    
    def _group_by_month(self, queryset, cycle_type: str) -> List[Dict[str, Any]]:
        """按月分组统计"""
        monthly_data = {}
        
        for item in queryset:
            if cycle_type == 'procurement':
                month_key = item.requirement_approval_date.strftime('%Y-%m')
                cycle_days = (item.result_publicity_release_date - item.requirement_approval_date).days
            else:  # contract
                month_key = item.signing_date.strftime('%Y-%m')
                cycle_days = (item.signing_date - item.procurement.result_publicity_release_date).days
            
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(cycle_days)
        
        # 计算每月统计
        results = []
        for month_key in sorted(monthly_data.keys()):
            cycles = sorted(monthly_data[month_key])
            results.append({
                'period': month_key,
                'avg_cycle': round(sum(cycles) / len(cycles), 1),
                'p50': self._calculate_percentile(cycles, 50),
                'p90': self._calculate_percentile(cycles, 90),
                'count': len(cycles)
            })
        
        return results
    
    def _group_by_half_year(self, queryset, cycle_type: str) -> List[Dict[str, Any]]:
        """按半年分组统计"""
        half_year_data = {}
        
        for item in queryset:
            if cycle_type == 'procurement':
                date_obj = item.requirement_approval_date
                cycle_days = (item.result_publicity_release_date - item.requirement_approval_date).days
            else:  # contract
                date_obj = item.signing_date
                cycle_days = (item.signing_date - item.procurement.result_publicity_release_date).days
            
            year = date_obj.year
            half = 1 if date_obj.month <= 6 else 2
            key = f"{year}-H{half}"
            
            if key not in half_year_data:
                half_year_data[key] = []
            half_year_data[key].append(cycle_days)
        
        # 计算每半年统计
        results = []
        for key in sorted(half_year_data.keys()):
            cycles = sorted(half_year_data[key])
            results.append({
                'period': key.replace('-H1', '上半年').replace('-H2', '下半年'),
                'avg_cycle': round(sum(cycles) / len(cycles), 1),
                'p50': self._calculate_percentile(cycles, 50),
                'p90': self._calculate_percentile(cycles, 90),
                'count': len(cycles)
            })
        
        return results
    
    @staticmethod
    def _calculate_percentile(sorted_list: List[float], percentile: int) -> int:
        """计算百分位数"""
        if not sorted_list:
            return 0
        index = int(len(sorted_list) * percentile / 100)
        if index >= len(sorted_list):
            index = len(sorted_list) - 1
        return round(sorted_list[index])