#!/bin/sh
# Buduje pomocnik kalendarza jako małą aplikację (build/PanelKalendarz.app).
# Aplikacja jest potrzebna, żeby macOS mógł zapytać o zgodę na dostęp do kalendarza.
# Uwaga: po każdym przebudowaniu macOS zapyta o zgodę ponownie (podpis ad hoc).
set -e
cd "$(dirname "$0")"
APP=build/PanelKalendarz.app
mkdir -p "$APP/Contents/MacOS"
swiftc -O kalendarz.swift -o "$APP/Contents/MacOS/kalendarz"
cp kalendarz-Info.plist "$APP/Contents/Info.plist"
codesign --force --sign - "$APP"
echo "Gotowe: $APP"
