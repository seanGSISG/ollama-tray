"""
Ollama Tray App - A system tray application to control and monitor Ollama AI model server
"""

from .version import VERSION as __version__

# Export main classes for easy imports
from .models import ModelManager
from .config import get_config, save_config
