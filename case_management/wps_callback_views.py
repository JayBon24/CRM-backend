"""
WPS回调服务接口实现（符合WPS官方规范）
"""
import json
import logging
import os
import time
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .models import CaseDocument
from .utils.wps_service import WPSService
from .utils.wps_document_handler import WPSDocumentHandler

logger = logging.getLogger(__name__)


class FrameAllowedHttpResponse(HttpResponse):
    """允许iframe加载的HTTP响应类"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 设置xframe_options_exempt属性，防止中间件添加X-Frame-Options: DENY
        # 但允许手动设置为SAMEORIGIN
        self.xframe_options_exempt = True
    
    def __setitem__(self, key, value):
        # 允许设置X-Frame-Options为SAMEORIGIN，阻止DENY
        if key.lower() == 'x-frame-options':
            if value.upper() == 'DENY':
                logger.warning(f"阻止设置 X-Frame-Options: DENY（不允许）")
            return
            # 允许SAMEORIGIN
            logger.debug(f"设置 X-Frame-Options: {value}")
        super().__setitem__(key, value)


class FrameAllowedFileResponse(FileResponse):
    """允许iframe加载的文件响应类"""
    def __init__(self, *args, **kwargs):
        # 移除as_attachment参数，确保是inline模式
        kwargs.pop('as_attachment', None)
        super().__init__(*args, **kwargs)
        # 设置xframe_options_exempt属性，防止中间件添加X-Frame-Options: DENY
        # 但允许手动设置为SAMEORIGIN
        self.xframe_options_exempt = True
    
    def __setitem__(self, key, value):
        # 允许设置X-Frame-Options为SAMEORIGIN，阻止DENY
        if key.lower() == 'x-frame-options':
            if value.upper() == 'DENY':
                logger.warning(f"阻止设置 X-Frame-Options: DENY（不允许）")
            return
            # 允许SAMEORIGIN
            logger.debug(f"设置 X-Frame-Options: {value}")
        super().__setitem__(key, value)
    
    def __delitem__(self, key):
        """删除响应头"""
        if key.lower() == 'x-frame-options':
            logger.info("删除 X-Frame-Options 响应头")
        super().__delitem__(key)
    
    def _set_content_disposition(self, value):
        """设置Content-Disposition响应头"""
        if hasattr(self, '_headers'):
            self._headers['content-disposition'] = ('Content-Disposition', value)
        else:
            super().__setitem__('Content-Disposition', value)
    
    def _get_response_headers(self):
        """获取响应头，确保移除X-Frame-Options"""
        headers = super()._get_response_headers() if hasattr(super(), '_get_response_headers') else []
        # 过滤掉X-Frame-Options头
        return [(k, v) for k, v in headers if k.lower() != 'x-frame-options']


def verify_wps_signature(request):
    """
    验证WPS回调请求签名（WPS-2签名算法）
    
    Args:
        request: Django请求对象
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        app_id = request.headers.get('X-App-Id')
        app_secret = getattr(settings, 'WPS_APP_SECRET', '')
        
        if not app_id or not app_secret:
            return False, "缺少WPS配置"
        
        # 验证AppId
        expected_app_id = getattr(settings, 'WPS_APP_ID', '')
        if app_id != expected_app_id:
            logger.warning(f"AppId不匹配: expected={expected_app_id}, got={app_id}")
            return False, "AppId不匹配"
        
        # 获取签名
        authorization = request.headers.get('Authorization', '')
        if not authorization:
            # 开发环境可以跳过签名验证
            if settings.DEBUG:
                logger.warning("开发环境：跳过WPS签名验证")
                return True, None
            return False, "缺少Authorization签名"
        
        # 使用WPS服务验证签名
        wps_service = WPSService()
        
        # 构建签名字符串所需的信息
        method = request.method
        uri = request.path
        query_string = request.GET.urlencode()
        headers_dict = dict(request.headers)
        body = request.body.decode('utf-8') if request.body else ''
        
        # 验证WPS-2签名
        is_valid = wps_service.verify_wps2_signature(
            method=method,
            uri=uri,
            query_string=query_string,
            headers=headers_dict,
            body=body
        )
        
        if not is_valid:
            return False, "签名验证失败"
        
        return True, None
        
    except Exception as e:
        logger.error(f"验证WPS签名失败: {str(e)}", exc_info=True)
        return False, f"签名验证失败: {str(e)}"


def get_user_from_token(request):
    """
    从WPS请求头获取用户信息
    
    Args:
        request: Django请求对象
    
    Returns:
        tuple: (user_id, user_name)
    """
    try:
        token = request.headers.get('X-WebOffice-Token', '')
        if not token:
            return None, None
        
        # 验证Token并获取用户信息
        wps_service = WPSService()
        token_info = wps_service.verify_token(token)
        
        if not token_info.get('valid'):
            return None, None
        
        user_id = token_info.get('user_id')
        # 这里可以根据user_id查询用户信息
        # 暂时返回user_id
        return user_id, f"user_{user_id}"
        
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}", exc_info=True)
        return None, None


