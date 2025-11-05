"""
PDF智能提取 - 独立运行脚本
用于批量处理PDF文件并生成结构化JSON输出
"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# 设置Windows控制台UTF-8编码
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pdf_import.core.pdf_detector import PDFDetector
from pdf_import.core.field_extractor import FieldExtractor
from pdf_import.core.config_loader import ConfigLoader


class PDFBatchExtractor:
    """PDF批量提取器"""
    
    def __init__(self):
        """初始化提取器"""
        self.detector = PDFDetector()
        self.extractor = FieldExtractor()
        self.config_loader = ConfigLoader()
    
    def process_single_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        处理单个PDF文件
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            提取结果字典
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            return {
                'file': str(pdf_path),
                'status': 'error',
                'error': '文件不存在'
            }
        
        try:
            # 检测PDF类型
            pdf_type, confidence, method = self.detector.detect(str(pdf_path))
            
            print(f"\n{'='*60}")
            print(f"文件: {pdf_path.name}")
            print(f"检测类型: {pdf_type} (置信度: {confidence:.2f}, 方法: {method})")
            print(f"{'='*60}")
            
            if pdf_type == 'unknown' or confidence < 0.5:
                return {
                    'file': str(pdf_path),
                    'status': 'warning',
                    'detected_type': pdf_type,
                    'confidence': confidence,
                    'warning': 'PDF类型识别置信度低',
                    'extracted_data': {}
                }
            
            # 提取字段
            extracted_data = self.extractor.extract(str(pdf_path), pdf_type)
            
            # 统计提取结果
            total_fields = len(extracted_data)
            extracted_fields = sum(1 for v in extracted_data.values() if v is not None)
            
            print(f"\n提取统计:")
            print(f"  总字段数: {total_fields}")
            print(f"  成功提取: {extracted_fields}")
            print(f"  提取率: {extracted_fields/total_fields*100:.1f}%")
            
            return {
                'file': str(pdf_path),
                'filename': pdf_path.name,
                'status': 'success',
                'detected_type': pdf_type,
                'confidence': confidence,
                'detection_method': method,
                'extracted_data': extracted_data,
                'statistics': {
                    'total_fields': total_fields,
                    'extracted_fields': extracted_fields,
                    'extraction_rate': f"{extracted_fields/total_fields*100:.1f}%"
                }
            }
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"错误: {e}")
            print(error_detail)
            
            return {
                'file': str(pdf_path),
                'status': 'error',
                'error': str(e),
                'error_detail': error_detail
            }
    
    def process_pdf_group(self, pdf_files: List[str]) -> Dict[str, Any]:
        """
        处理一组PDF文件（属于同一采购项目）
        
        Args:
            pdf_files: PDF文件路径列表
            
        Returns:
            合并提取结果
        """
        # 首先检测所有PDF类型
        pdf_type_map = {}
        for pdf_file in pdf_files:
            pdf_path = Path(pdf_file)
            if not pdf_path.exists():
                print(f"警告: 文件不存在 {pdf_file}")
                continue
            
            pdf_type, confidence, method = self.detector.detect(str(pdf_path))
            if pdf_type != 'unknown' and confidence >= 0.5:
                pdf_type_map[pdf_type] = str(pdf_path)
        
        print(f"\n{'='*60}")
        print(f"PDF组合提取 - 共 {len(pdf_type_map)} 个有效PDF")
        print(f"{'='*60}")
        for pdf_type, pdf_path in pdf_type_map.items():
            print(f"  {pdf_type}: {Path(pdf_path).name}")
        
        # 使用FieldExtractor的合并提取功能
        try:
            merged_data = self.extractor.extract_all_from_pdfs(pdf_type_map)
            
            # 统计
            total_fields = len(merged_data)
            extracted_fields = sum(1 for v in merged_data.values() if v is not None)
            
            print(f"\n合并提取统计:")
            print(f"  总字段数: {total_fields}")
            print(f"  成功提取: {extracted_fields}")
            print(f"  提取率: {extracted_fields/total_fields*100:.1f}%")
            
            return {
                'status': 'success',
                'pdf_files': pdf_type_map,
                'extracted_data': merged_data,
                'statistics': {
                    'total_fields': total_fields,
                    'extracted_fields': extracted_fields,
                    'extraction_rate': f"{extracted_fields/total_fields*100:.1f}%"
                }
            }
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"错误: {e}")
            print(error_detail)
            
            return {
                'status': 'error',
                'error': str(e),
                'error_detail': error_detail
            }
    
    def save_results_to_json(self, results: Any, output_path: str) -> None:
        """
        保存结果到JSON文件
        
        Args:
            results: 提取结果
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 添加元数据
        output_data = {
            'metadata': {
                'extraction_time': datetime.now().isoformat(),
                'version': '1.0'
            },
            'results': results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到: {output_path}")


def main():
    """主函数 - 处理指定的5个样本PDF文件"""
    
    # 定义样本PDF文件路径
    docs_dir = Path(__file__).parent.parent / 'docs'
    
    sample_files = [
        docs_dir / '2-23.采购请示OA审批（PDF导出版）.pdf',
        docs_dir / '2-24.采购公告-特区建工采购平台（PDF导出版）.pdf',
        docs_dir / '2-44.采购结果OA审批（PDF导出版）.pdf',
        docs_dir / '2-45.中标候选人公示-特区建工采购平台（PDF导出版）.pdf',
        docs_dir / '2-47.采购结果公示-特区建工采购平台（PDF导出版）.pdf'
    ]
    
    print("="*60)
    print("PDF智能提取系统 - 独立验证模式")
    print("="*60)
    print(f"样本文件数: {len(sample_files)}")
    print(f"工作目录: {Path.cwd()}")
    print("="*60)
    
    # 检查文件是否存在
    existing_files = []
    for file_path in sample_files:
        if file_path.exists():
            existing_files.append(str(file_path))
            print(f"[OK] {file_path.name}")
        else:
            print(f"[X] {file_path.name} (不存在)")
    
    if not existing_files:
        print("\n错误: 未找到任何样本PDF文件")
        print(f"请确保文件位于: {docs_dir}")
        return
    
    # 创建提取器
    extractor = PDFBatchExtractor()
    
    # 处理方式1: 单个文件提取（用于详细分析）
    print("\n\n" + "="*60)
    print("方式1: 单文件提取（详细模式）")
    print("="*60)
    
    individual_results = []
    for pdf_file in existing_files:
        result = extractor.process_single_pdf(pdf_file)
        individual_results.append(result)
    
    # 保存单文件提取结果
    output_dir = Path(__file__).parent.parent / 'data' / 'extraction_results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    extractor.save_results_to_json(
        individual_results,
        output_dir / f'individual_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )
    
    # 处理方式2: 组合提取（模拟真实场景）
    print("\n\n" + "="*60)
    print("方式2: 组合提取（实际应用模式）")
    print("="*60)
    print("将多个PDF作为同一采购项目处理，合并提取结果")
    
    merged_result = extractor.process_pdf_group(existing_files)
    
    # 保存合并提取结果
    extractor.save_results_to_json(
        merged_result,
        output_dir / f'merged_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )
    
    # 输出最终摘要
    print("\n\n" + "="*60)
    print("提取完成摘要")
    print("="*60)
    
    if merged_result['status'] == 'success':
        stats = merged_result['statistics']
        print(f"[OK] 状态: 成功")
        print(f"[OK] 处理文件数: {len(merged_result['pdf_files'])}")
        print(f"[OK] 总字段数: {stats['total_fields']}")
        print(f"[OK] 成功提取: {stats['extracted_fields']}")
        print(f"[OK] 提取率: {stats['extraction_rate']}")
        
        # 显示提取的数据
        print(f"\n提取的字段:")
        extracted_data = merged_result['extracted_data']
        for field_name, value in sorted(extracted_data.items()):
            if value is not None:
                # 截断过长的值
                value_str = str(value)
                if len(value_str) > 60:
                    value_str = value_str[:60] + '...'
                print(f"  {field_name}: {value_str}")
        
        # 显示未提取的字段
        null_fields = [k for k, v in extracted_data.items() if v is None]
        if null_fields:
            print(f"\n未提取字段 ({len(null_fields)}个):")
            for field in null_fields:
                print(f"  - {field}")
    else:
        print(f"[X] 状态: 失败")
        print(f"[X] 错误: {merged_result.get('error', '未知错误')}")
    
    print("\n" + "="*60)
    print(f"结果文件保存在: {output_dir}")
    print("="*60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断执行")
    except Exception as e:
        print(f"\n\n程序执行错误: {e}")
        import traceback
        traceback.print_exc()