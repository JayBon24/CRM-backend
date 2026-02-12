import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def reverse_geocode_by_amap(lng: float, lat: float) -> Optional[dict]:
    """
    使用高德地图 Web 服务进行逆地理编码，将经纬度转换为结构化地址信息。

    返回示例：
    {
        "formatted_address": "广东省深圳市福田区嘉盈华大厦",
        "province": "...",
        "city": "...",
        "district": "...",
        "township": "...",
        "street": "...",
        "street_number": "..."
    }
    """
    try:
        amap_key = getattr(settings, "AMAP_WEB_KEY", None)
        if not amap_key:
            logger.warning("AMAP_WEB_KEY not configured in settings, skip reverse geocoding.")
            return None

        url = "https://restapi.amap.com/v3/geocode/regeo"
        params = {
            "key": amap_key,
            "location": f"{lng},{lat}",
            "extensions": "base",
        }
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "1":
            logger.warning("Amap reverse geocode failed: %s", data)
            return None

        regeocode = data.get("regeocode") or {}
        comp = regeocode.get("addressComponent") or {}
        result = {
            "formatted_address": regeocode.get("formatted_address") or "",
            "province": comp.get("province") or "",
            "city": (comp.get("city") or "") if not isinstance(comp.get("city"), list) else "".join(comp.get("city")),
            "district": comp.get("district") or "",
            "township": comp.get("township") or "",
            "street": comp.get("street") or "",
            "street_number": (comp.get("streetNumber") or {}).get("number", ""),
        }
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("reverse_geocode_by_amap error: %s", exc)
        return None

