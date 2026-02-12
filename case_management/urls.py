"""
案例管理URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CaseManagementViewSet, 
    CaseDocumentViewSet, 
    DocumentTemplateViewSet, 
    CaseFolderViewSet,
    convert_docx_to_html,
    convert_html_to_docx,
    upload_document_image
)
from .regulation_search_views import RegulationSearchViewSet, RegulationConversationViewSet
from .wps_views import (
    wps_preview_config,
    wps_edit_config,
    wps_init_config,
    wps_get_file,
    wps_save_document,
    wps_download_document,
    wps_callback
)
from .wps_callback_views import (
    wps_get_file_download_url,
    wps_get_file_info,
    wps_get_file_permission,
    wps_save_file,
    wps_rename_file,
    wps_get_file_watermark,
    wps_get_users,
    wps_notify,
    wps_office_view,
    wps_upload_prepare,
    wps_upload_get_url,
    wps_upload_commit,
    wps_upload_temp,
    wps_upload_object,
    wps_get_object_url,
    wps_copy_object
)

router = DefaultRouter()
router.register(r'cases', CaseManagementViewSet, basename='case-management')
router.register(r'documents', CaseDocumentViewSet, basename='case-documents')
router.register(r'templates', DocumentTemplateViewSet, basename='document-templates')
router.register(r'folders', CaseFolderViewSet, basename='case-folders')
router.register(r'regulation-search', RegulationSearchViewSet, basename='regulation-search')
router.register(r'regulation-conversations', RegulationConversationViewSet, basename='regulation-conversations')

urlpatterns = [
    path('', include(router.urls)),
    # 文档转换API
    path('document/convert/docx-to-html/', convert_docx_to_html, name='convert_docx_to_html'),
    path('document/convert/html-to-docx/', convert_html_to_docx, name='convert_html_to_docx'),
    path('document/upload-image/', upload_document_image, name='upload_document_image'),
    # WPS文档集成API
    path('document/wps/preview-config/', wps_preview_config, name='wps_preview_config'),
    path('document/wps/edit-config/', wps_edit_config, name='wps_edit_config'),
    # WPS init方式配置接口（官方推荐）
    path('documents/<int:documentId>/wps/init-config/', wps_init_config, name='wps_init_config'),
    path('document/wps/file/<int:document_id>/', wps_get_file, name='wps_get_file'),
    path('document/wps/save/<int:document_id>/', wps_save_document, name='wps_save_document'),
    path('document/wps/callback/', wps_callback, name='wps_callback'),
    path('document/wps/download/<int:document_id>/', wps_download_document, name='wps_download_document'),
    # WPS回调服务接口（符合WPS官方规范）
    path('v3/3rd/files/<int:file_id>/download', wps_get_file_download_url, name='wps_get_file_download_url'),
    path('v3/3rd/files/<int:file_id>', wps_get_file_info, name='wps_get_file_info'),
    path('v3/3rd/files/<int:file_id>/permission', wps_get_file_permission, name='wps_get_file_permission'),
    # 单阶段提交接口（已弃用，但保持兼容）
    path('v3/3rd/files/<int:file_id>/upload', wps_save_file, name='wps_save_file'),
    # 三阶段保存接口（WPS官方推荐）
    path('v3/3rd/files/<int:file_id>/upload/prepare', wps_upload_prepare, name='wps_upload_prepare'),
    path('v3/3rd/files/<int:file_id>/upload/', wps_upload_get_url, name='wps_upload_get_url'),
    path('v3/3rd/files/<int:file_id>/upload/address', wps_upload_get_url, name='wps_upload_get_url_address'),  # WPS官方路径
    path('v3/3rd/files/<int:file_id>/upload/temp', wps_upload_temp, name='wps_upload_temp'),
    path('v3/3rd/files/<int:file_id>/upload/commit', wps_upload_commit, name='wps_upload_commit'),
    path('v3/3rd/files/<int:file_id>/upload/complete', wps_upload_commit, name='wps_upload_commit_complete'),  # WPS官方路径
    # 扩展能力接口（智能文档/多维表格）
    path('v3/3rd/object/<str:key>', wps_upload_object, name='wps_upload_object'),
    path('v3/3rd/object/<str:key>/url', wps_get_object_url, name='wps_get_object_url'),
    path('v3/3rd/object/copy', wps_copy_object, name='wps_copy_object'),
    path('v3/3rd/files/<int:file_id>/name', wps_rename_file, name='wps_rename_file'),
    path('v3/3rd/files/<int:file_id>/watermark', wps_get_file_watermark, name='wps_get_file_watermark'),
    path('v3/3rd/users', wps_get_users, name='wps_get_users'),
    # WPS事件通知接口
    path('v3/3rd/notify', wps_notify, name='wps_notify'),
    # WPS直接访问路由（推荐方式）
    path('office/<str:office_type>/<str:file_id>/', wps_office_view, name='wps_office_view'),
]
