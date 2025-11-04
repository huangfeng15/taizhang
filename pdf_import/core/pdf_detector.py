"""
PDF类型检测器 - 识别PDF文档类型
"""
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import yaml


class PDFDetector:
    """PDF文档类型识别器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化PDF检测器"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'pdf_patterns.yml'
        
        self.patterns = self._load_patterns(config_path)
    
    def _load_patterns(self, config_path: str) -> Dict:
        """加载PDF识别模式配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except:
            # 如果配置文件不存在，使用默认模式
            return {
                'pdf_types': {
                    'procurement_request': {
                        'name': '采购请示',
                        'filename_patterns': ['采购请示', '请示', 'OA审批'],
                        'content_markers': ['采购请示', '申请人', '采购控制价', '定标方法'],
                        'confidence_threshold': 0.7
                    },
                    'procurement_notice': {
                        'name': '采购公告',
                        'filename_patterns': ['采购公告', '公告', '询价公告'],
                        'content_markers': ['询价公告', '项目编号', '开标时间', '采购控制价'],
                        'confidence_threshold': 0.7
                    },
                    'procurement_result_oa': {
                        'name': '采购结果OA',
                        'filename_patterns': ['采购结果', '结果', 'OA'],
                        'content_markers': ['采购结果', '中标单位', '中标金额'],
                        'confidence_threshold': 0.7
                    },
                    'candidate_publicity': {
                        'name': '候选人公示',
                        'filename_patterns': ['候选人公示', '候选人', '公示'],
                        'content_markers': ['候选人', '公示', '中标候选人'],
                        'confidence_threshold': 0.7
                    },
                    'result_publicity': {
                        'name': '结果公示',
                        'filename_patterns': ['结果公示', '成交结果'],
                        'content_markers': ['成交结果公示', '成交人', '成交价'],
                        'confidence_threshold': 0.7
                    }
                }
            }
    
    def detect(self, pdf_path: str) -> Tuple[str, float, str]:
        """
        检测PDF类型
        
        Returns:
            (pdf_type, confidence, method)
        """
        import fitz
        
        filename = Path(pdf_path).name
        
        # 提取PDF文本
        doc = fitz.open(pdf_path)
        text = ''
        for page in doc:
            text += page.get_text()
        doc.close()
        
        # 尝试识别
        best_match = ('unknown', 0.0, 'none')
        
        for pdf_type, config in self.patterns.get('pdf_types', {}).items():
            # 方法1: 文件名匹配
            filename_score = self._match_filename(filename, config.get('filename_patterns', []))
            if filename_score >= config.get('confidence_threshold', 0.7):
                best_match = (pdf_type, filename_score, 'filename')
                continue
            
            # 方法2: 内容标记匹配
            content_score = self._match_content(text, config.get('content_markers', []))
            if content_score > best_match[1]:
                best_match = (pdf_type, content_score, 'content')
        
        return best_match
    
    def _match_filename(self, filename: str, patterns: List[str]) -> float:
        """文件名匹配"""
        if not patterns:
            return 0.0
        
        matches = sum(1 for p in patterns if p in filename)
        return matches / len(patterns)
    
    def _match_content(self, text: str, markers: List[str]) -> float:
        """内容标记匹配"""
        if not markers:
            return 0.0
        
        matches = sum(1 for m in markers if m in text)
        return matches / len(markers)
    
    def detect_batch(self, pdf_paths: List[str]) -> Dict[str, List[Dict]]:
        """批量检测PDF类型"""
        results = {}
        
        for path in pdf_paths:
            pdf_type, confidence, method = self.detect(str(path))
            
            if pdf_type not in results:
                results[pdf_type] = []
            
            results[pdf_type].append({
                'path': str(path),
                'confidence': confidence,
                'method': method
            })
        
        return results