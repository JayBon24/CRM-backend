"""
响应解析工具
"""
from typing import Dict, Any, List
import json
import re


class ResponseParser:
    """响应解析器"""
    
    @staticmethod
    def parse_ai_response(response: str) -> Dict[str, Any]:
        """
        解析 AI 响应
        
        Args:
            response: AI 原始响应
            
        Returns:
            解析后的响应数据
        """
        # 尝试解析 JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 部分
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # 返回纯文本响应
        return {
            "text": response,
            "type": "text"
        }
    
    @staticmethod
    def extract_suggestions(response: str) -> List[str]:
        """
        从响应中提取建议操作
        
        Args:
            response: AI 响应
            
        Returns:
            建议操作列表
        """
        suggestions = []
        
        # 尝试从 JSON 中提取
        parsed = ResponseParser.parse_ai_response(response)
        if isinstance(parsed, dict) and 'suggestions' in parsed:
            suggestions = parsed['suggestions']
        
        return suggestions

