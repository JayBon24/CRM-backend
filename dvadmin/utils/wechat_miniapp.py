import base64
import json
import os
import time
from typing import Optional, Dict

import requests
from django.core.cache import cache
from django.conf import settings
from dvadmin.utils.validator import CustomValidationError

try:
    from Crypto.Cipher import AES
except ImportError:
    try:
        from Cryptodome.Cipher import AES
    except ImportError:
        AES = None


WECHAT_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
SESSION_KEY_TTL = 10 * 60


def _get_setting(name: str, default: str = "") -> str:
    env_val = os.getenv(name)
    if env_val is not None and str(env_val).strip() != "":
        return str(env_val).strip()
    return str(getattr(settings, name, default) or "").strip()


def _get_appid_secret():
    appid = _get_setting("WECHAT_MINIAPP_APPID", "")
    secret = _get_setting("WECHAT_MINIAPP_SECRET", "")
    if not appid or not secret:
        raise CustomValidationError("微信登录未配置")
    return appid, secret


def code2session(code: str) -> Dict[str, str]:
    if not code:
        raise CustomValidationError("code 不能为空")
    appid, secret = _get_appid_secret()
    params = {
        "appid": appid,
        "secret": secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    resp = requests.get(WECHAT_CODE2SESSION_URL, params=params, timeout=10)
    data = resp.json() if resp.content else {}
    if data.get("errcode"):
        raise CustomValidationError(data.get("errmsg", "微信登录失败"))
    openid = data.get("openid")
    session_key = data.get("session_key")
    unionid = data.get("unionid")
    if not openid or not session_key:
        raise CustomValidationError("微信登录失败")
    cache.set(f"wx:session:{openid}", session_key, SESSION_KEY_TTL)
    return {"openid": openid, "session_key": session_key, "unionid": unionid}


def get_session_key(openid: str) -> Optional[str]:
    if not openid:
        return None
    return cache.get(f"wx:session:{openid}")


def decrypt_phone(encrypted_data: str, iv: str, session_key: str) -> Dict[str, str]:
    if AES is None:
        raise CustomValidationError("系统未安装微信解密依赖")
    if not encrypted_data or not iv or not session_key:
        raise CustomValidationError("缺少解密参数")
    try:
        session_key = base64.b64decode(session_key)
        encrypted_data = base64.b64decode(encrypted_data)
        iv = base64.b64decode(iv)
        cipher = AES.new(session_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_data)
        decrypted = _unpad(decrypted).decode("utf-8")
        data = json.loads(decrypted)
    except Exception:
        raise CustomValidationError("解密手机号失败，请重试")
    watermark = data.get("watermark", {})
    appid = _get_setting("WECHAT_MINIAPP_APPID", "")
    if appid and watermark.get("appid") != appid:
        raise CustomValidationError("解密手机号失败")
    return data


def _unpad(s: bytes) -> bytes:
    pad = s[-1]
    if pad < 1 or pad > 32:
        return s
    return s[:-pad]
