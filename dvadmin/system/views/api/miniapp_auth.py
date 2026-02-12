import base64
import logging
import os
from django.db import transaction
from rest_framework.views import APIView

from dvadmin.system.models import Users
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from dvadmin.utils.validator import CustomValidationError
from dvadmin.utils.wechat_miniapp import code2session, get_session_key, decrypt_phone
from dvadmin.utils.sms_provider import send_sms_code, validate_sms_code
from rest_framework_simplejwt.tokens import RefreshToken

try:
    from Crypto.Cipher import PKCS1_v1_5
    from Crypto.PublicKey import RSA
except ImportError:
    try:
        from Cryptodome.Cipher import PKCS1_v1_5
        from Cryptodome.PublicKey import RSA
    except ImportError:
        PKCS1_v1_5 = None
        RSA = None

logger = logging.getLogger(__name__)

RSA_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDL4s6NWLmNSD68
uefHsm/t3yrKdWOjUBbY3JWLGomTNT26UoGEGvX62g4u3FaiCoKVEFdPP6VzmpZg
HsNjPyRo42FVwwylTD1h6ZWjiFRh7xvKnUleUmJq3uZsCQfj50G7C9HxRb+qGrRV
Io37XjHqzGOriPc0RHnCZPsWdqYKN0Yca3sL5fK0BcMHmvpQgf/qYZDbh0i7kYyZ
E3D91V956S9NhlsPReRPc9EUfUtF5y/h5ZmZzQb6hzV33kW4fZKBRUIAZwzxpdfy
7IdDrlT53tDOOvlzn1rJPEFZ+onz4H4ybB/9i6YwWEJOSBKEqsEoQtVogb6Kh5cO
dVCTM2J9AgMBAAECggEBAJ79tRjgUYHtDo9ZYXeGnGYgm1vaAuL9t3NRQISDIzla
UVKUuE7uP1do55p/VEd0brQTVCKGfV0S9aTrGG6ydJAekG6ydZAJTeymnHwz+amN
LlzoHqihEgJI4+Lnf/GnCsjzxLmjLH1X6bxh/9o/cCmrTSYc3rkxlMmUuYCg8YYQ
gogVwGKW6LR890u/kZAoC8XgNtX/QHqEmype2Es2qnX2JTUNdbcaqkZdJuDPU1EP
8oaP2I+hVEaQGQptVzuX4Bpu1UJfIoQRFV/RBDaRrGxkr1TE5F5Zex4aL6JnRsqx
KdIgSBpi2QOmQok+JiPmb1PR5YJqcaXaMXUXvCb6c0ECgYEA+ujBwnB0dMm6TKOy
NDr/Hf+iYr3RIcLyM4GEo6tiOio66tgyTQ9K4lU9is6kE6qjxaNtOeAs+0gtLzXZ
w/MVRpwn456XNCK08sqmHR33mFayOJ9vw3lLlvJ9lJEC4vBRKrAMV7k46b6IoZLv
MdzWBFshC81VKUb8raQYCAxfJskCgYEA0AXOr8d/a8PQ1qImMzIbD+6NyTCQ0kG9
w/QNdhTkWF8yOU1Ffn5e4lqsBkP5WweTbIkiq8Rvgc3XGydTokawcMBITI2mga6x
nJwQ0OsG0aVIU6ZSdqZ+eeAJDYUJwnl3cJYR3jvfd60DbAmeEVMfY2+aqa0MFURx
8HtmUtyxlBUCgYB3Se3EuZ5EYBwYj8MLnfjolD7p3wDsojhwUGV1QugCa01zlbHk
fR7HGGuX8MKFLx2JuzcUywXXuerxhRKxXIKC/X7hcubEPLP2sm3jbfnnDWDSFssW
Djbn3wXhekf7CPIt72EO29q5FoLy/l6GQE3n6EN/zvFsHHnJPDjIqskaMQKBgQCB
ZXthwBi0sgNv30Efy2UmDd/IbBtJjnc6Ms9Eyk4X4m9dUYGO45CmAHzNEO9E/ntn
og4dBn3OInpRe678XDhYimLuq5YNSNtWbYXQTsHZGpTY47ab84jsyr0W2dBuVhxD
vjWzJU8mJErio0DdyfTWZ4+vR+MiP4cYbcoCdSFI2QKBgQCZsauHLsFaw5WC7fLc
985QBlj6KQbUE75YGdNMsFe4Orc+IEb7pZCVYi418veQZR3X7I7zGh1j6cloKlNQ
/TzR2F5PFTC3x6zwrFPvMpzvjQI05RYh78N2mOsIW86/Ilf48q42wh2tZ21eOLWN
maWbMwVYDSX+h6rCh3zYeb3pig==
-----END PRIVATE KEY-----"""


def _build_token(user: Users):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)

def _decrypt_password(encrypted_password: str) -> str:
    if PKCS1_v1_5 is None or RSA is None:
        raise CustomValidationError("系统配置错误，请联系管理员")
    if not encrypted_password:
        raise CustomValidationError("密码不能为空")
    try:
        encrypted_bytes = base64.b64decode(encrypted_password)
    except Exception as e:
        logger.error(f"Base64解码失败: {str(e)}")
        raise CustomValidationError("密码格式错误")
    try:
        private_key = RSA.importKey(RSA_PRIVATE_KEY)
        cipher = PKCS1_v1_5.new(private_key)
        decrypted_password = cipher.decrypt(encrypted_bytes, None)
        if decrypted_password is None:
            raise CustomValidationError("密码解密失败，请重试")
        return decrypted_password.decode("utf-8")
    except CustomValidationError:
        raise
    except Exception as e:
        logger.error(f"RSA解密失败: {str(e)}")
        raise CustomValidationError("密码解密失败，请重试")


class SmsSendView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        phone = request.data.get("phone")
        code_type = request.data.get("type", "login")
        try:
            send_sms_code(phone, code_type)
            return DetailResponse(msg="验证码已发送")
        except CustomValidationError as e:
            return ErrorResponse(msg=str(e))


class SmsLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        phone = request.data.get("phone")
        sms_code = request.data.get("smsCode")
        if not phone or not sms_code:
            return ErrorResponse(msg="手机号或验证码不能为空")
        if not validate_sms_code(phone, "login", sms_code):
            return ErrorResponse(msg="验证码错误或已过期")
        user = Users.objects.filter(mobile=phone).first()
        if not user:
            return ErrorResponse(msg="用户不存在，请先注册")
        if not user.is_active:
            return ErrorResponse(msg="账号已停用，请联系管理员")
        token = _build_token(user)
        data = {"token": token, "userInfo": {"userId": user.id, "userName": user.username, "nickName": user.name, "avatar": user.avatar}}
        return DetailResponse(data=data, msg="登录成功")

class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        phone = request.data.get("phone")
        encrypted_password = request.data.get("password")
        code = request.data.get("code")
        if not phone or not encrypted_password or not code:
            return ErrorResponse(msg="手机号、密码或验证码不能为空")
        if not validate_sms_code(phone, "register", code):
            return ErrorResponse(msg="验证码错误或已过期")
        if Users.objects.filter(mobile=phone).exists():
            return ErrorResponse(msg="手机号已注册")
        try:
            password = _decrypt_password(encrypted_password)
        except CustomValidationError as e:
            return ErrorResponse(msg=str(e))

        user = Users()
        user.username = phone
        user.mobile = phone
        user.name = phone
        user.set_password(password)
        user.save()

        token = _build_token(user)
        data = {
            "token": token,
            "userInfo": {
                "userId": user.id,
                "userName": user.username,
                "nickName": user.name,
                "avatar": user.avatar,
            },
        }
        return DetailResponse(data=data, msg="注册成功")

class WechatCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        code = request.data.get("code")
        try:
            session = code2session(code)
        except CustomValidationError as e:
            return ErrorResponse(msg=str(e))
        openid = session.get("openid")
        unionid = session.get("unionid")
        user = Users.objects.filter(wechat_openid=openid).first()
        data = {"openid": openid, "unionid": unionid}
        if user:
            if not user.is_active:
                return ErrorResponse(msg="账号已停用，请联系管理员")
            token = _build_token(user)
            data.update({
                "needRegister": False,
                "token": token,
                "phone": user.mobile,
                "userInfo": {
                    "userId": user.id,
                    "userName": user.username,
                    "nickName": user.name,
                    "avatar": user.avatar
                }
            })
            return DetailResponse(data=data, msg="登录成功")
        data.update({"needRegister": True})
        return DetailResponse(data=data, msg="需要完善信息")


class WechatRegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        openid = request.data.get("openid")
        unionid = request.data.get("unionid")
        encrypted_data = request.data.get("encryptedData")
        iv = request.data.get("iv")
        phone = request.data.get("phone")
        sms_code = request.data.get("smsCode")
        user_info = request.data.get("userInfo") or {}
        sms_validated = False

        if not openid:
            return ErrorResponse(msg="openid 不能为空")

        if encrypted_data and iv:
            session_key = get_session_key(openid)
            if not session_key:
                return ErrorResponse(msg="session_key 已过期，请重新登录")
            try:
                phone_info = decrypt_phone(encrypted_data, iv, session_key)
            except CustomValidationError as e:
                return ErrorResponse(msg=str(e))
            phone = phone_info.get("phoneNumber") or phone
        else:
            if not phone or not sms_code:
                return ErrorResponse(msg="手机号或验证码不能为空")
            if not validate_sms_code(phone, "bind_phone", sms_code):
                return ErrorResponse(msg="验证码错误或已过期")
            sms_validated = True

        if not phone:
            return ErrorResponse(msg="手机号不能为空")

        with transaction.atomic():
            user = Users.objects.filter(mobile=phone).first()
            if user:
                if not user.is_active:
                    return ErrorResponse(msg="账号已停用，请联系管理员")
                if user.wechat_openid and user.wechat_openid != openid:
                    if not sms_validated:
                        return ErrorResponse(msg="手机号已绑定其他微信，请使用短信验证码绑定")
                user.wechat_openid = openid
                if unionid:
                    user.wechat_unionid = unionid
            else:
                user = Users()
                user.username = phone
                user.mobile = phone
                nick_name = user_info.get("nickName") if isinstance(user_info, dict) else None
                nick_name = (nick_name or "").strip()
                if nick_name in {"微信用户", "微信用户昵称"}:
                    nick_name = ""
                user.name = nick_name or phone
                user.wechat_openid = openid
                if unionid:
                    user.wechat_unionid = unionid
                default_password = os.getenv("WECHAT_DEFAULT_PASSWORD", "admin123456")
                user.set_password(default_password)
            avatar = user_info.get("avatarUrl")
            if avatar:
                user.avatar = avatar
            user.save()

        token = _build_token(user)
        data = {
            "token": token,
            "phone": phone,
            "openid": openid,
            "unionid": unionid,
            "userInfo": {"userId": user.id, "userName": user.username, "nickName": user.name, "avatar": user.avatar},
        }
        return DetailResponse(data=data, msg="注册成功")
