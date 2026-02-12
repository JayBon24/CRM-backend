"""
检索视图（控制器）
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from ai_management.serializers import RegulationSearchSerializer, LegalSearchSerializer
from ai_management.services.search_service import SearchService


class SearchViewSet(ViewSet):
    """检索视图集"""
    
    permission_classes = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_service = SearchService()
    
    @action(detail=False, methods=['post'], url_path='regulation')
    def regulation_search(self, request):
        """
        法规检索接口
        
        POST /api/ai/search/regulation/
        """
        serializer = RegulationSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            query = serializer.validated_data.get('query')
            category = serializer.validated_data.get('category')
            
            # 调用服务层
            result = self.search_service.regulation_search(
                query=query,
                category=category
            )
            
            return DetailResponse(data=result)
            
        except Exception as e:
            return ErrorResponse(msg=f"法规检索失败: {str(e)}")
    
    @action(detail=False, methods=['post'], url_path='legal')
    def legal_search(self, request):
        """
        法律检索接口
        
        POST /api/ai/search/legal/
        """
        serializer = LegalSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            query = serializer.validated_data.get('query')
            search_type = serializer.validated_data.get('search_type')
            
            # 调用服务层
            result = self.search_service.legal_search(
                query=query,
                search_type=search_type
            )
            
            return DetailResponse(data=result)
            
        except Exception as e:
            return ErrorResponse(msg=f"法律检索失败: {str(e)}")

