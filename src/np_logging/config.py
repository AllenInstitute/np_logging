import logging
from typing import Any, Dict
 
import importlib_resources
import np_config

logger = logging.getLogger(__name__)

ZK_DEFAULT_LOGGING_CONFIG_PATH = "/projects/np_logging/defaults/logging"
LOCAL_DEFAULT_LOGGING_CONFIG_PATH = importlib_resources.files(__name__) / "default_logging_config.yaml"

ZK_PROJECT_CONFIG_PATH = "/projects/np_logging/defaults/configuration"
LOCAL_PROJECT_CONFIG_PATH = importlib_resources.files(__name__) / "package_config.yaml"

try:
    config = np_config.from_zk(ZK_PROJECT_CONFIG_PATH)
except ConnectionError as exc:
    logger.debug(
        "Could not connect to ZooKeeper. Using local copy of package config: %s",
        LOCAL_PROJECT_CONFIG_PATH,
    )
    config = np_config.from_file(LOCAL_PROJECT_CONFIG_PATH)
finally:
    PKG_CONFIG: Dict[str, Any] = config

try:
    config = np_config.from_zk(ZK_DEFAULT_LOGGING_CONFIG_PATH)
except ConnectionError as exc:
    logger.debug(
        "Could not connect to ZooKeeper. Using local copy of default logging config: %s",
        LOCAL_DEFAULT_LOGGING_CONFIG_PATH,
    )
    config = np_config.from_file(LOCAL_DEFAULT_LOGGING_CONFIG_PATH)
finally:
    DEFAULT_LOGGING_CONFIG: Dict[str, Any] = config
