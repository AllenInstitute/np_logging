import logging
import logging.handlers
import os
import sys
import pathlib
from typing import Dict, Optional, Union

import np_config
import pytest
import np_logging
from np_logging import utils, handlers
from np_logging.config import CONFIG

def get_handler(
    logger: Union[str, logging.Logger], handler_cls: logging.Handler
) -> Optional[logging.Handler]:
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    try:
        return next(h for h in logger.handlers if isinstance(h, handler_cls))
    except StopIteration:
        return None


def has_handler(
    logger: Union[str, logging.Logger], handler_cls: logging.Handler
) -> bool:
    return bool(get_handler(logger, handler_cls))


def test_default_config():
    assert np_logging.DEFAULT_LOGGING_CONFIG


def test_setup_with_default_config():
    "Minimum expected from default setup: extra loggers and modified record factory."
    np_logging.setup()
    assert has_handler(CONFIG["default_server_logger_name"], logging.handlers.SocketHandler)
    assert has_handler(CONFIG["default_exit_email_logger_name"], logging.handlers.SMTPHandler)
    assert has_handler("root", logging.StreamHandler)
    assert has_handler("root", logging.FileHandler)
    log_record = logging.getLogRecordFactory()(
        name=None, level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
    )
    assert all(
        hasattr(log_record, attr)
        for attr in ("project", "rig_name", "comp_id", "version")
    )


@pytest.fixture
def custom_handler_config() -> Dict:
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


def test_email_server():
    assert utils.host_responsive(handlers.EmailHandler("test@email.com").mailhost)


def test_log_server():
    assert utils.host_responsive(handlers.ServerHandler().host)


def test_web_standalone():
    "Undocumented func - might be modified in future"
    expected_handler = logging.handlers.SocketHandler
    web = np_logging.web()
    assert logging.getLogger(CONFIG["default_server_logger_name"]) is web
    assert has_handler(web, expected_handler)
    assert get_handler(web, expected_handler).host == CONFIG["handlers"]["log_server"]["host"]


def test_email_standalone():
    "Undocumented func - might be modified in future"
    expected_handler = logging.handlers.SMTPHandler
    address = "test@email.com"
    email = np_logging.email(address)
    assert logging.getLogger(CONFIG["default_exit_email_logger_name"]) is email
    assert has_handler(email, expected_handler)
    assert get_handler(email, expected_handler).toaddrs == [address]
