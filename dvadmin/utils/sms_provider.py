import os
import random
from django.conf import settings
from django.core.cache import cache
from dvadmin.utils.validator import CustomValidationError

SMS_CODE_TTL = 5 * 60
SMS_RESEND_TTL = 60


def _get_setting(name: str, default: str = "") -> str:
    env_val = os.getenv(name)
    if env_val is not None and str(env_val).strip() != "":
        return str(env_val).strip()
    return str(getattr(settings, name, default) or "").strip()


def _get_sms_config():
    secret_id = _get_setting("TENCENT_SMS_SECRET_ID", "")
    secret_key = _get_setting("TENCENT_SMS_SECRET_KEY", "")
    sdk_app_id = _get_setting("TENCENT_SMS_SDK_APP_ID", "")
    sign_name = _get_setting("TENCENT_SMS_SIGN", "")
    region = _get_setting("TENCENT_SMS_REGION", "ap-guangzhou")
    return secret_id, secret_key, sdk_app_id, sign_name, region


def _get_template_id(code_type: str):
    login_template = _get_setting("TENCENT_SMS_TEMPLATE_LOGIN", "")
    login_template_simple = _get_setting("TENCENT_SMS_TEMPLATE_LOGIN_1", "")
    bind_template = _get_setting("TENCENT_SMS_TEMPLATE_BIND", "")
    reset_template = _get_setting("TENCENT_SMS_TEMPLATE_RESET", "")
    forget_template = _get_setting("TENCENT_SMS_TEMPLATE_FORGET", "")
    register_template = _get_setting("TENCENT_SMS_TEMPLATE_REGISTER", "")

    if code_type == "login":
        return login_template_simple or login_template
    if code_type == "register":
        return register_template or login_template_simple or login_template
    if code_type == "bind_phone":
        return bind_template or login_template_simple or login_template
    if code_type == "reset":
        return reset_template or forget_template
    return ""


def _check_config(code_type: str):
    secret_id, secret_key, sdk_app_id, sign_name, region = _get_sms_config()
    template_id = _get_template_id(code_type)
    if not all([secret_id, secret_key, sdk_app_id, sign_name, template_id]):
        raise CustomValidationError("短信服务未配置")
    return secret_id, secret_key, sdk_app_id, sign_name, template_id, region


def _is_dev_mode():
    return _get_setting("TENCENT_SMS_IS_DEV", "False").lower() == "true"


def send_sms_code(phone: str, code_type: str) -> str:
    if not phone:
        raise CustomValidationError("手机号不能为空")
    resend_key = f"sms:resend:{code_type}:{phone}"
    if cache.get(resend_key):
        raise CustomValidationError("操作过于频繁，请稍后再试")

    if not _is_dev_mode():
        _check_config(code_type)
    code = f"{random.randint(0, 999999):06d}"
    if not _is_dev_mode():
        _send_tencent_sms(phone, code_type, code)
    cache.set(f"sms:code:{code_type}:{phone}", code, SMS_CODE_TTL)
    cache.set(resend_key, 1, SMS_RESEND_TTL)
    return code


def validate_sms_code(phone: str, code_type: str, code: str) -> bool:
    if not phone or not code:
        return False
    cached = cache.get(f"sms:code:{code_type}:{phone}")
    if cached and str(cached) == str(code):
        cache.delete(f"sms:code:{code_type}:{phone}")
        return True
    return False


def _send_tencent_sms(phone: str, code_type: str, code: str):
    secret_id, secret_key, sdk_app_id, sign_name, template_id, region = _check_config(code_type)
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.sms.v20210111 import sms_client, models
    except Exception:
        raise CustomValidationError("短信SDK未安装")

    cred = credential.Credential(secret_id, secret_key)
    http_profile = HttpProfile()
    http_profile.endpoint = "sms.tencentcloudapi.com"
    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    client = sms_client.SmsClient(cred, region or "ap-guangzhou", client_profile)

    req = models.SendSmsRequest()
    req.SmsSdkAppId = sdk_app_id
    req.SignName = sign_name
    req.TemplateId = template_id
    params = [code]
    if code_type == "login":
        expire = _get_setting("TENCENT_SMS_LOGIN_EXPIRE_MINUTES", "5")
        if template_id == _get_setting("TENCENT_SMS_TEMPLATE_LOGIN", "") and expire:
            params = [code, str(expire)]
    req.TemplateParamSet = params
    req.PhoneNumberSet = [f"+86{phone}"]
    resp = client.SendSms(req)
    if not resp or not resp.SendStatusSet:
        raise CustomValidationError("短信发送失败")
    status = resp.SendStatusSet[0]
    if status.Code != "Ok":
        raise CustomValidationError(status.Message or "短信发送失败")
