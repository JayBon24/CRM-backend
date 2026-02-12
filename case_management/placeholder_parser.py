#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
占位符解析器
用于解析模板中的占位符信息
"""

import re
import json
import logging
from typing import Dict, List, Any, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class PlaceholderParser:
    """占位符解析器"""
    
    def __init__(self):
        """初始化解析器"""
        # 占位符正则表达式，支持 {{ key }} 和 {{ key | 默认值 }} 格式
        self.placeholder_pattern = re.compile(r'\{\{\s*([^}|]+)(?:\s*\|\s*([^}]+))?\s*\}\}')
        
        # 常见的占位符分类
        self.placeholder_categories = {
            'plaintiff': ['name', 'credit_code', 'address', 'legal_representative'],
            'defendant': ['name', 'credit_code', 'address', 'legal_representative'],
            'case': ['number', 'type', 'amount', 'description'],
            'court': ['name', 'address'],
            'date': ['filing_date', 'hearing_date', 'judgment_date'],
            'amount': ['contract_amount', 'lawyer_fee', 'damages'],
            'other': ['description', 'notes', 'remarks']
        }
    
    def parse_template_content(self, content: str) -> Dict[str, Any]:
        """解析模板内容中的占位符
        
        Args:
            content: 模板内容字符串
            
        Returns:
            包含占位符信息的字典
        """
        try:
            # 查找所有占位符
            placeholders = self._extract_placeholders(content)
            
            # 分析占位符
            analysis = self._analyze_placeholders(placeholders)
            
            result = {
                'placeholders': placeholders,
                'analysis': analysis,
                'total_count': len(placeholders),
                'unique_count': len(set(p['key'] for p in placeholders))
            }
            
            # 确保返回的数据格式正确，中文不被转义
            return self._ensure_chinese_format(result)
            
        except Exception as e:
            logger.error(f"解析模板内容失败: {e}")
            return {
                'placeholders': [],
                'analysis': {},
                'total_count': 0,
                'unique_count': 0,
                'error': str(e)
            }
    
    def parse_template_file(self, file_path: str) -> Dict[str, Any]:
        """解析模板文件中的占位符
        
        Args:
            file_path: 模板文件路径
            
        Returns:
            包含占位符信息的字典
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {
                    'placeholders': [],
                    'analysis': {},
                    'total_count': 0,
                    'unique_count': 0,
                    'error': '文件不存在'
                }
            
            # 根据文件类型读取内容
            if file_path.suffix.lower() in ['.txt', '.md', '.html']:
                # 文本文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif file_path.suffix.lower() in ['.docx', '.doc']:
                # Word文档，使用现有的解析函数
                from .direct_langchain_ai_service import parse_docx_file, parse_doc_file
                if file_path.suffix.lower() == '.docx':
                    content = parse_docx_file(str(file_path))
                else:
                    content = parse_doc_file(str(file_path))
            else:
                # 其他格式，尝试读取为文本
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    return {
                        'placeholders': [],
                        'analysis': {},
                        'total_count': 0,
                        'unique_count': 0,
                        'error': f'无法解析此格式的文件: {file_path.suffix}'
                    }
            
            # 解析内容
            return self.parse_template_content(content)
            
        except Exception as e:
            logger.error(f"解析模板文件失败: {e}")
            return {
                'placeholders': [],
                'analysis': {},
                'total_count': 0,
                'unique_count': 0,
                'error': str(e)
            }
    
    def _extract_placeholders(self, content: str) -> List[str]:
        """提取内容中的所有占位符
        
        Args:
            content: 模板内容
            
        Returns:
            占位符列表
        """
        placeholders = []
        matches = self.placeholder_pattern.findall(content)
        
        for match in matches:
            placeholder = match[0].strip()
            default_value = match[1].strip() if match[1] else None
            
            # 构建占位符信息
            placeholder_info = {
                'key': placeholder,
                'default_value': default_value,
                'full_match': f"{{{{ {placeholder}{' | ' + default_value if default_value else ''} }}}}"
            }
            placeholders.append(placeholder_info)
        
        return placeholders
    
    def _analyze_placeholders(self, placeholders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析占位符
        
        Args:
            placeholders: 占位符列表
            
        Returns:
            分析结果
        """
        analysis = {
            'by_category': {},
            'by_type': {},
            'with_defaults': [],
            'without_defaults': [],
            'nested_keys': [],
            'simple_keys': []
        }
        
        for placeholder in placeholders:
            key = placeholder['key']
            
            # 分类统计
            category = self._categorize_placeholder(key)
            if category not in analysis['by_category']:
                analysis['by_category'][category] = []
            analysis['by_category'][category].append(key)
            
            # 默认值统计
            if placeholder['default_value']:
                analysis['with_defaults'].append(key)
            else:
                analysis['without_defaults'].append(key)
            
            # 嵌套键统计
            if '.' in key:
                analysis['nested_keys'].append(key)
            else:
                analysis['simple_keys'].append(key)
        
        return analysis
    
    def _categorize_placeholder(self, key: str) -> str:
        """对占位符进行分类
        
        Args:
            key: 占位符键
            
        Returns:
            分类名称
        """
        key_lower = key.lower()
        
        # 根据键名进行分类
        if any(term in key_lower for term in ['plaintiff', '原告']):
            return 'plaintiff'
        elif any(term in key_lower for term in ['defendant', '被告']):
            return 'defendant'
        elif any(term in key_lower for term in ['case', '案件', 'case_number']):
            return 'case'
        elif any(term in key_lower for term in ['court', '法院', 'court_name']):
            return 'court'
        elif any(term in key_lower for term in ['date', '日期', 'time']):
            return 'date'
        elif any(term in key_lower for term in ['amount', '金额', 'money', 'fee']):
            return 'amount'
        else:
            return 'other'
    
    def get_placeholder_schema(self, placeholders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成占位符的JSON Schema
        
        Args:
            placeholders: 占位符列表
            
        Returns:
            JSON Schema
        """
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for placeholder in placeholders:
            key = placeholder['key']
            default_value = placeholder['default_value']
            
            # 根据键名推断类型
            field_type = self._infer_field_type(key, default_value)
            
            # 构建字段定义
            field_def = {
                "type": field_type,
                "description": f"占位符: {key}"
            }
            
            if default_value:
                field_def["default"] = default_value
            
            # 处理嵌套键
            if '.' in key:
                # 嵌套对象处理
                parts = key.split('.')
                current = schema["properties"]
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {"type": "object", "properties": {}}
                    current = current[part]["properties"]
                
                current[parts[-1]] = field_def
            else:
                schema["properties"][key] = field_def
            
            # 如果没有默认值，则添加到必需字段
            if not default_value:
                schema["required"].append(key)
        
        return schema
    
    def _infer_field_type(self, key: str, default_value: str = None) -> str:
        """推断字段类型
        
        Args:
            key: 占位符键
            default_value: 默认值
            
        Returns:
            字段类型
        """
        if default_value is not None:
            # 根据默认值推断类型
            if default_value.isdigit():
                return "integer"
            elif default_value.replace('.', '').isdigit():
                return "number"
            elif default_value.lower() in ['true', 'false']:
                return "boolean"
            else:
                return "string"
        
        # 根据键名推断类型
        key_lower = key.lower()
        if any(term in key_lower for term in ['amount', 'money', 'fee', 'price']):
            return "number"
        elif any(term in key_lower for term in ['date', 'time']):
            return "string"  # 日期作为字符串处理
        elif any(term in key_lower for term in ['count', 'number', 'id']):
            return "integer"
        else:
            return "string"
    
    def _ensure_chinese_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """确保数据中的中文格式正确
        
        Args:
            data: 要处理的数据
            
        Returns:
            处理后的数据
        """
        try:
            # 深度处理数据，确保所有字符串都是正确的Unicode格式
            return self._deep_ensure_unicode(data)
        except Exception as e:
            logger.warning(f"确保中文格式失败: {e}")
            return data
    
    def _deep_ensure_unicode(self, obj):
        """深度确保Unicode格式
        
        Args:
            obj: 要处理的对象
            
        Returns:
            处理后的对象
        """
        if isinstance(obj, dict):
            return {key: self._deep_ensure_unicode(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_ensure_unicode(item) for item in obj]
        elif isinstance(obj, str):
            # 确保字符串是Unicode格式，不是转义字符
            try:
                # 如果字符串包含Unicode转义字符，尝试解码
                if '\\u' in obj:
                    # 尝试解码Unicode转义字符
                    decoded = obj.encode().decode('unicode_escape')
                    return decoded
                return obj
            except:
                return obj
        else:
            return obj
    
    def fix_unicode_escaped_data(self, data):
        """修复包含Unicode转义字符的数据
        
        Args:
            data: 包含Unicode转义字符的数据
            
        Returns:
            修复后的数据
        """
        import json
        import re
        
        def fix_unicode_string(text):
            """修复字符串中的Unicode转义字符"""
            if not isinstance(text, str):
                return text
            
            # 查找所有Unicode转义字符
            unicode_pattern = r'\\u[0-9a-fA-F]{4}'
            matches = re.findall(unicode_pattern, text)
            
            if matches:
                # 替换Unicode转义字符
                for match in matches:
                    try:
                        # 将Unicode转义字符转换为实际字符
                        unicode_char = match.encode().decode('unicode_escape')
                        text = text.replace(match, unicode_char)
                    except:
                        pass
            
            return text
        
        def deep_fix_unicode(obj):
            """深度修复Unicode转义字符"""
            if isinstance(obj, dict):
                return {key: deep_fix_unicode(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [deep_fix_unicode(item) for item in obj]
            elif isinstance(obj, str):
                return fix_unicode_string(obj)
            else:
                return obj
        
        return deep_fix_unicode(data)


# 创建全局解析器实例
placeholder_parser = PlaceholderParser()
