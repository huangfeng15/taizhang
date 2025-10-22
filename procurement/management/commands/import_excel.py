"""
采购台账Excel导入命令
支持标准长表导入和历史宽表转长表转换
"""
import os
import csv
import re
import logging
import chardet
from collections import defaultdict
from bisect import bisect_left, bisect_right, insort
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from project.models import Project
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement
from supplier_eval.models import SupplierEvaluation
from project.validators import validate_code_field, check_url_safe_string

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '从Excel/CSV文件导入采购台账数据（支持长表和宽表转换）'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='要导入的CSV文件路径'
        )
        parser.add_argument(
            '--mode',
            type=str,
            choices=['long', 'wide'],
            default='long',
            help='导入模式：long=长表（默认），wide=宽表转长表'
        )
        parser.add_argument(
            '--module',
            type=str,
            choices=['project', 'procurement', 'contract', 'payment', 'evaluation'],
            default='procurement',
            help='导入模块类型'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8-sig',
            help='文件编码（默认：utf-8-sig）'
        )
        parser.add_argument(
            '--skip-errors',
            action='store_true',
            help='跳过错误行继续导入'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅验证数据，不实际导入'
        )
        parser.add_argument(
            '--conflict-mode',
            type=str,
            choices=['update', 'skip', 'error', 'replace'],
            default='update',
            help='数据冲突处理模式：update=更新现有记录（默认），skip=跳过现有记录，error=报错停止'
        )
        parser.add_argument(
            '--project-code',
            type=str,
            help='replace 模式下需要指定的项目编码，其关联数据会在导入前清空'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        mode = options['mode']
        module = options['module']
        encoding = options['encoding']
        skip_errors = options['skip_errors']
        dry_run = options['dry_run']
        conflict_mode = options['conflict_mode']
        project_code = options.get('project_code')

        # 验证replace模式必须提供project_code
        if conflict_mode == 'replace':
            if not project_code:
                raise CommandError('replace模式必须指定--project-code参数')
            
            # 验证项目是否存在
            try:
                project = Project.objects.get(project_code=project_code)
                self.stdout.write(self.style.WARNING(
                    f'\n⚠️  警告：即将清空项目【{project.project_name}】({project_code})的所有{self._get_module_name(module)}数据！'
                ))
                if not dry_run:
                    self.stdout.write(self.style.ERROR('此操作不可恢复！'))
            except Project.DoesNotExist:
                raise CommandError(f'项目不存在: {project_code}')

        # 验证文件存在
        if not os.path.exists(file_path):
            raise CommandError(f'文件不存在: {file_path}')

        # 自动检测文件编码（如果是CSV文件且用户使用默认编码）
        if file_path.endswith('.csv') and encoding == 'utf-8-sig':
            detected_encoding = self._detect_encoding(file_path)
            if detected_encoding:
                encoding = detected_encoding
                self.stdout.write(f'自动检测到文件编码: {encoding}')

        self.stdout.write(self.style.SUCCESS(f'开始导入文件: {file_path}'))
        self.stdout.write(f'导入模式: {mode} | 模块: {module} | 编码: {encoding}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('*** 预演模式 - 不会实际写入数据库 ***'))

        # 如果是replace模式，先清空项目数据
        if conflict_mode == 'replace' and not dry_run:
            self._clear_project_data(project_code, module)
        
        try:
            if mode == 'long':
                self._handle_long_table(file_path, module, encoding, skip_errors, dry_run, conflict_mode)
            else:
                self._handle_wide_table(file_path, module, encoding, skip_errors, dry_run, conflict_mode)
        except Exception as e:
            logger.exception(f'导入过程中发生错误: {str(e)}')
            raise CommandError(f'导入失败: {str(e)}')
    
    def _get_module_name(self, module):
        """获取模块的中文名称"""
        module_names = {
            'project': '项目',
            'procurement': '采购',
            'contract': '合同',
            'payment': '付款',
            'evaluation': '供应商评价'
        }
        return module_names.get(module, module)
    
    def _clear_project_data(self, project_code, module):
        """清空指定项目的数据"""
        try:
            project = Project.objects.get(project_code=project_code)
        except Project.DoesNotExist:
            raise CommandError(f'项目不存在: {project_code}')
        
        self.stdout.write(self.style.WARNING(f'\n>>> 开始清空项目【{project.project_name}】的{self._get_module_name(module)}数据...'))
        
        deleted_counts = {}
        
        if module == 'procurement':
            # 清空采购数据
            count = Procurement.objects.filter(project=project).count()
            Procurement.objects.filter(project=project).delete()
            deleted_counts['采购记录'] = count
            
        elif module == 'contract':
            # 清空合同及相关付款数据
            contracts = Contract.objects.filter(project=project)
            payment_count = Payment.objects.filter(contract__in=contracts).count()
            Payment.objects.filter(contract__in=contracts).delete()
            deleted_counts['付款记录'] = payment_count
            
            contract_count = contracts.count()
            contracts.delete()
            deleted_counts['合同记录'] = contract_count
            
        elif module == 'payment':
            # 清空付款数据（通过合同关联项目）
            count = Payment.objects.filter(contract__project=project).count()
            Payment.objects.filter(contract__project=project).delete()
            deleted_counts['付款记录'] = count
            
        elif module == 'evaluation':
            # 清空供应商评价数据
            count = SupplierEvaluation.objects.filter(contract__project=project).count()
            SupplierEvaluation.objects.filter(contract__project=project).delete()
            deleted_counts['评价记录'] = count
        
        # 输出删除统计
        self.stdout.write(self.style.SUCCESS('数据清空完成：'))
        for name, count in deleted_counts.items():
            self.stdout.write(f'  - {name}: {count} 条')
        self.stdout.write('')
    
    def _detect_encoding(self, file_path):
        """自动检测文件编码"""
        try:
            # 读取文件的前10000字节用于检测
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)
            
            # 使用chardet检测编码
            result = chardet.detect(raw_data)
            detected_encoding = result['encoding']
            confidence = result['confidence']
            
            # 如果置信度足够高，使用检测到的编码
            if confidence > 0.7:
                # 处理一些常见的编码别名
                encoding_map = {
                    'GB2312': 'gbk',
                    'ISO-8859-1': 'latin1',
                    'ascii': 'utf-8',
                }
                detected_encoding = encoding_map.get(detected_encoding, detected_encoding)
                
                self.stdout.write(self.style.SUCCESS(
                    f'检测到文件编码: {detected_encoding} (置信度: {confidence:.2%})'
                ))
                return detected_encoding
            else:
                self.stdout.write(self.style.WARNING(
                    f'编码检测置信度较低 ({confidence:.2%})，使用默认编码 utf-8-sig'
                ))
                return 'utf-8-sig'
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f'编码检测失败: {str(e)}，使用默认编码 utf-8-sig'
            ))
            return 'utf-8-sig'

    def _handle_long_table(self, file_path, module, encoding, skip_errors, dry_run, conflict_mode):
        """处理长表格式导入"""
        # 如果是合同模块，使用两遍导入策略
        if module == 'contract':
            self._handle_contract_two_pass(file_path, encoding, skip_errors, dry_run, conflict_mode)
        else:
            self._handle_long_table_single_pass(file_path, module, encoding, skip_errors, dry_run, conflict_mode)

    def _handle_long_table_single_pass(self, file_path, module, encoding, skip_errors, dry_run, conflict_mode):
        """处理长表格式导入（单遍导入）"""
        stats = {
            'total_rows': 0,
            'success_rows': 0,
            'error_rows': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
        }
        errors = []

        with open(file_path, 'r', encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row_num, row in enumerate(reader, start=2):  # 从第2行开始计数(第1行是表头)
                # 跳过完全空的行
                if not any(v.strip() for v in row.values() if v):
                    continue
                
                stats['total_rows'] += 1
                
                try:
                    if not dry_run:
                        with transaction.atomic():
                            result = self._import_long_row(row, module, conflict_mode)
                            if result == 'created':
                                stats['created'] += 1
                                stats['success_rows'] += 1
                            elif result == 'updated':
                                stats['updated'] += 1
                                stats['success_rows'] += 1
                            elif result == 'skipped':
                                stats['skipped'] += 1
                                # 跳过的记录不计入成功行数
                    else:
                        self._validate_long_row(row, module)
                        stats['success_rows'] += 1
                    
                    # 每处理10行显示进度（包括跳过的）
                    if (stats['success_rows'] + stats['skipped']) % 10 == 0:
                        self.stdout.write(f'已处理 {stats["success_rows"] + stats["skipped"]} 行...')
                
                except Exception as e:
                    stats['error_rows'] += 1
                    error_msg = f'第 {row_num} 行错误: {str(e)}'
                    errors.append(error_msg)
                    logger.error(error_msg)
                    
                    if not skip_errors:
                        raise CommandError(error_msg)
                    else:
                        self.stdout.write(self.style.WARNING(error_msg))

        self._print_summary(stats, errors)

    def _handle_contract_two_pass(self, file_path, encoding, skip_errors, dry_run, conflict_mode):
        """处理合同导入（两遍导入策略）"""
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('使用两遍导入策略处理合同数据'))
        self.stdout.write(self.style.SUCCESS('第一遍：导入主合同'))
        self.stdout.write(self.style.SUCCESS('第二遍：导入补充协议和解除协议'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        stats = {
            'total_rows': 0,
            'success_rows': 0,
            'error_rows': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
        }
        errors = []
        
        # 第一遍：只导入主合同
        self.stdout.write(self.style.SUCCESS('\n>>> 第一遍：导入主合同'))
        with open(file_path, 'r', encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row_num, row in enumerate(reader, start=2):
                # 跳过完全空的行
                if not any(v.strip() for v in row.values() if v):
                    continue
                
                # 获取合同类型
                contract_type = row.get('合同类型', '主合同').strip()
                if not contract_type:
                    contract_type = '主合同'
                
                # 第一遍只处理主合同
                if contract_type != '主合同':
                    continue
                
                stats['total_rows'] += 1
                
                try:
                    if not dry_run:
                        with transaction.atomic():
                            result = self._import_contract_long(row, conflict_mode)
                            if result == 'created':
                                stats['created'] += 1
                                stats['success_rows'] += 1
                            elif result == 'updated':
                                stats['updated'] += 1
                                stats['success_rows'] += 1
                            elif result == 'skipped':
                                stats['skipped'] += 1
                                # 跳过的记录不计入成功行数
                    else:
                        self._validate_long_row(row, 'contract')
                        stats['success_rows'] += 1
                    
                    # 每处理10行显示进度（包括跳过的）
                    if (stats['success_rows'] + stats['skipped']) % 10 == 0:
                        self.stdout.write(f'已处理 {stats["success_rows"] + stats["skipped"]} 行...')
                
                except Exception as e:
                    stats['error_rows'] += 1
                    error_msg = f'第 {row_num} 行错误: {str(e)}'
                    errors.append(error_msg)
                    logger.error(error_msg)
                    
                    if not skip_errors:
                        raise CommandError(error_msg)
                    else:
                        self.stdout.write(self.style.WARNING(error_msg))
        
        # 第二遍：导入补充协议和解除协议
        self.stdout.write(self.style.SUCCESS('\n>>> 第二遍：导入补充协议和解除协议'))
        with open(file_path, 'r', encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row_num, row in enumerate(reader, start=2):
                # 跳过完全空的行
                if not any(v.strip() for v in row.values() if v):
                    continue
                
                # 获取合同类型
                contract_type = row.get('合同类型', '主合同').strip()
                if not contract_type:
                    contract_type = '主合同'
                
                # 第二遍只处理补充协议和解除协议
                if contract_type not in ['补充协议', '解除协议']:
                    continue
                
                stats['total_rows'] += 1
                
                try:
                    if not dry_run:
                        with transaction.atomic():
                            result = self._import_contract_long(row, conflict_mode)
                            if result == 'created':
                                stats['created'] += 1
                                stats['success_rows'] += 1
                            elif result == 'updated':
                                stats['updated'] += 1
                                stats['success_rows'] += 1
                            elif result == 'skipped':
                                stats['skipped'] += 1
                                # 跳过的记录不计入成功行数
                    else:
                        self._validate_long_row(row, 'contract')
                        stats['success_rows'] += 1
                    
                    # 每处理10行显示进度（包括跳过的）
                    if (stats['success_rows'] + stats['skipped']) % 10 == 0:
                        self.stdout.write(f'已处理 {stats["success_rows"] + stats["skipped"]} 行...')
                
                except Exception as e:
                    stats['error_rows'] += 1
                    error_msg = f'第 {row_num} 行错误: {str(e)}'
                    errors.append(error_msg)
                    logger.error(error_msg)
                    
                    if not skip_errors:
                        raise CommandError(error_msg)
                    else:
                        self.stdout.write(self.style.WARNING(error_msg))

        self._print_summary(stats, errors)

    def _handle_wide_table(self, file_path, module, encoding, skip_errors, dry_run, conflict_mode):
        """处理宽表转长表导入"""
        import pandas as pd
        
        self.stdout.write(f'读取宽表文件...')
        df = pd.read_excel(file_path) if file_path.endswith('.xlsx') else pd.read_csv(
            file_path, encoding=encoding
        )
        
        self.stdout.write(f'原始数据: {len(df)} 行')
        
        # 识别日期列
        date_cols = self._identify_date_columns(df.columns)
        if not date_cols:
            raise CommandError('未能识别任何日期列，请检查文件格式')
        
        self.stdout.write(f'识别到 {len(date_cols)} 个日期列: {date_cols[:5]}... (显示前5个)')
        
        # 确定ID列（供应商评价需要保留供应商名称列）
        if module == 'evaluation':
            # 供应商评价：第1列=合同编号，第2列=供应商名称
            id_cols = [df.columns[0], df.columns[1]]
            group_col = id_cols[0]  # 按合同编号分组
            df_long = pd.melt(
                df,
                id_vars=id_cols,
                value_vars=date_cols,
                var_name='period',
                value_name='value'
            )
        else:
            # 付款：第1列=合同编号，第2列=结算价，第3列=是否已结算
            id_cols = [df.columns[0]]
            # 检查是否有结算相关列
            if len(df.columns) > 1 and '结算价' in df.columns[1]:
                id_cols.append(df.columns[1])
            if len(df.columns) > 2 and '是否' in df.columns[2]:
                id_cols.append(df.columns[2])
            
            group_col = id_cols[0]
            df_long = pd.melt(
                df,
                id_vars=id_cols,
                value_vars=date_cols,
                var_name='period',
                value_name='value'
            )
        
        # 清理空值和零值
        df_long = df_long[df_long['value'].notna()]
        df_long = df_long[df_long['value'].astype(str).str.strip() != '']
        
        self.stdout.write(f'转换后有效记录: {len(df_long)} 条')
        
        stats = {
            'total_rows': len(df_long),
            'success_rows': 0,
            'error_rows': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
        }
        errors = []

        if module == 'payment':
            stats, errors = self._process_payment_wide(
                df_long,
                id_cols,
                group_col,
                skip_errors,
                dry_run,
                conflict_mode,
                stats,
            )
            self._print_summary(stats, errors)
            return

        # 按ID分组处理，但使用全局序号
        global_seq = 0
        for group_id, group_df in df_long.groupby(group_col):
            for idx, (_, row) in enumerate(group_df.iterrows(), start=1):
                global_seq += 1  # 全局序号
                try:
                    if not dry_run:
                        with transaction.atomic():
                            result = self._import_wide_row(row, module, global_seq, group_id, conflict_mode)
                            if result == 'created':
                                stats['created'] += 1
                                stats['success_rows'] += 1
                            elif result == 'updated':
                                stats['updated'] += 1
                                stats['success_rows'] += 1
                            elif result == 'skipped':
                                stats['skipped'] += 1
                                # 跳过的记录不计入成功行数
                    else:
                        self._validate_wide_row(row, module, global_seq, group_id)
                        stats['success_rows'] += 1
                
                except Exception as e:
                    stats['error_rows'] += 1
                    error_msg = f'ID: {group_id}, 第 {idx} 条记录错误: {str(e)}'
                    errors.append(error_msg)
                    logger.error(error_msg)
                    
                    if not skip_errors:
                        raise CommandError(error_msg)
                    else:
                        self.stdout.write(self.style.WARNING(error_msg))

        self._print_summary(stats, errors)

    def _process_payment_wide(self, df_long, id_cols, group_col, skip_errors, dry_run, conflict_mode, stats):
        """批量处理付款宽表数据，降低逐行数据库操作成本"""
        errors = []

        if df_long.empty:
            return stats, errors

        df_long[group_col] = df_long[group_col].astype(str).str.strip()
        contract_cache = self._build_contract_cache(df_long[group_col].unique())
        records_by_contract = defaultdict(list)
        period_cache = {}

        for idx, record in enumerate(df_long.to_dict('records'), start=1):
            contract_key = str(record.get(group_col, '')).strip()
            if not contract_key or contract_key.lower() == 'nan':
                error_msg = f'第 {idx} 条记录缺少合同编号'
                stats['error_rows'] += 1
                errors.append(error_msg)
                logger.error(error_msg)
                if not skip_errors:
                    raise CommandError(error_msg)
                self.stdout.write(self.style.WARNING(error_msg))
                continue

            contract = contract_cache.get(contract_key)
            if not contract:
                error_msg = f'合同序号/编号不存在: {contract_key}'
                stats['error_rows'] += 1
                errors.append(error_msg)
                logger.error(error_msg)
                if not skip_errors:
                    raise CommandError(error_msg)
                self.stdout.write(self.style.WARNING(error_msg))
                continue

            amount = self._parse_decimal(record.get('value'))
            if amount is None or amount <= 0:
                stats['skipped'] += 1
                stats['success_rows'] += 1
                continue

            settlement_amount = None
            if len(id_cols) > 1:
                settlement_amount = self._parse_decimal(record.get(id_cols[1]))

            is_settled = False
            if len(id_cols) > 2:
                is_settled = self._parse_settlement_flag(record.get(id_cols[2]))

            period_label = record.get('period')
            if not period_label:
                error_msg = f'ID: {contract_key}, 第 {idx} 条记录缺少期间列'
                stats['error_rows'] += 1
                errors.append(error_msg)
                logger.error(error_msg)
                if not skip_errors:
                    raise CommandError(error_msg)
                self.stdout.write(self.style.WARNING(error_msg))
                continue

            try:
                if period_label not in period_cache:
                    period_cache[period_label] = self._parse_month_to_date(period_label)
                payment_date = period_cache[period_label]
            except ValueError as exc:
                error_msg = f'ID: {contract_key}, 第 {idx} 条记录日期解析失败: {exc}'
                stats['error_rows'] += 1
                errors.append(error_msg)
                logger.error(error_msg)
                if not skip_errors:
                    raise CommandError(error_msg)
                self.stdout.write(self.style.WARNING(error_msg))
                continue

            base_identifier = self._get_contract_identifier(contract)
            if not base_identifier:
                error_msg = f'合同缺少可用编号: {contract.pk}'
                stats['error_rows'] += 1
                errors.append(error_msg)
                logger.error(error_msg)
                if not skip_errors:
                    raise CommandError(error_msg)
                self.stdout.write(self.style.WARNING(error_msg))
                continue

            records_by_contract[contract.pk].append({
                'contract': contract,
                'payment_amount': amount,
                'payment_date': payment_date,
                'settlement_amount': settlement_amount,
                'is_settled': is_settled,
                'source_index': idx,
                'base_identifier': base_identifier,
            })
            stats['success_rows'] += 1

        if not records_by_contract:
            return stats, errors

        if dry_run:
            return stats, errors

        if conflict_mode not in ['update', 'replace']:
            for recs in records_by_contract.values():
                stats['skipped'] += len(recs)
            return stats, errors

        contract_pks = list(records_by_contract.keys())
        existing_payments = Payment.objects.filter(contract__contract_code__in=contract_pks).select_related('contract')
        existing_by_contract = defaultdict(list)
        existing_by_code = {}
        for payment in existing_payments:
            existing_by_contract[payment.contract.pk].append(payment)
            existing_by_code[payment.payment_code] = payment

        prepared_entries = []
        for contract_pk, recs in records_by_contract.items():
            contract = recs[0]['contract']
            base_identifier = recs[0]['base_identifier']
            # 按付款日期和来源索引排序（保证顺序一致性）
            recs.sort(key=lambda item: (item['payment_date'], item['source_index']))

            # 获取该合同的现有付款记录，按日期排序
            existing_list = existing_by_contract.get(contract_pk, [])
            existing_list.sort(key=lambda item: (item.payment_date, item.created_at, item.payment_code))
            
            # 合并现有付款和新付款的日期列表，用于计算正确的序号
            # 对于每笔新付款，计算它在整个时间线中的位置
            for record in recs:
                payment_date = record['payment_date']
                
                # 计算有多少现有付款的日期早于或等于当前付款日期
                earlier_existing = sum(1 for p in existing_list if p.payment_date < payment_date)
                same_date_existing = sum(1 for p in existing_list if p.payment_date == payment_date)
                
                # 计算有多少本批次的付款日期早于当前付款日期
                earlier_new = sum(1 for r in prepared_entries if r['payment_date'] < payment_date)
                same_date_new = sum(1 for r in prepared_entries if r['payment_date'] == payment_date)
                
                # 序号 = 所有早于该日期的付款 + 该日期的现有付款 + 该日期的新付款 + 1
                seq = earlier_existing + earlier_new + same_date_existing + same_date_new + 1
                payment_code = f"{base_identifier}-FK-{seq:03d}"

                prepared_entries.append({
                    'payment_code': payment_code,
                    'contract': contract,
                    'payment_amount': record['payment_amount'],
                    'payment_date': payment_date,
                    'settlement_amount': record['settlement_amount'],
                    'is_settled': record['is_settled'],
                })

        if not prepared_entries:
            return stats, errors

        now = timezone.now()
        to_update = []
        to_create = []

        for entry in prepared_entries:
            existing = existing_by_code.get(entry['payment_code'])
            if existing:
                existing.contract = entry['contract']
                existing.payment_amount = entry['payment_amount']
                existing.payment_date = entry['payment_date']
                existing.settlement_amount = entry['settlement_amount']
                existing.is_settled = entry['is_settled']
                existing.updated_at = now
                to_update.append(existing)
                stats['updated'] += 1
            else:
                # 创建付款对象，确保 payment_code 已经正确生成
                payment_obj = Payment(
                    payment_code=entry['payment_code'],
                    contract=entry['contract'],
                    payment_amount=entry['payment_amount'],
                    payment_date=entry['payment_date'],
                    settlement_amount=entry['settlement_amount'],
                    is_settled=entry['is_settled'],
                    created_at=now,
                    updated_at=now,
                )
                to_create.append(payment_obj)
                stats['created'] += 1

        if to_update:
            Payment.objects.bulk_update(
                to_update,
                ['contract', 'payment_amount', 'payment_date', 'settlement_amount', 'is_settled', 'updated_at'],
            )

        if to_create:
            # 使用 bulk_create 前，确保所有 payment_code 都已设置
            # bulk_create 不会调用 save() 方法，因此需要提前验证
            codes_to_create = set(p.payment_code for p in to_create)
            existing_codes = set(Payment.objects.filter(payment_code__in=codes_to_create).values_list('payment_code', flat=True))
            
            # 过滤掉已存在的记录
            if existing_codes:
                self.stdout.write(self.style.WARNING(
                    f'检测到 {len(existing_codes)} 个已存在的付款编号，将跳过这些记录'
                ))
                to_create = [p for p in to_create if p.payment_code not in existing_codes]
                stats['skipped'] += len(existing_codes)
                stats['created'] -= len(existing_codes)
            
            if to_create:
                Payment.objects.bulk_create(to_create, batch_size=500)

        return stats, errors

    def _build_contract_cache(self, identifiers):
        """建立合同缓存，避免重复数据库查询"""
        cleaned = []
        for ident in identifiers:
            if ident is None:
                continue
            ident_str = str(ident).strip()
            if not ident_str or ident_str.lower() == 'nan':
                continue
            cleaned.append(ident_str)

        if not cleaned:
            return {}

        contracts = Contract.objects.filter(
            Q(contract_code__in=cleaned) | Q(contract_sequence__in=cleaned)
        )

        cache = {}
        for contract in contracts:
            if contract.contract_code:
                cache[contract.contract_code.strip()] = contract
            if contract.contract_sequence:
                cache[contract.contract_sequence.strip()] = contract
        return cache

    def _parse_settlement_flag(self, value):
        """解析结算状态标记"""
        if value is None:
            return False
        value_str = str(value).strip()
        if not value_str:
            return False
        if value_str in {'是', '已结算', '已办理', '已完成'}:
            return True
        normalized = value_str.lower()
        return normalized in {'true', '1', 'y', 'yes'}

    def _get_contract_identifier(self, contract):
        """优先返回合同序号，若无则回退到合同编号"""
        identifier = contract.contract_sequence or contract.contract_code
        return identifier.strip() if identifier else None

    def _identify_date_columns(self, columns):
        """识别包含日期信息的列（支持月度和半年度）"""
        # 月度格式：2019年1月、2019-01、2019/01
        month_pattern = re.compile(r'\d{4}\D*\d{1,2}月?')
        # 半年度格式：2019年上半年、2019年下半年
        halfyear_pattern = re.compile(r'\d{4}\D*(上|下)半年')
        
        date_cols = []
        for col in columns:
            col_str = str(col)
            if month_pattern.search(col_str) or halfyear_pattern.search(col_str):
                date_cols.append(col)
        
        return date_cols

    def _parse_month_to_date(self, month_str):
        """将"2022年1月"或"2022年上半年"格式的字符串转换为日期对象"""
        month_str = str(month_str).strip()
        
        # 半年度格式处理：2019年上半年 -> 2019-01-01, 2019年下半年 -> 2019-07-01
        halfyear_match = re.search(r'(\d{4})\D*(上|下)半年', month_str)
        if halfyear_match:
            year = int(halfyear_match.group(1))
            half = halfyear_match.group(2)
            month = 1 if half == '上' else 7
            return datetime(year, month, 1).date()
        
        # 月度格式处理
        formats = [
            (r'(\d{4})\D*(\d{1,2})月?', lambda m: datetime(int(m.group(1)), int(m.group(2)), 1).date()),
            (r'(\d{4})/(\d{1,2})', lambda m: datetime(int(m.group(1)), int(m.group(2)), 1).date()),
            (r'(\d{4})-(\d{1,2})', lambda m: datetime(int(m.group(1)), int(m.group(2)), 1).date()),
        ]
        
        for pattern, converter in formats:
            match = re.search(pattern, month_str)
            if match:
                return converter(match)
        
        raise ValueError(f'无法解析日期: {month_str}')
    
    def _parse_halfyear_period(self, halfyear_str):
        """将"2022年上半年"格式转换为期间字符串"""
        halfyear_str = str(halfyear_str).strip()
        
        halfyear_match = re.search(r'(\d{4})\D*(上|下)半年', halfyear_str)
        if halfyear_match:
            year = int(halfyear_match.group(1))
            half = halfyear_match.group(2)
            if half == '上':
                return f"{year}-01-01至{year}-06-30"
            else:
                return f"{year}-07-01至{year}-12-31"
        
        raise ValueError(f'无法解析半年度: {halfyear_str}')

    def _import_long_row(self, row, module, conflict_mode='update'):
        """导入长表单行数据"""
        if module == 'project':
            return self._import_project_long(row, conflict_mode)
        elif module == 'procurement':
            return self._import_procurement_long(row, conflict_mode)
        elif module == 'contract':
            return self._import_contract_long(row, conflict_mode)
        elif module == 'payment':
            return self._import_payment_long(row, conflict_mode)
        else:
            raise ValueError(f'不支持的模块: {module}')

    def _import_wide_row(self, row, module, seq, group_id, conflict_mode='update'):
        """导入宽表转换后的单行数据"""
        if module == 'payment':
            return self._import_payment_wide(row, seq, group_id, conflict_mode)
        elif module == 'evaluation':
            return self._import_evaluation_wide(row, seq, group_id, conflict_mode)
        else:
            raise ValueError(f'宽表模式不支持模块: {module}')

    def _import_project_long(self, row, conflict_mode='update'):
        """导入项目长表数据"""
        project_code = row.get('项目编码', '').strip()
        project_name = row.get('项目名称', '').strip()
        
        if not project_code:
            raise ValueError('项目编码不能为空')
        if not project_name:
            raise ValueError('项目名称不能为空')
        
        # 验证项目编码格式（不包含URL不安全字符）
        try:
            validate_code_field(project_code)
        except ValidationError as e:
            raise ValueError(f'项目编码格式错误: {e.message}')
        
        # 检查是否已存在
        existing = Project.objects.filter(project_code=project_code).first()
        
        if existing:
            if conflict_mode == 'skip':
                return 'skipped'
        
        if conflict_mode in ['update', 'replace']:
            obj, created = Project.objects.update_or_create(
                project_code=project_code,
                defaults={
                    'project_name': project_name,
                    'description': row.get('项目描述', '').strip(),
                    'project_manager': row.get('项目负责人', '').strip(),
                    'status': row.get('项目状态', '进行中').strip(),
                    'remarks': row.get('备注', '').strip(),
                }
            )
            return 'created' if created else 'updated'
        else:
            # skip模式，不创建新记录
            return 'skipped'

    def _import_procurement_long(self, row, conflict_mode='update'):
        """导入采购长表数据"""
        from project.models import Project
        
        procurement_code = row.get('招采编号', '').strip()
        project_name = row.get('采购名称', '').strip()
        project_code = row.get('项目编码', '').strip()
        
        if not procurement_code:
            raise ValueError('招采编号不能为空')
        if not project_name:
            raise ValueError('采购名称不能为空')
        
        # 验证采购编号格式（不包含URL不安全字符）
        try:
            validate_code_field(procurement_code)
        except ValidationError as e:
            raise ValueError(f'招采编号格式错误: {e.message}')
        
        # 检查是否已存在
        existing = Procurement.objects.filter(procurement_code=procurement_code).first()
        
        if existing:
            if conflict_mode == 'skip':
                return 'skipped'
        
        # 处理项目关联
        project = None
        if project_code:
            try:
                project = Project.objects.get(project_code=project_code)
            except Project.DoesNotExist:
                # 如果项目不存在，记录警告但继续导入
                self.stdout.write(self.style.WARNING(f'项目编码不存在: {project_code}，将不关联项目'))
        
        if conflict_mode in ['update', 'replace']:
            obj, created = Procurement.objects.update_or_create(
                procurement_code=procurement_code,
                defaults={
                    'project': project,
                    'project_name': project_name,
                    'procurement_unit': row.get('采购单位', '').strip(),
                    'planned_completion_date': self._parse_date(row.get('采购计划完成日期')),
                    'requirement_approval_date': self._parse_date(row.get('采购需求书审批完成日期（OA）')),
                    'procurement_officer': row.get('招采经办人', '').strip(),
                    'demand_department': row.get('需求部门', '').strip(),
                    'demand_contact': row.get('需求部门经办人及联系方式', '').strip(),
                    'budget_amount': self._parse_decimal(row.get('预算金额（元）')),
                    'control_price': self._parse_decimal(row.get('采购控制价（元）')),
                    'winning_amount': self._parse_decimal(row.get('中标价（元）')),
                    'procurement_platform': row.get('采购平台', '').strip(),
                    'procurement_method': row.get('采购方式', '').strip(),
                    'bid_evaluation_method': row.get('评标方法', '').strip(),
                    'bid_awarding_method': row.get('定标方法', '').strip(),
                    'bid_opening_date': self._parse_date(row.get('开标日期')),
                    'evaluation_committee': row.get('评标委员会成员', '').strip(),
                    'awarding_committee': row.get('定标委员会成员', '').strip(),
                    'platform_publicity_date': self._parse_date(row.get('平台中标结果公示完成日期（阳光采购平台）')),
                    'notice_issue_date': self._parse_date(row.get('中标通知书发放日期')),
                    'winning_bidder': row.get('中标人', '').strip(),
                    'winning_contact': row.get('中标人联系人及方式', '').strip(),
                    'bid_guarantee': row.get('投标担保形式及金额（元）', '').strip(),
                    'bid_guarantee_return_date': self._parse_date(row.get('中标单位投标担保退回日期')),
                    'performance_guarantee': row.get('履约担保形式及金额（元）', '').strip(),
                    'has_complaint': row.get('全程有无投诉', '').strip(),
                    'non_bidding_explanation': row.get('应招未招说明', '').strip(),
                    'procurement_cost': self._parse_decimal(row.get('招采费用（元）')),
                    'archive_date': self._parse_date(row.get('资料归档日期')),
                }
            )
            return 'created' if created else 'updated'
        else:
            # skip模式，不创建新记录
            return 'skipped'

    def _import_contract_long(self, row, conflict_mode='update'):
        """导入合同长表数据"""
        from project.models import Project
        from procurement.models import Procurement
        
        contract_code = row.get('合同编号', '').strip()
        contract_name = row.get('合同名称', '').strip()
        project_code = row.get('项目编码', '').strip()
        
        if not contract_code:
            raise ValueError('合同编号不能为空')
        if not contract_name:
            raise ValueError('合同名称不能为空')
        
        # 验证合同编号格式（不包含URL不安全字符）
        try:
            validate_code_field(contract_code)
        except ValidationError as e:
            raise ValueError(f'合同编号格式错误: {e.message}')
        
        # 检查是否已存在
        existing = Contract.objects.filter(contract_code=contract_code).first()
        
        if existing:
            if conflict_mode == 'skip':
                return 'skipped'
        
        # 解析合同序号（保持为字符串，支持 BHHY-NH-014 格式）
        contract_sequence = row.get('合同序号', '').strip() or None
        
        # 验证合同序号格式（如果提供了的话）
        if contract_sequence:
            try:
                validate_code_field(contract_sequence)
            except ValidationError as e:
                raise ValueError(f'合同序号格式错误: {e.message}')
        
        # 处理项目关联
        project = None
        if project_code:
            try:
                project = Project.objects.get(project_code=project_code)
            except Project.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'项目编码不存在: {project_code}，将不关联项目'))
        
        # 处理采购关联（优先使用CSV中的关联采购编号）
        procurement = None
        procurement_code = row.get('关联采购编号', '').strip()
        if procurement_code:
            try:
                procurement = Procurement.objects.get(procurement_code=procurement_code)
            except Procurement.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'采购编号不存在: {procurement_code}，将不关联采购'))
        
        # 获取合同类型（第3列），默认为主合同
        contract_type = row.get('合同类型', '主合同').strip()
        if not contract_type:
            contract_type = '主合同'
        
        # 验证合同类型
        valid_types = ['主合同', '补充协议', '解除协议']
        if contract_type not in valid_types:
            self.stdout.write(self.style.WARNING(f'无效的合同类型: {contract_type}，将设置为主合同'))
            contract_type = '主合同'
        
        # 获取合同来源（先获取用户输入的值）
        contract_source = row.get('合同来源', '').strip()
        
        # 处理关联主合同（用于补充协议）
        parent_contract = None
        parent_contract_sequence = row.get('关联主合同编号', '').strip()
        parent_contract_found = False
        
        if parent_contract_sequence:
            # 优先按合同序号查找（支持字符串格式如 BHHY-NH-014）
            try:
                parent_contract = Contract.objects.get(contract_sequence=parent_contract_sequence)
                parent_contract_found = True
            except Contract.DoesNotExist:
                # 如果序号查找失败，尝试按合同编号查找（向后兼容）
                try:
                    parent_contract = Contract.objects.get(contract_code=parent_contract_sequence)
                    parent_contract_found = True
                except Contract.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f'主合同序号/编号不存在: {parent_contract_sequence}，将不关联主合同'
                    ))
        
        # 验证合同类型与关联关系的一致性，并自动继承关联数据
        if contract_type == '主合同':
            if parent_contract:
                self.stdout.write(self.style.WARNING('主合同不能关联其他合同，将清除关联关系'))
                parent_contract = None
        elif contract_type in ['补充协议', '解除协议']:
            # 如果是补充协议或解除协议，必须关联主合同
            if not parent_contract:
                error_msg = (
                    f'{contract_type}必须关联主合同。'
                    f'合同编号: {contract_code}, '
                    f'关联主合同编号: {parent_contract_sequence or "未填写"}'
                )
                raise ValueError(error_msg)
            
            # 自动继承主合同的关联数据
            if parent_contract:
                # 继承采购信息（如果用户没有填写）
                if not procurement and parent_contract.procurement:
                    procurement = parent_contract.procurement
                    self.stdout.write(self.style.SUCCESS(
                        f'{contract_type}自动继承主合同的采购信息: {procurement.procurement_code}'
                    ))
                
                # 继承项目信息（如果用户没有填写）
                if not project and parent_contract.project:
                    project = parent_contract.project
                    self.stdout.write(self.style.SUCCESS(
                        f'{contract_type}自动继承主合同的项目信息: {project.project_code}'
                    ))
                
                # 继承合同来源（如果用户没有填写）
                if not contract_source or contract_source == '':
                    contract_source = parent_contract.contract_source
                    self.stdout.write(self.style.SUCCESS(
                        f'{contract_type}自动继承主合同的合同来源: {contract_source}'
                    ))
        
        # 确保合同来源正确设置（在继承之后再次检查）
        if not contract_source:
            # 如果CSV中没有指定且没有从主合同继承，根据是否有采购关联来设置
            contract_source = '采购合同' if procurement else '直接签订'
        
        # 获取支付方式
        payment_method = row.get('支付方式', '').strip()
        
        if conflict_mode in ['update', 'replace']:
            obj, created = Contract.objects.update_or_create(
                contract_code=contract_code,
                defaults={
                    'project': project,
                    'contract_name': contract_name,
                    'contract_type': contract_type,
                    'contract_source': contract_source,
                    'parent_contract': parent_contract,
                    'procurement': procurement,
                    'contract_sequence': contract_sequence,
                    'contract_officer': row.get('合同签订经办人', '').strip(),
                    'party_a': row.get('甲方', '').strip(),
                    'party_b': row.get('乙方', '').strip(),
                    'party_b_contact': row.get('乙方负责人及联系方式', '').strip(),
                    'party_b_contact_in_contract': row.get('合同文本内乙方联系人及方式', '').strip(),
                    'contract_amount': self._parse_decimal(row.get('含税签约合同价（元）')),
                    'signing_date': self._parse_date(row.get('合同签订日期')),
                    'duration': row.get('合同工期/服务期限', '').strip(),
                    'payment_method': payment_method,
                    'performance_guarantee_return_date': self._parse_date(row.get('履约担保退回时间')),
                }
            )
            return 'created' if created else 'updated'
        else:
            # skip模式，不创建新记录
            return 'skipped'

    def _import_payment_long(self, row, conflict_mode='update'):
        """导入付款长表数据"""
        payment_code = row.get('付款编号', '').strip()
        contract_code = row.get('关联合同编号', '').strip()
        
        if not contract_code:
            raise ValueError('关联合同编号不能为空')
        
        # 验证付款编号格式（如果提供了的话）
        if payment_code:
            try:
                validate_code_field(payment_code)
            except ValidationError as e:
                raise ValueError(f'付款编号格式错误: {e.message}')
        
        try:
            contract = Contract.objects.get(contract_code=contract_code)
        except Contract.DoesNotExist:
            raise ValueError(f'合同编号不存在: {contract_code}')
        
        # 如果付款编号为空，将在模型的save方法中自动生成
        # 如果付款编号不为空，检查是否已存在
        if payment_code:
            existing = Payment.objects.filter(payment_code=payment_code).first()
            
            if existing:
                if conflict_mode == 'skip':
                    return 'skipped'
        
        payment_amount = self._parse_decimal(row.get('实付金额(元)'))
        if payment_amount is None:
            raise ValueError('实付金额不能为空')
        
        payment_date = self._parse_date(row.get('付款日期'))
        if payment_date is None:
            raise ValueError('付款日期不能为空')
        
        # 解析结算相关字段
        settlement_amount = self._parse_decimal(row.get('结算价（元）'))
        is_settled_str = row.get('是否办理结算', '').strip()
        is_settled = is_settled_str in ['是', '已结算', 'True', 'true', '1', 'Y', 'y']
        
        if conflict_mode in ['update', 'replace']:
            if payment_code:
                # 如果提供了付款编号，使用update_or_create
                obj, created = Payment.objects.update_or_create(
                    payment_code=payment_code,
                    defaults={
                        'contract': contract,
                        'payment_amount': payment_amount,
                        'payment_date': payment_date,
                        'settlement_amount': settlement_amount,
                        'is_settled': is_settled,
                    }
                )
                return 'created' if created else 'updated'
            else:
                # 如果没有提供付款编号，创建新记录（会自动生成编号）
                obj = Payment.objects.create(
                    contract=contract,
                    payment_amount=payment_amount,
                    payment_date=payment_date,
                    settlement_amount=settlement_amount,
                    is_settled=is_settled,
                )
                return 'created'
        else:
            # skip模式，不创建新记录
            return 'skipped'

    def _import_payment_wide(self, row, seq, group_id, conflict_mode='update'):
        """导入宽表转换的付款数据"""
        # 第一列：合同编号或合同序号
        contract_identifier = str(row.iloc[0] if hasattr(row, 'iloc') else row[0]).strip()
        
        # 获取结算相关字段（从melt后的DataFrame中获取）
        settlement_amount = None
        is_settled = False
        
        # 检查是否有结算价列
        if len(row) > 3:  # melt后会有: 合同编号, 结算价, 是否已结算, period, value
            settlement_amount = self._parse_decimal(row.iloc[1])
            is_settled_str = str(row.iloc[2]).strip() if len(row) > 2 else ''
            is_settled = is_settled_str in ['是', '已结算', 'True', 'true', '1', 'Y', 'y']
        
        period = row['period']  # 日期列标签
        amount = self._parse_decimal(row['value'])
        
        if amount is None or amount <= 0:
            return 'skipped'
        
        # 尝试通过合同序号查找(优先),如果失败则通过合同编号查找
        contract = None
        try:
            contract = Contract.objects.get(contract_sequence=contract_identifier)
        except Contract.DoesNotExist:
            try:
                contract = Contract.objects.get(contract_code=contract_identifier)
            except Contract.DoesNotExist:
                raise ValueError(f'合同序号/编号不存在: {contract_identifier}')
        
        payment_date = self._parse_month_to_date(period)
        
        # 不再在这里生成付款编号，让Payment模型的save方法自动生成
        # 这样可以使用新的按付款日期排序的逻辑
        # 先创建一个临时的Payment对象来生成编号
        temp_payment = Payment(
            contract=contract,
            payment_amount=amount,
            payment_date=payment_date,
            settlement_amount=settlement_amount,
            is_settled=is_settled,
        )
        # 调用生成方法获取编号
        payment_code = temp_payment._generate_payment_code()
        
        # 检查是否已存在
        existing = Payment.objects.filter(payment_code=payment_code).first()
        
        if existing:
            if conflict_mode == 'skip':
                return 'skipped'
        
        if conflict_mode in ['update', 'replace']:
            obj, created = Payment.objects.update_or_create(
                payment_code=payment_code,
                defaults={
                    'contract': contract,
                    'payment_amount': amount,
                    'payment_date': payment_date,
                    'settlement_amount': settlement_amount,
                    'is_settled': is_settled,
                }
            )
            return 'created' if created else 'updated'
        else:
            # skip模式，不创建新记录
            return 'skipped'

    def _import_evaluation_wide(self, row, seq, group_id, conflict_mode='update'):
        """导入宽表转换的评价数据（支持半年度）"""
        # 第一列是合同编号
        contract_code = row.iloc[0] if hasattr(row, 'iloc') else row[0]
        # 第二列是供应商名称
        supplier_name = row.iloc[1] if hasattr(row, 'iloc') else row[1]
        # period列标签
        period = row['period']
        score = self._parse_decimal(row['value'])
        
        if score is None:
            return 'skipped'
        
        try:
            contract = Contract.objects.get(contract_code=contract_code)
        except Contract.DoesNotExist:
            raise ValueError(f'合同编号不存在: {contract_code}')
        
        evaluation_code = f"{contract_code}-PJ-{seq:03d}"
        
        # 检查是否已存在
        existing = SupplierEvaluation.objects.filter(evaluation_code=evaluation_code).first()
        
        if existing:
            if conflict_mode == 'skip':
                return 'skipped'
        
        # 解析半年度期间
        try:
            evaluation_period = self._parse_halfyear_period(period)
        except ValueError:
            # 如果不是半年度格式，直接使用原字符串
            evaluation_period = str(period)
        
        # 判断评价类型（最后一个半年度为末次评价）
        is_last = '2025年下半年' in str(period)
        evaluation_type = '末次评价' if is_last else '履约过程评价'
        
        if conflict_mode in ['update', 'replace']:
            obj, created = SupplierEvaluation.objects.update_or_create(
                evaluation_code=evaluation_code,
                defaults={
                    'contract': contract,
                    'supplier_name': supplier_name.strip(),
                    'evaluation_period': evaluation_period,
                    'score': score,
                    'evaluation_type': evaluation_type,
                }
            )
            return 'created' if created else 'updated'
        else:
            # skip模式，不创建新记录
            return 'skipped'

    def _validate_long_row(self, row, module):
        """验证长表单行数据"""
        # 基础验证
        pass

    def _validate_wide_row(self, row, module, idx, group_id):
        """验证宽表单行数据"""
        # 基础验证
        pass

    def _parse_decimal(self, value):
        """解析decimal数值"""
        if value is None or value == '':
            return None
        
        # 处理pandas的NaN值
        import math
        if isinstance(value, float) and math.isnan(value):
            return None
        
        value_str = str(value).strip().replace(',', '').replace('，', '')
        # 明确处理常见的空值标记，包括字符串形式的NaN
        if not value_str or value_str in ['/', '-', '—', '无', 'N/A', 'n/a', 'NaN', 'nan', 'None']:
            return None
        
        try:
            return Decimal(value_str)
        except (InvalidOperation, ValueError):
            return None

    def _parse_date(self, value):
        """解析日期"""
        if value is None or value == '':
            return None
        
        value_str = str(value).strip()
        # 明确处理常见的空值标记
        if value_str in ['/', '-', '—', '无', 'N/A', 'n/a']:
            return None
        
        # 尝试多种日期格式
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y年%m月%d日',
            '%Y-%m',
            '%Y/%m',
            '%Y年%m月',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue
        
        return None

    def _parse_enum(self, value, choices):
        """解析枚举值"""
        value = str(value).strip()
        if value in choices:
            return value
        if value == '/' or value == '':
            return None
        
        # 模糊匹配
        for choice in choices:
            if choice in value:
                return choice
        
        return None

    def _print_summary(self, stats, errors):
        """打印导入统计摘要"""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('导入完成！'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'总行数:         {stats["total_rows"]}')
        
        # 计算实际导入数量（新增+更新）
        actual_imported = stats.get("created", 0) + stats.get("updated", 0)
        
        if actual_imported > 0:
            self.stdout.write(self.style.SUCCESS(f'成功导入:       {actual_imported} 条'))
        else:
            self.stdout.write(self.style.WARNING(f'成功导入:       {actual_imported} 条'))
        
        if 'created' in stats and stats.get("created", 0) > 0:
            self.stdout.write(f'  - 新增记录:   {stats.get("created", 0)} 条')
        if 'updated' in stats and stats.get("updated", 0) > 0:
            self.stdout.write(f'  - 更新记录:   {stats.get("updated", 0)} 条')
        
        # 重复数据提示
        if 'skipped' in stats and stats.get("skipped", 0) > 0:
            self.stdout.write(self.style.WARNING(f'跳过重复:       {stats.get("skipped", 0)} 条（数据已存在）'))
        
        # 错误统计
        if stats["error_rows"] > 0:
            self.stdout.write(self.style.ERROR(f'导入失败:       {stats["error_rows"]} 条'))
        
        if errors:
            self.stdout.write('\n' + self.style.WARNING('错误详情:'))
            for error in errors[:10]:  # 只显示前10条
                self.stdout.write(f'  - {error}')
            if len(errors) > 10:
                self.stdout.write(f'  ... 还有 {len(errors) - 10} 条错误')
        
        self.stdout.write('=' * 50)
        
        # 添加友好的总结提示
        if actual_imported == 0 and stats.get("skipped", 0) > 0:
            self.stdout.write(self.style.WARNING(
                f'\n提示：本次未导入任何新数据，所有 {stats.get("skipped", 0)} 条记录均为重复数据。'
            ))
        elif actual_imported > 0 and stats.get("skipped", 0) > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n提示：成功导入 {actual_imported} 条数据，跳过 {stats.get("skipped", 0)} 条重复数据。'
            ))
        elif actual_imported > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n提示：成功导入 {actual_imported} 条数据。'
            ))
