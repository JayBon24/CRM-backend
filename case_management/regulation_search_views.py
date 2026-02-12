"""
法规检索视图
"""
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import (
    SearchSuggestion, RegulationSearchHistory, RegulationSearchResult,
    RegulationConversation, RegulationMessage
)
from .xpert_integration import XpertAIClient
from .document_parser import parse_regulation_document
from django.db import models
from django.conf import settings
import json
import logging
import asyncio
import os

logger = logging.getLogger(__name__)


class RegulationSearchViewSet(ViewSet):
    """法规检索视图集"""
    permission_classes = []  # 允许匿名访问
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @action(detail=False, methods=['get'], url_path='suggestions')
    def get_suggestions(self, request):
        """获取搜索建议"""
        try:
            query = request.GET.get('query', '')
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 5))
            
            # 从数据库获取搜索建议
            suggestions_query = SearchSuggestion.objects.filter(is_active=True)
            
            if query:
                # 如果有查询关键词，优先匹配包含关键词的建议
                suggestions_query = suggestions_query.filter(
                    models.Q(question__icontains=query) | 
                    models.Q(keywords__icontains=query)
                ).order_by('sort_order', 'id')
            else:
                # 如果没有查询关键词，按排序获取
                suggestions_query = suggestions_query.order_by('sort_order', 'id')
            
            # 分页处理
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            suggestions = suggestions_query[start_index:end_index]
            
            # 转换为列表
            suggestions_list = [suggestion.question for suggestion in suggestions]
            
            # 检查是否还有更多数据
            has_more = suggestions_query.count() > end_index
            
            logger.info(f"获取搜索建议: {query} -> 第{page}页, {len(suggestions_list)}条建议")
            
            return Response({
                'code': 2000,
                'msg': '获取搜索建议成功',
                'data': {
                    'suggestions': suggestions_list,
                    'has_more': has_more,
                    'current_page': page,
                    'total_count': suggestions_query.count()
                }
            })
            
        except Exception as e:
            logger.error(f"获取搜索建议失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'获取搜索建议失败: {str(e)}',
                'data': []
            })
    
    @action(detail=False, methods=['post'], url_path='regulations')
    def search_regulations(self, request):
        """搜索法规"""
        import time
        start_time = time.time()
        
        try:
            data = request.data
            query = data.get('query', '')
            filters = data.get('filters', {})
            config = data.get('config', {})
            
            if not query:
                return Response({
                    'code': 4000,
                    'msg': '搜索关键词不能为空',
                    'data': []
                })
            
            # 调用xpert平台进行法规检索
            try:
                # 初始化XpertAI客户端
                xpert_client = XpertAIClient(
                    api_key=os.getenv("XPERTAI_API_KEY", "")
                )
                
                # 异步调用法规检索
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                search_result = loop.run_until_complete(
                    xpert_client.search_regulations(query, filters)
                )
                loop.close()
                
                # 处理专家返回的结果
                if search_result and search_result.get('regulations'):
                    regulations = search_result.get('regulations', [])
                    total = search_result.get('total_count', len(regulations))
                    
                    # 转换数据格式以匹配前端期望的结构
                    results = []
                    for reg in regulations:
                        results.append({
                            'id': reg.get('id', ''),
                            'title': reg.get('title', ''),
                            'type': reg.get('law_type', ''),
                            'summary': reg.get('content', ''),
                            'date': reg.get('effective_date', ''),
                            'authority': reg.get('department', ''),
                            'lawNumber': reg.get('article_number', ''),
                            'relevance': reg.get('relevance_score', 0.0),
                            'tags': [reg.get('law_type', '')] if reg.get('law_type') else []
                        })
                    
                    logger.info(f"Xpert平台法规检索成功: {query} -> {total}条结果")
                else:
                    # 如果xpert平台调用失败，使用模拟数据作为备选
                    logger.warning(f"Xpert平台调用失败，使用模拟数据: {search_result}")
                    results = self._get_mock_results()
                    total = len(results)
                    
            except Exception as xpert_error:
                # 如果xpert平台调用异常，使用模拟数据作为备选
                logger.error(f"Xpert平台调用异常，使用模拟数据: {str(xpert_error)}")
                results = self._get_mock_results()
                total = len(results)
            
            # 计算搜索耗时
            end_time = time.time()
            search_time = end_time - start_time
            
            # 保存搜索历史和搜索结果
            try:
                # 获取用户信息
                user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None
                
                # 如果用户未登录，使用默认值0
                if user_id is None:
                    user_id = 0
                
                # 获取客户端信息
                ip_address = self.get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # 创建搜索历史记录
                search_history = RegulationSearchHistory.objects.create(
                    user_id=user_id,
                    search_query=query,
                    search_filters=filters,
                    search_results_count=total,
                    search_time=search_time,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    search_type='regulation'
                )
                
                # 保存搜索结果
                if results and len(results) > 0:
                    for index, result in enumerate(results):
                        RegulationSearchResult.objects.create(
                            search_history=search_history,
                            title=result.get('title', ''),
                            content=result.get('summary', ''),
                            article_number=result.get('lawNumber', ''),
                            law_type=result.get('type', ''),
                            effective_date=result.get('date', ''),
                            department=result.get('authority', ''),
                            relevance_score=result.get('relevance', 0.0),
                            sort_order=index
                        )
                
                logger.info(f"已保存搜索历史和结果: {query} -> 用户ID: {user_id}, 结果数: {total}, 耗时: {search_time:.2f}秒")
                
            except Exception as history_error:
                logger.error(f"保存搜索历史和结果失败: {str(history_error)}")
                # 不影响主要搜索功能，继续执行
            
            logger.info(f"搜索法规: {query} -> {total}条结果")
            
            return Response({
                'code': 2000,
                'msg': '法规搜索成功',
                'data': {
                    'results': results,
                    'total': total,
                    'query': query,
                    'filters': filters,
                    'config': config
                }
            })
            
        except Exception as e:
            logger.error(f"搜索法规失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'搜索法规失败: {str(e)}',
                'data': []
            })
    
    @action(detail=False, methods=['post'], url_path='regulations-stream')
    def search_regulations_stream(self, request):
        """流式搜索法规"""
        import time
        start_time = time.time()
        
        try:
            data = request.data
            query = data.get('query', '')
            filters = data.get('filters', {})
            conversation_id = data.get('conversation_id')  # 获取对话ID
            
            # 获取用户ID
            user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None
            
            if not query:
                # 返回错误的SSE消息
                def error_stream():
                    yield f"data: {json.dumps({'error': '搜索关键词不能为空', 'done': True}, ensure_ascii=False)}\n\n"
                
                response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
                response['Cache-Control'] = 'no-cache'
                response['X-Accel-Buffering'] = 'no'
                return response
            
            # 定义流式生成器
            def regulation_stream():
                # 捕获外部作用域的变量到闭包中
                _query = query
                _filters = filters
                _conversation_id = conversation_id
                _user_id = user_id
                _request = request  # 捕获 request 对象
                
                try:
                    # 初始化XpertAI客户端
                    xpert_client = XpertAIClient(
                        api_key=os.getenv("XPERTAI_API_KEY", "")
                    )
                    
                    # 用于存储流式数据的列表
                    stream_data = []
                    
                    # 定义异步流式回调函数
                    async def stream_callback(chunk):
                        stream_data.append(chunk)
                    
                    # 异步调用法规检索
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # 创建一个队列用于线程间通信
                    import queue
                    message_queue = queue.Queue()
                    
                    # 重新定义回调函数，将数据放入队列
                    async def queue_callback(chunk):
                        message_queue.put(chunk)
                    
                    # 在后台线程中运行异步任务
                    import threading
                    search_complete = threading.Event()
                    search_result = [None]
                    search_error = [None]
                    
                    def run_search():
                        try:
                            result = loop.run_until_complete(
                                xpert_client.search_regulations(
                                    _query, 
                                    _filters, 
                                    queue_callback,
                                    conversation_id=_conversation_id,  # 传递对话ID，用于 Xpert thread
                                    user_id=_user_id  # 传递用户ID
                                )
                            )
                            search_result[0] = result
                        except Exception as e:
                            search_error[0] = e
                            logger.error(f"流式搜索法规失败: {str(e)}")
                        finally:
                            search_complete.set()
                            message_queue.put(None)  # 发送结束信号
                            loop.close()
                    
                    search_thread = threading.Thread(target=run_search)
                    search_thread.start()
                    
                    # 从队列中读取并发送消息
                    chunk_number = 0
                    while True:
                        try:
                            # 等待消息，超时时间为0.5秒(缩短以提高响应速度)
                            chunk = message_queue.get(timeout=0.5)
                            
                            if chunk is None:
                                # 结束信号
                                logger.info("收到结束信号，停止流式传输")
                                break
                            
                            # 发送数据块
                            chunk_number += 1
                            event_data = {
                                'type': 'chunk',
                                'content': chunk,
                                'done': False
                            }
                            
                            # 立即发送数据
                            data_line = f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                            yield data_line
                            
                        except queue.Empty:
                            # 超时，发送心跳保持连接
                            yield f": heartbeat\n\n"
                            continue
                    
                    # 等待搜索完成
                    search_thread.join()
                    
                    # 计算搜索耗时
                    end_time = time.time()
                    search_time = end_time - start_time
                    
                    # 发送完成消息
                    if search_error[0]:
                        final_data = {
                            'type': 'error',
                            'message': str(search_error[0]),
                            'done': True
                        }
                    else:
                        result = search_result[0]
                        final_data = {
                            'type': 'complete',
                            'query': _query,
                            'filters': _filters,
                            'success': result.get('success', False) if result else False,
                            'message': result.get('message', '') if result else '',
                            'search_time': search_time,
                            'done': True
                        }
                    
                    yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                    
                    # 保存搜索历史
                    try:
                        history_user_id = getattr(_request.user, 'id', None) if hasattr(_request, 'user') and _request.user.is_authenticated else 0
                        ip_address = self.get_client_ip(_request)
                        user_agent = _request.META.get('HTTP_USER_AGENT', '')
                        
                        # 创建搜索历史记录
                        RegulationSearchHistory.objects.create(
                            user_id=history_user_id,
                            search_query=_query,
                            search_filters=_filters,
                            search_results_count=1 if result and result.get('success') else 0,
                            search_time=search_time,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            search_type='regulation_stream'
                        )
                        logger.info(f"已保存流式搜索历史: {_query} -> 用户ID: {history_user_id}, 耗时: {search_time:.2f}秒")
                    except Exception as history_error:
                        logger.error(f"保存搜索历史失败: {str(history_error)}")
                    
                except Exception as e:
                    logger.error(f"流式搜索法规异常: {str(e)}")
                    error_data = {
                        'type': 'error',
                        'message': f'搜索失败: {str(e)}',
                        'done': True
                    }
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            # 返回流式响应
            response = StreamingHttpResponse(regulation_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
            
        except Exception as e:
            logger.error(f"流式搜索法规失败: {str(e)}")
            
            def error_stream():
                error_data = {
                    'type': 'error',
                    'message': f'搜索失败: {str(e)}',
                    'done': True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
    
    def _get_mock_results(self):
        """获取模拟法规搜索结果"""
        return [
            {
                'id': 1,
                'title': '中华人民共和国道路交通安全法',
                'type': '法律',
                'summary': '为了维护道路交通秩序，预防和减少交通事故，保护人身安全，保护公民、法人和其他组织的财产安全及其他合法权益，提高通行效率，制定本法。',
                'date': '2021-04-29',
                'authority': '全国人大常委会',
                'lawNumber': '中华人民共和国主席令第81号',
                'relevance': 0.92,
                'tags': ['道路交通安全', '交通管理', '法律责任']
            },
            {
                'id': 2,
                'title': '最高人民法院关于审理道路交通事故损害赔偿案件适用法律若干问题的解释',
                'type': '司法解释',
                'summary': '为正确审理道路交通事故损害赔偿案件，根据《中华人民共和国民法典》《中华人民共和国道路交通安全法》《中华人民共和国保险法》《中华人民共和国民事诉讼法》等法律的规定，结合审判实践，制定本解释。',
                'date': '2020-12-29',
                'authority': '最高人民法院',
                'lawNumber': '法释[2020]17号',
                'relevance': 0.89,
                'tags': ['交通事故', '损害赔偿', '司法解释']
            },
            {
                'id': 3,
                'title': '机动车交通事故责任强制保险条例',
                'type': '行政法规',
                'summary': '为了保障机动车道路交通事故受害人依法得到赔偿，促进道路交通安全，根据《中华人民共和国道路交通安全法》、《中华人民共和国保险法》，制定本条例。',
                'date': '2019-03-02',
                'authority': '国务院',
                'lawNumber': '国务院令第462号',
                'relevance': 0.85,
                'tags': ['交强险', '交通事故', '保险赔偿']
            }
        ]
    
    @action(detail=False, methods=['get'], url_path='history')
    def get_search_history(self, request):
        """获取搜索历史"""
        try:
            # 获取用户ID
            user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None
            
            # 获取分页参数
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            
            # 查询搜索历史
            if user_id:
                # 如果用户已登录，只返回该用户的搜索历史
                history_query = RegulationSearchHistory.objects.filter(user_id=user_id)
            else:
                # 如果用户未登录，返回匿名用户的搜索历史（user_id=0或null）
                history_query = RegulationSearchHistory.objects.filter(
                    models.Q(user_id=0) | models.Q(user_id__isnull=True)
                )
            
            # 分页处理
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            histories = history_query[start_index:end_index]
            
            # 转换为列表
            history_list = []
            for history in histories:
                history_list.append({
                    'id': history.id,
                    'search_query': history.search_query,
                    'search_filters': history.search_filters,
                    'search_results_count': history.search_results_count,
                    'search_time': history.search_time,
                    'ip_address': str(history.ip_address) if history.ip_address else None,
                    'search_type': history.search_type,
                    'create_datetime': history.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if history.create_datetime else None
                })
            
            # 检查是否还有更多数据
            has_more = history_query.count() > end_index
            
            logger.info(f"获取搜索历史: 用户ID {user_id} -> 第{page}页, {len(history_list)}条记录")
            
            return Response({
                'code': 2000,
                'msg': '获取搜索历史成功',
                'data': {
                    'histories': history_list,
                    'has_more': has_more,
                    'current_page': page,
                    'total_count': history_query.count()
                }
            })
            
        except Exception as e:
            logger.error(f"获取搜索历史失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'获取搜索历史失败: {str(e)}',
                'data': []
            })
    
    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['delete'], url_path='history/(?P<history_id>[^/.]+)')
    def delete_history_item(self, request, history_id=None):
        """删除单个历史记录"""
        try:
            # 获取用户ID
            user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None
            
            # 查找历史记录
            try:
                history_item = RegulationSearchHistory.objects.get(id=history_id)
            except RegulationSearchHistory.DoesNotExist:
                return Response({
                    'code': 4000,
                    'msg': '历史记录不存在',
                    'data': []
                })
            
            # 检查权限：只有记录的所有者或管理员可以删除
            if user_id and history_item.user_id != user_id:
                return Response({
                    'code': 4003,
                    'msg': '无权限删除此历史记录',
                    'data': []
                })
            
            # 删除历史记录
            history_item.delete()
            
            logger.info(f"删除历史记录成功: ID {history_id}, 用户ID {user_id}")
            
            return Response({
                'code': 2000,
                'msg': '删除历史记录成功',
                'data': []
            })
            
        except Exception as e:
            logger.error(f"删除历史记录失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'删除历史记录失败: {str(e)}',
                'data': []
            })
    
    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['delete'], url_path='clear-history')
    def clear_all_history(self, request):
        """清空所有历史记录"""
        try:
            # 获取用户ID
            user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None
            
            # 删除所有历史记录
            if user_id:
                # 如果用户已登录，只删除该用户的历史记录
                deleted_count = RegulationSearchHistory.objects.filter(user_id=user_id).count()
                RegulationSearchHistory.objects.filter(user_id=user_id).delete()
            else:
                # 如果用户未登录，删除所有匿名用户的历史记录（user_id=0或null）
                deleted_count = RegulationSearchHistory.objects.filter(
                    models.Q(user_id=0) | models.Q(user_id__isnull=True)
                ).count()
                RegulationSearchHistory.objects.filter(
                    models.Q(user_id=0) | models.Q(user_id__isnull=True)
                ).delete()
            
            logger.info(f"清空历史记录成功: 用户ID {user_id}, 删除数量 {deleted_count}")
            
            return Response({
                'code': 2000,
                'msg': f'已清空 {deleted_count} 条历史记录',
                'data': {
                    'deleted_count': deleted_count
                }
            })
            
        except Exception as e:
            logger.error(f"清空历史记录失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'清空历史记录失败: {str(e)}',
                'data': []
            })
    
    @action(detail=False, methods=['post'], url_path='export')
    def export_results(self, request):
        """导出搜索结果"""
        try:
            data = request.data
            results = data.get('results', [])
            query = data.get('query', '')
            search_type = data.get('type', '')
            
            if not results:
                return Response({
                    'code': 4000,
                    'msg': '没有搜索结果可导出',
                    'data': None
                })
            
            # 构建导出数据
            export_data = {
                'query': query,
                'type': search_type,
                'timestamp': data.get('timestamp', ''),
                'total': len(results),
                'results': results
            }
            
            logger.info(f"导出搜索结果: {query} -> {len(results)}条结果")
            
            return Response({
                'code': 2000,
                'msg': '导出成功',
                'data': export_data
            })
            
        except Exception as e:
            logger.error(f"导出搜索结果失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'导出搜索结果失败: {str(e)}',
                'data': None
            })
    
    @action(detail=False, methods=['get'], url_path='results/(?P<history_id>[^/.]+)')
    def get_search_results_by_history(self, request, history_id=None):
        """根据历史记录ID获取搜索结果"""
        try:
            # 获取用户ID
            user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None
            
            # 查找历史记录
            try:
                history_item = RegulationSearchHistory.objects.get(id=history_id)
            except RegulationSearchHistory.DoesNotExist:
                return Response({
                    'code': 4000,
                    'msg': '历史记录不存在',
                    'data': []
                })
            
            # 检查权限：只有记录的所有者或管理员可以查看
            if user_id and history_item.user_id != user_id:
                return Response({
                    'code': 4003,
                    'msg': '无权限查看此历史记录',
                    'data': []
                })
            
            # 获取搜索结果
            results = RegulationSearchResult.objects.filter(search_history=history_item).order_by('sort_order', 'relevance_score')
            
            # 转换为前端格式
            results_list = []
            for result in results:
                results_list.append({
                    'id': result.id,
                    'title': result.title,
                    'type': result.law_type,
                    'summary': result.content,
                    'date': result.effective_date,
                    'authority': result.department,
                    'lawNumber': result.article_number,
                    'relevance': result.relevance_score,
                    'tags': [result.law_type] if result.law_type else []
                })
            
            logger.info(f"获取历史搜索结果: 历史ID {history_id} -> {len(results_list)}条结果")
            
            return Response({
                'code': 2000,
                'msg': '获取搜索结果成功',
                'data': {
                    'results': results_list,
                    'total': len(results_list),
                    'query': history_item.search_query,
                    'filters': history_item.search_filters,
                    'search_time': history_item.search_time,
                    'create_time': history_item.create_datetime.strftime('%Y-%m-%d %H:%M:%S') if history_item.create_datetime else None
                }
            })
            
        except Exception as e:
            logger.error(f"获取历史搜索结果失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'获取历史搜索结果失败: {str(e)}',
                'data': []
            })
    
    @action(detail=False, methods=['get'], url_path='stats')
    def get_search_stats(self, request):
        """获取搜索统计信息"""
        try:
            # TODO: 从数据库获取真实的搜索统计
            stats = {
                'totalSearches': 0,
                'totalResults': 0,
                'averageResponseTime': 0,
                'popularQueries': [],
                'searchTypes': {
                    'regulations': 0
                }
            }
            
            return Response({
                'code': 2000,
                'msg': '获取搜索统计成功',
                'data': stats
            })
            
        except Exception as e:
            logger.error(f"获取搜索统计失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'获取搜索统计失败: {str(e)}',
                'data': None
            })


