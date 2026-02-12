"""
WPS文档处理模块
"""
import os
import shutil
import logging
from datetime import datetime
from typing import Dict, Optional
from django.conf import settings
from django.http import HttpResponse, FileResponse, Http404
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

logger = logging.getLogger(__name__)

from case_management.models import CaseDocument


class WPSDocumentHandler:
    """WPS文档处理类"""
    
    def __init__(self):
        """初始化文档处理器"""
        self.max_file_size = getattr(settings, 'WPS_MAX_FILE_SIZE', 50 * 1024 * 1024)  # 50MB
        self.version_backup_count = getattr(settings, 'WPS_VERSION_BACKUP_COUNT', 5)
        self.version_management_enabled = getattr(
            settings, 'WPS_VERSION_MANAGEMENT_ENABLED', True
        )
    
    def get_document_file(self, document_id: int, user_id: int) -> HttpResponse:
        """
        获取文档文件（用于WPS加载）
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
        
        Returns:
            HttpResponse: 文件响应
        """
        try:
            # 查询文档
            try:
                document = CaseDocument.objects.get(id=document_id, is_deleted=False)
            except CaseDocument.DoesNotExist:
                logger.warning(f"文档不存在: document_id={document_id}")
                raise Http404("文档不存在")
            
            # 检查权限
            if not self.check_document_permission(document_id, user_id, 'read'):
                logger.warning(
                    f"用户无权限访问文档: document_id={document_id}, user_id={user_id}"
                )
                return HttpResponse("无权限访问", status=403)
            
            # 获取文件路径
            file_path = document.full_file_path
            if not file_path or not os.path.exists(file_path):
                logger.error(f"文件不存在: document_id={document_id}, path={file_path}")
                raise Http404("文件不存在")
            
            # 读取文件
            try:
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type=document.mime_type or 
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
                
                # 设置响应头
                filename = document.file_name or document.document_name or 'document.docx'
                response['Content-Disposition'] = f'inline; filename="{filename}"'
                response['Access-Control-Allow-Origin'] = '*'
                response['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'Range'
                # 移除X-Frame-Options响应头，允许在iframe中加载（WPS需要）
                # 使用xframe_options_exempt属性来防止中间件添加X-Frame-Options
                response.xframe_options_exempt = True
                
                # 支持Range请求（断点续传）
                if os.path.getsize(file_path) > 0:
                    response['Accept-Ranges'] = 'bytes'
                
                logger.info(
                    f"提供文档文件: document_id={document_id}, "
                    f"user_id={user_id}, size={os.path.getsize(file_path)}"
                )
                
                return response
                
            except IOError as e:
                logger.error(f"读取文件失败: document_id={document_id}, error={str(e)}", exc_info=True)
                raise Http404("文件读取失败")
            
        except Http404:
            raise
        except Exception as e:
            logger.error(
                f"获取文档文件失败: document_id={document_id}, user_id={user_id}, error={str(e)}",
                exc_info=True
            )
            return HttpResponse(f"获取文件失败: {str(e)}", status=500)
    
    def save_document(
        self, 
        document_id: int, 
        file: UploadedFile, 
        user_id: int
    ) -> Dict:
        """
        保存WPS编辑后的文档
        
        Args:
            document_id: 文档ID
            file: 上传的文件
            user_id: 用户ID
        
        Returns:
            dict: {
                'documentId': int,
                'filePath': str,
                'fileSize': int,
                'version': int
            }
        """
        try:
            # 查询文档
            try:
                document = CaseDocument.objects.get(id=document_id, is_deleted=False)
            except CaseDocument.DoesNotExist:
                logger.warning(f"文档不存在: document_id={document_id}")
                raise ValueError("文档不存在")
            
            # 检查权限
            if not self.check_document_permission(document_id, user_id, 'write'):
                logger.warning(
                    f"用户无权限编辑文档: document_id={document_id}, user_id={user_id}"
                )
                raise PermissionError("无权限编辑文档")
            
            # 验证文件
            if not file.name.lower().endswith('.docx'):
                raise ValueError("只支持.docx格式文件")
            
            if file.size > self.max_file_size:
                raise ValueError(f"文件大小超过限制（最大{self.max_file_size / 1024 / 1024}MB）")
            
            # 使用事务确保数据一致性
            with transaction.atomic():
                # 创建版本备份
                backup_path = None
                if self.version_management_enabled and document.file_path:
                    backup_path = self.create_version_backup(document_id)
                
                # 保存新文件
                file_path = self._save_file(document, file)
                
                # 更新文档信息
                document.file_path = file_path
                document.file_name = file.name
                document.file_size = file.size
                document.file_ext = '.docx'
                document.mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                document.version += 1
                
                # 更新最后编辑信息
                if hasattr(document, 'last_edit_time'):
                    document.last_edit_time = datetime.now()
                if hasattr(document, 'last_editor_id'):
                    document.last_editor_id = user_id
                
                document.save()
                
                logger.info(
                    f"保存WPS文档: document_id={document_id}, user_id={user_id}, "
                    f"size={file.size}, version={document.version}, backup={backup_path}"
                )
                
                return {
                    'documentId': document_id,
                    'filePath': file_path,
                    'fileSize': file.size,
                    'version': document.version,
                    'backupPath': backup_path,
                }
            
        except Exception as e:
            logger.error(
                f"保存WPS文档失败: document_id={document_id}, user_id={user_id}, error={str(e)}",
                exc_info=True
            )
            raise
    
    def update_document_metadata(
        self, 
        document_id: int, 
        user_id: int,
        file_name: str = None,
        file_size: int = None
    ) -> Dict:
        """
        更新文档元数据（用于三阶段保存，文件已上传到存储服务的情况）
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            file_name: 文件名称（可选）
            file_size: 文件大小（可选）
        
        Returns:
            dict: {
                'documentId': int,
                'version': int
            }
        """
        try:
            # 查询文档
            try:
                document = CaseDocument.objects.get(id=document_id, is_deleted=False)
            except CaseDocument.DoesNotExist:
                logger.warning(f"文档不存在: document_id={document_id}")
                raise ValueError("文档不存在")
            
            # 检查权限
            if not self.check_document_permission(document_id, user_id, 'write'):
                logger.warning(
                    f"用户无权限编辑文档: document_id={document_id}, user_id={user_id}"
                )
                raise PermissionError("无权限编辑文档")
            
            # 使用事务确保数据一致性
            with transaction.atomic():
                # 更新文档信息
                if file_name:
                    # 重要：document_name 字段不应该包含扩展名
                    # 扩展名应该单独存储在 file_ext 字段中
                    # 因为文档树的 label 会组合：document_name + file_ext
                    clean_file_name = file_name.strip()
                    
                    # 检查是否已经包含常见的文档扩展名
                    doc_extensions = ['.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.pdf']
                    
                    # 移除扩展名（如果存在）
                    base_name = clean_file_name
                    detected_ext = None
                    for ext in doc_extensions:
                        if clean_file_name.lower().endswith(ext):
                            base_name = clean_file_name[:-len(ext)]
                            detected_ext = ext
                            break
                    
                    # 保存文档名称（不包含扩展名）
                    document.document_name = base_name
                    
                    # 如果检测到扩展名，更新 file_ext（如果文档还没有设置）
                    if detected_ext and (not document.file_ext or document.file_ext != detected_ext):
                        document.file_ext = detected_ext
                    
                    logger.info(
                        f"更新文档名称: document_id={document_id}, "
                        f"input_file_name={file_name}, "
                        f"base_name={base_name}, "
                        f"file_ext={document.file_ext}"
                    )
                if file_size:
                    document.file_size = file_size
                
                # 更新版本号
                document.version += 1
                
                # 更新最后编辑信息
                if hasattr(document, 'last_edit_time'):
                    document.last_edit_time = datetime.now()
                if hasattr(document, 'last_editor_id'):
                    document.last_editor_id = user_id
                
                document.save()
                
                logger.info(
                    f"更新WPS文档元数据: document_id={document_id}, user_id={user_id}, "
                    f"version={document.version}"
                )
                
                return {
                    'documentId': document_id,
                    'version': document.version,
                }
            
        except Exception as e:
            logger.error(
                f"更新WPS文档元数据失败: document_id={document_id}, user_id={user_id}, error={str(e)}",
                exc_info=True
            )
            raise
    
    def create_version_backup(self, document_id: int) -> Optional[str]:
        """
        创建版本备份
        
        Args:
            document_id: 文档ID
        
        Returns:
            str: 备份文件路径，如果失败返回None
        """
        try:
            document = CaseDocument.objects.get(id=document_id)
            
            if not document.file_path:
                return None
            
            original_path = document.full_file_path
            if not original_path or not os.path.exists(original_path):
                return None
            
            # 创建版本目录
            version_dir = os.path.join(
                settings.MEDIA_ROOT,
                'documents',
                'versions',
                str(document_id)
            )
            os.makedirs(version_dir, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"v{document.version}_{timestamp}.docx"
            backup_path = os.path.join(version_dir, backup_filename)
            
            # 复制文件
            shutil.copy2(original_path, backup_path)
            
            # 清理旧版本（保留最近N个版本）
            self._cleanup_old_versions(version_dir)
            
            logger.info(f"创建版本备份: document_id={document_id}, backup={backup_path}")
            
            return backup_path
            
        except Exception as e:
            logger.error(
                f"创建版本备份失败: document_id={document_id}, error={str(e)}",
                exc_info=True
            )
            return None
    
    def _save_file(self, document: CaseDocument, file: UploadedFile) -> str:
        """
        保存文件到指定位置
        
        Args:
            document: 文档对象
            file: 上传的文件
        
        Returns:
            str: 相对路径
        """
        # 生成文件保存路径
        now = datetime.now()
        year_month_dir = now.strftime('%Y/%m')
        
        # 使用案件ID组织目录
        case_id = document.case.id if document.case else 'default'
        file_dir = os.path.join(
            settings.MEDIA_ROOT,
            'cases',
            str(case_id),
            'case_documents',
            year_month_dir
        )
        os.makedirs(file_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        filename = f"{document.id}_{timestamp}.docx"
        file_path = os.path.join(file_dir, filename)
        
        # 保存文件
        with open(file_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
        
        # 返回相对路径
        relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
        return relative_path.replace('\\', '/')
    
    def _cleanup_old_versions(self, version_dir: str) -> None:
        """
        清理旧版本备份
        
        Args:
            version_dir: 版本目录
        """
        try:
            if not os.path.exists(version_dir):
                return
            
            # 获取所有版本文件，按修改时间排序
            files = []
            for filename in os.listdir(version_dir):
                if filename.startswith('v') and filename.endswith('.docx'):
                    file_path = os.path.join(version_dir, filename)
                    mtime = os.path.getmtime(file_path)
                    files.append((mtime, file_path))
            
            # 按修改时间倒序排序（最新的在前）
            files.sort(key=lambda x: x[0], reverse=True)
            
            # 删除超出保留数量的旧版本
            if len(files) > self.version_backup_count:
                for mtime, file_path in files[self.version_backup_count:]:
                    try:
                        os.remove(file_path)
                        logger.info(f"删除旧版本备份: {file_path}")
                    except Exception as e:
                        logger.warning(f"删除旧版本失败: {file_path}, error={str(e)}")
            
        except Exception as e:
            logger.error(f"清理旧版本失败: {str(e)}", exc_info=True)
    
    def check_document_permission(
        self, 
        document_id: int, 
        user_id: int, 
        permission: str = 'read'
    ) -> bool:
        """
        检查文档权限
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            permission: 权限类型，'read', 'write', 'delete'
        
        Returns:
            bool: 是否有权限
        """
        try:
            document = CaseDocument.objects.get(id=document_id, is_deleted=False)
            
            # 基本权限检查：用户是否有权限访问该文档
            # 这里可以根据实际业务逻辑扩展
            # 例如：检查用户是否是该案件的创建者、是否有角色权限等
            
            # 简单实现：检查文档是否启用WPS编辑
            if hasattr(document, 'wps_enabled') and not document.wps_enabled:
                if permission in ['write', 'delete']:
                    return False
            
            # 可以扩展更复杂的权限检查逻辑
            # 例如：检查用户是否属于该案件团队、是否有特定角色等
            
            return True
            
        except CaseDocument.DoesNotExist:
            return False
        except Exception as e:
            logger.error(
                f"检查文档权限失败: document_id={document_id}, user_id={user_id}, "
                f"permission={permission}, error={str(e)}",
                exc_info=True
            )
            return False

