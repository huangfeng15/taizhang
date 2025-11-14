"""
齐全性检查统计服务
负责计算项目和个人的字段齐全性统计数据
参照归档监控的成功设计模式
"""
from django.db.models import Q, Count, Avg
from procurement.models import Procurement
from contract.models import Contract
from project.models import Project
from project.enums import FilePositioning
from project.services.completeness import (
    get_enabled_fields,
    check_procurement_field_completeness,
    check_contract_field_completeness
)


class CompletenessStatisticsService:
    """齐全性统计服务类（遵循SRP原则）"""

    def __init__(self):
        pass

    def get_projects_completeness_overview(self, year_filter=None, project_filter=None):
        """
        获取项目维度的齐全性概览
        
        Args:
            year_filter: str - 年度筛选（'all' 或具体年份）
            project_filter: str or None - 项目编码筛选
        
        Returns:
            dict: {
                'summary': {汇总统计},
                'projects': [{项目列表}]
            }
        """
        # 获取项目列表
        projects_qs = Project.objects.all()
        if project_filter:
            projects_qs = projects_qs.filter(project_code=project_filter)
        
        projects_data = []
        total_procurement_count = 0
        total_procurement_complete = 0
        total_contract_count = 0
        total_contract_complete = 0
        
        for project in projects_qs:
            # 计算该项目的采购齐全性
            procurement_stats = self._calculate_project_procurement_completeness(
                project_code=project.project_code,
                year_filter=year_filter
            )
            
            # 计算该项目的合同齐全性
            contract_stats = self._calculate_project_contract_completeness(
                project_code=project.project_code,
                year_filter=year_filter
            )
            
            # 计算综合齐全率
            total_records = procurement_stats['total_count'] + contract_stats['total_count']
            if total_records > 0:
                # 采购和合同齐全率的加权平均
                overall_rate = (
                    procurement_stats['completeness_rate'] * procurement_stats['total_count'] +
                    contract_stats['completeness_rate'] * contract_stats['total_count']
                ) / total_records
            else:
                overall_rate = 0
            
            # 只有当项目有数据时才加入列表
            if total_records > 0:
                projects_data.append({
                    'project_code': project.project_code,
                    'project_name': project.project_name,
                    'procurement_count': procurement_stats['total_count'],
                    'procurement_complete': procurement_stats['complete_count'],
                    'procurement_rate': round(procurement_stats['completeness_rate'], 2),
                    'contract_count': contract_stats['total_count'],
                    'contract_complete': contract_stats['complete_count'],
                    'contract_rate': round(contract_stats['completeness_rate'], 2),
                    'overall_rate': round(overall_rate, 2)
                })
                
                # 累加到汇总数据
                total_procurement_count += procurement_stats['total_count']
                total_procurement_complete += procurement_stats['complete_count']
                total_contract_count += contract_stats['total_count']
                total_contract_complete += contract_stats['complete_count']
        
        # 按综合齐全率降序排序
        projects_data.sort(key=lambda x: x['overall_rate'], reverse=True)
        
        # 计算汇总统计
        total_all = total_procurement_count + total_contract_count
        if total_all > 0:
            overall_rate = (
                (total_procurement_complete / total_procurement_count * 100 if total_procurement_count > 0 else 0) * total_procurement_count +
                (total_contract_complete / total_contract_count * 100 if total_contract_count > 0 else 0) * total_contract_count
            ) / total_all
        else:
            overall_rate = 0
        
        summary = {
            'project_count': len(projects_data),
            'procurement_total': total_procurement_count,
            'procurement_complete': total_procurement_complete,
            'procurement_rate': round(total_procurement_complete / total_procurement_count * 100, 1) if total_procurement_count > 0 else 0,
            'contract_total': total_contract_count,
            'contract_complete': total_contract_complete,
            'contract_rate': round(total_contract_complete / total_contract_count * 100, 1) if total_contract_count > 0 else 0,
            'overall_rate': round(overall_rate, 1)
        }
        
        return {
            'summary': summary,
            'projects': projects_data
        }

    def get_persons_completeness_overview(self, year_filter=None, project_filter=None):
        """
        获取个人维度的齐全性概览
        
        Args:
            year_filter: str - 年度筛选
            project_filter: str or None - 项目筛选（影响经办人范围）
        
        Returns:
            dict: {
                'summary': {汇总统计},
                'persons': [{经办人列表}]
            }
        """
        # 获取所有经办人名单
        person_names = set()
        
        # 采购经办人
        procurement_qs = Procurement.objects.filter(procurement_officer__isnull=False)
        if year_filter and year_filter != 'all':
            procurement_qs = procurement_qs.filter(result_publicity_release_date__year=int(year_filter))
        if project_filter:
            procurement_qs = procurement_qs.filter(project_id=project_filter)
        person_names.update(procurement_qs.values_list('procurement_officer', flat=True).distinct())
        
        # 合同经办人
        contract_qs = Contract.objects.filter(
            contract_officer__isnull=False,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
        )
        if year_filter and year_filter != 'all':
            contract_qs = contract_qs.filter(signing_date__year=int(year_filter))
        if project_filter:
            contract_qs = contract_qs.filter(project_id=project_filter)
        person_names.update(contract_qs.values_list('contract_officer', flat=True).distinct())
        
        persons_data = []
        total_procurement_count = 0
        total_procurement_complete = 0
        total_contract_count = 0
        total_contract_complete = 0
        
        for person_name in person_names:
            # 计算该经办人的采购齐全性
            procurement_stats = self._calculate_person_procurement_completeness(
                person_name=person_name,
                year_filter=year_filter,
                project_filter=project_filter
            )
            
            # 计算该经办人的合同齐全性
            contract_stats = self._calculate_person_contract_completeness(
                person_name=person_name,
                year_filter=year_filter,
                project_filter=project_filter
            )
            
            # 计算负责的项目数
            project_count = self._get_person_project_count(
                person_name=person_name,
                year_filter=year_filter,
                project_filter=project_filter
            )
            
            # 计算综合齐全率
            total_records = procurement_stats['total_count'] + contract_stats['total_count']
            if total_records > 0:
                overall_rate = (
                    procurement_stats['completeness_rate'] * procurement_stats['total_count'] +
                    contract_stats['completeness_rate'] * contract_stats['total_count']
                ) / total_records
            else:
                overall_rate = 0
            
            # 只有当经办人有数据时才加入列表
            if total_records > 0:
                persons_data.append({
                    'handler_name': person_name,
                    'project_count': project_count,
                    'procurement_count': procurement_stats['total_count'],
                    'procurement_complete': procurement_stats['complete_count'],
                    'procurement_rate': round(procurement_stats['completeness_rate'], 2),
                    'contract_count': contract_stats['total_count'],
                    'contract_complete': contract_stats['complete_count'],
                    'contract_rate': round(contract_stats['completeness_rate'], 2),
                    'overall_rate': round(overall_rate, 2)
                })
                
                # 累加到汇总数据
                total_procurement_count += procurement_stats['total_count']
                total_procurement_complete += procurement_stats['complete_count']
                total_contract_count += contract_stats['total_count']
                total_contract_complete += contract_stats['complete_count']
        
        # 按综合齐全率降序排序
        persons_data.sort(key=lambda x: x['overall_rate'], reverse=True)
        
        # 计算汇总统计
        total_all = total_procurement_count + total_contract_count
        if total_all > 0:
            overall_rate = (
                (total_procurement_complete / total_procurement_count * 100 if total_procurement_count > 0 else 0) * total_procurement_count +
                (total_contract_complete / total_contract_count * 100 if total_contract_count > 0 else 0) * total_contract_count
            ) / total_all
        else:
            overall_rate = 0
        
        summary = {
            'person_count': len(persons_data),
            'procurement_total': total_procurement_count,
            'procurement_complete': total_procurement_complete,
            'procurement_rate': round(total_procurement_complete / total_procurement_count * 100, 1) if total_procurement_count > 0 else 0,
            'contract_total': total_contract_count,
            'contract_complete': total_contract_complete,
            'contract_rate': round(total_contract_complete / total_contract_count * 100, 1) if total_contract_count > 0 else 0,
            'overall_rate': round(overall_rate, 1)
        }
        
        return {
            'summary': summary,
            'persons': persons_data
        }

    def get_project_completeness_detail(self, project_code, year_filter=None):
        """
        获取单个项目的齐全性详情
        
        Args:
            project_code: 项目编码
            year_filter: 年度筛选
        
        Returns:
            dict: {
                'summary': {统计概要},
                'field_stats': {字段级统计},
                'incomplete_records': {不完整记录}
            }
        """
        # 获取采购字段统计
        procurement_result = check_procurement_field_completeness(
            year=int(year_filter) if year_filter and year_filter != 'all' else None,
            project_codes=[project_code]
        )
        
        # 获取合同字段统计
        contract_result = check_contract_field_completeness(
            year=int(year_filter) if year_filter and year_filter != 'all' else None,
            project_codes=[project_code]
        )
        
        # 计算综合齐全率
        total_count = procurement_result['total_count'] + contract_result['total_count']
        if total_count > 0:
            overall_rate = (
                procurement_result['completeness_rate'] * procurement_result['total_count'] +
                contract_result['completeness_rate'] * contract_result['total_count']
            ) / total_count
        else:
            overall_rate = 0
        
        summary = {
            'procurement': {
                'total_count': procurement_result['total_count'],
                'completeness_rate': procurement_result['completeness_rate'],
                'field_count': procurement_result['field_count']
            },
            'contract': {
                'total_count': contract_result['total_count'],
                'completeness_rate': contract_result['completeness_rate'],
                'field_count': contract_result['field_count']
            },
            'overall_rate': round(overall_rate, 2)
        }
        
        return {
            'summary': summary,
            'procurement_field_stats': procurement_result['field_stats'],
            'contract_field_stats': contract_result['field_stats'],
            'procurement_incomplete': procurement_result['incomplete_records'],
            'contract_incomplete': contract_result['incomplete_records']
        }

    def get_person_completeness_detail(self, person_name, year_filter=None, project_filter=None):
        """
        获取单个经办人的齐全性详情
        
        Args:
            person_name: 经办人姓名
            year_filter: 年度筛选
            project_filter: 项目筛选
        
        Returns:
            dict: 同 get_project_completeness_detail
        """
        # 获取该经办人的采购记录
        procurement_codes = list(
            Procurement.objects.filter(procurement_officer=person_name)
            .values_list('project__project_code', flat=True)
            .distinct()
        )
        
        # 获取该经办人的合同记录
        contract_codes = list(
            Contract.objects.filter(contract_officer=person_name)
            .values_list('project__project_code', flat=True)
            .distinct()
        )
        
        # 合并项目编码
        project_codes = list(set(procurement_codes + contract_codes))
        if project_filter:
            project_codes = [project_filter]
        
        # 获取采购字段统计（筛选该经办人的记录）
        procurement_result = self._get_person_procurement_field_stats(
            person_name=person_name,
            year_filter=year_filter,
            project_filter=project_filter
        )
        
        # 获取合同字段统计（筛选该经办人的记录）
        contract_result = self._get_person_contract_field_stats(
            person_name=person_name,
            year_filter=year_filter,
            project_filter=project_filter
        )
        
        # 计算综合齐全率
        total_count = procurement_result['total_count'] + contract_result['total_count']
        if total_count > 0:
            overall_rate = (
                procurement_result['completeness_rate'] * procurement_result['total_count'] +
                contract_result['completeness_rate'] * contract_result['total_count']
            ) / total_count
        else:
            overall_rate = 0
        
        summary = {
            'procurement': {
                'total_count': procurement_result['total_count'],
                'completeness_rate': procurement_result['completeness_rate'],
                'field_count': procurement_result['field_count']
            },
            'contract': {
                'total_count': contract_result['total_count'],
                'completeness_rate': contract_result['completeness_rate'],
                'field_count': contract_result['field_count']
            },
            'overall_rate': round(overall_rate, 2),
            'project_count': len(project_codes)
        }
        
        return {
            'summary': summary,
            'procurement_field_stats': procurement_result['field_stats'],
            'contract_field_stats': contract_result['field_stats'],
            'procurement_incomplete': procurement_result['incomplete_records'],
            'contract_incomplete': contract_result['incomplete_records']
        }

    def _calculate_project_procurement_completeness(self, project_code, year_filter=None):
        """计算项目的采购齐全性"""
        required_fields = get_enabled_fields('procurement')
        
        queryset = Procurement.objects.filter(project_id=project_code)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(result_publicity_release_date__year=int(year_filter))
        
        total_count = queryset.count()
        if total_count == 0:
            return {'total_count': 0, 'complete_count': 0, 'completeness_rate': 0}
        
        # 计算齐全率：总填写单元格数 / 总单元格数
        total_cells = total_count * len(required_fields)
        filled_cells = 0
        complete_count = 0  # 所有字段都填写完整的记录数
        
        for record in queryset:
            filled_in_record = 0
            for field_name in required_fields:
                value = getattr(record, field_name, None)
                if value is not None and value != '':
                    filled_cells += 1
                    filled_in_record += 1
            
            # 统计完全填写的记录数
            if filled_in_record == len(required_fields):
                complete_count += 1
        
        completeness_rate = round(filled_cells / total_cells * 100, 2) if total_cells > 0 else 0
        
        return {
            'total_count': total_count,
            'complete_count': complete_count,
            'completeness_rate': completeness_rate
        }

    def _calculate_project_contract_completeness(self, project_code, year_filter=None):
        """计算项目的合同齐全性"""
        required_fields = get_enabled_fields('contract')
        
        queryset = Contract.objects.filter(
            project_id=project_code,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
        )
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(signing_date__year=int(year_filter))
        
        total_count = queryset.count()
        if total_count == 0:
            return {'total_count': 0, 'complete_count': 0, 'completeness_rate': 0}
        
        # 计算齐全率：总填写单元格数 / 总单元格数
        total_cells = total_count * len(required_fields)
        filled_cells = 0
        complete_count = 0  # 所有字段都填写完整的记录数
        
        for record in queryset:
            filled_in_record = 0
            for field_name in required_fields:
                value = getattr(record, field_name, None)
                if value is not None and value != '':
                    filled_cells += 1
                    filled_in_record += 1
            
            # 统计完全填写的记录数
            if filled_in_record == len(required_fields):
                complete_count += 1
        
        completeness_rate = round(filled_cells / total_cells * 100, 2) if total_cells > 0 else 0
        
        return {
            'total_count': total_count,
            'complete_count': complete_count,
            'completeness_rate': completeness_rate
        }

    def _calculate_person_procurement_completeness(self, person_name, year_filter=None, project_filter=None):
        """计算经办人的采购齐全性"""
        required_fields = get_enabled_fields('procurement')
        
        queryset = Procurement.objects.filter(procurement_officer=person_name)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(result_publicity_release_date__year=int(year_filter))
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        
        total_count = queryset.count()
        if total_count == 0:
            return {'total_count': 0, 'complete_count': 0, 'completeness_rate': 0}
        
        # 计算齐全率：总填写单元格数 / 总单元格数
        total_cells = total_count * len(required_fields)
        filled_cells = 0
        complete_count = 0  # 所有字段都填写完整的记录数
        
        for record in queryset:
            filled_in_record = 0
            for field_name in required_fields:
                value = getattr(record, field_name, None)
                if value is not None and value != '':
                    filled_cells += 1
                    filled_in_record += 1
            
            # 统计完全填写的记录数
            if filled_in_record == len(required_fields):
                complete_count += 1
        
        completeness_rate = round(filled_cells / total_cells * 100, 2) if total_cells > 0 else 0
        
        return {
            'total_count': total_count,
            'complete_count': complete_count,
            'completeness_rate': completeness_rate
        }

    def _calculate_person_contract_completeness(self, person_name, year_filter=None, project_filter=None):
        """计算经办人的合同齐全性"""
        required_fields = get_enabled_fields('contract')
        
        queryset = Contract.objects.filter(
            contract_officer=person_name,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
        )
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(signing_date__year=int(year_filter))
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        
        total_count = queryset.count()
        if total_count == 0:
            return {'total_count': 0, 'complete_count': 0, 'completeness_rate': 0}
        
        # 计算齐全率：总填写单元格数 / 总单元格数
        total_cells = total_count * len(required_fields)
        filled_cells = 0
        complete_count = 0  # 所有字段都填写完整的记录数
        
        for record in queryset:
            filled_in_record = 0
            for field_name in required_fields:
                value = getattr(record, field_name, None)
                if value is not None and value != '':
                    filled_cells += 1
                    filled_in_record += 1
            
            # 统计完全填写的记录数
            if filled_in_record == len(required_fields):
                complete_count += 1
        
        completeness_rate = round(filled_cells / total_cells * 100, 2) if total_cells > 0 else 0
        
        return {
            'total_count': total_count,
            'complete_count': complete_count,
            'completeness_rate': completeness_rate
        }

    def _get_person_procurement_field_stats(self, person_name, year_filter=None, project_filter=None):
        """获取经办人的采购字段统计"""
        required_fields = get_enabled_fields('procurement')
        
        queryset = Procurement.objects.filter(procurement_officer=person_name)
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(result_publicity_release_date__year=int(year_filter))
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        
        total_count = queryset.count()
        if total_count == 0:
            return {
                'total_count': 0,
                'completeness_rate': 0,
                'field_count': len(required_fields),
                'field_stats': [],
                'incomplete_records': []
            }
        
        # 统计每个字段的填写情况
        field_stats = []
        for field_name in required_fields:
            filled_count = 0
            for record in queryset:
                value = getattr(record, field_name, None)
                if value is not None and value != '':
                    filled_count += 1
            
            fill_rate = (filled_count / total_count) * 100 if total_count > 0 else 0
            field_stats.append({
                'field_name': field_name,
                'field_label': Procurement._meta.get_field(field_name).verbose_name,
                'filled_count': filled_count,
                'fill_rate': round(fill_rate, 2)
            })
        
        # 计算不完整记录
        incomplete_records = []
        for record in queryset:
            filled_fields = 0
            missing_fields = []
            
            for field_name in required_fields:
                value = getattr(record, field_name, None)
                if value is not None and value != '':
                    filled_fields += 1
                else:
                    field_label = Procurement._meta.get_field(field_name).verbose_name
                    missing_fields.append(field_label)
            
            completeness = (filled_fields / len(required_fields)) * 100
            
            if completeness < 100:
                incomplete_records.append({
                    'code': record.procurement_code,
                    'name': record.project_name,
                    'project_code': record.project_id if record.project_id else '',
                    'completeness': round(completeness, 2),
                    'filled_count': filled_fields,
                    'total_fields': len(required_fields),
                    'missing_fields': missing_fields[:5],
                    'missing_count': len(missing_fields)
                })
        
        # 计算总体齐全率
        total_filled = sum(stat['filled_count'] for stat in field_stats)
        total_cells = total_count * len(required_fields)
        overall_completeness = (total_filled / total_cells) * 100 if total_cells > 0 else 0
        
        return {
            'total_count': total_count,
            'completeness_rate': round(overall_completeness, 2),
            'field_count': len(required_fields),
            'field_stats': field_stats,
            'incomplete_records': incomplete_records[:50]
        }

    def _get_person_contract_field_stats(self, person_name, year_filter=None, project_filter=None):
        """获取经办人的合同字段统计"""
        required_fields = get_enabled_fields('contract')
        
        queryset = Contract.objects.filter(
            contract_officer=person_name,
            file_positioning=FilePositioning.MAIN_CONTRACT.value
        )
        if year_filter and year_filter != 'all':
            queryset = queryset.filter(signing_date__year=int(year_filter))
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        
        total_count = queryset.count()
        if total_count == 0:
            return {
                'total_count': 0,
                'completeness_rate': 0,
                'field_count': len(required_fields),
                'field_stats': [],
                'incomplete_records': []
            }
        
        # 统计每个字段的填写情况
        field_stats = []
        for field_name in required_fields:
            filled_count = 0
            for record in queryset:
                value = getattr(record, field_name, None)
                if value is not None and value != '':
                    filled_count += 1
            
            fill_rate = (filled_count / total_count) * 100 if total_count > 0 else 0
            field_stats.append({
                'field_name': field_name,
                'field_label': Contract._meta.get_field(field_name).verbose_name,
                'filled_count': filled_count,
                'fill_rate': round(fill_rate, 2)
            })
        
        # 计算不完整记录
        incomplete_records = []
        for record in queryset:
            filled_fields = 0
            missing_fields = []
            
            for field_name in required_fields:
                value = getattr(record, field_name, None)
                if value is not None and value != '':
                    filled_fields += 1
                else:
                    field_label = Contract._meta.get_field(field_name).verbose_name
                    missing_fields.append(field_label)
            
            completeness = (filled_fields / len(required_fields)) * 100
            
            if completeness < 100:
                incomplete_records.append({
                    'code': record.contract_code,
                    'name': record.contract_name,
                    'project_code': record.project_id if record.project_id else '',
                    'completeness': round(completeness, 2),
                    'filled_count': filled_fields,
                    'total_fields': len(required_fields),
                    'missing_fields': missing_fields[:5],
                    'missing_count': len(missing_fields)
                })
        
        # 计算总体齐全率
        total_filled = sum(stat['filled_count'] for stat in field_stats)
        total_cells = total_count * len(required_fields)
        overall_completeness = (total_filled / total_cells) * 100 if total_cells > 0 else 0
        
        return {
            'total_count': total_count,
            'completeness_rate': round(overall_completeness, 2),
            'field_count': len(required_fields),
            'field_stats': field_stats,
            'incomplete_records': incomplete_records[:50]
        }

    def _get_person_project_count(self, person_name, year_filter=None, project_filter=None):
        """获取经办人负责的项目数"""
        project_ids = set()
        
        # 从采购中获取项目
        procurement_qs = Procurement.objects.filter(procurement_officer=person_name)
        if year_filter and year_filter != 'all':
            procurement_qs = procurement_qs.filter(result_publicity_release_date__year=int(year_filter))
        if project_filter:
            procurement_qs = procurement_qs.filter(project_id=project_filter)
        project_ids.update(procurement_qs.values_list('project_id', flat=True).distinct())
        
        # 从合同中获取项目
        contract_qs = Contract.objects.filter(contract_officer=person_name)
        if year_filter and year_filter != 'all':
            contract_qs = contract_qs.filter(signing_date__year=int(year_filter))
        if project_filter:
            contract_qs = contract_qs.filter(project_id=project_filter)
        project_ids.update(contract_qs.values_list('project_id', flat=True).distinct())
        
        return len(project_ids)