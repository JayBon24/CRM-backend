"""
智能文档填充主控制器 - 整合所有功能模块
基于现有人工录入生成文书功能优化实现
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from django.conf import settings

# 导入自定义模块
from .document_converter import DocumentConverter, convert_docx_to_markdown, convert_docx_to_xml
from .intelligent_filler import IntelligentFiller, fill_template_with_ai, extract_and_fill_template
from .document_rebuilder import DocumentRebuilder, rebuild_document_from_markdown, rebuild_document_from_xml

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartDocumentFiller:
    """智能文档填充主控制器"""
    
    def __init__(self):
        """初始化智能文档填充器"""
        self.filler = IntelligentFiller()
    
    def fill_document_from_template(self, template_path: str, case_data: Dict[str, Any], 
                                  output_path: str, use_xml: bool = False) -> Dict[str, Any]:
        """
        从模板文件智能填充文档
        
        Args:
            template_path: 模板文件路径
            case_data: 案例数据
            output_path: 输出文件路径
            use_xml: 是否使用XML格式
            
        Returns:
            填充结果
        """
        try:
            logger.info(f"开始智能填充文档: {template_path}")
            
            # 1. 转换模板为结构化格式
            logger.info("正在转换模板...")
            converter = DocumentConverter(template_path)
            
            if use_xml:
                template_content = converter.to_xml()
                logger.info("模板已转换为XML格式")
            else:
                template_content = converter.to_structured_markdown()
                logger.info("模板已转换为结构化Markdown格式")
            
            # 2. 使用AI智能填充内容
            logger.info("正在使用AI智能填充内容...")
            filled_content = self.filler.fill_structured_template(
                template_content, case_data, use_xml
            )
            
            # 3. 重建文档
            logger.info("正在重建文档...")
            rebuilder = DocumentRebuilder(template_path)
            
            if use_xml:
                success = rebuilder.rebuild_from_xml(filled_content, output_path)
            else:
                success = rebuilder.rebuild_from_structured_markdown(filled_content, output_path)
            
            if success:
                logger.info(f"文档填充完成: {output_path}")
                return {
                    'success': True,
                    'output_path': output_path,
                    'template_path': template_path,
                    'case_data': case_data,
                    'message': '文档填充成功'
                }
            else:
                logger.error("文档重建失败")
                return {
                    'success': False,
                    'error': '文档重建失败',
                    'message': '文档重建失败'
                }
                
        except Exception as e:
            logger.error(f"智能填充文档失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'智能填充失败: {str(e)}'
            }
    
    def fill_all_templates(self, case_data: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
        """
        填充所有模板文件
        
        Args:
            case_data: 案例数据
            output_dir: 输出目录
            
        Returns:
            填充结果
        """
        try:
            # 获取模板目录
            template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'template')
            
            if not os.path.exists(template_dir):
                return {
                    'success': False,
                    'error': '模板目录不存在',
                    'message': '模板目录不存在'
                }
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            results = []
            success_count = 0
            error_count = 0
            
            # 遍历模板文件
            for filename in os.listdir(template_dir):
                if filename.startswith('~$'):  # 跳过临时文件
                    continue
                
                file_path = os.path.join(template_dir, filename)
                if not os.path.isfile(file_path):
                    continue
                
                # 只处理Word文档
                if not filename or not filename.lower().endswith(('.doc', '.docx')):
                    continue
                
                try:
                    # 生成输出文件名
                    name_without_ext = os.path.splitext(filename)[0]
                    output_filename = f"{name_without_ext}_填充版.docx"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # 填充文档
                    result = self.fill_document_from_template(file_path, case_data, output_path)
                    
                    if result['success']:
                        success_count += 1
                        results.append({
                            'template_name': filename,
                            'output_name': output_filename,
                            'success': True,
                            'output_path': output_path
                        })
                    else:
                        error_count += 1
                        results.append({
                            'template_name': filename,
                            'output_name': output_filename,
                            'success': False,
                            'error': result.get('error', '未知错误')
                        })
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理模板 {filename} 失败: {e}")
                    results.append({
                        'template_name': filename,
                        'output_name': f"{os.path.splitext(filename)[0]}_填充版.docx",
                        'success': False,
                        'error': str(e)
                    })
            
            return {
                'success': success_count > 0,
                'results': results,
                'success_count': success_count,
                'error_count': error_count,
                'total_count': len(results),
                'message': f'成功填充 {success_count} 个文档，失败 {error_count} 个'
            }
            
        except Exception as e:
            logger.error(f"填充所有模板失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'填充所有模板失败: {str(e)}'
            }
    
    def generate_smart_documents(self, case_data: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
        """
        智能生成文档（结合现有功能）
        
        Args:
            case_data: 案例数据
            output_dir: 输出目录
            
        Returns:
            生成结果
        """
        try:
            logger.info("开始智能生成文档")
            
            # 1. 使用现有的AI服务生成基础文档
            from .ai_service import generate_all_documents_with_ai
            ai_result = generate_all_documents_with_ai(case_data)
            
            # 2. 使用智能填充功能处理模板文件
            template_result = self.fill_all_templates(case_data, output_dir)
            
            # 3. 合并结果
            all_documents = []
            
            # 添加AI生成的文档
            if ai_result.get('success', False):
                for doc in ai_result.get('documents', []):
                    all_documents.append({
                        'name': doc.get('document_name', ''),
                        'type': 'ai_generated',
                        'content': doc.get('content', ''),
                        'success': doc.get('success', False),
                        'template_used': doc.get('template_name', '')
                    })
            
            # 添加模板填充的文档
            if template_result.get('success', False):
                for result in template_result.get('results', []):
                    all_documents.append({
                        'name': result.get('output_name', ''),
                        'type': 'template_filled',
                        'output_path': result.get('output_path', ''),
                        'success': result.get('success', False),
                        'template_used': result.get('template_name', '')
                    })
            
            return {
                'success': True,
                'documents': all_documents,
                'ai_generated_count': ai_result.get('success_count', 0),
                'template_filled_count': template_result.get('success_count', 0),
                'total_count': len(all_documents),
                'message': f'智能生成完成：AI生成 {ai_result.get("success_count", 0)} 个，模板填充 {template_result.get("success_count", 0)} 个'
            }
            
        except Exception as e:
            logger.error(f"智能生成文档失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'智能生成文档失败: {str(e)}'
            }

def smart_fill_document(template_path: str, case_data: Dict[str, Any], 
                       output_path: str, use_xml: bool = False) -> Dict[str, Any]:
    """
    智能填充单个文档的便捷函数
    
    Args:
        template_path: 模板文件路径
        case_data: 案例数据
        output_path: 输出文件路径
        use_xml: 是否使用XML格式
        
    Returns:
        填充结果
    """
    try:
        filler = SmartDocumentFiller()
        return filler.fill_document_from_template(template_path, case_data, output_path, use_xml)
    except Exception as e:
        logger.error(f"智能填充文档失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f'智能填充失败: {str(e)}'
        }

def smart_fill_all_templates(case_data: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
    """
    智能填充所有模板的便捷函数
    
    Args:
        case_data: 案例数据
        output_dir: 输出目录
        
    Returns:
        填充结果
    """
    try:
        filler = SmartDocumentFiller()
        return filler.fill_all_templates(case_data, output_dir)
    except Exception as e:
        logger.error(f"智能填充所有模板失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f'智能填充所有模板失败: {str(e)}'
        }

def generate_smart_documents(case_data: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
    """
    智能生成文档的便捷函数
    
    Args:
        case_data: 案例数据
        output_dir: 输出目录
        
    Returns:
        生成结果
    """
    try:
        filler = SmartDocumentFiller()
        return filler.generate_smart_documents(case_data, output_dir)
    except Exception as e:
        logger.error(f"智能生成文档失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f'智能生成文档失败: {str(e)}'
        }

if __name__ == "__main__":
    # 测试智能文档填充功能
    test_case_data = {
        "案件编号": "2024民初1234号",
        "案件名称": "张三诉李四合同纠纷案",
        "案件类型": "合同纠纷",
        "管辖法院": "北京市朝阳区人民法院",
        "拟稿人": "李律师",
        "原告名称": "张三",
        "原告所住地": "北京市朝阳区",
        "原告统一社会信用代码": "91110105MA01234567",
        "原告法定代表人": "张三",
        "被告名称": "李四",
        "被告所住地": "北京市海淀区",
        "被告统一社会信用代码": "91110108MA07654321",
        "被告法定代表人": "李四",
        "合同金额": 100000,
        "律师费": 10000
    }
    
    # 测试单个文档填充
    template_path = "backend/template/起诉状.docx"
    output_path = "test_output/起诉状_填充版.docx"
    
    if os.path.exists(template_path):
        result = smart_fill_document(template_path, test_case_data, output_path)
        print(f"单个文档填充结果: {result}")
    else:
        print(f"模板文件不存在: {template_path}")
    
    # 测试所有模板填充
    output_dir = "test_output"
    result = smart_fill_all_templates(test_case_data, output_dir)
    print(f"所有模板填充结果: {result}")
    
    # 测试智能生成文档
    result = generate_smart_documents(test_case_data, output_dir)
    print(f"智能生成文档结果: {result}")
