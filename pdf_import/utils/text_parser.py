"""
文本解析工具 - 基于键值对的智能提取
核心功能：横向/纵向键值对识别，表格单元格定位
"""
import re
from typing import Optional, List, Dict, Any, Tuple
import fitz  # PyMuPDF


class TextParser:
    """文本解析器 - 键值对提取核心"""
    
    @staticmethod
    def extract_horizontal_kv(text: str, key: str, 
                             delimiter: str = r"[：:]\s*",
                             stop_pattern: str = r"(?=\n|$)") -> Optional[str]:
        """
        提取横向键值对（key: value 格式）
        
        Args:
            text: 源文本
            key: 键名（支持模糊匹配）
            delimiter: 分隔符模式（默认：冒号+可选空格）
            stop_pattern: 停止模式（默认：换行或文本结束）
            
        Returns:
            提取的值，未找到返回None
            
        示例：
            text = "项目名称：深圳市某某项目\\n项目编号：123"
            extract_horizontal_kv(text, "项目名称") → "深圳市某某项目"
        """
        if not text or not key:
            return None
        
        # 构建提取模式：key + delimiter + 捕获组(value) + stop
        pattern = rf"{re.escape(key)}{delimiter}(.+?){stop_pattern}"
        
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            # 清理可能的多余空白和换行
            value = re.sub(r'\s+', ' ', value)
            return value if value else None
        
        return None
    
    @staticmethod
    def extract_vertical_kv(text: str, key: str, 
                           max_lines: int = 3,
                           value_pattern: Optional[str] = None) -> Optional[str]:
        """
        提取纵向键值对（键在上，值在下）
        
        Args:
            text: 源文本
            key: 键名
            max_lines: 向下搜索的最大行数
            value_pattern: 值的正则模式（可选，用于进一步筛选）
            
        Returns:
            提取的值，未找到返回None
            
        示例：
            text = "采购控制价(元)\\n￥1,234,567.00\\n其他信息"
            extract_vertical_kv(text, "采购控制价", value_pattern=r"￥?([\d,\.]+)")
            → "1,234,567.00"
        """
        if not text or not key:
            return None
        
        # 分割文本为行
        lines = text.split('\n')
        
        # 找到包含key的行索引
        key_line_idx = None
        for i, line in enumerate(lines):
            if key in line:
                key_line_idx = i
                break
        
        if key_line_idx is None:
            return None
        
        # 在后续行中查找值
        for offset in range(1, max_lines + 1):
            if key_line_idx + offset >= len(lines):
                break
            
            value_line = lines[key_line_idx + offset].strip()
            
            # 跳过空行
            if not value_line:
                continue
            
            # 如果提供了值模式，使用模式提取
            if value_pattern:
                match = re.search(value_pattern, value_line)
                if match:
                    return match.group(1) if match.lastindex else match.group(0)
            else:
                # 否则返回整行（清理后）
                return value_line
        
        return None
    
    @staticmethod
    def extract_multiline_value(text: str, key: str, 
                               end_marker: Optional[str] = None,
                               max_lines: int = 10) -> Optional[str]:
        """
        提取多行值（用于提取大段文本，如评标委员会成员）
        
        Args:
            text: 源文本
            key: 起始键名
            end_marker: 结束标记（可选）
            max_lines: 最大行数限制
            
        Returns:
            提取的多行值
            
        示例：
            text = "评标委员会成员：\\n张三、李四\\n王五、赵六\\n其他信息"
            extract_multiline_value(text, "评标委员会成员", "其他信息")
            → "张三、李四 王五、赵六"
        """
        if not text or not key:
            return None
        
        # 找到起始位置
        start_match = re.search(rf"{re.escape(key)}[：:]\s*", text)
        if not start_match:
            return None
        
        start_pos = start_match.end()
        
        # 确定结束位置
        if end_marker:
            end_match = re.search(rf"{re.escape(end_marker)}", text[start_pos:])
            if end_match:
                end_pos = start_pos + end_match.start()
            else:
                # 如果没找到结束标记，取max_lines行
                lines = text[start_pos:].split('\n')[:max_lines]
                return ' '.join(line.strip() for line in lines if line.strip())
        else:
            # 没有结束标记，取max_lines行
            lines = text[start_pos:].split('\n')[:max_lines]
            return ' '.join(line.strip() for line in lines if line.strip())
        
        # 提取内容
        content = text[start_pos:end_pos].strip()
        # 合并多行，用空格分隔
        content = re.sub(r'\s+', ' ', content)
        return content if content else None
    
    @staticmethod
    def extract_amount(text: str, key: str, 
                      currency_symbols: str = r"￥¥元") -> Optional[str]:
        """
        提取金额（专用方法，自动处理货币符号和千分位）
        
        Args:
            text: 源文本
            key: 键名
            currency_symbols: 货币符号字符集
            
        Returns:
            纯数字金额字符串（移除货币符号和逗号）
            
        示例：
            extract_amount(text, "采购控制价") → "1234567.00"
        """
        # 先尝试横向键值对
        value = TextParser.extract_horizontal_kv(text, key)
        
        # 如果横向没找到，尝试纵向
        if not value:
            value = TextParser.extract_vertical_kv(
                text, key, 
                value_pattern=rf"[{currency_symbols}]?([\d,\.]+)"
            )
        
        if not value:
            return None
        
        # 清理金额：移除货币符号和逗号
        cleaned = re.sub(rf"[{currency_symbols},\s]", "", value)
        
        # 验证是否为有效数字
        try:
            float(cleaned)
            return cleaned
        except ValueError:
            return None
    
    @staticmethod
    def extract_date(text: str, key: str) -> Optional[str]:
        """
        提取日期（专用方法，支持多种日期格式）
        
        Args:
            text: 源文本
            key: 键名
            
        Returns:
            标准格式日期字符串 YYYY-MM-DD
            
        示例：
            extract_date(text, "开标时间") → "2025-01-15"
        """
        # 先尝试横向
        value = TextParser.extract_horizontal_kv(text, key)
        
        # 如果横向没找到，尝试纵向
        if not value:
            value = TextParser.extract_vertical_kv(
                text, key,
                value_pattern=r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)"
            )
        
        if not value:
            return None
        
        # 提取日期部分（YYYY-MM-DD 或 YYYY/MM/DD 或 YYYY年MM月DD日）
        date_match = re.search(
            r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日]?",
            value
        )
        
        if date_match:
            year, month, day = date_match.groups()
            # 标准化为 YYYY-MM-DD
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return None
    
    @staticmethod
    def extract_from_table(pdf_path: str, 
                          table_markers: List[str],
                          row_identifier: Dict[str, str],
                          target_column: str) -> Optional[str]:
        """
        从PDF表格中提取单元格值
        
        Args:
            pdf_path: PDF文件路径
            table_markers: 表格标识词列表（用于定位表格）
            row_identifier: 行标识 {"column": "key_column", "value": "key_value"}
            target_column: 目标列名
            
        Returns:
            目标单元格的值
            
        示例：
            extract_from_table(
                pdf_path,
                ["成交结果", "序号", "成交人"],
                {"column": "序号", "value": "1"},
                "成交人"
            ) → "XX科技有限公司"
        """
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # 检查页面是否包含表格标记
                    page_text = page.extract_text() or ""
                    if not any(marker in page_text for marker in table_markers):
                        continue
                    
                    # 提取表格
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        # 假设第一行是表头
                        headers = [cell.strip() if cell else "" for cell in table[0]]
                        
                        # 查找目标列索引
                        try:
                            target_col_idx = headers.index(target_column)
                            key_col_idx = headers.index(row_identifier["column"])
                        except ValueError:
                            continue
                        
                        # 查找匹配的行
                        for row in table[1:]:
                            if len(row) > max(target_col_idx, key_col_idx):
                                if row[key_col_idx] and row_identifier["value"] in str(row[key_col_idx]):
                                    target_value = row[target_col_idx]
                                    if target_value:
                                        return target_value.strip()
            
            return None
            
        except Exception as e:
            print(f"表格提取错误: {e}")
            return None
    
    @staticmethod
    def extract_table_first_data_row(pdf_path: str,
                                    table_marker: str,
                                    column_name: str) -> Optional[str]:
        """
        提取表格第一个数据行的指定列值（简化版）
        
        Args:
            pdf_path: PDF文件路径
            table_marker: 表格标识词
            column_name: 列名
            
        Returns:
            第一个数据行的该列值
        """
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if table_marker not in page_text:
                        continue
                    
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        headers = [cell.strip() if cell else "" for cell in table[0]]
                        
                        # 查找列索引
                        try:
                            col_idx = headers.index(column_name)
                        except ValueError:
                            continue
                        
                        # 返回第一个数据行的值
                        if len(table) > 1 and len(table[1]) > col_idx:
                            value = table[1][col_idx]
                            if value:
                                return value.strip()
            
            return None
            
        except Exception as e:
            print(f"表格提取错误: {e}")
            return None
    
    @staticmethod
    def clean_whitespace(text: str) -> str:
        """清理多余空白字符"""
        if not text:
            return ""
        # 替换多个空白为单个空格
        cleaned = re.sub(r'\s+', ' ', text)
        return cleaned.strip()
    
    @staticmethod
    def remove_special_chars(text: str, keep_chars: str = "") -> str:
        """
        移除特殊字符
        
        Args:
            text: 源文本
            keep_chars: 要保留的特殊字符
        """
        if not text:
            return ""
        
        # 定义允许的字符：中文、英文、数字、keep_chars
        pattern = rf"[^\u4e00-\u9fa5a-zA-Z0-9{re.escape(keep_chars)}\s]"
        return re.sub(pattern, "", text)
    
    @staticmethod
    def split_by_delimiter(text: str, delimiters: List[str] = None) -> List[str]:
        """
        按多个分隔符分割文本
        
        Args:
            text: 源文本
            delimiters: 分隔符列表（默认：逗号、顿号、分号）
            
        Returns:
            分割后的列表
        """
        if not text:
            return []
        
        if delimiters is None:
            delimiters = ['、', '，', ',', '；', ';']
        
        # 构建分隔符模式
        pattern = '|'.join(re.escape(d) for d in delimiters)
        
        parts = re.split(pattern, text)
        return [p.strip() for p in parts if p.strip()]