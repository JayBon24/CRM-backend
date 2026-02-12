import json
import os
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from customer_management.models import (
    Contract,
    FollowupRecord,
    LegalFee,
    RecoveryPayment,
    Schedule,
)
from dvadmin.system.models import FileList
from dvadmin.utils.aliyunoss import ali_oss_delete, aliyun_oss_extract_key
from dvadmin.utils.tencentcos import tencent_cos_delete, tencent_cos_extract_key


def _iter_attachment_items(payload):
    if payload is None:
        return
    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            return
        if text.startswith("{") or text.startswith("["):
            try:
                parsed = json.loads(text)
                yield from _iter_attachment_items(parsed)
                return
            except Exception:
                pass
        yield text
        return
    if isinstance(payload, dict):
        # 常见结构：{attachments:[...]} 或单个附件对象
        if "attachments" in payload and isinstance(payload.get("attachments"), list):
            for item in payload.get("attachments", []):
                yield from _iter_attachment_items(item)
            return
        yield payload
        return
    if isinstance(payload, list):
        for item in payload:
            yield from _iter_attachment_items(item)


def _normalize_url_variants(value):
    if not value:
        return set()
    raw = str(value).strip()
    if not raw:
        return set()
    no_query = raw.split("?", 1)[0].split("#", 1)[0].replace("\\", "/")
    variants = {no_query}
    if no_query.startswith("http://") or no_query.startswith("https://"):
        parsed = urlparse(no_query)
        if parsed.path:
            variants.add(parsed.path)
            variants.add(parsed.path.lstrip("/"))
    else:
        variants.add(no_query.lstrip("/"))
        if not no_query.startswith("/"):
            variants.add(f"/{no_query}")
    normalized = set()
    for item in variants:
        if not item:
            continue
        normalized.add(item)
        if item.startswith("media/"):
            normalized.add(item[len("media/"):])
            normalized.add(f"/{item}")
        if item.startswith("/media/"):
            normalized.add(item[1:])
            normalized.add(item[len("/media/"):])
    return normalized


def _extract_references(payload):
    ref_ids = set()
    ref_urls = set()
    ref_keys = set()
    for item in _iter_attachment_items(payload):
        if isinstance(item, str):
            ref_urls.update(_normalize_url_variants(item))
            ref_keys.add(tencent_cos_extract_key(item))
            ref_keys.add(aliyun_oss_extract_key(item))
            continue
        if not isinstance(item, dict):
            continue
        attachment_id = item.get("attachment_id") or item.get("file_id") or item.get("id")
        if attachment_id is not None and str(attachment_id).strip():
            ref_ids.add(str(attachment_id).strip())
        for url_key in ("url", "preview_url", "file_url", "path"):
            ref_urls.update(_normalize_url_variants(item.get(url_key)))
        for key_key in ("storage_key", "key", "object_key"):
            key_value = item.get(key_key)
            if key_value:
                ref_keys.add(str(key_value).strip().lstrip("/"))
        for url_key in ("url", "preview_url", "file_url"):
            key_from_url = tencent_cos_extract_key(item.get(url_key))
            if key_from_url:
                ref_keys.add(key_from_url)
            key_from_url = aliyun_oss_extract_key(item.get(url_key))
            if key_from_url:
                ref_keys.add(key_from_url)
    ref_keys = {key for key in ref_keys if key}
    return ref_ids, ref_urls, ref_keys


def _file_match_keys(file_obj):
    keys = set()
    urls = set()
    file_url = (getattr(file_obj, "file_url", "") or "").replace("\\", "/")
    url_field = str(getattr(file_obj, "url", "") or "").replace("\\", "/")
    urls.update(_normalize_url_variants(file_url))
    urls.update(_normalize_url_variants(url_field))
    if url_field:
        urls.update(_normalize_url_variants(f"media/{url_field}"))
        urls.update(_normalize_url_variants(f"/media/{url_field}"))
    keys.add(tencent_cos_extract_key(file_url))
    keys.add(tencent_cos_extract_key(url_field))
    keys.add(aliyun_oss_extract_key(file_url))
    keys.add(aliyun_oss_extract_key(url_field))
    return urls, {k for k in keys if k}


