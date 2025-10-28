"""
归档监控服务
监控采购、合同、结算资料的归档情况
"""
from django.utils import timezone
from datetime import timedelta
from procurement.models import Procurement
from contract.models import Contract


class ArchiveMonitorService:
    """归档监控服务"""
    
    def __init__(self, year=None, project_codes=None):
        """
        初始化服务
        
        Args:
            year: 筛选年份，None表示全部年份
            project_codes: 项目编码列表，None表示全部项目
        """
        self.year = year
        self.project_codes = project_codes
    
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
        
        # 计算归档及时率
        overall_timely_rate = self._calculate_overall_timely_rate(
            procurement_stats,
            contract_stats
        )
        
        return {
            'procurement': procurement_stats,
            'contract': contract_stats,
            'settlement': settlement_stats,
            'overall_rate': overall_rate,
            'overall_timely_rate': overall_timely_rate,
            'last_updated': timezone.now()
        }
    
    def _get_filtered_procurements(self):
        """按当前服务配置返回过滤后的采购查询集。"""
        qs = Procurement.objects.filter(result_publicity_release_date__isnull=False)
        if self.year:
            qs = qs.filter(result_publicity_release_date__year=self.year)
        if self.project_codes:
            qs = qs.filter(project__project_code__in=self.project_codes)
        return qs

    def _get_filtered_contracts(self):
        """按当前服务配置返回过滤后的合同查询集（主合同）。"""
        qs = Contract.objects.filter(
            file_positioning='主合同',
            signing_date__isnull=False
        )
        if self.year:
            qs = qs.filter(signing_date__year=self.year)
        if self.project_codes:
            qs = qs.filter(project__project_code__in=self.project_codes)
        return qs

    def _get_procurement_archive_stats(self):
        """
        采购归档统计
        
        统计规则：
        - 应归档项数 = 已完成公示的采购项目数（有result_publicity_release_date的记录）
        - 已归档项数 = 有archive_date的记录数
        - 逾期标准 = 公示后40天
        - 及时归档标准 = 在公示后40天内完成归档
        
        Returns:
            dict: 采购归档统计数据
        """
        base_qs = self._get_filtered_procurements()
        
        # 应归档总数
        total = base_qs.count()
        
        # 已归档数量
        archived_qs = base_qs.filter(archive_date__isnull=False)
        archived = archived_qs.count()
        
        # 计算归档及时率（在40天内完成归档的比例）
        timely_archived = 0
        avg_archive_days = 0
        
        if archived > 0:
            # 统计及时归档的数量
            for proc in archived_qs:
                if proc.archive_date and proc.result_publicity_release_date:
                    days_to_archive = (proc.archive_date - proc.result_publicity_release_date).days
                    if days_to_archive <= 40:
                        timely_archived += 1
            
            # 计算平均归档周期
            archive_days_list = []
            for proc in archived_qs:
                if proc.archive_date and proc.result_publicity_release_date:
                    days = (proc.archive_date - proc.result_publicity_release_date).days
                    archive_days_list.append(days)
            
            if archive_days_list:
                avg_archive_days = round(sum(archive_days_list) / len(archive_days_list), 1)
        
        timely_rate = round((timely_archived / archived * 100), 2) if archived > 0 else 0
        
        # 逾期统计（公示后40天）
        if total > 0:
            deadline = timezone.now().date() - timedelta(days=40)
            overdue = base_qs.filter(
                result_publicity_release_date__lte=deadline,
                archive_date__isnull=True
            ).count()
            
            # 分级预警
            severe_deadline = timezone.now().date() - timedelta(days=70)  # 超过30天
            moderate_deadline = timezone.now().date() - timedelta(days=56)  # 超过16天
            mild_deadline = deadline  # 超过1天
            
            severe_overdue = base_qs.filter(
                result_publicity_release_date__lte=severe_deadline,
                archive_date__isnull=True
            ).count()
            
            moderate_overdue = base_qs.filter(
                result_publicity_release_date__lte=moderate_deadline,
                result_publicity_release_date__gt=severe_deadline,
                archive_date__isnull=True
            ).count()
            
            mild_overdue = base_qs.filter(
                result_publicity_release_date__lte=mild_deadline,
                result_publicity_release_date__gt=moderate_deadline,
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
            'timely_archived': timely_archived,
            'timely_rate': timely_rate,
            'avg_archive_days': avg_archive_days,
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
        - 及时归档标准 = 在签订后30天内完成归档
        
        Returns:
            dict: 合同归档统计数据
        """
        base_qs = self._get_filtered_contracts()
        
        # 应归档总数
        total = base_qs.count()
        
        # 已归档数量
        archived_qs = base_qs.filter(archive_date__isnull=False)
        archived = archived_qs.count()
        
        # 计算归档及时率（在30天内完成归档的比例）
        timely_archived = 0
        avg_archive_days = 0
        
        if archived > 0:
            # 统计及时归档的数量
            for contract in archived_qs:
                if contract.archive_date and contract.signing_date:
                    days_to_archive = (contract.archive_date - contract.signing_date).days
                    if days_to_archive <= 30:
                        timely_archived += 1
            
            # 计算平均归档周期
            archive_days_list = []
            for contract in archived_qs:
                if contract.archive_date and contract.signing_date:
                    days = (contract.archive_date - contract.signing_date).days
                    archive_days_list.append(days)
            
            if archive_days_list:
                avg_archive_days = round(sum(archive_days_list) / len(archive_days_list), 1)
        
        timely_rate = round((timely_archived / archived * 100), 2) if archived > 0 else 0
        
        # 逾期统计（签订后30天）
        if total > 0:
            deadline = timezone.now().date() - timedelta(days=30)
            overdue = base_qs.filter(
                signing_date__lte=deadline,
                archive_date__isnull=True
            ).count()
            
            # 分级预警
            severe_deadline = timezone.now().date() - timedelta(days=60)  # 超过30天
            moderate_deadline = timezone.now().date() - timedelta(days=46)  # 超过16天
            mild_deadline = deadline  # 超过1天
            
            severe_overdue = base_qs.filter(
                signing_date__lte=severe_deadline,
                archive_date__isnull=True
            ).count()
            
            moderate_overdue = base_qs.filter(
                signing_date__lte=moderate_deadline,
                signing_date__gt=severe_deadline,
                archive_date__isnull=True
            ).count()
            
            mild_overdue = base_qs.filter(
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
            'timely_archived': timely_archived,
            'timely_rate': timely_rate,
            'avg_archive_days': avg_archive_days,
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
    
    def _calculate_overall_timely_rate(self, procurement_stats, contract_stats):
        """
        计算总体归档及时率
        
        综合采购和合同的归档及时率
        
        Args:
            procurement_stats: 采购归档统计
            contract_stats: 合同归档统计
            
        Returns:
            float: 总体归档及时率
        """
        total_archived = procurement_stats['archived'] + contract_stats['archived']
        total_timely = procurement_stats['timely_archived'] + contract_stats['timely_archived']
        
        if total_archived > 0:
            return round((total_timely / total_archived * 100), 2)
        return 0
    
    def get_project_archive_performance(self):
        """
        获取项目维度的归档表现数据，包含各项目的归档完成率与及时率。

        Returns:
            list: 每个项目的统计数据
        """
        project_stats = {}

        def ensure_entry(project_obj):
            key = project_obj.project_code if project_obj else '__unassigned__'
            if key not in project_stats:
                project_stats[key] = {
                    'project_code': project_obj.project_code if project_obj else '',
                    'project_name': project_obj.project_name if project_obj else '未关联项目',
                    'procurement_total': 0,
                    'procurement_archived': 0,
                    'procurement_timely': 0,
                    'contract_total': 0,
                    'contract_archived': 0,
                    'contract_timely': 0,
                }
            return project_stats[key]

        # 采购维度
        for proc in self._get_filtered_procurements().select_related('project'):
            entry = ensure_entry(proc.project)
            entry['procurement_total'] += 1
            if proc.archive_date:
                entry['procurement_archived'] += 1
                if proc.result_publicity_release_date and (proc.archive_date - proc.result_publicity_release_date).days <= 40:
                    entry['procurement_timely'] += 1

        # 合同维度
        for contract in self._get_filtered_contracts().select_related('project'):
            entry = ensure_entry(contract.project)
            entry['contract_total'] += 1
            if contract.archive_date:
                entry['contract_archived'] += 1
                if contract.signing_date and (contract.archive_date - contract.signing_date).days <= 30:
                    entry['contract_timely'] += 1

        performance_list = []
        for entry in project_stats.values():
            procurement_total = entry['procurement_total']
            contract_total = entry['contract_total']
            procurement_archived = entry['procurement_archived']
            contract_archived = entry['contract_archived']
            procurement_timely = entry['procurement_timely']
            contract_timely = entry['contract_timely']

            entry['procurement_rate'] = round((procurement_archived / procurement_total * 100), 2) if procurement_total else 0
            entry['procurement_timely_rate'] = round((procurement_timely / procurement_archived * 100), 2) if procurement_archived else 0
            entry['contract_rate'] = round((contract_archived / contract_total * 100), 2) if contract_total else 0
            entry['contract_timely_rate'] = round((contract_timely / contract_archived * 100), 2) if contract_archived else 0

            performance_list.append(entry)

        # 按采购归档率排序
        performance_list.sort(key=lambda item: item['procurement_rate'], reverse=True)
        return performance_list

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
        
        queryset = self._get_filtered_procurements().filter(
            result_publicity_release_date__lte=deadline,
            archive_date__isnull=True
        ).select_related('project')
        
        # 单项目筛选（用于详情页）
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        overdue_list = []
        for proc in queryset:
            if not proc.result_publicity_release_date:
                continue
            overdue_days = (timezone.now().date() - proc.result_publicity_release_date).days - 40
            
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
                'reference_date': proc.result_publicity_release_date,
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
        
        queryset = self._get_filtered_contracts().filter(
            signing_date__lte=deadline,
            archive_date__isnull=True
        ).select_related('project')
        
        # 单项目筛选（用于详情页）
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
