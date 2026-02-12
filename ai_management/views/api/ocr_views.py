"""
OCR 识别接口
"""
import logging
import traceback
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from ai_management.services.ocr_service import TencentOCRService

logger = logging.getLogger(__name__)


class OCRViewSet(CustomModelViewSet):
    """OCR 识别视图集"""

    queryset = None
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser]
    swagger_schema = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.ocr_service = TencentOCRService()
            logger.info("OCR 服务初始化成功")
        except Exception as exc:
            logger.error(f"OCR 服务初始化失败: {exc}")
            logger.error(traceback.format_exc())
            self.ocr_service = None

    @action(detail=False, methods=['post'], url_path='business-card')
    def business_card(self, request):
        """
        名片识别
        POST /api/ai/ocr/business-card/
        """
        try:
            if not self.ocr_service:
                return ErrorResponse(msg="OCR 服务不可用", code=500)

            image_file = request.FILES.get('image')
            if not image_file:
                return ErrorResponse(msg="请上传图片文件（字段名：image）", code=400)

            result = self.ocr_service.recognize_business_card(image_file)
            if not result.get("success"):
                logger.error(f"名片OCR识别失败: {result}")
                return ErrorResponse(msg=result.get("error", "识别失败"), code=500)

            return DetailResponse(data=result, msg="识别成功")
        except Exception as exc:
            logger.error(f"名片识别失败: {exc}")
            logger.error(traceback.format_exc())
            return ErrorResponse(msg=f"名片识别失败: {str(exc)}", code=500)

    @action(detail=False, methods=['post'], url_path='general')
    def general(self, request):
        """
        通用文字识别
        POST /api/ai/ocr/general/
        """
        try:
            if not self.ocr_service:
                return ErrorResponse(msg="OCR 服务不可用", code=500)

            image_file = request.FILES.get('image')
            if not image_file:
                return ErrorResponse(msg="请上传图片文件（字段名：image）", code=400)

            result = self.ocr_service.recognize_general(image_file)
            if not result.get("success"):
                logger.error(f"通用OCR识别失败: {result}")
                return ErrorResponse(msg=result.get("error", "识别失败"), code=500)

            return DetailResponse(data=result, msg="识别成功")
        except Exception as exc:
            logger.error(f"通用识别失败: {exc}")
            logger.error(traceback.format_exc())
            return ErrorResponse(msg=f"通用识别失败: {str(exc)}", code=500)
