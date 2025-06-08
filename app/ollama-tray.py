#!/usr/bin/env python3

import sys, os, subprocess, psutil, requests, logging
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer

# Import local modules
from .config import get_config, save_config
from .models import ModelManager
from .ui import AboutDialog, ConfigDialog, ModelsDialog
from .version import get_version_string

# Get configuration
config = get_config()

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.get('log_level', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.get('log_file', '~/.cache/ollama-tray.log'))
    ]
)
logger = logging.getLogger('ollama-tray')

# Configuration
SERVICE_NAME = config.get('service_name', 'ollama.service')
OLLAMA_URL = config.get('api_url', 'http://127.0.0.1:11434')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(SCRIPT_DIR, "icon.png")  # Updated to use icon.png
MODEL_DIR = config.get('model_dir', '~/.ollama/models')
REFRESH_INTERVAL = config.get('refresh_interval', 15000)  # ms

class OllamaTray:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.tray = QSystemTrayIcon(QIcon(ICON_PATH))
        self.tray.setToolTip("Ollama Service Monitor")
        self.menu = QMenu()
        self.last_model_count = 0
        self.model_manager = ModelManager(OLLAMA_URL, MODEL_DIR)
        self.config = config
        self.setup_ui()

    def setup_ui(self):
        # Status indicators
        self.status_action = QAction("Status: checking...")
        self.status_action.setDisabled(True)
        self.menu.addAction(self.status_action)

        self.model_action = QAction("Models: checking...")
        self.model_action.setDisabled(True)
        self.menu.addAction(self.model_action)

        self.gpu_action = QAction("GPU: checking...")
        self.gpu_action.setDisabled(True)
        self.menu.addAction(self.gpu_action)

        self.token_action = QAction("Context: -")
        self.token_action.setDisabled(True)
        self.menu.addAction(self.token_action)

        self.menu.addSeparator()

        # Controls
        start_action = QAction("Start Ollama")
        start_action.triggered.connect(self.start_ollama)
        self.menu.addAction(start_action)

        stop_action = QAction("Stop Ollama")
        stop_action.triggered.connect(self.stop_ollama)
        self.menu.addAction(stop_action)

        # Model Management
        model_management_action = QAction("Manage Models...")
        model_management_action.triggered.connect(self.show_model_management)
        self.menu.addAction(model_management_action)

        open_folder_action = QAction("Open Model Folder")
        open_folder_action.triggered.connect(self.open_model_folder)
        self.menu.addAction(open_folder_action)

        self.menu.addSeparator()

        # Settings
        settings_action = QAction("Settings...")
        settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(settings_action)

        refresh_action = QAction("Refresh")
        refresh_action.triggered.connect(self.refresh)
        self.menu.addAction(refresh_action)

        # About
        about_action = QAction("About")
        about_action.triggered.connect(self.show_about)
        self.menu.addAction(about_action)

        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)

    def start_ollama(self):
        logger.info("Starting Ollama service")
        try:
            subprocess.Popen(["systemctl", "--user", "start", SERVICE_NAME])
            QTimer.singleShot(2000, self.refresh)  # Refresh after a delay
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            self.show_error(f"Failed to start Ollama: {e}")

    def stop_ollama(self):
        logger.info("Stopping Ollama service")
        try:
            subprocess.Popen(["systemctl", "--user", "stop", SERVICE_NAME])
            QTimer.singleShot(2000, self.refresh)  # Refresh after a delay
        except Exception as e:
            logger.error(f"Failed to stop Ollama: {e}")
            self.show_error(f"Failed to stop Ollama: {e}")

    def open_model_folder(self):
        logger.info(f"Opening model folder: {MODEL_DIR}")
        try:
            subprocess.Popen(["xdg-open", MODEL_DIR])
        except Exception as e:
            logger.error(f"Failed to open model folder: {e}")
            self.show_error(f"Failed to open model folder: {e}")

    def is_service_running(self):
        try:
            output = subprocess.check_output(["systemctl", "--user", "is-active", SERVICE_NAME])
            return output.strip() == b"active"
        except subprocess.CalledProcessError:
            return False
        except Exception as e:
            logger.error(f"Error checking service status: {e}")
            return False

    def get_model_status(self):
        try:
            models = self.model_manager.list_models()
            if models is not None:
                return models, f"{len(models)} model(s) loaded" if models else "No models loaded"
            logger.warning("Failed to get models from API")
        except requests.exceptions.ConnectionError:
            logger.debug("Connection refused - Ollama service might be down")
        except requests.exceptions.Timeout:
            logger.warning("Timeout connecting to Ollama API")
        except Exception as e:
            logger.error(f"Error getting model status: {e}")
        return [], "Ollama not responding"

    def get_token_usage(self):
        try:
            res = requests.get(f"{OLLAMA_URL}/api/generate/status", timeout=1)
            if res.ok:
                data = res.json()
                tokens = data.get("context_size", 0)
                used = data.get("context_used", 0)
                return f"{used}/{tokens} tokens"
            logger.debug(f"Token usage API returned status code: {res.status_code}")
        except Exception as e:
            logger.debug(f"Error getting token usage: {e}")
        return "-"

    def get_gpu_memory(self):
        try:
            output = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"])
            used, total = map(int, output.decode().strip().split(','))
            return f"{used} MiB / {total} MiB"
        except subprocess.SubprocessError:
            return "NVIDIA GPU not found"
        except Exception as e:
            logger.error(f"Error getting GPU info: {e}")
            return "Error reading GPU"

    def refresh(self):
        logger.debug("Refreshing status")
        try:
            running = self.is_service_running()
            self.status_action.setText(f"Status: {'Running' if running else 'Stopped'}")

            models, model_msg = self.get_model_status()
            self.model_action.setText(f"Models: {model_msg}")

            if running:
                self.gpu_action.setText(f"GPU: {self.get_gpu_memory()}")
                self.token_action.setText(f"Context: {self.get_token_usage()}")

            if running and len(models) != self.last_model_count:
                self.tray.showMessage("Ollama Status", model_msg, QSystemTrayIcon.Information, 3000)
                self.last_model_count = len(models)
        except Exception as e:
            logger.error(f"Error during refresh: {e}")

    def show_error(self, message):
        QMessageBox.critical(None, "Ollama Tray Error", message)

    def show_model_management(self):
        """Show the model management dialog"""
        dialog = ModelsDialog(self.model_manager)
        dialog.exec_()
        self.refresh()  # Refresh after dialog closes

    def show_settings(self):
        """Show the settings dialog"""
        dialog = ConfigDialog(self.config)
        if dialog.exec_() == dialog.Accepted:
            # Settings were saved, reload config
            self.config = get_config()
            QMessageBox.information(None, "Restart Required",
                                   "Some settings will take effect after restarting the application.")

    def show_about(self):
        """Show the about dialog"""
        dialog = AboutDialog()
        dialog.exec_()

    def run(self):
        self.tray.show()
        self.refresh()

        # Set up the refresh timer
        timer = QTimer()
        timer.timeout.connect(self.refresh)
        timer.start(REFRESH_INTERVAL)

        return self.app.exec_()

def main():
    """Entry point for the application when installed as a package"""
    try:
        tray_app = OllamaTray()
        sys.exit(tray_app.run())
    except Exception as e:
        logging.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
