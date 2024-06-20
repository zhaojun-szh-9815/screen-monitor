import tkinter as tk
from tkinter import ttk
import pyautogui
from PIL import Image, ImageTk
import numpy as np
import winsound
import time
import threading
from datetime import datetime
from ping3 import ping, errors
import os
import sys
import json
import requests
import pathlib
import traceback
import re
import webbrowser

class ScreenMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Monitor")
        self.root.geometry('1200x800')
        self.root.iconbitmap(self.get_path("avatars.ico"))

        self.screen_width = root.winfo_screenwidth()
        self.screen_height = root.winfo_screenheight()

        self.timeFormat = "%Y%m%d%H%M%S"
        self.screenshot_path = "./screenshots"
        self.log_path = "./logs"
        self.logTimeFormat = "%Y%m%d"
        self.version_info_path = "./version-info.json"
        self.version_key = "version"
        self.version_url_key = "v-url"
        self.new_file_url_key = "d-url"

        self.top = None
        self.canvas = None
        self.rect_start = None
        self.rect_end = None
        self.rectangle = None
        self.previous_text = tk.Label(root, text="Previous").grid(row=1, column=0, padx=10, pady=1, sticky="ew")
        self.image_label_previous = tk.Label(root)
        self.image_label_previous.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.current_text = tk.Label(root, text="Current").grid(row=1, column=1, padx=10, pady=1, sticky="ew")
        self.image_label_current = tk.Label(root)
        self.image_label_current.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        self.resize_height = None
        self.resize_width = None
        self.running = False
        self.previous_time = None
        self.screenshot_previous = None
        self.current_time = None
        self.screenshot_current = None
        self.alert_window = None
        self.alert_open = False
        self.log_expand = False

        self.network_health = True
        # in second
        self.network_timeout = 10
        # 1000 ms * 60 * 30
        self.check_network_interval = 1800000
        # self.check_network_interval = 6000

        # 1000 ms
        self.screenshot_interval = 1000

        # in second
        self.beep_interval = 3
        self.beep_freq = 440
        self.beep_duration = 2000

        ttk.Button(root, text="Config", command=self.open_fullscreen).grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.start_stop_button = ttk.Button(root, text="Start", command=self.toggle_loop)
        self.start_stop_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.toggle_btn = ttk.Button(root, text="Expand", command=self.toggle_log)
        self.toggle_btn.grid(row=3, column=0, padx=10, pady=10, sticky='ew')
        self.export_btn = ttk.Button(root, text="Export", command=self.export)
        self.export_btn.grid(row=3, column=1, padx=10, pady=10, sticky='ew')
        
        # Create a Text widget and a Scrollbar for the log
        self.text_frame = tk.Frame(root)
        self.log = tk.Text(self.text_frame, height=10, width=50)
        self.scroll = tk.Scrollbar(self.text_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=self.scroll.set)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Initially hide the log area. Span across two columns
        self.text_frame.grid(row=4, column=0, columnspan=2, sticky='nsew', padx=10, pady=10, ipadx=20, ipady=20)
        self.text_frame.grid_remove()

        # Allow columns to expand
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        
        # Allow rows to expand
        if self.log_expand:
            root.rowconfigure(0, weight=1)
            root.rowconfigure(1, weight=1)
            root.rowconfigure(2, weight=7)
            root.rowconfigure(3, weight=1)
            root.rowconfigure(4, weight=4)
        else:
            root.rowconfigure(0, weight=1)
            root.rowconfigure(1, weight=1)
            root.rowconfigure(2, weight=7)
            root.rowconfigure(3, weight=1)

        self.check_version()
        self.ping_server_with_retry()

    def get_path(self, relative_path):
        try:
            base_path = sys._MEIPASS # path after packaging by pyinstaller
        except AttributeError:
            base_path = os.path.abspath(".") # current path
    
        return os.path.normpath(os.path.join(base_path, relative_path))
    
    def check_version(self):
        f = open(self.get_path(self.version_info_path), 'r')
        data = json.load(f)
        f.close()
        version = data[self.version_key]
        v_url = data[self.version_url_key]
        d_url = data[self.new_file_url_key]
        try:
            response = requests.get(v_url)
            data = response.json()
            if version < data[self.version_key]:
                self.add_log_entry("New version found on: " + d_url)
                self.tag_urls()
                self.log.tag_bind("url", "<Button-1>", self.open_url)
            else:
                self.add_log_entry("It is the latest version ...")
        except Exception as e:
            self.add_log_entry(str(e))
            self.add_log_entry(traceback.format_exc())

    def open_fullscreen(self):
        self.top = tk.Toplevel(self.root)
        self.top.attributes('-fullscreen', True, '-alpha', 0.3)  # Makes the window fullscreen and semi-transparent
        self.canvas = tk.Canvas(self.top, cursor="cross", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.rect_start = (event.x, event.y)
        self.rectangle = self.canvas.create_rectangle(0, 0, 0, 0, outline='red')

    def on_motion(self, event):
        self.canvas.coords(self.rectangle, self.rect_start[0], self.rect_start[1], event.x, event.y)

    def on_release(self, event):
        self.rect_end = (event.x, event.y)
        # Close the overlay after drawing the rectangle
        self.top.destroy()

    def toggle_loop(self):
        if not self.running:
            self.running = True
            self.screenshot_previous = None
            self.screenshot_current = None
            self.start_stop_button.config(text="Stop")
            self.capture_loop()
        else:
            self.running = False
            sec = int(self.screenshot_interval / 1000)
            self.add_log_entry("Stopping in " + str(sec) + " sec ...")
            time.sleep(sec)
            self.start_stop_button.config(text="Start")
            if self.alert_open and self.alert_window:
                self.alert_open = False
                self.display_image(self.screenshot_previous, False)
                self.alert_window.destroy()
                self.alert_window = None
    
    def toggle_log(self):
        if self.text_frame.winfo_ismapped():
            # Hide the text frame and change button text to "Expand"
            self.text_frame.grid_remove()
            self.toggle_btn.config(text="Expand")
            self.log_expand = False
        else:
            # Show the text frame and change button text to "Close"
            self.text_frame.grid()
            self.toggle_btn.config(text="Close")
            self.log_expand = True

    def add_log_entry(self, text):
        self.log.config(state="normal")
        # Insert the text at the end of the Text widget
        self.log.insert(tk.END, text + "\n")
        self.log.config(state="disabled")
        # Automatically scroll to the end
        self.log.see(tk.END)

    def export(self):
        os.makedirs(self.log_path, exist_ok=True)
        now = datetime.now()
        log_filename = self.log_path + "/log_" + now.strftime(self.logTimeFormat) + ".txt"
        pathlib.Path(log_filename).touch(exist_ok=True)

        log_file = open(log_filename, "r")
        existing_lines = log_file.readlines()
        existing_lines = {line for line in existing_lines}
        log_file.close()

        new_content = [line + "\n" for line in self.log.get(1.0, tk.END).split("\n") if line not in existing_lines]

        log_file = open(log_filename, "a")
        if new_content:
            log_file.writelines(new_content[:-1])
        log_file.close()
    
    def save_screenshot(self):
        os.makedirs(self.screenshot_path, exist_ok=True)

        self.screenshot_previous.save(self.screenshot_path + "/sc_"+self.previous_time.strftime(self.timeFormat)+"_pre.png")
        self.screenshot_current.save(self.screenshot_path + "/sc_"+self.current_time.strftime(self.timeFormat)+"_cur.png")

    def create_alert(self, change_detected_alert: bool):
        if self.alert_open:
            return

        def beep():
            while self.alert_open:
                winsound.Beep(self.beep_freq, self.beep_duration)
                time.sleep(self.beep_interval)

        def on_close():
            self.alert_open = False
            if change_detected_alert:
                self.display_image(self.screenshot_previous, False)
            self.alert_window.destroy()
            self.alert_window = None

        def yes_action():
            self.save_screenshot()
            on_close()

        self.alert_open = True
        self.alert_window = tk.Toplevel(root)
        self.alert_window.title("Alert")
        self.alert_window.geometry("300x150+" + str(self.screen_width-300) + "+" + str(self.screen_height-200))
        # Make the window stay on top
        self.alert_window.wm_attributes("-topmost", 1)
        # Set the label text based on the alert type
        alert_text = "Detected Something Changed.""\nPress Yes to save screenshot.\nPress No or close window to stop." if change_detected_alert else "Network unhealthy.\nClose window to stop."
        alert_label = tk.Label(self.alert_window, text=alert_text)
        alert_label.pack(expand=True)

        if change_detected_alert:
            # Buttons
            yes_button = tk.Button(self.alert_window, text="Yes", command=yes_action)
            yes_button.pack(side=tk.LEFT, expand=True, padx=20, pady=20)

            no_button = tk.Button(self.alert_window, text="No", command=on_close)
            no_button.pack(side=tk.RIGHT, expand=True, padx=20, pady=20)

        self.alert_window.protocol("WM_DELETE_WINDOW", on_close)

        threading.Thread(target=beep, daemon=True).start()

    def capture_loop(self):
        if self.running and self.rect_start and self.rect_end:
            x1, y1 = self.rect_start
            x2, y2 = self.rect_end
            screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
            now = datetime.now()
            if self.screenshot_previous:
                if not np.array_equal(np.array(self.screenshot_previous), np.array(screenshot)):
                    # print(str(now) + ": change detected...")
                    self.add_log_entry(str(now) + ": change detected...")
                    # print("There is no changes from", str(self.previous_time),", it has been", round((now - self.previous_time).seconds/60, 2), "mins")
                    self.add_log_entry("There is no changes from " + str(self.previous_time) + " .It has been " + str(round((now - self.previous_time).seconds/60, 2)) + " mins")
                    self.current_time = now
                    self.screenshot_current = screenshot
                    self.display_image(screenshot, True)
                    self.create_alert(True)
                    
                    self.previous_time = now
                    self.screenshot_previous = screenshot
                else:
                    if not self.screenshot_current:
                        self.current_time = now
                        self.screenshot_current = screenshot
                        self.display_image(screenshot, True)
            else:
                self.previous_time = now
                self.screenshot_previous = screenshot
                self.display_image(screenshot, False)
            self.root.after(self.screenshot_interval, self.capture_loop)

    def display_image(self, image, current):
        if not self.resize_height or not self.resize_width:
            # Define the desired size
            desired_width = max(self.root.winfo_width()/2, 100)
            desired_height = max(self.root.winfo_height()/2 - 50, 50)

            # Calculate the scaling factor to maintain aspect ratio
            original_width, original_height = image.size
            width_ratio = desired_width / original_width
            height_ratio = desired_height / original_height
            scale_factor = min(width_ratio, height_ratio)  # Choose the smallest to ensure the image fits within the constraints

            # Calculate new dimensions
            self.resize_width = int(original_width * scale_factor)
            self.resize_height = int(original_height * scale_factor)

        if current:
            # Resize the image using Pillow
            image = self.screenshot_current.resize((self.resize_width, self.resize_height), Image.LANCZOS)

            # Convert to PhotoImage
            img = ImageTk.PhotoImage(image)

            # Destroy old label if exists
            if hasattr(self, 'image_label_current'):
                self.image_label_current.destroy()

            # Create a new label for the image
            self.image_label_current = tk.Label(self.root, image=img)
            self.image_label_current.image = img
            self.image_label_current.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        else:
            image = self.screenshot_previous.resize((self.resize_width, self.resize_height), Image.LANCZOS)
            img = ImageTk.PhotoImage(image)

            if hasattr(self, 'image_label_previous'):
                self.image_label_previous.destroy()

            self.image_label_previous = tk.Label(self.root, image=img)
            self.image_label_previous.image = img
            self.image_label_previous.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

    def ping_server_with_retry(self, host='www.google.com', retries=3, delay=60000, attempt=0):
        self.add_log_entry(str(datetime.now()) + ": checking network...")
        
        try:
            response = ping(host, timeout=self.network_timeout)
            if not response:
                # print(f"No response from {host}. Retrying...")
                self.add_log_entry("No response from " + host +". Retrying...")
            else:
                # print(f"Response time from {host}: {round(response, 2)} seconds")
                self.add_log_entry("Response time from " + host + ": " + str(round(response, 4)) + " seconds")
                self.network_health = True
                self.root.after(self.check_network_interval, self.ping_server_with_retry)
                return
        except errors as e:
            # print(f"Failed to ping {host}: {str(e)}. Retrying...")
            self.add_log_entry("Failed to ping " + host +": " + str(e) + ". Retrying...")

        if attempt == 2:
        # print(f"Failed to ping {host} after {retries} retries.")
            self.add_log_entry("Failed to ping " + host +" after " + str(retries) +" retries.")
            self.create_alert(False)
            self.root.after(self.check_network_interval, self.ping_server_with_retry)
        else:
            self.root.after(delay, lambda:self.ping_server_with_retry(attempt=attempt+1))

    def tag_urls(self):
        self.log.tag_remove("url", "1.0", tk.END)
        text_content = self.log.get("1.0", tk.END)
        for match in re.finditer(r'http[s]?://\S+', text_content):
            start, end = match.span()
            start_index = self.log.index(f"1.0 + {start} chars")
            end_index = self.log.index(f"1.0 + {end} chars")
            self.log.tag_add("url", start_index, end_index)
            self.log.tag_config("url", foreground="blue", underline=True)

    def open_url(self, event):
        # Get the index of the text where the click happened
        click_index = self.log.index(f"@{event.x},{event.y}")
        # Get all tags at the click index
        tags = self.log.tag_names(click_index)
        # If 'url' tag is among the tags, open the URL
        if 'url' in tags:
            # Get the start and end indices of the URL
            url_start = self.log.tag_prevrange('url', click_index + "+1c")[0]
            url_end = self.log.tag_prevrange('url', click_index + "+1c")[1]
            webbrowser.open(self.log.get(url_start, url_end))

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenMonitor(root)
    root.mainloop()
