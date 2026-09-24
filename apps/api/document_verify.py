"""Document link validation: confirms a linked document is safe to reference
and records its real metadata, without executing or macro-processing anything.

Text extraction from documents is explicitly out of scope for this phase —
the brief allows it "only with a safe tool and proper permission," and no PDF
library is in the offline wheelhouse. That is a documented limitation, not a
silent gap: `security_status` never claims more than was actually checked.
"""
import re
from dataclasses import dataclass

import net_guard as ng

MAX_DOCUMENT_BYTES = 40 * 1024 * 1024
MAX_DOWNLOAD_FOR_HASH = 20 * 1024 * 1024

# Executable, script and macro-capable container formats are never accepted,
# regardless of what the server claims their Content-Type is.
BLOCKED_EXTENSIONS = {
    '.exe', '.dll', '.bat', '.cmd', '.com', '.scr', '.msi', '.ps1', '.sh',
    '.js', '.jse', '.vbs', '.vbe', '.wsf', '.jar', '.apk', '.app',
    '.docm', '.xlsm', '.pptm', '.dotm', '.xltm',  # macro-enabled Office
}
ALLOWED_MIME = {
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.ms-excel': '.xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'application/vnd.ms-powerpoint': '.ppt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
    'text/csv': '.csv', 'text/plain': '.txt',
}
MAGIC_BYTES = {
    b'%PDF-': 'application/pdf',
    b'PK\x03\x04': None,  # zip container: docx/xlsx/pptx all share this; MIME stays as declared
}


@dataclass
class DocumentCheck:
    security_status: str  # downloaded_safe | link_only | rejected | unavailable
    reason: str
    mime_type: str | None
    byte_size: int | None
    content_sha256: str | None


def _extension_of(url):
    path = url.split('?', 1)[0].split('#', 1)[0]
    dot = path.rfind('.')
    return path[dot:].lower() if dot > 0 and len(path) - dot <= 6 else ''


def check_document(url, *, download_for_hash=False):
    """HEAD the document first; only perform a bounded GET (for a hash) when
    explicitly asked and the HEAD result looks safe. Never follows more than
    the shared guard's redirect budget, and never trusts the extension alone."""
    ext = _extension_of(url)
    if ext in BLOCKED_EXTENSIONS:
        return DocumentCheck('rejected', f'blocked_extension:{ext}', None, None, None)

    try:
        head = ng.guarded_head(url)
    except ng.GuardError as exc:
        return DocumentCheck('unavailable', f'head_failed:{exc}', None, None, None)

    if head.status != 200:
        return DocumentCheck('unavailable', f'http_{head.status}', None, None, None)

    declared_mime = (head.headers.get('content-type') or '').split(';')[0].strip().lower()
    declared_len = head.headers.get('content-length')
    byte_size = int(declared_len) if declared_len and declared_len.isdigit() else None

    if declared_mime and declared_mime not in ALLOWED_MIME:
        return DocumentCheck('rejected', f'disallowed_mime:{declared_mime}', declared_mime, byte_size, None)
    if byte_size is not None and byte_size > MAX_DOCUMENT_BYTES:
        return DocumentCheck('rejected', f'too_large:{byte_size}', declared_mime, byte_size, None)

    if not download_for_hash:
        return DocumentCheck('link_only', 'head_only_by_policy', declared_mime or None, byte_size, None)

    try:
        got = ng.guarded_get(url, max_bytes=min(MAX_DOWNLOAD_FOR_HASH, MAX_DOCUMENT_BYTES))
    except ng.GuardError as exc:
        return DocumentCheck('link_only', f'download_failed_kept_link:{exc}', declared_mime or None, byte_size, None)

    real_mime = None
    for magic, mime in MAGIC_BYTES.items():
        if got.body.startswith(magic):
            real_mime = mime or declared_mime
            break
    if real_mime is None:
        return DocumentCheck('rejected', 'magic_bytes_did_not_match_a_known_document_type',
                              declared_mime, len(got.body), None)

    import hashlib
    digest = hashlib.sha256(got.body).hexdigest()
    return DocumentCheck('downloaded_safe', 'verified', real_mime, len(got.body), digest)
