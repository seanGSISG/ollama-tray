#!/usr/bin/env python3
"""
UI components for Ollama Tray application
"""

import os
import sys
import logging
from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QLineEdit, QSpinBox, QPushButton, QFileDialog, QComboBox,
    QFormLayout, QGroupBox, QCheckBox, QDialogButtonBox,
    QTextBrowser, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QFont

from .version import get_version_info
from .config import save_config, DEFAULT_CONFIG

logger = logging.getLogger('ollama-tray.ui')

class AboutDialog(QDialog):
    """About dialog showing version information"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Ollama Tray")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # App name and icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            icon_layout = QHBoxLayout()
            icon_label = QLabel()
            icon_pixmap = QPixmap(icon_path).scaled(64, 64, Qt.KeepAspectRatio)
            icon_label.setPixmap(icon_pixmap)
            icon_layout.addWidget(icon_label)

            app_name = QLabel("Ollama Tray")
            app_name.setStyleSheet("font-size: 18pt; font-weight: bold;")
            icon_layout.addWidget(app_name)
            icon_layout.addStretch()
            layout.addLayout(icon_layout)

        # Version info
        info = get_version_info()
        version_layout = QFormLayout()
        version_layout.addRow("Version:", QLabel(f"v{info['version']}"))
        version_layout.addRow("Build Date:", QLabel(info['build_date']))

        if 'git_revision' in info:
            version_layout.addRow("Git Revision:", QLabel(info['git_revision']))

        version_layout.addRow("Python:", QLabel(info['python_version']))

        version_group = QGroupBox("Version Information")
        version_group.setLayout(version_layout)
        layout.addWidget(version_group)

        # Description
        description = QTextBrowser()
        description.setMaximumHeight(100)
        description.setOpenExternalLinks(True)
        description.setHtml("""
        <p>A lightweight Linux system tray application to monitor and control the Ollama model server.</p>
        <p>Project repository: <a href="https://github.com/seanGSISG/ollama-tray">github.com/seanGSISG/ollama-tray</a></p>
        <p>License: MIT</p>
        """)
        layout.addWidget(description)

        # OK button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.setLayout(layout)


class ConfigDialog(QDialog):
    """Configuration dialog for application settings"""
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ollama Tray Settings")
        self.setMinimumWidth(500)
        self.config = current_config.copy()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        tabs = QTabWidget()

        # General Settings Tab
        general_tab = QWidget()
        general_layout = QFormLayout()

        # Service name
        self.service_name = QLineEdit(self.config.get("service_name", DEFAULT_CONFIG["service_name"]))
        general_layout.addRow("Service Name:", self.service_name)

        # API URL
        self.api_url = QLineEdit(self.config.get("api_url", DEFAULT_CONFIG["api_url"]))
        general_layout.addRow("API URL:", self.api_url)

        # Model directory with browse button
        model_dir_layout = QHBoxLayout()
        self.model_dir = QLineEdit(self.config.get("model_dir", DEFAULT_CONFIG["model_dir"]))
        model_dir_layout.addWidget(self.model_dir)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_model_dir)
        model_dir_layout.addWidget(browse_btn)

        general_layout.addRow("Model Directory:", model_dir_layout)

        # Refresh interval
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(1000, 60000)
        self.refresh_interval.setSingleStep(1000)
        self.refresh_interval.setSuffix(" ms")
        self.refresh_interval.setValue(int(self.config.get("refresh_interval", DEFAULT_CONFIG["refresh_interval"])))
        general_layout.addRow("Refresh Interval:", self.refresh_interval)

        general_tab.setLayout(general_layout)
        tabs.addTab(general_tab, "General")

        # Logging Tab
        logging_tab = QWidget()
        logging_layout = QFormLayout()

        # Log file
        log_file_layout = QHBoxLayout()
        self.log_file = QLineEdit(self.config.get("log_file", DEFAULT_CONFIG["log_file"]))
        log_file_layout.addWidget(self.log_file)

        log_browse_btn = QPushButton("Browse...")
        log_browse_btn.clicked.connect(self.browse_log_file)
        log_file_layout.addWidget(log_browse_btn)

        logging_layout.addRow("Log File:", log_file_layout)

        # Log level
        self.log_level = QComboBox()
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_level.addItems(log_levels)

        current_level = self.config.get("log_level", DEFAULT_CONFIG["log_level"])
        level_index = log_levels.index(current_level) if current_level in log_levels else 1  # Default to INFO
        self.log_level.setCurrentIndex(level_index)

        logging_layout.addRow("Log Level:", self.log_level)

        logging_tab.setLayout(logging_layout)
        tabs.addTab(logging_tab, "Logging")

        # Add tabs to layout
        layout.addWidget(tabs)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def browse_model_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Models Directory",
            os.path.expanduser(self.model_dir.text())
        )
        if directory:
            self.model_dir.setText(directory)

    def browse_log_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Log File",
            os.path.expanduser(self.log_file.text()),
            "Log Files (*.log);;All Files (*)"
        )
        if file_path:
            self.log_file.setText(file_path)

    def save_settings(self):
        # Build config from UI values
        self.config["service_name"] = self.service_name.text()
        self.config["api_url"] = self.api_url.text()
        self.config["model_dir"] = self.model_dir.text()
        self.config["refresh_interval"] = self.refresh_interval.value()
        self.config["log_file"] = self.log_file.text()
        self.config["log_level"] = self.log_level.currentText()

        # Save to file
        if save_config(self.config):
            logger.info("Configuration saved successfully")
            QMessageBox.information(self, "Settings Saved",
                                   "Your settings have been saved. Please restart the application for all changes to take effect.")
            self.accept()
        else:
            logger.error("Failed to save configuration")
            QMessageBox.critical(self, "Error", "Failed to save configuration.")


class ModelsDialog(QDialog):
    """Dialog for model management"""
    def __init__(self, model_manager, parent=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.setWindowTitle("Manage Ollama Models")
        self.setMinimumSize(600, 400)
        self.model_list = []
        self.init_ui()
        self.load_models()

    def init_ui(self):
        layout = QVBoxLayout()

        # Model stats
        stats_layout = QHBoxLayout()
        self.model_count_label = QLabel("0 models")
        stats_layout.addWidget(self.model_count_label)

        stats_layout.addStretch()

        self.disk_usage_label = QLabel("Disk usage: 0 MB")
        stats_layout.addWidget(self.disk_usage_label)

        layout.addLayout(stats_layout)

        # Models table
        self.models_table = QTableWidget(0, 3)
        self.models_table.setHorizontalHeaderLabels(["Model", "Size", "Tags"])
        self.models_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.models_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.models_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.models_table)

        # Model actions
        actions_layout = QHBoxLayout()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_models)
        actions_layout.addWidget(refresh_btn)

        # Pull a model
        pull_btn = QPushButton("Pull Model")
        pull_btn.clicked.connect(self.pull_model_dialog)
        actions_layout.addWidget(pull_btn)

        # Remove model
        remove_btn = QPushButton("Delete Model")
        remove_btn.clicked.connect(self.remove_selected_model)
        actions_layout.addWidget(remove_btn)
        
        # Run model in terminal
        run_btn = QPushButton("Run in Terminal")
        run_btn.clicked.connect(self.run_model_in_terminal)
        actions_layout.addWidget(run_btn)

        layout.addLayout(actions_layout)

        # Progress section (hidden by default)
        self.progress_group = QGroupBox("Operation Progress")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Idle")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        progress_layout.addWidget(self.progress_bar)

        self.progress_group.setLayout(progress_layout)
        self.progress_group.setVisible(False)
        layout.addWidget(self.progress_group)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.accept)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def load_models(self):
        """Load models from API and display in table"""
        self.models_table.setRowCount(0)
        self.model_list = self.model_manager.list_models()

        if not self.model_list:
            self.model_count_label.setText("No models found")
            disk_usage = self.model_manager.get_disk_usage()
            self.disk_usage_label.setText(f"Disk usage: {disk_usage:.1f} MB")
            return

        self.model_count_label.setText(f"{len(self.model_list)} models")

        # Update disk usage
        disk_usage = self.model_manager.get_disk_usage()
        self.disk_usage_label.setText(f"Disk usage: {disk_usage:.1f} MB")

        # Populate table
        self.models_table.setRowCount(len(self.model_list))

        for i, model in enumerate(self.model_list):
            # Model name
            name_item = QTableWidgetItem(model.get("name", ""))
            self.models_table.setItem(i, 0, name_item)

            # Size
            size_mb = model.get("size", 0) / (1024 * 1024)
            size_item = QTableWidgetItem(f"{size_mb:.1f} MB")
            self.models_table.setItem(i, 1, size_item)

            # Tags
            tags = ", ".join(model.get("tags", []))
            tags_item = QTableWidgetItem(tags if tags else "none")
            self.models_table.setItem(i, 2, tags_item)

    def pull_model_dialog(self):
        """Show dialog to pull a new model"""
        model_name, ok = QInputDialog.getText(
            self, "Pull Model",
            "Enter model name to download (e.g., 'llama2', 'llama2:7b'):"
        )

        if ok and model_name:
            # Show progress
            self.progress_group.setVisible(True)
            self.progress_label.setText(f"Downloading {model_name}...")

            # Define callback for progress updates
            def update_progress(line):
                if "download" in line.lower():
                    self.progress_label.setText(line)

            # Pull in a background thread
            class PullThread(QThread):
                finished_signal = pyqtSignal(bool)

                def __init__(self, model_manager, model_name, callback):
                    super().__init__()
                    self.model_manager = model_manager
                    self.model_name = model_name
                    self.callback = callback

                def run(self):
                    result = self.model_manager.pull_model(self.model_name, self.callback)
                    self.finished_signal.emit(result)

            self.pull_thread = PullThread(self.model_manager, model_name, update_progress)
            self.pull_thread.finished_signal.connect(self.on_pull_finished)
            self.pull_thread.start()

    def on_pull_finished(self, success):
        """Handle completion of model pull operation"""
        self.progress_group.setVisible(False)

        if success:
            QMessageBox.information(self, "Success", "Model pulled successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to pull model. Check logs for details.")

        # Refresh model list
        self.load_models()

    def remove_selected_model(self):
        """Remove the selected model"""
        selected_items = self.models_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a model to delete.")
            return

        # Get model name from the first column of the selected row
        row = selected_items[0].row()
        model_name = self.models_table.item(row, 0).text()

        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete model '{model_name}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Show progress
            self.progress_group.setVisible(True)
            self.progress_label.setText(f"Removing {model_name}...")

            # Remove in a background thread
            class RemoveThread(QThread):
                finished_signal = pyqtSignal(bool)

                def __init__(self, model_manager, model_name):
                    super().__init__()
                    self.model_manager = model_manager
                    self.model_name = model_name

                def run(self):
                    result = self.model_manager.remove_model(self.model_name)
                    self.finished_signal.emit(result)

            self.remove_thread = RemoveThread(self.model_manager, model_name)
            self.remove_thread.finished_signal.connect(self.on_remove_finished)
            self.remove_thread.start()

    def on_remove_finished(self, success):
        """Handle completion of model removal operation"""
        self.progress_group.setVisible(False)

        if success:
            QMessageBox.information(self, "Success", "Model removed successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to remove model. Check logs for details.")

        # Refresh model list
        self.load_models()
    
    def run_model_in_terminal(self):
        """Run the selected model in a terminal"""
        selected_items = self.models_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a model to run.")
            return
        
        # Get model name from the first column of the selected row
        row = selected_items[0].row()
        model_name = self.models_table.item(row, 0).text()
        
        # Check if service is running
        try:
            import subprocess
            result = subprocess.run(['systemctl', '--user', 'is-active', 'ollama.service'], 
                                  capture_output=True, text=True)
            if result.stdout.strip() != 'active':
                reply = QMessageBox.question(
                    self, "Service Not Running",
                    "Ollama service is not running. Would you like to start it first?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    subprocess.run(['systemctl', '--user', 'start', 'ollama.service'])
                    # Wait a moment for service to start
                    import time
                    time.sleep(2)
        except Exception as e:
            logger.warning(f"Could not check service status: {e}")
        
        # Try different terminal emulators in order of preference
        terminal_commands = [
            # KDE Konsole
            ['konsole', '-e', 'bash', '-c', f'ollama run {model_name}; echo "Press Enter to close..."; read'],
            # GNOME Terminal
            ['gnome-terminal', '--', 'bash', '-c', f'ollama run {model_name}; echo "Press Enter to close..."; read'],
            # xterm (fallback)
            ['xterm', '-e', 'bash', '-c', f'ollama run {model_name}; echo "Press Enter to close..."; read'],
            # Generic x-terminal-emulator (Debian/Ubuntu)
            ['x-terminal-emulator', '-e', 'bash', '-c', f'ollama run {model_name}; echo "Press Enter to close..."; read']
        ]
        
        # Try each terminal command
        for cmd in terminal_commands:
            try:
                import subprocess
                subprocess.Popen(cmd)
                logger.info(f"Launched terminal with model: {model_name}")
                return
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.error(f"Error launching terminal with {cmd[0]}: {e}")
                continue
        
        # If we get here, no terminal worked
        QMessageBox.critical(self, "Error", 
                           "Could not find a suitable terminal emulator.\n"
                           "Please run manually: ollama run " + model_name)
