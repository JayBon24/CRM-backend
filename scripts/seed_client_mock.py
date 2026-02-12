import os
import sys
from pathlib import Path
from datetime import datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import connection, transaction


def _to_naive_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = parse_datetime(str(value))
    if not parsed:
        return None
    if timezone.is_aware(parsed):
        parsed = timezone.make_naive(parsed, timezone.get_current_timezone())
    return parsed


def _map_source_channel(value):
    if not value:
        return "OTHER"
    text = str(value)
    if "\u5b98\u7f51" in text or "\u5e7f\u544a" in text:
        return "ONLINE"
    if "\u8f6c\u4ecb" in text:
        return "REFERRAL"
    if "\u5c55\u4f1a" in text:
        return "OFFLINE"
    return "OTHER"


def _ensure_client_table():
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE 'client'")
        if cursor.fetchone():
            return
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS client (
                is_deleted tinyint(1) NOT NULL,
                id bigint NOT NULL AUTO_INCREMENT,
                description varchar(255) DEFAULT NULL,
                modifier varchar(255) DEFAULT NULL,
                dept_belong_id varchar(255) DEFAULT NULL,
                update_datetime datetime(6) DEFAULT NULL,
                create_datetime datetime(6) DEFAULT NULL,
                name varchar(200) NOT NULL,
                contact_person varchar(100) DEFAULT NULL,
                contact_phone varchar(50) DEFAULT NULL,
                status varchar(20) NOT NULL DEFAULT 'PUBLIC_POOL',
                grade varchar(10) NOT NULL DEFAULT 'C',
                source varchar(20) NOT NULL DEFAULT 'OTHER',
                owner_user_id int DEFAULT NULL,
                team_id int DEFAULT NULL,
                branch_id int DEFAULT NULL,
                remark longtext,
                creator_id bigint DEFAULT NULL,
                PRIMARY KEY (id),
                KEY client_is_deleted_idx (is_deleted),
                KEY client_creator_id_idx (creator_id),
                KEY client_status_idx (status),
                KEY client_grade_idx (grade),
                KEY client_source_idx (source),
                KEY client_owner_user_id_idx (owner_user_id),
                KEY client_team_id_idx (team_id),
                KEY client_branch_id_idx (branch_id),
                KEY client_status_1af351_idx (status, owner_user_id),
                KEY client_grade_1e6559_idx (grade, status),
                KEY client_source_2e6c75_idx (source, status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """
        )


def _setup_django():
    base_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(base_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")
    import django

    django.setup()


def main():
    _setup_django()

    from customer_management.views.crm.client_views import _generate_mock_clients

    _ensure_client_table()

    mock_clients = _generate_mock_clients()
    if not mock_clients:
        print("No mock clients generated.")
        return

    with transaction.atomic():
        with connection.cursor() as cursor:
            for client in mock_clients:
                create_dt = _to_naive_datetime(client.get("create_datetime")) or timezone.now()
                update_dt = _to_naive_datetime(client.get("update_datetime")) or timezone.now()
                cursor.execute(
                    """
                    INSERT INTO client (
                        id,
                        name,
                        contact_person,
                        contact_phone,
                        status,
                        grade,
                        source,
                        owner_user_id,
                        team_id,
                        branch_id,
                        remark,
                        is_deleted,
                        create_datetime,
                        update_datetime,
                        creator_id,
                        description,
                        modifier,
                        dept_belong_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        contact_person = VALUES(contact_person),
                        contact_phone = VALUES(contact_phone),
                        status = VALUES(status),
                        grade = VALUES(grade),
                        source = VALUES(source),
                        owner_user_id = VALUES(owner_user_id),
                        team_id = VALUES(team_id),
                        branch_id = VALUES(branch_id),
                        remark = VALUES(remark),
                        is_deleted = VALUES(is_deleted),
                        update_datetime = VALUES(update_datetime),
                        create_datetime = VALUES(create_datetime),
                        creator_id = VALUES(creator_id),
                        description = VALUES(description),
                        modifier = VALUES(modifier),
                        dept_belong_id = VALUES(dept_belong_id)
                    """,
                    [
                        client.get("id"),
                        client.get("client_name"),
                        client.get("contact_name"),
                        client.get("mobile"),
                        client.get("status") or "PUBLIC_POOL",
                        client.get("client_grade") or client.get("grade") or "C",
                        _map_source_channel(client.get("source_channel")),
                        client.get("owner_user_id"),
                        client.get("team_id"),
                        client.get("branch_id"),
                        client.get("remark"),
                        0,
                        create_dt,
                        update_dt,
                        None,
                        None,
                        None,
                        None,
                    ],
                )

    print(f"Synced {len(mock_clients)} mock clients to client table.")


if __name__ == "__main__":
    main()
