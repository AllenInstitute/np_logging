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
from typing import Any, Dict, List, Mapping, Sequence, Union

import np_config

from . import handlers
from .config import PKG_CONFIG, DEFAULT_LOGGING_CONFIG

START_TIME = datetime.datetime.now()

def host_responsive(host: str) -> bool:
    """
    Remember that a host may not respond to a ping (ICMP) request even if the host name
    is valid. https://stackoverflow.com/a/32684938
    """
    param = "-n" if platform.system().lower() == "windows" else "-c"
    command = ["ping", param, "1", host]
    return subprocess.call(command, stdout=subprocess.PIPE) == 0


def ensure_accessible_handlers(config: Dict) -> Union[None, List[str]]:
    """
    Check filepaths and write access for file handlers; server availability for socket/smtp handlers.
    Remove inaccessible handlers from config and return their names.
    """
    removed_handlers = []
    for name, handler in config["handlers"].items():
        if "filename" in handler:
            file = pathlib.Path(handler["filename"]).resolve()
            if not file.suffix:
                handler["filename"] = str(file.with_suffix(".log"))
            try:
                file.parent.mkdir(parents=True, exist_ok=True)
                if not os.access(file.parent, os.W_OK):  # check write access
                    raise PermissionError
            except PermissionError:
                removed_handlers.append(name)

        if any(
            host in handler and not host_responsive(handler[host])
            for host in ("host", "mailhost")
        ):
            removed_handlers.append(name)

    for handler in removed_handlers:
        del config["handlers"][handler]
        for logger in config["loggers"].values():
            if handler in logger["handlers"]:
                logger["handlers"].remove(handler)

    return removed_handlers or None


def elapsed_time() -> str:
    return "%s [h:m:s.μs]" % (datetime.datetime.now() - START_TIME)


class ExitHooks(object):
    """Capture the exit code or exception + traceback when program terminates.

    https://stackoverflow.com/a/9741784
    """

    def __init__(self, run_orig_hooks=False):
        self.exit_code = self.exception = self.traceback = None
        self.run_orig_hooks = run_orig_hooks
        self.hook()

    def hook(self):
        self._orig_exit = sys.exit
        sys.exit = self.exit
        self._orig_sys_excepthook = sys.excepthook
        sys.excepthook = self.sys_excepthook
        try:
            self._orig_threading_excepthook = threading.excepthook
            threading.excepthook = self.threading_excepthook
        except AttributeError:  # threading.excepthook is not available in Python <3.8
            pass

    def exit(self, code=0):
        self.exit_code = code
        self._orig_exit(code)

    def threading_excepthook(self, args: tuple):
        exc_type, exc, tb, *_ = args  # from threading.excepthook
        if self.run_orig_hooks:
            self._orig_threading_excepthook(args)
        log_exception(exc_type, exc, tb)

    def sys_excepthook(self, exc_type, exc, tb):
        self.exception = exc
        self.traceback = tb
        if self.run_orig_hooks:
            self._orig_sys_excepthook(exc_type, exc, tb)
        log_exception(exc_type, exc, tb)


def log_exception(exc_type, exc, tb):
    logging.exception(msg="Exception:", exc_info=exc)


def log_exit(
    hooks: ExitHooks,
    email_level: Union[bool, int],
    email_logger: str = PKG_CONFIG["default_exit_email_logger_name"],
    root_log_at_exit: bool = True,
):

    elapsed = elapsed_time()

    msg_level = logging.INFO
    msg = "Exited normally"
    if hooks.exit_code is not None:
        msg = f"Exited via sys.exit({hooks.exit_code})"
    elif hooks.exception is not None:
        msg = f"Exited via {hooks.exception.__class__.__name__}"
        msg_level = logging.ERROR

    if email_level is not False:
        email = logging.getLogger(email_logger)
        if msg_level >= email_level:
            email.setLevel(
                msg_level
            )  # make sure msg gets through. program is exiting anyway so it doesn't matter that we change the level
            email.log(msg_level, "%s after %s", msg, elapsed, exc_info=hooks.exception)

    if root_log_at_exit and (not email.propagate if email_level else True):
        logging.log(msg_level, "%s after %s", msg, elapsed)


def setup_logging_at_exit(*args, **kwargs):
    hooks = ExitHooks()
    try:
        atexit.unregister(log_exit)
    except UnboundLocalError:
        pass
    atexit.register(log_exit, hooks, *args, **kwargs)


def configure_email_logger(
    email_address: Union[str, Sequence[str]],
    logger_name: str = PKG_CONFIG["default_exit_email_logger_name"],
    email_subject: str = __name__,
):
    email_logger = logging.getLogger(logger_name)
    for handler in email_logger.handlers:
        if isinstance(handler, logging.handlers.SMTPHandler):
            handler.toaddrs = (
                [email_address]
                if isinstance(email_address, str)
                else list(email_address)
            )
            break
    else:
        email_logger.addHandler(
            handlers.EmailHandler(
                list(email_address), level=logging.INFO, subject=email_subject
            )
        )


def get_config_dict_from_multi_input(
    arg: Union[str, Mapping, pathlib.Path]
) -> Dict[str, Any]:
    "Differentiate a file path from a ZK path and return corresponding logging config dict, if valid."

    config = np_config.fetch(arg)
    if not valid_logging_config_dict(config):
        raise ValueError(f"Input {arg!r} is not a valid python logging config dict.")

    return dict(**config)


def valid_logging_config_dict(config: Mapping) -> bool:
    "`version` is a mandatory key at the top level of a python logging config dict so we check its presence."
    try:
        return config.get("version", None) != None
    except AttributeError:
        return False
