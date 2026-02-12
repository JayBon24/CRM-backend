"""
WPS文档集成API视图
"""
import logging
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.request_util import get_request_user

from .utils.wps_service import WPSService
from .utils.wps_document_handler import WPSDocumentHandler
from .utils.wps_callback_handler import WPSCallbackHandler
from .models import CaseDocument

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wps_preview_config(request):
    """
    获取WPS预览配置
    
    POST /api/case/document/wps/preview-config/
    """
    try:
        user = get_request_user(request)
        document_id = request.data.get('documentId') or request.data.get('document_id')
        mode = request.data.get('mode', 'view')
        
        if not document_id:
            return ErrorResponse(msg="文档ID不能为空")
        
        # 生成配置
        wps_service = WPSService()
        config = wps_service.generate_edit_config(
            document_id=int(document_id),
            user_id=user.id,
            user_name=getattr(user, 'name', '') or getattr(user, 'username', ''),
            mode=mode
        )
        
        return DetailResponse(
            data={
                'documentId': document_id,
                'wpsConfig': config
            },
            msg="配置生成成功"
        )
        
    except Exception as e:
        logger.error(f"生成WPS预览配置失败: {str(e)}", exc_info=True)
        return ErrorResponse(msg=f"配置生成失败: {str(e)}")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wps_edit_config(request):
    """
    获取WPS编辑配置（旧版config方式，保留兼容）
    
    POST /api/case/document/wps/edit-config/
    """
    try:
        user = get_request_user(request)
        document_id = request.data.get('documentId') or request.data.get('document_id')
        mode = request.data.get('mode', 'edit')
        
        if not document_id:
            return ErrorResponse(msg="文档ID不能为空")
        
        # 检查文档是否存在
        try:
            document = CaseDocument.objects.get(id=document_id, is_deleted=False)
        except CaseDocument.DoesNotExist:
            return ErrorResponse(msg="文档不存在", code=404)
        
        # 检查权限
        handler = WPSDocumentHandler()
        if not handler.check_document_permission(document_id, user.id, 'read'):
            return ErrorResponse(msg="无权限访问此文档", code=403)
        
        if mode == 'edit' and not handler.check_document_permission(document_id, user.id, 'write'):
            return ErrorResponse(msg="无权限编辑此文档", code=403)
        
        # 生成配置
        wps_service = WPSService()
        config = wps_service.generate_edit_config(
            document_id=int(document_id),
            user_id=user.id,
            user_name=getattr(user, 'name', '') or getattr(user, 'username', ''),
            mode=mode
        )
        
        return DetailResponse(
            data={
                'documentId': document_id,
                'wpsConfig': config
            },
            msg="配置生成成功"
        )
        
    except Exception as e:
        logger.error(f"生成WPS编辑配置失败: {str(e)}", exc_info=True)
        return ErrorResponse(msg=f"配置生成失败: {str(e)}")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wps_init_config(request, documentId):
    """
    获取WPS初始化配置（init方式，官方推荐）
    
    POST /api/case/documents/{documentId}/wps/init-config/
    
    完全符合 WPS-init方式后端接口规范
    """
    try:
        import os
        from datetime import datetime, timedelta
        import jwt
        
        user = get_request_user(request)
        document_id = int(documentId)
        
        # 获取请求参数
        mode = request.data.get('mode', 'edit')  # "view" 或 "edit"
        user_id = request.data.get('userId', user.id)
        user_name = request.data.get('userName', getattr(user, 'name', '') or getattr(user, 'username', ''))
        
        # 检查文档是否存在
        try:
            document = CaseDocument.objects.get(id=document_id, is_deleted=False)
        except CaseDocument.DoesNotExist:
            return JsonResponse({
                'code': 40004,
                'message': 'file not exists'
            }, status=404)
        
        # 检查权限
        handler = WPSDocumentHandler()
        if not handler.check_document_permission(document_id, user.id, 'read'):
            return JsonResponse({
                'code': 40003,
                'message': 'permission denied'
            }, status=403)
        
        if mode == 'edit' and not handler.check_document_permission(document_id, user.id, 'write'):
            return JsonResponse({
                'code': 40003,
                'message': 'permission denied for edit'
            }, status=403)
        
        # 判断文件类型（officeType）
        file_ext = os.path.splitext(document.document_name or document.file_name or 'document.docx')[1].lower()
        if not file_ext and document.file_ext:
            file_ext = document.file_ext.lower()
        
        office_type_map = {
            '.doc': 'w', '.docx': 'w',
            '.xls': 's', '.xlsx': 's',
            '.ppt': 'p', '.pptx': 'p',
            '.pdf': 'pdf'
        }
        office_type = office_type_map.get(file_ext, 'w')  # 默认Word
        
        # 生成JWT Token（用于回调接口鉴权）
        wps_service = WPSService()
        token = wps_service.generate_token(
            document_id=document_id,
            user_id=user.id,
            expires_in=24 * 3600  # 24小时
        )
        
        # 生成回调服务的基础地址（endpoint）
        # WPS 会在 endpoint 后面加上接口路径，如 /v3/3rd/users
        from django.http import HttpRequest
        if isinstance(request, HttpRequest):
            scheme = request.scheme
            host = request.get_host()
        else:
            # 如果无法从request获取，使用默认值
            scheme = 'https' if not settings.DEBUG else 'http'
            host = request.META.get('HTTP_HOST', 'localhost:8000')
        
        endpoint = f"{scheme}://{host}/api/case"
        
        logger.info(
            f"生成WPS init配置: document_id={document_id}, user_id={user.id}, "
            f"mode={mode}, office_type={office_type}, endpoint={endpoint}"
        )
        
        return JsonResponse({
            'code': 0,
            'data': {
                'appId': wps_service.app_id,
                'fileId': str(document_id),
                'officeType': office_type,
                'token': token,
                'endpoint': endpoint  # 回调服务的基础地址
            }
        })
        
    except ValueError as e:
        logger.warning(f"WPS init配置生成失败（参数错误）: documentId={documentId}, error={str(e)}")
        return JsonResponse({
            'code': 40005,
            'message': f'invalid arguments: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.error(f"生成WPS init配置失败: documentId={documentId}, error={str(e)}", exc_info=True)
        return JsonResponse({
            'code': 50000,
            'message': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wps_get_file(request, document_id):
    """
    获取文档文件（用于WPS加载）
    
    GET /api/case/document/wps/file/<document_id>/
    """
    try:
        user = get_request_user(request)
        
        # 验证URL签名
        expires = request.GET.get('expires')
        signature = request.GET.get('signature')
        user_id = request.GET.get('user_id')
        
        if expires and signature and user_id:
            wps_service = WPSService()
            if not wps_service.verify_url_signature(
                document_id, int(user_id), int(expires), signature
            ):
                return HttpResponse("签名验证失败", status=403)
        
        # 获取文档文件
        handler = WPSDocumentHandler()
        return handler.get_document_file(document_id, user.id)
        
    except Exception as e:
        logger.error(
            f"获取WPS文档文件失败: document_id={document_id}, error={str(e)}",
            exc_info=True
        )
        return HttpResponse(f"获取文件失败: {str(e)}", status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wps_save_document(request, document_id):
    """
    保存WPS编辑后的文档
    
    POST /api/case/document/wps/save/<document_id>/
    """
    try:
        user = get_request_user(request)
        
        # 检查文件是否上传
        if 'file' not in request.FILES:
            return ErrorResponse(msg="未上传文件")
        
        uploaded_file = request.FILES['file']
        
        # 保存文档
        handler = WPSDocumentHandler()
        result = handler.save_document(document_id, uploaded_file, user.id)
        
        return DetailResponse(
            data=result,
            msg="保存成功"
        )
        
    except ValueError as e:
        logger.warning(f"保存WPS文档失败（参数错误）: document_id={document_id}, error={str(e)}")
        return ErrorResponse(msg=str(e), code=400)
    except PermissionError as e:
        logger.warning(f"保存WPS文档失败（权限不足）: document_id={document_id}, error={str(e)}")
        return ErrorResponse(msg=str(e), code=403)
    except Exception as e:
        logger.error(
            f"保存WPS文档失败: document_id={document_id}, error={str(e)}",
            exc_info=True
        )
        return ErrorResponse(msg=f"保存失败: {str(e)}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wps_download_document(request, document_id):
    """
    下载WPS文档
    
    GET /api/case/document/wps/download/<document_id>/
    """
    try:
        user = get_request_user(request)
        
        # 获取文档文件
        handler = WPSDocumentHandler()
        response = handler.get_document_file(document_id, user.id)
        
        # 修改Content-Disposition为下载
        if hasattr(response, 'content_disposition'):
            response['Content-Disposition'] = response['Content-Disposition'].replace(
                'inline', 'attachment'
            )
        else:
            try:
                document = CaseDocument.objects.get(id=document_id, is_deleted=False)
                filename = document.file_name or document.document_name or 'document.docx'
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            except CaseDocument.DoesNotExist:
                response['Content-Disposition'] = 'attachment; filename="document.docx"'
        
        logger.info(f"下载WPS文档: document_id={document_id}, user_id={user.id}")
        
        return response
        
    except Exception as e:
        logger.error(
            f"下载WPS文档失败: document_id={document_id}, error={str(e)}",
            exc_info=True
        )
        return HttpResponse(f"下载失败: {str(e)}", status=500)


@csrf_exempt
@require_http_methods(["POST"])
def wps_callback(request):
    """
    处理WPS回调
    
    POST /api/case/document/wps/callback/
    注意：此接口可能需要被WPS服务器调用，所以使用csrf_exempt
    """
    try:
        import json
        
        # 获取回调数据
        if request.content_type == 'application/json':
            callback_data = json.loads(request.body)
        else:
            callback_data = request.POST.dict()
        
        # 验证签名（如果提供）
        signature = request.headers.get('X-WPS-Signature') or request.GET.get('signature')
        if signature:
            handler = WPSCallbackHandler()
            if not handler.verify_callback_signature(callback_data, signature):
                logger.warning(f"WPS回调签名验证失败: {callback_data}")
                return JsonResponse({'success': False, 'message': '签名验证失败'}, status=403)
        
        # 处理回调
        handler = WPSCallbackHandler()
        result = handler.handle_callback(callback_data)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(
            f"处理WPS回调失败: error={str(e)}",
            exc_info=True
        )
        return JsonResponse(
            {'success': False, 'message': f'处理失败: {str(e)}'},
            status=500
        )

