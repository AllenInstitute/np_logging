"""
Pre-configured logging handlers for manual setup.

Can be specified in logging config dict:
    handlers:
    info_file_handler:
        (): np_logging.handlers.FileHandler
        level: INFO
"""
# from __future__ import annotations

import logging
import logging.handlers
import os
import pathlib
import platform
import sys
from typing import Callable, List, Optional, Tuple, Union


def setup_record_factory(project_name: str) -> Callable:
    "Make log records compatible with eng-mindscope log server."
    log_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs) -> logging.LogRecord:
        record = log_factory(*args, **kwargs)
        record.project = project_name
        record.comp_id = os.getenv("aibs_comp_id", None)
        record.rig_name = record.hostname = platform.node()
        record.version = None
        return record

    logging.setLogRecordFactory(record_factory)
    return record_factory


class ServerBackupHandler(logging.handlers.RotatingFileHandler):

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(hostname)s %(project)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    def __init__(
        self,
        filename: str = "//allen/programs/mindscope/workgroups/np-exp/log_server/eng-mindscope_backup.log",
        mode: str = "a",
        maxBytes: int = 10 * 1024**2,
        backupCount: int = 9999,
        encoding: str = "utf8",
        delay: bool = False,
        **kwargs,
    ):
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.setLevel(logging.NOTSET)
        self.setFormatter(self.formatter)

    def emit(self, record):
        try:
            super().emit(record)
        except OSError:
            return


class ServerHandler(logging.handlers.SocketHandler):

    backup: logging.Handler = ServerBackupHandler()

    def __init__(
        self,
        project_name: str = pathlib.Path.cwd().name,
        host: str = "eng-mindscope",
        port: int = 9000,
        formatter: logging.Formatter = logging.Formatter(
            "%(message)s,", "%Y-%m-%d %H:%M:%S"
        ),
        loglevel: int = logging.ERROR,
        **kwargs,
    ):
        super().__init__(host, port)
        self.setLevel(loglevel)
        self.setFormatter(formatter)
        setup_record_factory(project_name)

    def emit(self, record):
        super().emit(record)
        self.backup.emit(record)


class EmailHandler(logging.handlers.SMTPHandler):
    def __init__(
        self,
        toaddrs: Union[str, List[str]],
        project_name: str = pathlib.Path.cwd().name,
        mailhost: Union[str, Tuple[str, int]] = "aicas-1.corp.alleninstitute.org",
        fromaddr: str = "rigs@alleninstitute.org",
        subject: str = "np_logging",
        credentials: Optional[Tuple[str, str]] = None,
        secure=None,
        timeout: float = 5.0,
        formatter: logging.Formatter = logging.Formatter(
            "%(project)s %(levelname)s | %(message)s"
        ),
        loglevel: int = logging.INFO,
        **kwargs,
    ):
        super().__init__(
            mailhost, fromaddr, toaddrs, subject, credentials, secure, timeout
        )
        self.setLevel(loglevel)
        self.setFormatter(formatter)
        setup_record_factory(project_name)


class ConsoleHandler(logging.StreamHandler):
    def __init__(
        self,
        stream=sys.stdout,
        formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s | %(message)s", "%H:%M"
        ),
        loglevel: int = logging.DEBUG,
        **kwargs,
    ):
        super().__init__(stream)
        self.setLevel(loglevel)
        self.setFormatter(formatter)


class FileHandler(logging.handlers.RotatingFileHandler):
    def __init__(
        self,
        logs_dir: Union[str, pathlib.Path] = "logs",
        mode: str = "a",
        maxBytes: int = 10 * 1024**2,
        backupCount: int = 10,
        encoding: str = "utf8",
        delay: bool = True,
        loglevel: int = logging.INFO,
        formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s %(name)s %(levelname)s %(filename)s:%(lineno)d %(funcName)s %(threadName)s | %(message)s",
            "%Y-%m-%d %H:%M:%S",
        ),
        **kwargs,
    ):
        name = (
            logging.getLevelName(loglevel)
            if not isinstance(loglevel, str)
            else loglevel
        )
        filename = pathlib.Path(logs_dir).resolve() / f"{name.lower()}.log"
        filename.parent.mkdir(parents=True, exist_ok=True)

        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.setLevel(loglevel)
        self.setFormatter(formatter)
