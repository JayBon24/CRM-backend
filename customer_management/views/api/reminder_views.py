from datetime import datetime

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from customer_management.models import ReminderMessage
from customer_management.services.reminder_service import ReminderService
from dvadmin.utils.json_response import SuccessResponse, ErrorResponse


class ReminderPagination(PageNumberPagination):
    page_size_query_param = "pageSize"
    page_query_param = "page"
    max_page_size = 100
    page_size = 10


class ReminderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user or (getattr(user, "role_level", None) or "").upper() != "HQ":
            return ErrorResponse(msg="仅总所账号可查看提醒", code=4003)

        reminder_type = request.query_params.get("reminder_type")
        is_read = request.query_params.get("is_read")

        queryset = ReminderMessage.objects.filter(is_deleted=False, recipient=user).order_by("-create_datetime")
        if reminder_type:
            queryset = queryset.filter(reminder_type=reminder_type)
        if is_read is not None:
            if str(is_read).lower() in ["1", "true", "yes"]:
                queryset = queryset.filter(is_read=True)
            elif str(is_read).lower() in ["0", "false", "no"]:
                queryset = queryset.filter(is_read=False)

        # 手动分页，返回与项目其他接口一致的格式
        page_num = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 10))
        
        total = queryset.count()
        start = (page_num - 1) * page_size
        end = start + page_size
        page_items = queryset[start:end]
        
        data = [
            {
                "id": item.id,
                "reminder_type": item.reminder_type,
                "title": item.title,
                "content": item.content,
                "related_type": item.related_type,
                "related_id": item.related_id,
                "is_read": item.is_read,
                "read_time": item.read_time.isoformat() if item.read_time else None,
                "create_time": item.create_datetime.isoformat() if item.create_datetime else None,
                "extra_data": item.extra_data,
            }
            for item in page_items
        ]
        
        # 返回与项目其他接口一致的格式：{code: 2000, data: {results: [], count: ...}}
        return SuccessResponse(data={
            "results": data,
            "count": total,
            "page": page_num,
            "pageSize": page_size
        })


class ReminderReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        try:
            reminder = ReminderMessage.objects.get(id=pk, is_deleted=False)
        except ReminderMessage.DoesNotExist:
            return ErrorResponse(msg="提醒不存在", code=404)

        if reminder.recipient_id != request.user.id:
            return ErrorResponse(msg="无权操作该提醒", code=403)

        reminder.is_read = True
        reminder.read_time = timezone.now()
        reminder.save(update_fields=["is_read", "read_time"])
        return SuccessResponse(data={"ok": True})


class ReminderScanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user or (getattr(user, "role_level", None) or "").upper() != "HQ":
            return ErrorResponse(msg="仅总所账号可触发扫描", code=4003)

        service = ReminderService()
        recycle_count = service.scan_recycle_reminders()
        followup_count = service.scan_followup_reminders()
        return SuccessResponse(data={"recycle": recycle_count, "followup": followup_count})


class ReminderUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # 过滤已删除和已读的记录
        count = ReminderMessage.objects.filter(
            recipient=user, 
            is_read=False, 
            is_deleted=False
        ).count()
        return SuccessResponse(data={"unread": count})
