#!/usr/bin/env python3
"""
Model management utilities for Ollama Tray
"""

import os
import json
import logging
import requests
import subprocess
from urllib.parse import urljoin

logger = logging.getLogger('ollama-tray.models')

class ModelManager:
    def __init__(self, api_url, model_dir):
        self.api_url = api_url
        self.model_dir = os.path.expanduser(model_dir)
        self.timeout = 5  # seconds for API requests

    def list_models(self):
        """List all available models from Ollama API"""
        try:
            res = requests.get(urljoin(self.api_url, "/api/tags"), timeout=self.timeout)
            if res.ok:
                return res.json().get("models", [])
            logger.warning(f"Failed to get models: HTTP {res.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    def get_model_details(self, model_name):
        """Get detailed information about a specific model"""
        try:
            res = requests.post(
                urljoin(self.api_url, "/api/show"),
                json={"name": model_name},
                timeout=self.timeout
            )
            if res.ok:
                return res.json()
            logger.warning(f"Failed to get model details: HTTP {res.status_code}")
            return {}
        except Exception as e:
            logger.error(f"Error getting model details: {e}")
            return {}

    def pull_model(self, model_name, callback=None):
        """Pull a model from Ollama library"""
        try:
            cmd = ["ollama", "pull", model_name]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                if callback:
                    callback(line.strip())
                logger.info(f"Pull progress: {line.strip()}")

            return_code = process.wait()
            if return_code != 0:
                logger.error(f"Failed to pull model {model_name}, return code: {return_code}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False

    def remove_model(self, model_name):
        """Remove a model from Ollama"""
        try:
            res = requests.delete(
                urljoin(self.api_url, "/api/delete"),
                json={"name": model_name},
                timeout=self.timeout
            )
            if res.ok:
                logger.info(f"Successfully removed model {model_name}")
                return True
            logger.warning(f"Failed to remove model: HTTP {res.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error removing model: {e}")
            return False

    def get_disk_usage(self):
        """Get disk usage information for models directory"""
        try:
            if not os.path.exists(self.model_dir):
                return 0

            total_size = 0
            for path, dirs, files in os.walk(self.model_dir):
                for f in files:
                    fp = os.path.join(path, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)

            # Return size in MB
            return total_size / (1024 * 1024)
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return 0
