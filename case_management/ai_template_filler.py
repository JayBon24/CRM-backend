"""
AI模板填充服务
使用AI进一步优化和填充模板数据，提高填充准确率
"""
import logging
from typing import Dict, Any, List
from .ai_service import generate_document_with_ai

logger = logging.getLogger(__name__)


class AITemplateFiller:
    """AI模板填充器"""
    
    def __init__(self):
        self.field_mapping = {
            'plaintiff_name': '原告名称',
            'plaintiff_address': '原告地址',
            'plaintiff_credit_code': '原告统一社会信用代码',
            'plaintiff_legal_representative': '原告法定代表人',
            'defendant_name': '被告名称',
            'defendant_address': '被告地址',
            'defendant_credit_code': '被告统一社会信用代码',
            'defendant_legal_representative': '被告法定代表人',
            'case_number': '案件编号',
            'case_name': '案件名称',
            'case_type': '案件类型',
            'jurisdiction': '管辖法院',
            'contract_amount': '合同金额',
            'lawyer_fee': '律师费',
            'contract_date': '合同签订日期',
            'dispute_date': '纠纷发生日期',
            'filing_date': '起诉日期'
        }
    
    def enhance_with_ai(self, extracted_content: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI增强数据填充"""
        try:
            # 构建AI提示词
            prompt = self._build_enhancement_prompt(extracted_content, case_data)
            
            # 调用AI服务 - 使用正确的参数格式
            ai_response = generate_document_with_ai({'prompt': prompt}, 'template_enhancement')
            
            # 检查AI响应格式
            if ai_response and isinstance(ai_response, dict):
                # 检查是否成功
                if ai_response.get('success', False):
                    # 检查是否有content字段
                    content = ai_response.get('content', '')
                    if content:
                        # 解析AI返回的结构化数据
                        enhanced_data = self._parse_ai_response(content)
                        
                        if enhanced_data:  # 只有当解析到有效数据时才合并
                            # 合并AI增强的数据
                            final_data = self._merge_ai_data(case_data, enhanced_data)
                            
                            logger.info(f"AI增强完成，更新了 {len(enhanced_data)} 个字段")
                            return final_data
                        else:
                            logger.warning("AI返回内容解析失败，使用基础提取结果")
                            return case_data
                    else:
                        logger.warning(f"AI成功但返回内容为空: {ai_response}")
                        return case_data
                else:
                    # AI失败，记录错误但继续使用基础提取结果
                    error_msg = ai_response.get('error', '未知错误')
                    logger.warning(f"AI增强失败: {error_msg}，使用基础提取结果")
                    return case_data
            else:
                logger.warning(f"AI增强失败，响应格式错误: {ai_response}")
                return case_data
                
        except Exception as e:
            logger.error(f"AI增强过程中出错: {e}，使用基础提取结果")
            return case_data
    
    def _build_enhancement_prompt(self, content: str, case_data: Dict[str, Any]) -> str:
        """构建AI增强提示词"""
        prompt = f"""
请分析以下法律文档内容，并提取或完善以下字段信息。请以JSON格式返回结果，只返回JSON数据，不要其他文字说明。

文档内容：
{content}

当前已有数据：
{self._format_current_data(case_data)}

需要提取/完善的字段：
- 原告名称 (plaintiff_name)
- 原告地址 (plaintiff_address) 
- 原告统一社会信用代码 (plaintiff_credit_code)
- 原告法定代表人 (plaintiff_legal_representative)
- 被告名称 (defendant_name)
- 被告地址 (defendant_address)
- 被告统一社会信用代码 (defendant_credit_code)
- 被告法定代表人 (defendant_legal_representative)
- 案件编号 (case_number)
- 案件名称 (case_name)
- 案件类型 (case_type)
- 管辖法院 (jurisdiction)
- 合同金额 (contract_amount) - 数字类型
- 律师费 (lawyer_fee) - 数字类型
- 合同签订日期 (contract_date) - YYYY-MM-DD格式
- 纠纷发生日期 (dispute_date) - YYYY-MM-DD格式
- 起诉日期 (filing_date) - YYYY-MM-DD格式

要求：
1. 如果文档中没有某个字段的信息，请保持原值或设为null
2. 金额字段请转换为数字（去掉单位）
3. 日期字段请转换为YYYY-MM-DD格式
4. 确保提取的信息准确且完整
5. 只返回JSON格式的数据，不要其他说明

返回格式示例：
{{
    "plaintiff_name": "张三",
    "plaintiff_address": "北京市朝阳区xxx街道xxx号",
    "defendant_name": "李四",
    "contract_amount": 100000.0,
    "lawyer_fee": 5000.0
}}
"""
        return prompt
    
    def _format_current_data(self, case_data: Dict[str, Any]) -> str:
        """格式化当前数据用于提示词"""
        formatted = []
        for key, value in case_data.items():
            if key in self.field_mapping and value:
                chinese_name = self.field_mapping[key]
                formatted.append(f"- {chinese_name}: {value}")
        return '\n'.join(formatted) if formatted else "无"
    
    def _parse_ai_response(self, ai_content: str) -> Dict[str, Any]:
        """解析AI返回的JSON数据"""
        try:
            import json
            import re
            
            logger.info(f"开始解析AI响应内容: {ai_content[:200]}...")
            
            # 检查是否是错误信息
            if '失败' in ai_content or '错误' in ai_content or 'error' in ai_content.lower():
                logger.warning(f"AI返回了错误信息: {ai_content}")
                return {}
            
            # 清理内容，去除可能的markdown格式
            cleaned_content = ai_content.strip()
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.endswith('```'):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()
            
            # 尝试直接解析
            try:
                result = json.loads(cleaned_content)
                logger.info(f"直接解析JSON成功: {list(result.keys())}")
                return result
            except json.JSONDecodeError:
                pass
            
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', cleaned_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                logger.info(f"找到JSON字符串: {json_str[:100]}...")
                result = json.loads(json_str)
                logger.info(f"提取JSON解析成功: {list(result.keys())}")
                return result
            else:
                logger.warning("AI返回内容中未找到JSON格式数据")
                logger.warning(f"原始内容: {ai_content}")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"解析AI返回的JSON失败: {e}")
            logger.error(f"尝试解析的内容: {ai_content}")
            return {}
        except Exception as e:
            logger.error(f"解析AI响应时出错: {e}")
            return {}
    
    def _merge_ai_data(self, original_data: Dict[str, Any], ai_data: Dict[str, Any]) -> Dict[str, Any]:
        """合并AI增强的数据"""
        merged_data = original_data.copy()
        
        for key, value in ai_data.items():
            if value is not None and value != "" and value != "null":
                # 处理数字类型字段
                if key in ['contract_amount', 'lawyer_fee']:
                    try:
                        merged_data[key] = float(value)
                    except (ValueError, TypeError):
                        logger.warning(f"无法转换 {key} 为数字: {value}")
                        continue
                # 处理日期字段
                elif key in ['contract_date', 'dispute_date', 'filing_date']:
                    merged_data[key] = str(value)
                # 处理其他字段
                else:
                    merged_data[key] = str(value)
                
                logger.info(f"AI增强字段 {key}: {value}")
        
        return merged_data


# 创建全局实例
ai_template_filler = AITemplateFiller()