class Command(BaseCommand):
    help = "清理未被业务引用的历史上传文件（支持本地/COS/OSS）"

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=24, help="仅清理创建超过 N 小时的文件，默认 24")
        parser.add_argument("--limit", type=int, default=5000, help="本次最多处理文件数，默认 5000")
        parser.add_argument("--dry-run", action="store_true", help="仅打印，不实际删除")

    def _scan_model_field(self, model, field_name):
        qs = model.objects.all()
        if "is_deleted" in [field.name for field in model._meta.fields]:
            qs = qs.filter(is_deleted=False)
        for value in qs.values_list(field_name, flat=True).iterator(chunk_size=1000):
            yield value

    def _collect_references(self):
        ref_ids = set()
        ref_urls = set()
        ref_keys = set()
        sources = [
            (FollowupRecord, "attachments"),
            (Schedule, "attachments"),
            (Contract, "attachments"),
            (RecoveryPayment, "voucher_attachments"),
            (LegalFee, "voucher_attachments"),
        ]
        for model, field_name in sources:
            for payload in self._scan_model_field(model, field_name):
                ids, urls, keys = _extract_references(payload)
                ref_ids.update(ids)
                ref_urls.update(urls)
                ref_keys.update(keys)
        return ref_ids, ref_urls, ref_keys

    def _delete_file_object(self, file_obj):
        engine = (getattr(file_obj, "engine", "") or "local").lower()
        file_url = (getattr(file_obj, "file_url", "") or "").replace("\\", "/")
        local_deleted = False
        remote_deleted = False

        if engine == "cos":
            remote_deleted = tencent_cos_delete(file_url) or tencent_cos_delete(getattr(file_obj, "url", ""))
        elif engine == "oss":
            remote_deleted = ali_oss_delete(file_url) or ali_oss_delete(getattr(file_obj, "url", ""))
        else:
            # local: 优先走 storage.delete，回退直接删磁盘
            try:
                if file_obj.url and file_obj.url.name:
                    file_obj.url.storage.delete(file_obj.url.name)
                    local_deleted = True
            except Exception:
                pass
            if not local_deleted and file_url:
                local_path = file_url.lstrip("/").replace("\\", "/")
                if local_path.startswith("media/"):
                    local_path = local_path[len("media/"):]
                abs_path = os.path.join(settings.MEDIA_ROOT, local_path)
                if os.path.exists(abs_path):
                    os.remove(abs_path)
                    local_deleted = True

        return local_deleted or remote_deleted or engine in {"cos", "oss"}

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        hours = max(int(options["hours"]), 1)
        limit = max(int(options["limit"]), 1)
        cutoff = timezone.now() - timedelta(hours=hours)

        self.stdout.write(self.style.NOTICE(f"[cleanup] start: hours={hours}, limit={limit}, dry_run={dry_run}"))
        ref_ids, ref_urls, ref_keys = self._collect_references()
        self.stdout.write(
            self.style.NOTICE(
                f"[cleanup] reference stats: ids={len(ref_ids)}, urls={len(ref_urls)}, keys={len(ref_keys)}"
            )
        )

        qs = FileList.objects.filter(create_datetime__lt=cutoff)
        if "is_deleted" in [field.name for field in FileList._meta.fields]:
            qs = qs.filter(is_deleted=False)
        candidates = qs.order_by("create_datetime")[:limit]

        scanned = 0
        deleted = 0
        skipped = 0
        for file_obj in candidates:
            scanned += 1
            file_id = str(file_obj.id)
            if file_id in ref_ids:
                skipped += 1
                continue
            url_keys, storage_keys = _file_match_keys(file_obj)
            if ref_urls.intersection(url_keys) or ref_keys.intersection(storage_keys):
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"[dry-run] delete candidate id={file_obj.id}, engine={file_obj.engine}, file_url={file_obj.file_url}"
                )
                deleted += 1
                continue

            self._delete_file_object(file_obj)
            file_obj.delete()
            deleted += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"[cleanup] done: scanned={scanned}, deleted={deleted}, skipped={skipped}, dry_run={dry_run}"
            )
        )
