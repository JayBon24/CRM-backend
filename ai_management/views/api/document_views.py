"""
文档生成视图（控制器）
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from ai_management.serializers import (
    DocumentGenerateSerializer,
    DocumentGenerateResponseSerializer,
    DocumentExtractSerializer,
)
from ai_management.services.document_service import DocumentGeneratorService
from ai_management.services.document_extract_service import DocumentExtractService


class DocumentViewSet(CustomModelViewSet):
    """文档生成视图集"""
    
    # 添加空的 queryset 以满足 DRF 要求（此 ViewSet 不使用数据库模型）
    queryset = None
    permission_classes = []
    
    # 禁用 Swagger 文档生成（避免因无 queryset 导致错误）
    swagger_schema = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document_service = DocumentGeneratorService()
        self.extract_service = DocumentExtractService()
    
    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """
        生成文档接口
        
        POST /api/ai/document/generate/
        """
        serializer = DocumentGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            document_type = serializer.validated_data.get('document_type')
            case_id = serializer.validated_data.get('case_id')
            template_id = serializer.validated_data.get('template_id')
            case_data = serializer.validated_data.get('case_data')
            
            # 调用服务层
            result = self.document_service.generate_document(
                document_type=document_type,
                case_id=case_id,
                template_id=template_id,
                case_data=case_data
            )
            
            return DetailResponse(data=result)
            
        except Exception as e:
            return ErrorResponse(msg=f"文档生成失败: {str(e)}")

    @action(detail=False, methods=['post'], url_path='extract')
    def extract(self, request):
        """
        Extract text from document or image.
        POST /api/ai/document/extract/
        """
        serializer = DocumentExtractSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = serializer.validated_data
            result = self.extract_service.extract(
                url=data.get('url'),
                file_name=data.get('file_name'),
                force_ocr=data.get('force_ocr', False),
                ocr_all_pages=data.get('ocr_all_pages', False),
                ocr_page_limit=data.get('ocr_page_limit', 0),
            )
            return DetailResponse(data=result)
        except Exception as e:
            return ErrorResponse(msg=f"文档解析失败: {str(e)}")

