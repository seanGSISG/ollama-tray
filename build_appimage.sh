#!/bin/bash

# Build script for OllamaTray AppImage

# Exit on error
set -e

echo "Building OllamaTray AppImage..."

# Prepare AppDir
echo "Preparing AppDir..."
rm -rf AppDir
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/lib/qt5/plugins/platforms
mkdir -p AppDir/usr/share/icons/hicolor/128x128/apps
mkdir -p AppDir/usr/share/icons/hicolor/64x64/apps
mkdir -p AppDir/usr/share/icons/hicolor/48x48/apps
mkdir -p AppDir/usr/share/icons/hicolor/32x32/apps
mkdir -p AppDir/usr/share/icons/hicolor/24x24/apps
mkdir -p AppDir/usr/share/icons/hicolor/22x22/apps

# Copy application files
cp -r app AppDir/usr/bin/
cp ollama-tray.desktop AppDir/
cp app/icon.png AppDir/icon.png
cp appimage/AppRun AppDir/AppRun
chmod +x AppDir/AppRun

# Copy icons to proper locations
echo "Installing icons..."
cp app/icon_128.png AppDir/usr/share/icons/hicolor/128x128/apps/ollama-tray.png
cp app/icon_64.png AppDir/usr/share/icons/hicolor/64x64/apps/ollama-tray.png
cp app/icon_48.png AppDir/usr/share/icons/hicolor/48x48/apps/ollama-tray.png
cp app/icon_32.png AppDir/usr/share/icons/hicolor/32x32/apps/ollama-tray.png
cp app/icon_24.png AppDir/usr/share/icons/hicolor/24x24/apps/ollama-tray.png
cp app/icon_22.png AppDir/usr/share/icons/hicolor/22x22/apps/ollama-tray.png

# Copy PyQt5 platform plugins for standalone operation
echo "Copying Qt5 platform plugins..."
if [ -d /usr/lib/x86_64-linux-gnu/qt5/plugins/platforms ]; then
  cp -r /usr/lib/x86_64-linux-gnu/qt5/plugins/platforms AppDir/usr/lib/qt5/plugins/
elif [ -d /usr/lib/python3/dist-packages/PyQt5/Qt5/plugins/platforms ]; then
  cp -r /usr/lib/python3/dist-packages/PyQt5/Qt5/plugins/platforms AppDir/usr/lib/qt5/plugins/
else
  echo "Warning: Qt5 platform plugins not found in expected locations"
fi

# Download appimagetool if not exists
if [ ! -f appimagetool-x86_64.AppImage ]; then
    echo "Downloading appimagetool..."
    wget https://github.com/AppImage/AppImageKit/releases/latest/download/appimagetool-x86_64.AppImage
    chmod +x appimagetool-x86_64.AppImage
fi

# Get version
VERSION=$(date +'%Y%m%d')-$(git rev-parse --short HEAD)
APPIMAGE_NAME="OllamaTray-$VERSION.AppImage"

# Build AppImage
echo "Building AppImage: $APPIMAGE_NAME"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 ./appimagetool-x86_64.AppImage AppDir "$APPIMAGE_NAME"

echo "Build complete! AppImage created: $APPIMAGE_NAME"
echo ""
echo "To run it: ./$APPIMAGE_NAME"