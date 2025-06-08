#!/usr/bin/env python3
"""
Configuration settings for Ollama Tray application
"""

import os
import json

# Default configuration
DEFAULT_CONFIG = {
    "service_name": "ollama.service",
    "api_url": "http://127.0.0.1:11434",
    "model_dir": "~/.ollama/models",
    "refresh_interval": 15000,  # milliseconds
    "log_file": "~/.cache/ollama-tray.log",
    "log_level": "INFO"
}

# Configuration file path
CONFIG_FILE = os.path.expanduser("~/.config/ollama-tray/config.json")

def get_config():
    """Load configuration from file or return defaults"""
    config = DEFAULT_CONFIG.copy()

    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        # Continue with defaults

    # Ensure paths are expanded
    for key in ['model_dir', 'log_file']:
        if key in config:
            config[key] = os.path.expanduser(config[key])

    return config

def save_config(config):
    """Save configuration to file"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Failed to save configuration: {e}")
        return False
