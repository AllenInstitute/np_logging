from __future__ import annotations

import logging
import logging.config
import logging.handlers
import pathlib
from typing import Optional, Sequence

import np_logging.handlers as handlers
import np_logging.utils as utils
import np_logging.config as config

DEFAULT_LOGGING_CONFIG, PKG_CONFIG = config.DEFAULT_LOGGING_CONFIG, config.PKG_CONFIG

logger = logging.getLogger(__name__)
logger.setLevel(logging.NOTSET)

def getLogger(name: Optional[str] = None) -> logging.Logger:
    """`logging.getLogger`, with console & debug/warning file handlers if root logger"""
    logger = logging.getLogger(name)
    if (
        name is None or name == "root"
    ) and not logger.handlers:  # logger.handlers empty if logger didn't already exist
        logger.addHandler(handlers.FileHandler(level=logging.WARNING))
        logger.addHandler(handlers.FileHandler(level=logging.DEBUG))
        logger.addHandler(handlers.ConsoleHandler(level=logging.DEBUG))
        utils.setup_logging_at_exit()
        logger.setLevel(PKG_CONFIG["default_logger_level"])
    elif not logger.handlers:
        # we created a new logger
        # make sure all logs are propagated to root:
        logger.setLevel(logging.NOTSET)
    return logger


get_logger = getLogger


def web(project_name: str = pathlib.Path.cwd().name) -> logging.Logger:
    """
    Set up a socket handler to send logs to the eng-mindscope log server.
    """
    name = PKG_CONFIG.get("default_server_logger_name", "web")
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = handlers.ServerHandler(project_name)
    logger.addHandler(handler)
    logger.setLevel(PKG_CONFIG["default_logger_level"])
    return logger


def email(
    address: str | Sequence[str],
    subject: str = __name__,
    exception_only: bool = False,
    propagate_to_root: bool = True,
) -> logging.Logger:
    """
    Set up an email logger to send an email at program exit.
    """
    name = PKG_CONFIG.get("default_exit_email_logger_name", "email")
    logger = logging.getLogger(name)
    if logger.handlers: # we already created it
        return logger
    utils.configure_email_logger(address, name, subject)
    level = logging.ERROR if exception_only else logging.INFO
    utils.setup_logging_at_exit(
        email_level=level, email_logger=name, root_log_at_exit=propagate_to_root
    )
    return logger


def setup(
    config: str | dict | pathlib.Path = DEFAULT_LOGGING_CONFIG,
    project_name: str = pathlib.Path.cwd().name,  # for log server
    email_address: Optional[str | Sequence[str]] = None,
    email_at_exit: bool | int = False,  # auto-True if address arg provided
    log_at_exit: bool = True,
):
    """
    With no args, uses default config to set up loggers named `web` and `email`, plus console logging
    and info/debug file handlers on root logger.

    - `config`
        - a custom config dict for the logging module
        - input dict, or path to dict in json/yaml file, or path to dict on
          zookeeper [http://eng-mindscope:8081](http://eng-mindscope:8081)

    - `project_name`
        - sets the `channel` value for the web logger
        - the web log can be viewed at [http://eng-mindscope:8080](http://eng-mindscope:8080)

    - `email_address`
        - if one or more addresses are supplied, an email is sent at program exit reporting the
        elapsed time and cause of termination. If an exception was raised, the
        traceback is included.

    - `log_at_exit`
        - If `True`, a message is logged when the program terminates, reporting total
        elapsed time.

    - `email_at_exit` (`True` if `email_address` is not `None`)
        - If `True`, an email is sent when the program terminates.
        - If `logging.ERROR`, the email is only sent if the program terminates via an exception.
    """
    config = utils.get_config_dict_from_multi_input(config)
    removed_handlers = utils.ensure_accessible_handlers(config)

    handlers.setup_record_factory(project_name)

    logging.config.dictConfig(config)

    if removed_handlers:
        logger.debug(
            "Removed handler(s) with inaccessible filepath or server: %s",
            removed_handlers,
        )

    exit_email_logger = config.get("exit_email_logger", None) or PKG_CONFIG.get(
        "default_exit_email_logger_name", "email"
    )
    if email_at_exit is True:
        email_at_exit = logging.INFO
    if email_address:  # overrides config
        utils.configure_email_logger(
            logger_name=exit_email_logger, email_address=email_address
        )
        logger.debug(
            "Updated email address for logger %r to %s",
            exit_email_logger,
            email_address,
        )
        if email_at_exit is False or email_at_exit is None:
            # no reason for user to provide an email address unless exit logging is desired
            email_at_exit = logging.INFO
    utils.setup_logging_at_exit(
        email_level=email_at_exit,
        email_logger=exit_email_logger,
        root_log_at_exit=log_at_exit,
    )
    logger.setLevel(PKG_CONFIG["default_logger_level"])
    logger.debug("np_logging setup complete")
