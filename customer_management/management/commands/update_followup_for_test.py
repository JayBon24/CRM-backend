# -*- coding: utf-8 -*-
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from customer_management.models import FollowupRecord, Customer


class Command(BaseCommand):
    help = "Update followup_time for test reminders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--customer-id",
            type=int,
            help="Customer ID to target",
        )
        parser.add_argument(
            "--days-ago",
            type=int,
            default=20,
            help="Set followup_time to N days ago (default: 20)",
        )
        parser.add_argument(
            "--owner-user-id",
            type=int,
            help="Owner user ID to target",
        )

    def handle(self, *args, **options):
        days_ago = options.get("days_ago") or 20
        customer_id = options.get("customer_id")
        owner_user_id = options.get("owner_user_id")

        target_time = timezone.now() - timedelta(days=days_ago)
        queryset = FollowupRecord.objects.filter(is_deleted=False)

        if customer_id:
            queryset = queryset.filter(Q(customer_id=customer_id) | Q(client_id=customer_id))

        if owner_user_id:
            customer_ids = Customer.objects.filter(
                owner_user_id=owner_user_id,
                is_deleted=False,
            ).values_list("id", flat=True)
            queryset = queryset.filter(Q(customer_id__in=customer_ids) | Q(client_id__in=customer_ids))

        updated_count = queryset.update(
            followup_time=target_time,
            update_datetime=timezone.now(),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {updated_count} followup records to {days_ago} days ago."
            )
        )
