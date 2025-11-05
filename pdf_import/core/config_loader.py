"""
配置加载器 - 加载和验证YAML配置文件
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """配置加载和验证器"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置文件目录，默认为 pdf_import/config/
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / 'config'
        
        self.config_dir = Path(config_dir)
        self._field_mapping = None
        self._pdf_patterns = None
    
    def load_field_mapping(self) -> Dict[str, Any]:
        """
        加载字段映射配置
        
        Returns:
            字段映射配置字典
        """
        if self._field_mapping is not None:
            return self._field_mapping
        
        config_path = self.config_dir / 'field_mapping.yml'
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self._field_mapping = yaml.safe_load(f)
        
        # 验证配置结构
        self._validate_field_mapping(self._field_mapping)
        
        return self._field_mapping
    
    def load_pdf_patterns(self) -> Dict[str, Any]:
        """
        加载PDF识别模式配置
        
        Returns:
            PDF模式配置字典
        """
        if self._pdf_patterns is not None:
            return self._pdf_patterns
        
        config_path = self.config_dir / 'pdf_patterns.yml'
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self._pdf_patterns = yaml.safe_load(f)
        
        return self._pdf_patterns
    
    def get_field_config(self, field_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定字段的配置
        
        Args:
            field_name: 字段名
            
        Returns:
            字段配置字典，未找到返回None
        """
        mapping = self.load_field_mapping()
        return mapping.get('fields', {}).get(field_name)
    
    def get_fields_by_pdf_type(self, pdf_type: str) -> Dict[str, Dict[str, Any]]:
        """
        获取指定PDF类型应提取的所有字段
        
        Args:
            pdf_type: PDF类型（如 procurement_notice）
            
        Returns:
            {field_name: field_config, ...}
        """
        mapping = self.load_field_mapping()
        fields = mapping.get('fields', {})
        
        result = {}
        for field_name, config in fields.items():
            source = config.get('source', {})
            # 跳过手动填写的字段
            if source.get('manual'):
                continue
            # 匹配PDF类型（主来源或fallback来源）
            if source.get('pdf_type') == pdf_type:
                result[field_name] = config
            # 检查fallback_source
            elif config.get('fallback_source', {}).get('pdf_type') == pdf_type:
                # 为fallback类型创建临时配置
                fallback_config = config.copy()
                fallback_config['source'] = config['fallback_source']
                result[field_name] = fallback_config
        
        return result
    
    def get_manual_fields(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有需要手动填写的字段
        
        Returns:
            {field_name: field_config, ...}
        """
        mapping = self.load_field_mapping()
        fields = mapping.get('fields', {})
        
        return {
            name: config 
            for name, config in fields.items()
            if config.get('source', {}).get('manual')
        }
    
    def _validate_field_mapping(self, config: Dict[str, Any]) -> None:
        """
        验证字段映射配置的完整性
        
        Args:
            config: 配置字典
            
        Raises:
            ValueError: 配置无效时抛出
        """
        if not config:
            raise ValueError("配置文件为空")
        
        if 'fields' not in config:
            raise ValueError("配置缺少 'fields' 节点")
        
        fields = config['fields']
        if not isinstance(fields, dict):
            raise ValueError("'fields' 必须是字典类型")
        
        # 验证每个字段的基本结构
        for field_name, field_config in fields.items():
            if not isinstance(field_config, dict):
                raise ValueError(f"字段 '{field_name}' 配置必须是字典类型")
            
            # 检查必需的键
            required_keys = ['label', 'data_type', 'source']
            for key in required_keys:
                if key not in field_config:
                    raise ValueError(f"字段 '{field_name}' 缺少必需的配置项: {key}")
            
            # 验证source配置
            source = field_config['source']
            if not isinstance(source, dict):
                raise ValueError(f"字段 '{field_name}' 的 source 必须是字典类型")
            
            # source必须包含manual或pdf_type
            if not source.get('manual') and not source.get('pdf_type'):
                raise ValueError(
                    f"字段 '{field_name}' 的 source 必须指定 'manual' 或 'pdf_type'"
                )
    
    def get_enum_aliases(self, field_name: str) -> Dict[str, str]:
        """
        获取字段的枚举别名映射
        
        Args:
            field_name: 字段名
            
        Returns:
            别名映射字典 {alias: standard_value, ...}
        """
        field_config = self.get_field_config(field_name)
        if not field_config:
            return {}
        
        return field_config.get('aliases', {})
    
    def get_enum_choices(self, field_name: str) -> list:
        """
        获取字段的枚举选项列表
        
        Args:
            field_name: 字段名
            
        Returns:
            枚举选项列表
        """
        field_config = self.get_field_config(field_name)
        if not field_config:
            return []
        
        return field_config.get('choices', [])
    
    def reload(self) -> None:
        """重新加载所有配置（清除缓存）"""
        self._field_mapping = None
        self._pdf_patterns = None