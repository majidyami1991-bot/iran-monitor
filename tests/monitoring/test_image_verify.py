"""Offline image header verification tests. Fixtures are hand-built minimal
headers for each format — no network, no binary fixture files needed."""
import struct

import image_verify as iv


def _png_bytes(width, height):
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    chunk = struct.pack('>I', len(ihdr_data)) + b'IHDR' + ihdr_data + b'\x00\x00\x00\x00'
    return sig + chunk


def _gif_bytes(width, height):
    return b'GIF89a' + struct.pack('<HH', width, height) + b'\x00' * 3


def _jpeg_bytes(width, height):
    soi = b'\xff\xd8'
    # A minimal APP0 segment, then a baseline SOF0 with real dimensions.
    app0 = b'\xff\xe0' + struct.pack('>H', 16) + b'JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    sof0_payload = struct.pack('>BHHB', 8, height, width, 1) + b'\x01\x11\x00'
    sof0 = b'\xff\xc0' + struct.pack('>H', len(sof0_payload) + 2) + sof0_payload
    return soi + app0 + sof0


def _webp_vp8x_bytes(width, height):
    chunk = b'VP8X' + b'\x00' * 4 + b'\x00\x00\x00' + struct.pack('<I', ((width - 1) | ((height - 1) << 24)) & 0xFFFFFFFF)
    riff_body = chunk
    return b'RIFF' + struct.pack('<I', len(riff_body) + 4) + b'WEBP' + riff_body


def test_png_dimensions_are_read_from_the_ihdr_chunk():
    info = iv.verify_image(_png_bytes(1200, 800))
    assert info.mime_type == 'image/png'
    assert (info.width, info.height) == (1200, 800)


def test_gif_dimensions_are_read():
    info = iv.verify_image(_gif_bytes(300, 250))
    assert info.mime_type == 'image/gif'
    assert (info.width, info.height) == (300, 250)


def test_jpeg_dimensions_are_read_from_sof0():
    info = iv.verify_image(_jpeg_bytes(1024, 576))
    assert info.mime_type == 'image/jpeg'
    assert (info.width, info.height) == (1024, 576)


def test_unrecognized_bytes_return_none_not_a_guess():
    assert iv.verify_image(b'this is not an image, just html <html>') is None
    assert iv.verify_image(b'') is None
    assert iv.verify_image(b'\x00\x01\x02') is None


def test_html_error_page_served_with_an_image_extension_is_rejected():
    # The classic "404.jpg is actually an HTML error page" case: an attacker
    # or a broken CDN can serve HTML at an image-shaped URL. The declared
    # extension must never substitute for verifying the real bytes.
    html_body = b'<!DOCTYPE html><html><body>Not Found</body></html>'
    assert iv.verify_image(html_body) is None


def test_meets_minimum_size_true_for_large_image():
    assert iv.meets_minimum_size(iv.verify_image(_png_bytes(800, 600))) is True


def test_meets_minimum_size_false_for_small_image():
    assert iv.meets_minimum_size(iv.verify_image(_png_bytes(80, 60))) is False


def test_meets_minimum_size_none_when_dimensions_unknown():
    assert iv.meets_minimum_size(None) is None


def test_truncated_png_does_not_raise():
    # A response cut short mid-download must be handled safely, not crash
    # the enrichment worker.
    assert iv.verify_image(b'\x89PNG\r\n\x1a\n\x00\x00\x00') is None


def test_truncated_jpeg_reports_unknown_dimensions_rather_than_crashing():
    info = iv.verify_image(b'\xff\xd8\xff\xe0\x00\x02')
    assert info is None or info.width is None
