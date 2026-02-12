"""
案件创建服务
"""
from __future__ import annotations

import random
from typing import Dict, Optional

from django.utils import timezone
from django.utils.dateparse import parse_date

from case_management.models import CaseManagement
from customer_management.models import Customer
from customer_management.models.contract import Contract


def generate_case_number(contract_no: Optional[str] = None) -> str:
    """
    生成案件编号，优先使用合同编号，确保唯一。
    """
    if contract_no:
        base = f"AJ{contract_no}"
    else:
        base = f"AJ{timezone.now().strftime('%Y%m%d%H%M%S')}"

    candidate = base
    index = 1
    while CaseManagement.objects.filter(case_number=candidate).exists():
        index += 1
        candidate = f"{base}-{index}-{random.randint(10, 99)}"
    return candidate


def _normalize_case_data(case_data: Dict) -> Dict:
    return case_data or {}


def _parse_date(value):
    if not value:
        return None
    if hasattr(value, "strftime"):
        return value
    parsed = parse_date(str(value))
    return parsed


def _build_case_fields(customer: Customer, contract: Contract, case_data: Dict) -> Dict:
    data = _normalize_case_data(case_data)

    case_name = data.get("case_name") or contract.contract_no or f"{customer.name}案件"
    case_type = data.get("case_type") or contract.service_type or "other"
    status = data.get("status") or CaseManagement.STATUS_CASE
    sales_stage = data.get("sales_stage") or CaseManagement.SALES_STAGE_CASE

    return {
        "case_number": generate_case_number(contract.contract_no),
        "case_name": case_name,
        "case_type": case_type,
        "case_status": data.get("case_status") or "待处理",
        "status": status,
        "sales_stage": sales_stage,
        "case_description": data.get("case_description") or data.get("project_background"),
        "plaintiff_name": data.get("plaintiff_name"),
        "plaintiff_credit_code": data.get("plaintiff_credit_code"),
        "plaintiff_address": data.get("plaintiff_address"),
        "plaintiff_legal_representative": data.get("plaintiff_legal_representative"),
        "defendant_name": data.get("defendant_name"),
        "defendant_credit_code": data.get("defendant_credit_code"),
        "defendant_address": data.get("defendant_address"),
        "defendant_legal_representative": data.get("defendant_legal_representative"),
        "contract_amount": data.get("contract_amount") or contract.amount,
        "lawyer_fee": data.get("lawyer_fee"),
        "litigation_request": data.get("litigation_request"),
        "facts_and_reasons": data.get("facts_and_reasons"),
        "jurisdiction": data.get("jurisdiction"),
        "petitioner": data.get("petitioner"),
        "draft_person": data.get("draft_person"),
        "filing_date": _parse_date(data.get("filing_date")),
        "customer": customer,
        "owner_user": customer.owner_user,
        "owner_user_name": customer.owner_user_name or (customer.owner_user.name if customer.owner_user else None),
        "contract": contract,
    }


def create_case_from_effective_case(
    customer: Customer,
    effective_case_plan,
    contract: Contract,
    override_data: Optional[Dict] = None,
) -> CaseManagement:
    data = _normalize_case_data(getattr(effective_case_plan, "extra_data", {}) or {})
    if override_data:
        for key, value in override_data.items():
            if value not in (None, ""):
                data[key] = value
    fields = _build_case_fields(customer, contract, data)
    return CaseManagement.objects.create(**fields)


def create_case_from_contract_data(
    customer: Customer,
    contract: Contract,
    case_data: Optional[Dict] = None,
) -> CaseManagement:
    fields = _build_case_fields(customer, contract, _normalize_case_data(case_data))
    return CaseManagement.objects.create(**fields)
