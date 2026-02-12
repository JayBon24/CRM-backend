from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from customer_management.services.geo_service import reverse_geocode_by_amap


class ReverseGeocodeView(APIView):
    """
    代理高德逆地理编码接口，隐藏后端的 AMAP_WEB_KEY。

    GET /api/customer/geo/reverse?lng=114.057865&lat=22.543096
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            lng = float(request.query_params.get("lng", ""))
            lat = float(request.query_params.get("lat", ""))
        except (TypeError, ValueError):
            return Response({"detail": "参数 lng/lat 无效"}, status=400)

        data = reverse_geocode_by_amap(lng, lat)
        if not data:
            return Response({"detail": "逆地理编码失败"}, status=502)

        return Response(
            {
                "formatted_address": data.get("formatted_address", ""),
                "province": data.get("province", ""),
                "city": data.get("city", ""),
                "district": data.get("district", ""),
                "township": data.get("township", ""),
                "street": data.get("street", ""),
                "street_number": data.get("street_number", ""),
            }
        )

