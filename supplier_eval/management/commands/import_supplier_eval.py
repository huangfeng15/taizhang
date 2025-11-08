"""
供应商履约评价CSV导入命令

使用方法:
    python manage.py import_supplier_eval <csv_file_path>

CSV格式(13列):
    序号, 合同序号, 履约综合评价得分, 末次评价得分,
    2019年度评价得分, 2020年度评价得分, 2021年度评价得分,
    2022年度评价得分, 2023年度评价得分, 2024年度评价得分, 2025年度评价得分,
    第一次不定期评价得分, 第二次不定期评价得分, 备注
"""
import csv
import sys
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from contract.models import Contract
from supplier_eval.models import SupplierEvaluation


class Command(BaseCommand):
    help = '从CSV文件批量导入供应商履约评价数据'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='CSV文件路径'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8-sig',
            help='CSV文件编码 (默认: utf-8-sig, 支持带BOM的UTF-8)'
        )
        parser.add_argument(
            '--skip-header',
            action='store_true',
            help='跳过第一行表头'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模拟运行,不实际写入数据库'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='如果评价编号已存在则更新,否则跳过'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        encoding = options['encoding']
        skip_header = options['skip_header']
        dry_run = options['dry_run']
        update_mode = options['update']

        self.stdout.write(self.style.SUCCESS(f'开始导入CSV文件: {csv_file}'))
        self.stdout.write(f'编码: {encoding}')
        self.stdout.write(f'模式: {"模拟运行" if dry_run else "实际导入"}')
        self.stdout.write(f'更新策略: {"更新已存在记录" if update_mode else "跳过已存在记录"}')
        self.stdout.write('-' * 80)

        try:
            with open(csv_file, 'r', encoding=encoding, newline='') as f:
                reader = csv.reader(f)
                
                # 跳过表头
                if skip_header:
                    next(reader)
                else:
                    # 读取表头验证
                    header = next(reader)
                    self.validate_header(header)
                
                # 统计信息
                total_rows = 0
                success_count = 0
                skip_count = 0
                error_count = 0
                errors = []

                # 逐行处理
                for row_num, row in enumerate(reader, start=2):
                    total_rows += 1
                    
                    try:
                        result = self.process_row(row, row_num, update_mode, dry_run)
                        if result == 'success':
                            success_count += 1
                        elif result == 'skip':
                            skip_count += 1
                    except Exception as e:
                        error_count += 1
                        error_msg = f"行 {row_num}: {str(e)}"
                        errors.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))

                # 输出统计结果
                self.stdout.write('-' * 80)
                self.stdout.write(self.style.SUCCESS(f'导入完成!'))
                self.stdout.write(f'总行数: {total_rows}')
                self.stdout.write(self.style.SUCCESS(f'成功: {success_count}'))
                if skip_count > 0:
                    self.stdout.write(self.style.WARNING(f'跳过: {skip_count}'))
                if error_count > 0:
                    self.stdout.write(self.style.ERROR(f'失败: {error_count}'))
                
                if errors:
                    self.stdout.write('\n错误详情:')
                    for error in errors[:10]:  # 只显示前10条错误
                        self.stdout.write(self.style.ERROR(f'  - {error}'))
                    if len(errors) > 10:
                        self.stdout.write(f'  ... 还有 {len(errors) - 10} 条错误')

        except FileNotFoundError:
            raise CommandError(f'文件不存在: {csv_file}')
        except UnicodeDecodeError:
            raise CommandError(f'编码错误,请尝试使用 --encoding 参数指定正确的编码')

    def validate_header(self, header):
        """验证CSV表头是否符合预期"""
        expected_columns = [
            '序号', '合同序号', '履约综合评价得分', '末次评价得分',
            '2019年度评价得分', '2020年度评价得分', '2021年度评价得分',
            '2022年度评价得分', '2023年度评价得分', '2024年度评价得分', '2025年度评价得分',
            '第一次不定期评价得分', '第二次不定期评价得分', '备注'
        ]
        
        if len(header) != len(expected_columns):
            self.stdout.write(
                self.style.WARNING(
                    f'警告: CSV列数({len(header)})与预期({len(expected_columns)})不符'
                )
            )
        
        self.stdout.write(f'CSV列数: {len(header)}')
        self.stdout.write(f'表头: {", ".join(header)}')

    def process_row(self, row, row_num, update_mode, dry_run):
        """
        处理单行数据
        
        CSV格式(13列):
        0: 序号
        1: 合同序号
        2: 履约综合评价得分
        3: 末次评价得分
        4-10: 2019-2025年度评价得分
        11-12: 第一次、第二次不定期评价得分
        13: 备注
        """
        if len(row) < 13:
            raise ValueError(f'列数不足,期望至少13列,实际{len(row)}列')

        # 提取字段
        sequence = row[0].strip()
        contract_code = row[1].strip()
        
        # 验证必填字段
        if not sequence:
            raise ValueError('序号不能为空')
        if not contract_code:
            raise ValueError('合同序号不能为空')

        # 查找关联合同
        try:
            contract = Contract.objects.get(contract_code=contract_code)
        except Contract.DoesNotExist:
            raise ValueError(f'合同不存在: {contract_code}')

        # 生成评价编号(使用序号作为评价编号)
        evaluation_code = f'EVAL-{contract_code}-{sequence}'

        # 检查是否已存在
        existing = SupplierEvaluation.objects.filter(
            evaluation_code=evaluation_code
        ).first()

        if existing and not update_mode:
            self.stdout.write(
                self.style.WARNING(f'行 {row_num}: 评价编号已存在,跳过: {evaluation_code}')
            )
            return 'skip'

        # 解析评分字段
        comprehensive_score = self.parse_decimal(row[2], '履约综合评价得分', row_num)
        last_evaluation_score = self.parse_decimal(row[3], '末次评价得分', row_num)
        score_2019 = self.parse_decimal(row[4], '2019年度评价得分', row_num)
        score_2020 = self.parse_decimal(row[5], '2020年度评价得分', row_num)
        score_2021 = self.parse_decimal(row[6], '2021年度评价得分', row_num)
        score_2022 = self.parse_decimal(row[7], '2022年度评价得分', row_num)
        score_2023 = self.parse_decimal(row[8], '2023年度评价得分', row_num)
        score_2024 = self.parse_decimal(row[9], '2024年度评价得分', row_num)
        score_2025 = self.parse_decimal(row[10], '2025年度评价得分', row_num)
        irregular_eval_1 = self.parse_decimal(row[11], '第一次不定期评价得分', row_num)
        irregular_eval_2 = self.parse_decimal(row[12], '第二次不定期评价得分', row_num)
        remarks = row[13].strip() if len(row) > 13 else ''

        # 验证评分范围
        score_fields = {
            '履约综合评价得分': comprehensive_score,
            '末次评价得分': last_evaluation_score,
            '2019年度评价得分': score_2019,
            '2020年度评价得分': score_2020,
            '2021年度评价得分': score_2021,
            '2022年度评价得分': score_2022,
            '2023年度评价得分': score_2023,
            '2024年度评价得分': score_2024,
            '2025年度评价得分': score_2025,
            '第一次不定期评价得分': irregular_eval_1,
            '第二次不定期评价得分': irregular_eval_2,
        }

        for field_name, score_value in score_fields.items():
            if score_value is not None:
                if score_value < 0 or score_value > 100:
                    raise ValueError(f'{field_name}超出范围(0-100): {score_value}')

        # 如果是模拟运行,不实际写入
        if dry_run:
            action = '更新' if existing else '创建'
            self.stdout.write(
                self.style.SUCCESS(
                    f'行 {row_num}: [模拟] {action} {evaluation_code} - {contract.party_b}'
                )
            )
            return 'success'

        # 创建或更新记录
        with transaction.atomic():
            if existing:
                # 更新现有记录
                existing.contract = contract
                existing.supplier_name = contract.party_b
                existing.comprehensive_score = comprehensive_score
                existing.last_evaluation_score = last_evaluation_score
                existing.score_2019 = score_2019
                existing.score_2020 = score_2020
                existing.score_2021 = score_2021
                existing.score_2022 = score_2022
                existing.score_2023 = score_2023
                existing.score_2024 = score_2024
                existing.score_2025 = score_2025
                existing.irregular_evaluation_1 = irregular_eval_1
                existing.irregular_evaluation_2 = irregular_eval_2
                existing.remarks = remarks
                existing.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'行 {row_num}: 更新 {evaluation_code} - {contract.party_b}'
                    )
                )
            else:
                # 创建新记录
                evaluation = SupplierEvaluation(
                    evaluation_code=evaluation_code,
                    contract=contract,
                    supplier_name=contract.party_b,
                    comprehensive_score=comprehensive_score,
                    last_evaluation_score=last_evaluation_score,
                    score_2019=score_2019,
                    score_2020=score_2020,
                    score_2021=score_2021,
                    score_2022=score_2022,
                    score_2023=score_2023,
                    score_2024=score_2024,
                    score_2025=score_2025,
                    irregular_evaluation_1=irregular_eval_1,
                    irregular_evaluation_2=irregular_eval_2,
                    remarks=remarks
                )
                evaluation.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'行 {row_num}: 创建 {evaluation_code} - {contract.party_b}'
                    )
                )

        return 'success'

    def parse_decimal(self, value, field_name, row_num):
        """解析Decimal字段"""
        if not value or not value.strip():
            return None
        
        try:
            return Decimal(value.strip())
        except (InvalidOperation, ValueError):
            raise ValueError(f'{field_name}格式错误: {value}')