"""IP 归属地解析（不打外网）。"""

from app.common.operation_log.ip_location import (
    is_public_ip,
    parse_ip_api_payload,
    parse_ipwho_payload,
)


def test_private_ip_is_not_public() -> None:
    assert is_public_ip("127.0.0.1") is False
    assert is_public_ip("192.168.1.8") is False
    assert is_public_ip("10.0.0.1") is False
    assert is_public_ip("::1") is False
    assert is_public_ip("") is False
    assert is_public_ip("not-an-ip") is False


def test_parse_ip_api_zh_cn() -> None:
    location = parse_ip_api_payload(
        {
            "status": "success",
            "country": "中国",
            "regionName": "安徽省",
            "city": "芜湖",
        }
    )
    assert location == {"country": "中国", "province": "安徽省", "city": "芜湖"}


def test_parse_ip_api_fail_status() -> None:
    assert parse_ip_api_payload({"status": "fail", "message": "private range"}) is None
    assert parse_ip_api_payload([]) is None


def test_parse_ipwho() -> None:
    location = parse_ipwho_payload(
        {
            "success": True,
            "country": "China",
            "region": "Anhui",
            "city": "Wuhu",
        }
    )
    assert location == {"country": "China", "province": "Anhui", "city": "Wuhu"}
    assert parse_ipwho_payload({"success": False}) is None
