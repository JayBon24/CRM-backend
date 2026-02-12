# -*- coding: utf-8 -*-
from collections import defaultdict

from django.core.management import BaseCommand
from django.db import transaction

from customer_management.models import Customer
from customer_management.models.organization import Team, Branch
from dvadmin.system.models import Users


def _build_username(prefix: str, branch_id: int, team_id: int, index: int) -> str:
    return f"{prefix}_{branch_id or 0}_{team_id or 0}_{index}"


def _ensure_sales_user(username: str, name: str, branch_id: int, team_id: int, hq_id: int) -> Users:
    user, created = Users.objects.get_or_create(
        username=username,
        defaults={
            "name": name,
            "role_level": "SALES",
            "org_scope": "SELF",
            "branch_id": branch_id,
            "team_id": team_id,
            "headquarters_id": hq_id,
            "user_type": 0,
        },
    )
    if created:
        user.set_password("123456")
        user.save(update_fields=["password"])
    return user


class Command(BaseCommand):
    help = "创建销售账号并按分所/团队补全客户经办人"

    def add_arguments(self, parser):
        parser.add_argument("--per-team", type=int, default=2, help="每个团队创建的销售账号数量")
        parser.add_argument("--include-public", action="store_true", help="是否给公海客户补经办人")
        parser.add_argument("--dry-run", action="store_true", help="只打印不写入")

    def handle(self, *args, **options):
        per_team = int(options.get("per_team") or 2)
        include_public = bool(options.get("include_public"))
        dry_run = bool(options.get("dry_run"))

        team_list = list(Team.objects.filter(status=True).order_by("id"))
        branch_list = list(Branch.objects.filter(status=True).order_by("id"))

        created_users = []
        team_users = defaultdict(list)
        branch_users = defaultdict(list)

        if team_list:
            for team in team_list:
                for idx in range(1, per_team + 1):
                    username = _build_username("sales", team.branch_id, team.id, idx)
                    name = f"{team.name}销售{idx}"
                    if dry_run:
                        self.stdout.write(f"[dry-run] 创建销售用户: {username} ({name})")
                        continue
                    user = _ensure_sales_user(username, name, team.branch_id, team.id, team.headquarters_id)
                    team_users[team.id].append(user)
                    branch_users[team.branch_id].append(user)
                    created_users.append(user)
        elif branch_list:
            for branch in branch_list:
                for idx in range(1, per_team + 1):
                    username = _build_username("sales", branch.id, 0, idx)
                    name = f"{branch.name}销售{idx}"
                    if dry_run:
                        self.stdout.write(f"[dry-run] 创建销售用户: {username} ({name})")
                        continue
                    user = _ensure_sales_user(username, name, branch.id, None, branch.headquarters_id)
                    branch_users[branch.id].append(user)
                    created_users.append(user)

        if dry_run:
            self.stdout.write("dry-run 模式不执行客户分配。")
            return

        sales_users = Users.objects.filter(role_level="SALES").order_by("id")
        if not sales_users.exists():
            self.stdout.write("未找到销售账号，无法分配客户。")
            return

        customers = Customer.objects.filter(is_deleted=False, owner_user__isnull=True)
        if not include_public:
            customers = customers.exclude(status=Customer.STATUS_PUBLIC_POOL)

        team_index = defaultdict(int)
        branch_index = defaultdict(int)
        global_index = 0
        assigned_count = 0

        with transaction.atomic():
            for customer in customers:
                candidate_users = []
                if customer.team_id and team_users.get(customer.team_id):
                    candidate_users = team_users[customer.team_id]
                    idx = team_index[customer.team_id] % len(candidate_users)
                    team_index[customer.team_id] += 1
                elif customer.branch_id and branch_users.get(customer.branch_id):
                    candidate_users = branch_users[customer.branch_id]
                    idx = branch_index[customer.branch_id] % len(candidate_users)
                    branch_index[customer.branch_id] += 1
                else:
                    candidate_users = list(sales_users)
                    idx = global_index % len(candidate_users)
                    global_index += 1

                if not candidate_users:
                    continue

                owner = candidate_users[idx]
                customer.owner_user = owner
                customer.owner_user_name = owner.name or owner.username
                customer.team_id = owner.team_id or customer.team_id
                customer.branch_id = owner.branch_id or customer.branch_id
                customer.hq_id = owner.headquarters_id or customer.hq_id
                customer.modifier = "system_init"
                customer.save(update_fields=["owner_user", "owner_user_name", "team_id", "branch_id", "hq_id", "modifier"])
                assigned_count += 1

        self.stdout.write(f"销售账号创建完成: {len(created_users)} 个，客户分配完成: {assigned_count} 条。")
