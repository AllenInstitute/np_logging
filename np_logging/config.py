import yaml
from kazoo.client import KazooClient

# preserve order of keys in dict ?
yaml.add_representer(dict, lambda self, data: yaml.representer.SafeRepresenter.represent_dict(self, data.items()))

DEFAULT_ZK_LOGGING_CONFIG_PATH = '/np_defaults/logging'

def fetch_zk_config(path: str = DEFAULT_ZK_LOGGING_CONFIG_PATH) -> dict:
    "Access eng-mindscope Zookeeper, return config dict."
    with ConfigServer() as zk:
        return zk[path]
    
class ConfigServer(KazooClient):
    """
    A dictionary and context API wrapper around the zookeeper interface - from mpeconfig.
    """

    def __init__(self, hosts="eng-mindscope:2181"):
        self.hosts = hosts
        super().__init__(hosts=hosts, timeout=10)

    def __getitem__(self, key):
        if self.exists(key):
            return yaml.load(self.get(key)[0], Loader=yaml.loader.Loader)
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        self.ensure_path(key)
        self.set(key, value)

    def __delitem__(self, key):
        if self.exists(key):
            self.delete(key)

    def __enter__(self):
        try:
            self.start(timeout=1)
        except Exception as exc:
            if not self.connected:
                raise ConnectionError(f"Could not connect to {self.hosts}") from exc
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.stop()