**For use on internal Allen Institute network**

Quick start:
```
import logging
import np_logging

np_logging.setup()
```

`np_logging.setup()` with no arguments uses a default config, providing the loggers `web` and `email`, in addition to the default
`root` which includes file handlers for `logging.INFO` and `logging.DEBUG`  levels, plus
console logging. 

The built-in python `logging` module can then be used as normal.

Usage example:
```
logging.getLogger('web').info('test: web server')
logging.getLogger('email').info('test: email logger')
logging.debug('test: root logger')
```

- user configs should be specified according to the python logging [library dict schema](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema)

- the default config is fetched from the
ZooKeeper server `eng-mindscope:2181`
- configs can be added via ZooNavigator webview:
  [http://eng-mindscope:8081](http://eng-mindscope:8081)
- or more conveniently, via an extension for VSCode such as [gaoliang.visual-zookeeper](https://marketplace.visualstudio.com/items?itemName=gaoliang.visual-zookeeper)

ZooKeeper configs or config files can be used by supplying their path to `setup()`:
```
np_logging.setup(
    '/projects/np_logging_test/defaults/logging'
)
```


Other input arguments to `np_logging.setup()`:

- `project_name` (default current working directory name) 
  
    - sets the `channel` value for the web logger
    - the web log can be viewed at [http://eng-mindscope:8080](http://eng-mindscope:8080)

- `email_address` (default `None`)
      
    - if one or more addresses are supplied, an email is sent at program exit reporting the
      elapsed time and cause of termination. If an exception was raised, the
      traceback is included.

- `log_at_exit` (default `True`)

    - If `True`, a message is logged when the program terminates, reporting total
      elapsed time.

- `email_at_exit` (default `False` or `True` if `email_address` is not `None`)

    - If `True`, an email is sent when the program terminates.
      
    - If `logging.ERROR`, the email is only sent if the program terminates via an exception.

