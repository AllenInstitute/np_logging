import logging
from importlib.resources import files
from typing import Any, Dict

import np_config

logger = logging.getLogger(__name__)

ZK_DEFAULT_CONFIG_PATH = "/np_defaults/logging"
LOCAL_DEFAULT_CONFIG_PATH = files(__name__) / "config.yaml"

try:
    config = np_config.from_zk(ZK_DEFAULT_CONFIG_PATH)
except ConnectionError as exc:
    logger.debug(
        "Could not connect to ZooKeeper. Using default config file: %s",
        LOCAL_DEFAULT_CONFIG_PATH,
    )
    config = np_config.from_file(LOCAL_DEFAULT_CONFIG_PATH)
finally:
    CONFIG: Dict[str, Any] = config
