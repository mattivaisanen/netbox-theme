"""
Logos are stored in the database as `data:` URIs, so they need no media
storage, work the same in every NetBox container and travel inside exported
theme files. The type is decided from the file's content, never its name.
"""
import base64
import binascii
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .settings import get_setting

# Where logos go: the sidebar and the login page, each per mode. Model fields
# are `logo_<slot>`.
SLOTS = ('light', 'dark', 'login_light', 'login_dark')

DATA_URI = re.compile(r'^data:(?P<type>image/[a-z0-9.+-]+);base64,(?P<data>[A-Za-z0-9+/=\s]*)$')


def sniff(data):
    """The image type of `data`, or None if it is not a logo we accept."""
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    head = data[:2048].lstrip(b'\xef\xbb\xbf \t\r\n').lower()
    if head.startswith((b'<svg', b'<?xml', b'<!--', b'<!doctype svg')) and b'<svg' in data[:65536].lower():
        return 'image/svg+xml'
    return None


def to_data_uri(data):
    """A logo file's bytes as a `data:` URI. Raises ValidationError."""
    limit = get_setting('max_logo_kb') * 1024
    if len(data) > limit:
        raise ValidationError(_('Logo is larger than {kb} KB.').format(kb=get_setting('max_logo_kb')))
    content_type = sniff(data)
    if content_type is None:
        raise ValidationError(_('Logo must be an SVG, PNG, JPEG, GIF or WebP image.'))
    return f'data:{content_type};base64,{base64.b64encode(data).decode()}'


def check_data_uri(uri):
    """An imported logo: re-checked as if it were uploaded. '' stays ''."""
    if not uri:
        return ''
    if not isinstance(uri, str):
        raise ValidationError(_('Logo is not a base64 data: URI.'))
    _content_type, data = from_data_uri(uri)
    return to_data_uri(data)


def from_data_uri(uri):
    """(content type, bytes) of a stored logo. Raises ValidationError."""
    match = DATA_URI.match(uri or '')
    if not match:
        raise ValidationError(_('Logo is not a base64 data: URI.'))
    try:
        data = base64.b64decode(match['data'], validate=False)
    except (binascii.Error, ValueError):
        raise ValidationError(_('Logo is not valid base64.'))
    return match['type'], data
