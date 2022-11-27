import atexit
import datetime
import logging
import logging.config
import logging.handlers
import os
import pathlib
import platform
import sys
import threading
import traceback
from typing import Union

from .config import DEFAULT_ZK_LOGGING_CONFIG_PATH, fetch_zk_config

START_TIME = datetime.datetime.now()
EMAIL_HANDLER_NAME = 'email'

def setup_record_factory(project_name):
    "Make log records compatible with eng-mindscope log server."
    log_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = log_factory(*args, **kwargs)
        record.project = project_name
        record.comp_id = os.getenv("aibs_comp_id", platform.node())
        record.rig_name = os.getenv("aibs_rig_id", None)
        record.version = None
        # if type(record.msg) is str:
        #     record.msg = record.msg if record.msg and record.msg[-1] == ',' else record.msg + ','
        return record
    
    logging.setLogRecordFactory(record_factory)
    
def ensure_file_handler_paths_exist(config):
    for handler in config['handlers'].values():
        if 'filename' in handler:
            file = pathlib.Path(handler['filename']).resolve()
            file.parent.mkdir(parents=True, exist_ok=True)
            if not file.suffix:
                handler['filename'] = str(file.with_suffix('.log'))
                
def elapsed_time() -> str:
    return "%s [h:m:s.μs]" % (datetime.datetime.now() - START_TIME)
   
class ExitHooks(object):
    """Capture the exit code or exception + traceback when program terminates.
        
        https://stackoverflow.com/a/9741784
    """
    def __init__(self):
        self.exit_code = self.exception = self.traceback = None
        self.hook()

    def hook(self):
        self._orig_exit = sys.exit
        sys.exit = self.exit
        self._orig_sys_excepthook = sys.excepthook
        sys.excepthook = self.sys_excepthook
        self._orig_threading_excepthook = threading.excepthook
        threading.excepthook = self.threading_excepthook
        
    def exit(self, code=0):
        self.exit_code = code
        self._orig_exit(code)
        
    def threading_excepthook(self, args:tuple):
        exc_type, exc, tb, *_ = args # from threading.excepthook
        # self._orig_threading_excepthook(args)
        exception_log(exc_type, exc, tb)
            
    def sys_excepthook(self, exc_type, exc, tb):
        self.exception = exc
        self.traceback = tb# ''.join(['\n']+traceback.format_exception(type(exc), value=exc, tb=exc.__traceback__))[:-1]
        # self._orig_sys_excepthook(exc_type, exc, tb)
        exception_log(exc_type, exc, tb)

def exception_log(exc_type, exc, tb):
    logging.exception(msg='Exception:', exc_info=exc)

def exit_log(hooks: ExitHooks, email_level: Union[int, None], log_at_exit: bool = True):
    
    elapsed = elapsed_time()
    
    msg_level = logging.INFO
    msg = "Exited normally"
    if hooks.exit_code is not None:
        msg = f"Exited via sys.exit({hooks.exit_code})"
    elif hooks.exception is not None:
        msg = f"Exited via {hooks.exception.__class__.__name__}"
        msg_level = logging.ERROR
        
    if email_level:
        email = logging.getLogger(EMAIL_HANDLER_NAME)
        if msg_level >= email_level:
            email.setLevel(msg_level) # make sure msg gets through. program is exiting anyway so it doesn't matter that we change the level
            email.log(msg_level, msg='%s after %s' % (msg, elapsed), exc_info=hooks.exception)
        
    if log_at_exit and (not email.propagate if email_level else True):
        logging.log(msg_level, msg='%s after %s' % (msg, elapsed))

def setup_logging_at_exit(*args, **kwargs):
    hooks = ExitHooks()
    try:
        atexit.unregister(exit_log)
    except UnboundLocalError:
        pass
    atexit.register(exit_log, hooks, *args, **kwargs)
    
def setup(
    config: dict = fetch_zk_config(DEFAULT_ZK_LOGGING_CONFIG_PATH),
    project_name: str = pathlib.Path.cwd().name, #reqd for log server
    email_at_exit: Union[bool, int] = False,
    log_at_exit: bool = True,
    ):
    "Log handler setup from aibspi/mpeconfig."
    
    ensure_file_handler_paths_exist(config)
    
    setup_record_factory(project_name)
    
    logging.config.dictConfig(config)
    
    if email_at_exit is True:
        email_at_exit = logging.INFO
    setup_logging_at_exit(email_at_exit, log_at_exit)