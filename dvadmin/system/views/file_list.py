import hashlib
import mimetypes

import django_filters
from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from application import dispatch
from dvadmin.system.models import FileList
from dvadmin.utils.json_response import DetailResponse, SuccessResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class FileSerializer(CustomModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)
    file_id = serializers.IntegerField(source="id", read_only=True)
    preview_url = serializers.SerializerMethodField(read_only=True)
    storage_key = serializers.SerializerMethodField(read_only=True)

    def get_url(self, instance):
        if (instance.engine or '').lower() == 'db':
            return instance.file_url or f'admin-api/system/file/{instance.id}/preview/'
        if self.request.query_params.get('prefix'):
            if settings.ENVIRONMENT in ['local']:
                prefix = 'http://127.0.0.1:8000'
            elif settings.ENVIRONMENT in ['test']:
                prefix = 'http://{host}/api'.format(host=self.request.get_host())
            else:
                prefix = 'https://{host}/api'.format(host=self.request.get_host())
            if instance.file_url:
                return instance.file_url if instance.file_url.startswith('http') else f"{prefix}/{instance.file_url}"
            return (f'{prefix}/media/{str(instance.url)}')
        return instance.file_url or (f'media/{str(instance.url)}')

    def _append_access_token(self, target_url: str):
        """
        /media 资源默认受保护，允许使用 access_token 查询参数给 <image> 场景透传鉴权
        """
        if not target_url:
            return target_url
        normalized = target_url if target_url.startswith('/') else f'/{target_url}'
        if '/media/' not in normalized and '/admin-api/system/file/' not in normalized:
            return target_url
        auth_header = self.request.META.get('HTTP_AUTHORIZATION', '')
        token = ''
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        if not token:
            return target_url
        if 'access_token=' in target_url:
            return target_url
        sep = '&' if '?' in target_url else '?'
        return f"{target_url}{sep}access_token={token}"

    def get_preview_url(self, instance):
        url = self.get_url(instance)
        if not url:
            return ""
        return url

    def get_storage_key(self, instance):
        file_url = instance.file_url or ""
        if file_url.startswith("http://") or file_url.startswith("https://"):
            parts = file_url.split("/", 3)
            if len(parts) >= 4:
                return parts[3]
            return ""
        normalized = file_url.lstrip("/")
        if normalized.startswith("media/"):
            return normalized[len("media/"):]
        if instance.url:
            return str(instance.url)
        return normalized

    class Meta:
        model = FileList
        fields = "__all__"

    def create(self, validated_data):
        file_engine = dispatch.get_system_config_values("file_storage.file_engine") or 'local'
        file_backup = dispatch.get_system_config_values("file_storage.file_backup")
        file = self.initial_data.get('file')
        file_size = file.size
        validated_data['name'] = str(file)
        validated_data['size'] = file_size
        md5 = hashlib.md5()
        for chunk in file.chunks():
            md5.update(chunk)
        validated_data['md5sum'] = md5.hexdigest()
        validated_data['engine'] = file_engine
        validated_data['mime_type'] = file.content_type
        ft = {'image':0,'video':1,'audio':2}.get(file.content_type.split('/')[0], None)
        validated_data['file_type'] = 3 if ft is None else ft
        if file_backup and file_engine != 'db':
            validated_data['url'] = file
        if file_engine == 'oss':
            from dvadmin.utils.aliyunoss import ali_oss_upload
            file_path = ali_oss_upload(file, file_name=validated_data['name'])
            if file_path:
                validated_data['file_url'] = file_path
            else:
                raise ValueError("上传失败")
        elif file_engine == 'cos':
            from dvadmin.utils.tencentcos import tencent_cos_upload
            file_path = tencent_cos_upload(file, file_name=validated_data['name'])
            if file_path:
                validated_data['file_url'] = file_path
            else:
                raise ValueError("上传失败")
        elif file_engine == 'db':
            try:
                file.seek(0)
                validated_data['file_blob'] = file.read()
            except Exception:
                raise ValueError("上传失败")
            validated_data['file_url'] = ''
        else:
            validated_data['url'] = file
        # 审计字段
        try:
            request_user = self.request.user
            validated_data['dept_belong_id'] = request_user.dept.id
            validated_data['creator'] = request_user.id
            validated_data['modifier'] = request_user.id
        except:
            pass
        return super().create(validated_data)


class FileAllSerializer(CustomModelSerializer):
    
    class Meta:
        model = FileList
        fields = ['id', 'name']


class FileFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains", help_text="文件名")
    mime_type = django_filters.CharFilter(field_name="mime_type", lookup_expr="icontains", help_text="文件类型")

    class Meta:
        model = FileList
        fields = ['name', 'mime_type', 'upload_method', 'file_type']


class FileViewSet(CustomModelViewSet):
    """
    文件管理接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = FileList.objects.all()
    serializer_class = FileSerializer
    filter_class = FileFilter
    permission_classes = []

    def _resolve_token_user(self, request):
        if request.user and request.user.is_authenticated:
            return request.user
        token = request.query_params.get("access_token")
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

    @action(methods=['GET'], detail=True, permission_classes=[], url_path='preview')
    def preview(self, request, pk=None):
        user = self._resolve_token_user(request)
        if not user:
            return Response(
                {"detail": "身份认证信息未提供。"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        # 这里不能使用 self.get_object()，否则会先触发数据权限过滤，
        # 小程序通过 access_token 访问图片时 request.user 仍是匿名，导致被误判 404。
        instance = get_object_or_404(FileList, pk=pk)

        engine = (instance.engine or '').lower()
        if engine == 'db':
            if not instance.file_blob:
                return Response({"detail": "文件不存在"}, status=status.HTTP_404_NOT_FOUND)
            content_type = instance.mime_type or mimetypes.guess_type(instance.name or '')[0] or 'application/octet-stream'
            response = HttpResponse(instance.file_blob, content_type=content_type)
            # 小程序 <image> 在 iOS 真机下对带 Content-Disposition 的图片响应兼容较差，
            # 会出现可下载但缩略图不渲染。图片场景不设置该头，其他文件保留 inline 名称。
            if not str(content_type).lower().startswith('image/'):
                filename = instance.name or f'file_{instance.id}'
                response['Content-Disposition'] = f"inline; filename*=UTF-8''{filename}"
            return response

        serializer = self.get_serializer(instance)
        target_url = serializer.get_preview_url(instance) or serializer.get_url(instance)
        if not target_url:
            return Response({"detail": "文件不存在"}, status=status.HTTP_404_NOT_FOUND)
        if target_url.startswith('http://') or target_url.startswith('https://'):
            return redirect(target_url)
        normalized = target_url if target_url.startswith('/') else f'/{target_url}'
        return redirect(serializer._append_access_token(normalized))

    @action(methods=['GET'], detail=False)
    def get_all(self, request):
        data1 = self.get_serializer(self.get_queryset(), many=True).data
        data2 = []
        if dispatch.is_tenants_mode():
            from django_tenants.utils import schema_context
            with schema_context('public'):
                data2 = self.get_serializer(FileList.objects.all(), many=True).data
        return DetailResponse(data=data2+data1)

    def list(self, request, *args, **kwargs):
        if self.request.query_params.get('system', 'False') == 'True' and dispatch.is_tenants_mode():
            from django_tenants.utils import schema_context
            with schema_context('public'):
                return super().list(request, *args, **kwargs)
        return super().list(request, *args, **kwargs)
