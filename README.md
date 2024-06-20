## Introduction
An application to detect screen changes in a specific area and check network health by ping Google.

Using Tkinter to build GUI

## Functions
1. Check network health by Ping Google every 30 mins. If connect failed, it will retry after 1 min. If it failed after 3 attempts, it will create an alert.
2. Detect screen changes in a specific area. The application has "Config" button to specify an area to monitor. The application will create a screenshot every 5 seconds, and if the screenshot is different from the previous one, it will create an alert. The user can press "Yes" button to save screenshots to analyze and debug later.
3. The alert will be winsound.Beep with 2000ms duration and 3s interval.
4. Informations about network health and screen changes will be displayed on logging area in the bottom of the window. The content can be stored by "Export" button.
5. When the application launched, it will check new version, and will display result in logging area.

## Usage
1. Install libraries in requirements.txt
2. create avatars.ico and version-info.json which contains: version, v-url, d-url. the value of v-url should be a download link for a json file.
3. Execute screen_monitor.py

## Packaging
pyinstaller -F -w -i avatars.ico --add-data .\\avatars.ico;. --add-data .\\version-info.json;. screen_monitor.py