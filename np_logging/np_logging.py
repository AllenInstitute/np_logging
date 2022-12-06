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
from typing import Dict, List, Union

from .config import fetch_zk_config

START_TIME = datetime.datetime.now()
EMAIL_HANDLER_NAME = 'email'

try:
    DEFAULT_CONFIG = fetch_zk_config()
except ConnectionError as exc:
    print("Could not fetch default logging config from zookeeper.\n\t> provide a config dict to np_logging.setup() to use.", file=sys.stderr)
    DEFAULT_CONFIG = None
    
def setup_record_factory(project_name: str):
    "Make log records compatible with eng-mindscope log server."
    log_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = log_factory(*args, **kwargs)
        record.project = project_name
        record.comp_id = os.getenv("aibs_comp_id", None)
        record.hostname = platform.node()
        record.rig_name = record.hostname
        record.version = None
        # if type(record.msg) is str:
        #     record.msg = record.msg if record.msg and record.msg[-1] == ',' else record.msg + ','
        return record
    
    logging.setLogRecordFactory(record_factory)

def host_responsive(host: str) -> bool:
    """
    Remember that a host may not respond to a ping (ICMP) request even if the host name
    is valid. https://stackoverflow.com/a/32684938
    """
    param = '-n' if platform.system().lower()=='windows' else '-c'
    command = ['ping', param, '1', host]
    return subprocess.call(command, stdout=subprocess.PIPE) == 0

def ensure_accessible_file_handlers(config: Dict) -> Union[None, List[str]]:
    """
    Check filepaths and write access for file handlers; server availability for socket/smtp handlers.
    Remove inaccessible handlers from config and return their names.
    """
    removed_handlers = []
    for name, handler in config['handlers'].items():
        if 'filename' in handler:
            file = pathlib.Path(handler['filename']).resolve()
            if not file.suffix:
                handler['filename'] = str(file.with_suffix('.log'))
            try:
                file.parent.mkdir(parents=True, exist_ok=True)
                if not os.access(file.parent, os.W_OK): # check write access
                    raise PermissionError
            except PermissionError:
                removed_handlers.append(name)
        
        if any(
            host in handler and not host_responsive(handler[host])
            for host in ('host', 'mailhost')
        ):
            removed_handlers.append(name)     
                      
    for handler in removed_handlers:
        del config['handlers'][handler] 
        for logger in config['loggers'].values():
            if handler in logger['handlers']:
                logger['handlers'].remove(handler)
                
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
        self._orig_threading_excepthook = threading.excepthook
        threading.excepthook = self.threading_excepthook
        
    def exit(self, code=0):
        self.exit_code = code
        self._orig_exit(code)
        
    def threading_excepthook(self, args:tuple):
        exc_type, exc, tb, *_ = args # from threading.excepthook
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
    logging.exception(msg='Exception:', exc_info=exc)

def log_exit(hooks: ExitHooks, email_level: Union[int, None], log_at_exit: bool = True):
    
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
        atexit.unregister(log_exit)
    except UnboundLocalError:
        pass
    atexit.register(log_exit, hooks, *args, **kwargs)
    
def setup(
    config: Dict = DEFAULT_CONFIG,
    project_name: str = pathlib.Path.cwd().name, # for log server
    email_at_exit: Union[bool, int] = False,
    log_at_exit: bool = True,
    ):
    """
    Log handler setup from aibspi/mpeconfig. 
    
    `email_at_exit` can also be used to set the logging level used at exit: 
    when the program terminates, a message will be logged at the `logging.INFO`
    level. An email will only be sent if `logging.INFO >= email_at_exit`.
    """
    
    removed_handlers = ensure_accessible_file_handlers(config)
    
    setup_record_factory(project_name)
    
    logging.config.dictConfig(config)
    
    if removed_handlers:
        logging.info('Removed handler(s) with inaccessible filepath or server: %s' % removed_handlers)
    
    if email_at_exit is True:
        email_at_exit = logging.INFO
    setup_logging_at_exit(email_at_exit, log_at_exit)