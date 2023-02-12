# **np_logging**

**For use on internal Allen Institute network**

***


## Quick start

Follow the conventions for using the `logging` module in the standard library:

 - in a script or main module, `np_logging` adds console & file handlers and exit messages to the root logger:

```python
import np_logging

logger = np_logging.getLogger()
```


 - or, in a package or project with multiple modules, all logged messages are propagated to the root logger:
```python
import np_logging

logger = np_logging.getLogger(__name__)     # logger.level = logging.NOTSET = 0
```


 - then log messages as usual:

```python 
logger.info('test message')
logger.warning('test message')
```


No further setup is required, and importing `logging`
from the standard library isn't necessary.


***


To send a message to the Mindscope log-server, use `np_logging.web()` and supply a project name, which will
appear in the 
`channel` field on the server:

```python
project_name = 'spike_sorting'

np_logging.web(project_name).info('test message')
```
- the web log can be viewed at [http://eng-mindscope:8080](http://eng-mindscope:8080)

***


For customization, use `np_logging.setup()` to supply a logging config dict than specifies
loggers and their handlers/formatters, and extra functions such as exit messages & exit
emails will be added.

- logging configs should be specified according to the python logging [library dict schema](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema)


- logging configs on the `eng-mindscope` ZooKeeper server can also be used directly to setup
  logging by supplying their path to `np_logging.setup()`:

```python
np_logging.setup(
    '/projects/np_workflows/defaults/logging'
)
```

See [np_config](https://github.com/AllenInstitute/np_config) for further info on using ZooKeeper
for configs.



Other input arguments to `np_logging.setup()`:

- `project_name` (default: current working directory name) 
  
    - sets the `channel` displayed on the log server

- `email_address` (default: `None`)
      
    - if one or more addresses are supplied, an email is sent at program exit reporting the
      elapsed time and cause of termination. If an exception was raised, the
      traceback is included.

- `log_at_exit` (default: `True`)

    - If `True`, a message is logged when the program terminates, reporting total
      elapsed time.

- `email_at_exit` (default: `False`, or `True` if `email_address` is not `None`)

    - If `True`, an email is sent when the program terminates.
      
    - If `logging.ERROR`, the email is only sent if the program terminates via an exception.

