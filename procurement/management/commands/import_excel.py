"""
采购台账Excel导入命令
支持标准长表导入和历史宽表转长表转换
"""
import os
import csv
import re
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from procurement.models import Procurement
from contract.models import Contract
from payment.models import Payment
from settlement.models import Settlement
from supplier_eval.models import SupplierEvaluation

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
            choices=['procurement', 'contract', 'payment', 'evaluation'],
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

    def handle(self, *args, **options):
        file_path = options['file_path']
        mode = options['mode']
        module = options['module']
        encoding = options['encoding']
        skip_errors = options['skip_errors']
        dry_run = options['dry_run']

        # 验证文件存在
        if not os.path.exists(file_path):
            raise CommandError(f'文件不存在: {file_path}')

        self.stdout.write(self.style.SUCCESS(f'开始导入文件: {file_path}'))
        self.stdout.write(f'导入模式: {mode} | 模块: {module}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('*** 预演模式 - 不会实际写入数据库 ***'))

        try:
            if mode == 'long':
                self._handle_long_table(file_path, module, encoding, skip_errors, dry_run)
            else:
                self._handle_wide_table(file_path, module, encoding, skip_errors, dry_run)
        except Exception as e:
            logger.exception(f'导入过程中发生错误: {str(e)}')
            raise CommandError(f'导入失败: {str(e)}')

    def _handle_long_table(self, file_path, module, encoding, skip_errors, dry_run):
        """处理长表格式导入"""
        stats = {
            'total_rows': 0,
            'success_rows': 0,
            'error_rows': 0,
            'created': 0,
            'updated': 0,
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
                            created, updated = self._import_long_row(row, module)
                            if created:
                                stats['created'] += 1
                            if updated:
                                stats['updated'] += 1
                    else:
                        self._validate_long_row(row, module)
                    
                    stats['success_rows'] += 1
                    
                    if stats['success_rows'] % 10 == 0:
                        self.stdout.write(f'已处理 {stats["success_rows"]} 行...')
                
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

    def _handle_wide_table(self, file_path, module, encoding, skip_errors, dry_run):
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
        
        self.stdout.write(f'识别到 {len(date_cols)} 个日期列: {date_cols}')
        
        # 宽表转长表
        id_col = df.columns[0]
        df_long = pd.melt(
            df,
            id_vars=[id_col],
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
        }
        errors = []

        # 按ID分组处理
        for group_id, group_df in df_long.groupby(id_col):
            for idx, (_, row) in enumerate(group_df.iterrows(), start=1):
                try:
                    if not dry_run:
                        with transaction.atomic():
                            self._import_wide_row(row, module, idx, group_id)
                            stats['created'] += 1
                    else:
                        self._validate_wide_row(row, module, idx, group_id)
                    
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

    def _identify_date_columns(self, columns):
        """识别包含日期信息的列"""
        date_pattern = re.compile(r'\d{4}\D*\d{1,2}')
        return [col for col in columns if date_pattern.search(str(col))]

    def _parse_month_to_date(self, month_str):
        """将"2022年1月"格式的字符串转换为日期对象"""
        month_str = str(month_str).strip()
        
        # 尝试多种日期格式
        formats = [
            (r'(\d{4})\D*(\d{1,2})', lambda m: datetime(int(m.group(1)), int(m.group(2)), 1).date()),
            (r'(\d{4})/(\d{1,2})', lambda m: datetime(int(m.group(1)), int(m.group(2)), 1).date()),
            (r'(\d{4})-(\d{1,2})', lambda m: datetime(int(m.group(1)), int(m.group(2)), 1).date()),
        ]
        
        for pattern, converter in formats:
            match = re.search(pattern, month_str)
            if match:
                return converter(match)
        
        raise ValueError(f'无法解析日期: {month_str}')

    def _import_long_row(self, row, module):
        """导入长表单行数据"""
        if module == 'procurement':
            return self._import_procurement_long(row)
        elif module == 'contract':
            return self._import_contract_long(row)
        elif module == 'payment':
            return self._import_payment_long(row)
        else:
            raise ValueError(f'不支持的模块: {module}')

    def _import_wide_row(self, row, module, seq, group_id):
        """导入宽表转换后的单行数据"""
        if module == 'payment':
            return self._import_payment_wide(row, seq, group_id)
        elif module == 'evaluation':
            return self._import_evaluation_wide(row, seq, group_id)
        else:
            raise ValueError(f'宽表模式不支持模块: {module}')

    def _import_procurement_long(self, row):
        """导入采购长表数据"""
        procurement_code = row.get('招采编号', '').strip()
        project_name = row.get('采购项目名称', '').strip()
        
        if not procurement_code:
            raise ValueError('招采编号不能为空')
        if not project_name:
            raise ValueError('采购项目名称不能为空')
        
        obj, created = Procurement.objects.update_or_create(
            procurement_code=procurement_code,
            defaults={
                'project_name': project_name,
                'procurement_unit': row.get('采购单位', '').strip(),
                'winning_unit': row.get('中标单位', '').strip(),
                'winning_contact': row.get('中标单位联系人及方式', '').strip(),
                'procurement_method': row.get('采购方式', '').strip(),
                'procurement_category': self._parse_enum(
                    row.get('采购类别', '').strip(), 
                    ['工程', '货物', '服务']
                ),
                'budget_amount': self._parse_decimal(row.get('采购预算金额(元)')),
                'control_price': self._parse_decimal(row.get('采购控制价(元)')),
                'winning_amount': self._parse_decimal(row.get('中标金额(元)')),
                'planned_end_date': self._parse_date(row.get('计划结束采购时间')),
                'notice_issue_date': self._parse_date(row.get('中标通知书发放日期')),
                'procurement_officer': row.get('采购经办人', '').strip(),
                'demand_department': row.get('需求部门', '').strip(),
            }
        )
        return created, not created

    def _import_contract_long(self, row):
        """导入合同长表数据"""
        contract_code = row.get('合同编号', '').strip()
        contract_name = row.get('合同名称', '').strip()
        
        if not contract_code:
            raise ValueError('合同编号不能为空')
        if not contract_name:
            raise ValueError('合同名称不能为空')
        
        # 获取关联采购
        procurement = None
        procurement_code = row.get('关联采购编号', '').strip()
        if procurement_code:
            try:
                procurement = Procurement.objects.get(procurement_code=procurement_code)
            except Procurement.DoesNotExist:
                raise ValueError(f'采购编号不存在: {procurement_code}')
        
        # 获取关联主合同
        parent_contract = None
        parent_code = row.get('关联主合同编号', '').strip()
        if parent_code:
            try:
                parent_contract = Contract.objects.get(contract_code=parent_code)
            except Contract.DoesNotExist:
                raise ValueError(f'主合同编号不存在: {parent_code}')
        
        contract_source = row.get('合同来源', '采购合同').strip()
        if contract_source not in ['采购合同', '直接签订']:
            contract_source = '采购合同'
        
        obj, created = Contract.objects.update_or_create(
            contract_code=contract_code,
            defaults={
                'contract_name': contract_name,
                'contract_type': row.get('合同类型', '主合同').strip(),
                'contract_source': contract_source,
                'procurement': procurement,
                'parent_contract': parent_contract,
                'party_a': row.get('甲方', '').strip(),
                'party_b': row.get('乙方', '').strip(),
                'contract_amount': self._parse_decimal(row.get('含税签约合同价(元)')),
                'signing_date': self._parse_date(row.get('合同签订日期')),
                'duration': row.get('合同工期/服务期限', '').strip(),
                'contract_officer': row.get('合同签订经办人', '').strip(),
                'payment_method': row.get('支付方式', '').strip(),
            }
        )
        return created, not created

    def _import_payment_long(self, row):
        """导入付款长表数据"""
        payment_code = row.get('付款编号', '').strip()
        contract_code = row.get('关联合同编号', '').strip()
        
        if not payment_code:
            raise ValueError('付款编号不能为空')
        if not contract_code:
            raise ValueError('关联合同编号不能为空')
        
        try:
            contract = Contract.objects.get(contract_code=contract_code)
        except Contract.DoesNotExist:
            raise ValueError(f'合同编号不存在: {contract_code}')
        
        payment_amount = self._parse_decimal(row.get('实付金额(元)'))
        if payment_amount is None:
            raise ValueError('实付金额不能为空')
        
        payment_date = self._parse_date(row.get('付款日期'))
        if payment_date is None:
            raise ValueError('付款日期不能为空')
        
        obj, created = Payment.objects.update_or_create(
            payment_code=payment_code,
            defaults={
                'contract': contract,
                'payment_amount': payment_amount,
                'payment_date': payment_date,
            }
        )
        return created, not created

    def _import_payment_wide(self, row, seq, group_id):
        """导入宽表转换的付款数据"""
        contract_code = row[0]  # 第一列是合同编号
        period = row['period']  # 日期列标签
        amount = self._parse_decimal(row['value'])
        
        if amount is None or amount <= 0:
            return
        
        try:
            contract = Contract.objects.get(contract_code=contract_code)
        except Contract.DoesNotExist:
            raise ValueError(f'合同编号不存在: {contract_code}')
        
        payment_date = self._parse_month_to_date(period)
        payment_code = f"{contract_code}-FK-{seq:03d}"
        
        obj, created = Payment.objects.update_or_create(
            payment_code=payment_code,
            defaults={
                'contract': contract,
                'payment_amount': amount,
                'payment_date': payment_date,
            }
        )
        return created

    def _import_evaluation_wide(self, row, seq, group_id):
        """导入宽表转换的评价数据"""
        contract_code = row[0]  # 第一列是合同编号
        period = row['period']  # 日期列标签
        score = self._parse_decimal(row['value'])
        
        if score is None:
            return
        
        try:
            contract = Contract.objects.get(contract_code=contract_code)
        except Contract.DoesNotExist:
            raise ValueError(f'合同编号不存在: {contract_code}')
        
        evaluation_code = f"{contract_code}-PJ-{seq:03d}"
        
        obj, created = SupplierEvaluation.objects.update_or_create(
            evaluation_code=evaluation_code,
            defaults={
                'contract': contract,
                'supplier_name': contract.party_b or '未知供应商',
                'evaluation_period': str(period),
                'score': score,
                'evaluation_type': '履约过程评价',
            }
        )
        return created

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
        
        value_str = str(value).strip().replace(',', '').replace('，', '')
        if not value_str or value_str == '/':
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
        if value_str == '/':
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
        self.stdout.write(self.style.SUCCESS(f'成功: {stats["success_rows"]}'))
        self.stdout.write(self.style.ERROR(f'失败: {stats["error_rows"]}'))
        
        if 'created' in stats:
            self.stdout.write(f'新增记录:       {stats.get("created", 0)}')
        if 'updated' in stats:
            self.stdout.write(f'更新记录:       {stats.get("updated", 0)}')
        
        if errors:
            self.stdout.write('\n' + self.style.WARNING('错误详情:'))
            for error in errors[:10]:  # 只显示前10条
                self.stdout.write(f'  - {error}')
            if len(errors) > 10:
                self.stdout.write(f'  ... 还有 {len(errors) - 10} 条错误')
        
        self.stdout.write('=' * 50)