**For use on internal Allen Institute network**

```
import logging
import np_logging
```

`np_logging.setup()` runs automatically on import to add handlers and loggers from a default config,
then the `logging` module can be used as normal.

- user configs can be specified according to the python logging [library dict schema](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema)

- the default config is fetched from the
ZooKeeper server `eng-mindscope:2181`
- configs can be added via ZooNavigator webview:
  [http://eng-mindscope:8081](http://eng-mindscope:8081)
- or more conveniently, via an extension for VSCode such as [gaoliang.visual-zookeeper](https://marketplace.visualstudio.com/items?itemName=gaoliang.visual-zookeeper)

ZooKeeper configs can be fetched via their path:
```
test_config: dict = np_logging.fetch_zk_config(
    '/projects/np_logging_test/defaults/logging'
)
```

Once a logging config dict has been modified as necessary...
```
test_config['handlers']['email_handler']['toaddrs'] = username@alleninstitute.org
```
re-run the logging setup with the new config dict:
```
np_logging.setup(
    config: dict = test_config,
    project_name = 'test',
)
```

- `project_name` should be supplied to use the web logger - if unspecified, the name of the
  current working directory is used
- the web log can be viewed at [http://eng-mindscope:8080](http://eng-mindscope:8080)

The default config provides the loggers `web` and `email`, in addition to the default
`root` which includes file handlers
for info and debug logging levels, plus console logging:
```
logging.getLogger('web').info('test message')
logging.getLogger('email').info('test message')
logging.debug('test message to files and console')
```


Other input arguments to `np_logging.setup()`:
- `log_at_exit` (default `True`)

    - If `True`, a message is logged when the program terminates, reporting total
      elapsed time.

- `email_at_exit` (default `False`)

    - If `True`, an email is sent when the program terminates, reporting the
      elapsed time and cause of termination. If an exception was raised, the
      traceback is included.
      
    - If `logging.error`, the email is only sent if the program terminates via an exception.

