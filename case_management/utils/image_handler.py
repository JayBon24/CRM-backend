"""
图片处理模块
处理图片上传、压缩、URL生成等
"""
import os
import uuid
import logging
from typing import Dict, Optional, Tuple
from io import BytesIO
from urllib.parse import urlparse
import requests
from PIL import Image
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class ImageHandler:
    """图片处理器"""
    
    # 允许的图片格式
    ALLOWED_FORMATS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
    
    # 最大文件大小（5MB）
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # 最大图片尺寸（1920px）
    MAX_IMAGE_SIZE = 1920
    
    def __init__(self):
        """初始化图片处理器"""
        self.media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        self.image_base_dir = os.path.join(self.media_root, 'images', 'documents')
        os.makedirs(self.image_base_dir, exist_ok=True)
    
    def upload_image(self, file: UploadedFile, document_id: Optional[int] = None) -> Dict:
        """
        上传图片
        
        Args:
            file: 上传的文件对象
            document_id: 文档ID（可选，用于关联）
        
        Returns:
            {
                'url': str,
                'path': str,
                'size': int,
                'width': int,
                'height': int
            }
        """
        try:
            # 校验图片
            if not self.validate_image(file):
                raise ValueError("图片格式或大小不符合要求")
            
            # 读取文件内容
            file_content = file.read()
            file_size = len(file_content)
            
            # 打开图片获取信息
            image = Image.open(BytesIO(file_content))
            width, height = image.size
            
            # 压缩图片（如果过大）
            if width > self.MAX_IMAGE_SIZE or height > self.MAX_IMAGE_SIZE:
                image = self.compress_image(image, self.MAX_IMAGE_SIZE)
                width, height = image.size
                
                # 重新编码
                output = BytesIO()
                format = self._get_format(file.name)
                image.save(output, format=format, quality=85, optimize=True)
                file_content = output.getvalue()
                file_size = len(file_content)
            
            # 生成唯一文件名
            filename = self._generate_filename(file.name)
            file_path = os.path.join(self.image_base_dir, filename)
            
            # 按年月组织目录
            from datetime import datetime
            now = datetime.now()
            year_month = now.strftime('%Y/%m')
            file_dir = os.path.join(self.image_base_dir, year_month)
            os.makedirs(file_dir, exist_ok=True)
            
            file_path = os.path.join(file_dir, filename)
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # 生成URL
            url = f"/media/images/documents/{year_month}/{filename}"
            
            return {
                'url': url,
                'path': os.path.relpath(file_path, self.media_root),
                'size': file_size,
                'width': width,
                'height': height,
                'filename': filename
            }
            
        except Exception as e:
            logger.error(f"上传图片失败: {e}", exc_info=True)
            raise
    
    def validate_image(self, file: UploadedFile) -> bool:
        """
        校验图片文件
        
        Args:
            file: 文件对象
        
        Returns:
            是否有效
        """
        try:
            # 检查文件大小
            if file.size > self.MAX_FILE_SIZE:
                logger.warning(f"图片文件过大: {file.size} bytes")
                return False
            
            # 检查文件扩展名
            ext = self._get_format(file.name)
            if ext not in self.ALLOWED_FORMATS:
                logger.warning(f"不支持的图片格式: {ext}")
                return False
            
            # 尝试打开图片
            file.seek(0)
            try:
                image = Image.open(file)
                image.verify()  # 验证图片完整性
                file.seek(0)  # 重置文件指针
                return True
            except Exception as e:
                logger.warning(f"图片验证失败: {e}")
                return False
            
        except Exception as e:
            logger.error(f"校验图片失败: {e}")
            return False
    
    def compress_image(self, image: Image.Image, max_size: int = 1920) -> Image.Image:
        """
        压缩图片
        
        Args:
            image: PIL Image对象
            max_size: 最大尺寸（像素）
        
        Returns:
            压缩后的Image对象
        """
        try:
            width, height = image.size
            
            # 计算缩放比例
            if width <= max_size and height <= max_size:
                return image
            
            if width > height:
                new_width = max_size
                new_height = int(height * max_size / width)
            else:
                new_height = max_size
                new_width = int(width * max_size / height)
            
            # 调整尺寸
            compressed_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return compressed_image
            
        except Exception as e:
            logger.error(f"压缩图片失败: {e}", exc_info=True)
            return image
    
    def get_image_url(self, image_path: str) -> str:
        """
        生成图片URL
        
        Args:
            image_path: 图片路径（相对或绝对）
        
        Returns:
            图片URL
        """
        try:
            if os.path.isabs(image_path):
                # 绝对路径，转换为相对路径
                relative_path = os.path.relpath(image_path, self.media_root)
            else:
                relative_path = image_path
            
            # 生成URL
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            if not media_url.endswith('/'):
                media_url += '/'
            
            return f"{media_url}{relative_path}"
            
        except Exception as e:
            logger.error(f"生成图片URL失败: {e}")
            return ""
    
    def download_remote_image(self, url: str) -> Optional[bytes]:
        """
        下载远程图片（HTML中的网络图片）
        
        Args:
            url: 图片URL
        
        Returns:
            图片字节流，失败返回None
        """
        try:
            response = requests.get(url, timeout=10, stream=True)
            if response.status_code == 200:
                # 检查Content-Type
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"URL不是图片: {url}")
                    return None
                
                # 检查大小
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > self.MAX_FILE_SIZE:
                    logger.warning(f"远程图片过大: {url}")
                    return None
                
                return response.content
            else:
                logger.warning(f"下载远程图片失败: {url}, 状态码: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"下载远程图片失败: {url}, 错误: {e}")
            return None
    
    def _generate_filename(self, original_filename: str) -> str:
        """生成唯一文件名"""
        ext = self._get_format(original_filename)
        unique_id = str(uuid.uuid4())
        return f"{unique_id}.{ext}"
    
    def _get_format(self, filename: str) -> str:
        """获取文件格式"""
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        if ext == 'jpeg':
            ext = 'jpg'
        return ext

