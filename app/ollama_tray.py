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
ICON_PATH = os.path.join(SCRIPT_DIR, "icon_64.png")  # Use smaller icon for system tray
MODEL_DIR = config.get('model_dir', '~/.ollama/models')
REFRESH_INTERVAL = config.get('refresh_interval', 15000)  # ms

class OllamaTray:
    def __init__(self, app):
        self.app = app
        self.tray = QSystemTrayIcon(QIcon(ICON_PATH))
        self.tray.setToolTip("Ollama Service Monitor")
        self.menu = QMenu()
        self.last_model_count = 0
        self.model_manager = ModelManager(OLLAMA_URL, MODEL_DIR)
        self.config = config
        self.setup_ui()

    def setup_ui(self):
        # Status indicators
        self.status_action = QAction("Status: checking...", self.menu)
        self.status_action.setDisabled(True)
        self.menu.addAction(self.status_action)

        self.model_action = QAction("Models: checking...", self.menu)
        self.model_action.setDisabled(True)
        self.menu.addAction(self.model_action)

        self.gpu_action = QAction("GPU: checking...", self.menu)
        self.gpu_action.setDisabled(True)
        self.menu.addAction(self.gpu_action)

        self.token_action = QAction("Context: -", self.menu)
        self.token_action.setDisabled(True)
        self.menu.addAction(self.token_action)

        self.menu.addSeparator()

        # Controls
        start_action = QAction("Start Ollama", self.menu)
        start_action.triggered.connect(self.start_ollama)
        self.menu.addAction(start_action)

        stop_action = QAction("Stop Ollama", self.menu)
        stop_action.triggered.connect(self.stop_ollama)
        self.menu.addAction(stop_action)

        # Model Management
        model_management_action = QAction("Manage Models...", self.menu)
        model_management_action.triggered.connect(self.show_model_management)
        self.menu.addAction(model_management_action)

        open_folder_action = QAction("Open Model Folder", self.menu)
        open_folder_action.triggered.connect(self.open_model_folder)
        self.menu.addAction(open_folder_action)

        self.menu.addSeparator()

        # Settings
        settings_action = QAction("Settings...", self.menu)
        settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(settings_action)

        refresh_action = QAction("Refresh", self.menu)
        refresh_action.triggered.connect(self.refresh)
        self.menu.addAction(refresh_action)

        # About
        about_action = QAction("About", self.menu)
        about_action.triggered.connect(self.show_about)
        self.menu.addAction(about_action)

        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)
        
        # Log menu structure for debugging
        logger.info(f"Menu has {len(self.menu.actions())} actions")
        for action in self.menu.actions():
            logger.info(f"  - {action.text()}")

    def start_ollama(self):
        logger.info("Starting Ollama service")
        try:
            subprocess.Popen(["systemctl", "--user", "start", SERVICE_NAME])
            QTimer.singleShot(2000, self.refresh)  # Refresh after a delay
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}", exc_info=True)
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
        expanded_path = os.path.expanduser(MODEL_DIR)
        logger.info(f"Opening model folder: {expanded_path}")
        try:
            subprocess.Popen(["xdg-open", expanded_path])
        except Exception as e:
            logger.error(f"Failed to open model folder: {e}", exc_info=True)
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
        logger.info("Refreshing status")
        try:
            running = self.is_service_running()
            self.status_action.setText(f"Status: {'Running' if running else 'Stopped'}")
            logger.info(f"Service running: {running}")

            models, model_msg = self.get_model_status()
            self.model_action.setText(f"Models: {model_msg}")
            logger.info(f"Models: {model_msg}")

            if running:
                gpu_info = self.get_gpu_memory()
                self.gpu_action.setText(f"GPU: {gpu_info}")
                logger.info(f"GPU: {gpu_info}")
                
                token_info = self.get_token_usage()
                self.token_action.setText(f"Context: {token_info}")
                logger.info(f"Context: {token_info}")

            if running and len(models) != self.last_model_count:
                self.tray.showMessage("Ollama Status", model_msg, QSystemTrayIcon.Information, 3000)
                self.last_model_count = len(models)
        except Exception as e:
            logger.error(f"Error during refresh: {e}", exc_info=True)

    def show_error(self, message):
        QMessageBox.critical(None, "Ollama Tray Error", message)

    def show_model_management(self):
        """Show the model management dialog"""
        try:
            dialog = ModelsDialog(self.model_manager)
            dialog.exec_()
            self.refresh()  # Refresh after dialog closes
        except Exception as e:
            logger.error(f"Error showing models dialog: {e}", exc_info=True)
            self.show_error(f"Failed to open models dialog: {e}")

    def show_settings(self):
        """Show the settings dialog"""
        try:
            dialog = ConfigDialog(self.config)
            if dialog.exec_() == dialog.Accepted:
                # Settings were saved, reload config
                self.config = get_config()
                QMessageBox.information(None, "Restart Required",
                                       "Some settings will take effect after restarting the application.")
        except Exception as e:
            logger.error(f"Error showing settings dialog: {e}", exc_info=True)
            self.show_error(f"Failed to open settings dialog: {e}")

    def show_about(self):
        """Show the about dialog"""
        try:
            dialog = AboutDialog()
            dialog.exec_()
        except Exception as e:
            logger.error(f"Error showing about dialog: {e}", exc_info=True)
            self.show_error(f"Failed to open about dialog: {e}")

    def run(self):
        logger.info("Starting Ollama Tray application")
        
        # Ensure tray is visible
        self.tray.show()
        logger.info(f"Tray icon shown: {self.tray.isVisible()}")
        logger.info(f"Icon path: {ICON_PATH}")
        logger.info(f"Icon exists: {os.path.exists(ICON_PATH)}")
        
        # Set the application not to quit when last window closes
        self.app.setQuitOnLastWindowClosed(False)
        
        # Show a notification
        if QSystemTrayIcon.supportsMessages():
            self.tray.showMessage("Ollama Tray", "Application started", QSystemTrayIcon.Information, 3000)
        
        self.refresh()

        # Set up the refresh timer
        timer = QTimer()
        timer.timeout.connect(self.refresh)
        timer.start(REFRESH_INTERVAL)

        logger.info("Starting main event loop")
        return self.app.exec_()

def main():
    """Entry point for the application when installed as a package"""
    try:
        # Check if another instance is running
        app = QApplication(sys.argv)
        
        # Check system tray availability
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.error("System tray is not available!")
            QMessageBox.critical(None, "System Tray Not Found", 
                               "System tray is not available. Please ensure your desktop environment supports system tray icons.")
            sys.exit(1)
            
        # Create and run the tray application
        tray_app = OllamaTray(app)
        sys.exit(tray_app.run())
    except Exception as e:
        logging.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
