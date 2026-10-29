import ipaddress
import socket
from urllib.parse import urlsplit

class UnsafeURL(ValueError):
    pass

def validate_public_url(url: str) -> str:
    """Accept only http(s) URLs resolving exclusively to public IPs."""
    if not isinstance(url, str) or len(url) > 2048:
        raise UnsafeURL("URL must be a string under 2048 characters.")
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnsafeURL("Enter a complete http:// or https:// URL.")
    if parts.username or parts.password:
        raise UnsafeURL("Credentials in URLs are not allowed.")
    try:
        port = parts.port
    except ValueError as exc:
        raise UnsafeURL("Invalid port.") from exc
    if port not in (None, 80, 443):
        raise UnsafeURL("Only standard HTTP(S) ports are allowed.")
    hostname = parts.hostname.rstrip(".").lower()
    if hostname in {"localhost"} or hostname.endswith((".local", ".internal")):
        raise UnsafeURL("Local hosts are not allowed.")
    try:
        addresses = socket.getaddrinfo(hostname, port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as exc:
        raise UnsafeURL("Hostname could not be resolved.") from exc
    if not addresses:
        raise UnsafeURL("Hostname could not be resolved.")
    for record in addresses:
        ip = ipaddress.ip_address(record[4][0])
        if not ip.is_global:
            raise UnsafeURL("Private or non-public addresses are blocked.")
    return url
