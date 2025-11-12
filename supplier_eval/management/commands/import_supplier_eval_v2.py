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
        parser.add_argument(
            '--json-output',
            action='store_true',
            help='以JSON格式输出统计汇总（提供给API使用）'
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
                created_count = 0
                updated_count = 0
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
                        if result == 'created':
                            created_count += 1
                        elif result == 'updated':
                            updated_count += 1
                        elif result == 'skip':
                            skip_count += 1
                    except Exception as e:
                        error_count += 1
                        error_msg = f"行 {row_num}: {str(e)}"
                        errors.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))

                # 汇总
                stats = {
                    'total_rows': total_rows,
                    'success_rows': created_count + updated_count,
                    'error_rows': error_count,
                    'created': created_count,
                    'updated': updated_count,
                    'skipped': skip_count,
                }

                if options.get('json-output') or options.get('json_output'):
                    import json as _json
                    summary = {
                        'module': 'supplier_eval',
                        'stats': stats,
                        'errors': errors[:200],
                        'has_more_errors': len(errors) > 200,
                    }
                    self.stdout.write(_json.dumps(summary, ensure_ascii=False))
                    return

                # 输出统计结果（文本）
                self.stdout.write('-' * 80)
                self.stdout.write(self.style.SUCCESS('导入完成!'))
                self.stdout.write(f'总行数: {total_rows}')
                self.stdout.write(self.style.SUCCESS(f'成功: {created_count + updated_count}'))
                if created_count:
                    self.stdout.write(self.style.SUCCESS(f'  - 新增: {created_count}'))
                if updated_count:
                    self.stdout.write(self.style.SUCCESS(f'  - 更新: {updated_count}'))
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
        分析CSV表头，仅识别系统约定的标准列名，动态列按正则匹配。

        Returns:
            dict: {
                'basic_fields': {...},
                'annual_fields': {year: column_name, ...},
                'irregular_fields': {index: column_name, ...}
            }
        """
        import collections
        header_info = {
            'basic_fields': {},
            'annual_fields': {},
            'irregular_fields': {}
        }

        # 仅接受系统原有命名（不支持同义项）
        canonical_basic_names = {
            '序号': 'sequence',
            '合同序号': 'contract_sequence',
            '履约综合评价得分': 'comprehensive_score',
            '末次评价得分': 'last_evaluation_score',
            '备注': 'remarks',
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

        # 检查重复列名（唯一性）
        counter = collections.Counter([ (str(fn).strip() if fn is not None else '') for fn in fieldnames ])
        duplicated = [name for name, c in counter.items() if name and c > 1]
        if duplicated:
            dup_text = ', '.join(duplicated[:5]) + (f' 等{len(duplicated)}列' if len(duplicated) > 5 else '')
            raise CommandError(f'模板列名存在重复，请确保唯一性: {dup_text}')

        for field in fieldnames:
            field = field.strip() if field else ''
            if not field:
                continue

            # 仅识别标准基础字段
            if field in canonical_basic_names:
                key = canonical_basic_names[field]
                # 冲突保护（理论上不会触发，因为上面已做唯一性校验）
                if key in header_info['basic_fields']:
                    raise CommandError(f'模板列名冲突（基础字段重复）: {field}')
                header_info['basic_fields'][key] = field
                continue

            # 识别年度动态字段
            annual_match = annual_pattern.match(field)
            if annual_match:
                year = int(annual_match.group(1))
                if 2000 <= year <= 2100:
                    header_info['annual_fields'][year] = field
                continue

            # 识别不定期动态字段
            irregular_match = irregular_pattern.match(field)
            if irregular_match:
                index_str = irregular_match.group(1)
                if index_str in chinese_num_map:
                    index = chinese_num_map[index_str]
                else:
                    try:
                        index = int(index_str)
                    except ValueError:
                        continue
                if 1 <= index <= 100:
                    header_info['irregular_fields'][index] = field

        # 校验必填基础列是否存在
        required_keys = ['sequence', 'contract_sequence']
        missing = [cn for cn, key in canonical_basic_names.items() if key in required_keys and key not in header_info['basic_fields']]
        if missing:
            raise CommandError('缺少必填列: ' + ', '.join(missing))

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
        """处理单行数据
        返回: 'created' | 'updated' | 'skip'
        在 dry_run 下也返回预期操作类型，便于统计。
        """
        from decimal import Decimal, ROUND_HALF_UP
        # 提取基础字段
        basic_fields = header_info['basic_fields']

        # 行内容预判：识别并跳过“模板说明/空行”
        sequence_key = basic_fields.get('sequence', '')
        contract_seq_key = basic_fields.get('contract_sequence', '')
        remarks_key = basic_fields.get('remarks', '')

        # 当前行非空列集合
        non_empty_keys = {k for k, v in row.items() if (str(v).strip() if v is not None else '')}

        # 识别“数据字段”列集合（已知基础列 + 动态年度/不定期列）
        data_fieldnames = set(basic_fields.values()) if basic_fields else set()
        data_fieldnames |= set(header_info.get('annual_fields', {}).values())
        data_fieldnames |= set(header_info.get('irregular_fields', {}).values())
        data_fieldnames_incl_remarks = set(data_fieldnames)
        if remarks_key:
            data_fieldnames_incl_remarks.add(remarks_key)

        # A：整行空
        if not non_empty_keys:
            self.stdout.write(self.style.WARNING(f'行 {row_num}: 空行，跳过'))
            return 'skip'

        # B：仅模板说明/未知列非空
        if non_empty_keys.issubset(set(row.keys()) - data_fieldnames_incl_remarks):
            self.stdout.write(self.style.WARNING(f'行 {row_num}: 仅模板说明/未知列非空，跳过'))
            return 'skip'

        # C：序号与合同序号皆空且评分列均空 → 跳过
        numeric_like_fields = set()
        if basic_fields.get('comprehensive_score'):
            numeric_like_fields.add(basic_fields['comprehensive_score'])
        if basic_fields.get('last_evaluation_score'):
            numeric_like_fields.add(basic_fields['last_evaluation_score'])
        numeric_like_fields |= set(header_info.get('annual_fields', {}).values())
        numeric_like_fields |= set(header_info.get('irregular_fields', {}).values())
        seq_val = (row.get(sequence_key, '') or '').strip()
        contract_seq_val = (row.get(contract_seq_key, '') or '').strip()
        if not seq_val and not contract_seq_val:
            if all(not (str(row.get(col, '') or '').strip()) for col in numeric_like_fields):
                self.stdout.write(self.style.WARNING(f'行 {row_num}: 模板/说明行或无有效数据，跳过'))
                return 'skip'

        # 正常解析必填字段
        sequence = seq_val
        contract_sequence = contract_seq_val

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

        # 解析基础评分字段（CSV 中若未提供综合评分，将在下方自动计算）
        csv_comprehensive_score = self.parse_decimal(
            row.get(basic_fields.get('comprehensive_score', ''), ''),
            '履约综合评价得分',
            row_num
        )
        last_evaluation_score = self.parse_decimal(
            row.get(basic_fields.get('last_evaluation_score', ''), ''),
            '末次评价得分',
            row_num
        )
        remarks = (row.get(remarks_key, '') or '').strip()

        # 解析年度与不定期得分
        annual_scores = {}
        for year, column_name in header_info['annual_fields'].items():
            score = self.parse_decimal(row.get(column_name, ''), f'{year}年度评价得分', row_num)
            if score is not None:
                annual_scores[str(year)] = float(score)
        irregular_scores = {}
        for index, column_name in header_info['irregular_fields'].items():
            score = self.parse_decimal(row.get(column_name, ''), f'第{index}次不定期评价得分', row_num)
            if score is not None:
                irregular_scores[str(index)] = float(score)

        # 自动计算综合评分
        process_values = []
        for v in annual_scores.values():
            if v is not None:
                process_values.append(Decimal(str(v)))
        for v in irregular_scores.values():
            if v is not None:
                process_values.append(Decimal(str(v)))
        process_avg = None
        if process_values:
            process_avg = (sum(process_values) / Decimal(len(process_values))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        computed_comprehensive = None
        if last_evaluation_score is not None and process_avg is not None:
            computed_comprehensive = (last_evaluation_score * Decimal('0.60') + process_avg * Decimal('0.40')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif last_evaluation_score is not None:
            computed_comprehensive = last_evaluation_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif process_avg is not None:
            computed_comprehensive = process_avg

        comprehensive_score = csv_comprehensive_score if csv_comprehensive_score is not None else computed_comprehensive

        # dry-run 仍返回预期操作类型
        op_type = 'updated' if existing else 'created'
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'行 {row_num}: [模拟] {"更新" if existing else "创建"} {evaluation_code}'))
            return op_type

        # 创建或更新
        with transaction.atomic():
            if existing:
                evaluation = existing
                evaluation.contract = contract
                evaluation.supplier_name = contract.party_b
                evaluation.comprehensive_score = comprehensive_score
                evaluation.last_evaluation_score = last_evaluation_score
                evaluation.annual_scores = annual_scores
                evaluation.irregular_scores = irregular_scores
                evaluation.remarks = remarks
                evaluation.save()
                self.stdout.write(self.style.SUCCESS(f'行 {row_num}: 更新成功 {evaluation_code}'))
                return 'updated'
            else:
                SupplierEvaluation.objects.create(
                    evaluation_code=evaluation_code,
                    contract=contract,
                    supplier_name=contract.party_b,
                    comprehensive_score=comprehensive_score,
                    last_evaluation_score=last_evaluation_score,
                    annual_scores=annual_scores,
                    irregular_scores=irregular_scores,
                    remarks=remarks
                )
                self.stdout.write(self.style.SUCCESS(f'行 {row_num}: 创建成功 {evaluation_code}'))
                return 'created'

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
