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

        返回:
            (pdf_type, confidence, method)

        说明:
        - 综合文件名与内容标记得分，支持权重与最低置信度（见 pdf_patterns.yml 中 detection_strategy）。
        - 为避免大型 PDF 性能问题，只解析前若干页文本。
        """
        import fitz

        filename = Path(pdf_path).name

        # 读取配置中的识别策略（带默认值，保持向后兼容）
        strategy = self.patterns.get('detection_strategy', {}) or {}
        filename_weight = float(strategy.get('filename_weight', 0.6))
        content_weight = float(strategy.get('content_weight', 0.4))
        min_confidence = float(strategy.get('min_confidence', 0.5))

        # 提取PDF文本（仅前 N 页，降低性能压力）
        max_pages = 3
        text = ''
        try:
            doc = fitz.open(pdf_path)
            for page_index, page in enumerate(doc):
                text += page.get_text()
                if page_index + 1 >= max_pages:
                    break
            doc.close()
        except Exception as exc:
            # 打印错误并回退为内容为空，后续只依赖文件名匹配
            print(f"PDF类型识别时文本提取失败: {exc}")

        best_type = 'unknown'
        best_score = 0.0
        best_method = 'none'

        for pdf_type, config in self.patterns.get('pdf_types', {}).items():
            filename_patterns = config.get('filename_patterns', []) or []
            content_markers = config.get('content_markers', []) or []

            # 方法1: 文件名匹配（正则）
            filename_score = self._match_filename(filename, filename_patterns)

            # 方法2: 内容标记匹配（关键词命中率）
            content_score = self._match_content(text, content_markers) if text else 0.0

            total_score = filename_weight * filename_score + content_weight * content_score

            # 记录最优类型（分数相同时按 priority 选择）
            if total_score > best_score:
                best_type = pdf_type
                best_score = total_score
                best_method = 'filename+content' if filename_score and content_score else (
                    'filename' if filename_score else 'content'
                )
            elif total_score == best_score and best_type != 'unknown':
                # 使用配置中的 priority 作为并列时的决策依据（数值越小优先级越高）
                current_priority = self._get_priority(pdf_type)
                best_priority = self._get_priority(best_type)
                if current_priority < best_priority:
                    best_type = pdf_type
                    best_score = total_score
                    best_method = 'filename+content' if filename_score and content_score else (
                        'filename' if filename_score else 'content'
                    )

        # 若最高得分低于最低置信度，则判定为 unknown
        if best_score < min_confidence:
            return 'unknown', best_score, 'none'

        return best_type, best_score, best_method
    
    def _match_filename(self, filename: str, patterns: List[str]) -> float:
        """文件名匹配（支持正则列表，返回命中率）"""
        if not patterns:
            return 0.0

        matches = 0
        for pattern in patterns:
            if not pattern:
                continue
            try:
                if re.search(pattern, filename):
                    matches += 1
            except re.error:
                # 如果正则无效，退化为简单子串匹配，避免因配置错误导致整体失败
                if pattern in filename:
                    matches += 1

        return matches / len(patterns)
    
    def _match_content(self, text: str, markers: List[str]) -> float:
        """内容标记匹配"""
        if not markers:
            return 0.0
        
        matches = sum(1 for m in markers if m in text)
        return matches / len(markers)

    def _get_priority(self, pdf_type: str) -> int:
        """获取配置中的 priority，默认较低优先级"""
        pdf_cfg = self.patterns.get('pdf_types', {}).get(pdf_type, {}) or {}
        try:
            return int(pdf_cfg.get('priority', 100))
        except (TypeError, ValueError):
            return 100
    
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
