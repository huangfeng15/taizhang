"""
PDF文件过滤器 - 智能识别并过滤特定编号的PDF文件
"""
import re
from typing import List, Tuple
from pathlib import Path


class PDFFileFilter:
    """
    PDF文件智能过滤器
    
    根据文件名中的编号自动识别并过滤需要处理的PDF文件。
    支持的编号格式：2-21、2-23、2-24、2-25、2-44、2-45、2-47
    """
    
    # 允许处理的PDF文件编号列表（已过滤2-25，因为它与2-24重复）
    ALLOWED_NUMBERS = ['2-21', '2-23', '2-24', '2-44', '2-45', '2-47']
    
    # 编号对应的文档类型说明（用于日志和提示）
    NUMBER_DESCRIPTIONS = {
        '2-21': '采购控制价OA审批',
        '2-23': '采购请示OA审批',
        '2-24': '采购公告-特区建工采购平台',
        '2-44': '采购结果OA审批',
        '2-45': '中标候选人公示-特区建工采购平台',
        '2-47': '采购结果公示-特区建工采购平台',
    }
    
    # 被过滤的重复编号及其原因
    EXCLUDED_NUMBERS = {
        '2-25': '与2-24重复（采购公告）',
    }
    
    @classmethod
    def should_process_file(cls, filename: str) -> Tuple[bool, str, str]:
        """
        判断文件是否应该被处理
        
        Args:
            filename: PDF文件名
            
        Returns:
            (should_process, matched_number, reason)
            - should_process: 是否应该处理该文件
            - matched_number: 匹配到的编号（如果有）
            - reason: 决策原因说明
        """
        # 提取文件名（去除扩展名）
        file_stem = Path(filename).stem
        
        # 使用正则表达式查找编号模式
        # 支持格式：2-21、2_21、2.21 等变体
        pattern = r'(\d+[-_.]?\d+)'
        matches = re.findall(pattern, file_stem)
        
        if not matches:
            return False, '', f'文件名中未找到编号模式'
        
        # 标准化编号格式（统一为 "数字-数字" 格式）
        for match in matches:
            # 将各种分隔符统一为短横线
            normalized = re.sub(r'[-_.]', '-', match)
            
            # 检查是否在允许列表中
            if normalized in cls.ALLOWED_NUMBERS:
                doc_type = cls.NUMBER_DESCRIPTIONS.get(normalized, '未知类型')
                return True, normalized, f'匹配编号 {normalized} ({doc_type})'
        
        # 如果有编号但不在允许列表中
        found_numbers = [re.sub(r'[-_.]', '-', m) for m in matches]
        return False, '', f'文件编号 {", ".join(found_numbers)} 不在处理范围内'
    
    @classmethod
    def filter_pdf_files(cls, file_list: List[dict]) -> Tuple[List[dict], List[dict]]:
        """
        批量过滤PDF文件列表
        
        Args:
            file_list: 文件信息字典列表，每个字典包含 'name', 'path', 'size' 等字段
            
        Returns:
            (allowed_files, filtered_files)
            - allowed_files: 允许处理的文件列表
            - filtered_files: 被过滤掉的文件列表（附带原因）
        """
        allowed_files = []
        filtered_files = []
        
        for file_info in file_list:
            filename = file_info.get('name', '')
            
            # 检查是否应该处理
            should_process, matched_number, reason = cls.should_process_file(filename)
            
            if should_process:
                # 添加匹配信息到文件信息中
                file_info_copy = file_info.copy()
                file_info_copy['matched_number'] = matched_number
                file_info_copy['doc_type'] = cls.NUMBER_DESCRIPTIONS.get(matched_number, '未知类型')
                allowed_files.append(file_info_copy)
            else:
                # 添加过滤原因
                file_info_copy = file_info.copy()
                file_info_copy['filter_reason'] = reason
                filtered_files.append(file_info_copy)
        
        return allowed_files, filtered_files
    
    @classmethod
    def get_filter_summary(cls, total_count: int, allowed_count: int, filtered_count: int) -> str:
        """
        生成过滤摘要信息
        
        Args:
            total_count: 总文件数
            allowed_count: 允许处理的文件数
            filtered_count: 被过滤的文件数
            
        Returns:
            格式化的摘要字符串
        """
        summary_lines = [
            f'📊 文件过滤摘要：',
            f'  • 总文件数：{total_count}',
            f'  • 允许处理：{allowed_count}',
            f'  • 已过滤：{filtered_count}',
        ]
        
        if allowed_count > 0:
            summary_lines.append(f'  ✅ 将处理包含以下编号的PDF：{", ".join(cls.ALLOWED_NUMBERS)}')
        
        return '\n'.join(summary_lines)
    
    @classmethod
    def validate_allowed_numbers(cls) -> bool:
        """
        验证允许的编号列表配置是否正确
        
        Returns:
            配置是否有效
        """
        if not cls.ALLOWED_NUMBERS:
            return False
        
        # 检查编号格式是否正确（应该是 "数字-数字" 格式）
        pattern = r'^\d+-\d+$'
        for number in cls.ALLOWED_NUMBERS:
            if not re.match(pattern, number):
                return False
        
        return True
    
    @classmethod
    def get_allowed_numbers_display(cls) -> str:
        """
        获取允许的编号列表的友好显示格式
        
        Returns:
            格式化的编号列表字符串
        """
        items = []
        for number in cls.ALLOWED_NUMBERS:
            desc = cls.NUMBER_DESCRIPTIONS.get(number, '未知类型')
            items.append(f'{number}（{desc}）')
        
        return '、'.join(items)