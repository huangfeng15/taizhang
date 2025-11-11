"""日期解析工具"""
import re
from datetime import datetime
from typing import Optional


class DateParser:
    """日期解析器 - 支持多种日期格式"""
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[object]:
        """
        解析日期字符串，支持多种格式：
        - YYYY年MM月DD日 (例如: 2024年10月15日)
        - YYYY/MM/DD (例如: 2024/10/15)
        - YYYY-MM-DD (例如: 2024-10-15)
        
        Args:
            date_str: 日期字符串
            
        Returns:
            date对象或None
        """
        if not date_str:
            return None
        
        # 转换为字符串并去除空白
        date_str = str(date_str).strip()
        
        if not date_str:
            return None
        
        # 过滤无效输入：只包含分隔符的情况
        # 例如: "/", "-", "//", "--", "//" 等
        if re.match(r'^[-/\s]+$', date_str):
            return None
        
        # 格式1: YYYY年MM月DD日
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
        if match:
            try:
                year, month, day = match.groups()
                return datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d').date()
            except:
                pass
        
        # 格式2: YYYY-MM-DD 或 YYYY/MM/DD
        match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
        if match:
            try:
                year, month, day = match.groups()
                return datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d').date()
            except:
                pass
        
        return None