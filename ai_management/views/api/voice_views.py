"""
语音识别视图（控制器）
使用极速版API，一次请求返回结果
"""
import logging
import traceback
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from ai_management.services.voice_recognition_service import DoubaoVoiceRecognitionService

logger = logging.getLogger(__name__)


class VoiceRecognitionViewSet(CustomModelViewSet):
    """语音识别视图集（极速版）"""
    
    # 添加空的 queryset 以满足 DRF 要求（此 ViewSet 不使用数据库模型）
    queryset = None
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser]  # 支持文件上传
    
    # 禁用 Swagger 文档生成（避免因无 queryset 导致错误）
    swagger_schema = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.voice_service = DoubaoVoiceRecognitionService()
            logger.info("语音识别服务初始化成功")
        except ValueError as e:
            logger.warning(f"语音识别服务初始化失败: {e}")
            self.voice_service = None
        except Exception as e:
            logger.error(f"语音识别服务初始化异常: {e}")
            logger.error(traceback.format_exc())
            self.voice_service = None
    
    @action(detail=False, methods=['post'], url_path='recognize')
    def recognize(self, request):
        """
        语音识别接口（极速版）
        
        POST /api/ai/voice/recognize/
        
        请求参数:
        - audio: 音频文件 (multipart/form-data)
          支持格式：WAV / MP3 / OGG OPUS
          文件大小：建议20MB以内，最大100MB
          音频时长：不超过2小时
        
        返回:
        {
            "code": 2000,
            "msg": "识别成功",
            "data": {
                "text": "识别出的文本内容",
                "request_id": "任务ID",
                "result": {
                    "text": "完整文本",
                    "utterances": [...]
                },
                "audio_info": {
                    "duration": "音频时长（毫秒）"
                },
                "logid": "日志ID"
            }
        }
        """
        try:
            # 检查服务是否可用
            if not self.voice_service:
                logger.error("语音识别服务未初始化")
                return ErrorResponse(msg="语音识别服务未配置，请检查DOUBAO_CONFIG配置", code=500)
            
            # 获取上传的音频文件
            logger.info(f"请求方法: {request.method}, Content-Type: {request.content_type}")
            logger.info(f"request.FILES keys: {list(request.FILES.keys())}")
            logger.info(f"request.data keys: {list(request.data.keys()) if hasattr(request, 'data') else 'N/A'}")
            
            audio_file = request.FILES.get('audio')
            if not audio_file:
                logger.warning("未找到音频文件，request.FILES内容:")
                for key, value in request.FILES.items():
                    logger.warning(f"  {key}: {type(value)}")
                return ErrorResponse(msg="请上传音频文件（字段名：audio）", code=400)
            
            logger.info(f"收到语音识别请求（极速版），文件: {audio_file.name}, 大小: {audio_file.size}, 类型: {audio_file.content_type}")
            
            # 执行语音识别（极速版：直接Base64编码上传，一次请求返回结果）
            result = self.voice_service.recognize_voice(audio_file)
            
            if result.get('success'):
                text = result.get('text', '')
                logger.info(f"语音识别成功，文本长度: {len(text)}, 识别结果: {text}")
                return DetailResponse(
                    data={
                        'text': result.get('text', ''),
                        'request_id': result.get('request_id'),
                        'result': result.get('result', {}),
                        'audio_info': result.get('audio_info', {}),
                        'logid': result.get('logid'),
                    },
                    msg="语音识别成功"
                )
            else:
                error_msg = result.get('error', '语音识别失败')
                logger.error(f"语音识别失败: {error_msg}")
                return ErrorResponse(
                    msg=error_msg,
                    code=500
                )
                
        except Exception as e:
            logger.error(f"语音识别API出错: {e}")
            logger.error(traceback.format_exc())
            return ErrorResponse(msg=f"语音识别失败: {str(e)}", code=500)

