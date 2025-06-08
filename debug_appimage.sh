#!/bin/bash

# Debug script for AppImage issues

# Check if the AppImage path was provided
if [ -z "$1" ]; then
    echo "Usage: $0 /path/to/your/OllamaTray.AppImage"
    exit 1
fi

APPIMAGE_PATH="$1"

# Check if file exists
if [ ! -f "$APPIMAGE_PATH" ]; then
    echo "Error: AppImage file not found at $APPIMAGE_PATH"
    exit 1
fi

# Make sure AppImage is executable
chmod +x "$APPIMAGE_PATH"

# Check for FUSE
echo "Checking for FUSE..."
if [ -f "/usr/lib/libfuse.so.2" ] || [ -f "/usr/lib/x86_64-linux-gnu/libfuse.so.2" ]; then
    echo "FUSE library found."
else
    echo "FUSE library not found. Installing it now..."
    sudo apt-get update
    sudo apt-get install -y libfuse2
fi

# Check for PyQt5
echo "Checking for PyQt5..."
python3 -c "import PyQt5" >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "PyQt5 is installed."
else
    echo "PyQt5 is not installed. Installing it now..."
    sudo apt-get install -y python3-pyqt5 libqt5gui5 libqt5widgets5 libqt5core5a
fi

# Try running with debug
echo "Running AppImage with debugging enabled..."
echo "------------------------------------------------------"
APPIMAGE_DEBUG=1 "$APPIMAGE_PATH"
echo "------------------------------------------------------"

# If it didn't work, try extract and run mode
if [ $? -ne 0 ]; then
    echo "Direct execution failed. Trying extract and run mode..."
    echo "------------------------------------------------------"

    # Create a temp directory
    TMP_DIR=$(mktemp -d)

    # Extract the AppImage
    echo "Extracting AppImage to $TMP_DIR..."
    "$APPIMAGE_PATH" --appimage-extract -o "$TMP_DIR"

    # Run the extracted AppRun
    echo "Running extracted AppRun..."
    cd "$TMP_DIR/squashfs-root"
    ./AppRun

    # Clean up
    echo "Cleaning up..."
    cd -
    rm -rf "$TMP_DIR"
fi

echo "Debug complete. If the application still doesn't run, check the output above for errors."
