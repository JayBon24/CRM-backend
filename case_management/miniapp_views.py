"""
小程序案件列表接口
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from case_management.models import CaseManagement


def _apply_case_scope(queryset, user):
    scope = getattr(user, "role_level", None) or getattr(user, "org_scope", None)
    if scope == "HQ":
        return queryset
    if scope == "BRANCH":
        branch_id = getattr(user, "branch_id", None) or getattr(user, "dept_id", None)
        if branch_id:
            return queryset.filter(customer__branch_id=branch_id)
        return queryset.none()
    if scope == "TEAM":
        team_id = getattr(user, "team_id", None) or getattr(user, "dept_id", None)
        if team_id:
            return queryset.filter(customer__team_id=team_id)
        return queryset.none()
    return queryset.filter(owner_user=user)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_case_list(request):
    """
    获取案件列表
    GET /api/case/cases/
    """
    try:
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size") or request.query_params.get("limit") or 20)
        case_status = request.query_params.get("case_status")
        case_type = request.query_params.get("case_type")
        customer_id = request.query_params.get("customer_id")
        owner_user_id = request.query_params.get("owner_user_id")
        search = request.query_params.get("search")

        queryset = CaseManagement.objects.filter(is_deleted=False).select_related("customer", "owner_user")
        queryset = _apply_case_scope(queryset, request.user)

        if case_status:
            queryset = queryset.filter(case_status=case_status)
        if case_type:
            queryset = queryset.filter(case_type=case_type)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        if owner_user_id:
            queryset = queryset.filter(owner_user_id=owner_user_id)
        if search:
            queryset = queryset.filter(
                Q(case_name__icontains=search) | Q(case_number__icontains=search)
            )

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        # Fix: CaseManagement doesn't inherit CoreModel, so it doesn't have create_datetime field
        # Use id for ordering instead
        cases = queryset.order_by("-id")[start:end]

        results = []
        for case in cases:
            results.append({
                "id": case.id,
                "case_number": case.case_number,
                "case_name": case.case_name,
                "case_type": case.case_type,
                "case_status": case.case_status,
                "customer_id": case.customer_id,
                "customer_name": case.customer.name if case.customer else None,
                "owner_user_id": case.owner_user_id,
                "owner_user_name": case.owner_user_name or (case.owner_user.name if case.owner_user else None),
                "create_datetime": None,  # CaseManagement doesn't have create_datetime field
            })

        return DetailResponse(data={
            "count": total,
            "results": results,
            "page": page,
            "page_size": page_size,
        })
    except Exception as e:
        return ErrorResponse(msg=f"获取案件列表失败: {str(e)}", code=4000)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_case_detail(request, case_id: int):
    """
    获取案件详情
    GET /api/case/cases/{id}/
    """
    try:
        queryset = CaseManagement.objects.filter(is_deleted=False).select_related("customer", "owner_user")
        queryset = _apply_case_scope(queryset, request.user)
        case = queryset.filter(id=case_id).first()
        if not case:
            return ErrorResponse(msg="案件不存在", code=4004)

        return DetailResponse(data={
            "id": case.id,
            "case_number": case.case_number,
            "case_name": case.case_name,
            "case_type": case.case_type,
            "case_status": case.case_status,
            "case_description": case.case_description,
            "plaintiff_name": case.plaintiff_name,
            "plaintiff_credit_code": case.plaintiff_credit_code,
            "plaintiff_address": case.plaintiff_address,
            "plaintiff_legal_representative": case.plaintiff_legal_representative,
            "defendant_name": case.defendant_name,
            "defendant_credit_code": case.defendant_credit_code,
            "defendant_address": case.defendant_address,
            "defendant_legal_representative": case.defendant_legal_representative,
            "contract_amount": float(case.contract_amount) if case.contract_amount else None,
            "lawyer_fee": float(case.lawyer_fee) if case.lawyer_fee else None,
            "litigation_request": case.litigation_request,
            "facts_and_reasons": case.facts_and_reasons,
            "jurisdiction": case.jurisdiction,
            "petitioner": case.petitioner,
            "filing_date": case.filing_date.strftime("%Y-%m-%d") if case.filing_date else None,
            "customer_id": case.customer_id,
            "customer_name": case.customer.name if case.customer else None,
            "owner_user_id": case.owner_user_id,
            "owner_user_name": case.owner_user_name or (case.owner_user.name if case.owner_user else None),
            "create_datetime": None,  # CaseManagement doesn't have create_datetime field
            "update_datetime": None,  # CaseManagement doesn't have update_datetime field
        })
    except Exception as e:
        return ErrorResponse(msg=f"获取案件详情失败: {str(e)}", code=4000)
