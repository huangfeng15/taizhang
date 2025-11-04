"""金额解析工具"""
from decimal import Decimal, InvalidOperation
import re
from typing import Optional


class AmountParser:
    """金额解析器"""
    
    @staticmethod
    def parse_amount(amount_str: str) -> Optional[Decimal]:
        """
        解析金额字符串
        
        Args:
            amount_str: 金额字符串
            
        Returns:
            Decimal对象或None
        """
        if not amount_str:
            return None
        
        # 移除货币符号和逗号
        cleaned = re.sub(r'[￥¥元,]', '', str(amount_str))
        cleaned = cleaned.strip()
        
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None