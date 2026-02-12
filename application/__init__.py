# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery 未安装或配置错误，不影响主应用运行
    celery_app = None
    __all__ = ()