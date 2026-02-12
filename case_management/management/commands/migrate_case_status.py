# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from case_management.models import CaseManagement
from customer_management.models import Customer


class Command(BaseCommand):
    help = "Backfill CaseManagement status/sales_stage based on linked customer status."

    def handle(self, *args, **options):
        updated = 0
        total = 0
        for case in CaseManagement.objects.all():
            total += 1
            status = CaseManagement.STATUS_FOLLOW_UP
            sales_stage = CaseManagement.SALES_STAGE_BLANK

            customer = getattr(case, "customer", None)
            if customer:
                if customer.status == Customer.STATUS_PUBLIC_POOL:
                    status = CaseManagement.STATUS_PUBLIC_POOL
                    sales_stage = CaseManagement.SALES_STAGE_PUBLIC
                elif customer.status == Customer.STATUS_FOLLOW_UP:
                    status = CaseManagement.STATUS_FOLLOW_UP
                    sales_stage = (
                        CaseManagement.SALES_STAGE_MEETING
                        if customer.valid_visit_count > 0
                        else CaseManagement.SALES_STAGE_BLANK
                    )
                elif customer.status == Customer.STATUS_CASE:
                    status = CaseManagement.STATUS_CASE
                    sales_stage = CaseManagement.SALES_STAGE_CASE
                elif customer.status == Customer.STATUS_PAYMENT:
                    status = CaseManagement.STATUS_PAYMENT
                    sales_stage = CaseManagement.SALES_STAGE_PAYMENT
                elif customer.status == Customer.STATUS_WON:
                    status = CaseManagement.STATUS_WON
                    sales_stage = CaseManagement.SALES_STAGE_WON

            if case.status != status or case.sales_stage != sales_stage:
                case.status = status
                case.sales_stage = sales_stage
                case.save(update_fields=["status", "sales_stage"])
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Case status migration completed. updated={updated} total={total}"
            )
        )
