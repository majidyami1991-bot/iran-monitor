"""Verify an image's real MIME type and dimensions from its actual bytes.

No image library is added for this: PIL/Pillow is not in the collector's
offline wheelhouse, and pulling one in for header parsing alone is not
justified. PNG, JPEG, GIF and WEBP headers are simple, well-documented binary
formats; this parses only the fixed-size header fields needed to confirm what
was declared in HTML actually matches the downloaded bytes; it never decodes
pixel data.
"""
import struct
from dataclasses import dataclass

MIN_DIMENSION = 200
MAX_HEADER_BYTES = 64 * 1024


@dataclass
class ImageInfo:
    mime_type: str
    width: int | None
    height: int | None


def _png(data):
    if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data) < 24:
        return None
    if data[12:16] != b'IHDR':
        return None
    width, height = struct.unpack('>II', data[16:24])
    return ImageInfo('image/png', width, height)


def _gif(data):
    if not (data.startswith(b'GIF87a') or data.startswith(b'GIF89a')) or len(data) < 10:
        return None
    width, height = struct.unpack('<HH', data[6:10])
    return ImageInfo('image/gif', width, height)


def _jpeg(data):
    if not data.startswith(b'\xff\xd8'):
        return None
    i, n = 2, len(data)
    while i + 4 <= n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker == 0xD9:  # EOI reached before a SOF marker
            break
        if i + 4 > n:
            break
        seg_len = struct.unpack('>H', data[i + 2:i + 4])[0]
        # SOFn markers (baseline/progressive), excluding DHT(C4)/JPG(C8)/DAC(CC)
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if i + 9 > n:
                return ImageInfo('image/jpeg', None, None)
            height, width = struct.unpack('>HH', data[i + 5:i + 9])
            return ImageInfo('image/jpeg', width, height)
        i += 2 + seg_len
    return ImageInfo('image/jpeg', None, None) if data.startswith(b'\xff\xd8') else None


def _webp(data):
    if not (data.startswith(b'RIFF') and len(data) >= 30 and data[8:12] == b'WEBP'):
        return None
    chunk = data[12:16]
    if chunk == b'VP8 ' and len(data) >= 30:
        width, height = struct.unpack('<HH', data[26:30])
        return ImageInfo('image/webp', width & 0x3FFF, height & 0x3FFF)
    if chunk == b'VP8L' and len(data) >= 25:
        b = data[21:25]
        bits = int.from_bytes(b, 'little')
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return ImageInfo('image/webp', width, height)
    if chunk == b'VP8X' and len(data) >= 30:
        width = int.from_bytes(data[24:27], 'little') + 1
        height = int.from_bytes(data[27:30], 'little') + 1
        return ImageInfo('image/webp', width, height)
    return ImageInfo('image/webp', None, None)


_PARSERS = (_png, _jpeg, _gif, _webp)


def verify_image(data):
    """Return an ImageInfo for supported formats, or None if the bytes don't
    match a known image header — the caller must treat that as untrusted,
    never as "trust the declared type"."""
    if not data:
        return None
    head = data[:MAX_HEADER_BYTES]
    for parser in _PARSERS:
        info = parser(head)
        if info is not None:
            return info
    return None


def meets_minimum_size(info):
    if info is None or info.width is None or info.height is None:
        return None  # unknown, not "fails"
    return info.width >= MIN_DIMENSION and info.height >= MIN_DIMENSION
