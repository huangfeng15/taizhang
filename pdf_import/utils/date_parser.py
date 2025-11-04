"""日期解析工具"""
import re
from datetime import datetime
from typing import Optional


class DateParser:
    """日期解析器"""
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[object]:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
            
        Returns:
            date对象或None
        """
        if not date_str:
            return None
        
        # 提取 YYYY-MM-DD 或 YYYY/MM/DD 格式
        match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
        if match:
            try:
                year, month, day = match.groups()
                return datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d').date()
            except:
                pass
        
        return None