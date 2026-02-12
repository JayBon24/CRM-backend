"""
文档文件管理模块
处理文档文件的读写、路径管理、临时文件等
"""
import os
import shutil
import tempfile
import logging
from typing import Optional
from datetime import datetime
from django.conf import settings
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


class DocumentFileManager:
    """文档文件管理器"""
    
    def __init__(self):
        """初始化文件管理器"""
        self.media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        self.document_base_dir = os.path.join(self.media_root, 'documents')
        self.temp_dir = os.path.join(self.media_root, 'temp')
        
        # 确保目录存在
        os.makedirs(self.document_base_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def get_document_path(self, document_id: int, filename: Optional[str] = None) -> str:
        """
        获取文档路径
        
        Args:
            document_id: 文档ID
            filename: 文件名（可选）
        
        Returns:
            文档路径
        """
        # 按年月组织目录
        now = datetime.now()
        year_month = now.strftime('%Y/%m')
        doc_dir = os.path.join(self.document_base_dir, 'original', year_month)
        os.makedirs(doc_dir, exist_ok=True)
        
        if filename:
            return os.path.join(doc_dir, filename)
        else:
            # 生成文件名
            timestamp = now.strftime('%Y%m%d%H%M%S')
            return os.path.join(doc_dir, f"{document_id}_{timestamp}.docx")
    
    def save_document(self, file_content: bytes, document_id: int, 
                     filename: Optional[str] = None) -> str:
        """
        保存文档
        
        Args:
            file_content: 文件内容（字节）
            document_id: 文档ID
            filename: 文件名（可选）
        
        Returns:
            保存的文件路径（相对于MEDIA_ROOT）
        """
        try:
            file_path = self.get_document_path(document_id, filename)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 写入文件
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # 返回相对路径
            return os.path.relpath(file_path, self.media_root)
            
        except Exception as e:
            logger.error(f"保存文档失败: {e}", exc_info=True)
            raise
    
    def create_temp_file(self, suffix: str = '.docx', prefix: str = 'doc_') -> str:
        """
        创建临时文件
        
        Args:
            suffix: 文件扩展名
            prefix: 文件前缀
        
        Returns:
            临时文件路径
        """
        try:
            fd, temp_path = tempfile.mkstemp(
                suffix=suffix,
                prefix=prefix,
                dir=self.temp_dir
            )
            os.close(fd)
            return temp_path
        except Exception as e:
            logger.error(f"创建临时文件失败: {e}", exc_info=True)
            raise
    
    def cleanup_temp_files(self, max_age_seconds: int = 3600) -> int:
        """
        清理临时文件
        
        Args:
            max_age_seconds: 最大存活时间（秒），默认1小时
        
        Returns:
            清理的文件数量
        """
        cleaned_count = 0
        current_time = datetime.now().timestamp()
        
        try:
            if not os.path.exists(self.temp_dir):
                return 0
            
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                
                try:
                    if os.path.isfile(file_path):
                        file_mtime = os.path.getmtime(file_path)
                        age = current_time - file_mtime
                        
                        if age > max_age_seconds:
                            os.remove(file_path)
                            cleaned_count += 1
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {file_path}, {e}")
                    continue
            
            logger.info(f"清理了 {cleaned_count} 个临时文件")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}", exc_info=True)
            return cleaned_count
    
    def create_version_backup(self, document_id: int, file_path: str, 
                             version_number: Optional[int] = None) -> str:
        """
        创建版本备份
        
        Args:
            document_id: 文档ID
            file_path: 原文件路径
            version_number: 版本号（可选，不提供则自动递增）
        
        Returns:
            备份文件路径
        """
        try:
            # 版本目录
            version_dir = os.path.join(self.document_base_dir, 'versions', str(document_id))
            os.makedirs(version_dir, exist_ok=True)
            
            # 确定版本号
            if version_number is None:
                existing_versions = [f for f in os.listdir(version_dir) if f.startswith('v') and f.endswith('.docx')]
                if existing_versions:
                    max_version = max([int(f[1:-5]) for f in existing_versions])
                    version_number = max_version + 1
                else:
                    version_number = 1
            
            # 备份文件名
            backup_filename = f"v{version_number}.docx"
            backup_path = os.path.join(version_dir, backup_filename)
            
            # 复制文件
            if os.path.exists(file_path):
                shutil.copy2(file_path, backup_path)
                logger.info(f"创建版本备份: {backup_path}")
                return backup_path
            else:
                logger.warning(f"原文件不存在，无法创建备份: {file_path}")
                return ""
            
        except Exception as e:
            logger.error(f"创建版本备份失败: {e}", exc_info=True)
            raise
    
    def get_document_file_size(self, file_path: str) -> int:
        """获取文件大小"""
        try:
            if os.path.isabs(file_path):
                full_path = file_path
            else:
                full_path = os.path.join(self.media_root, file_path)
            
            if os.path.exists(full_path):
                return os.path.getsize(full_path)
            return 0
        except Exception as e:
            logger.error(f"获取文件大小失败: {e}")
            return 0
    
    def delete_document_file(self, file_path: str) -> bool:
        """删除文档文件"""
        try:
            if os.path.isabs(file_path):
                full_path = file_path
            else:
                full_path = os.path.join(self.media_root, file_path)
            
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"删除文档文件: {full_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除文档文件失败: {e}", exc_info=True)
            return False
    
    def ensure_directory(self, directory_path: str) -> str:
        """确保目录存在"""
        try:
            if not os.path.isabs(directory_path):
                directory_path = os.path.join(self.media_root, directory_path)
            
            os.makedirs(directory_path, exist_ok=True)
            return directory_path
        except Exception as e:
            logger.error(f"创建目录失败: {e}", exc_info=True)
            raise

