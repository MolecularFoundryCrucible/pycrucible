#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crucible Configuration Management

Loads Crucible API keys and configuration from:
1. Environment variables (highest priority)
2. INI config file in user config directory

@author: roncofaber
"""

import os
import logging
import configparser
from pathlib import Path
from platformdirs import user_config_dir, user_cache_dir

# Set up logger for this module
logger = logging.getLogger(__name__)

class Config:
    """
    Configuration manager for pycrucible.

    Loads configuration from environment variables and config file,
    providing a clean interface for accessing settings.
    """

    # Mapping of config keys to their environment variable names and INI keys
    _CONFIG_MAP = {
        'api_key': {'env': 'CRUCIBLE_API_KEY', 'ini': 'api_key'},
        'api_url': {'env': 'CRUCIBLE_API_URL', 'ini': 'api_url'},
        'cache_dir': {'env': 'PYCRUCIBLE_CACHE_DIR', 'ini': 'cache_dir'},
        'orcid_id': {'env': 'ORCID_ID', 'ini': 'orcid_id'},
        'graph_explorer_url': {'env': 'CRUCIBLE_GRAPH_EXPLORER_URL', 'ini': 'graph_explorer_url'},
        'current_project': {'env': 'CRUCIBLE_CURRENT_PROJECT', 'ini': 'current_project'},
    }

    def __init__(self):
        """Initialize and load configuration."""
        self._data = {}
        self._client = None
        self._load()

    def _load(self):
        """Load configuration from all available sources."""
        # 1. Load from environment variables (highest priority)
        for key, mapping in self._CONFIG_MAP.items():
            env_value = os.environ.get(mapping['env'])
            if env_value is not None:
                self._data[key] = env_value

        # 2. Load from INI config file
        config_file = self.config_file_path
        if config_file.exists():
            parser = configparser.ConfigParser()
            parser.read(config_file)

            if "crucible" in parser:
                for key, mapping in self._CONFIG_MAP.items():
                    # Only load from file if not already set from environment
                    if key not in self._data and mapping['ini'] in parser["crucible"]:
                        value = parser["crucible"][mapping['ini']].strip('"').strip("'")
                        self._data[key] = value

        return

    @property
    def config_file_path(self):
        """Get the path to the configuration file."""
        return Path(user_config_dir("pycrucible")) / "config.ini"

    @property
    def api_key(self):
        """
        Get the Crucible API key.

        Returns:
            str: The API key

        Raises:
            ValueError: If no API key is found
        """
        key = self._data.get('api_key')
        if key is None:
            raise ValueError(
                f"Crucible API key not found. Please set it using one of these methods:\n"
                f"1. Environment variable: export CRUCIBLE_API_KEY='your_key_here'\n"
                f"2. Config file: Create {self.config_file_path} with:\n"
                f"   [crucible]\n"
                f"   api_key = your_key_here\n"
                f"\nUse create_config_file() to create the config file automatically:\n"
                f"from pycrucible.config import create_config_file\n"
                f"create_config_file('your_key_here')"
            )
        return key

    @property
    def api_url(self):
        """
        Get the Crucible API URL.

        Returns:
            str: The API URL (defaults to https://crucible.lbl.gov/testapi)
        """
        return self._data.get('api_url', 'https://crucible.lbl.gov/testapi')

    @property
    def cache_dir(self):
        """
        Get the cache directory path.

        Returns:
            Path: The cache directory path
        """
        cache_dir_str = self._data.get('cache_dir')

        if cache_dir_str is None:
            # Use default platform-specific cache directory
            cache_path = Path(user_cache_dir("pycrucible"))
        else:
            # Expand ~ and convert to Path
            cache_path = Path(os.path.expanduser(cache_dir_str))

        # Ensure the cache directory exists
        cache_path.mkdir(parents=True, exist_ok=True)

        return cache_path

    @property
    def orcid_id(self):
        """
        Get the user's ORCID ID.

        Returns:
            str or None: The ORCID ID if configured, None otherwise
        """
        return self._data.get('orcid_id')

    @property
    def graph_explorer_url(self):
        """
        Get the Crucible Graph Explorer URL.

        Returns:
            str: The graph explorer URL
        """
        default_url = 'https://crucible-graph-explorer-776258882599.us-central1.run.app'
        return self._data.get('graph_explorer_url', default_url)

    @property
    def current_project(self):
        """
        Get the current/default project ID.

        Returns:
            str or None: The current project ID if configured, None otherwise
        """
        return self._data.get('current_project')

    @property
    def client(self):
        """
        Get a configured CrucibleClient instance.

        Returns:
            CrucibleClient: Configured client instance
        """
        if self._client is None:
            # Import here to avoid circular imports
            from pycrucible import CrucibleClient
            self._client = CrucibleClient(self.api_url, self.api_key)
        return self._client

    @property
    def user_info(self):
        """
        Get the user info for the configured ORCID ID.

        Returns:
            dict or None: User information if ORCID is configured, None otherwise
        """
        if self.orcid_id is not None:
            return self.client.get_user(self.orcid_id)
        return None

    def reload(self):
        """Reload configuration from all sources."""
        self._data.clear()
        self._client = None
        self._load()


# Global singleton config instance
config = Config()


# Helper functions
def get_crucible_api_key():
    """
    Get the Crucible API key from configuration.

    Priority order:
    1. CRUCIBLE_API_KEY environment variable
    2. api_key from ~/.config/pycrucible/config.ini

    Returns:
        str: The API key

    Raises:
        ValueError: If no API key is found anywhere
    """
    return config.api_key


def get_api_url():
    """
    Get the Crucible API URL from configuration.

    Priority order:
    1. CRUCIBLE_API_URL environment variable
    2. api_url from ~/.config/pycrucible/config.ini
    3. Default: https://crucible.lbl.gov/testapi

    Returns:
        str: The API URL
    """
    return config.api_url


def get_cache_dir():
    """
    Get the cache directory for storing downloaded data.

    Priority order:
    1. PYCRUCIBLE_CACHE_DIR environment variable
    2. cache_dir from ~/.config/pycrucible/config.ini
    3. Default: ~/.cache/pycrucible/ (platform-specific)

    Returns:
        Path: The cache directory path
    """
    return config.cache_dir


def get_orcid_id():
    """
    Get the user's ORCID ID from configuration.

    Priority order:
    1. ORCID_ID environment variable
    2. orcid_id from ~/.config/pycrucible/config.ini
    3. None if not configured

    Returns:
        str or None: The ORCID ID if configured, None otherwise
    """
    return config.orcid_id


def get_graph_explorer_url():
    """
    Get the Crucible Graph Explorer URL from configuration.

    Priority order:
    1. CRUCIBLE_GRAPH_EXPLORER_URL environment variable
    2. graph_explorer_url from ~/.config/pycrucible/config.ini
    3. Default: https://crucible-graph-explorer-776258882599.us-central1.run.app

    Returns:
        str: The graph explorer URL
    """
    return config.graph_explorer_url


def get_current_project():
    """
    Get the current/default project ID from configuration.

    Priority order:
    1. CRUCIBLE_CURRENT_PROJECT environment variable
    2. current_project from ~/.config/pycrucible/config.ini
    3. None if not configured

    Returns:
        str or None: The current project ID if configured, None otherwise
    """
    return config.current_project


def get_client():
    """
    Get a configured CrucibleClient instance.

    Returns:
        CrucibleClient: Configured client instance

    Raises:
        ValueError: If API key is not configured
    """
    return config.client


def create_config_file(api_key, api_url=None, cache_dir=None, orcid_id=None, **kwargs):
    """
    Create a configuration file with the given API key and optional settings.

    Args:
        api_key (str): The API key to store
        api_url (str, optional): Custom API URL. Defaults to https://crucible.lbl.gov/testapi
        cache_dir (str, optional): Custom cache directory path. If not provided,
                                   defaults to platform-specific cache directory
        orcid_id (str, optional): User's ORCID ID (e.g., '0000-0002-1234-5678')
        **kwargs: Additional configuration values to store

    Returns:
        Path: Path to the created config file
    """
    config_dir = Path(user_config_dir("pycrucible"))
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.ini"

    parser = configparser.ConfigParser()

    # Build config dictionary
    config_data = {"api_key": api_key}

    if api_url is not None:
        config_data["api_url"] = str(api_url)

    if cache_dir is not None:
        config_data["cache_dir"] = str(cache_dir)

    if orcid_id is not None:
        config_data["orcid_id"] = str(orcid_id)

    # Add any additional kwargs
    config_data.update(kwargs)

    # Set up crucible section
    parser["crucible"] = config_data

    with open(config_file, 'w') as f:
        parser.write(f)

    logger.info(f"Created config file: {config_file}")
    for key, value in config_data.items():
        if key != "api_key":  # Don't log the API key
            logger.debug(f"{key}: {value}")

    # Reload the global config
    config.reload()

    return config_file


def get_config_file_path():
    """Get the path where the config file should be located."""
    return config.config_file_path
