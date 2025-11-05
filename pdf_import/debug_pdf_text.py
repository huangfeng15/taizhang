"""
PDF文本内容调试工具
用于查看PDF实际文本，帮助优化提取规则
"""
import sys
import fitz
from pathlib import Path

def debug_pdf_text(pdf_path, output_file, max_chars=3000):
    """输出PDF文本内容到文件"""
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"PDF文件: {Path(pdf_path).name}\n")
        f.write(f"{'='*80}\n\n")
        
        try:
            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc):
                text = page.get_text()
                f.write(f"--- 第{i+1}页 (前{max_chars}字符) ---\n")
                f.write(text[:max_chars])
                f.write(f"\n\n{'='*80}\n\n")
                if i >= 1:  # 只看前2页
                    break
            doc.close()
        except Exception as e:
            f.write(f"错误: {e}\n")

if __name__ == '__main__':
    # 调试所有样本PDF
    docs_dir = Path(__file__).parent.parent / 'docs'
    output_file = Path(__file__).parent.parent / 'pdf_text_debug.txt'
    
    # 清空输出文件
    if output_file.exists():
        output_file.unlink()
    
    pdf_files = [
        docs_dir / '2-23.采购请示OA审批（PDF导出版）.pdf',
        docs_dir / '2-24.采购公告-特区建工采购平台（PDF导出版）.pdf',
        docs_dir / '2-47.采购结果公示-特区建工采购平台（PDF导出版）.pdf',
    ]
    
    for pdf_file in pdf_files:
        if pdf_file.exists():
            debug_pdf_text(str(pdf_file), str(output_file), max_chars=3000)
    
    print(f"调试输出已保存到: {output_file}")