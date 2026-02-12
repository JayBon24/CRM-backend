"""
WPS回调处理模块
"""
import json
import logging
from typing import Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class WPSCallbackHandler:
    """WPS回调处理类"""
    
    def __init__(self):
        """初始化回调处理器"""
        self.app_secret = getattr(settings, 'WPS_APP_SECRET', '')
    
    def handle_callback(self, callback_data: Dict) -> Dict:
        """
        处理WPS回调
        
        Args:
            callback_data: 回调数据
        
        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        try:
            event_type = callback_data.get('event', '')
            file_id = callback_data.get('fileId', '')
            user_id = callback_data.get('userId', '')
            
            logger.info(
                f"处理WPS回调: event={event_type}, file_id={file_id}, user_id={user_id}"
            )
            
            # 根据事件类型处理
            if event_type == 'file_save':
                self.handle_file_save(file_id, callback_data.get('data', {}))
            elif event_type == 'file_close':
                self.handle_file_close(file_id, callback_data.get('data', {}))
            elif event_type == 'file_error':
                self.handle_file_error(file_id, callback_data.get('data', {}))
            else:
                logger.warning(f"未知的WPS回调事件类型: {event_type}")
            
            return {
                'success': True,
                'message': '回调处理成功'
            }
            
        except Exception as e:
            logger.error(
                f"处理WPS回调失败: callback_data={callback_data}, error={str(e)}",
                exc_info=True
            )
            return {
                'success': False,
                'message': f'回调处理失败: {str(e)}'
            }
    
    def handle_file_save(self, file_id: str, event_data: Dict) -> None:
        """
        处理文件保存事件
        
        Args:
            file_id: WPS文件ID
            event_data: 事件数据
        """
        try:
            document_id = int(file_id) if file_id.isdigit() else None
            if not document_id:
                logger.warning(f"无效的文件ID: {file_id}")
                return
            
            # 这里可以记录保存事件，触发自动备份等
            logger.info(
                f"文件保存事件: file_id={file_id}, document_id={document_id}, "
                f"data={event_data}"
            )
            
            # 可以在这里实现自动备份、通知等逻辑
            # 例如：触发版本备份、发送通知等
            
        except Exception as e:
            logger.error(
                f"处理文件保存事件失败: file_id={file_id}, error={str(e)}",
                exc_info=True
            )
    
    def handle_file_close(self, file_id: str, event_data: Dict) -> None:
        """
        处理文件关闭事件
        
        Args:
            file_id: WPS文件ID
            event_data: 事件数据
        """
        try:
            document_id = int(file_id) if file_id.isdigit() else None
            if not document_id:
                logger.warning(f"无效的文件ID: {file_id}")
                return
            
            logger.info(
                f"文件关闭事件: file_id={file_id}, document_id={document_id}, "
                f"data={event_data}"
            )
            
            # 这里可以清理临时文件、更新编辑记录状态等
            # 例如：更新编辑记录状态为completed、清理临时文件等
            
        except Exception as e:
            logger.error(
                f"处理文件关闭事件失败: file_id={file_id}, error={str(e)}",
                exc_info=True
            )
    
    def handle_file_error(self, file_id: str, event_data: Dict) -> None:
        """
        处理文件错误事件
        
        Args:
            file_id: WPS文件ID
            event_data: 事件数据
        """
        try:
            document_id = int(file_id) if file_id.isdigit() else None
            if not document_id:
                logger.warning(f"无效的文件ID: {file_id}")
                return
            
            error_message = event_data.get('error', '未知错误')
            
            logger.error(
                f"文件错误事件: file_id={file_id}, document_id={document_id}, "
                f"error={error_message}, data={event_data}"
            )
            
            # 这里可以记录错误日志、发送告警等
            # 例如：记录到错误日志表、发送邮件通知等
            
        except Exception as e:
            logger.error(
                f"处理文件错误事件失败: file_id={file_id}, error={str(e)}",
                exc_info=True
            )
    
    def verify_callback_signature(
        self, 
        callback_data: Dict, 
        signature: str
    ) -> bool:
        """
        验证回调签名
        
        Args:
            callback_data: 回调数据
            signature: 签名
        
        Returns:
            bool: 签名是否有效
        """
        try:
            # 如果没有配置密钥，跳过签名验证
            if not self.app_secret:
                logger.warning("未配置WPS_APP_SECRET，跳过签名验证")
                return True
            
            # 构建签名字符串
            # 根据WPS实际签名规则实现
            # 这里提供基本实现示例
            import hashlib
            import hmac
            
            # 将回调数据转换为字符串（按特定规则排序）
            data_str = json.dumps(callback_data, sort_keys=True, ensure_ascii=False)
            
            # 生成签名
            expected_signature = hmac.new(
                self.app_secret.encode('utf-8'),
                data_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # 验证签名
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                logger.warning(
                    f"回调签名验证失败: expected={expected_signature[:16]}..., "
                    f"got={signature[:16]}..."
                )
            
            return is_valid
            
        except Exception as e:
            logger.error(
                f"验证回调签名失败: error={str(e)}",
                exc_info=True
            )
            return False

