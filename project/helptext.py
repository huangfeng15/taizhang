"""
帮助文案管理
集中管理所有帮助文本和示例数据
支持按环境差异化配置
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from django.conf import settings
from project.enums import (
    ProcurementMethod, 
    FilePositioning, 
    ContractSource,
    get_enum_labels_text
)


class HelpTextManager:
    """帮助文案管理器"""
    
    def __init__(self):
        self.config = self._load_config()
        self.environment = self._get_environment()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path(__file__).parent / 'configs' / 'helptexts.yml'
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_environment(self) -> str:
        """获取当前环境"""
        debug = getattr(settings, 'DEBUG', True)
        return 'default' if debug else 'production'
    
    def get_contact_example(self, field: str) -> str:
        """
        获取联系人示例
        
        Args:
            field: 字段名（name/phone/email）
        
        Returns:
            示例值
        """
        contacts = self.config.get('contacts', {})
        env_contacts = contacts.get(self.environment, contacts.get('default', {}))
        return env_contacts.get(field, '')
    
    def get_field_config(self, module: str, field: str) -> Dict[str, str]:
        """
        获取字段配置
        
        Args:
            module: 模块名
            field: 字段名
        
        Returns:
            字段配置字典
        """
        fields = self.config.get('fields', {})
        module_fields = fields.get(module, {})
        field_config = module_fields.get(field, {})
        
        # 替换占位符
        return self._replace_placeholders(field_config)
    
    def get_help_text(self, module: str, field: str) -> str:
        """获取字段的帮助文本"""
        config = self.get_field_config(module, field)
        return config.get('help_text', '')
    
    def get_label(self, module: str, field: str) -> str:
        """获取字段的标签"""
        config = self.get_field_config(module, field)
        return config.get('label', '')
    
    def get_placeholder(self, module: str, field: str) -> str:
        """获取字段的占位符"""
        config = self.get_field_config(module, field)
        return config.get('placeholder', '')
    
    def get_message(self, category: str, key: str) -> str:
        """
        获取消息文本
        
        Args:
            category: 消息类别
            key: 消息键
        
        Returns:
            消息文本
        """
        messages = self.config.get('messages', {})
        category_messages = messages.get(category, {})
        message = category_messages.get(key, '')
        
        return self._replace_placeholders({'text': message})['text']
    
    def get_validation_message(self, key: str) -> str:
        """获取验证消息"""
        validation = self.config.get('validation', {})
        return validation.get(key, '')
    
    def _replace_placeholders(self, config: Dict) -> Dict:
        """替换配置中的占位符"""
        result = {}
        
        for key, value in config.items():
            if isinstance(value, str):
                # 替换联系人占位符
                value = value.replace('{contact_name}', self.get_contact_example('name'))
                value = value.replace('{contact_phone}', self.get_contact_example('phone'))
                value = value.replace('{contact_email}', self.get_contact_example('email'))
                
                # 替换枚举占位符
                value = self._replace_enum_placeholders(value)
            
            result[key] = value
        
        return result
    
    def _replace_enum_placeholders(self, text: str) -> str:
        """替换枚举占位符"""
        # 采购方式
        if '{procurement_method_choices}' in text:
            choices = get_enum_labels_text(ProcurementMethod)
            text = text.replace('{procurement_method_choices}', choices)
        
        # 文件定位
        if '{file_positioning_choices}' in text:
            choices = get_enum_labels_text(FilePositioning)
            text = text.replace('{file_positioning_choices}', choices)
        
        # 合同来源
        if '{contract_source_choices}' in text:
            choices = get_enum_labels_text(ContractSource)
            text = text.replace('{contract_source_choices}', choices)
        
        return text


# 全局实例
helptext_manager = HelpTextManager()


# 便捷函数
def get_help_text(module: str, field: str) -> str:
    """获取帮助文本的快捷函数"""
    return helptext_manager.get_help_text(module, field)


def get_label(module: str, field: str) -> str:
    """获取字段标签的快捷函数"""
    return helptext_manager.get_label(module, field)


def get_placeholder(module: str, field: str) -> str:
    """获取占位符的快捷函数"""
    return helptext_manager.get_placeholder(module, field)


def get_message(category: str, key: str) -> str:
    """获取消息文本的快捷函数"""
    return helptext_manager.get_message(category, key)


def get_validation_message(key: str) -> str:
    """获取验证消息的快捷函数"""
    return helptext_manager.get_validation_message(key)


def get_contact_example(field: str) -> str:
    """获取联系人示例的快捷函数"""
    return helptext_manager.get_contact_example(field)