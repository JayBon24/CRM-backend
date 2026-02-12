import os
import tempfile
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from ai_management.services.ocr_service import TencentOCRService

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional dependency
    fitz = None

try:
    from docx import Document
except Exception:  # pragma: no cover - optional dependency
    Document = None


IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff'}


class DocumentExtractService:
    def __init__(self):
        self.ocr_service = TencentOCRService()

    def extract(
        self,
        url: str,
        file_name: Optional[str] = None,
        force_ocr: bool = False,
        ocr_all_pages: bool = False,
        ocr_page_limit: int = 0,
    ) -> Dict[str, Any]:
        if not url:
            raise ValueError("url is required")

        local_path, cleanup_path = self._resolve_to_local_path(url)
        try:
            ext = self._get_ext(file_name or local_path or url)
            if ext in IMAGE_EXTS:
                return self._extract_image(local_path)
            if ext == '.pdf':
                return self._extract_pdf(
                    local_path,
                    force_ocr=force_ocr,
                    ocr_all_pages=ocr_all_pages,
                    ocr_page_limit=ocr_page_limit,
                )
            if ext in {'.docx', '.doc'}:
                return self._extract_docx(local_path)
            if ext in {'.txt', '.md'}:
                return self._extract_text_file(local_path)

            raise ValueError(f"unsupported file type: {ext or 'unknown'}")
        finally:
            if cleanup_path:
                try:
                    os.remove(cleanup_path)
                except Exception:
                    pass

    def _resolve_to_local_path(self, url: str) -> Tuple[str, Optional[str]]:
        parsed = urlparse(url)
        raw_path = parsed.path if parsed.scheme in ('http', 'https') else url
        raw_path = raw_path.split('?', 1)[0]

        media_url = (settings.MEDIA_URL or '/media/').rstrip('/') + '/'
        media_root = getattr(settings, 'MEDIA_ROOT', '')

        if raw_path.startswith(media_url):
            rel = raw_path[len(media_url):]
            local_path = os.path.join(media_root, rel)
            if os.path.exists(local_path):
                return local_path, None

        if raw_path.startswith('/media/'):
            rel = raw_path[len('/media/'):]
            local_path = os.path.join(media_root, rel)
            if os.path.exists(local_path):
                return local_path, None

        if raw_path.startswith('media/'):
            local_path = os.path.join(media_root, raw_path[len('media/'):])
            if os.path.exists(local_path):
                return local_path, None

        if parsed.scheme in ('http', 'https'):
            return self._download_to_temp(url)

        if os.path.exists(raw_path):
            return raw_path, None

        raise ValueError("file not found")

    def _download_to_temp(self, url: str) -> Tuple[str, Optional[str]]:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        suffix = os.path.splitext(urlparse(url).path)[1] or ''
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp.write(response.content)
        temp.flush()
        temp.close()
        return temp.name, temp.name

    def _get_ext(self, path: str) -> str:
        return os.path.splitext(path)[1].lower()

    def _extract_text_file(self, path: str) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
            content = handle.read()
        return {
            'text': content.strip(),
            'method': 'text',
            'page_count': 1,
            'ocr_pages': 0,
            'warnings': [],
        }

    def _extract_docx(self, path: str) -> Dict[str, Any]:
        if Document is None:
            raise ValueError("python-docx is not available")
        doc = Document(path)
        lines = [p.text for p in doc.paragraphs if p.text]
        return {
            'text': "\n".join(lines).strip(),
            'method': 'text',
            'page_count': 1,
            'ocr_pages': 0,
            'warnings': [],
        }

    def _extract_image(self, path: str) -> Dict[str, Any]:
        with open(path, 'rb') as handle:
            content = handle.read()
        uploaded = SimpleUploadedFile(os.path.basename(path), content)
        result = self.ocr_service.recognize_general(uploaded)
        text = (result or {}).get('rawText', '') or ''
        return {
            'text': text.strip(),
            'method': 'ocr',
            'page_count': 1,
            'ocr_pages': 1,
            'warnings': [],
        }

    def _extract_pdf(
        self,
        path: str,
        force_ocr: bool = False,
        ocr_all_pages: bool = False,
        ocr_page_limit: int = 0,
    ) -> Dict[str, Any]:
        if fitz is None:
            raise ValueError("PyMuPDF is not available")

        doc = fitz.open(path)
        try:
            page_count = doc.page_count
            text_parts = []

            for page in doc:
                page_text = page.get_text("text").strip()
                if page_text:
                    text_parts.append(page_text)

            extracted_text = "\n".join(text_parts).strip()
            warnings = []

            ocr_text = ''
            if force_ocr or not extracted_text:
                ocr_pages = page_count if ocr_all_pages else min(1, page_count)
                if ocr_page_limit and ocr_page_limit > 0:
                    ocr_pages = min(ocr_pages, ocr_page_limit)
                ocr_text = self._ocr_pdf_pages(doc, ocr_pages)
            else:
                ocr_pages = 0

            if extracted_text and ocr_text:
                method = 'text+ocr'
                text = f"{extracted_text}\n{ocr_text}".strip()
            elif ocr_text:
                method = 'ocr'
                text = ocr_text.strip()
            else:
                method = 'text'
                text = extracted_text.strip()

            if not text:
                warnings.append('no_text_extracted')

            return {
                'text': text,
                'method': method,
                'page_count': page_count,
                'ocr_pages': ocr_pages,
                'warnings': warnings,
            }
        finally:
            doc.close()

    def _ocr_pdf_pages(self, doc, pages: int) -> str:
        lines = []
        for index in range(pages):
            page = doc.load_page(index)
            pix = page.get_pixmap(dpi=200, alpha=False)
            image_bytes = pix.tobytes("png")
            uploaded = SimpleUploadedFile(f"page_{index + 1}.png", image_bytes)
            result = self.ocr_service.recognize_general(uploaded)
            text = (result or {}).get('rawText', '') or ''
            if text.strip():
                lines.append(text.strip())
        return "\n".join(lines)
