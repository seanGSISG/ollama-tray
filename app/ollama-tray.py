#!/usr/bin/env python3

import sys, os, subprocess, psutil, requests
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer

SERVICE_NAME = "ollama.service"
OLLAMA_URL = "http://127.0.0.1:11434"
ICON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon.png"))
MODEL_DIR = os.path.expanduser("~/.ollama/models")

app = QApplication(sys.argv)
tray = QSystemTrayIcon(QIcon(ICON_PATH))
tray.setToolTip("Ollama Service Monitor")
menu = QMenu()

status_action = QAction("Status: checking...")
status_action.setDisabled(True)
menu.addAction(status_action)

model_action = QAction("Models: checking...")
model_action.setDisabled(True)
menu.addAction(model_action)

gpu_action = QAction("GPU: checking...")
gpu_action.setDisabled(True)
menu.addAction(gpu_action)

token_action = QAction("Context: -")
token_action.setDisabled(True)
menu.addAction(token_action)

menu.addSeparator()

start_action = QAction("Start Ollama")
start_action.triggered.connect(lambda: subprocess.Popen(["systemctl", "--user", "start", SERVICE_NAME]))
menu.addAction(start_action)

stop_action = QAction("Stop Ollama")
stop_action.triggered.connect(lambda: subprocess.Popen(["systemctl", "--user", "stop", SERVICE_NAME]))
menu.addAction(stop_action)

open_folder_action = QAction("Open Model Folder")
open_folder_action.triggered.connect(lambda: subprocess.Popen(["xdg-open", MODEL_DIR]))
menu.addAction(open_folder_action)

menu.addSeparator()

refresh_action = QAction("Refresh")
menu.addAction(refresh_action)

quit_action = QAction("Quit")
quit_action.triggered.connect(app.quit)
menu.addAction(quit_action)

tray.setContextMenu(menu)

def is_service_running():
    try:
        output = subprocess.check_output(["systemctl", "--user", "is-active", SERVICE_NAME])
        return output.strip() == b"active"
    except subprocess.CalledProcessError:
        return False

def get_model_status():
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1)
        if res.ok:
            models = res.json().get("models", [])
            return models, f"{len(models)} model(s) loaded" if models else "No models loaded"
    except:
        pass
    return [], "Ollama not responding"

def get_token_usage():
    try:
        res = requests.get(f"{OLLAMA_URL}/api/generate/status", timeout=1)
        if res.ok:
            data = res.json()
            tokens = data.get("context_size", 0)
            used = data.get("context_used", 0)
            return f"{used}/{tokens} tokens"
    except:
        return "-"
    return "-"

def get_gpu_memory():
    try:
        output = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"])
        used, total = map(int, output.decode().strip().split(','))
        return f"{used} MiB / {total} MiB"
    except:
        return "NVIDIA GPU not found"

last_model_count = 0

def refresh():
    global last_model_count
    running = is_service_running()
    status_action.setText(f"Status: {'Running' if running else 'Stopped'}")
    models, model_msg = get_model_status()
    model_action.setText(f"Models: {model_msg}")

    if running:
        gpu_action.setText(f"GPU: {get_gpu_memory()}")
        token_action.setText(f"Context: {get_token_usage()}")

    if running and len(models) != last_model_count:
        tray.showMessage("Ollama Status", model_msg, QSystemTrayIcon.Information, 3000)
        last_model_count = len(models)

refresh_action.triggered.connect(refresh)

timer = QTimer()
timer.timeout.connect(refresh)
timer.start(15000)

tray.show()
refresh()
sys.exit(app.exec_())
