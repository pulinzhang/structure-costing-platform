"""启动完成日志要带上从进程创建到就绪的耗时。"""

import logging
import re
import time

import pytest

from app.bootstrap.lifecycle import (
    _decimal_seconds_to_ns,
    _format_elapsed_seconds,
    _log_startup,
    _startup_elapsed_ns,
    _unix_ns_from_proc_stat,
)


def test_proc_stat_start_uses_field_22_after_comm() -> None:
    fields = ["S", *["0"] * 18, "1000"]
    stat_text = "1 (python (main)) " + " ".join(fields)
    now_ns = 1_700_000_000_000_000_000
    started = _unix_ns_from_proc_stat(
        stat_text,
        uptime_ns=12_500_000_000,
        now_ns=now_ns,
        clock_ticks=100,
    )
    assert started == now_ns - 2_500_000_000


def test_proc_stat_rejects_short_or_broken_text() -> None:
    assert _unix_ns_from_proc_stat("no-paren", uptime_ns=1, now_ns=1, clock_ticks=100) is None
    assert _unix_ns_from_proc_stat("1 (py) S 0", uptime_ns=1, now_ns=1, clock_ticks=100) is None
    broken = "1 (py) " + " ".join(["S", *["0"] * 18, "x"])
    assert _unix_ns_from_proc_stat(broken, uptime_ns=1, now_ns=1, clock_ticks=100) is None
    zero_tick = "1 (py) " + " ".join(["S", *["0"] * 18, "1000"])
    assert _unix_ns_from_proc_stat(zero_tick, uptime_ns=1, now_ns=1, clock_ticks=0) is None


def test_decimal_seconds_to_ns_keeps_fraction_as_int() -> None:
    assert _decimal_seconds_to_ns("12.5") == 12_500_000_000
    assert _decimal_seconds_to_ns("12") == 12_000_000_000


def test_format_elapsed_seconds_uses_centiseconds() -> None:
    assert _format_elapsed_seconds(6_426_000_000) == "6.42"


def test_startup_elapsed_is_non_negative() -> None:
    assert _startup_elapsed_ns(time.perf_counter_ns()) >= 0


def test_log_startup_reports_elapsed(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="bootstrap.lifecycle"):
        _log_startup(time.perf_counter_ns())
    matched = [
        record.message for record in caplog.records if record.message.startswith("启动耗时:")
    ]
    assert len(matched) == 1
    assert re.fullmatch(r"启动耗时: \d+\.\d{2} 秒", matched[0])
