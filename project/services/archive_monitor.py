"""
归档监控服务
监控采购、合同、结算资料的归档情况
"""
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from procurement.models import Procurement
from contract.models import Contract
from settlement.models import Settlement


class ArchiveMonitorService:
    """归档监控服务"""
    
    def get_archive_overview(self):
        """
        获取归档总览数据
        
        Returns:
            dict: 包含采购、合同、结算的归档统计和总体归档率
        """
        procurement_stats = self._get_procurement_archive_stats()
        contract_stats = self._get_contract_archive_stats()
        settlement_stats = self._get_settlement_archive_stats()
        overall_rate = self._calculate_overall_rate(
            procurement_stats, 
            contract_stats, 
            settlement_stats
        )
        
        return {
            'procurement': procurement_stats,
            'contract': contract_stats,
            'settlement': settlement_stats,
            'overall_rate': overall_rate,
            'last_updated': timezone.now()
        }
    
    def _get_procurement_archive_stats(self):
        """
        采购归档统计
        
        统计规则：
        - 应归档项数 = 已完成公示的采购项目数（有platform_publicity_date的记录）
        - 已归档项数 = 有archive_date的记录数
        - 逾期标准 = 公示后40天
        
        Returns:
            dict: 采购归档统计数据
        """
        # 应归档总数：已完成平台公示的采购
        total = Procurement.objects.filter(
            platform_publicity_date__isnull=False
        ).count()
        
        # 已归档数量
        archived = Procurement.objects.filter(
            platform_publicity_date__isnull=False,
            archive_date__isnull=False
        ).count()
        
        # 逾期统计（公示后40天）
        if total > 0:
            deadline = timezone.now().date() - timedelta(days=40)
            overdue = Procurement.objects.filter(
                platform_publicity_date__lte=deadline,
                archive_date__isnull=True
            ).count()
            
            # 分级预警
            severe_deadline = timezone.now().date() - timedelta(days=70)  # 超过30天
            moderate_deadline = timezone.now().date() - timedelta(days=56)  # 超过16天
            mild_deadline = deadline  # 超过1天
            
            severe_overdue = Procurement.objects.filter(
                platform_publicity_date__lte=severe_deadline,
                archive_date__isnull=True
            ).count()
            
            moderate_overdue = Procurement.objects.filter(
                platform_publicity_date__lte=moderate_deadline,
                platform_publicity_date__gt=severe_deadline,
                archive_date__isnull=True
            ).count()
            
            mild_overdue = Procurement.objects.filter(
                platform_publicity_date__lte=mild_deadline,
                platform_publicity_date__gt=moderate_deadline,
                archive_date__isnull=True
            ).count()
        else:
            overdue = 0
            severe_overdue = 0
            moderate_overdue = 0
            mild_overdue = 0
        
        return {
            'total': total,
            'archived': archived,
            'unarchived': total - archived,
            'rate': round((archived / total * 100), 2) if total > 0 else 0,
            'overdue': overdue,
            'overdue_breakdown': {
                'severe': severe_overdue,  # 红色：30天以上
                'moderate': moderate_overdue,  # 橙色：16-30天
                'mild': mild_overdue  # 黄色：1-15天
            }
        }
    
    def _get_contract_archive_stats(self):
        """
        合同归档统计
        
        统计规则：
        - 只统计主合同（不统计补充协议和解除协议）
        - 应归档项数 = 已签订的主合同数
        - 逾期标准 = 签订后30天
        
        Returns:
            dict: 合同归档统计数据
        """
        # 只统计主合同
        total = Contract.objects.filter(
            contract_type='主合同',
            signing_date__isnull=False
        ).count()
        
        # 已归档数量
        archived = Contract.objects.filter(
            contract_type='主合同',
            signing_date__isnull=False,
            archive_date__isnull=False
        ).count()
        
        # 逾期统计（签订后30天）
        if total > 0:
            deadline = timezone.now().date() - timedelta(days=30)
            overdue = Contract.objects.filter(
                contract_type='主合同',
                signing_date__lte=deadline,
                archive_date__isnull=True
            ).count()
            
            # 分级预警
            severe_deadline = timezone.now().date() - timedelta(days=60)  # 超过30天
            moderate_deadline = timezone.now().date() - timedelta(days=46)  # 超过16天
            mild_deadline = deadline  # 超过1天
            
            severe_overdue = Contract.objects.filter(
                contract_type='主合同',
                signing_date__lte=severe_deadline,
                archive_date__isnull=True
            ).count()
            
            moderate_overdue = Contract.objects.filter(
                contract_type='主合同',
                signing_date__lte=moderate_deadline,
                signing_date__gt=severe_deadline,
                archive_date__isnull=True
            ).count()
            
            mild_overdue = Contract.objects.filter(
                contract_type='主合同',
                signing_date__lte=mild_deadline,
                signing_date__gt=moderate_deadline,
                archive_date__isnull=True
            ).count()
        else:
            overdue = 0
            severe_overdue = 0
            moderate_overdue = 0
            mild_overdue = 0
        
        return {
            'total': total,
            'archived': archived,
            'unarchived': total - archived,
            'rate': round((archived / total * 100), 2) if total > 0 else 0,
            'overdue': overdue,
            'overdue_breakdown': {
                'severe': severe_overdue,
                'moderate': moderate_overdue,
                'mild': mild_overdue
            }
        }
    
    def _get_settlement_archive_stats(self):
        """
        结算归档统计
        
        注意：结算归档日期字段暂未实现，返回占位数据
        
        Returns:
            dict: 结算归档统计数据（暂未实现）
        """
        return {
            'total': 0,
            'archived': 0,
            'unarchived': 0,
            'rate': 0,
            'overdue': 0,
            'overdue_breakdown': {
                'severe': 0,
                'moderate': 0,
                'mild': 0
            },
            'note': '结算归档日期字段待补充'
        }
    
    def _calculate_overall_rate(self, procurement_stats, contract_stats, settlement_stats):
        """
        计算总体归档率
        
        综合采购和合同的归档率（暂不包含结算）
        
        Args:
            procurement_stats: 采购归档统计
            contract_stats: 合同归档统计
            settlement_stats: 结算归档统计
            
        Returns:
            float: 总体归档率
        """
        total_items = procurement_stats['total'] + contract_stats['total']
        total_archived = procurement_stats['archived'] + contract_stats['archived']
        
        if total_items > 0:
            return round((total_archived / total_items * 100), 2)
        return 0
    
    def get_overdue_list(self, module=None, severity=None, project_id=None):
        """
        获取逾期项目列表
        
        Args:
            module: 模块类型 ('procurement'/'contract'/'settlement')
            severity: 严重程度 ('mild'/'moderate'/'severe')
            project_id: 项目ID，用于筛选特定项目
            
        Returns:
            list: 逾期项目列表
        """
        overdue_list = []
        
        # 如果指定模块，只返回该模块；否则返回全部
        modules = [module] if module else ['procurement', 'contract']
        
        for mod in modules:
            if mod == 'procurement':
                overdue_list.extend(
                    self._get_procurement_overdue_list(severity, project_id)
                )
            elif mod == 'contract':
                overdue_list.extend(
                    self._get_contract_overdue_list(severity, project_id)
                )
        
        # 按逾期天数降序排序
        overdue_list.sort(key=lambda x: x['overdue_days'], reverse=True)
        
        return overdue_list
    
    def _get_procurement_overdue_list(self, severity=None, project_id=None):
        """获取采购逾期列表"""
        deadline = timezone.now().date() - timedelta(days=40)
        
        queryset = Procurement.objects.filter(
            platform_publicity_date__lte=deadline,
            archive_date__isnull=True
        ).select_related('project')
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        overdue_list = []
        for proc in queryset:
            if not proc.platform_publicity_date:
                continue
            overdue_days = (timezone.now().date() - proc.platform_publicity_date).days - 40
            
            # 确定严重程度
            if overdue_days > 30:
                level = 'severe'
            elif overdue_days > 15:
                level = 'moderate'
            else:
                level = 'mild'
            
            # 如果指定了严重程度，只返回匹配的
            if severity and level != severity:
                continue
            
            overdue_list.append({
                'module': '采购',
                'code': proc.procurement_code,
                'name': proc.project_name,
                'project_code': proc.project.project_code if proc.project else '',
                'project_name': proc.project.project_name if proc.project else '',
                'reference_date': proc.platform_publicity_date,
                'reference_date_label': '平台公示完成日期',
                'deadline_days': 40,
                'overdue_days': overdue_days,
                'severity': level,
                'officer': proc.procurement_officer
            })
        
        return overdue_list
    
    def _get_contract_overdue_list(self, severity=None, project_id=None):
        """获取合同逾期列表"""
        deadline = timezone.now().date() - timedelta(days=30)
        
        queryset = Contract.objects.filter(
            contract_type='主合同',
            signing_date__lte=deadline,
            archive_date__isnull=True
        ).select_related('project')
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        overdue_list = []
        for contract in queryset:
            if not contract.signing_date:
                continue
            overdue_days = (timezone.now().date() - contract.signing_date).days - 30
            
            # 确定严重程度
            if overdue_days > 30:
                level = 'severe'
            elif overdue_days > 15:
                level = 'moderate'
            else:
                level = 'mild'
            
            # 如果指定了严重程度，只返回匹配的
            if severity and level != severity:
                continue
            
            overdue_list.append({
                'module': '合同',
                'code': contract.contract_code,
                'name': contract.contract_name,
                'project_code': contract.project.project_code if contract.project else '',
                'project_name': contract.project.project_name if contract.project else '',
                'reference_date': contract.signing_date,
                'reference_date_label': '合同签订日期',
                'deadline_days': 30,
                'overdue_days': overdue_days,
                'severity': level,
                'officer': contract.contract_officer
            })
        
        return overdue_list