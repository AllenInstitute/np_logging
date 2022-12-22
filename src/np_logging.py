import atexit
import datetime
import logging
import logging.config
import logging.handlers
import os
import pathlib
import platform
import subprocess
import sys
import threading
from typing import Dict, List, Mapping, Optional, Sequence, Union

import np_config

import handlers
import utils

ROOT_DIR = pathlib.Path(__file__).absolute().parent.parent
DEFAULT_ZK_LOGGING_CONFIG_PATH = "/np_defaults/logging"
DEFAULT_LOGGING_CONFIG_PATH = ROOT_DIR / "configs" / "logging.yaml"

try:
    DEFAULT_CONFIG = np_config.fetch_zk_config(DEFAULT_ZK_LOGGING_CONFIG_PATH)
except ConnectionError as exc:
    print(
        f"Could not connect to ZooKeeper.\n\t> Using default config file in package: {DEFAULT_LOGGING_CONFIG_PATH}",
        file=sys.stderr,
    )
    DEFAULT_CONFIG = np_config.fetch_file_config(DEFAULT_LOGGING_CONFIG_PATH)


def web(project_name: str = pathlib.Path.cwd().name) -> logging.Logger:
    """
    Set up a socket handler to send logs to the eng-mindscope log server.
    """
    web = logging.getLogger("web")
    handler = handlers.ServerHandler(project_name, loglevel=logging.INFO)
    web.addHandler(handler)
    web.setLevel(logging.INFO)
    return web


def email(
    address: Union[str, Sequence[str]],
    subject: str = "np_logging",
    exception_only: bool = False,
    logger: str = "email",
    propagate_to_root: bool = True,
) -> logging.Logger:
    """
    Set up an email logger to send an email at program exit.
    """
    utils.configure_email_logger(address, logger, subject)
    level = logging.ERROR if exception_only else logging.INFO
    utils.setup_logging_at_exit(
        email_level=level, email_logger=logger, root_log_at_exit=propagate_to_root
    )
    return logging.getLogger(logger)


def setup(
    config: Union[str, Dict, pathlib.Path] = DEFAULT_CONFIG,
    project_name: str = pathlib.Path.cwd().name,  # for log server
    email_address: Optional[Union[str, Sequence[str]]] = None,
    email_at_exit: Union[bool, int] = False,  # auto-True if address arg provided
    log_at_exit: bool = True,
):
    """
    Log handler setup from aibspi/mpeconfig.

    `email_at_exit` can also be used to set the logging level used at exit:
    when the program terminates, a message will be logged at the `logging.INFO`
    level. An email will only be sent if `logging.INFO >= email_at_exit`.
    """
    config = utils.get_config_dict_from_multi_input(config)
    removed_handlers = utils.ensure_accessible_handlers(config)

    handlers.setup_record_factory(project_name)

    logging.config.dictConfig(config)

    if removed_handlers:
        logging.debug(
            "Removed handler(s) with inaccessible filepath or server: %s",
            removed_handlers,
        )

    exit_email_logger = (
        config.get("exit_email_logger", None) or utils.DEFAULT_EXIT_EMAIL_LOGGER
    )
    if email_at_exit is True:
        email_at_exit = logging.INFO
    if email_address:  # overrides config
        utils.configure_email_logger(
            logger_name=exit_email_logger, email_address=email_address
        )
        logging.debug(
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

    logging.debug("np_logging setup complete")
