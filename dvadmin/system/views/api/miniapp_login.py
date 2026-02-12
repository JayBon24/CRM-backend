"""
小程序登录接口
"""
import base64
import logging
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

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

from dvadmin.system.models import Users
from dvadmin.utils.request_util import save_login_log
from dvadmin.utils.validator import CustomValidationError

logger = logging.getLogger(__name__)


class MiniappLoginSerializer(TokenObtainPairSerializer):
    """
    小程序登录序列化器
    支持用户名/手机号 + 密码登录
    不需要验证码
    """

    class Meta:
        model = Users
        fields = "__all__"
        read_only_fields = ["id"]

    default_error_messages = {"no_active_account": _("账号/密码错误")}

    def validate(self, attrs):
        # RSA私钥（需要与前端公钥配对）
        # 注意：这里需要完整的PEM格式私钥，包括 -----BEGIN RSA PRIVATE KEY----- 和 -----END RSA PRIVATE KEY-----
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

        # 1. RSA解密密码
        if PKCS1_v1_5 is None or RSA is None:
            logger.error("RSA解密库未安装，请安装 pycryptodome: pip install pycryptodome")
            raise CustomValidationError("系统配置错误，请联系管理员")
        
        try:
            encrypted_password = attrs.get('password', '')
            if not encrypted_password:
                raise CustomValidationError("密码不能为空")
            
            # Base64解码
            try:
                encrypted_bytes = base64.b64decode(encrypted_password)
            except Exception as e:
                logger.error(f"Base64解码失败: {str(e)}")
                raise CustomValidationError("密码格式错误")
            
            # RSA解密
            try:
                private_key = RSA.importKey(RSA_PRIVATE_KEY)
                cipher = PKCS1_v1_5.new(private_key)
                decrypted_password = cipher.decrypt(encrypted_bytes, None)
                
                if decrypted_password is None:
                    logger.error("RSA解密失败：解密结果为None")
                    raise CustomValidationError("密码解密失败，请重试")
                
                # 转换为字符串
                decrypted_password = decrypted_password.decode('utf-8')
                logger.info("RSA解密成功")
                
                # 将解密后的明文密码替换到attrs中
                attrs['password'] = decrypted_password
                
            except ValueError as e:
                logger.error(f"RSA私钥格式错误: {str(e)}")
                raise CustomValidationError("系统配置错误，请联系管理员")
            except Exception as e:
                logger.error(f"RSA解密失败: {str(e)}")
                raise CustomValidationError("密码解密失败，请重试")
                
        except CustomValidationError:
            raise
        except Exception as e:
            logger.error(f"密码处理异常: {str(e)}")
            raise CustomValidationError("密码处理失败，请重试")

        # 2. 查找用户：支持用户名和手机号，不支持邮箱
        try:
            user = Users.objects.get(
                Q(username=attrs['username']) | Q(mobile=attrs['username'])
            )
        except Users.DoesNotExist:
            raise CustomValidationError("您登录的账号不存在")
        except Users.MultipleObjectsReturned:
            raise CustomValidationError("您登录的账号存在多个,请联系管理员检查登录账号唯一性")

        # 检查账号是否被锁定
        if not user.is_active:
            raise CustomValidationError("账号已被锁定,联系管理员解锁")

        try:
            # 必须重置用户名为username,否则使用手机号登录会提示密码错误
            attrs['username'] = user.username
            
            # 调用父类验证密码
            data = super().validate(attrs)
            
            # 返回用户信息
            data["username"] = self.user.username
            data["name"] = self.user.name
            data["userId"] = self.user.id
            data["avatar"] = self.user.avatar
            data['user_type'] = self.user.user_type
            data['pwd_change_count'] = self.user.pwd_change_count
            
            # 角色层级
            data['role_level'] = self.user.role_level
            
            # 组织架构ID
            data['team_id'] = self.user.team_id
            data['branch_id'] = self.user.branch_id
            data['hq_id'] = self.user.headquarters_id
            
            # 部门信息
            dept = getattr(self.user, 'dept', None)
            if dept:
                data['dept_info'] = {
                    'dept_id': dept.id,
                    'dept_name': dept.name,
                }
            
            # 角色信息
            role = getattr(self.user, 'role', None)
            if role:
                data['role_info'] = list(role.values('id', 'name', 'key'))
            
            # 记录登录日志
            request = self.context.get("request")
            request.user = self.user
            # 标记为小程序登录
            request.login_type = 3
            save_login_log(request=request)
            
            # 重置登录错误次数
            user.login_error_count = 0
            user.save()
            
            return {"code": 2000, "msg": "请求成功", "data": data}
            
        except Exception as e:
            # 登录失败，错误次数+1
            user.login_error_count += 1
            if user.login_error_count >= 5:
                # 5次失败后锁定账号
                user.is_active = False
                user.save()
                raise CustomValidationError("账号已被锁定,联系管理员解锁")
            user.save()
            count = 5 - user.login_error_count
            raise CustomValidationError(f"账号/密码错误;重试{count}次后将被锁定~")


class MiniappLoginView(TokenObtainPairView):
    """
    小程序登录接口
    POST /api/miniapp/login/
    """
    serializer_class = MiniappLoginSerializer
    permission_classes = []
    authentication_classes = []  # 不需要认证
