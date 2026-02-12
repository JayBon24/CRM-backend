"""
媒体文件权限控制视图
提供对上传文件的权限控制访问
"""
import os
import mimetypes
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken


def _authenticate_from_query_token(request):
    """
    允许图片/附件通过 access_token 查询参数访问（用于 <image> 无法附带 Authorization 头的场景）
    """
    token = request.query_params.get("access_token") or request.GET.get("access_token")
    if not token:
        return None
    try:
        auth = JWTAuthentication()
        validated_token = auth.get_validated_token(token)
        user = auth.get_user(validated_token)
        if user and user.is_active:
            return user
    except (TokenError, InvalidToken, Exception):
        return None
    return None


@api_view(['GET'])
def serve_protected_media(request, file_path):
    """
    提供受保护的媒体文件访问
    
    当前权限：只有登录用户可以访问
    未来扩展：可以根据文件路径、用户角色等进行更细粒度的权限控制
    
    Args:
        request: HTTP请求对象
        file_path: 相对于MEDIA_ROOT的文件路径
    
    Returns:
        FileResponse: 文件响应
    """
    
    # ========== 友好的权限检查 ==========
    user = request.user if request.user and request.user.is_authenticated else _authenticate_from_query_token(request)
    if not user or not user.is_authenticated:
        return Response(
            {
                "error": "没有权限访问",
                "message": "您没有权限访问此文件，请先登录",
                "code": "AUTHENTICATION_REQUIRED"
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # 构建完整的文件路径
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    
    # 安全检查：防止路径穿越攻击
    full_path = os.path.abspath(full_path)
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    
    if not full_path.startswith(media_root):
        return Response(
            {
                "error": "访问被拒绝",
                "message": "非法的文件路径，无法访问",
                "code": "INVALID_PATH"
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # 检查文件是否存在
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        return Response(
            {
                "error": "文件不存在",
                "message": "您访问的文件不存在或已被删除",
                "code": "FILE_NOT_FOUND"
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # ========== 权限控制逻辑（可扩展） ==========
    # 当前：已登录即可访问
    # 未来可以在这里添加更细粒度的权限检查，例如：
    
    # 1. 检查用户是否有权限访问特定案件的文件
    # if 'cases/' in file_path:
    #     case_id = extract_case_id_from_path(file_path)
    #     if not has_case_access_permission(request.user, case_id):
    #         return Response(
    #             {
    #                 "error": "没有权限访问",
    #                 "message": "您没有权限访问此案件的文件",
    #                 "code": "CASE_ACCESS_DENIED"
    #             },
    #             status=status.HTTP_403_FORBIDDEN
    #         )
    
    # 2. 检查用户角色权限
    # if not request.user.has_perm('case_management.view_casedocument'):
    #     return Response(
    #         {
    #             "error": "没有权限访问",
    #             "message": "您没有查看文档的权限",
    #             "code": "PERMISSION_DENIED"
    #         },
    #         status=status.HTTP_403_FORBIDDEN
    #     )
    
    # 3. 检查文件类型权限
    # file_ext = os.path.splitext(file_path)[1].lower()
    # if file_ext in ['.pdf', '.docx'] and not user_has_document_permission(request.user):
    #     return Response(
    #         {
    #             "error": "没有权限访问",
    #             "message": "您没有权限访问此类型的文件",
    #             "code": "FILE_TYPE_DENIED"
    #         },
    #         status=status.HTTP_403_FORBIDDEN
    #     )
    
    # ========== 权限检查通过，返回文件 ==========
    
    # 获取文件的MIME类型
    content_type, _ = mimetypes.guess_type(full_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    # 返回文件
    try:
        response = FileResponse(open(full_path, 'rb'), content_type=content_type)
        
        # 设置文件名（支持中文）
        filename = os.path.basename(full_path)
        response['Content-Disposition'] = f'inline; filename*=UTF-8\'\'{filename}'
        
        return response
    except Exception as e:
        return Response(
            {
                "error": "文件读取失败",
                "message": f"无法读取文件，请稍后重试",
                "detail": str(e),
                "code": "FILE_READ_ERROR"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ========== 未来可扩展的权限检查辅助函数 ==========

def extract_case_id_from_path(file_path):
    """
    从文件路径中提取案件ID
    例如: cases/17/document.pdf -> 17
    """
    parts = file_path.split('/')
    if len(parts) >= 2 and parts[0] == 'cases':
        try:
            return int(parts[1])
        except ValueError:
            pass
    return None


def has_case_access_permission(user, case_id):
    """
    检查用户是否有权限访问指定案件的文件
    
    可以根据以下条件判断：
    - 用户是案件的创建者
    - 用户是案件的负责人
    - 用户有管理员权限
    - 用户在案件的协作人员列表中
    
    Args:
        user: 当前用户
        case_id: 案件ID
    
    Returns:
        bool: 是否有权限
    """
    # TODO: 实现具体的权限检查逻辑
    # from .models import CaseManagement
    # try:
    #     case = CaseManagement.objects.get(id=case_id, is_deleted=False)
    #     # 检查用户是否是创建者或负责人
    #     if case.creator == user or case.draft_person == user:
    #         return True
    #     # 检查是否是管理员
    #     if user.is_superuser:
    #         return True
    #     # 其他权限检查...
    #     return False
    # except CaseManagement.DoesNotExist:
    #     return False
    
    # 暂时返回True，表示所有登录用户都可以访问
    return True


def user_has_document_permission(user):
    """
    检查用户是否有文档查看权限
    
    可以基于：
    - Django的内置权限系统
    - 自定义的角色权限
    - 部门权限等
    
    Args:
        user: 当前用户
    
    Returns:
        bool: 是否有权限
    """
    # TODO: 实现具体的权限检查逻辑
    # return user.has_perm('case_management.view_casedocument')
    
    # 暂时返回True
    return True