@csrf_exempt
@require_http_methods(["GET"])
def wps_get_file_download_url(request, file_id):
    """
    获取文件下载地址（WPS回调接口）
    
    GET /v3/3rd/files/:file_id/download
    
    完全符合 WPS 标准：返回 URL + Digest(SHA1) + Headers(Referer)
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 获取用户信息
        user_id, user_name = get_user_from_token(request)
        
        # 查询文档
        try:
            document = CaseDocument.objects.get(id=file_id, is_deleted=False)
        except CaseDocument.DoesNotExist:
            return JsonResponse({
                "code": 40004,
                "message": "file not exists"
            }, status=404)
        
        # 生成文件下载URL
        base_url = f"{request.scheme}://{request.get_host()}"
        download_url = f"{base_url}/api/case/documents/{file_id}/public_download/"
        
        # 计算文件 SHA1 摘要
        import hashlib
        digest = ""
        digest_type = "sha1"
        
        file_path = document.full_file_path
        if file_path and os.path.exists(file_path):
            try:
                sha1 = hashlib.sha1()
                with open(file_path, 'rb') as f:
                    while chunk := f.read(8192):
                        sha1.update(chunk)
                digest = sha1.hexdigest()
            except Exception as e:
                logger.warning(f"计算文件摘要失败: file_id={file_id}, error={str(e)}")
        
        # 自定义请求头（用于防盗链等）
        headers = {}
        wps_referer_check = getattr(settings, 'WPS_REFERER_CHECK_ENABLED', False)
        if wps_referer_check:
            headers["Referer"] = "https://solution.wps.cn"
        
        logger.info(
            f"WPS获取文件下载地址: file_id={file_id}, user_id={user_id}, "
            f"url={download_url}, digest={digest[:16]}..."
        )
        
        response_data = {
            "url": download_url
        }
        
        # 添加摘要（如果计算成功）
        if digest:
            response_data["digest"] = digest
            response_data["digest_type"] = digest_type
        
        # 添加自定义请求头（如果需要）
        if headers:
            response_data["headers"] = headers
        
        return JsonResponse({
            "code": 0,
            "data": response_data
        })
        
    except Exception as e:
        logger.error(
            f"WPS获取文件下载地址失败: file_id={file_id}, error={str(e)}",
            exc_info=True
        )
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def wps_get_file_info(request, file_id):
    """
    获取文件信息（WPS回调接口）
    
    GET /v3/3rd/files/:file_id
    
    完全符合 WPS 标准：返回 creator_id、modifier_id
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 查询文档
        try:
            document = CaseDocument.objects.get(id=file_id, is_deleted=False)
        except CaseDocument.DoesNotExist:
            return JsonResponse({
                "code": 40004,
                "message": "file not exists"
            }, status=404)
        
        # 转换时间戳（安全处理None值）
        try:
            create_time = int(document.create_datetime.timestamp()) if (hasattr(document, 'create_datetime') and document.create_datetime) else 0
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning(f"获取创建时间失败: file_id={file_id}, error={str(e)}")
            create_time = 0
        
        try:
            modify_time = int(document.update_datetime.timestamp()) if (hasattr(document, 'update_datetime') and document.update_datetime) else create_time
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning(f"获取修改时间失败: file_id={file_id}, error={str(e)}")
            modify_time = create_time
        
        # 获取创建者和修改者ID（必须字段，WPS要求不能为空）
        creator_id = "system"
        modifier_id = "system"
        
        # 尝试从文档字段获取创建者ID（优先顺序）
        try:
            if hasattr(document, 'creator') and document.creator:
                # creator 是 ForeignKey，获取其ID
                creator_id = str(document.creator.id)
            elif hasattr(document, 'creator_id') and document.creator_id:
                creator_id = str(document.creator_id)
        except Exception as e:
            logger.warning(f"获取创建者ID失败: file_id={file_id}, error={str(e)}")
        
        # 尝试从文档字段获取修改者ID（优先顺序）
        try:
            if hasattr(document, 'last_editor_id') and document.last_editor_id:
                modifier_id = str(document.last_editor_id)
            elif hasattr(document, 'modifier_id') and document.modifier_id:
                modifier_id = str(document.modifier_id)
            elif hasattr(document, 'modifier') and document.modifier:
                # modifier 可能是 CharField（用户名）或 ForeignKey
                if hasattr(document.modifier, 'id'):
                    modifier_id = str(document.modifier.id)
                else:
                    # 如果是字符串类型的用户名，尝试通过用户名查找用户ID
                    try:
                        from dvadmin.system.models import Users
                        modifier_user = Users.objects.filter(username=str(document.modifier)).first()
                        if modifier_user:
                            modifier_id = str(modifier_user.id)
                    except:
                        pass
        except Exception as e:
            logger.warning(f"获取修改者ID失败: file_id={file_id}, error={str(e)}")
        
        # 如果修改者ID仍为空，使用创建者ID
        if not modifier_id or modifier_id == "system":
            modifier_id = creator_id
        
        # 最终确保ID不为空（WPS要求：creator_id 和 modifier_id 都不能为空）
        if not creator_id or creator_id == "None" or creator_id == "":
            creator_id = "system"
        if not modifier_id or modifier_id == "None" or modifier_id == "":
            modifier_id = creator_id if creator_id != "system" else "system"
        
        # 验证文档名称（不能包含特殊字符：\/|":*?<>）
        # 安全处理None值
        raw_document_name = document.document_name or ""
        raw_file_ext = document.file_ext if hasattr(document, 'file_ext') and document.file_ext else ".docx"
        
        # 如果文档名为空，使用默认名称
        if not raw_document_name or raw_document_name.strip() == "":
            raw_document_name = f"document_{file_id}"
        
        # 组合文件名和扩展名
        document_name = f"{raw_document_name}{raw_file_ext}"
        
        # 过滤特殊字符
        import re
        invalid_chars = r'[\/|":*?<>]'
        if re.search(invalid_chars, document_name):
            # 替换特殊字符为下划线
            document_name = re.sub(invalid_chars, '_', document_name)
            logger.warning(f"文档名称包含特殊字符，已替换: file_id={file_id}, name={document_name}")
        
        # 确保ID长度不超过47（WPS要求）
        document_id_str = str(document.id)
        if len(document_id_str) > 47:
            logger.warning(f"文档ID长度超过47: file_id={file_id}, id={document_id_str}")
            document_id_str = document_id_str[:47]
        
        # 严格类型转换，确保所有字段都是可序列化的基本类型
        # 处理 version（必须是正整数）
        try:
            version_value = int(document.version) if (hasattr(document, 'version') and document.version is not None) else 1
            if version_value < 1:
                version_value = 1
        except (ValueError, TypeError):
            version_value = 1
        
        # 处理 size（必须是非负整数）
        try:
            size_value = int(document.file_size) if (hasattr(document, 'file_size') and document.file_size is not None) else 0
            if size_value < 0:
                size_value = 0
        except (ValueError, TypeError):
            size_value = 0
        
        # 确保时间戳是整数
        create_time_int = int(create_time) if create_time else 0
        modify_time_int = int(modify_time) if modify_time else create_time_int
        
        # 确保文档名称是有效字符串
        safe_name = str(document_name)[:240] if document_name else f"document_{file_id}.docx"
        # 移除可能导致 JSON 解析失败的字符
        safe_name = safe_name.replace('\x00', '').replace('\r', '').replace('\n', ' ')
        
        # 确保 ID 是有效字符串（不能包含特殊字符）
        safe_creator_id = str(creator_id).replace('\x00', '') if creator_id else "system"
        safe_modifier_id = str(modifier_id).replace('\x00', '') if modifier_id else safe_creator_id
        
        # 构建响应数据（所有字段都是基本类型）
        response_data = {
            "code": 0,
            "data": {
                "id": str(document_id_str),
                "name": safe_name,
                "version": version_value,
                "size": size_value,
                "create_time": create_time_int,
                "modify_time": modify_time_int,
                "creator_id": safe_creator_id,
                "modifier_id": safe_modifier_id
            }
        }
        
        # 严格验证响应数据可以序列化
        try:
            import json
            # 先测试序列化
            json_str = json.dumps(response_data, ensure_ascii=False, separators=(',', ':'))
            # 再测试反序列化（确保格式正确）
            json.loads(json_str)
            
            # 记录响应内容（用于调试）
            logger.info(
                f"WPS获取文件信息成功: file_id={file_id}, "
                f"response_length={len(json_str)}, "
                f"data_keys={list(response_data['data'].keys())}, "
                f"response_preview={json_str[:200] if len(json_str) > 200 else json_str}"
            )
            
            # 详细记录每个字段的值和类型（用于调试）
            logger.debug(
                f"WPS文件信息详情: file_id={file_id}, "
                f"id={response_data['data']['id']}, "
                f"name={response_data['data']['name']}, "
                f"version={response_data['data']['version']}, "
                f"size={response_data['data']['size']}, "
                f"create_time={response_data['data']['create_time']}, "
                f"modify_time={response_data['data']['modify_time']}, "
                f"creator_id={response_data['data']['creator_id']}, "
                f"modifier_id={response_data['data']['modifier_id']}"
            )
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            logger.error(
                f"响应数据序列化失败: file_id={file_id}, error={str(e)}, "
                f"data={response_data}, "
                f"data_types={[(k, type(v).__name__) for k, v in response_data['data'].items()]}"
            )
            # 返回一个安全的错误响应
            return JsonResponse({
                "code": 50000,
                "message": "数据序列化失败"
            }, status=500)
        
        # 返回 JSON 响应（使用严格的 JSON 格式）
        response = JsonResponse(
            response_data,
            json_dumps_params={
                'ensure_ascii': False,
                'separators': (',', ':'),  # 紧凑格式，无多余空格
                'sort_keys': False  # 保持字段顺序
            }
        )
        
        # 确保响应头正确
        response['Content-Type'] = 'application/json; charset=utf-8'
        
        return response
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        error_msg = str(e) if e else "未知错误"
        # 确保错误消息是安全的字符串
        safe_error_msg = error_msg.replace('\x00', '').replace('\r', '').replace('\n', ' ')[:500]
        
        logger.error(
            f"WPS获取文件信息失败: file_id={file_id}, error={error_msg}\n{error_detail}",
            exc_info=True
        )
        
        # 返回安全的 JSON 错误响应
        error_response = JsonResponse({
            "code": 50000,
            "message": safe_error_msg
        }, status=500, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        error_response['Content-Type'] = 'application/json; charset=utf-8'
        return error_response


@csrf_exempt
@require_http_methods(["GET"])
def wps_get_file_permission(request, file_id):
    """
    获取文档用户权限（WPS回调接口）
    
    GET /v3/3rd/files/:file_id/permission
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 获取用户信息
        user_id, user_name = get_user_from_token(request)
        if not user_id:
            return JsonResponse({
                "code": 40003,
                "message": "invalid token"
            }, status=401)
        
        # 查询文档
        try:
            document = CaseDocument.objects.get(id=file_id, is_deleted=False)
        except CaseDocument.DoesNotExist:
            return JsonResponse({
                "code": 40004,
                "message": "file not exists"
            }, status=404)
        
        # 检查权限
        handler = WPSDocumentHandler()
        can_read = handler.check_document_permission(file_id, user_id, 'read')
        can_write = handler.check_document_permission(file_id, user_id, 'write')
        
        # 根据权限设置返回值
        # 1表示有权限，0表示无权限
        # 重要：当 update=1 或 print=1 时，必须返回 user_id（WPS文档要求）
        can_write = can_write  # update权限
        can_print = can_read  # print权限（通常与read权限相同）
        
        response_data = {
            "code": 0,
            "data": {
                "read": 1 if can_read else 0,
                "update": 1 if can_write else 0,
                "download": 1 if can_read else 0,
                "rename": 1 if can_write else 0,
                "history": 1 if can_read else 0,
                "copy": 1 if can_read else 0,
                "print": 1 if can_print else 0,
                "saveas": 1 if can_read else 0,
                "comment": 1 if can_write else 0
            }
        }
        
        # 当 update=1 或 print=1 时，必须返回 user_id（WPS文档要求）
        if can_write or can_print:
            response_data["data"]["user_id"] = str(user_id)
            logger.info(
                f"WPS权限接口: file_id={file_id}, user_id={user_id}, "
                f"update={1 if can_write else 0}, print={1 if can_print else 0}, "
                f"已返回user_id（WPS要求）"
            )
        
        logger.info(
            f"WPS获取文件权限: file_id={file_id}, user_id={user_id}, "
            f"read={1 if can_read else 0}, update={1 if can_write else 0}, "
            f"print={1 if can_print else 0}"
        )
        
        return JsonResponse(response_data, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
    except Exception as e:
        logger.error(
            f"WPS获取文件权限失败: file_id={file_id}, error={str(e)}",
            exc_info=True
        )
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def wps_save_file(request, file_id):
    """
    保存文档（WPS回调接口）
    
    POST /v3/3rd/files/:file_id/save
    
    完全符合 WPS 标准：接收 name/size/sha1/is_manual/file
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 获取用户信息
        user_id, user_name = get_user_from_token(request)
        if not user_id:
            return JsonResponse({
                "code": 40003,
                "message": "invalid token"
            }, status=401)
        
        # 检查文件是否上传
        if 'file' not in request.FILES:
            return JsonResponse({
                "code": 40002,
                "message": "file is required"
            }, status=400)
        
        uploaded_file = request.FILES['file']
        
        # 获取WPS传递的额外参数（符合WPS标准）
        file_name = request.POST.get('name', uploaded_file.name)
        file_size = int(request.POST.get('size', uploaded_file.size))
        file_sha1 = request.POST.get('sha1', '')
        is_manual = request.POST.get('is_manual', 'false').lower() == 'true'
        
        # 验证文件大小
        if file_size != uploaded_file.size:
            logger.warning(
                f"文件大小不匹配: file_id={file_id}, expected={file_size}, actual={uploaded_file.size}"
            )
        
        # 验证 SHA1 摘要（如果提供）
        if file_sha1:
            import hashlib
            sha1 = hashlib.sha1()
            for chunk in uploaded_file.chunks():
                sha1.update(chunk)
            calculated_sha1 = sha1.hexdigest()
            
            # 重置文件指针
            uploaded_file.seek(0)
            
            if calculated_sha1 != file_sha1:
                logger.error(
                    f"文件SHA1校验失败: file_id={file_id}, "
                    f"expected={file_sha1}, calculated={calculated_sha1}"
                )
                return JsonResponse({
                    "code": 40002,
                    "message": "file sha1 mismatch"
                }, status=400)
            
            logger.info(f"文件SHA1校验成功: file_id={file_id}, sha1={file_sha1}")
        
        # 保存文档
        handler = WPSDocumentHandler()
        result = handler.save_document(file_id, uploaded_file, user_id)
        
        logger.info(
            f"WPS保存文档成功: file_id={file_id}, user_id={user_id}, "
            f"size={uploaded_file.size}, version={result.get('version')}, "
            f"is_manual={is_manual}, sha1_verified={bool(file_sha1)}"
        )
        
        return JsonResponse({
            "code": 0,
            "data": {
                "id": str(file_id),
                "version": result.get('version', 1),
                "modify_time": int(time.time())
            }
        })
        
    except ValueError as e:
        logger.warning(f"WPS保存文档失败（参数错误）: file_id={file_id}, error={str(e)}")
        return JsonResponse({
            "code": 40002,
            "message": str(e)
        }, status=400)
    except PermissionError as e:
        logger.warning(f"WPS保存文档失败（权限不足）: file_id={file_id}, error={str(e)}")
        return JsonResponse({
            "code": 40005,
            "message": str(e)
        }, status=403)
    except Exception as e:
        logger.error(
            f"WPS保存文档失败: file_id={file_id}, error={str(e)}",
            exc_info=True
        )
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
def wps_rename_file(request, file_id):
    """
    重命名文件（WPS回调接口）
    
    PUT /v3/3rd/files/:file_id/name
    
    Request Body: {"name": "新文件名.docx"}
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 获取用户信息
        user_id, user_name = get_user_from_token(request)
        if not user_id:
            return JsonResponse({
                "code": 40003,
                "message": "invalid token"
            }, status=401)
        
        # 查询文档
        try:
            document = CaseDocument.objects.get(id=file_id, is_deleted=False)
        except CaseDocument.DoesNotExist:
            return JsonResponse({
                "code": 40004,
                "message": "file not exists"
            }, status=404)
        
        # 检查权限
        handler = WPSDocumentHandler()
        if not handler.check_document_permission(file_id, user_id, 'write'):
            return JsonResponse({
                "code": 40003,
                "message": "permission denied"
            }, status=403)
        
        # 解析请求体
        try:
            import json
            body_data = json.loads(request.body.decode('utf-8'))
            new_name = body_data.get('name', '').strip()
        except Exception as e:
            return JsonResponse({
                "code": 40005,
                "message": "invalid request body"
            }, status=400)
        
        if not new_name:
            return JsonResponse({
                "code": 40005,
                "message": "name is required"
            }, status=400)
        
        # 验证文件名
        if len(new_name) > 255:
            return JsonResponse({
                "code": 40005,
                "message": "name too long"
            }, status=400)
        
        # 分离文件名和扩展名
        import os
        base_name, file_ext = os.path.splitext(new_name)
        
        # 更新文档名称
        document.document_name = base_name
        if file_ext:
            document.file_ext = file_ext
        
        # 更新修改信息
        if hasattr(document, 'last_editor_id'):
            document.last_editor_id = user_id
        if hasattr(document, 'last_edit_time'):
            document.last_edit_time = datetime.now()
        
        document.save()
        
        logger.info(
            f"WPS重命名文件成功: file_id={file_id}, user_id={user_id}, "
            f"new_name={new_name}"
        )
        
        return JsonResponse({
            "code": 0,
            "data": {}
        })
        
    except Exception as e:
        logger.error(
            f"WPS重命名文件失败: file_id={file_id}, error={str(e)}",
            exc_info=True
        )
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def wps_get_file_watermark(request, file_id):
    """
    获取文件水印配置（WPS回调接口）
    
    GET /v3/3rd/files/:file_id/watermark
    
    完全符合 WPS 标准：返回水印配置信息
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 查询文档
        try:
            document = CaseDocument.objects.get(id=file_id, is_deleted=False)
        except CaseDocument.DoesNotExist:
            return JsonResponse({
                "code": 40004,
                "message": "file not exists"
            }, status=404)
        
        # 获取用户信息（用于判断是否需要显示水印）
        user_id, user_name = get_user_from_token(request)
        
        # 检查是否启用水印（可以从配置或文档属性读取）
        # 默认配置：无水印（type=0）
        watermark_config = {
            "type": 0  # 0表示无水印
        }
        
        # 检查是否需要显示水印
        # 1. 从配置读取全局水印设置
        wps_watermark_enabled = getattr(settings, 'WPS_WATERMARK_ENABLED', False)
        watermark_text = getattr(settings, 'WPS_WATERMARK_TEXT', '机密文档')
        
        # 2. 检查业务逻辑：是否需要对当前用户显示水印
        should_show_watermark = False
        
        if wps_watermark_enabled and user_id:
            # 获取创建者ID
            creator_id = None
            if hasattr(document, 'creator') and document.creator:
                creator_id = document.creator.id
            elif hasattr(document, 'creator_id') and document.creator_id:
                creator_id = document.creator_id
            
            # 业务逻辑：如果用户不是文档创建者，显示水印
            if creator_id and str(user_id) != str(creator_id):
                should_show_watermark = True
            # 或者：对所有用户显示水印（根据业务需求调整）
            # should_show_watermark = True
        
        # 如果启用水印，配置文字水印（type=1时必须包含所有必需字段）
        if should_show_watermark:
            watermark_config = {
                "type": 1,  # 1表示文字水印（必须）
                "value": watermark_text,  # type=1时必须：水印文字内容
                "horizontal": 100,  # type=1时必须：水印水平间距
                "vertical": 100,  # type=1时必须：水印垂直间距
                # 以下字段为可选
                "fill_style": "rgba(192, 192, 192, 0.6)",  # 可选：水印透明度
                "font": "bold 20px Microsoft YaHei",  # 可选：水印字体设置
                "rotate": -0.7853982  # 可选：水印旋转度（-45度，约-0.7853982弧度）
            }
        
        logger.info(
            f"WPS获取文件水印配置: file_id={file_id}, user_id={user_id}, "
            f"watermark_type={watermark_config.get('type', 0)}"
        )
        
        return JsonResponse({
            "code": 0,
            "data": watermark_config
        })
        
    except Exception as e:
        logger.error(
            f"WPS获取文件水印配置失败: file_id={file_id}, error={str(e)}",
            exc_info=True
        )
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def wps_notify(request):
    """
    事件通知接口（WPS回调接口）
    
    POST /v3/3rd/notify
    
    接收WPS的各种事件通知：
    - session_open: 文件首次打开
    - session_quit: 文件关闭
    - user_join: 用户加入会话
    - user_quit: 用户退出会话
    - operate_record_export: 导出/打印操作
    """
    try:
        import json
        
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 解析请求体
        try:
            body_data = json.loads(request.body.decode('utf-8'))
        except Exception as e:
            logger.error(f"解析事件通知请求体失败: error={str(e)}")
            return JsonResponse({
                "code": 40005,
                "message": "invalid request body"
            }, status=400)
        
        # 获取事件信息
        file_id = body_data.get('file_id', '')
        event_type = body_data.get('type', '')
        content = body_data.get('content', {})
        
        if not file_id or not event_type:
            return JsonResponse({
                "code": 40005,
                "message": "file_id and type are required"
            }, status=400)
        
        # 处理不同类型的事件
        try:
            document_id = int(file_id) if str(file_id).isdigit() else None
        except ValueError:
            document_id = None
        
        # 根据事件类型处理
        if event_type == 'session_open':
            # 文件首次打开
            handle_session_open(file_id, document_id, content)
        elif event_type == 'session_quit':
            # 文件关闭
            handle_session_quit(file_id, document_id, content)
        elif event_type == 'user_join':
            # 用户加入会话
            handle_user_join(file_id, document_id, content)
        elif event_type == 'user_quit':
            # 用户退出会话
            handle_user_quit(file_id, document_id, content)
        elif event_type == 'operate_record_export':
            # 导出/打印操作
            handle_operate_record_export(file_id, document_id, content)
        else:
            logger.warning(f"未知的事件类型: type={event_type}, file_id={file_id}")
        
        logger.info(
            f"WPS事件通知: file_id={file_id}, type={event_type}, "
            f"document_id={document_id}"
        )
        
        # 返回成功响应
        return JsonResponse({
            "code": 0,
            "data": {}
        })
        
    except Exception as e:
        logger.error(
            f"WPS事件通知处理失败: error={str(e)}",
            exc_info=True
        )
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


def handle_session_open(file_id: str, document_id: int, content: dict):
    """
    处理文件首次打开事件
    
    Args:
        file_id: 文件ID
        document_id: 文档ID
        content: 事件内容（SessionOpenContent）
    """
    try:
        # content 可能包含：
        # - session_id: 会话ID
        # - user_id: 用户ID
        # - timestamp: 时间戳等
        
        session_id = content.get('session_id', '')
        user_id = content.get('user_id', '')
        
        logger.info(
            f"文件首次打开: file_id={file_id}, document_id={document_id}, "
            f"session_id={session_id}, user_id={user_id}"
        )
        
        # 可以在这里记录编辑会话开始
        # 例如：创建编辑记录、更新文档状态等
        
        # 记录到数据库（如果模型存在）
        try:
            from .models import WPSEditRecord, CaseDocument
            if document_id:
                try:
                    document = CaseDocument.objects.get(id=document_id)
                    WPSEditRecord.objects.create(
                        document=document,
                        user_id=int(user_id) if user_id and str(user_id).isdigit() else None,
                        user_name=content.get('user_name', ''),
                        file_id=file_id,
                        edit_mode='edit',  # 默认为编辑模式
                        start_time=datetime.now()
                    )
                except CaseDocument.DoesNotExist:
                    pass
        except Exception as e:
            logger.warning(f"记录编辑会话失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"处理session_open事件失败: file_id={file_id}, error={str(e)}", exc_info=True)


def handle_session_quit(file_id: str, document_id: int, content: dict):
    """
    处理文件关闭事件
    
    Args:
        file_id: 文件ID
        document_id: 文档ID
        content: 事件内容（SessionQuitContent）
    """
    try:
        session_id = content.get('session_id', '')
        user_id = content.get('user_id', '')
        
        logger.info(
            f"文件关闭: file_id={file_id}, document_id={document_id}, "
            f"session_id={session_id}, user_id={user_id}"
        )
        
        # 可以在这里清理会话数据、更新文档状态等
        # 例如：更新编辑记录状态、清理临时文件等
        
    except Exception as e:
        logger.error(f"处理session_quit事件失败: file_id={file_id}, error={str(e)}", exc_info=True)


def handle_user_join(file_id: str, document_id: int, content: dict):
    """
    处理用户加入会话事件
    
    Args:
        file_id: 文件ID
        document_id: 文档ID
        content: 事件内容（UserJoinContent）
    """
    try:
        user_id = content.get('user_id', '')
        user_name = content.get('user_name', '')
        session_id = content.get('session_id', '')
        
        logger.info(
            f"用户加入会话: file_id={file_id}, document_id={document_id}, "
            f"user_id={user_id}, user_name={user_name}, session_id={session_id}"
        )
        
        # 可以在这里记录协作编辑用户、发送通知等
        # 例如：记录当前在线用户、通知其他用户等
        
    except Exception as e:
        logger.error(f"处理user_join事件失败: file_id={file_id}, error={str(e)}", exc_info=True)


def handle_user_quit(file_id: str, document_id: int, content: dict):
    """
    处理用户退出会话事件
    
    Args:
        file_id: 文件ID
        document_id: 文档ID
        content: 事件内容（UserQuitContent）
    """
    try:
        user_id = content.get('user_id', '')
        user_name = content.get('user_name', '')
        session_id = content.get('session_id', '')
        
        logger.info(
            f"用户退出会话: file_id={file_id}, document_id={document_id}, "
            f"user_id={user_id}, user_name={user_name}, session_id={session_id}"
        )
        
        # 可以在这里更新在线用户列表、清理用户相关数据等
        
    except Exception as e:
        logger.error(f"处理user_quit事件失败: file_id={file_id}, error={str(e)}", exc_info=True)


def handle_operate_record_export(file_id: str, document_id: int, content: dict):
    """
    处理导出/打印操作事件
    
    Args:
        file_id: 文件ID
        document_id: 文档ID
        content: 事件内容（OperateRecordExportContent）
    """
    try:
        user_id = content.get('user_id', '')
        operate_type = content.get('operate_type', '')  # export/print
        timestamp = content.get('timestamp', 0)
        
        logger.info(
            f"导出/打印操作: file_id={file_id}, document_id={document_id}, "
            f"user_id={user_id}, operate_type={operate_type}, timestamp={timestamp}"
        )
        
        # 可以在这里记录操作日志、统计导出/打印次数等
        # 例如：更新文档的打印次数、记录操作日志等
        
        if document_id:
            try:
                document = CaseDocument.objects.get(id=document_id)
                if operate_type == 'print' and hasattr(document, 'print_count'):
                    document.print_count = (document.print_count or 0) + 1
                    document.save(update_fields=['print_count'])
                    logger.info(f"更新文档打印次数: document_id={document_id}, count={document.print_count}")
            except CaseDocument.DoesNotExist:
                pass
            except Exception as e:
                logger.warning(f"更新操作记录失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"处理operate_record_export事件失败: file_id={file_id}, error={str(e)}", exc_info=True)


@xframe_options_exempt
@require_http_methods(["GET", "HEAD"])
def wps_office_view(request, office_type, file_id):
    """
    WPS SDK直接访问的路由（推荐方式）
    
    路径格式：/office/{officeType}/{fileId}
    例如：/office/w/238
    
    参数:
        office_type: 文档类型 (w/s/p/pdf)
            - w: Word文档 (.doc, .docx)
            - s: Excel表格 (.xls, .xlsx)
            - p: PowerPoint演示文稿 (.ppt, .pptx)
            - pdf: PDF文档
        file_id: 文档ID
    """
    try:
        # 解析file_id（通常就是document_id）
        try:
            document_id = int(file_id)
        except ValueError:
            return FrameAllowedHttpResponse(
                json.dumps({"code": 40001, "message": "invalid file_id"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )
        
        # 获取文档
        try:
            document = CaseDocument.objects.get(id=document_id)
        except CaseDocument.DoesNotExist:
            return FrameAllowedHttpResponse(
                json.dumps({"code": 40004, "message": "file not exists"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=404
            )
        
        # 文件扩展名映射（用于验证和生成文件名）
        office_type_map = {
            '.doc': 'w', '.docx': 'w',
            '.xls': 's', '.xlsx': 's',
            '.ppt': 'p', '.pptx': 'p',
            '.pdf': 'pdf'
        }
        file_ext_map = {
            'w': '.docx',
            's': '.xlsx',
            'p': '.pptx',
            'pdf': '.pdf'
        }
        
        # 验证文件类型是否匹配
        file_ext = os.path.splitext(document.document_name)[1].lower() if document.document_name else ''
        expected_type = office_type_map.get(file_ext, 'w')
        
        if office_type != expected_type:
            return FrameAllowedHttpResponse(
                json.dumps({
                    "code": 40003,
                    "message": f"文件类型不匹配，期望 {expected_type}，实际 {office_type}"
                }, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=400
            )
        
        # 获取文件路径（使用full_file_path属性，它会处理相对路径和绝对路径）
        file_path = document.full_file_path
        
        # 详细日志记录
        logger.info(
            f"WPS文档访问检查: document_id={document_id}, "
            f"file_path字段={document.file_path}, "
            f"full_file_path={file_path}, "
            f"file_path_exists={os.path.exists(file_path) if file_path else False}"
        )
        
        if not file_path:
            logger.warning(f"文档file_path为空: document_id={document_id}, document.document_name={document.document_name}")
            return FrameAllowedHttpResponse(
                json.dumps({"code": 40004, "message": "file path is empty"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=404
            )
        
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: file_path={file_path}, document_id={document_id}, document.file_path={document.file_path}")
            return FrameAllowedHttpResponse(
                json.dumps({"code": 40004, "message": f"file not exists: {file_path}"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=404
            )
        
        # 打开文件
        try:
            file = open(file_path, 'rb')
        except IOError as e:
            logger.error(f"打开文件失败: file_path={file_path}, error={str(e)}")
            return FrameAllowedHttpResponse(
                json.dumps({"code": 50000, "message": f"文件读取失败: {str(e)}"}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
                status=500
            )
        
        # 根据文件类型设置Content-Type
        content_type_map = {
            'w': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            's': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'p': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'pdf': 'application/pdf'
        }
        content_type = content_type_map.get(office_type, 'application/octet-stream')
        
        # 使用FrameAllowedFileResponse确保iframe可以加载
        response = FrameAllowedFileResponse(file, content_type=content_type)
        
        # ⚠️ 关键：必须设置这些响应头（WPS SDK要求）
        # ✅ 确保文件名不为空，并包含正确的扩展名
        # 获取文件名（使用 document_name 字段）
        raw_filename = document.document_name or ''
        
        # 移除可能存在的扩展名，获取纯文件名部分
        base_name = raw_filename
        if base_name:
            # 移除扩展名
            for ext in ['.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.pdf']:
                if base_name.lower().endswith(ext):
                    base_name = base_name[:-len(ext)]
                    break
        
        # 如果文件名为空或只有扩展名（base_name为空），使用默认文件名
        if not base_name or base_name.strip() == '':
            base_name = f'document_{document_id}'
        
        # 获取正确的扩展名
        ext = file_ext_map.get(office_type, '.docx')
        
        # 处理文件名中的特殊字符，确保是ASCII安全
        try:
            # 先对文件名部分进行编码
            ascii_base = base_name.encode('ascii', 'ignore').decode('ascii')
            # 如果编码后文件名为空，使用默认文件名
            if not ascii_base or ascii_base.strip() == '':
                ascii_base = f'document_{document_id}'
            
            # 组合文件名和扩展名
            ascii_filename = ascii_base + ext
            
            # 最终验证：确保文件名不为空且不是只有扩展名
            if not ascii_filename or ascii_filename == ext or ascii_filename.startswith('.'):
                ascii_filename = f"document_{document_id}{ext}"
                
        except Exception as e:
            logger.warning(f"文件名编码失败: base_name={base_name}, error={str(e)}")
            ascii_filename = f"document_{document_id}{ext}"
        
        # 记录最终的文件名，便于调试
        logger.debug(f"文件名处理: raw={raw_filename}, base={base_name}, final={ascii_filename}")
        
        # ✅ 1. 设置Content-Disposition为inline（WPS SDK要求）
        content_disposition = f'inline; filename="{ascii_filename}"'
        response['Content-Disposition'] = content_disposition
        if hasattr(response, '_headers'):
            response._headers['content-disposition'] = ('Content-Disposition', content_disposition)
        else:
            # 如果 _headers 不存在，尝试直接设置
            response._headers = {}
            response._headers['content-disposition'] = ('Content-Disposition', content_disposition)
        
        # ✅ 2. 设置X-Frame-Options为SAMEORIGIN（不能是DENY，WPS SDK要求）
        response['X-Frame-Options'] = 'SAMEORIGIN'
        if hasattr(response, '_headers'):
            response._headers['x-frame-options'] = ('X-Frame-Options', 'SAMEORIGIN')
        
        # 确保xframe_options_exempt属性被设置（防止中间件添加DENY）
        response.xframe_options_exempt = True
        
        # 对于HEAD请求，确保响应头正确返回（但不返回内容）
        if request.method == 'HEAD':
            # FileResponse 会自动处理 HEAD 请求，但我们需要确保响应头已设置
            # 创建一个只有响应头的响应
            head_response = FrameAllowedHttpResponse()
            head_response['Content-Disposition'] = content_disposition
            head_response['X-Frame-Options'] = 'SAMEORIGIN'
            head_response['Content-Type'] = content_type
            # 设置Content-Length（文件大小）
            try:
                file_size = os.path.getsize(file_path)
                head_response['Content-Length'] = str(file_size)
            except Exception:
                pass
            head_response.xframe_options_exempt = True
            if hasattr(head_response, '_headers'):
                head_response._headers['content-disposition'] = ('Content-Disposition', content_disposition)
                head_response._headers['x-frame-options'] = ('X-Frame-Options', 'SAMEORIGIN')
            file.close()  # 关闭文件，因为HEAD请求不需要内容
            logger.info(
                f"WPS HEAD请求: office_type={office_type}, file_id={file_id}, "
                f"document_id={document_id}, filename={ascii_filename}"
            )
            return head_response
        
        logger.info(
            f"WPS直接访问文档: office_type={office_type}, file_id={file_id}, "
            f"document_id={document_id}, filename={ascii_filename}"
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"WPS直接访问文档失败(参数错误): office_type={office_type}, file_id={file_id}, error={str(e)}", exc_info=True)
        return FrameAllowedHttpResponse(
            json.dumps({"code": 40001, "message": f"invalid parameter: {str(e)}"}, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=400
        )
    except CaseDocument.DoesNotExist:
        logger.warning(f"WPS直接访问文档失败(文档不存在): office_type={office_type}, file_id={file_id}")
        return FrameAllowedHttpResponse(
            json.dumps({"code": 40004, "message": "file not exists"}, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=404
        )
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(
            f"WPS直接访问文档失败(服务器错误): office_type={office_type}, file_id={file_id}, error={str(e)}\n{error_detail}",
            exc_info=True
        )
        # 错误页面也不能设置 X-Frame-Options: DENY
        error_response = FrameAllowedHttpResponse(
            json.dumps({
                "code": 50000,
                "message": f"服务器错误: {str(e)}",
                "detail": error_detail if settings.DEBUG else None
            }, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=500
        )
        return error_response


@csrf_exempt
@require_http_methods(["GET"])
def wps_get_users(request):
    """
    获取用户信息（WPS回调接口）
    
    GET /v3/3rd/users?user_ids=id1&user_ids=id2...
    
    完全符合 WPS 标准：支持批量查询多个用户
    """
    try:
        # 记录请求信息（用于调试）
        logger.info(
            f"WPS获取用户信息请求: method={request.method}, "
            f"path={request.path}, "
            f"full_path={request.get_full_path()}, "
            f"query_params={dict(request.GET)}, "
            f"headers_X_App_Id={request.headers.get('X-App-Id', 'N/A')}, "
            f"headers_X_WebOffice_Token={request.headers.get('X-WebOffice-Token', 'N/A')[:20]}..."
        )
        
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            logger.error(
                f"WPS用户信息接口签名验证失败: {error_msg}, "
                f"path={request.path}, "
                f"query_params={dict(request.GET)}"
            )
            error_response = JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
            error_response['Content-Type'] = 'application/json; charset=utf-8'
            return error_response
        
        # 获取请求的用户ID列表（WPS文档要求：user_ids 是必须参数）
        user_ids = request.GET.getlist('user_ids')
        
        # 验证 user_ids 参数（必须提供）
        if not user_ids:
            logger.warning("WPS用户信息: 未提供user_ids参数（必须参数）")
            return JsonResponse({
                "code": 40005,
                "message": "user_ids parameter is required"
            }, status=400, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 批量查询用户信息
        from dvadmin.system.models import Users
        users_data = []
        
        for uid in user_ids:
            try:
                # 处理特殊用户
                if uid == "anonymous":
                    users_data.append({
                        "id": "anonymous",
                        "name": "匿名用户"
                        # 注意：根据WPS文档，avatar_url是可选的，不包含logined字段
                    })
                    continue
                
                # 查询数据库用户
                try:
                    user = Users.objects.get(id=int(uid))
                    user_data = {
                        "id": str(user.id),
                        "name": user.name or user.username or f"用户{uid}"
                    }
                    # avatar_url是可选的，如果存在则添加（WPS要求必须是https链接）
                    avatar_url = getattr(user, 'avatar', '') or ""
                    if avatar_url:
                        # 确保 avatar_url 是 https 链接（WPS要求）
                        if avatar_url.startswith('http://'):
                            # 将 http 转换为 https
                            avatar_url = avatar_url.replace('http://', 'https://', 1)
                        elif not avatar_url.startswith('https://'):
                            # 如果是相对路径或其他格式，构建完整的 https URL
                            from django.http import HttpRequest
                            if isinstance(request, HttpRequest):
                                host = request.get_host()
                            else:
                                host = request.META.get('HTTP_HOST', 'localhost:8000')
                            
                            # WPS要求必须是 https 链接，所以统一使用 https
                            # 如果 avatar_url 以 / 开头，是相对路径
                            if avatar_url.startswith('/'):
                                avatar_url = f"https://{host}{avatar_url}"
                            else:
                                # 否则作为完整URL处理
                                avatar_url = f"https://{host}/{avatar_url.lstrip('/')}"
                        
                        user_data["avatar_url"] = avatar_url
                    users_data.append(user_data)
                except (Users.DoesNotExist, ValueError):
                    # 用户不存在，返回默认信息
                    users_data.append({
                        "id": str(uid),
                        "name": f"用户{uid}"
                        # 注意：不包含avatar_url，因为用户不存在
                    })
            except Exception as e:
                logger.warning(f"查询用户失败: user_id={uid}, error={str(e)}")
                # 查询失败，返回默认信息
                users_data.append({
                    "id": str(uid),
                    "name": f"用户{uid}"
                })
        
        logger.info(
            f"WPS批量获取用户信息: user_ids={user_ids}, "
            f"count={len(users_data)}, "
            f"users={[{'id': u.get('id'), 'name': u.get('name')} for u in users_data]}"
        )
        
        # 确保所有用户数据都是可序列化的
        safe_users_data = []
        for user in users_data:
            safe_user = {
                "id": str(user.get("id", "")),
                "name": str(user.get("name", ""))
            }
            # avatar_url是可选的（WPS要求必须是https链接）
            if "avatar_url" in user and user["avatar_url"]:
                avatar_url = str(user["avatar_url"])
                # 最终验证：确保是 https 链接
                if avatar_url.startswith('http://'):
                    avatar_url = avatar_url.replace('http://', 'https://', 1)
                elif not avatar_url.startswith('https://'):
                    # 如果不是 http/https，不添加该字段（避免WPS报错）
                    logger.warning(f"用户头像URL格式不正确（非https链接）: user_id={user.get('id')}, avatar_url={avatar_url}")
                    avatar_url = None
                
                if avatar_url:
                    safe_user["avatar_url"] = avatar_url
            safe_users_data.append(safe_user)
        
        # 构建响应数据
        response_data = {
            "code": 0,
            "data": safe_users_data
        }
        
        # 验证响应数据可以序列化
        try:
            import json
            json_str = json.dumps(response_data, ensure_ascii=False, separators=(',', ':'))
            json.loads(json_str)  # 验证可以反序列化
            
            logger.debug(
                f"WPS用户信息响应: user_ids={user_ids}, "
                f"response_length={len(json_str)}, "
                f"users_count={len(safe_users_data)}"
            )
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            logger.error(
                f"WPS用户信息序列化失败: error={str(e)}, "
                f"data={response_data}"
            )
            return JsonResponse({
                "code": 50000,
                "message": "数据序列化失败"
            }, status=500, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 根据文档规范，如果只查询一个用户，返回单个对象；多个用户返回数组
        # 但为了统一，我们始终返回数组（符合WPS标准）
        response = JsonResponse(
            response_data,
            json_dumps_params={
                'ensure_ascii': False,
                'separators': (',', ':'),
                'sort_keys': False
            }
        )
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        error_msg = str(e) if e else "未知错误"
        safe_error_msg = error_msg.replace('\x00', '').replace('\r', '').replace('\n', ' ')[:500]
        
        logger.error(
            f"WPS获取用户信息失败: error={error_msg}\n{error_detail}",
            exc_info=True
        )
        
        error_response = JsonResponse({
            "code": 50000,
            "message": safe_error_msg
        }, status=500, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        error_response['Content-Type'] = 'application/json; charset=utf-8'
        return error_response


# ================================================= #
# 三阶段保存接口（WPS官方推荐）
# ================================================= #

@csrf_exempt
@require_http_methods(["GET"])
def wps_upload_prepare(request, file_id):
    """
    准备上传阶段（三阶段保存第一步）
    
    GET /v3/3rd/files/:file_id/upload/prepare
    
    主要用于 WebOffice 与接入方进行参数协商（主要协商摘要算法）
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 检查文档是否存在
        try:
            document = CaseDocument.objects.get(id=file_id, is_deleted=False)
        except CaseDocument.DoesNotExist:
            return JsonResponse({
                "code": 40004,
                "message": "file not exists"
            }, status=404)
        
        logger.info(f"WPS准备上传: file_id={file_id}")
        
        # 返回支持的摘要算法（WPS标准：sha1, sha256, md5）
        return JsonResponse({
            "code": 0,
            "data": {
                "digest_types": ["sha1", "sha256", "md5"]
            },
            "message": ""
        })
        
    except Exception as e:
        logger.error(f"WPS准备上传失败: file_id={file_id}, error={str(e)}", exc_info=True)
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def wps_upload_get_url(request, file_id):
    """
    获取上传地址（三阶段保存第二步）
    
    POST /v3/3rd/files/:file_id/upload/
    或
    POST /v3/3rd/files/:file_id/upload/address
    
    返回文件上传地址和参数
    支持两种格式：
    1. 旧格式：{"request": {...}, "send_back_params": {...}}
    2. 新格式（WPS官方）：直接在Body中传参数
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 获取用户信息
        user_id, user_name = get_user_from_token(request)
        if not user_id:
            return JsonResponse({
                "code": 40003,
                "message": "invalid token"
            }, status=401, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 检查文档是否存在
        try:
            document = CaseDocument.objects.get(id=file_id, is_deleted=False)
        except CaseDocument.DoesNotExist:
            return JsonResponse({
                "code": 40004,
                "message": "file not exists"
            }, status=404, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 解析请求体
        try:
            request_data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError as e:
            logger.error(f"WPS获取上传地址JSON解析失败: file_id={file_id}, error={str(e)}, body={request.body[:200] if request.body else 'empty'}")
            return JsonResponse({
                "code": 40002,
                "message": "invalid json format"
            }, status=400, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 判断请求格式：新格式（WPS官方）还是旧格式
        # 新格式：直接在Body中，有file_id, name, size等字段
        # 旧格式：包装在request对象中
        if 'file_id' in request_data and 'name' in request_data:
            # 新格式（WPS官方文档格式）
            req_file_id = request_data.get('file_id', str(file_id))
            file_name = request_data.get('name', document.document_name)
            file_size = request_data.get('size', 0)
            digest = request_data.get('digest', {})
            is_manual = request_data.get('is_manual', False)
            attachment_size = request_data.get('attachment_size', 0)
            content_type = request_data.get('content_type', '')
            send_back_params = {}  # 新格式不包含send_back_params
        else:
            # 旧格式（兼容）
            req_file_id = request_data.get('request', {}).get('file_id', str(file_id))
            file_name = request_data.get('request', {}).get('name', document.document_name)
            file_size = request_data.get('request', {}).get('size', 0)
            digest = request_data.get('request', {}).get('digest', {})
            is_manual = request_data.get('request', {}).get('is_manual', False)
            attachment_size = request_data.get('request', {}).get('attachment_size', 0)
            content_type = request_data.get('request', {}).get('content_type', '')
            send_back_params = request_data.get('send_back_params', {})
        
        # 验证file_id一致性
        if str(req_file_id) != str(file_id):
            return JsonResponse({
                "code": 40002,
                "message": "file_id mismatch"
            }, status=400, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 生成上传URL（使用当前服务器地址）
        upload_url = f"{request.scheme}://{request.get_host()}/api/case/v3/3rd/files/{file_id}/upload/temp"
        
        # 生成上传token（用于验证）
        import hashlib
        import base64
        token_data = f"{file_id}:{user_id}:{int(time.time())}"
        token = base64.b64encode(token_data.encode()).decode()
        
        logger.info(
            f"WPS获取上传地址: file_id={file_id}, user_id={user_id}, "
            f"file_name={file_name}, size={file_size}, is_manual={is_manual}, "
            f"format={'new' if 'file_id' in request_data and 'name' in request_data else 'old'}"
        )
        
        # 根据WPS官方文档格式返回
        response_data = {
            "code": 0,
            "data": {
                "url": upload_url,  # WPS官方文档要求：url（不是upload_url）
                "method": "PUT",  # WPS官方文档要求：method（不是upload_method）
                "headers": {
                    "X-Upload-Token": token,
                    "Content-Type": "application/octet-stream"
                }
            }
        }
        
        # 如果有send_back_params（旧格式），添加到返回数据中
        if send_back_params:
            response_data["data"]["send_back_params"] = send_back_params
        
        # 确保JSON可以序列化
        try:
            json.dumps(response_data, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error(f"WPS上传地址响应序列化失败: file_id={file_id}, error={str(e)}")
            return JsonResponse({
                "code": 50000,
                "message": "响应数据序列化失败"
            }, status=500, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        response = JsonResponse(
            response_data,
            json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')}
        )
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response
        
    except Exception as e:
        logger.error(f"WPS获取上传地址失败: file_id={file_id}, error={str(e)}", exc_info=True)
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def wps_upload_commit(request, file_id):
    """
    完成上传阶段（三阶段保存第三步）
    
    POST /v3/3rd/files/:file_id/upload/commit
    
    确认上传完成并保存文档信息
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 获取用户信息
        user_id, user_name = get_user_from_token(request)
        if not user_id:
            return JsonResponse({
                "code": 40003,
                "message": "invalid token"
            }, status=401, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 检查文档是否存在
        try:
            document = CaseDocument.objects.get(id=file_id, is_deleted=False)
        except CaseDocument.DoesNotExist:
            return JsonResponse({
                "code": 40004,
                "message": "file not exists"
            }, status=404, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 解析请求体
        try:
            request_data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError as e:
            logger.error(f"WPS完成上传JSON解析失败: file_id={file_id}, error={str(e)}, body={request.body[:200] if request.body else 'empty'}")
            return JsonResponse({
                "code": 40002,
                "message": "invalid json format"
            }, status=400, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 判断请求格式：新格式（WPS官方）还是旧格式
        # 新格式：直接在Body中，有file_id, name, size等字段
        # 旧格式：包装在request对象中
        if 'file_id' in request_data and 'name' in request_data:
            # 新格式（WPS官方文档格式）
            req_file_id = request_data.get('file_id', str(file_id))
            file_name = request_data.get('name', document.document_name)
            file_size = request_data.get('size', 0)
            digest = request_data.get('digest', {})
            is_manual = request_data.get('is_manual', False)
            response_status = request_data.get('response', {}).get('status_code', 200) if 'response' in request_data else 200
            response_headers = request_data.get('response', {}).get('headers', {}) if 'response' in request_data else {}
            send_back_params = {}  # 新格式可能不包含send_back_params
        else:
            # 旧格式（兼容）
            req_file_id = request_data.get('request', {}).get('file_id', str(file_id))
            file_name = request_data.get('request', {}).get('name', document.document_name)
            file_size = request_data.get('request', {}).get('size', 0)
            digest = request_data.get('request', {}).get('digest', {})
            is_manual = request_data.get('request', {}).get('is_manual', False)
            response_status = request_data.get('response', {}).get('status_code', 200)
            response_headers = request_data.get('response', {}).get('headers', {})
            send_back_params = request_data.get('send_back_params', {})
        
        # 验证file_id一致性
        if str(req_file_id) != str(file_id):
            return JsonResponse({
                "code": 40002,
                "message": "file_id mismatch"
            }, status=400, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 验证上传响应状态
        if response_status != 200:
            return JsonResponse({
                "code": 40002,
                "message": f"upload failed with status {response_status}"
            }, status=400, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        # 从临时存储中获取文件（如果WPS上传到我们的临时接口）
        handler = WPSDocumentHandler()
        
        uploaded_file = None
        # 检查临时文件目录
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp', 'wps_uploads', str(file_id))
        if os.path.exists(temp_dir):
            # 查找最新的临时文件
            temp_files = [f for f in os.listdir(temp_dir) if f.endswith('.tmp')]
            if temp_files:
                # 按修改时间排序，获取最新的
                temp_files.sort(key=lambda x: os.path.getmtime(os.path.join(temp_dir, x)), reverse=True)
                latest_temp_file = os.path.join(temp_dir, temp_files[0])
                
                # 读取临时文件
                from django.core.files.uploadedfile import InMemoryUploadedFile
                from io import BytesIO
                
                with open(latest_temp_file, 'rb') as f:
                    file_content = f.read()
                    file_buffer = BytesIO(file_content)
                    uploaded_file = InMemoryUploadedFile(
                        file_buffer, None, document.document_name or 'document.docx',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        len(file_content), None
                    )
                
                # 删除临时文件
                try:
                    os.remove(latest_temp_file)
                    logger.info(f"已删除临时文件: {latest_temp_file}")
                except Exception as e:
                    logger.warning(f"删除临时文件失败: {latest_temp_file}, error={str(e)}")
        
        if uploaded_file:
            # 验证摘要
            if digest:
                import hashlib
                sha1 = hashlib.sha1()
                for chunk in uploaded_file.chunks():
                    sha1.update(chunk)
                calculated_sha1 = sha1.hexdigest()
                uploaded_file.seek(0)
                
                expected_sha1 = digest.get('sha1', '')
                if expected_sha1 and calculated_sha1 != expected_sha1:
                    logger.error(
                        f"文件SHA1校验失败: file_id={file_id}, "
                        f"expected={expected_sha1}, calculated={calculated_sha1}"
                    )
                    return JsonResponse({
                        "code": 40002,
                        "message": "file sha1 mismatch"
                    }, status=400, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
            
            # 保存文档
            result = handler.save_document(file_id, uploaded_file, user_id)
        else:
            # 如果文件已经保存，只更新元数据
            result = handler.update_document_metadata(file_id, user_id, file_name, file_size)
        
        # 获取文档信息
        document.refresh_from_db()
        
        logger.info(
            f"WPS完成上传: file_id={file_id}, user_id={user_id}, "
            f"version={result.get('version', 1)}, is_manual={is_manual}"
        )
        
        # 安全处理时间戳
        try:
            create_time = int(document.create_datetime.timestamp()) if (hasattr(document, 'create_datetime') and document.create_datetime) else int(time.time())
        except (AttributeError, ValueError, TypeError):
            create_time = int(time.time())
        
        try:
            modify_time = int(document.update_datetime.timestamp()) if (hasattr(document, 'update_datetime') and document.update_datetime) else create_time
        except (AttributeError, ValueError, TypeError):
            modify_time = create_time
        
        # 安全处理创建者和修改者ID
        creator_id = str(user_id)
        try:
            if hasattr(document, 'creator_id') and document.creator_id:
                creator_id = str(document.creator_id)
            elif hasattr(document, 'creator') and document.creator:
                creator_id = str(document.creator.id) if hasattr(document.creator, 'id') else str(user_id)
        except Exception:
            creator_id = str(user_id)
        
        # 构建响应数据
        response_data = {
            "code": 0,
            "data": {
                "id": str(file_id),
                "name": str(document.document_name or file_name or f"document_{file_id}"),
                "version": int(result.get('version', 1)),
                "size": int(file_size or document.file_size or 0),
                "create_time": int(create_time),
                "modify_time": int(modify_time),
                "creator_id": str(creator_id),
                "modifier_id": str(user_id)
            },
            "message": ""
        }
        
        # 验证响应数据可以序列化
        try:
            json.dumps(response_data, ensure_ascii=False, separators=(',', ':'))
        except (TypeError, ValueError) as e:
            logger.error(f"WPS完成上传响应序列化失败: file_id={file_id}, error={str(e)}, data={response_data}")
            return JsonResponse({
                "code": 50000,
                "message": "响应数据序列化失败"
            }, status=500, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        
        response = JsonResponse(
            response_data,
            json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')}
        )
        response['Content-Type'] = 'application/json; charset=utf-8'
        return response
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        error_msg = str(e) if e else "未知错误"
        safe_error_msg = error_msg.replace('\x00', '').replace('\r', '').replace('\n', ' ')[:500]
        
        logger.error(
            f"WPS完成上传失败: file_id={file_id}, error={error_msg}\n{error_detail}",
            exc_info=True
        )
        
        error_response = JsonResponse({
            "code": 50000,
            "message": safe_error_msg
        }, status=500, json_dumps_params={'ensure_ascii': False, 'separators': (',', ':')})
        error_response['Content-Type'] = 'application/json; charset=utf-8'
        return error_response


# ================================================= #
# 三阶段保存临时文件上传接口
# ================================================= #

@csrf_exempt
@require_http_methods(["PUT", "POST"])
def wps_upload_temp(request, file_id):
    """
    临时文件上传接口（三阶段保存中使用）
    
    PUT/POST /v3/3rd/files/:file_id/upload/temp
    
    用于接收WPS上传的文件内容，临时存储，等待commit阶段确认
    """
    try:
        # 验证上传token（从headers中获取）
        upload_token = request.headers.get('X-Upload-Token', '')
        if not upload_token:
            return JsonResponse({
                "code": 40001,
                "message": "missing upload token"
            }, status=403)
        
        # 获取文件内容
        file_content = request.body
        
        if not file_content:
            return JsonResponse({
                "code": 40002,
                "message": "file content is required"
            }, status=400)
        
        # 临时存储文件（存储在临时目录，等待commit阶段处理）
        import tempfile
        import hashlib
        
        # 创建临时文件目录
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp', 'wps_uploads', str(file_id))
        os.makedirs(temp_dir, exist_ok=True)
        
        # 生成临时文件名（使用token和文件ID）
        temp_filename = f"upload_{file_id}_{int(time.time())}.tmp"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        # 保存临时文件
        with open(temp_path, 'wb') as f:
            f.write(file_content)
        
        # 计算文件SHA1（用于commit阶段验证）
        sha1 = hashlib.sha1(file_content).hexdigest()
        
        logger.info(
            f"WPS临时文件上传: file_id={file_id}, size={len(file_content)}, "
            f"sha1={sha1}, temp_path={temp_path}"
        )
        
        # 返回成功响应（WPS会读取这个响应）
        return HttpResponse(
            json.dumps({
                "code": 0,
                "data": {
                    "sha1": sha1,
                    "size": len(file_content)
                }
            }, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            status=200
        )
        
    except Exception as e:
        logger.error(f"WPS临时文件上传失败: file_id={file_id}, error={str(e)}", exc_info=True)
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


# ================================================= #
# 扩展能力接口（智能文档/多维表格）
# ================================================= #

@csrf_exempt
@require_http_methods(["PUT"])
def wps_upload_object(request, key):
    """
    上传附件对象（扩展能力）
    
    PUT /v3/3rd/object/:key?name=xxx
    
    智能文档/多维表格 插入图片需要实现该接口
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 获取用户信息
        user_id, user_name = get_user_from_token(request)
        if not user_id:
            return JsonResponse({
                "code": 40003,
                "message": "invalid token"
            }, status=401)
        
        # 获取附件名称
        attachment_name = request.GET.get('name', f'attachment_{key}')
        
        # 获取附件数据
        attachment_data = request.body
        
        if not attachment_data:
            return JsonResponse({
                "code": 40002,
                "message": "attachment data is required"
            }, status=400)
        
        # 保存附件到媒体目录
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        
        # 构建附件存储路径
        attachment_path = f"wps/attachments/{key}/{attachment_name}"
        
        # 保存附件
        saved_path = default_storage.save(attachment_path, ContentFile(attachment_data))
        
        logger.info(
            f"WPS上传附件对象: key={key}, name={attachment_name}, "
            f"size={len(attachment_data)}, user_id={user_id}"
        )
        
        return JsonResponse({
            "code": 0,
            "data": {}
        })
        
    except Exception as e:
        logger.error(f"WPS上传附件对象失败: key={key}, error={str(e)}", exc_info=True)
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def wps_get_object_url(request, key):
    """
    获取附件对象下载地址（扩展能力）
    
    GET /v3/3rd/object/:key/url
    
    智能文档/多维表格 预览图片需要实现该接口
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 获取查询参数（缩略图参数）
        scale_max_fit_width = request.GET.get('scale_max_fit_width')
        scale_max_fit_height = request.GET.get('scale_max_fit_height')
        scale_long_edge = request.GET.get('scale_long_edge')
        
        # 构建附件下载URL
        attachment_url = f"{request.scheme}://{request.get_host()}/media/wps/attachments/{key}"
        
        # 如果有缩略图参数，可以添加到URL中
        if scale_max_fit_width or scale_max_fit_height or scale_long_edge:
            params = []
            if scale_max_fit_width:
                params.append(f"scale_max_fit_width={scale_max_fit_width}")
            if scale_max_fit_height:
                params.append(f"scale_max_fit_height={scale_max_fit_height}")
            if scale_long_edge:
                params.append(f"scale_long_edge={scale_long_edge}")
            if params:
                attachment_url += "?" + "&".join(params)
        
        logger.info(f"WPS获取附件下载地址: key={key}")
        
        return JsonResponse({
            "code": 0,
            "data": {
                "url": attachment_url
            }
        })
        
    except Exception as e:
        logger.error(f"WPS获取附件下载地址失败: key={key}, error={str(e)}", exc_info=True)
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def wps_copy_object(request):
    """
    拷贝附件对象（扩展能力）
    
    POST /v3/3rd/object/copy
    
    智能文档/多维表格 拷贝图片需要实现该接口
    """
    try:
        # 验证签名
        is_valid, error_msg = verify_wps_signature(request)
        if not is_valid:
            return JsonResponse({
                "code": 40001,
                "message": error_msg or "签名验证失败"
            }, status=403)
        
        # 解析请求体
        try:
            request_data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({
                "code": 40002,
                "message": "invalid json format"
            }, status=400)
        
        # 获取key_dict
        key_dict = request_data.get('key_dict', {})
        
        if not key_dict:
            return JsonResponse({
                "code": 40002,
                "message": "key_dict is required"
            }, status=400)
        
        # 拷贝附件（从源key到目标key）
        from django.core.files.storage import default_storage
        
        copied_count = 0
        for source_key, target_key in key_dict.items():
            try:
                # 构建源文件路径和目标文件路径
                source_path = f"wps/attachments/{source_key}"
                target_path = f"wps/attachments/{target_key}"
                
                # 检查源文件是否存在
                if default_storage.exists(source_path):
                    # 读取源文件
                    source_file = default_storage.open(source_path, 'rb')
                    source_content = source_file.read()
                    source_file.close()
                    
                    # 保存为目标文件
                    from django.core.files.base import ContentFile
                    default_storage.save(target_path, ContentFile(source_content))
                    copied_count += 1
                    logger.info(f"拷贝附件: {source_key} -> {target_key}")
                else:
                    logger.warning(f"源附件不存在: {source_key}")
                    
            except Exception as e:
                logger.error(f"拷贝附件失败: {source_key} -> {target_key}, error={str(e)}")
        
        logger.info(f"WPS拷贝附件对象: copied_count={copied_count}, total={len(key_dict)}")
        
        return JsonResponse({
            "code": 0,
            "data": {}
        })
        
    except Exception as e:
        logger.error(f"WPS拷贝附件对象失败: error={str(e)}", exc_info=True)
        return JsonResponse({
            "code": 50000,
            "message": str(e)
        }, status=500)

