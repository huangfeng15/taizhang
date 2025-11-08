"""
供应商履约评价CSV导入命令 v2.0（动态年度支持）

使用方法:
    python manage.py import_supplier_eval_v2 <csv_file_path>

CSV格式（灵活列数）:
    基础列（必需）:
      - 序号
      - 合同序号
      - 履约综合评价得分
      - 末次评价得分
      - 备注

    年度评价列（可选，支持任意年份）:
      - 2019年度评价得分, 2020年度评价得分, ..., 2026年度评价得分, ...
      - 列名格式: "{年份}年度评价得分"

    不定期评价列（可选，支持任意次数）:
      - 第1次不定期评价得分, 第2次不定期评价得分, ...
      - 列名格式: "第{次数}次不定期评价得分"
"""
import csv
import re
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from contract.models import Contract
from supplier_eval.models import SupplierEvaluation


class Command(BaseCommand):
    help = '从CSV文件批量导入供应商履约评价数据（支持动态年度）'

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
            help='CSV文件编码（默认: utf-8-sig，支持带BOM的UTF-8）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模拟运行，不实际写入数据库'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='如果评价编号已存在则更新，否则跳过'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        encoding = options['encoding']
        dry_run = options['dry_run']
        update_mode = options['update']

        self.stdout.write(self.style.SUCCESS(f'开始导入CSV文件: {csv_file}'))
        self.stdout.write(f'编码: {encoding}')
        self.stdout.write(f'模式: {"模拟运行" if dry_run else "实际导入"}')
        self.stdout.write(f'更新策略: {"更新已存在记录" if update_mode else "跳过已存在记录"}')
        self.stdout.write('-' * 80)

        try:
            with open(csv_file, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f)

                # 分析表头
                header_info = self.analyze_header(reader.fieldnames)
                self.print_header_info(header_info)

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
                        result = self.process_row(
                            row, row_num, header_info, update_mode, dry_run
                        )
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
            raise CommandError(f'编码错误，请尝试使用 --encoding 参数指定正确的编码')

    def analyze_header(self, fieldnames):
        """
        分析CSV表头，识别动态年度字段

        Returns:
            dict: {
                'basic_fields': {...},
                'annual_fields': {year: column_name, ...},
                'irregular_fields': {index: column_name, ...}
            }
        """
        header_info = {
            'basic_fields': {},
            'annual_fields': {},
            'irregular_fields': {}
        }

        # 基础字段映射
        basic_field_map = {
            '序号': 'sequence',
            '合同序号': 'contract_sequence',
            '履约综合评价得分': 'comprehensive_score',
            '末次评价得分': 'last_evaluation_score',
            '备注': 'remarks'
        }

        # 年度字段正则: "2019年度评价得分"
        annual_pattern = re.compile(r'^(\d{4})年度评价得分$')

        # 不定期字段正则: "第1次不定期评价得分" 或 "第一次不定期评价得分"
        irregular_pattern = re.compile(r'^第(\d+|[一二三四五六七八九十]+)次不定期评价得分$')

        # 中文数字转阿拉伯数字
        chinese_num_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }

        for field in fieldnames:
            field = field.strip()

            # 检查基础字段
            if field in basic_field_map:
                header_info['basic_fields'][basic_field_map[field]] = field
                continue

            # 检查年度字段
            annual_match = annual_pattern.match(field)
            if annual_match:
                year = int(annual_match.group(1))
                if 2000 <= year <= 2100:
                    header_info['annual_fields'][year] = field
                continue

            # 检查不定期字段
            irregular_match = irregular_pattern.match(field)
            if irregular_match:
                index_str = irregular_match.group(1)
                # 转换中文数字
                if index_str in chinese_num_map:
                    index = chinese_num_map[index_str]
                else:
                    try:
                        index = int(index_str)
                    except ValueError:
                        continue

                if 1 <= index <= 100:
                    header_info['irregular_fields'][index] = field

        return header_info

    def print_header_info(self, header_info):
        """打印表头分析结果"""
        self.stdout.write('\n表头分析结果:')
        self.stdout.write(f'  基础字段: {len(header_info["basic_fields"])} 个')
        for field_key, column_name in header_info['basic_fields'].items():
            self.stdout.write(f'    - {column_name} ({field_key})')

        if header_info['annual_fields']:
            years = sorted(header_info['annual_fields'].keys())
            self.stdout.write(f'  年度评价字段: {len(years)} 个')
            self.stdout.write(f'    年份范围: {min(years)}-{max(years)}')
            for year in years:
                self.stdout.write(f'    - {header_info["annual_fields"][year]}')

        if header_info['irregular_fields']:
            indices = sorted(header_info['irregular_fields'].keys())
            self.stdout.write(f'  不定期评价字段: {len(indices)} 个')
            for index in indices:
                self.stdout.write(f'    - {header_info["irregular_fields"][index]}')

        self.stdout.write('')

    def process_row(self, row, row_num, header_info, update_mode, dry_run):
        """处理单行数据"""
        # 提取基础字段
        basic_fields = header_info['basic_fields']

        sequence = row.get(basic_fields.get('sequence', ''), '').strip()
        contract_sequence = row.get(basic_fields.get('contract_sequence', ''), '').strip()

        # 验证必填字段
        if not sequence:
            raise ValueError('序号不能为空')
        if not contract_sequence:
            raise ValueError('合同序号不能为空')

        # 查找关联合同
        try:
            contract = Contract.objects.get(contract_sequence=contract_sequence)
        except Contract.DoesNotExist:
            raise ValueError(f'合同不存在: {contract_sequence}')

        # 生成评价编号
        evaluation_code = f'EVAL-{contract.contract_code}-{sequence}'

        # 检查是否已存在
        existing = SupplierEvaluation.objects.filter(
            evaluation_code=evaluation_code
        ).first()

        if existing and not update_mode:
            self.stdout.write(
                self.style.WARNING(f'行 {row_num}: 评价编号已存在，跳过: {evaluation_code}')
            )
            return 'skip'

        # 解析基础评分字段
        comprehensive_score = self.parse_decimal(
            row.get(basic_fields.get('comprehensive_score', ''), ''),
            '履约综合评价得分',
            row_num
        )
        last_evaluation_score = self.parse_decimal(
            row.get(basic_fields.get('last_evaluation_score', ''), ''),
            '末次评价得分',
            row_num
        )
        remarks = row.get(basic_fields.get('remarks', ''), '').strip()

        # 解析年度评价得分（动态）
        annual_scores = {}
        for year, column_name in header_info['annual_fields'].items():
            score = self.parse_decimal(
                row.get(column_name, ''),
                f'{year}年度评价得分',
                row_num
            )
            if score is not None:
                annual_scores[str(year)] = float(score)

        # 解析不定期评价得分（动态）
        irregular_scores = {}
        for index, column_name in header_info['irregular_fields'].items():
            score = self.parse_decimal(
                row.get(column_name, ''),
                f'第{index}次不定期评价得分',
                row_num
            )
            if score is not None:
                irregular_scores[str(index)] = float(score)

        # 模拟运行模式
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'行 {row_num}: [模拟] {"更新" if existing else "创建"} {evaluation_code}'
                )
            )
            return 'success'

        # 创建或更新记录
        with transaction.atomic():
            if existing:
                # 更新模式
                evaluation = existing
                evaluation.contract = contract
                evaluation.supplier_name = contract.party_b
                evaluation.comprehensive_score = comprehensive_score
                evaluation.last_evaluation_score = last_evaluation_score
                evaluation.annual_scores = annual_scores
                evaluation.irregular_scores = irregular_scores
                evaluation.remarks = remarks
                evaluation.save()

                self.stdout.write(
                    self.style.SUCCESS(f'行 {row_num}: 更新成功 {evaluation_code}')
                )
            else:
                # 创建模式
                evaluation = SupplierEvaluation.objects.create(
                    evaluation_code=evaluation_code,
                    contract=contract,
                    supplier_name=contract.party_b,
                    comprehensive_score=comprehensive_score,
                    last_evaluation_score=last_evaluation_score,
                    annual_scores=annual_scores,
                    irregular_scores=irregular_scores,
                    remarks=remarks
                )

                self.stdout.write(
                    self.style.SUCCESS(f'行 {row_num}: 创建成功 {evaluation_code}')
                )

        return 'success'

    def parse_decimal(self, value, field_name, row_num):
        """解析Decimal类型字段"""
        value = value.strip() if value else ''

        if not value:
            return None

        try:
            decimal_value = Decimal(value)

            # 验证评分范围
            if decimal_value < 0 or decimal_value > 100:
                raise ValueError(f'{field_name}必须在0-100之间，实际值: {decimal_value}')

            return decimal_value
        except (InvalidOperation, ValueError) as e:
            raise ValueError(f'{field_name}格式错误: {value} ({str(e)})')
