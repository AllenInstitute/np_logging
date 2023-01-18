from __future__ import annotations

import logging
from typing import Any

try:
    import importlib.resources as importlib_resources
except ImportError:
    import importlib_resources
import np_config

logger = logging.getLogger(__name__)

ZK_DEFAULT_LOGGING_CONFIG = "/projects/np_logging/defaults/logging"
LOCAL_DEFAULT_LOGGING_CONFIG = (
    importlib_resources.files("np_logging") / "default_logging_config.yaml"
)

ZK_PROJECT_CONFIG = "/projects/np_logging/defaults/configuration"
LOCAL_PROJECT_CONFIG = importlib_resources.files("np_logging") / "package_config.yaml"

try:
    config = np_config.from_zk(ZK_PROJECT_CONFIG)
except ConnectionError as exc:
    logger.debug(
        "Could not connect to ZooKeeper. Using local copy of package config: %s",
        LOCAL_PROJECT_CONFIG,
    )
    config = np_config.from_file(LOCAL_PROJECT_CONFIG)
finally:
    PKG_CONFIG: dict[str, Any] = config

try:
    config = np_config.from_zk(ZK_DEFAULT_LOGGING_CONFIG)
except ConnectionError as exc:
    logger.debug(
        "Could not connect to ZooKeeper. Using local copy of default logging config: %s",
        LOCAL_DEFAULT_LOGGING_CONFIG,
    )
    config = np_config.from_file(LOCAL_DEFAULT_LOGGING_CONFIG)
finally:
    DEFAULT_LOGGING_CONFIG: dict[str, Any] = config
