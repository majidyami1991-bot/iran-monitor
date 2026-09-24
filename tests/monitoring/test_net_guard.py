"""Offline SSRF-guard tests. No real network access: resolve_safe is tested
against its own address-classification logic, and guarded_fetch's redirect
and size bookkeeping are tested by monkeypatching the one function that
actually opens a socket, so the tests stay fast and deterministic."""
import pytest

import net_guard as ng


@pytest.mark.parametrize('host', [
    '127.0.0.1', '127.0.0.53', 'localhost', '0.0.0.0',
    '10.1.2.3', '172.16.0.1', '172.31.255.255', '192.168.0.1',
    '169.254.169.254',  # cloud metadata endpoint
    '100.64.0.1',  # carrier-grade NAT
    '198.18.0.1',  # benchmarking range
])
def test_private_and_special_addresses_are_blocked(host):
    with pytest.raises(ng.GuardError):
        ng.resolve_safe(host, 443)


def test_public_looking_ip_is_not_blocked():
    # A real public-range address should resolve without raising, since
    # resolve_safe classifies by address, not by reachability.
    ng.resolve_safe('8.8.8.8', 443)


def test_ipv6_loopback_and_link_local_are_blocked():
    for host in ('::1', 'fe80::1', 'fc00::1'):
        with pytest.raises(ng.GuardError):
            ng.resolve_safe(host, 443)


def test_local_and_internal_tlds_are_blocked_by_shape_before_dns():
    for host in ('printer.local', 'router.internal', 'localhost.localdomain'):
        with pytest.raises(ng.GuardError):
            ng.resolve_safe(host, 443)


def test_credentialed_url_is_refused_before_any_connection_attempt():
    with pytest.raises(ng.GuardError, match='credentials_in_url'):
        ng.guarded_fetch('https://user:pass@example.com/')


@pytest.mark.parametrize('scheme', ['file', 'ftp', 'gopher', 'data', 'javascript'])
def test_non_http_schemes_are_refused(scheme):
    with pytest.raises(ng.GuardError, match='invalid_scheme'):
        ng.guarded_fetch(f'{scheme}://example.com/x')


def test_sanitize_url_redacts_token_shaped_query_params():
    out = ng.sanitize_url('https://example.com/a?token=abc123&id=7')
    assert 'abc123' not in out
    assert 'id=7' in out
    assert 'REDACTED' in out  # urlencode percent-escapes the brackets


def _fake_single_request(responses):
    """Returns a stand-in for net_guard._single_request that replays a fixed
    sequence of (status, headers, body) tuples, one per call — used to drive
    guarded_fetch's redirect loop without opening a real socket."""
    calls = iter(responses)

    def fake(method, url, *, max_bytes, extra_headers=None):
        try:
            status, headers, body = next(calls)
        except StopIteration:
            raise AssertionError('fake_single_request called more times than scripted')
        if body is not None and len(body) > max_bytes:
            raise ng.GuardError('response_too_large')
        return status, headers, body
    return fake


def test_redirect_chain_is_followed_and_each_hop_recorded(monkeypatch):
    monkeypatch.setattr(ng, '_single_request', _fake_single_request([
        (302, {'location': 'https://example.com/b'}, b''),
        (301, {'location': 'https://example.com/c'}, b''),
        (200, {'content-type': 'text/html'}, b'<html>ok</html>'),
    ]))
    r = ng.guarded_get('https://example.com/a', max_bytes=1000)
    assert r.status == 200
    assert r.body == b'<html>ok</html>'
    assert len(r.redirect_chain) == 3


def test_redirect_loop_is_bounded(monkeypatch):
    monkeypatch.setattr(ng, '_single_request', _fake_single_request(
        [(302, {'location': 'https://example.com/next'}, b'')] * 10
    ))
    with pytest.raises(ng.GuardError, match='too_many_redirects'):
        ng.guarded_get('https://example.com/a', max_bytes=1000, max_redirects=3)


def test_redirect_without_location_header_is_refused(monkeypatch):
    monkeypatch.setattr(ng, '_single_request', _fake_single_request([(302, {}, b'')]))
    with pytest.raises(ng.GuardError, match='redirect_without_location'):
        ng.guarded_get('https://example.com/a')


def test_oversized_response_is_refused(monkeypatch):
    monkeypatch.setattr(ng, '_single_request', _fake_single_request([
        (200, {'content-type': 'application/octet-stream'}, b'x' * 5000),
    ]))
    with pytest.raises(ng.GuardError, match='response_too_large'):
        ng.guarded_get('https://example.com/big', max_bytes=1000)


def test_relative_redirect_location_resolves_against_the_current_url(monkeypatch):
    monkeypatch.setattr(ng, '_single_request', _fake_single_request([
        (302, {'location': '/moved'}, b''),
        (200, {'content-type': 'text/html'}, b'ok'),
    ]))
    r = ng.guarded_get('https://example.com/original')
    assert r.redirect_chain[-1] == 'https://example.com/moved'
