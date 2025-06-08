# Release Notes

## Version 0.3.0 (June 7, 2025)

### New Features:

- **Model Management**: Added UI for downloading, viewing and removing Ollama models
  - List all installed models with sizes and tags
  - Pull new models from Ollama library
  - Remove unwanted models to free up space
  - Monitor disk usage for models

- **Configuration System**: Added a settings dialog
  - Customize service name, API URL, model directory
  - Configure refresh interval for status updates
  - Set logging preferences and locations
  - Settings persisted in `~/.config/ollama-tray/config.json`

- **About Dialog**: Added version information screen
  - Shows version number, build date
  - Git commit information when available
  - System information

### Improvements:

- Better error handling with detailed logging
- Modular code structure with separate functionality in modules
- Updated documentation with new features
- Clean modern UI for dialogs

### Bug Fixes:

- Fixed icon path references
- Improved error handling for network issues

## Version 0.2.0 (Initial Release)

- Basic tray functionality
- Start/stop Ollama service
- Monitor loaded models
- Check GPU usage
- View token usage
