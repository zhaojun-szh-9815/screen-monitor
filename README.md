## Introduction
An application to detect screen changes in a specific area and check network health by ping Google.

Using Tkinter to build GUI

## Usage
1. Create icon.py by executing ico2base64.py
2. Execute screen_monitor_gui.py

## Packaging
pyinstaller -F -w -i avatars.ico --add-data .\\avatars.ico;. screen_monitor_gui.py