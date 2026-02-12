from typing import List

from dvadmin.system.models import Users

from customer_management.models import ApprovalTask, ApprovalHistory


class ApprovalService:
    CHAIN_MAP = {
        "SALES": ["HQ"],
        "TEAM": ["HQ"],
        "BRANCH": ["HQ"],
        "HQ": ["HQ"],
    }

    @classmethod
    def build_approval_chain(cls, applicant_role: str) -> List[str]:
        """构建审批链，所有申请都提交给HQ审批"""
        return cls.CHAIN_MAP.get(applicant_role, ["HQ"])

    @classmethod
    def create_task(cls, applicant: Users, approval_type: str, customer=None, related_data=None) -> ApprovalTask:
        chain = cls.build_approval_chain(applicant.role_level or "TEAM")
        task = ApprovalTask.objects.create(
            applicant=applicant,
            approval_type=approval_type,
            related_customer=customer,
            approval_chain=chain,
            current_step=0,
            current_approver_role=chain[0] if chain else None,
            related_data=related_data or {},
        )
        return task

    @classmethod
    def can_approve(cls, task: ApprovalTask, user: Users) -> bool:
        """只有HQ角色可以审批，且任务状态为待审批"""
        # HQ角色可以审批所有待审批的任务（不管current_approver_role是什么）
        # 这样可以兼容旧的审批任务（之前current_approver_role是TEAM/BRANCH）
        if user.role_level != 'HQ':
            return False
        # 只有待审批状态的任务才能被审批
        if task.status != 'pending':
            return False
        return True

    @classmethod
    def advance_task(cls, task: ApprovalTask, approver: Users, action: str, comment: str = None):
        history = ApprovalHistory.objects.create(
            approval_task=task,
            approver=approver,
            approver_role=approver.role_level,
            action=action,
            comment=comment,
        )

        if action == "approve":
            next_step = task.current_step + 1
            if next_step >= len(task.approval_chain):
                task.status = "approved"
                task.current_approver_role = None
            else:
                task.current_step = next_step
                task.current_approver_role = task.approval_chain[next_step]
        else:
            task.status = "rejected"
            task.reject_reason = comment
            task.current_approver_role = None

        task.save()
        return task, history
