"""免费 IP 归属地查询（失败则放弃，不抛给调用方）。"""

from __future__ import annotations

import ipaddress
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from typing import TypedDict

_TIMEOUT_SECONDS = 3
_CACHE_MAX = 2048
_cache_lock = threading.Lock()
_cache: OrderedDict[str, IpLocation | None] = OrderedDict()


class IpLocation(TypedDict):
    """国家 / 省 / 市。"""

    country: str | None
    province: str | None
    city: str | None


def is_public_ip(ip: str) -> bool:
    """仅对公网地址发起查询。"""
    text = (ip or "").strip()
    if not text:
        return False
    host = text.split("%", 1)[0]
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return False


def lookup_ip_location(ip: str) -> IpLocation | None:
    """查国家/省/市；内网、失败、限流均返回 None。带进程内缓存。"""
    host = (ip or "").strip().split("%", 1)[0]
    if not is_public_ip(host):
        return None
    hit, cached = _cache_lookup(host)
    if hit:
        return cached
    location = _fetch_ip_api(host) or _fetch_ipwho(host)
    _cache_put(host, location)
    return location


def parse_ip_api_payload(payload: object) -> IpLocation | None:
    """解析 ip-api.com JSON。"""
    if not isinstance(payload, dict):
        return None
    status = payload.get("status")
    if status != "success":
        return None
    return _clean_location(
        country=_as_text(payload.get("country")),
        province=_as_text(payload.get("regionName")),
        city=_as_text(payload.get("city")),
    )


def parse_ipwho_payload(payload: object) -> IpLocation | None:
    """解析 ipwho.is JSON。"""
    if not isinstance(payload, dict):
        return None
    if payload.get("success") is not True:
        return None
    return _clean_location(
        country=_as_text(payload.get("country")),
        province=_as_text(payload.get("region")),
        city=_as_text(payload.get("city")),
    )


def _fetch_ip_api(ip: str) -> IpLocation | None:
    query = urllib.parse.urlencode({"fields": "status,country,regionName,city", "lang": "zh-CN"})
    url = f"http://ip-api.com/json/{urllib.parse.quote(ip)}?{query}"
    return parse_ip_api_payload(_http_json(url))


def _fetch_ipwho(ip: str) -> IpLocation | None:
    url = f"https://ipwho.is/{urllib.parse.quote(ip)}"
    return parse_ipwho_payload(_http_json(url))


def _http_json(url: str) -> object | None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "stamping-costing-platform/operation-log"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8", errors="replace")
        loaded: object = json.loads(body)
        return loaded
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None


def _as_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text in {"-", "XX", "N/A", "Unknown", "unknown"}:
        return None
    return text[:64]


def _clean_location(
    *,
    country: str | None,
    province: str | None,
    city: str | None,
) -> IpLocation | None:
    if not country and not province and not city:
        return None
    return {"country": country, "province": province, "city": city}


def _cache_lookup(ip: str) -> tuple[bool, IpLocation | None]:
    with _cache_lock:
        if ip not in _cache:
            return False, None
        _cache.move_to_end(ip)
        return True, _cache[ip]


def _cache_put(ip: str, location: IpLocation | None) -> None:
    with _cache_lock:
        _cache[ip] = location
        _cache.move_to_end(ip)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
