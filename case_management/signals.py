"""
案件管理信号处理
"""
import logging
import os
import threading
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CaseManagement
from .utils.folder_helper import create_case_folders

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CaseManagement)
def init_case_folders(sender, instance, created, **kwargs):
    """
    案件创建后自动初始化目录结构
    
    Args:
        sender: 信号发送者
        instance: CaseManagement 实例
        created: 是否是新创建的
        **kwargs: 其他参数
    """
    if created:
        case_id = instance.id
        case_number = instance.case_number
        def _create():
            try:
                create_case_folders(case_id)
                logger.info(f"案件 {case_id} ({case_number}) 的目录结构已自动创建")
            except Exception as e:
                logger.error(f"初始化案件目录失败 (case_id={case_id}): {str(e)}")
                # 不抛出异常，避免影响案件创建

        async_enabled = os.getenv("CASE_FOLDER_INIT_ASYNC", "True").lower() == "true"

        def _run_after_commit():
            if async_enabled:
                threading.Thread(target=_create, daemon=True).start()
            else:
                _create()

        try:
            transaction.on_commit(_run_after_commit)
        except Exception:
            _run_after_commit()
