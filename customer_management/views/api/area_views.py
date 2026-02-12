from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from dvadmin.system.models import Area
from dvadmin.utils.json_response import SuccessResponse


def _serialize_area(area: Area) -> dict:
    return {
        "id": area.id,
        "areaId": area.code,
        "code": area.code,
        "fullname": area.name,
        "name": area.name,
        "level": area.level,
        "pcode": area.pcode_id,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_area_by_pid(request, pid=None):
    """
    根据 pid 返回子级地区列表，pid=0 返回所有省份
    """
    parent_code = pid
    if not parent_code or parent_code in ("0", ""):
        queryset = Area.objects.filter(enable=True, level=1).order_by("code")
    else:
        queryset = Area.objects.filter(enable=True, pcode_id=parent_code).order_by("code")

    data = [_serialize_area(area) for area in queryset]
    return SuccessResponse(data=data, total=len(data), page=1, limit=len(data))
