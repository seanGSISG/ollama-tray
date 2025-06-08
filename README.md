# 🦙 Ollama Tray App

![Build & Release](https://github.com/YOUR_USERNAME/ollama-tray/actions/workflows/build-appimage.yml/badge.svg)

A lightweight Linux system tray application to monitor and control the `ollama` model server.

## ✅ Features

- Start/stop the `ollama` systemd service
- Monitor loaded models
- View GPU memory usage (NVIDIA only)
- See token context window usage
- Tray notifications for model events
- Open model directory in file manager

## 🧪 Requirements

- Linux (tested on Arch/KDE Wayland)
- Python 3.11+
- Python packages in `requirements.txt`

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python3 app/ollama-tray.py
```

## 📁 Project Structure

```
ollama-tray/
├── app/
│   ├── ollama-tray.py
│   └── ollama.png
├── appimage/
│   └── AppRun
├── .github/workflows/build-appimage.yml
├── ollama-tray.desktop
├── requirements.txt
└── README.md
```

## 📝 License

MIT
