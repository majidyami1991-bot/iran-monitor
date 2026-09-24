"""Offline document verification tests. net_guard calls are monkeypatched so
these run without network access."""
import hashlib
from types import SimpleNamespace

import pytest

import document_verify as dv
import net_guard as ng


def _resp(status, headers, body=b''):
    return SimpleNamespace(status=status, headers=headers, body=body)


@pytest.mark.parametrize('ext', ['.exe', '.bat', '.js', '.docm', '.jar', '.apk'])
def test_executable_and_macro_extensions_are_rejected_without_any_request(ext, monkeypatch):
    called = []
    monkeypatch.setattr(ng, 'guarded_head', lambda *a, **k: called.append(1))
    result = dv.check_document(f'https://example.com/file{ext}')
    assert result.security_status == 'rejected'
    assert not called, 'must reject by extension before making any request'


def test_pdf_head_only_by_default_is_link_only(monkeypatch):
    monkeypatch.setattr(ng, 'guarded_head', lambda url: _resp(
        200, {'content-type': 'application/pdf', 'content-length': '12345'}))
    result = dv.check_document('https://example.com/report.pdf', download_for_hash=False)
    assert result.security_status == 'link_only'
    assert result.mime_type == 'application/pdf'
    assert result.byte_size == 12345
    assert result.content_sha256 is None


def test_pdf_download_verifies_magic_bytes_and_hashes(monkeypatch):
    body = b'%PDF-1.4\n%fake pdf body for testing\n%%EOF'
    monkeypatch.setattr(ng, 'guarded_head', lambda url: _resp(
        200, {'content-type': 'application/pdf', 'content-length': str(len(body))}))
    monkeypatch.setattr(ng, 'guarded_get', lambda url, **k: _resp(200, {}, body))
    result = dv.check_document('https://example.com/report.pdf', download_for_hash=True)
    assert result.security_status == 'downloaded_safe'
    assert result.content_sha256 == hashlib.sha256(body).hexdigest()


def test_declared_pdf_whose_bytes_are_actually_html_is_rejected(monkeypatch):
    # A server that serves an HTML error/login page at a .pdf-shaped URL but
    # claims Content-Type: application/pdf — the magic-byte check must catch
    # what the declared MIME lied about.
    body = b'<html><body>Please log in</body></html>'
    monkeypatch.setattr(ng, 'guarded_head', lambda url: _resp(
        200, {'content-type': 'application/pdf', 'content-length': str(len(body))}))
    monkeypatch.setattr(ng, 'guarded_get', lambda url, **k: _resp(200, {}, body))
    result = dv.check_document('https://example.com/fake.pdf', download_for_hash=True)
    assert result.security_status == 'rejected'
    assert 'magic_bytes' in result.reason


def test_disallowed_mime_is_rejected(monkeypatch):
    monkeypatch.setattr(ng, 'guarded_head', lambda url: _resp(
        200, {'content-type': 'application/x-msdownload', 'content-length': '999'}))
    result = dv.check_document('https://example.com/thing.bin')
    assert result.security_status == 'rejected'
    assert 'disallowed_mime' in result.reason


def test_oversized_document_is_rejected_from_head_alone(monkeypatch):
    monkeypatch.setattr(ng, 'guarded_head', lambda url: _resp(
        200, {'content-type': 'application/pdf', 'content-length': str(dv.MAX_DOCUMENT_BYTES + 1)}))
    result = dv.check_document('https://example.com/huge.pdf')
    assert result.security_status == 'rejected'
    assert 'too_large' in result.reason


def test_head_failure_is_unavailable_not_rejected(monkeypatch):
    def raise_guard(url):
        raise ng.GuardError('connect_failed:TimeoutError')
    monkeypatch.setattr(ng, 'guarded_head', raise_guard)
    result = dv.check_document('https://example.com/report.pdf')
    assert result.security_status == 'unavailable'


def test_non_200_head_is_unavailable(monkeypatch):
    monkeypatch.setattr(ng, 'guarded_head', lambda url: _resp(403, {}))
    result = dv.check_document('https://example.com/blocked.pdf')
    assert result.security_status == 'unavailable'
    assert 'http_403' in result.reason


def test_download_failure_after_a_safe_head_falls_back_to_link_only(monkeypatch):
    monkeypatch.setattr(ng, 'guarded_head', lambda url: _resp(
        200, {'content-type': 'application/pdf', 'content-length': '500'}))
    def raise_guard(url, **k):
        raise ng.GuardError('response_too_large')
    monkeypatch.setattr(ng, 'guarded_get', raise_guard)
    result = dv.check_document('https://example.com/report.pdf', download_for_hash=True)
    assert result.security_status == 'link_only'
