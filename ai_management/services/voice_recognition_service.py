"""
豆包语音识别服务（极速版）
根据官方文档：https://www.volcengine.com/docs/6561/1631584
一次请求即返回识别结果，无需轮询
"""
import base64
import uuid
import logging
import requests
from typing import Dict, Any
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class DoubaoVoiceRecognitionService:
    """豆包语音识别服务（极速版）"""
    
    def __init__(self):
        self.config = getattr(settings, 'DOUBAO_CONFIG', {})
        self.app_id = self.config.get('APP_ID', '')
        self.access_key = self.config.get('ACCESS_KEY', '')
        self.resource_id = self.config.get('RESOURCE_ID', 'volc.bigasr.auc_turbo')  # 极速版资源ID
        self.api_url = self.config.get('API_URL', 'https://openspeech.bytedance.com')
        
        if not all([self.app_id, self.access_key]):
            raise ValueError("豆包API配置不完整，请检查DOUBAO_CONFIG配置（需要APP_ID和ACCESS_KEY）")
    
    def _file_to_base64(self, audio_file: UploadedFile) -> str:
        """
        将音频文件转换为Base64编码
        
        Args:
            audio_file: 上传的音频文件
            
        Returns:
            Base64编码的字符串
        """
        # 读取文件内容
        audio_file.seek(0)  # 确保从文件开头读取
        file_data = audio_file.read()
        
        # 转换为Base64
        base64_data = base64.b64encode(file_data).decode('utf-8')
        return base64_data
    
    def recognize_voice(self, audio_file: UploadedFile) -> Dict[str, Any]:
        """
        语音识别主方法（极速版，一次请求返回结果）
        
        Args:
            audio_file: 上传的音频文件
            
        Returns:
            识别结果字典
        """
        try:
            
            # 验证文件大小（极速版限制100MB，建议20MB以内）
            max_size = self.config.get('MAX_AUDIO_SIZE', 100 * 1024 * 1024)  # 100MB
            if audio_file.size > max_size:
                raise ValueError(f"文件大小超过限制: {audio_file.size} > {max_size}字节（最大{max_size // (1024*1024)}MB）")
            
            # 验证文件格式（极速版支持：WAV / MP3 / OGG OPUS）
            filename = audio_file.name
            file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
            supported_formats = self.config.get('SUPPORTED_FORMATS', ['wav', 'mp3', 'ogg'])
            
            if file_ext not in supported_formats:
                raise ValueError(f"不支持的文件格式: {file_ext}，支持格式: {', '.join(supported_formats)}")
            
            # 将文件转换为Base64
            base64_data = self._file_to_base64(audio_file)
            
            # 构建请求
            url = f"{self.api_url}/api/v3/auc/bigmodel/recognize/flash"
            request_id = str(uuid.uuid4())
            
            headers = {
                'X-Api-App-Key': self.app_id,
                'X-Api-Access-Key': self.access_key,
                'X-Api-Resource-Id': self.resource_id,
                'X-Api-Request-Id': request_id,
                'X-Api-Sequence': '-1',
                'Content-Type': 'application/json',
            }
            
            # 构建请求体
            request_body = {
                'user': {
                    'uid': self.app_id
                },
                'audio': {
                    'data': base64_data  # 使用Base64编码的文件数据
                },
                'request': {
                    'model_name': 'bigmodel',
                    # 可选参数（可根据需要启用）：
                    # 'enable_itn': True,      # 是否启用逆文本规范化
                    # 'enable_punc': True,    # 是否启用标点符号
                    # 'enable_ddc': True,     # 是否启用说话人分离
                    # 'enable_speaker_info': False,  # 是否返回说话人信息
                },
            }
            
            # 发送请求
            response = requests.post(
                url,
                json=request_body,
                headers=headers,
                timeout=self.config.get('RECOGNITION_TIMEOUT', 60)
            )
            response.raise_for_status()
            
            # 检查响应头中的状态码
            status_code = response.headers.get('X-Api-Status-Code', '')
            message = response.headers.get('X-Api-Message', '')
            logid = response.headers.get('X-Tt-Logid', '')
            
            if status_code == '20000000':
                # 识别成功
                result = response.json()
                result_data = result.get('result', {})
                text = result_data.get('text', '')
                
                logger.info(f"语音识别成功，文本长度: {len(text)}, 识别结果: {text}")
                
                return {
                    'success': True,
                    'text': text,
                    'request_id': request_id,
                    'result': result_data,
                    'audio_info': result.get('audio_info', {}),
                    'logid': logid,
                }
            else:
                # 识别失败
                error_msg = message or f'识别失败，状态码: {status_code}'
                logger.error(f"语音识别失败: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'request_id': request_id,
                    'status_code': status_code,
                    'logid': logid,
                }
            
        except Exception as e:
            logger.error(f"语音识别过程出错: {e}")
            return {
                'success': False,
                'error': str(e)
            }
