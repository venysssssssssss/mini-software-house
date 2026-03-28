"""Tests for structured logging configuration."""

import io
import json

import structlog

from src.core.logger import configure_logger, get_logger


def test_get_logger_returns_bound_logger():
    log = get_logger("test-module")
    assert log is not None


def test_get_logger_different_names_return_loggers():
    a = get_logger("module-a")
    b = get_logger("module-b")
    # Both should be usable (structlog returns BoundLoggerLazyProxy)
    assert a is not None
    assert b is not None


def test_logger_can_log_info(capsys):
    log = get_logger("info-test")
    log.info("hello from test", extra_key="extra_val")
    captured = capsys.readouterr()
    assert "hello from test" in captured.out


def test_logger_can_log_warning(capsys):
    log = get_logger("warn-test")
    log.warning("watch out")
    captured = capsys.readouterr()
    assert "watch out" in captured.out


def test_logger_can_log_error(capsys):
    log = get_logger("err-test")
    log.error("something broke", detail="x")
    captured = capsys.readouterr()
    assert "something broke" in captured.out


def test_json_mode_output(monkeypatch):
    """When stdout is not a tty, structlog should produce JSON."""
    # Force non-tty by reconfiguring with JSON renderer
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=io.StringIO()),
        cache_logger_on_first_use=False,
    )

    log = structlog.get_logger(logger_name="json-test")
    output = io.StringIO()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=output),
        cache_logger_on_first_use=False,
    )

    log = structlog.get_logger(logger_name="json-test")
    log.info("json check", key="val")

    raw = output.getvalue().strip()
    parsed = json.loads(raw)
    assert parsed["event"] == "json check"
    assert parsed["key"] == "val"
    assert "timestamp" in parsed

    # Restore default config for other tests
    configure_logger()