class RegulationConversationViewSet(ViewSet):
    """法规检索对话管理视图集"""
    permission_classes = []  # 允许匿名访问
    
    def get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_user_id(self, request):
        """获取用户ID"""
        return getattr(request.user, 'id', 0) if hasattr(request, 'user') and request.user.is_authenticated else 0
    
    @action(detail=False, methods=['get'], url_path='list')
    def list_conversations(self, request):
        """获取对话列表"""
        try:
            user_id = self.get_user_id(request)
            
            # 获取对话列表
            conversations = RegulationConversation.objects.filter(
                user_id=user_id
            ).order_by('-is_pinned', '-last_message_time', '-create_datetime')[:50]
            
            from .serializers import RegulationConversationListSerializer
            serializer = RegulationConversationListSerializer(conversations, many=True)
            
            return Response({
                'code': 2000,
                'msg': '获取对话列表成功',
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"获取对话列表失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'获取对话列表失败: {str(e)}',
                'data': []
            })
    
    @action(detail=True, methods=['get'], url_path='messages')
    def get_conversation_messages(self, request, pk=None):
        """获取对话的所有消息"""
        try:
            conversation = RegulationConversation.objects.get(id=pk)
            
            from .serializers import RegulationMessageSerializer
            messages = conversation.messages.all()
            serializer = RegulationMessageSerializer(messages, many=True)
            
            return Response({
                'code': 2000,
                'msg': '获取消息成功',
                'data': serializer.data
            })
            
        except RegulationConversation.DoesNotExist:
            return Response({
                'code': 4004,
                'msg': '对话不存在',
                'data': []
            })
        except Exception as e:
            logger.error(f"获取消息失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'获取消息失败: {str(e)}',
                'data': []
            })
    
    @action(detail=False, methods=['post'], url_path='create')
    def create_conversation(self, request):
        """创建新对话"""
        try:
            user_id = self.get_user_id(request)
            ip_address = self.get_client_ip(request)
            title = request.data.get('title', '新对话')
            category = request.data.get('category', 'question')
            
            conversation = RegulationConversation.objects.create(
                user_id=user_id,
                title=title,
                category=category,
                ip_address=ip_address
            )
            
            from .serializers import RegulationConversationSerializer
            serializer = RegulationConversationSerializer(conversation)
            
            logger.info(f"创建新对话: {conversation.id}")
            
            return Response({
                'code': 2000,
                'msg': '创建对话成功',
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"创建对话失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'创建对话失败: {str(e)}',
                'data': None
            })
    
    @action(detail=True, methods=['post'], url_path='add-message')
    def add_message(self, request, pk=None):
        """添加消息到对话"""
        try:
            import time
            from django.utils import timezone
            
            conversation = RegulationConversation.objects.get(id=pk)
            
            role = request.data.get('role', 'user')
            content = request.data.get('content', '')
            query = request.data.get('query', '')
            filters = request.data.get('filters', {})
            response_time = request.data.get('response_time', 0)
            
            # 创建消息
            message = RegulationMessage.objects.create(
                conversation=conversation,
                role=role,
                content=content,
                query=query if role == 'user' else None,
                filters=filters if role == 'user' else None,
                response_time=response_time if role == 'assistant' else None
            )
            
            # 更新对话信息
            conversation.message_count = conversation.messages.count()
            conversation.last_message_time = timezone.now()
            
            # 如果是第一条用户消息，用它作为对话标题
            if role == 'user' and conversation.message_count <= 2:
                conversation.title = content[:50] + ('...' if len(content) > 50 else '')
            
            conversation.save()
            
            from .serializers import RegulationMessageSerializer
            serializer = RegulationMessageSerializer(message)
            
            return Response({
                'code': 2000,
                'msg': '添加消息成功',
                'data': serializer.data
            })
            
        except RegulationConversation.DoesNotExist:
            return Response({
                'code': 4004,
                'msg': '对话不存在',
                'data': None
            })
        except Exception as e:
            logger.error(f"添加消息失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'添加消息失败: {str(e)}',
                'data': None
            })
    
    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_conversation(self, request, pk=None):
        """删除对话"""
        try:
            conversation = RegulationConversation.objects.get(id=pk)
            conversation.delete()
            
            logger.info(f"删除对话: {pk}")
            
            return Response({
                'code': 2000,
                'msg': '删除对话成功',
                'data': None
            })
            
        except RegulationConversation.DoesNotExist:
            return Response({
                'code': 4004,
                'msg': '对话不存在',
                'data': None
            })
        except Exception as e:
            logger.error(f"删除对话失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'删除对话失败: {str(e)}',
                'data': None
            })
    
    @action(detail=False, methods=['delete'], url_path='clear-all')
    def clear_all_conversations(self, request):
        """清空所有对话"""
        try:
            user_id = self.get_user_id(request)
            
            deleted_count = RegulationConversation.objects.filter(user_id=user_id).delete()[0]
            
            logger.info(f"清空用户 {user_id} 的所有对话，共 {deleted_count} 条")
            
            return Response({
                'code': 2000,
                'msg': f'成功清空 {deleted_count} 条对话',
                'data': {'deleted_count': deleted_count}
            })
            
        except Exception as e:
            logger.error(f"清空对话失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'清空对话失败: {str(e)}',
                'data': None
            })
    
    @action(detail=True, methods=['put'], url_path='toggle-pin')
    def toggle_pin(self, request, pk=None):
        """切换对话置顶状态"""
        try:
            conversation = RegulationConversation.objects.get(id=pk)
            conversation.is_pinned = not conversation.is_pinned
            conversation.save()
            
            return Response({
                'code': 2000,
                'msg': '置顶状态已更新',
                'data': {'is_pinned': conversation.is_pinned}
            })
            
        except RegulationConversation.DoesNotExist:
            return Response({
                'code': 4004,
                'msg': '对话不存在',
                'data': None
            })
        except Exception as e:
            logger.error(f"切换置顶失败: {str(e)}")
            return Response({
                'code': 5000,
                'msg': f'切换置顶失败: {str(e)}',
                'data': None
            })
    
    @action(detail=True, methods=['post'], url_path='ask-expert')
    def ask_expert(self, request, pk=None):
        """使用Xpert平台专家进行智能对话（流式响应）"""
        import time
        start_time = time.time()
        
        try:
            from django.utils import timezone
            
            conversation = RegulationConversation.objects.get(id=pk)
            user_id = self.get_user_id(request)
            
            # 获取请求参数
            question = request.data.get('question', '')
            category = request.data.get('category', 'question')
            
            if not question:
                # 返回错误的SSE消息
                def error_stream():
                    yield f"data: {json.dumps({'error': '问题内容不能为空', 'done': True}, ensure_ascii=False)}\n\n"
                
                response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
                response['Cache-Control'] = 'no-cache'
                response['X-Accel-Buffering'] = 'no'
                return response
            
            # 保存用户消息
            user_message = RegulationMessage.objects.create(
                conversation=conversation,
                role='user',
                content=question,
                query=question
            )
            
            # 更新对话信息
            conversation.message_count = conversation.messages.count()
            conversation.last_message_time = timezone.now()
            
            # 如果是第一条用户消息，用它作为对话标题
            if conversation.message_count <= 2:
                conversation.title = question[:50] + ('...' if len(question) > 50 else '')
                conversation.category = category  # 保存分类信息
            
            conversation.save()
            
            # 定义流式生成器
            def expert_stream():
                # 捕获外部作用域的变量到闭包中
                _question = question
                _category = category
                _conversation = conversation
                _user_id = user_id
                _user_message = user_message
                _start_time = start_time
                
                try:
                    # 初始化Xpert客户端
                    xpert_client = XpertAIClient()
                    
                    # 使用对话ID作为thread_id，实现多轮对话上下文
                    thread_id = f"chat_{conversation.id}"
                    
                    # 创建一个队列用于线程间通信
                    import queue
                    message_queue = queue.Queue()
                    
                    # 定义异步流式回调函数，将数据放入队列
                    async def queue_callback(chunk):
                        message_queue.put(chunk)
                    
                    # 异步调用专家
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # 在后台线程中运行异步任务
                    import threading
                    expert_complete = threading.Event()
                    expert_result = [None]
                    expert_error = [None]
                    
                    def run_expert():
                        try:
                            result = loop.run_until_complete(
                                xpert_client.ask_expert_for_chat(
                                    question=_question,
                                    category=_category,
                                    thread_id=thread_id,
                                    user_id=_user_id,
                                    stream_callback=queue_callback
                                )
                            )
                            expert_result[0] = result
                        except Exception as e:
                            expert_error[0] = e
                            logger.error(f"调用Xpert专家失败: {str(e)}")
                            import traceback
                            logger.error(f"错误详情:\n{traceback.format_exc()}")
                        finally:
                            expert_complete.set()
                            message_queue.put(None)  # 发送结束信号
                            loop.close()
                    
                    expert_thread = threading.Thread(target=run_expert)
                    expert_thread.start()
                    
                    # 用于累积AI回复内容
                    ai_content_parts = []
                    
                    # 从队列中读取并发送消息
                    chunk_number = 0
                    while True:
                        try:
                            # 等待消息，超时时间为0.5秒
                            chunk = message_queue.get(timeout=0.5)
                            
                            if chunk is None:
                                # 结束信号
                                logger.info("收到结束信号，停止流式传输")
                                break
                            
                            # 累积内容
                            ai_content_parts.append(chunk)
                            
                            # 发送数据块
                            chunk_number += 1
                            event_data = {
                                'type': 'chunk',
                                'content': chunk,
                                'done': False
                            }
                            
                            # 立即发送数据
                            data_line = f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                            yield data_line
                            
                        except queue.Empty:
                            # 超时，发送心跳保持连接
                            yield f": heartbeat\n\n"
                            continue
                    
                    # 等待专家调用完成
                    expert_thread.join()
                    
                    # 计算响应时间
                    end_time = time.time()
                    response_time = end_time - _start_time
                    
                    # 合并所有AI回复内容
                    ai_content = ''.join(ai_content_parts)
                    
                    # 发送完成消息
                    if expert_error[0]:
                        error_content = f"抱歉，处理您的请求时出现了错误：{str(expert_error[0])}"
                        # 保存错误消息
                        error_message = RegulationMessage.objects.create(
                            conversation=_conversation,
                            role='assistant',
                            content=error_content
                        )
                        
                        final_data = {
                            'type': 'error',
                            'message': str(expert_error[0]),
                            'response_time': response_time,
                            'done': True
                        }
                    else:
                        result = expert_result[0]
                        if result and result.get('success'):
                            related_regulations = result.get('related_regulations', [])
                            logger.info(f"获取到相关法规: {len(related_regulations)}条")
                            if related_regulations:
                                logger.info(f"法规详情: {[reg.get('name') for reg in related_regulations]}")
                            
                            # 保存AI回复消息（包含相关法规）
                            ai_message = RegulationMessage.objects.create(
                                conversation=_conversation,
                                role='assistant',
                                content=ai_content,
                                response_time=response_time,
                                related_regulations=related_regulations  # 保存相关法规到数据库
                            )
                            
                            # 更新对话信息
                            _conversation.message_count = _conversation.messages.count()
                            _conversation.last_message_time = timezone.now()
                            _conversation.save()
                            
                            final_data = {
                                'type': 'complete',
                                'question': _question,
                                'category': _category,
                                'success': True,
                                'message': result.get('message', '智能对话完成'),
                                'response_time': response_time,
                                'thread_id': result.get('thread_id'),
                                'related_regulations': related_regulations,  # 添加相关法规
                                'done': True
                            }
                            
                            logger.info(f"智能对话完成: 对话ID={_conversation.id}, 用时={response_time:.2f}秒")
                        else:
                            # 保存错误消息
                            error_content = ai_content or result.get('content', '') if result else '抱歉，处理您的请求时出现了错误'
                            error_message = RegulationMessage.objects.create(
                                conversation=_conversation,
                                role='assistant',
                                content=error_content,
                                response_time=response_time
                            )
                            
                            final_data = {
                                'type': 'error',
                                'message': result.get('message', '智能对话失败') if result else '智能对话失败',
                                'response_time': response_time,
                                'done': True
                            }
                            
                            logger.error(f"智能对话失败: {result.get('message') if result else '未知错误'}")
                    
                    yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                    
                except Exception as e:
                    logger.error(f"流式智能对话异常: {str(e)}")
                    import traceback
                    logger.error(f"错误详情:\n{traceback.format_exc()}")
                    
                    # 保存错误消息
                    try:
                        error_content = f"抱歉，处理您的请求时出现了错误：{str(e)}"
                        error_message = RegulationMessage.objects.create(
                            conversation=conversation,
                            role='assistant',
                            content=error_content
                        )
                    except:
                        pass
                    
                    error_data = {
                        'type': 'error',
                        'message': f'智能对话失败: {str(e)}',
                        'done': True
                    }
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            # 返回流式响应
            response = StreamingHttpResponse(expert_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
            
        except RegulationConversation.DoesNotExist:
            def error_stream():
                error_data = {
                    'type': 'error',
                    'message': '对话不存在',
                    'done': True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
            
        except Exception as e:
            logger.error(f"智能对话失败: {str(e)}")
            import traceback
            logger.error(f"错误详情:\n{traceback.format_exc()}")
            
            def error_stream():
                error_data = {
                    'type': 'error',
                    'message': f'智能对话失败: {str(e)}',
                    'done': True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
    
    @action(detail=False, methods=['get'], url_path='regulation-detail')
    def get_regulation_detail(self, request):
        """获取法规详情（支持通过URL下载解析Word文档）"""
        try:
            regulation_name = request.query_params.get('name')
            file_url = request.query_params.get('fileUrl')
            
            if not regulation_name:
                return Response({
                    'code': 4000,
                    'msg': '缺少法规名称参数',
                    'data': None
                })
            
            if not file_url:
                return Response({
                    'code': 4000,
                    'msg': '缺少文档URL参数',
                    'data': None
                })
            
            logger.info(f"开始获取法规详情: {regulation_name}, URL: {file_url}")
            
            # 基本信息（从文件名提取）
            regulation_info = {
                'name': regulation_name,
                'fileUrl': file_url,
                'level': '法律',
                'status': '现行有效',
                'summary': ''
            }
            
            # 下载文档到临时文件
            import requests
            import tempfile
            
            try:
                logger.info(f"开始下载文档: {file_url}")
                response = requests.get(file_url, timeout=30)
                response.raise_for_status()
                
                # 创建临时文件保存下载的文档
                with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                    temp_file.write(response.content)
                    temp_file_path = temp_file.name
                
                logger.info(f"文档下载成功，保存到: {temp_file_path}")
                
                # 解析Word文档
                logger.info(f"开始解析文档...")
                parse_result = parse_regulation_document(temp_file_path)
                
                if parse_result.get('success'):
                    # 合并基本信息和解析结果
                    regulation_info['chapters'] = parse_result.get('chapters', [])
                    regulation_info['total_articles'] = parse_result.get('total_articles', 0)
                    regulation_info['title'] = parse_result.get('title', regulation_name)
                    logger.info(f"法规解析成功: {regulation_info['name']}, 共{regulation_info.get('total_articles', 0)}条")
                else:
                    logger.error(f"法规解析失败: {parse_result.get('error')}")
                    return Response({
                        'code': 5000,
                        'msg': f"法规解析失败: {parse_result.get('error')}",
                        'data': None
                    })
                
                # 删除临时文件
                try:
                    os.unlink(temp_file_path)
                    logger.info(f"临时文件已删除: {temp_file_path}")
                except Exception as del_error:
                    logger.warning(f"删除临时文件失败: {del_error}")
                
            except requests.RequestException as download_error:
                logger.error(f"下载文档失败: {download_error}")
                return Response({
                    'code': 5000,
                    'msg': f'下载文档失败: {str(download_error)}',
                    'data': None
                })
            
            return Response({
                'code': 2000,
                'msg': '获取法规详情成功',
                'data': regulation_info
            })
            
        except Exception as e:
            logger.error(f"获取法规详情失败: {str(e)}")
            import traceback
            logger.error(f"错误详情:\n{traceback.format_exc()}")
            return Response({
                'code': 5000,
                'msg': f'获取法规详情失败: {str(e)}',
                'data': None
            })
