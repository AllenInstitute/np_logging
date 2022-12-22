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
from typing import Callable, Dict, List, Optional, Tuple, Union

from config import CONFIG

FORMAT: Dict[str, logging.Formatter] = {k:logging.Formatter(**v) for k,v in CONFIG['formatters'].items()}

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

    def __init__(
        self,
        filename: str = CONFIG["log_server_file_backup"]["backup_file"],
        mode: str = CONFIG["log_server_file_backup"]["mode"],
        maxBytes: int = CONFIG["log_server_file_backup"]["maxBytes"],
        backupCount: int = CONFIG["log_server_file_backup"]["backupCount"],
        encoding: str = CONFIG["log_server_file_backup"]["encoding"],
        delay: bool = CONFIG["log_server_file_backup"]["delay"],
        formatter: logging.Formatter = FORMAT['detailed'],
        **kwargs,
    ):
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        self.setLevel(logging.NOTSET)
        self.setFormatter(formatter)

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
        formatter: logging.Formatter = FORMAT['log_server'],
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
        formatter: logging.Formatter = FORMAT['email'],
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
        formatter: logging.Formatter = FORMAT['simple'],
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
        formatter: logging.Formatter = FORMAT['detailed'],
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
