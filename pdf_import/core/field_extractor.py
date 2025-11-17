"""
字段提取引擎 - 核心模块
基于配置驱动的智能字段提取 + 单元格检测增强
"""
import fitz  # PyMuPDF
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path

from .config_loader import ConfigLoader
from ..utils.text_parser import TextParser
from ..utils.date_parser import DateParser
from ..utils.amount_parser import AmountParser
from ..utils.enum_mapper import EnumMapper
from ..utils.cell_detector import CellDetector


class FieldExtractor:
    """字段提取引擎"""
    
    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        """
        初始化字段提取器
        
        Args:
            config_loader: 配置加载器实例
        """
        self.config_loader = config_loader or ConfigLoader()
        self.text_parser = TextParser()
        self.date_parser = DateParser()
        self.amount_parser = AmountParser()
        self.enum_mapper = EnumMapper()
        self.cell_detector = None  # 延迟初始化
        self._pdf_cache = {}  # 缓存已处理的PDF的单元格数据
    
    def extract(self, pdf_path: str, pdf_type: str) -> Dict[str, Any]:
        """
        从PDF提取字段
        
        Args:
            pdf_path: PDF文件路径
            pdf_type: PDF类型（procurement_request/procurement_notice等）
            
        Returns:
            提取的字段字典 {field_name: value, ...}
        """
        # 获取该PDF类型需要提取的字段配置
        fields_config = self.config_loader.get_fields_by_pdf_type(pdf_type)
        
        if not fields_config:
            print(f"警告: PDF类型 '{pdf_type}' 没有配置字段")
            return {}
        
        # 提取PDF全文文本
        full_text = self._extract_text_from_pdf(pdf_path)
        
        # 逐字段提取
        extracted_data = {}
        for field_name, field_config in fields_config.items():
            try:
                value = self._extract_field(
                    pdf_path=pdf_path,
                    full_text=full_text,
                    field_name=field_name,
                    field_config=field_config
                )
                extracted_data[field_name] = value
            except Exception as e:
                print(f"字段 '{field_name}' 提取失败: {e}")
                extracted_data[field_name] = None
        
        return extracted_data
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """提取PDF全文文本"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            print(f"PDF文本提取失败: {e}")
            return ""
    
    def _extract_field(self, pdf_path: str, full_text: str, 
                      field_name: str, field_config: Dict[str, Any]) -> Any:
        """
        提取单个字段
        
        Args:
            pdf_path: PDF文件路径
            full_text: PDF全文文本
            field_name: 字段名
            field_config: 字段配置
            
        Returns:
            提取的值
        """
        extraction_config = field_config.get('source', {}).get('extraction', {})
        method = extraction_config.get('method')
        
        if not method:
            return None
        
        # 初始化单元格检测器（如果需要）
        if method in ['cell_keyvalue', 'horizontal_keyvalue', 'vertical_keyvalue']:
            if pdf_path not in self._pdf_cache:
                self.cell_detector = CellDetector()
                self.cell_detector.extract_cells_from_pdf(pdf_path)
                self._pdf_cache[pdf_path] = True
        
        # 根据不同的提取方法调用相应的处理函数
        if method == 'cell_keyvalue':
            # 新方法：基于单元格检测的键值对提取
            return self._extract_cell_kv(pdf_path, extraction_config, field_config)
        
        elif method == 'horizontal_keyvalue':
            # 优先使用单元格检测，失败则回退到文本匹配
            value = self._extract_cell_kv(pdf_path, extraction_config, field_config, direction='right')
            if not value:
                value = self._extract_horizontal_kv(full_text, extraction_config, field_config)
            return value
        
        elif method == 'vertical_keyvalue':
            # 优先使用单元格检测，失败则回退到文本匹配
            value = self._extract_cell_kv(pdf_path, extraction_config, field_config, direction='below')
            if not value:
                value = self._extract_vertical_kv(full_text, extraction_config, field_config)
            return value
        
        elif method == 'amount':
            return self._extract_amount_field(full_text, extraction_config)
        
        elif method == 'date':
            return self._extract_date_field(full_text, extraction_config)
        
        elif method == 'regex':
            value = self._extract_by_regex(full_text, extraction_config)
            if value:
                value = self._post_process(value, field_config)
            return value
        
        elif method == 'multiline':
            return self._extract_multiline(full_text, extraction_config)
        
        elif method == 'table_first_row':
            return self._extract_table_first_row(pdf_path, extraction_config)
        
        elif method == 'table_cell':
            return self._extract_table_cell(pdf_path, extraction_config)
        
        elif method == 'fixed_value':
            return extraction_config.get('value')
        
        else:
            print(f"未知的提取方法: {method}")
            return None
    
    def _extract_cell_kv(self, pdf_path: str, extraction_config: Dict,
                        field_config: Dict, direction: str = 'auto') -> Optional[str]:
        """
        基于单元格检测的键值对提取（新方法）
        
        Args:
            pdf_path: PDF文件路径
            extraction_config: 提取配置
            field_config: 字段配置
            direction: 方向 'right'(右侧), 'below'(下方), 'auto'(自动)
            
        Returns:
            提取的值
        """
        if not self.cell_detector:
            return None
        
        key = extraction_config.get('key')
        if not key:
            return None
        
        # 使用单元格检测器提取键值对
        value = self.cell_detector.extract_keyvalue_pair(
            key_text=key,
            direction=direction,
            fuzzy=True
        )
        
        # 后处理
        if value:
            value = self._post_process(value, field_config)
        
        return value
    
    def _extract_horizontal_kv(self, text: str, extraction_config: Dict, 
                               field_config: Dict) -> Optional[str]:
        """提取横向键值对"""
        key = extraction_config.get('key')
        delimiter = extraction_config.get('delimiter', r"[：:]\s*")
        stop_pattern = extraction_config.get('stop_pattern', r"(?=\n|$)")
        
        value = self.text_parser.extract_horizontal_kv(
            text, key, delimiter, stop_pattern
        )
        
        # 如果配置了fallback_regex且横向提取失败，尝试正则
        if not value and extraction_config.get('fallback_regex'):
            value = self._extract_by_regex(text, {
                'pattern': extraction_config['fallback_regex']
            })
        
        # 后处理和枚举映射
        if value:
            value = self._post_process(value, field_config)
        
        return value
    
    def _extract_vertical_kv(self, text: str, extraction_config: Dict,
                            field_config: Dict) -> Optional[str]:
        """提取纵向键值对"""
        key = extraction_config.get('key')
        max_lines = extraction_config.get('max_lines', 3)
        value_pattern = extraction_config.get('value_pattern')
        
        value = self.text_parser.extract_vertical_kv(
            text, key, max_lines, value_pattern
        )
        
        if value:
            value = self._post_process(value, field_config)
        
        return value
    
    def _extract_amount_field(self, text: str, extraction_config: Dict) -> Optional[str]:
        """提取金额字段"""
        key = extraction_config.get('key')
        
        value = self.text_parser.extract_amount(text, key)
        
        if value:
            # 使用AmountParser解析
            parsed_amount = self.amount_parser.parse_amount(value)
            return str(parsed_amount) if parsed_amount else None
        
        return None
    
    def _extract_date_field(self, text: str, extraction_config: Dict) -> Optional[str]:
        """提取日期字段"""
        key = extraction_config.get('key')
        
        value = self.text_parser.extract_date(text, key)
        
        if value:
            # 使用DateParser解析
            parsed_date = self.date_parser.parse_date(value)
            return str(parsed_date) if parsed_date else value
        
        return None
    
    def _extract_by_regex(self, text: str, extraction_config: Dict) -> Optional[str]:
        """使用正则表达式提取（支持fallback）"""
        import re
        
        # 尝试主pattern
        pattern = extraction_config.get('pattern')
        if pattern:
            match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
            if match:
                # 如果有捕获组，返回第一个非None的捕获组
                if match.lastindex:
                    for i in range(1, match.lastindex + 1):
                        if match.group(i):
                            return match.group(i).strip()
                return match.group(0).strip()
        
        # 主pattern失败，尝试fallback_pattern
        fallback_pattern = extraction_config.get('fallback_pattern')
        if fallback_pattern:
            match = re.search(fallback_pattern, text, re.MULTILINE | re.DOTALL)
            if match:
                if match.lastindex:
                    for i in range(1, match.lastindex + 1):
                        if match.group(i):
                            return match.group(i).strip()
                return match.group(0).strip()
        
        # 如果有默认值，返回默认值
        default_value = extraction_config.get('default_value')
        if default_value:
            return default_value
        
        return None
    
    def _extract_multiline(self, text: str, extraction_config: Dict) -> Optional[str]:
        """提取多行文本"""
        key = extraction_config.get('key')
        end_marker = extraction_config.get('end_marker')
        max_lines = extraction_config.get('max_lines', 10)
        
        return self.text_parser.extract_multiline_value(
            text, key, end_marker, max_lines
        )
    
    def _extract_table_first_row(self, pdf_path: str, 
                                 extraction_config: Dict) -> Optional[str]:
        """从表格提取第一行数据"""
        table_marker = extraction_config.get('table_marker')
        column_name = extraction_config.get('column_name')
        
        if not table_marker or not column_name:
            return None
        
        return self.text_parser.extract_table_first_data_row(
            pdf_path, table_marker, column_name
        )
    
    def _extract_table_cell(self, pdf_path: str, 
                           extraction_config: Dict) -> Optional[str]:
        """从表格提取指定单元格"""
        table_markers = extraction_config.get('table_markers', [])
        if isinstance(table_markers, str):
            table_markers = [table_markers]
        
        row_identifier = {
            'column': extraction_config.get('key_column'),
            'value': extraction_config.get('key_value')
        }
        target_column = extraction_config.get('target_column')
        
        return self.text_parser.extract_from_table(
            pdf_path, table_markers, row_identifier, target_column
        )
    
    def _post_process(self, value: str, field_config: Dict) -> Any:
        """
        后处理提取的值
        
        1. 清理空白
        2. 自定义后处理（移除后缀等）
        3. 枚举映射（如果是choice类型）
        """
        if not value:
            return None
        
        # 清理空白
        value = self.text_parser.clean_whitespace(value)
        
        # 应用自定义后处理规则
        post_process_rules = field_config.get('post_process', [])
        for rule in post_process_rules:
            rule_type = rule.get('type')
            
            if rule_type == 'remove_suffix':
                # 移除指定后缀
                suffix = rule.get('suffix', '')
                if suffix and value.endswith(suffix):
                    value = value[:-len(suffix)]
                    print(f"  → 移除后缀'{suffix}': {value}")
            
            elif rule_type == 'remove_prefix':
                # 移除指定前缀
                prefix = rule.get('prefix', '')
                if prefix and value.startswith(prefix):
                    value = value[len(prefix):]
                    print(f"  → 移除前缀'{prefix}': {value}")
            
            elif rule_type == 'replace':
                # 替换文本
                old = rule.get('old', '')
                new = rule.get('new', '')
                if old:
                    value = value.replace(old, new)
                    print(f"  → 替换'{old}'为'{new}': {value}")
        
        # 如果是枚举类型，进行枚举映射
        if field_config.get('data_type') == 'choice':
            value = self._map_enum_value(value, field_config)
        
        return value
    
    def _map_enum_value(self, value: str, field_config: Dict) -> str:
        """
        枚举值映射
        
        1. 检查是否在标准枚举值中
        2. 检查是否在别名映射中
        3. 返回映射后的标准值
        """
        if not value:
            return value
        
        # 获取标准枚举值列表
        choices = field_config.get('choices', [])
        
        # 如果值已经在标准枚举中，直接返回
        if value in choices:
            return value
        
        # 尝试别名映射
        aliases = field_config.get('aliases', {})
        if value in aliases:
            mapped_value = aliases[value]
            print(f"枚举映射: '{value}' → '{mapped_value}'")
            return mapped_value
        
        # 如果都不匹配，返回原值（后续验证会标记为需要手动确认）
        print(f"警告: 枚举值 '{value}' 不在标准列表中，也无别名映射")
        return value
    
    def extract_all_from_pdfs(self, pdf_files: Dict[str, str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        从多个PDF文件提取所有字段（智能合并结果）
        
        改进点：
        1. 按优先级顺序处理PDF文件
        2. 字段级别的合并策略（避免覆盖）
        3. 过滤"采购需求书审批完成日期"字段
        4. 独立处理每个文件，避免数据混淆
        
        Args:
            pdf_files: {pdf_type: pdf_path, ...}
            例如: {
                'procurement_request': 'path/to/2-23.pdf',
                'procurement_notice': 'path/to/2-24.pdf',
                'control_price_approval': 'path/to/2-21.pdf',
                'procurement_result_oa': 'path/to/2-44.pdf',
                'candidate_publicity': 'path/to/2-45.pdf',
                'result_publicity': 'path/to/2-47.pdf',
            }
            
        Returns:
            (merged_data, requires_confirmation)
            - merged_data: 合并后的字段字典
            - requires_confirmation: 需要人工确认的字段列表
        """
        # 定义PDF类型的处理优先级（从高到低）
        # 优先级高的PDF类型的字段值会被优先采用
        PRIORITY_ORDER = [
            'procurement_request',      # 2-23 采购请示（最权威）
            'procurement_notice',        # 2-24 采购公告
            'procurement_result_oa',     # 2-44 采购结果OA
            'result_publicity',          # 2-47 结果公示
            'candidate_publicity',       # 2-45 候选人公示
            'control_price_approval',    # 2-21 控制价审批（fallback）
        ]
        
        # 过滤掉不需要提取的字段
        EXCLUDED_FIELDS = [
            'requirement_approval_date',  # 采购需求书审批完成日期（OA）
        ]
        
        # 存储每个文件的提取结果（独立存储，避免混淆）
        extraction_results = {}
        # 字段级别需确认列表
        requires_confirmation: List[Dict[str, Any]] = []
        
        # 按优先级顺序处理PDF文件
        for pdf_type in PRIORITY_ORDER:
            if pdf_type not in pdf_files:
                continue
            
            pdf_path = pdf_files[pdf_type]
            
            if not Path(pdf_path).exists():
                print(f"[警告] PDF文件不存在: {pdf_path}")
                continue
            
            print(f"\n[处理] {pdf_type}: {Path(pdf_path).name}")
            
            # 重要：清空缓存，确保每个文件独立处理
            self._pdf_cache.clear()
            if self.cell_detector:
                self.cell_detector = None
            
            # 提取字段
            try:
                extracted = self.extract(pdf_path, pdf_type)
                
                # 过滤掉不需要的字段
                filtered_extracted = {
                    field_name: value
                    for field_name, value in extracted.items()
                    if field_name not in EXCLUDED_FIELDS
                }
                
                # 存储提取结果
                extraction_results[pdf_type] = filtered_extracted
                
                # 打印提取到的字段
                for field_name, value in filtered_extracted.items():
                    if value is not None:
                        print(f"  [成功] {field_name}: {value}")
                
            except Exception as e:
                print(f"  [错误] 提取失败: {e}")
                extraction_results[pdf_type] = {}
        
        # 智能合并数据（字段级优先级策略）
        merged_data = {}
        field_sources = {}  # 记录每个字段的来源
        
        for pdf_type in PRIORITY_ORDER:
            if pdf_type not in extraction_results:
                continue
            
            extracted = extraction_results[pdf_type]
            
            for field_name, value in extracted.items():
                # 只有当字段还没有值，或当前值为None时才更新
                if value is not None and (field_name not in merged_data or merged_data.get(field_name) is None):
                    merged_data[field_name] = value
                    field_sources[field_name] = pdf_type
                    print(f"  -> {field_name} 采用自 {pdf_type}")
        
        # 特殊处理：control_price的fallback逻辑
        # 如果procurement_notice中没有提取到control_price，尝试从control_price_approval提取
        if 'control_price' not in merged_data or not merged_data.get('control_price'):
            if 'control_price_approval' in pdf_files:
                control_price_path = pdf_files['control_price_approval']
                if Path(control_price_path).exists() and 'control_price_approval' not in extraction_results:
                    print(f"\n[Fallback] 采购公告中未找到控制价，尝试从控制价审批(2-21)提取...")
                    
                    # 清空缓存，独立处理
                    self._pdf_cache.clear()
                    if self.cell_detector:
                        self.cell_detector = None
                    
                    try:
                        fallback_extracted = self.extract(control_price_path, 'control_price_approval')
                        if fallback_extracted.get('control_price'):
                            merged_data['control_price'] = fallback_extracted['control_price']
                            field_sources['control_price'] = 'control_price_approval (fallback)'
                            print(f"  [成功] control_price (from 2-21): {merged_data['control_price']}")
                    except Exception as e:
                        print(f"  [错误] Fallback提取失败: {e}")
        
        # 打印最终合并摘要
        print(f"\n[合并摘要]")
        print(f"  * 处理文件数: {len(extraction_results)}")
        print(f"  * 提取字段数: {len(merged_data)}")
        print(f"  * 有效字段数: {len([v for v in merged_data.values() if v])}")
        
        return merged_data, requires_confirmation
