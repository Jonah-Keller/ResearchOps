#!/bin/bash
# Build ~/Applications/ResearchOps.app (a Dock icon that runs launch.sh) and pin it
# to the Dock. Safe to re-run: it rebuilds the app and never adds a second Dock tile.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$HOME/Applications/ResearchOps.app"
mkdir -p "$HOME/Applications"; rm -rf "$APP"
osacompile -o "$APP" -e "do shell script quoted form of \"$DIR/launch.sh\" & \" > /dev/null 2>&1 &\""
cp "$DIR/assets/AppIcon.icns" "$APP/Contents/Resources/applet.icns"
plutil -replace CFBundleIdentifier -string local.researchops.launcher "$APP/Contents/Info.plist"
codesign --force --deep -s - "$APP" 2>/dev/null || true
touch "$APP"
if ! defaults read com.apple.dock persistent-apps 2>/dev/null | grep -q "ResearchOps.app"; then
  defaults write com.apple.dock persistent-apps -array-add "<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>file://$APP/</string><key>_CFURLStringType</key><integer>15</integer></dict></dict></dict>"
  killall Dock 2>/dev/null || true
fi
echo "ResearchOps icon is in your Dock (and in ~/Applications)."
