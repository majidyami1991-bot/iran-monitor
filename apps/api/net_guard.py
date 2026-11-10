"""SSRF-guarded HTTP fetching shared by article, image and document retrieval.

Every enrichment fetch in this phase goes through `guarded_get` or
`guarded_head`. The guard resolves DNS itself and validates every candidate
address before connecting — checking only the hostname string is not enough,
because a hostname can resolve to a private address (DNS rebinding), and a
redirect target must be re-validated the same way, not trusted because the
first hop passed.
"""
import ipaddress, re, socket, ssl, time
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

MAX_REDIRECTS = 3
CONNECT_TIMEOUT = 8
READ_TIMEOUT = 20
DEFAULT_MAX_BYTES = 8 * 1024 * 1024
UA = 'DefenceMonitor/1.0 (bounded enrichment fetch; project news-feed collector)'

# IANA special-purpose address blocks that must never be reachable from here:
# loopback, link-local (includes the 169.254.169.254 cloud metadata address),
# private ranges, carrier-grade NAT, documentation ranges, multicast/reserved.
_BLOCKED_NETS = [ipaddress.ip_network(n) for n in (
    '0.0.0.0/8', '10.0.0.0/8', '100.64.0.0/10', '127.0.0.0/8', '169.254.0.0/16',
    '172.16.0.0/12', '192.0.0.0/24', '192.0.2.0/24', '192.168.0.0/16',
    '198.18.0.0/15', '198.51.100.0/24', '203.0.113.0/24', '224.0.0.0/4', '240.0.0.0/4',
    '::1/128', 'fc00::/7', 'fe80::/10', '::ffff:0:0/96', '64:ff9b::/96', '100::/64',
)]


class GuardError(RuntimeError):
    """Raised for any policy refusal: bad scheme, blocked address, oversized
    response, too many redirects, bad MIME. The message is always safe to log."""


def _redact(text):
    text = re.sub(r'(?i)(password|secret|token|authorization|api[_-]?key)(\s*[:=]\s*)[^\s,;]+', r'\1\2[REDACTED]', text or '')
    return re.sub(r'[\r\n\t]+', ' ', text)[:240]


def sanitize_url(value):
    """Strip credential-shaped query parameters before a URL is ever logged."""
    try:
        p = urlsplit(value)
        query = [(k, '[REDACTED]' if re.search(r'(?i)(token|key|secret|auth|password|signature|sig)', k) else v)
                 for k, v in parse_qsl(p.query, keep_blank_values=True)]
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode(query), ''))
    except Exception:
        return '[URL]'


def _validate_hostname_shape(hostname):
    if not hostname or hostname.lower() in ('localhost', 'localhost.localdomain'):
        raise GuardError('blocked_host')
    if hostname.endswith('.local') or hostname.endswith('.internal'):
        raise GuardError('blocked_host')


def resolve_safe(hostname, port):
    """Resolve a hostname and return only addresses outside every blocked
    range. Raises if resolution fails or every candidate is blocked — this is
    the DNS-rebinding defense: validated at fetch time, not registration time."""
    _validate_hostname_shape(hostname)
    try:
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise GuardError(f'dns_resolution_failed:{type(exc).__name__}') from exc
    safe = []
    for family, _, _, _, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if any(ip in net for net in _BLOCKED_NETS) or ip.is_reserved or ip.is_unspecified:
            continue
        safe.append((family, sockaddr[0]))
    if not safe:
        raise GuardError('resolved_address_blocked')
    return safe


@dataclass
class GuardedResponse:
    status: int
    headers: dict
    body: bytes
    final_url: str
    redirect_chain: list


def _single_request(method, url, *, max_bytes, extra_headers=None):
    p = urlsplit(url)
    if p.scheme not in ('http', 'https'):
        raise GuardError('invalid_scheme')
    if p.username or p.password:
        raise GuardError('credentials_in_url')
    port = p.port or (443 if p.scheme == 'https' else 80)
    safe_addrs = resolve_safe(p.hostname, port)
    family, ip = safe_addrs[0]

    # Connect to the validated IP directly (never let the standard library
    # re-resolve the hostname itself, which would reopen the DNS-rebinding
    # window) while keeping the original hostname for the Host header / SNI.
    raw_sock = socket.socket(family, socket.SOCK_STREAM)
    raw_sock.settimeout(CONNECT_TIMEOUT)
    try:
        raw_sock.connect((ip, port))
    except OSError as exc:
        raw_sock.close()
        raise GuardError(f'connect_failed:{type(exc).__name__}') from exc
    raw_sock.settimeout(READ_TIMEOUT)

    if p.scheme == 'https':
        ctx = ssl.create_default_context()
        wrapped = ctx.wrap_socket(raw_sock, server_hostname=p.hostname)
        conn = HTTPSConnection(p.hostname, port, timeout=READ_TIMEOUT)
        conn.sock = wrapped
    else:
        conn = HTTPConnection(p.hostname, port, timeout=READ_TIMEOUT)
        conn.sock = raw_sock

    headers = {'User-Agent': UA, 'Accept-Encoding': 'identity'}
    headers.update(extra_headers or {})
    path = urlunsplit(('', '', p.path or '/', p.query, ''))
    try:
        conn.request(method, path, headers=headers)
        resp = conn.getresponse()
        status = resp.status
        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        body = b''
        if method != 'HEAD':
            declared = resp_headers.get('content-length')
            if declared and int(declared) > max_bytes:
                raise GuardError('response_too_large')
            chunks, total = [], 0
            while True:
                chunk = resp.read(min(65536, max_bytes + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > max_bytes:
                    raise GuardError('response_too_large')
            body = b''.join(chunks)
        return status, resp_headers, body
    finally:
        conn.close()


def guarded_fetch(url, *, method='GET', max_bytes=DEFAULT_MAX_BYTES, max_redirects=MAX_REDIRECTS, extra_headers=None):
    """SSRF-guarded HTTP fetch with bounded, individually-validated redirects.

    Every hop — including the first — is resolved and checked against the
    blocked-address list; a redirect to a private address is refused exactly
    like a direct request to one would be.
    """
    chain = []
    current = url
    for _ in range(max_redirects + 1):
        chain.append(sanitize_url(current))
        status, headers, body = _single_request(method, current, max_bytes=max_bytes, extra_headers=extra_headers)
        if status in (301, 302, 303, 307, 308):
            location = headers.get('location')
            if not location:
                raise GuardError('redirect_without_location')
            nxt = location if '://' in location else urlunsplit(urlsplit(current)[:2] + urlsplit(location)[2:])
            if len(chain) > max_redirects:
                raise GuardError('too_many_redirects')
            current = nxt
            continue
        return GuardedResponse(status=status, headers=headers, body=body, final_url=current, redirect_chain=chain)
    raise GuardError('too_many_redirects')


def guarded_get(url, *, max_bytes=DEFAULT_MAX_BYTES, max_redirects=MAX_REDIRECTS):
    return guarded_fetch(url, method='GET', max_bytes=max_bytes, max_redirects=max_redirects)


def guarded_head(url, *, max_redirects=MAX_REDIRECTS):
    return guarded_fetch(url, method='HEAD', max_bytes=0, max_redirects=max_redirects)
