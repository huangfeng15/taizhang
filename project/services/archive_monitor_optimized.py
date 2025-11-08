"""
归档监控服务 - 性能优化版本
通过数据库查询优化和缓存机制提升性能
"""
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Prefetch, Count, Q, F
from datetime import timedelta
from procurement.models import Procurement
from contract.models import Contract
from project.enums import FilePositioning


class ArchiveMonitorServiceOptimized:
    """归档监控服务 - 优化版"""
    
    # 缓存过期时间（秒）
    CACHE_TIMEOUT = 300  # 5分钟
    
    def __init__(self, year=None, project_codes=None):
        self.year = year
        self.project_codes = project_codes
        self._cache_key = self._generate_cache_key()
    
    def _generate_cache_key(self):
        """生成缓存键"""
        year_str = str(self.year) if self.year else 'all'
        projects_str = '_'.join(sorted(self.project_codes)) if self.project_codes else 'all'
        return f'archive_monitor:{year_str}:{projects_str}'
    
    def get_archive_overview(self, use_cache=True):
        """获取归档总览数据（带缓存）"""
        if use_cache:
            cached_data = cache.get(self._cache_key)
            if cached_data:
                return cached_data
        
        # 使用优化的查询
        procurement_stats = self._get_procurement_archive_stats_optimized()
        contract_stats = self._get_contract_archive_stats_optimized()
        settlement_stats = self._get_settlement_archive_stats()
        
        overall_rate = self._calculate_overall_rate(
            procurement_stats, contract_stats, settlement_stats
        )
        overall_timely_rate = self._calculate_overall_timely_rate(
            procurement_stats, contract_stats
        )
        
        result = {
            'procurement': procurement_stats,
            'contract': contract_stats,
            'settlement': settlement_stats,
            'overall_rate': overall_rate,
            'overall_timely_rate': overall_timely_rate,
            'last_updated': timezone.now()
        }
        
        if use_cache:
            cache.set(self._cache_key, result, self.CACHE_TIMEOUT)
        
        return result
    
    def _get_filtered_procurements(self):
        """获取过滤后的采购查询集（优化版）"""
        qs = Procurement.objects.select_related('project').filter(
            result_publicity_release_date__isnull=False
        )
        if self.year:
            qs = qs.filter(result_publicity_release_date__year=self.year)
        if self.project_codes:
            qs = qs.filter(project__project_code__in=self.project_codes)
        return qs
    
    def _get_filtered_contracts(self):
        """获取过滤后的合同查询集（优化版）"""
        qs = Contract.objects.select_related('project').filter(
            file_positioning=FilePositioning.MAIN_CONTRACT.value,
            signing_date__isnull=False
        )
        if self.year:
            qs = qs.filter(signing_date__year=self.year)
        if self.project_codes:
            qs = qs.filter(project__project_code__in=self.project_codes)
        return qs
    
    def _get_procurement_archive_stats_optimized(self):
        """采购归档统计（优化版 - 使用聚合查询）"""
        base_qs = self._get_filtered_procurements()
        
        # 使用聚合查询一次性获取所有统计数据
        stats = base_qs.aggregate(
            total=Count('id'),
            archived=Count('id', filter=Q(archive_date__isnull=False))
        )
        
        total = stats['total']
        archived = stats['archived']
        
        if total == 0:
            return self._empty_stats()
        
        # 批量获取已归档记录用于计算及时率
        archived_records = base_qs.filter(
            archive_date__isnull=False
        ).values('archive_date', 'result_publicity_release_date')
        
        timely_archived = 0
        archive_days_list = []
        
        for record in archived_records:
            if record['archive_date'] and record['result_publicity_release_date']:
                days = (record['archive_date'] - record['result_publicity_release_date']).days
                archive_days_list.append(days)
                if days <= 40:
                    timely_archived += 1
        
        avg_archive_days = round(sum(archive_days_list) / len(archive_days_list), 1) if archive_days_list else 0
        timely_rate = round((timely_archived / archived * 100), 2) if archived > 0 else 0
        
        # 逾期统计（使用数据库查询）
        deadline = timezone.now().date() - timedelta(days=40)
        severe_deadline = timezone.now().date() - timedelta(days=70)
        moderate_deadline = timezone.now().date() - timedelta(days=56)
        
        overdue_stats = base_qs.filter(archive_date__isnull=True).aggregate(
            total_overdue=Count('id', filter=Q(result_publicity_release_date__lte=deadline)),
            severe=Count('id', filter=Q(result_publicity_release_date__lte=severe_deadline)),
            moderate=Count('id', filter=Q(
                result_publicity_release_date__lte=moderate_deadline,
                result_publicity_release_date__gt=severe_deadline
            )),
            mild=Count('id', filter=Q(
                result_publicity_release_date__lte=deadline,
                result_publicity_release_date__gt=moderate_deadline
            ))
        )
        
        return {
            'total': total,
            'archived': archived,
            'unarchived': total - archived,
            'rate': round((archived / total * 100), 2) if total > 0 else 0,
            'timely_archived': timely_archived,
            'timely_rate': timely_rate,
            'avg_archive_days': avg_archive_days,
            'overdue': overdue_stats['total_overdue'],
            'overdue_breakdown': {
                'severe': overdue_stats['severe'],
                'moderate': overdue_stats['moderate'],
                'mild': overdue_stats['mild']
            }
        }
    
    def _get_contract_archive_stats_optimized(self):
        """合同归档统计（优化版）"""
        base_qs = self._get_filtered_contracts()
        
        stats = base_qs.aggregate(
            total=Count('id'),
            archived=Count('id', filter=Q(archive_date__isnull=False))
        )
        
        total = stats['total']
        archived = stats['archived']
        
        if total == 0:
            return self._empty_stats()
        
        # 批量获取已归档记录
        archived_records = base_qs.filter(
            archive_date__isnull=False
        ).values('archive_date', 'signing_date')
        
        timely_archived = 0
        archive_days_list = []
        
        for record in archived_records:
            if record['archive_date'] and record['signing_date']:
                days = (record['archive_date'] - record['signing_date']).days
                archive_days_list.append(days)
                if days <= 30:
                    timely_archived += 1
        
        avg_archive_days = round(sum(archive_days_list) / len(archive_days_list), 1) if archive_days_list else 0
        timely_rate = round((timely_archived / archived * 100), 2) if archived > 0 else 0
        
        # 逾期统计
        deadline = timezone.now().date() - timedelta(days=30)
        severe_deadline = timezone.now().date() - timedelta(days=60)
        moderate_deadline = timezone.now().date() - timedelta(days=46)
        
        overdue_stats = base_qs.filter(archive_date__isnull=True).aggregate(
            total_overdue=Count('id', filter=Q(signing_date__lte=deadline)),
            severe=Count('id', filter=Q(signing_date__lte=severe_deadline)),
            moderate=Count('id', filter=Q(
                signing_date__lte=moderate_deadline,
                signing_date__gt=severe_deadline
            )),
            mild=Count('id', filter=Q(
                signing_date__lte=deadline,
                signing_date__gt=moderate_deadline
            ))
        )
        
        return {
            'total': total,
            'archived': archived,
            'unarchived': total - archived,
            'rate': round((archived / total * 100), 2) if total > 0 else 0,
            'timely_archived': timely_archived,
            'timely_rate': timely_rate,
            'avg_archive_days': avg_archive_days,
            'overdue': overdue_stats['total_overdue'],
            'overdue_breakdown': {
                'severe': overdue_stats['severe'],
                'moderate': overdue_stats['moderate'],
                'mild': overdue_stats['mild']
            }
        }
    
    def _empty_stats(self):
        """返回空统计数据"""
        return {
            'total': 0,
            'archived': 0,
            'unarchived': 0,
            'rate': 0,
            'timely_archived': 0,
            'timely_rate': 0,
            'avg_archive_days': 0,
            'overdue': 0,
            'overdue_breakdown': {'severe': 0, 'moderate': 0, 'mild': 0}
        }
    
    def _get_settlement_archive_stats(self):
        """结算归档统计（占位）"""
        return {
            'total': 0,
            'archived': 0,
            'unarchived': 0,
            'rate': 0,
            'overdue': 0,
            'overdue_breakdown': {'severe': 0, 'moderate': 0, 'mild': 0},
            'note': '结算归档日期字段待补充'
        }
    
    def _calculate_overall_rate(self, procurement_stats, contract_stats, settlement_stats):
        """计算总体归档率"""
        total_items = procurement_stats['total'] + contract_stats['total']
        total_archived = procurement_stats['archived'] + contract_stats['archived']
        return round((total_archived / total_items * 100), 2) if total_items > 0 else 0
    
    def _calculate_overall_timely_rate(self, procurement_stats, contract_stats):
        """计算总体归档及时率"""
        total_archived = procurement_stats['archived'] + contract_stats['archived']
        total_timely = procurement_stats['timely_archived'] + contract_stats['timely_archived']
        return round((total_timely / total_archived * 100), 2) if total_archived > 0 else 0
    
    @classmethod
    def clear_cache(cls, year=None, project_codes=None):
        """清除缓存"""
        year_str = str(year) if year else 'all'
        projects_str = '_'.join(sorted(project_codes)) if project_codes else 'all'
        cache_key = f'archive_monitor:{year_str}:{projects_str}'
        cache.delete(cache_key)