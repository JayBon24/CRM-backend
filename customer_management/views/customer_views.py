from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from dvadmin.utils.viewset import CustomModelViewSet
from customer_management.models import Customer
from customer_management.serializers import CustomerSerializer


class CustomerViewSet(CustomModelViewSet):
    queryset = Customer.objects.filter(is_deleted=False)
    serializer_class = CustomerSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["name", "credit_code"]
    search_fields = ["name", "contact_person", "contact_phone", "credit_code"]
    ordering_fields = ["id", "name"]
    ordering = ["-id"]

    permission_classes = []
    extra_filter_class = []
