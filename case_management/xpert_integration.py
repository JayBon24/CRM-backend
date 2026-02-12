"""
XpertAI平台集成模块
用于与XpertAI智能体平台进行交互
"""

import os
import logging
import asyncio
import json
import hashlib
from typing import List, Dict, Any, Optional
from langgraph_sdk import client
from django.conf import settings

logger = logging.getLogger(__name__)


class XpertAIClient:
    """XpertAI平台客户端"""
    
    def __init__(self, api_url: str = None, api_key: str = None):
        """
        初始化XpertAI客户端
        
        Args:
            api_url: API地址，默认为XpertAI平台地址
            api_key: API密钥
        """
        # 优先使用传入的参数，其次使用Django配置，最后使用环境变量
        self.api_url = api_url or getattr(settings, 'XPERT_API_URL', None) or "https://api.mtda.cloud/api/ai/"
        self.api_key = api_key or getattr(settings, 'LANGGRAPH_API_KEY', None) or os.getenv("LANGGRAPH_API_KEY")
        
        if not self.api_key:
            raise ValueError("API密钥未提供，请设置api_key参数、LANGGRAPH_API_KEY配置或环境变量")
        
        # 初始化客户端
        self.client = client.get_client(
            url=self.api_url,
            api_key=self.api_key
        )
        
        logger.info(f"XpertAI客户端初始化成功，API地址: {self.api_url}")
    
    async def get_experts(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取数字专家列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            数字专家列表
        """
        try:
            logger.info(f"正在获取数字专家列表，limit={limit}, offset={offset}")
            
            # 调用SDK获取专家列表
            experts = await self.client.assistants.search(
                metadata=None,
                offset=offset,
                limit=limit
            )
            
            # 转换为字典格式便于处理
            experts_list = []
            for expert in experts:
                # 专家对象已经是字典格式，直接使用
                expert_dict = {
                    'assistant_id': expert.get('assistant_id'),
                    'name': expert.get('name'),
                    'description': expert.get('description'),
                    'instructions': expert.get('instructions'),
                    'model': expert.get('model'),
                    'metadata': expert.get('metadata'),
                    'created_at': expert.get('created_at'),
                    'updated_at': expert.get('updated_at'),
                    'version': expert.get('version'),
                    'graph_id': expert.get('graph_id'),
                    'config': expert.get('config'),
                    'context': expert.get('context')
                }
                experts_list.append(expert_dict)
            
            logger.info(f"成功获取到 {len(experts_list)} 个数字专家")
            return experts_list
            
        except Exception as e:
            import traceback
            logger.error(f"获取数字专家列表失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"详细错误:\n{traceback.format_exc()}")
            raise
    
    async def get_expert_by_id(self, expert_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单个数字专家
        
        Args:
            expert_id: 专家ID
            
        Returns:
            数字专家信息
        """
        try:
            logger.info(f"正在获取数字专家: {expert_id}")
            
            expert = await self.client.assistants.get(expert_id)
            
            expert_dict = {
                'assistant_id': expert.get('assistant_id'),
                'name': expert.get('name'),
                'description': expert.get('description'),
                'instructions': expert.get('instructions'),
                'model': expert.get('model'),
                'metadata': expert.get('metadata'),
                'created_at': expert.get('created_at'),
                'updated_at': expert.get('updated_at'),
                'version': expert.get('version'),
                'graph_id': expert.get('graph_id'),
                'config': expert.get('config'),
                'context': expert.get('context')
            }
            
            logger.info(f"成功获取数字专家: {expert_dict.get('name', 'Unknown')}")
            return expert_dict
            
        except Exception as e:
            logger.error(f"获取数字专家失败: {e}")
            return None
    
    async def create_thread(self, thread_id: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        创建新的对话线程
        
        Args:
            thread_id: 线程ID，可选
            metadata: 元数据
            
        Returns:
            线程信息
        """
        try:
            logger.info("正在创建新线程")
            
            thread = await self.client.threads.create(
                thread_id=thread_id,
                metadata=metadata
            )
            
            thread_dict = {
                'thread_id': thread.get('thread_id'),
                'status': thread.get('status'),
                'metadata': thread.get('metadata'),
                'created_at': thread.get('created_at'),
                'updated_at': thread.get('updated_at')
            }
            
            logger.info(f"成功创建线程: {thread_dict.get('thread_id')}")
            return thread_dict
            
        except Exception as e:
            logger.error(f"创建线程失败: {e}")
            raise
    
    async def run_expert(self, thread_id: str, expert_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行数字专家
        
        Args:
            thread_id: 线程ID
            expert_id: 专家ID
            input_data: 输入数据
            
        Returns:
            运行结果
        """
        try:
            logger.info(f"正在运行数字专家: {expert_id}")
            
            run = await self.client.runs.create(
                thread_id=thread_id,
                assistant_id=expert_id,
                input=input_data
            )
            
            run_dict = {
                'run_id': run.get('run_id'),
                'thread_id': run.get('thread_id'),
                'assistant_id': run.get('assistant_id'),
                'status': run.get('status'),
                'created_at': run.get('created_at'),
                'updated_at': run.get('updated_at')
            }
            
            logger.info(f"成功启动运行: {run_dict.get('run_id')}")
            return run_dict
            
        except Exception as e:
            logger.error(f"运行数字专家失败: {e}")
            raise
    
    def ask_expert(self, question: str, expert_id: str = "expert_001") -> str:
        """
        同步方法：向专家提问
        
        Args:
            question: 问题内容
            expert_id: 专家ID，默认为expert_001
            
        Returns:
            专家回答
        """
        import asyncio
        
        async def _ask_expert_async():
            try:
                # 创建线程
                thread = await self.create_thread()
                thread_id = thread.get('thread_id')
                
                if not thread_id:
                    raise ValueError("创建线程失败")
                
                # 准备输入数据
                input_data = {
                    "question": question,
                    "context": "请根据问题提供专业的回答"
                }
                
                # 运行专家
                result = await self.run_expert(thread_id, expert_id, input_data)
                
                # 获取专家回答
                if result.get('status') == 'completed':
                    # 获取消息
                    messages = await self.client.messages.list(thread_id=thread_id)
                    if messages.data:
                        latest_message = messages.data[0]
                        if latest_message.content:
                            return latest_message.content[0].text.value
                
                return "专家暂时无法回答，请稍后再试"
                
            except Exception as e:
                logger.error(f"ask_expert失败: {e}")
                return f"专家服务暂时不可用: {str(e)}"
        
        # 运行异步方法
        try:
            return asyncio.run(_ask_expert_async())
        except Exception as e:
            logger.error(f"ask_expert同步调用失败: {e}")
            return f"专家服务调用失败: {str(e)}"
    
    async def analyze_form_fields_with_expert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI专家分析表单字段匹配"""
        try:
            import json
            logger.info("开始使用AI专家分析表单字段匹配")
            
            # 获取专家列表
            experts = await self.get_experts(limit=1)
            if not experts:
                raise Exception("未找到可用的AI专家")
            
            expert_id = experts[0]['assistant_id']
            logger.info(f"使用专家: {expert_id}")
            
            # 创建对话线程
            thread = await self.create_thread()
            thread_id = thread['thread_id']
            
            # 准备专家输入数据
            form_data = data.get('form_data', {})
            placeholders = data.get('placeholders', [])
            
            expert_input = {
                "input": f"""请帮我匹配以下英文字段名和中文占位符，并返回简化的JSON格式。

英文字段名（来自表单数据）：
{json.dumps(form_data, ensure_ascii=False, indent=2)}

中文占位符（来自模板）：
{json.dumps(placeholders, ensure_ascii=False, indent=2)}

请分析每个英文字段名对应的中文占位符，并返回以下简化格式的JSON：
{{
    "31": [
        {{"key": "原告名称", "field": "plaintiff_name"}},
        {{"key": "原告法人代表人", "field": "plaintiff_legal_representative"}},
        {{"key": "被告名称", "field": "defendant_name"}},
        {{"key": "被告法定代表人", "field": "defendant_legal_representative"}},
        {{"key": "诉讼请求", "field": "contract_amount"}},
        {{"key": "管辖法院", "field": "court_name"}}
    ],
    "33": [
        {{"key": "原告名称", "field": "plaintiff_name"}},
        {{"key": "原告法人代表人", "field": "plaintiff_legal_representative"}},
        {{"key": "被告名称", "field": "defendant_name"}},
        {{"key": "被告法定代表人", "field": "defendant_legal_representative"}},
        {{"key": "诉讼请求", "field": "contract_amount"}},
        {{"key": "管辖法院", "field": "court_name"}}
    ]
}}

匹配规则：
1. plaintiff_name -> 原告名称
2. plaintiff_legal_representative -> 原告法人代表人  
3. defendant_name -> 被告名称
4. defendant_legal_representative -> 被告法定代表人
5. contract_amount -> 诉讼请求（需要格式化为法律语言）
6. lawyer_fee -> 相关费用信息
7. court_name -> 管辖法院
8. plaintiff_address -> 原告地址
9. defendant_address -> 被告地址
10. contract_date -> 时间
11. dispute_date -> 时间
12. filing_date -> 时间
13. 其他字段请根据语义进行合理匹配

重要要求：
- 必须为每个中文占位符找到对应的英文字段名
- 如果找不到直接匹配，请根据语义进行合理推断
- 对于没有对应英文字段的占位符，field字段设为null
- 使用模板ID作为键（这里是"33"）
- 每个匹配项包含key（中文占位符）和field（英文字段名）
- 只负责字段名匹配，不返回具体的值
- 字段值会从表单数据中根据field名获取
- 请确保返回有效的JSON格式"""
            }
            
            # 使用流式响应获取专家回答（参考analyze_documents_with_expert方法）
            try:
                # 创建流式运行
                stream = self.client.runs.stream(
                    thread_id=thread_id,
                    assistant_id=expert_id,
                    input=expert_input
                )
                
                logger.info("开始流式获取专家字段匹配响应...")
                expert_response = ""
                message_parts = []
                
                # 按照正确的流式响应处理结构
                chunk_count = 0
                async for chunk in stream:
                    chunk_count += 1
                    
                    try:
                        # 按照JavaScript代码的结构处理chunk
                        if hasattr(chunk, 'data') and chunk.data:
                            data = chunk.data
                            
                            # 处理消息类型的数据
                            if isinstance(data, dict) and data.get('type') == 'message':
                                message_data = data.get('data')
                                
                                # 处理字符串类型的数据
                                if isinstance(message_data, str):
                                    message_parts.append(message_data)
                                # 处理对象类型的数据
                                elif isinstance(message_data, dict):
                                    if message_data.get('type') == 'text':
                                        text_content = message_data.get('text', '')
                                        if text_content:
                                            message_parts.append(text_content)
                                    elif message_data.get('type') == 'message':
                                        # 处理直接的消息类型
                                        chunk_data = message_data.get('data')
                                        if chunk_data:
                                            if isinstance(chunk_data, str):
                                                message_parts.append(chunk_data)
                                            elif isinstance(chunk_data, dict):
                                                if chunk_data.get('type') == 'text':
                                                    text_content = chunk_data.get('text', '')
                                                    if text_content:
                                                        message_parts.append(text_content)
                        else:
                            # 尝试直接处理chunk
                            if hasattr(chunk, 'content'):
                                content = chunk.content
                                if isinstance(content, str):
                                    message_parts.append(content)
                            elif isinstance(chunk, str):
                                message_parts.append(chunk)
                    except Exception as chunk_error:
                        logger.warning(f"处理chunk时出错: {chunk_error}")
                        continue
                
                # 合并所有响应部分
                expert_response = ''.join(message_parts)
                logger.info(f"专家字段匹配响应获取完成，处理了 {chunk_count} 个chunks")
                
                if not expert_response:
                    raise Exception("专家未返回任何响应")
                
                # 解析JSON响应
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', expert_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = expert_response
                
                try:
                    matching_result = json.loads(json_str)
                    logger.info(f"专家字段匹配结果: {matching_result}")
                    return matching_result
                except json.JSONDecodeError as e:
                    logger.error(f"解析专家返回的JSON失败: {e}")
                    logger.error(f"原始响应: {expert_response}")
                    raise Exception(f"专家返回的不是有效的JSON格式: {e}")
                    
            except Exception as stream_error:
                logger.error(f"流式响应处理失败: {stream_error}")
                raise
            
        except Exception as e:
            logger.error(f"AI专家字段匹配失败: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """
        测试与XpertAI平台的连接
        
        Returns:
            连接是否成功
        """
        try:
            logger.info("正在测试与XpertAI平台的连接")
            
            # 尝试获取专家列表来测试连接
            experts = await self.get_experts(limit=1)
            
            logger.info("XpertAI平台连接测试成功")
            return True
            
        except Exception as e:
            logger.error(f"XpertAI平台连接测试失败: {e}")
            return False
    
    async def upload_file(self, file_data: str, file_name: str, file_type: str) -> Dict[str, Any]:
        """上传文件到XpertAI服务器"""
        try:
            import base64
            import requests
            
            # 解码Base64内容
            file_content = base64.b64decode(file_data)
            
            # 准备上传文件
            files = {
                'file': (file_name, file_content, file_type)
            }
            
            headers = {
                'x-api-key': self.api_key
            }
            
            # 上传文件到XpertAI服务器
            upload_url = f"{self.api_url}v1/file"
            response = requests.post(upload_url, files=files, headers=headers)
            
            if response.status_code in [200, 201]:  # 201表示创建成功
                upload_result = response.json()
                logger.info(f"文件上传成功: {file_name}, 文件ID: {upload_result.get('id', '未知')}")
                return upload_result
            else:
                logger.error(f"文件上传失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"文件上传异常: {str(e)}")
            return None
    
    async def analyze_documents_with_expert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI专家解析文档"""
        try:
            logger.info("开始使用AI专家解析文档")
            
            # 获取专家列表
            experts = await self.get_experts(limit=1)
            if not experts:
                raise Exception("未找到可用的AI专家")
            
            expert_id = experts[0]['assistant_id']
            logger.info(f"使用专家: {expert_id}")
            
            # 创建对话线程
            thread = await self.create_thread()
            thread_id = thread['thread_id']
            
            # 上传文件到XpertAI服务器
            uploaded_files = []
            for file in data.get('files', []):
                file_name = file.get('name', '未知文件')
                file_type = file.get('type', '未知类型')
                file_content = file.get('base64', '')
                
                if file_content:
                    upload_result = await self.upload_file(file_content, file_name, file_type)
                    if upload_result:
                        uploaded_files.append(upload_result)
                        logger.info(f"文件 {file_name} 上传成功，文件ID: {upload_result.get('id', '未知')}")
                        logger.info(f"文件 {file_name} 上传成功，文件结构: {upload_result}")
                    else:
                        logger.warning(f"文件 {file_name} 上传失败")
            
            # 准备模板信息，使用模板ID
            templates_info = []
            for template in data.get('templates', []):
                template_id = template.get('template_id', '未知ID')
                template_name = template.get('template_name', '未知模板')
                placeholders = template.get('placeholders', [])
                placeholder_names = [p.get('key', '') for p in placeholders]
                templates_info.append(f"- 模板ID: {template_id} (名称: {template_name}, 占位符: {', '.join(placeholder_names)})")
            
            # 按照正确的输入结构，包含上传的文件
            expert_input = {
                "input": f"""请帮我分析上传的文档并提取占位符信息：

                    模板信息：
                    {chr(10).join(templates_info) if templates_info else "无模板"}

                    请分析文档内容，提取与模板占位符匹配的信息，并返回JSON格式的分析结果，格式如下：
                    {{
                    "analysis": {{
                        "模板ID": {{
                        "placeholders": {{
                            "占位符名称": "提取的值"
                        }}
                        }}
                    }}
                    }}

                    注意：请使用模板ID作为键，不要使用模板名称。

                    请开始分析。""",
                "files": uploaded_files  # 传递上传的文件ID数组
            }
            
            # 打印发送给XpertAI平台的参数
            logger.info("=== 发送给XpertAI平台的参数 ===")
            logger.info(f"专家ID: {expert_id}")
            logger.info(f"线程ID: {thread_id}")
            logger.info(f"输入参数: {expert_input}")
            logger.info("=== 参数打印完成 ===")
            
            # 使用流式响应，等待所有响应完成后再解析
            try:
                # 创建流式运行
                stream = self.client.runs.stream(
                    thread_id=thread_id,
                    assistant_id=expert_id,
                    input=expert_input
                )
                
                logger.info("开始流式获取专家响应...")
                expert_response = ""
                message_parts = []
                
                # 按照正确的流式响应处理结构
                chunk_count = 0
                async for chunk in stream:
                    chunk_count += 1
                    
                    try:
                        # 按照JavaScript代码的结构处理chunk
                        if hasattr(chunk, 'data') and chunk.data:
                            data = chunk.data
                            
                            # 处理消息类型的数据
                            if isinstance(data, dict) and data.get('type') == 'message':
                                message_data = data.get('data')
                                
                                # 处理字符串类型的数据
                                if isinstance(message_data, str):
                                    message_parts.append(message_data)
                                # 处理对象类型的数据
                                elif isinstance(message_data, dict):
                                    if message_data.get('type') == 'text':
                                        text_content = message_data.get('text', '')
                                        if text_content:
                                            message_parts.append(text_content)
                            # 处理事件类型的数据
                            elif isinstance(data, dict) and data.get('type') == 'event':
                                event_name = data.get('event')
                                if event_name == 'on_message_delta':
                                    event_data = data.get('data', {})
                                    if 'content' in event_data and event_data['content']:
                                        content = event_data['content']
                                        message_parts.append(content)
                                elif event_name == 'message':
                                    # 处理直接的消息类型
                                    chunk_data = data.get('data')
                                    if chunk_data:
                                        if isinstance(chunk_data, str):
                                            message_parts.append(chunk_data)
                                            logger.info(f"添加字符串内容: {chunk_data}")
                                        elif isinstance(chunk_data, dict):
                                            if chunk_data.get('type') == 'text':
                                                text_content = chunk_data.get('text', '')
                                                if text_content:
                                                    message_parts.append(text_content)
                                                    logger.info(f"添加文本内容: {text_content}")
                        else:
                            # 尝试直接处理chunk
                            if hasattr(chunk, 'content'):
                                content = chunk.content
                                if isinstance(content, str):
                                    message_parts.append(content)
                            elif isinstance(chunk, str):
                                message_parts.append(chunk)
                    except Exception as chunk_error:
                        logger.warning(f"处理chunk时出错: {chunk_error}")
                        continue
                
                # 合并所有响应部分
                expert_response = ''.join(message_parts)
                logger.info(f"专家响应获取完成，处理了 {chunk_count} 个chunks")
                
            except Exception as api_error:
                logger.error(f"XpertAI流式API调用失败: {api_error}")
                expert_response = f"专家响应获取失败: {str(api_error)}"
            
            # 解析专家返回的JSON结果
            logger.info(f"专家最终响应: {expert_response}")
            
            try:
                import json
                import re
                
                # 尝试清理响应数据
                cleaned_response = expert_response.strip()
                if not cleaned_response:
                    logger.warning("专家返回空响应")
                    return {
                        'expert_response': expert_response,
                        'matched_placeholders': [],
                        'matched_templates': [],
                        'total_placeholders': 0,
                        'total_templates': 0,
                        'raw_analysis': expert_response
                    }
                
                # 处理被包装在代码块中的JSON - 改进正则表达式，支持多行匹配
                json_content = None
                
                # 首先尝试匹配 ```json ... ``` 格式（支持多行）
                json_match = re.search(r'```json\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1).strip()
                    logger.info("从 ```json 代码块中提取JSON")
                else:
                    # 尝试匹配 ``` ... ``` 格式（没有json标记）
                    json_match = re.search(r'```\s*\n(.*?)\n```', cleaned_response, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(1).strip()
                        logger.info("从 ``` 代码块中提取JSON")
                    else:
                        # 尝试直接查找JSON对象（以 { 开头，以 } 结尾）
                        json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                        if json_match:
                            json_content = json_match.group(0).strip()
                            logger.info("从文本中直接提取JSON对象")
                
                if not json_content:
                    logger.warning("未能从响应中提取JSON内容")
                    raise json.JSONDecodeError("未找到JSON内容", cleaned_response, 0)
                
                # 尝试解析JSON
                logger.info(f"准备解析JSON，长度: {len(json_content)}")
                analysis_result = json.loads(json_content)
                logger.info(f"JSON解析成功，包含键: {list(analysis_result.keys())}")
                
                # 处理解析结果，匹配占位符
                matched_placeholders = []
                matched_templates = []
                
                if 'analysis' in analysis_result:
                    logger.info(f"找到 analysis 字段，包含 {len(analysis_result['analysis'])} 个模板")
                    for template_key, template_data in analysis_result['analysis'].items():
                        logger.info(f"处理模板键: {template_key}, 数据: {template_data}")
                        # 尝试通过模板ID或模板名称匹配
                        template_name = None
                        template_id = None
                        
                        # 首先尝试通过模板ID匹配
                        for t in data.get('templates', []):
                            if str(t['template_id']) == str(template_key):
                                template_name = t['template_name']
                                template_id = t['template_id']
                                logger.info(f"通过模板ID匹配: {template_id} -> {template_name}")
                                break
                        
                        # 如果通过ID没找到，尝试通过模板名称匹配
                        if not template_name:
                            for t in data.get('templates', []):
                                if t['template_name'] == template_key:
                                    template_name = t['template_name']
                                    template_id = t['template_id']
                                    logger.info(f"通过模板名称匹配: {template_key} -> {template_id}")
                                    break
                        
                        # 如果都没找到，使用原始键作为模板名称
                        if not template_name:
                            template_name = template_key
                            template_id = template_key
                            logger.info(f"使用原始键作为模板: {template_key}")
                        
                        # 提取占位符
                        placeholders = template_data.get('placeholders', {})
                        logger.info(f"模板 {template_key} 包含 {len(placeholders)} 个占位符")
                        for placeholder, value in placeholders.items():
                            matched_placeholders.append({
                                'key': placeholder,
                                'value': value,
                                'template_name': template_name,
                                'template_id': template_id  # 添加template_id
                            })
                            logger.info(f"添加占位符: {placeholder} = {value}")
                        
                        matched_templates.append({
                            'template_id': template_id,
                            'template_name': template_name,
                            'matched_count': len(placeholders)
                        })
                else:
                    logger.warning(f"JSON中未找到 'analysis' 字段，可用键: {list(analysis_result.keys())}")
                
                result = {
                    'expert_response': expert_response,
                    'matched_placeholders': matched_placeholders,
                    'matched_templates': matched_templates,
                    'total_placeholders': len(matched_placeholders),
                    'total_templates': len(matched_templates)
                }
                
                logger.info(f"AI专家解析完成，匹配了 {len(matched_placeholders)} 个占位符")
                return result
                
            except json.JSONDecodeError as e:
                # 如果专家返回的不是JSON，尝试从文本中提取信息
                logger.warning(f"专家返回的不是标准JSON格式: {e}")
                logger.warning(f"响应内容: {expert_response[:200]}...")
                
                # 尝试从文本中提取占位符信息
                matched_placeholders = []
                matched_templates = []
                
                # 简单的文本解析，查找可能的占位符信息
                if "占位符" in expert_response or "placeholder" in expert_response.lower():
                    lines = expert_response.split('\n')
                    for line in lines:
                        if ":" in line and ("占位符" in line or "placeholder" in line.lower()):
                            parts = line.split(':')
                            if len(parts) >= 2:
                                matched_placeholders.append({
                                    'key': parts[0].strip(),
                                    'value': parts[1].strip(),
                                    'template_name': '未知模板'
                                })
                
                return {
                    'expert_response': expert_response,
                    'matched_placeholders': matched_placeholders,
                    'matched_templates': matched_templates,
                    'total_placeholders': len(matched_placeholders),
                    'total_templates': len(matched_templates),
                    'raw_analysis': expert_response,
                    'parse_error': str(e)
                }
                
        except Exception as e:
            logger.error(f"AI专家解析文档失败: {e}")
            raise
    
    async def _format_component_data(self, component: dict) -> str:
        """
        树形结构展示组件数据（多层可折叠，默认收起，加减号图标）
        异步版本，避免阻塞事件循环
        
        Args:
            component: 组件数据字典
            
        Returns:
            HTML 可折叠的树形结构组件数据
        """
        try:
            # 获取组件信息用于摘要
            component_data = component.get('data', {})
            component_type = component_data.get('type', 'unknown')
            component_title = component_data.get('title', '组件')
            component_status = component_data.get('status', '')
            
            # 生成唯一ID
            import uuid
            tree_id = f"tree_{uuid.uuid4().hex[:8]}"
            
            # 将组件数据转换为可折叠的树形HTML结构（异步，避免阻塞）
            tree_html = await self._dict_to_tree_html_async(component, node_id_prefix=tree_id, max_depth=15)
            
            # 返回完整的HTML结构（带CSS样式，使用data属性标记）
            result_text = f"""

---

<div class="tree-component-wrapper" data-component-html="true">
<div class="tree-container">
<div class="tree-root">
<span class="tree-title"><strong>{component_title}</strong></span>
<span class="tree-meta">类型: {component_type} | 状态: {component_status}</span>
</div>
{tree_html}
</div>
</div>

---

"""
            
            return result_text
                
        except Exception as e:
            logger.error(f"展示组件数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ""
    
    async def _dict_to_tree_html_async(self, data, node_id_prefix='node', depth=0, max_depth=15):
        """
        将字典/列表转换为可折叠的树形HTML结构（异步版本，避免阻塞）
        
        在递归过程中定期让出控制权，确保不会阻塞事件循环
        """
        # 每10层深度让出一次控制权
        if depth % 10 == 0:
            await asyncio.sleep(0)
        
        if depth > max_depth:
            return '<span class="tree-null">...</span>'
        
        if isinstance(data, dict):
            if not data:
                return '<span class="tree-type">{}</span>'
            
            html = '<div class="tree-node">\n'
            for idx, (key, value) in enumerate(data.items()):
                # 每处理10个键让出一次控制权
                if idx % 10 == 0 and idx > 0:
                    await asyncio.sleep(0)
                
                node_id = f"{node_id_prefix}_d{depth}_k{idx}"
                
                # 键名
                key_html = f'<span class="tree-key">"{key}"</span>'
                
                if isinstance(value, dict):
                    # 字典：可折叠
                    count = len(value)
                    html += f'<div><span class="tree-toggle" data-target="{node_id}">+</span>{key_html}: <span class="tree-type">{{...}} ({count} 项)</span>\n'
                    html += f'<div class="tree-content" id="{node_id}">\n'
                    html += await self._dict_to_tree_html_async(value, node_id, depth + 1, max_depth)
                    html += '</div></div>\n'
                elif isinstance(value, list):
                    # 列表：可折叠
                    count = len(value)
                    html += f'<div><span class="tree-toggle" data-target="{node_id}">+</span>{key_html}: <span class="tree-type">[...] ({count} 项)</span>\n'
                    html += f'<div class="tree-content" id="{node_id}">\n'
                    html += await self._dict_to_tree_html_async(value, node_id, depth + 1, max_depth)
                    html += '</div></div>\n'
                else:
                    # 简单值
                    value_html = self._format_value(value)
                    html += f'<div>{key_html}: {value_html}</div>\n'
            
            html += '</div>'
            return html
            
        elif isinstance(data, list):
            if not data:
                return '<span class="tree-type">[]</span>'
            
            html = '<div class="tree-node">\n'
            for idx, item in enumerate(data):
                # 每处理10个元素让出一次控制权
                if idx % 10 == 0 and idx > 0:
                    await asyncio.sleep(0)
                
                node_id = f"{node_id_prefix}_d{depth}_i{idx}"
                
                # 索引
                index_html = f'<span class="tree-index">[{idx}]</span>'
                
                if isinstance(item, dict):
                    # 字典：可折叠
                    count = len(item)
                    html += f'<div><span class="tree-toggle" data-target="{node_id}">+</span>{index_html}: <span class="tree-type">{{...}} ({count} 项)</span>\n'
                    html += f'<div class="tree-content" id="{node_id}">\n'
                    html += await self._dict_to_tree_html_async(item, node_id, depth + 1, max_depth)
                    html += '</div></div>\n'
                elif isinstance(item, list):
                    # 列表：可折叠
                    count = len(item)
                    html += f'<div><span class="tree-toggle" data-target="{node_id}">+</span>{index_html}: <span class="tree-type">[...] ({count} 项)</span>\n'
                    html += f'<div class="tree-content" id="{node_id}">\n'
                    html += await self._dict_to_tree_html_async(item, node_id, depth + 1, max_depth)
                    html += '</div></div>\n'
                else:
                    # 简单值
                    item_html = self._format_value(item)
                    html += f'<div>{index_html}: {item_html}</div>\n'
            
            html += '</div>'
            return html
            
        else:
            return self._format_value(data)
    
    def _dict_to_tree_html(self, data, node_id_prefix='node', depth=0, max_depth=15):
        """
        将字典/列表转换为可折叠的树形HTML结构（同步版本，已废弃）
        
        Args:
            data: 要转换的数据（dict/list/其他）
            node_id_prefix: 节点ID前缀
            depth: 当前深度
            max_depth: 最大深度
            
        Returns:
            HTML字符串
        """
        if depth > max_depth:
            return '<span class="tree-null">...</span>'
        
        if isinstance(data, dict):
            if not data:
                return '<span class="tree-type">{}</span>'
            
            html = '<div class="tree-node">\n'
            for idx, (key, value) in enumerate(data.items()):
                node_id = f"{node_id_prefix}_d{depth}_k{idx}"
                
                # 键名
                key_html = f'<span class="tree-key">"{key}"</span>'
                
                if isinstance(value, dict):
                    # 字典：可折叠
                    count = len(value)
                    html += f'<div><span class="tree-toggle" data-target="{node_id}">+</span>{key_html}: <span class="tree-type">{{...}} ({count} 项)</span>\n'
                    html += f'<div class="tree-content" id="{node_id}">\n'
                    html += self._dict_to_tree_html(value, node_id, depth + 1, max_depth)
                    html += '</div></div>\n'
                elif isinstance(value, list):
                    # 列表：可折叠
                    count = len(value)
                    html += f'<div><span class="tree-toggle" data-target="{node_id}">+</span>{key_html}: <span class="tree-type">[...] ({count} 项)</span>\n'
                    html += f'<div class="tree-content" id="{node_id}">\n'
                    html += self._dict_to_tree_html(value, node_id, depth + 1, max_depth)
                    html += '</div></div>\n'
                else:
                    # 简单值：直接显示
                    value_html = self._format_value(value)
                    html += f'<div>{key_html}: {value_html}</div>\n'
            
            html += '</div>'
            return html
            
        elif isinstance(data, list):
            if not data:
                return '<span class="tree-type">[]</span>'
            
            html = '<div class="tree-node">\n'
            for idx, item in enumerate(data):
                node_id = f"{node_id_prefix}_d{depth}_i{idx}"
                
                # 数组索引
                index_html = f'<span class="tree-index">[{idx}]</span>'
                
                if isinstance(item, dict):
                    # 字典：可折叠
                    count = len(item)
                    html += f'<div><span class="tree-toggle" data-target="{node_id}">+</span>{index_html}: <span class="tree-type">{{...}} ({count} 项)</span>\n'
                    html += f'<div class="tree-content" id="{node_id}">\n'
                    html += self._dict_to_tree_html(item, node_id, depth + 1, max_depth)
                    html += '</div></div>\n'
                elif isinstance(item, list):
                    # 列表：可折叠
                    count = len(item)
                    html += f'<div><span class="tree-toggle" data-target="{node_id}">+</span>{index_html}: <span class="tree-type">[...] ({count} 项)</span>\n'
                    html += f'<div class="tree-content" id="{node_id}">\n'
                    html += self._dict_to_tree_html(item, node_id, depth + 1, max_depth)
                    html += '</div></div>\n'
                else:
                    # 简单值：直接显示
                    item_html = self._format_value(item)
                    html += f'<div>{index_html}: {item_html}</div>\n'
            
            html += '</div>'
            return html
            
        else:
            return self._format_value(data)
    
    def _format_value(self, value):
        """
        格式化简单值的显示（使用CSS类，不需要转义）
        
        Args:
            value: 简单类型的值
            
        Returns:
            HTML字符串
        """
        if value is None:
            return '<span class="tree-null">null</span>'
        elif isinstance(value, bool):
            return f'<span class="tree-boolean">{str(value).lower()}</span>'
        elif isinstance(value, (int, float)):
            return f'<span class="tree-number">{value}</span>'
        elif isinstance(value, str):
            # 字符串值，截取过长内容，不转义（因为组件数据不需要转义）
            if len(value) > 300:
                return f'<span class="tree-string">"{value[:300]}..."</span>'
            else:
                return f'<span class="tree-string">"{value}"</span>'
        else:
            return f'<span class="tree-string">"{str(value)}"</span>'
    
    async def search_regulations(self, query: str, filters: Dict[str, Any] = None, stream_callback=None, conversation_id: str = None, user_id: int = None) -> Dict[str, Any]:
        """
        使用AI专家检索法规内容
        
        Args:
            query: 搜索查询内容
            filters: 筛选条件
            stream_callback: 流式回调函数，用于实时返回数据
            conversation_id: 对话ID，用于关联 Xpert 的 thread（同一对话使用同一个thread实现多轮对话）
            user_id: 用户ID，用于用户识别
            
        Returns:
            法规检索结果
        """
        try:
            logger.info(f"开始使用AI专家检索法规，查询: {query}")
            
            # 动态获取可用的专家（使用第一个可用专家）
            try:
                experts = await self.get_experts(limit=1)
                if not experts:
                    raise Exception("未找到可用的AI专家")
                expert_id = experts[0]['assistant_id']
                expert_name = experts[0].get('name', '未知专家')
                logger.info(f"使用专家: {expert_name} (ID: {expert_id})")
            except Exception as e:
                logger.error(f"获取专家列表失败: {e}")
                # 如果获取失败，尝试使用备用专家ID
                expert_id = "1e4a5666-8016-4576-857e-232c16990283"
                logger.warning(f"使用备用专家ID: {expert_id}")
            
            # 创建对话线程
            # 关键：使用 conversation_id 作为 Xpert 的 thread_id，实现多轮对话上下文
            xpert_thread_id = f"conv_{conversation_id}" if conversation_id else None
            
            # 准备线程元数据
            thread_metadata = {}
            if conversation_id:
                thread_metadata['conversation_id'] = conversation_id
            if user_id:
                thread_metadata['user_id'] = str(user_id)
            
            # 创建或复用线程（如果已存在则复用）
            thread = await self.create_thread(
                thread_id=xpert_thread_id,  # 同一对话使用同一个 thread
                metadata=thread_metadata if thread_metadata else None
            )
            thread_id = thread['thread_id']
            
            logger.info(f"Xpert 线程: {thread_id} (对话ID: {conversation_id})")
            
            
            # 准备专家输入参数 - 不要求返回结构化JSON，直接返回文本内容
            filters_text = ""
            if filters:
                filter_parts = []
                if filters.get('law_type'):
                    filter_parts.append(f"法规类型: {filters['law_type']}")
                if filters.get('effective_date'):
                    filter_parts.append(f"生效日期: {filters['effective_date']}")
                if filters.get('department'):
                    filter_parts.append(f"发布部门: {filters['department']}")
                if filter_parts:
                    filters_text = f"\n筛选条件: {', '.join(filter_parts)}"
            
            expert_input = {
                "input": f"""请帮我检索相关法规内容：

查询内容: {query}{filters_text}

请根据查询内容和筛选条件，检索相关的法规条文，并以清晰、易读的文本格式返回结果。
对于每条法规，请包含以下信息：
- 法规标题
- 法规内容/条文
- 条文编号（如果有）
- 法规类型
- 生效日期
- 发布部门
- 相关性说明

请确保返回的法规内容准确、相关，并按照相关性排序。"""
            }
            
            logger.info(f"发送给专家的参数: {expert_input}")
            
            # 调用专家进行法规检索
            max_wait_time = 120  # 增加超时时间到120秒
            start_time = asyncio.get_event_loop().time()
            
            stream = None  # 初始化stream变量
            try:
                # 使用流式API调用专家
                stream = self.client.runs.stream(
                    thread_id=thread_id,
                    assistant_id=expert_id,
                    input=expert_input
                )
                
                logger.info("开始流式获取专家响应...")
                expert_response = ""
                message_parts = []
                sent_components = set()  # 记录已发送的组件ID，避免重复
                
                # 已禁用文本去重以提升性能 - 创建一个虚假的集合对象
                # 所有的 "text_hash not in sent_texts" 检查都会返回 True
                # 所有的 "sent_texts.add()" 调用都会被忽略
                class _DummySet:
                    def __contains__(self, item): return False  # 永远返回False，让 "not in" 为True
                    def add(self, item): pass  # 忽略add操作
                    def __len__(self): return 0  # 返回0，避免日志错误
                sent_texts = _DummySet()
                
                # 按照正确的流式响应处理结构
                chunk_count = 0
                last_log_time = start_time
                timeout_occurred = False
                
                async for chunk in stream:
                    chunk_count += 1
                    current_time = asyncio.get_event_loop().time()
                    elapsed_time = current_time - start_time
                    
                    if elapsed_time > max_wait_time:
                        logger.warning(f"专家响应超时 ({elapsed_time:.1f}秒)，停止等待")
                        timeout_occurred = True
                        break
                    
                    # 每3秒打印一次进度
                    if current_time - last_log_time >= 3.0:
                        logger.info(f"专家响应处理中，已用时 {elapsed_time:.1f}秒")
                        last_log_time = current_time
                    
                    try:
                        chunk_content = None
                        event_name = None  # 初始化 event_name
                        
                        # 按照JavaScript代码的结构处理chunk
                        if hasattr(chunk, 'data') and chunk.data:
                            data = chunk.data
                            
                            # 处理消息类型的数据 - 立即发送
                            if isinstance(data, dict) and data.get('type') == 'message':
                                message_data = data.get('data')
                                
                                # 处理字符串类型的数据 - 立即发送（检查去重）
                                if isinstance(message_data, str):
                                    text_hash = hashlib.md5(message_data.encode()).hexdigest()
                                    
                                    if text_hash not in sent_texts:
                                        if stream_callback:
                                            await stream_callback(message_data)
                                            sent_texts.add(text_hash)
                                
                                # 处理对象类型的数据 - 立即发送
                                elif isinstance(message_data, dict):
                                    if message_data.get('type') == 'text':
                                        text_content = message_data.get('text', '')
                                        if text_content:
                                            text_hash = hashlib.md5(text_content.encode()).hexdigest()
                                            
                                            if text_hash not in sent_texts:
                                                if stream_callback:
                                                    await stream_callback(text_content)
                                                    sent_texts.add(text_hash)
                                    elif message_data.get('type') == 'component':
                                        # 组件数据 - 只处理 status 为 success 的组件
                                        component_unique_id = message_data.get('id', '')
                                        component_data = message_data.get('data', {})
                                        component_status = component_data.get('status', '')
                                        
                                        # 只处理 status 为 success 的组件
                                        if component_status == 'success' and component_unique_id and component_unique_id not in sent_components:
                                            component_text = await self._format_component_data(message_data)
                                            if component_text and stream_callback:
                                                await stream_callback(component_text)
                                                sent_components.add(component_unique_id)
                            # 处理事件类型的数据
                            elif isinstance(data, dict) and data.get('type') == 'event':
                                event_name = data.get('event')
                                if event_name == 'on_message_delta':
                                    event_data = data.get('data', {})
                                    if 'content' in event_data and event_data['content']:
                                        content = event_data['content']
                                        # 使用文本内容的MD5作为唯一标识进行去重
                                        text_hash = hashlib.md5(content.encode()).hexdigest()
                                        
                                        if text_hash not in sent_texts:
                                            logger.info(f"[流式] 收到 on_message_delta ({len(content)}字)")
                                            if stream_callback:
                                                await stream_callback(content)
                                                sent_texts.add(text_hash)
                                elif event_name == 'on_message_end':
                                    # on_message_end 事件只是表示流式传输结束，内容已经在之前的流式传输中发送过了
                                    # 不需要再处理其中的内容，避免重复发送
                                    logger.info(f"[流式] 收到 on_message_end 事件，跳过内容处理（内容已通过流式传输发送）")
                                elif event_name == 'message':
                                    # 处理直接的消息类型 - 立即发送（检查去重）
                                    chunk_data = data.get('data')
                                    if chunk_data:
                                        if isinstance(chunk_data, str):
                                            text_hash = hashlib.md5(chunk_data.encode()).hexdigest()
                                            
                                            if text_hash not in sent_texts:
                                                if stream_callback:
                                                    await stream_callback(chunk_data)
                                                    sent_texts.add(text_hash)
                                        elif isinstance(chunk_data, dict):
                                            if chunk_data.get('type') == 'text':
                                                text_content = chunk_data.get('text', '')
                                                if text_content:
                                                    text_hash = hashlib.md5(text_content.encode()).hexdigest()
                                                    
                                                    if text_hash not in sent_texts:
                                                        if stream_callback:
                                                            await stream_callback(text_content)
                                                            sent_texts.add(text_hash)
                        else:
                            # 尝试直接处理chunk - 立即发送（检查去重）
                            if hasattr(chunk, 'content'):
                                content = chunk.content
                                if isinstance(content, str):
                                    text_hash = hashlib.md5(content.encode()).hexdigest()
                                    
                                    if text_hash not in sent_texts:
                                        if stream_callback:
                                            await stream_callback(content)
                                            sent_texts.add(text_hash)
                            elif isinstance(chunk, str):
                                text_hash = hashlib.md5(chunk.encode()).hexdigest()
                                
                                if text_hash not in sent_texts:
                                    if stream_callback:
                                        await stream_callback(chunk)
                                        sent_texts.add(text_hash)
                            
                    except Exception as chunk_error:
                        logger.error(f"处理chunk时出错: {chunk_error}")
                        continue
                
                # 合并所有响应部分
                expert_response = ''.join(message_parts)
                logger.info(f"流式处理完成: 总chunks={chunk_count}, 有效parts={len(message_parts)}, 响应长度={len(expert_response)}")
                
            except Exception as api_error:
                import traceback
                logger.error(f"XpertAI流式API调用失败: {api_error}")
                logger.error(f"错误类型: {type(api_error).__name__}")
                logger.error(f"错误详情:\n{traceback.format_exc()}")
                
                # 如果是JSON解析错误，说明Xpert返回了非JSON数据
                if "unexpected character" in str(api_error) or "JSON" in str(api_error):
                    logger.error("⚠️ Xpert平台返回了非JSON格式的数据，这通常意味着:")
                    logger.error("  1. 专家ID不正确或已失效")
                    logger.error("  2. API权限不足")
                    logger.error("  3. Xpert平台服务异常")
                    logger.error(f"  当前使用的专家ID: {expert_id}")
                
                expert_response = f"专家响应获取失败: {str(api_error)}"
            
            finally:
                # 确保stream被正确关闭，避免资源泄漏
                if stream is not None:
                    try:
                        await stream.aclose()
                        logger.info("✅ Stream已正确关闭")
                    except Exception as close_error:
                        logger.warning(f"关闭stream时出错（可忽略）: {close_error}")
            
            # 直接返回文本响应，不再尝试解析JSON
            if not expert_response or expert_response.strip() == "":
                logger.warning("专家返回空响应")
                return {
                                'content': '',
                    'query': query,
                    'filters': filters,
                    'success': False,
                    'message': '专家返回空响应'
                }
            
            # 返回文本格式的响应
            logger.info(f"法规检索完成，返回长度: {len(expert_response)}")
            return {
                'content': expert_response,
                'query': query,
                'filters': filters,
                'success': True,
                'message': '法规检索完成'
            }
                
        except Exception as e:
            logger.error(f"法规检索失败: {e}")
            # 返回错误信息
            return {
                'content': f'法规检索失败: {str(e)}',
                'query': query,
                'filters': filters,
                'success': False,
                'message': f'法规检索失败: {str(e)}'
            }
    
    async def ask_expert_for_chat(self, question: str, category: str = "question", stream_callback=None, thread_id: str = None, user_id: int = None) -> Dict[str, Any]:
        """
        专门用于智能对话的专家调用方法
        
        Args:
            question: 用户问题
            category: 问题分类 (question/similar-case/regulation)
            stream_callback: 流式回调函数，用于实时返回数据
            thread_id: 线程ID，用于多轮对话上下文（可选，如果不提供则自动创建）
            user_id: 用户ID，用于用户识别
            
        Returns:
            专家回答结果
        """
        try:
            logger.info(f"开始智能对话专家调用，问题: {question}, 分类: {category}")
            
            # 动态获取可用的专家（使用第一个可用专家）
            try:
                experts = await self.get_experts(limit=1)
                if not experts:
                    raise Exception("未找到可用的AI专家")
                expert_id = experts[0]['assistant_id']
                expert_name = experts[0].get('name', '未知专家')
                logger.info(f"使用专家: {expert_name} (ID: {expert_id})")
            except Exception as e:
                logger.error(f"获取专家列表失败: {e}")
                # 如果获取失败，尝试使用备用专家ID
                expert_id = "1e4a5666-8016-4576-857e-232c16990283"
                logger.warning(f"使用备用专家ID: {expert_id}")
            
            # 创建或复用对话线程
            # 准备线程元数据
            thread_metadata = {}
            if user_id:
                thread_metadata['user_id'] = str(user_id)
            thread_metadata['category'] = category
            
            # 参考法规检索：传递 thread_id 参数以复用或创建线程
            thread = await self.create_thread(
                thread_id=thread_id,  # 传递 thread_id，如果为 None 则创建新的，否则复用
                metadata=thread_metadata if thread_metadata else None
            )
            thread_id = thread['thread_id']
            logger.info(f"Xpert 线程: {thread_id}")
            
            # 根据分类准备不同的提示词
            category_prompts = {
                "question": "请作为专业的法律助手，回答以下法律问题。请提供准确、详细、易懂的回答。",
                "similar-case": "请作为专业的法律助手，帮助查找类似的司法案例。请提供相关的案例信息、判决要点和适用法律。",
                "regulation": "请作为专业的法律助手，帮助检索相关法规条文。请提供准确的法规名称、条文内容和适用说明。"
            }
            
            system_prompt = category_prompts.get(category, category_prompts["question"])
            
            # 准备专家输入数据
            expert_input = {
                "input": f"{system_prompt}\n\n用户问题：{question}\n\n请提供专业、准确的回答。"
            }
            
            logger.info(f"发送给专家的参数: {expert_input}")
            
            # 调用专家进行智能对话
            max_wait_time = 120  # 超时时间120秒
            start_time = asyncio.get_event_loop().time()
            
            stream = None  # 初始化stream变量
            expert_response = ""
            message_parts = []  # 用于累积通过流式回调接收到的内容
            regulations_dict = {}  # 用于收集和去重法规文档信息（使用字典去重）
            
            try:
                # 使用流式API调用专家
                stream = self.client.runs.stream(
                    thread_id=thread_id,
                    assistant_id=expert_id,
                    input=expert_input
                )
                
                logger.info("开始流式获取专家响应...")
                
                # 已禁用文本去重以提升性能 - 创建一个虚假的集合对象
                class _DummySet:
                    def __contains__(self, item): return False  # 永远返回False，让 "not in" 为True
                    def add(self, item): pass  # 忽略add操作
                    def __len__(self): return 0  # 返回0，避免日志错误
                sent_texts = _DummySet()
                
                # 按照正确的流式响应处理结构
                chunk_count = 0
                last_log_time = start_time
                timeout_occurred = False
                logged_sample_data = False  # 用于记录是否已打印示例数据结构
                
                async for chunk in stream:
                    chunk_count += 1
                    current_time = asyncio.get_event_loop().time()
                    elapsed_time = current_time - start_time
                    
                    if elapsed_time > max_wait_time:
                        logger.warning(f"专家响应超时 ({elapsed_time:.1f}秒)，停止等待")
                        timeout_occurred = True
                        break
                    
                    # 每3秒打印一次进度
                    if current_time - last_log_time >= 3.0:
                        logger.info(f"专家响应处理中，已用时 {elapsed_time:.1f}秒")
                        last_log_time = current_time
                    
                    try:
                        chunk_content = None
                        event_name = None  # 初始化 event_name
                        
                        # 按照JavaScript代码的结构处理chunk
                        if hasattr(chunk, 'data') and chunk.data:
                            data = chunk.data
                            
                            # 暂时禁用打印数据结构（已知结构）
                            # if not logged_sample_data and isinstance(data, dict) and 'data' in data:
                            #     logged_sample_data = True
                            
                            # 处理消息类型的数据 - 立即发送
                            if isinstance(data, dict) and data.get('type') == 'message':
                                message_data = data.get('data')
                                
                                # 处理字符串类型的数据 - 立即发送（检查去重）
                                if isinstance(message_data, str):
                                    text_hash = hashlib.md5(message_data.encode()).hexdigest()
                                    
                                    if text_hash not in sent_texts:
                                        message_parts.append(message_data)
                                        if stream_callback:
                                            await stream_callback(message_data)
                                            sent_texts.add(text_hash)
                                
                                # 处理对象类型的数据 - 立即发送
                                elif isinstance(message_data, dict):
                                    if message_data.get('type') == 'text':
                                        text_content = message_data.get('text', '')
                                        if text_content:
                                            text_hash = hashlib.md5(text_content.encode()).hexdigest()
                                            
                                            if text_hash not in sent_texts:
                                                message_parts.append(text_content)
                                                if stream_callback:
                                                    await stream_callback(text_content)
                                                    sent_texts.add(text_hash)
                                    
                                    # 参考法规检索：处理组件类型的数据，从中提取法规文档信息
                                    elif message_data.get('type') == 'component':
                                        logger.info("📦 收到组件数据")
                                        
                                        # 打印完整的message_data结构（只打印一次）
                                        if not logged_sample_data:
                                            import json
                                            try:
                                                logger.info("📦 ===== 组件完整数据结构 =====")
                                                message_data_str = json.dumps(message_data, ensure_ascii=False, indent=2)
                                                if len(message_data_str) > 3000:
                                                    message_data_str = message_data_str[:3000] + "... (truncated)"
                                                logger.info(f"📦 message_data:\n{message_data_str}")
                                                logged_sample_data = True
                                            except Exception as e:
                                                logger.error(f"打印组件数据结构时出错: {e}")
                                        
                                        # 获取组件数据
                                        component_data = message_data.get('data', {})
                                        component_status = component_data.get('status', '')
                                        
                                        logger.info(f"📦 组件状态: {component_status}")
                                        
                                        # 只处理 status 为 success 的组件
                                        if component_status == 'success':
                                            # 从组件数据中提取法规文档列表
                                            component_data_array = component_data.get('data', [])
                                            
                                            if isinstance(component_data_array, list) and len(component_data_array) > 0:
                                                logger.info(f"📦 组件包含 {len(component_data_array)} 个数据项")
                                                
                                                for idx, item in enumerate(component_data_array):
                                                    if isinstance(item, dict):
                                                        # document 字段直接在 item 下面！
                                                        if 'document' in item:
                                                            doc = item.get('document', {})
                                                            if isinstance(doc, dict):
                                                                doc_name = doc.get('name', '')
                                                                doc_url = doc.get('fileUrl', '')
                                                                
                                                                if doc_name and doc_url:
                                                                    # 使用文档名称作为key去重
                                                                    regulations_dict[doc_name] = {
                                                                        'name': doc_name,
                                                                        'fileUrl': doc_url
                                                                    }
                                                                    logger.info(f"✅ 从组件中提取到法规文档[{idx}]: {doc_name}")
                                                                else:
                                                                    logger.info(f"⚠️ 组件文档[{idx}]缺少name或fileUrl: name={doc_name}, url={doc_url}")
                                                            else:
                                                                logger.info(f"⚠️ item[{idx}].document不是字典: {type(doc)}")
                                            else:
                                                logger.info("⚠️ 组件data不是数组或为空")
                                        else:
                                            logger.info(f"⚠️ 组件状态不是success: {component_status}")
                            
                            # 处理事件类型的数据
                            elif isinstance(data, dict) and data.get('type') == 'event':
                                event_name = data.get('event')
                                if event_name == 'on_message_delta':
                                    event_data = data.get('data', {})
                                    if 'content' in event_data and event_data['content']:
                                        content = event_data['content']
                                        # 使用文本内容的MD5作为唯一标识进行去重
                                        text_hash = hashlib.md5(content.encode()).hexdigest()
                                        
                                        if text_hash not in sent_texts:
                                            logger.info(f"[流式] 收到 on_message_delta ({len(content)}字)")
                                            message_parts.append(content)
                                            if stream_callback:
                                                await stream_callback(content)
                                                sent_texts.add(text_hash)
                                elif event_name == 'on_message_end':
                                    # on_message_end 事件只是表示流式传输结束，内容已经在之前的流式传输中发送过了
                                    # 不需要再处理其中的内容，避免重复发送
                                    logger.info(f"[流式] 收到 on_message_end 事件，跳过内容处理（内容已通过流式传输发送）")
                                elif event_name == 'message':
                                    # 处理直接的消息类型 - 立即发送（检查去重）
                                    chunk_data = data.get('data')
                                    if chunk_data:
                                        if isinstance(chunk_data, str):
                                            text_hash = hashlib.md5(chunk_data.encode()).hexdigest()
                                            
                                            if text_hash not in sent_texts:
                                                message_parts.append(chunk_data)
                                                if stream_callback:
                                                    await stream_callback(chunk_data)
                                                    sent_texts.add(text_hash)
                                        elif isinstance(chunk_data, dict):
                                            if chunk_data.get('type') == 'text':
                                                text_content = chunk_data.get('text', '')
                                                if text_content:
                                                    text_hash = hashlib.md5(text_content.encode()).hexdigest()
                                                    
                                                    if text_hash not in sent_texts:
                                                        message_parts.append(text_content)
                                                        if stream_callback:
                                                            await stream_callback(text_content)
                                                            sent_texts.add(text_hash)
                        else:
                            # 尝试直接处理chunk - 立即发送（检查去重）
                            if hasattr(chunk, 'content'):
                                content = chunk.content
                                if isinstance(content, str):
                                    text_hash = hashlib.md5(content.encode()).hexdigest()
                                    
                                    if text_hash not in sent_texts:
                                        message_parts.append(content)
                                        if stream_callback:
                                            await stream_callback(content)
                                            sent_texts.add(text_hash)
                            elif isinstance(chunk, str):
                                text_hash = hashlib.md5(chunk.encode()).hexdigest()
                                
                                if text_hash not in sent_texts:
                                    message_parts.append(chunk)
                                    if stream_callback:
                                        await stream_callback(chunk)
                                        sent_texts.add(text_hash)
                            
                    except Exception as chunk_error:
                        # 对于JSON解析错误，只记录警告，继续处理
                        if "JSON" in str(chunk_error) or "unexpected character" in str(chunk_error):
                            logger.warning(f"跳过无效的chunk数据（可能是SSE格式问题）: {chunk_error}")
                        else:
                            logger.warning(f"处理chunk时出错: {chunk_error}")
                        continue
                
                # 合并所有响应部分（从流式回调中累积的内容）
                expert_response = ''.join(message_parts)
                logger.info(f"流式处理完成: 总chunks={chunk_count}, 有效parts={len(message_parts)}, 响应长度={len(expert_response)}")
                
            except Exception as api_error:
                import traceback
                logger.error(f"XpertAI流式API调用失败: {api_error}")
                logger.error(f"错误类型: {type(api_error).__name__}")
                logger.error(f"错误详情:\n{traceback.format_exc()}")
                
                # 如果是JSON解析错误，说明Xpert返回了非JSON数据
                if "unexpected character" in str(api_error) or "JSON" in str(api_error):
                    logger.error("⚠️ Xpert平台返回了非JSON格式的数据，这通常意味着:")
                    logger.error("  1. 专家ID不正确或已失效")
                    logger.error("  2. API权限不足")
                    logger.error("  3. Xpert平台服务异常")
                    logger.error(f"  当前使用的专家ID: {expert_id}")
                
                # 参考法规检索：直接返回错误，不尝试备用方案
                # 如果流式处理失败时，message_parts中应该已经累积了部分内容
                expert_response = ''.join(message_parts)
                if not expert_response:
                    expert_response = f"专家响应获取失败: {str(api_error)}"
            
            finally:
                # 确保stream被正确关闭
                if stream is not None:
                    try:
                        await stream.aclose()
                        logger.info("✅ Stream已正确关闭")
                    except Exception as close_error:
                        logger.warning(f"关闭stream时出错（可忽略）: {close_error}")
            
            # 返回结果
            if not expert_response or expert_response.strip() == "":
                logger.warning("专家返回空响应")
                return {
                    'content': '',
                    'question': question,
                    'category': category,
                    'thread_id': thread_id,
                    'success': False,
                    'message': '专家返回空响应'
                }
            
            logger.info(f"智能对话完成，返回长度: {len(expert_response)}")
            
            # 使用从专家响应中提取的法规文档信息（已去重）
            related_regulations = list(regulations_dict.values())
            
            logger.info(f"从专家响应中提取到法规数量: {len(related_regulations)}条")
            if related_regulations:
                logger.info(f"提取到的法规列表: {[reg.get('name', 'Unknown') for reg in related_regulations]}")
            else:
                logger.warning("⚠️ 未从专家响应中提取到任何法规文档信息")
                logger.warning("请检查专家返回的数据结构是否包含 data.data[i].document 字段")
            
            return {
                'content': expert_response,
                'question': question,
                'category': category,
                'thread_id': thread_id,
                'success': True,
                'message': '智能对话完成',
                'related_regulations': related_regulations
            }
                
        except Exception as e:
            logger.error(f"智能对话失败: {e}")
            import traceback
            logger.error(f"错误详情:\n{traceback.format_exc()}")
            return {
                'content': f'智能对话失败: {str(e)}',
                'question': question,
                'category': category,
                'thread_id': thread_id,
                'success': False,
                'message': f'智能对话失败: {str(e)}'
            }
    
    def _get_mock_regulation_results(self, query: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取模拟法规检索结果"""
        mock_regulations = [
            {
                'id': '1',
                'title': '中华人民共和国民法典',
                'content': '第一条 为了保护民事主体的合法权益，调整民事关系，维护社会和经济秩序，适应中国特色社会主义发展要求，弘扬社会主义核心价值观，根据宪法，制定本法。',
                'article_number': '第一条',
                'law_type': '民法典',
                'effective_date': '2021-01-01',
                'department': '全国人民代表大会',
                'relevance_score': 0.95
            },
            {
                'id': '2',
                'title': '中华人民共和国合同法',
                'content': '第一条 为了保护合同当事人的合法权益，维护社会经济秩序，促进社会主义现代化建设，制定本法。',
                'article_number': '第一条',
                'law_type': '合同法',
                'effective_date': '1999-10-01',
                'department': '全国人民代表大会',
                'relevance_score': 0.88
            },
            {
                'id': '3',
                'title': '中华人民共和国刑法',
                'content': '第一条 为了惩罚犯罪，保护人民，根据宪法，结合我国同犯罪作斗争的具体经验及实际情况，制定本法。',
                'article_number': '第一条',
                'law_type': '刑法',
                'effective_date': '1997-10-01',
                'department': '全国人民代表大会',
                'relevance_score': 0.82
            }
        ]
        
        return {
            'regulations': mock_regulations,
            'total_count': len(mock_regulations),
            'search_summary': f'根据查询"{query}"找到{len(mock_regulations)}条相关法规',
            'expert_response': '使用模拟数据'
        }
    
    def generate_documents_from_placeholders(self, case_id: str, analysis_result: Dict[str, Any], templates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """基于占位符信息直接生成文书"""
        try:
            logger.info(f"开始为案例 {case_id} 生成文书")
            
            generated_documents = []
            
            # 从分析结果中提取占位符信息
            matched_placeholders = analysis_result.get('matched_placeholders', [])
            matched_templates = analysis_result.get('matched_templates', [])
            
            if not matched_placeholders:
                logger.warning("没有找到匹配的占位符信息")
                return {
                    'documents': [],
                    'total_documents': 0,
                    'message': '没有找到匹配的占位符信息'
                }
            
            # 按模板分组占位符
            placeholders_by_template = {}
            for placeholder in matched_placeholders:
                template_id = placeholder.get('template_id', 'unknown')
                if template_id not in placeholders_by_template:
                    placeholders_by_template[template_id] = []
                placeholders_by_template[template_id].append(placeholder)
            
            # 打印调试信息
            logger.info(f"可用的占位符模板ID: {list(placeholders_by_template.keys())}")
            logger.info(f"传入的模板: {templates}")
            
            # 为每个模板生成文档
            for template in templates:
                # 处理模板数据，支持字典和整数两种格式
                if isinstance(template, dict):
                    template_id = str(template.get('template_id', ''))
                    template_name = template.get('template_name', '未知模板')
                elif isinstance(template, (int, str)):
                    # 如果传入的是模板ID，需要从分析结果中获取模板信息
                    template_id = str(template)
                    template_name = f"模板{template_id}"
                else:
                    logger.warning(f"不支持的模板格式: {type(template)}")
                    continue
                
                logger.info(f"处理模板ID: {template_id}")
                template_placeholders = placeholders_by_template.get(template_id, [])
                
                if not template_placeholders:
                    logger.warning(f"模板 {template_name} 没有匹配的占位符")
                    continue
                
                # 生成文档内容
                document_content = self._generate_document_content(template, template_placeholders)
                
                generated_documents.append({
                    'document_name': f"{template_name}_{case_id}",
                    'document_type': 'word',
                    'content': document_content,
                    'template_id': template_id,
                    'template_name': template_name,
                    'generation_method': 'placeholder_fill',
                    'placeholders_count': len(template_placeholders)
                })
                
                logger.info(f"为模板 {template_name} 生成了文档，包含 {len(template_placeholders)} 个占位符")
                
                result = {
                    'documents': generated_documents,
                'total_documents': len(generated_documents),
                'message': f'成功生成 {len(generated_documents)} 个文档'
                }
                
            logger.info(f"文书生成完成，生成了 {len(generated_documents)} 个文档")
            return result
                
        except Exception as e:
            logger.error(f"文书生成失败: {e}")
            return {
                'documents': [],
                'total_documents': 0,
                'error': str(e),
                'message': f'文书生成失败: {str(e)}'
            }
    
    def _get_related_regulations(self, question: str, category: str) -> List[Dict[str, Any]]:
        """根据问题获取相关法规（目前使用模拟数据）"""
        # 定义一些常见法规的基本信息
        all_regulations = [
            {
                'id': 'labor_law',
                'name': '中华人民共和国劳动法',
                'level': '法律',
                'status': '现行有效',
                'publish_date': '2018-12-29',
                'effective_date': '2019-01-01',
                'authority': '全国人大常委会',
                'document_number': '中华人民共和国主席令第24号',
                'summary': '为了保护劳动者的合法权益，调整劳动关系，建立和维护适应社会主义市场经济的劳动制度，促进经济发展和社会进步，根据宪法，制定本法。',
                'keywords': ['劳动', '劳动合同', '工资', '工作时间', '劳动保护', '社会保险', '劳动争议', '开除', '赔偿', '经济补偿']
            },
            {
                'id': 'civil_code',
                'name': '中华人民共和国民法典',
                'level': '法律',
                'status': '现行有效',
                'publish_date': '2020-05-28',
                'effective_date': '2021-01-01',
                'authority': '全国人民代表大会',
                'document_number': '中华人民共和国主席令第45号',
                'summary': '为了保护民事主体的合法权益，调整民事关系，维护社会和经济秩序，适应中国特色社会主义发展要求，弘扬社会主义核心价值观，根据宪法，制定本法。',
                'keywords': ['民事', '合同', '财产', '侵权', '继承', '婚姻', '人格权', '物权']
            },
            {
                'id': 'labor_contract_law',
                'name': '中华人民共和国劳动合同法',
                'level': '法律',
                'status': '现行有效',
                'publish_date': '2012-12-28',
                'effective_date': '2013-07-01',
                'authority': '全国人大常委会',
                'document_number': '中华人民共和国主席令第73号',
                'summary': '为了完善劳动合同制度，明确劳动合同双方当事人的权利和义务，保护劳动者的合法权益，构建和发展和谐稳定的劳动关系，制定本法。',
                'keywords': ['劳动合同', '试用期', '服务期', '竞业限制', '解除', '终止', '经济补偿金', '赔偿金']
            }
        ]
        
        # 根据问题关键词匹配相关法规
        question_lower = question.lower()
        matched_regulations = []
        
        for regulation in all_regulations:
            # 检查问题是否包含法规的关键词
            if any(keyword in question for keyword in regulation['keywords']):
                matched_regulations.append(regulation)
        
        # 如果没有匹配到，返回劳动法作为默认
        if not matched_regulations:
            matched_regulations = [all_regulations[0]]
        
        # 最多返回3个相关法规
        return matched_regulations[:3]
    
    def _generate_document_content(self, template: Any, placeholders: List[Dict[str, Any]]) -> str:
        """生成文档内容"""
        try:
            # 这里可以根据实际需求实现文档生成逻辑
            # 目前返回一个简单的文本格式
            
            # 处理模板名称
            if isinstance(template, dict):
                template_name = template.get('template_name', '未知模板')
            else:
                template_name = f"模板{template}"
            
            content_lines = [
                f"# {template_name}",
                "",
                "基于以下占位符信息生成：",
                ""
            ]
            
            for placeholder in placeholders:
                key = placeholder.get('key', '')
                value = placeholder.get('value', '')
                content_lines.append(f"**{key}**: {value}")
                content_lines.append("")
            
            return "\n".join(content_lines)
                
        except Exception as e:
            logger.error(f"生成文档内容失败: {e}")
            return f"文档生成失败: {str(e)}"


def print_experts_list(experts: List[Dict[str, Any]]):
    """
    打印数字专家列表
    
    Args:
        experts: 专家列表
    """
    if not experts:
        print("未找到任何数字专家")
        return
    
    print(f"\n=== 数字专家列表 (共 {len(experts)} 个) ===")
    print("-" * 80)
    
    for i, expert in enumerate(experts, 1):
        print(f"\n{i}. 专家信息:")
        print(f"   ID: {expert.get('assistant_id', 'N/A')}")
        print(f"   名称: {expert.get('name', 'N/A')}")
        print(f"   描述: {expert.get('description', 'N/A')}")
        print(f"   模型: {expert.get('model', 'N/A')}")
        print(f"   创建时间: {expert.get('created_at', 'N/A')}")
        
        if expert.get('metadata'):
            print(f"   元数据: {expert.get('metadata')}")
        
        print("-" * 40)


async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 初始化客户端（使用配置文件中的API key）
    try:
        client = XpertAIClient()
        
        # 测试连接
        if await client.test_connection():
            print("✅ XpertAI平台连接成功!")
            
            # 获取并打印专家列表
            experts = await client.get_experts(limit=20)
            print_experts_list(experts)
        else:
            print("❌ XpertAI平台连接失败!")
            
    except Exception as e:
        print(f"❌ 初始化失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())



