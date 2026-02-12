import os

from application.settings import BASE_DIR

# ================================================= #
# *************** mysql数据库 配置  *************** #
# ================================================= #
# 数据库 ENGINE ，默认演示使用 sqlite3 数据库，正式环境建议使用 mysql 数据库
# sqlite3 设置
# DATABASE_ENGINE = "django.db.backends.sqlite3"
# DATABASE_NAME = os.path.join(BASE_DIR, "db.sqlite3")

# 使用mysql时，改为此配置
DATABASE_ENGINE = "django.db.backends.mysql"
DATABASE_NAME = 'law-smart-link' # mysql 时使用

# 数据库地址 改为自己数据库地址
DATABASE_HOST = '127.0.0.1'
# DATABASE_HOST = '171.80.10.200'
# # 数据库端口
DATABASE_PORT = 3306
# DATABASE_PORT = 33060
# # 数据库用户名
DATABASE_USER = "root"
# # 数据库密码
DATABASE_PASSWORD = 'your_db_password'

# 表前缀
TABLE_PREFIX = "lsl_"
# ================================================= #
# ******** redis配置，无redis 可不进行配置  ******** #
# ================================================= #
USE_REDIS = False
REDIS_DB = int(os.getenv('REDIS_DB', '1'))
CELERY_BROKER_DB = int(os.getenv('CELERY_BROKER_DB', '3'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'your_redis_password')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
# Redis URL redis://:password@host:port/db
if REDIS_PASSWORD:
    REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
else:
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
# Celery Broker URL（使用独立的数据库编号，避免 dvadmin3_celery 从 REDIS_URL 追加导致 /1/3 错误）
if REDIS_PASSWORD:
    CELERY_BROKER_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{CELERY_BROKER_DB}'
else:
    CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{CELERY_BROKER_DB}'
# ================================================= #
# ****************** 功能 启停  ******************* #
# ================================================= #
DEBUG = True
# 启动登录详细概略获取(通过调用api获取ip详细地址。如果是内网，关闭即可)
ENABLE_LOGIN_ANALYSIS_LOG = True
# 登录接口 /api/token/ 是否需要验证码认证，用于测试，正式环境建议取消
LOGIN_NO_CAPTCHA_AUTH = True
# ================================================= #
# ****************** 其他 配置  ******************* #
# ================================================= #

ALLOWED_HOSTS = ["*"]
# 列权限中排除App应用
COLUMN_EXCLUDE_APPS = []

# ================================================= #
# ****************** WPS 配置  ******************* #
# ================================================= #
# WPS 应用 ID（需要从 WPS 开放平台获取）
WPS_APP_ID = os.getenv('WPS_APP_ID', 'your_wps_app_id')

# WPS 应用密钥（需要从 WPS 开放平台获取）
WPS_APP_SECRET = os.getenv('WPS_APP_SECRET', 'your_wps_app_secret')

# WPS 服务器地址（私有化部署时需要）
WPS_SERVER_URL = os.getenv('WPS_SERVER_URL', 'https://wwo.wps.cn')

# WPS 回调地址（公网可访问的地址）
WPS_CALLBACK_URL = os.getenv('WPS_CALLBACK_URL', 'https://your-domain.example.com/api/case/v3/3rd/')

# 是否启用WPS编辑（默认True）
WPS_ENABLED = os.getenv('WPS_ENABLED', 'True').lower() == 'true'

# ================================================= #
# ****************** 豆包语音识别配置  ******************* #
# ================================================= #
# 豆包应用ID（需要从火山引擎控制台获取）
DOUBAO_APP_ID = os.getenv('DOUBAO_APP_ID', 'your_doubao_app_id')

# 豆包访问密钥Access Token（需要从火山引擎控制台获取）
DOUBAO_ACCESS_KEY = os.getenv('DOUBAO_ACCESS_KEY', 'your_doubao_access_key')

# 豆包模型资源ID（极速版，一次请求返回结果）
# 注意：需要开通 volc.bigasr.auc_turbo 权限
# - volc.bigasr.auc_turbo (极速版，推荐，一次请求返回结果)
DOUBAO_RESOURCE_ID = os.getenv('DOUBAO_RESOURCE_ID', 'volc.bigasr.auc_turbo')

# ================================================= #
# ****************** 腾讯OCR配置  ******************* #
# ================================================= #
# 注意：SecretId通常以AKID开头，SecretKey是更长的字符串
# 如果配置值看起来不对，请检查是否填反了
TENCENT_OCR_SECRET_ID = os.getenv('TENCENT_OCR_SECRET_ID', 'your_tencent_ocr_secret_id')
TENCENT_OCR_SECRET_KEY = os.getenv('TENCENT_OCR_SECRET_KEY', 'your_tencent_ocr_secret_key')
TENCENT_OCR_REGION = os.getenv('TENCENT_OCR_REGION', 'ap-guangzhou')

# ================================================= #
# ****************** 腾讯短信配置  ******************* #
# ================================================= #
TENCENT_SMS_SECRET_ID = os.getenv('TENCENT_SMS_SECRET_ID', 'your_tencent_sms_secret_id')
TENCENT_SMS_SECRET_KEY = os.getenv('TENCENT_SMS_SECRET_KEY', 'your_tencent_sms_secret_key')
TENCENT_SMS_SDK_APP_ID = os.getenv('TENCENT_SMS_SDK_APP_ID', '1400xxxxxx')
TENCENT_SMS_SIGN = os.getenv('TENCENT_SMS_SIGN', 'your_sms_sign')
TENCENT_SMS_REGION = os.getenv('TENCENT_SMS_REGION', 'ap-guangzhou')
TENCENT_SMS_IS_DEV = os.getenv('TENCENT_SMS_IS_DEV', 'False')
TENCENT_SMS_TEMPLATE_LOGIN = os.getenv('TENCENT_SMS_TEMPLATE_LOGIN', '2350456')
TENCENT_SMS_TEMPLATE_LOGIN_1 = os.getenv('TENCENT_SMS_TEMPLATE_LOGIN_1', '2549964')
TENCENT_SMS_TEMPLATE_REGISTER = os.getenv('TENCENT_SMS_TEMPLATE_REGISTER', '2516296')
TENCENT_SMS_TEMPLATE_BIND = os.getenv('TENCENT_SMS_TEMPLATE_BIND', '')
TENCENT_SMS_TEMPLATE_RESET = os.getenv('TENCENT_SMS_TEMPLATE_RESET', '')
TENCENT_SMS_TEMPLATE_FORGET = os.getenv('TENCENT_SMS_TEMPLATE_FORGET', '2350465')
TENCENT_SMS_LOGIN_EXPIRE_MINUTES = os.getenv('TENCENT_SMS_LOGIN_EXPIRE_MINUTES', '5')

# ================================================= #
# ****************** 微信小程序配置  ******************* #
# ================================================= #
WECHAT_MINIAPP_APPID = os.getenv('WECHAT_MINIAPP_APPID', 'your_wechat_miniapp_appid')
WECHAT_MINIAPP_SECRET = os.getenv('WECHAT_MINIAPP_SECRET', 'your_wechat_miniapp_secret')
WECHAT_DEFAULT_PASSWORD = os.getenv('WECHAT_DEFAULT_PASSWORD', 'change_me')

# ================================================= #
# ****************** XpertAI ChatKit 配置  ******************* #
# ================================================= #
# XpertAI 平台 API Key
XPERTAI_API_KEY = os.getenv("XPERTAI_API_KEY", "your_xpertai_api_key")
# XpertAI API Base URL（默认官方地址）
XPERTAI_API_URL = os.getenv("XPERTAI_API_URL", "https://api.mtda.cloud/api/ai/")
# ChatKit Assistant / Workflow ID（前端从 /api/ai/chatkit/config 获取）
XPERTAI_CHATKIT_ASSISTANT_ID = os.getenv("XPERTAI_CHATKIT_ASSISTANT_ID", "your_chatkit_assistant_id")
# ChatKit frameUrl（必须指向 chatkit-host 服务，例如 http://127.0.0.1:5200 ）
XPERTAI_CHATKIT_FRAME_URL = os.getenv("XPERTAI_CHATKIT_FRAME_URL", "http://127.0.0.1:5200")
# 小程序 web-view 要打开的 H5 中转页地址（可选，建议生产环境配置为完整 URL）
XPERTAI_CHATKIT_H5_URL = os.getenv("XPERTAI_CHATKIT_H5_URL", "")

# ================================================= #
# ************** XpertAI Tab3 配置  ************** #
# ================================================= #
# Tab3 使用的 XpertAI SDK API URL（LangGraph SDK 连接地址）
XPERT_SDK_API_URL = os.getenv("XPERT_SDK_API_URL", "https://api.mtda.cloud/api/ai/")
# Tab3 使用的 Assistant ID（与 ChatKit 可能不同）
XPERT_ASSISTANT_ID = os.getenv("XPERT_ASSISTANT_ID", "your_assistant_id")
# Tab3 流式模式（推荐 "debug" 以捕获所有事件包括 interrupt）
XPERT_STREAM_MODE = os.getenv("XPERT_STREAM_MODE", "debug")

# 与客户端工具 DEFAULT_CONFIG 对齐（Tab3 优先使用这一组变量名）
XPERT_API_URL = os.getenv("XPERT_API_URL", "https://api.mtda.cloud/api/ai/")
XPERT_API_KEY = os.getenv("XPERT_API_KEY", XPERTAI_API_KEY)
XPERT_STREAM_URL = os.getenv("XPERT_STREAM_URL", "https://api.mtda.cloud/api/ai/runs/stream")

# ================================================= #
# ************** 企业信息API配置 ***************** #
# ================================================= #
# 是否启用阿里云企业信息API
ALI_COMPANY_API_ENABLED = os.getenv('ALI_COMPANY_API_ENABLED', 'True').lower() == 'true'
# 阿里云接口地址
ALI_COMPANY_API_URL = os.getenv('ALI_COMPANY_API_URL', 'https://sdcombz.market.alicloudapi.com/company_normal/query')
# 阿里云AppCode（必须）
ALI_COMPANY_APP_CODE = os.getenv('ALI_COMPANY_APP_CODE', '48feee48191546ccaaec16a47f64e00f')
# 阿里云AppKey/AppSecret（仅用于日志或扩展）
ALI_COMPANY_APP_KEY = os.getenv('ALI_COMPANY_APP_KEY', '204969225')
ALI_COMPANY_APP_SECRET = os.getenv('ALI_COMPANY_APP_SECRET', 'MZCHppkrnpA2iwcucgoc0WibSZIKnPUp')
# 企业信息API缓存时间（秒）
COMPANY_API_CACHE_TIMEOUT = int(os.getenv('COMPANY_API_CACHE_TIMEOUT', '3600'))
# 企业信息API限流（每分钟最多请求次数）
COMPANY_API_RATE_LIMIT = int(os.getenv('COMPANY_API_RATE_LIMIT', '10'))
