from __future__ import annotations

import logging
import logging.handlers
import os
import pathlib
import sys
from typing import Optional

import np_config
import pytest

import np_logging
from np_logging import handlers, utils
from np_logging.config import DEFAULT_LOGGING_CONFIG, PKG_CONFIG


def get_handler(
    logger: str | logging.Logger, handler_cls: logging.Handler
) -> logging.Handler | None:
    if isinstance(logger, str):
        if logger == "root":
            logger = logging.getLogger() # before 3.9, getLogger('root') doesn't return the actual rootlogger
        else:
            logger = logging.getLogger(logger)
    try:
        return next(h for h in logger.handlers if isinstance(h, handler_cls))
    except StopIteration:
        return None


def has_handler(
    logger: str | logging.Logger, handler_cls: logging.Handler
) -> bool:
    return bool(get_handler(logger, handler_cls))


def test_default_config():
    assert DEFAULT_LOGGING_CONFIG


def test_setup_with_default_config():
    "Minimum expected from default setup: extra loggers and modified record factory."
    np_logging.setup()
    assert has_handler(
        PKG_CONFIG["default_server_logger_name"], logging.handlers.SocketHandler
    )
    assert has_handler(
        PKG_CONFIG["default_exit_email_logger_name"], logging.handlers.SMTPHandler
    )
    assert has_handler(logging.getLogger(), logging.StreamHandler)
    assert has_handler(logging.getLogger(), logging.FileHandler)
    log_record = logging.getLogRecordFactory()(
        name=None, level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
    )
    assert all(
        hasattr(log_record, attr)
        for attr in ("project", "rig_name", "comp_id", "version")
    )

@pytest.fixture
def custom_handler_config() -> dict:
    return np_config.from_file(
        (pathlib.Path(__file__).parent / "custom_handler_config.yaml").resolve()
    )


def test_custom_handlers(custom_handler_config):
    "Checks custom handlers are created and configured correctly."
    np_logging.setup(config=custom_handler_config)
    handler_names = {
        handler: config.get("()", None)
        for handler, config in custom_handler_config["handlers"].items()
    }
    handler_classes = {
        handler: eval(cls) for handler, cls in handler_names.items() if cls
    }
    for logger in custom_handler_config["loggers"]:
        for handler in custom_handler_config["loggers"][logger]["handlers"]:
            assert has_handler(logger, handler_classes[handler])

            if custom_handler_config["loggers"][logger].get("level", None):
                assert logging.getLogger(logger).level == logging.getLevelName(
                    custom_handler_config["loggers"][logger]["level"]
                )
            if custom_handler_config["handlers"][handler].get("level", None):
                assert logging._handlers[handler].level == logging.getLevelName(
                    custom_handler_config["handlers"][handler]["level"]
                )


def test_set_level():
    root = np_logging.getLogger()
    root_level_0 = root.level
    console = next((_ for _ in root.handlers if _.name == 'console'), None)
    assert console is not None
    for level in (10, 20, 30, 40, 50):
        np_logging.setLevel(level)
        assert console.level == level
        assert root.level == root_level_0


def test_email_server():
    assert utils.host_responsive(handlers.EmailHandler("test@email.com").mailhost)


def test_log_server():
    assert utils.host_responsive(handlers.ServerHandler().host)


def test_web_standalone():
    "Undocumented func - might be modified in future"
    expected_handler = logging.handlers.SocketHandler
    web = np_logging.web('test')
    assert logging.getLogger(PKG_CONFIG["default_server_logger_name"]) is web
    assert has_handler(web, expected_handler)
    assert (
        get_handler(web, expected_handler).host
        == PKG_CONFIG["handlers"]["log_server"]["host"]
    )


def test_email_standalone():
    "Undocumented func - might be modified in future"
    expected_handler = logging.handlers.SMTPHandler
    address = "test@email.com"
    email = np_logging.email(address)
    assert logging.getLogger(PKG_CONFIG["default_exit_email_logger_name"]) is email
    assert has_handler(email, expected_handler)
    assert get_handler(email, expected_handler).toaddrs == [address]


def test_root_logger():
    assert np_logging.getLogger() is logging.getLogger()
    
test_root_logger()

test_web_standalone()