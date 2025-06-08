#!/usr/bin/env python3
"""
Version information for Ollama Tray Application
"""

import os
import subprocess
from datetime import datetime

# Version constants
VERSION = "0.3.0"
BUILD_DATE = "2025-06-07"  # ISO format YYYY-MM-DD

def get_version_info():
    """Returns dictionary with version information"""
    info = {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "python_version": subprocess.check_output(["python3", "--version"]).decode().strip(),
    }

    # Try to get git revision if we're in a git repo
    try:
        git_rev = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        info["git_revision"] = git_rev
    except (subprocess.SubprocessError, FileNotFoundError):
        info["git_revision"] = "unknown"

    return info

def get_version_string():
    """Returns a formatted version string"""
    info = get_version_info()
    return f"v{info['version']} ({info['git_revision']})"
