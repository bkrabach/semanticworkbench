import json
import logging
import os

logger = logging.getLogger(__name__)


def load_server_configs(config_file: str) -> list:
    """
    Load server configurations from a JSON file.
    """
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            server_configs = json.load(f)
        logger.debug(f"Loaded server configurations from {config_file}")
        return server_configs
    else:
        logger.error(f"Configuration file {config_file} not found.")
        return []
