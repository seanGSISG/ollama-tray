# 🦙 Ollama Tray App

![Build & Release](https://github.com/seanGSISG/ollama-tray/actions/workflows/build-appimage.yml/badge.svg)

A lightweight Linux system tray application to monitor and control the `ollama` model server.

![image](https://github.com/user-attachments/assets/d545c412-3378-44a8-98e0-6c9a3594b744)


## ✅ Features

- Start/stop the `ollama` systemd service
- Monitor loaded models
- View GPU memory usage (NVIDIA only)
- See token context window usage
- Tray notifications for model events
- Open model directory in file manager
- **NEW:** Model management (pull/delete models)
- **NEW:** Run models directly in terminal from the UI
- **NEW:** Customizable settings via configuration UI
- **NEW:** About dialog with version information

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
│   ├── config.py        # Configuration management
│   ├── models.py        # Model management utilities
│   ├── ollama-tray.py   # Main application
│   ├── ollama.png       # Application icon
│   ├── ui.py            # UI components for settings and dialogs
│   └── version.py       # Version information
├── appimage/
│   └── AppRun           # AppImage runner script
├── .github/workflows/build-appimage.yml
├── ollama-tray.desktop  # Desktop entry file
├── requirements.txt     # Python dependencies
└── README.md            # Documentation
```

## ⚙️ Configuration

The application can be configured via the Settings dialog. Configuration is stored in `~/.config/ollama-tray/config.json`.

Available settings:

- **Service Name**: The systemd service name for ollama (default: `ollama.service`)
- **API URL**: The URL of the Ollama API (default: `http://127.0.0.1:11434`)
- **Model Directory**: The directory where models are stored (default: `~/.ollama/models`)
- **Refresh Interval**: How often the status is updated (default: `15000 ms`)
- **Log File**: The file where logs are written (default: `~/.cache/ollama-tray.log`)
- **Log Level**: The level of logging detail (default: `INFO`)

## 🤖 Model Management

The Model Management feature allows you to:

1. **View Installed Models**: See all models currently installed in your Ollama instance
2. **Pull New Models**: Download new models from the Ollama library
3. **Remove Models**: Delete models you no longer need to free up disk space
4. **Monitor Disk Usage**: See how much disk space your models are using

Access model management through the tray menu option "Manage Models..."

### Available Models

Ollama supports various models including:

- `llama2` - Meta's Llama 2 models
- `mistral` - Mistral AI's models
- `gemma` - Google's Gemma models
- `phi` - Microsoft's Phi models
- `orca-mini` - Smaller, faster models
- And many more!

You can specify model variants like `llama2:7b` or `llama2:13b` when pulling.

## 📝 License

MIT
