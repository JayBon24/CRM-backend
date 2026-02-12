from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dvadmin.utils.viewset import CustomModelViewSet
from customer_management.models import ApprovalTask
from customer_management.serializers import ApprovalTaskSerializer
from customer_management.services.approval_service import ApprovalService


class AdminApprovalViewSet(CustomModelViewSet):
    queryset = ApprovalTask.objects.all()
    serializer_class = ApprovalTaskSerializer
    permission_classes = []

    filterset_fields = ["approval_type", "status", "applicant"]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        task = self.get_object()
        if not ApprovalService.can_approve(task, request.user):
            return Response({"detail": "no permission"}, status=status.HTTP_403_FORBIDDEN)
        ApprovalService.advance_task(task, request.user, "approve", comment=request.data.get("comment"))
        serializer = self.get_serializer(task)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        task = self.get_object()
        if not ApprovalService.can_approve(task, request.user):
            return Response({"detail": "no permission"}, status=status.HTTP_403_FORBIDDEN)
        ApprovalService.advance_task(task, request.user, "reject", comment=request.data.get("comment"))
        serializer = self.get_serializer(task)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        task = self.get_object()
        serializer = self.get_serializer(task)
        return Response(serializer.data)
