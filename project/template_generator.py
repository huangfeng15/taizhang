"""
Excel 导入模板生成器
根据 YAML 配置文件生成标准化的导入模板
遵循 DRY 原则，避免硬编码
"""
import os
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.comments import Comment
from django.apps import apps
from project.helptext import get_message
from project.constants import get_current_year


class TemplateGenerator:
    """模板生成器"""
    
    def __init__(self, config_path: str):
        """
        初始化生成器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.model = self._get_model()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_model(self):
        """获取 Django 模型类"""
        module_name = self.config['metadata']['module']
        model_name = self.config['metadata']['model']
        return apps.get_model(module_name, model_name)
    
    def _get_choices_text(self, field_config: Dict) -> str:
        """获取选项文本"""
        if not field_config.get('choices_from_model'):
            return ""
        
        field_name = field_config['field']
        # 处理关联字段（如 project__project_name）
        if '__' in field_name:
            field_name = field_name.split('__')[0]
        
        try:
            model_field = self.model._meta.get_field(field_name)
            
            if hasattr(model_field, 'choices') and model_field.choices:
                choices = [display for value, display in model_field.choices]
                return "、".join(choices)
        except Exception as e:
            print(f"警告: 无法获取字段 {field_name} 的choices: {e}")
        
        return ""
    
    def _format_instructions(self) -> str:
        """
        格式化说明文本
        优先从 helptext 配置获取，如果不存在则使用模板配置
        """
        module_name = self.config['metadata']['module']
        
        # 尝试从 helptext 配置获取导入说明
        try:
            instructions = get_message('import', f'{module_name}_template')
            if instructions:
                return instructions
        except:
            pass
        
        # 降级到模板配置中的说明
        instructions = self.config['instructions']['content']
        
        # 替换占位符
        for field in self.config['fields']:
            if field.get('choices_from_model'):
                field_name = field['field'].split('__')[0] if '__' in field['field'] else field['field']
                placeholder = f"{{{field_name}_choices}}"
                choices_text = self._get_choices_text(field)
                if choices_text:
                    instructions = instructions.replace(placeholder, choices_text)
        
        return instructions
    
    def generate(self, output_path: str, year: Optional[int] = None) -> str:
        """
        生成模板文件
        
        Args:
            output_path: 输出目录
            year: 年份（用于文件名）
        
        Returns:
            生成的文件路径
        """
        if year is None:
            year = get_current_year()
        
        # 生成文件名
        filename_template = self.config['file']['name_template']
        filename = filename_template.format(year=year)
        filepath = Path(output_path) / filename
        
        # 创建工作簿
        wb = Workbook()
        ws = wb.active
        ws.title = self.config['file']['sheet_name']
        
        # 样式定义
        header_font = Font(bold=True, size=11, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        instruction_font = Font(size=10, color="FF0000")
        instruction_alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # 写入说明行
        instructions_row = self.config['instructions']['row']
        ws.merge_cells(start_row=instructions_row, start_column=1, 
                      end_row=instructions_row, end_column=len(self.config['fields']))
        cell = ws.cell(row=instructions_row, column=1)
        cell.value = self._format_instructions()
        cell.font = instruction_font
        cell.alignment = instruction_alignment
        ws.row_dimensions[instructions_row].height = 80
        
        # 写入表头
        header_row = instructions_row + 1
        for col_idx, field in enumerate(self.config['fields'], start=1):
            cell = ws.cell(row=header_row, column=col_idx)
            
            # 字段名（必填字段标记*）
            field_name = field['name']
            if field.get('required'):
                field_name += "*"
            
            cell.value = field_name
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
            
            # 设置列宽
            ws.column_dimensions[cell.column_letter].width = 15
            
            # 添加批注（帮助文本）
            if field.get('help_text'):
                comment = Comment(field['help_text'], "系统")
                cell.comment = comment
        
        # 保存文件
        wb.save(filepath)
        return str(filepath)


def generate_all_templates(output_dir: str, year: Optional[int] = None) -> List[str]:
    """
    生成所有模板
    
    Args:
        output_dir: 输出目录
        year: 年份
    
    Returns:
        生成的文件路径列表
    """
    templates_dir = Path(__file__).parent / 'import_templates'
    
    # 确保输出目录存在
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    generated_files = []
    
    for config_file in templates_dir.glob('*.yml'):
        print(f"正在生成模板: {config_file.name}")
        try:
            generator = TemplateGenerator(config_file)
            filepath = generator.generate(output_dir, year)
            print(f"  ✓ 已生成: {filepath}")
            generated_files.append(filepath)
        except Exception as e:
            print(f"  ✗ 生成失败: {e}")
            import traceback
            traceback.print_exc()
    
    return generated_files


def generate_template_by_module(module: str, output_dir: str, year: Optional[int] = None) -> Optional[str]:
    """
    根据模块名生成模板
    
    Args:
        module: 模块名（procurement, contract, payment, supplier_eval）
        output_dir: 输出目录
        year: 年份
    
    Returns:
        生成的文件路径，失败返回 None
    """
    templates_dir = Path(__file__).parent / 'import_templates'
    config_file = templates_dir / f'{module}.yml'
    
    if not config_file.exists():
        print(f"错误: 模板配置不存在: {config_file}")
        return None
    
    # 确保输出目录存在
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        generator = TemplateGenerator(config_file)
        filepath = generator.generate(output_dir, year)
        print(f"✓ 已生成模板: {filepath}")
        return filepath
    except Exception as e:
        print(f"✗ 生成模板失败: {e}")
        import traceback
        traceback.print_exc()
        return None