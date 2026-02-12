"""
WPS Office Web SDK 配置服务模块
"""
import hashlib
import hmac
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from django.conf import settings
from django.urls import reverse
import jwt

logger = logging.getLogger(__name__)


class WPSService:
    """WPS配置服务类"""
    
    def __init__(self):
        """初始化WPS服务"""
        self.app_id = getattr(settings, 'WPS_APP_ID', '')
        self.app_secret = getattr(settings, 'WPS_APP_SECRET', '')
        self.server_url = getattr(settings, 'WPS_SERVER_URL', 'https://wwo.wps.cn')
        self.callback_url = getattr(settings, 'WPS_CALLBACK_URL', '')
        self.file_url_expire = getattr(settings, 'WPS_FILE_URL_EXPIRE', 7200)  # 2小时
        self.token_expire = getattr(settings, 'WPS_TOKEN_EXPIRE', 7200)  # 2小时
        
        # 如果没有配置回调URL，自动生成
        if not self.callback_url:
            from django.contrib.sites.models import Site
            try:
                current_site = Site.objects.get_current()
                protocol = 'https' if not settings.DEBUG else 'http'
                self.callback_url = f"{protocol}://{current_site.domain}/api/case/document/wps/callback/"
            except Exception:
                # 如果无法获取站点信息，使用默认值
                self.callback_url = '/api/case/document/wps/callback/'
    
    def generate_edit_config(
        self, 
        document_id: int, 
        user_id: int, 
        user_name: str = '',
        mode: str = 'edit'
    ) -> Dict:
        """
        生成WPS编辑配置
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            user_name: 用户名
            mode: 模式，'view' 或 'edit'
        
        Returns:
            dict: WPS配置信息
        """
        try:
            # 生成Token
            token = self.generate_token(document_id, user_id, self.token_expire)
            
            # 生成文件URL（带签名）
            file_url = self.generate_signed_url(document_id, user_id, self.file_url_expire)
            
            # 生成保存URL
            save_url = self._get_full_url(f'/api/case/document/wps/save/{document_id}/')
            
            # 生成下载URL
            download_url = self._get_full_url(f'/api/case/document/wps/download/{document_id}/')
            
            # 使用配置的回调URL，如果没有配置则使用默认路径
            if self.callback_url:
                # 如果配置的是完整URL（包含协议），直接使用
                if self.callback_url.startswith('http://') or self.callback_url.startswith('https://'):
                    callback_url = self.callback_url.rstrip('/')
                else:
                    # 如果是相对路径，转换为完整URL
                    callback_url = self._get_full_url(self.callback_url.rstrip('/'))
            else:
                # 默认使用旧的回调接口路径
                callback_url = self._get_full_url('/api/case/document/wps/callback/')
            
            config = {
                'fileUrl': file_url,
                'fileId': str(document_id),
                'appId': self.app_id,
                'token': token,
                'mode': mode,
                'userId': str(user_id),
                'userName': user_name or f'user_{user_id}',
                'callbackUrl': callback_url,
                'saveUrl': save_url,
                'downloadUrl': download_url,
            }
            
            logger.info(
                f"生成WPS配置: document_id={document_id}, user_id={user_id}, mode={mode}"
            )
            
            return config
            
        except Exception as e:
            logger.error(f"生成WPS配置失败: document_id={document_id}, error={str(e)}", exc_info=True)
            raise
    
    def generate_token(
        self, 
        document_id: int, 
        user_id: int, 
        expires_in: int = 7200
    ) -> str:
        """
        生成WPS访问令牌
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            expires_in: 过期时间（秒），默认2小时
        
        Returns:
            str: JWT Token
        """
        try:
            # 如果没有配置密钥，使用app_secret
            secret = self.app_secret or settings.SECRET_KEY
            
            # 生成JWT Token
            payload = {
                'document_id': document_id,
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(seconds=expires_in),
                'iat': datetime.utcnow(),
            }
            
            token = jwt.encode(payload, secret, algorithm='HS256')
            
            # jwt.encode返回的是字符串（PyJWT 2.0+）
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            
            return token
            
        except Exception as e:
            logger.error(
                f"生成WPS Token失败: document_id={document_id}, user_id={user_id}, error={str(e)}",
                exc_info=True
            )
            raise
    
    def verify_token(self, token: str) -> Dict:
        """
        验证WPS令牌
        
        Args:
            token: JWT Token
        
        Returns:
            dict: {
                'valid': bool,
                'document_id': int,
                'user_id': int,
                'expires_at': datetime
            }
        """
        try:
            secret = self.app_secret or settings.SECRET_KEY
            
            # 解码Token
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            
            return {
                'valid': True,
                'document_id': payload.get('document_id'),
                'user_id': payload.get('user_id'),
                'expires_at': datetime.utcfromtimestamp(payload.get('exp', 0)),
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"WPS Token已过期: {token[:20]}...")
            return {
                'valid': False,
                'error': 'token_expired',
            }
        except jwt.InvalidTokenError as e:
            logger.warning(f"WPS Token无效: {str(e)}")
            return {
                'valid': False,
                'error': 'token_invalid',
            }
        except Exception as e:
            logger.error(f"验证WPS Token失败: {str(e)}", exc_info=True)
            return {
                'valid': False,
                'error': 'token_verify_error',
            }
    
    def generate_signed_url(
        self, 
        document_id: int, 
        user_id: int,
        expires_in: int = 7200
    ) -> str:
        """
        生成带签名的文档URL
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            expires_in: 过期时间（秒），默认2小时
        
        Returns:
            str: 带签名的完整URL
        """
        try:
            # 生成时间戳
            timestamp = int(time.time())
            expire_time = timestamp + expires_in
            
            # 生成签名
            message = f"{document_id}_{user_id}_{expire_time}"
            secret = self.app_secret or settings.SECRET_KEY
            signature = hmac.new(
                secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # 构建URL
            base_url = self._get_full_url(f'/api/case/document/wps/file/{document_id}/')
            url = f"{base_url}?expires={expire_time}&signature={signature}&user_id={user_id}"
            
            return url
            
        except Exception as e:
            logger.error(
                f"生成签名URL失败: document_id={document_id}, error={str(e)}",
                exc_info=True
            )
            raise
    
    def verify_url_signature(
        self, 
        document_id: int, 
        user_id: int,
        expires: int, 
        signature: str
    ) -> bool:
        """
        验证URL签名
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            expires: 过期时间戳
            signature: 签名
        
        Returns:
            bool: 签名是否有效
        """
        try:
            # 检查是否过期
            current_time = int(time.time())
            if expires < current_time:
                logger.warning(f"URL已过期: document_id={document_id}, expires={expires}")
                return False
            
            # 重新生成签名进行验证
            message = f"{document_id}_{user_id}_{expires}"
            secret = self.app_secret or settings.SECRET_KEY
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # 使用compare_digest防止时序攻击
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                logger.warning(
                    f"URL签名验证失败: document_id={document_id}, "
                    f"expected={expected_signature[:16]}..., got={signature[:16]}..."
                )
            
            return is_valid
            
        except Exception as e:
            logger.error(f"验证URL签名失败: {str(e)}", exc_info=True)
            return False
    
    def _get_full_url(self, path: str) -> str:
        """
        获取完整URL
        
        Args:
            path: 相对路径
        
        Returns:
            str: 完整URL
        """
        try:
            from django.contrib.sites.models import Site
            current_site = Site.objects.get_current()
            protocol = 'https' if not settings.DEBUG else 'http'
            return f"{protocol}://{current_site.domain}{path}"
        except Exception:
            # 如果无法获取站点信息，返回相对路径
            return path
    
    def verify_wps2_signature(
        self,
        method: str,
        uri: str,
        query_string: str,
        headers: Dict,
        body: str = ''
    ) -> bool:
        """
        验证WPS-2签名算法
        
        Args:
            method: HTTP方法（GET, POST等）
            uri: 请求URI（不包含查询参数）
            query_string: 查询参数字符串
            headers: 请求头字典
            body: 请求体（POST请求）
        
        Returns:
            bool: 签名是否有效
        """
        try:
            # 获取签名
            authorization = headers.get('Authorization', '')
            if not authorization:
                return False
            
            # 获取AppId
            app_id = headers.get('X-App-Id', '')
            if app_id != self.app_id:
                return False
            
            # TODO: 实现WPS-2签名验证算法
            # 根据WPS官方文档实现完整的签名验证
            # 参考：https://solution.wps.cn/docs/callback/gateway.html
            
            # 基本验证：检查AppId是否匹配
            # 生产环境需要实现完整的签名验证
            
            # 开发环境可以跳过详细验证
            if settings.DEBUG:
                logger.warning("开发环境：跳过WPS-2签名详细验证")
                return True
            
            # 生产环境需要实现完整验证
            # 这里需要根据WPS官方文档实现签名算法
            # 1. 构建签名字符串
            # 2. 使用AppSecret计算HMAC-SHA256
            # 3. 与Authorization头中的签名对比
            
            return True
            
        except Exception as e:
            logger.error(f"验证WPS-2签名失败: {str(e)}", exc_info=True)
            return False

