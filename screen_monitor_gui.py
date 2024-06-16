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
import base64
import os
from icon import img

class ScreenMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Monitor")
        tmp = open('tmp.ico', 'wb+')
        tmp.write(base64.b64decode(img))
        tmp.close()
        self.root.iconbitmap("tmp.ico")
        os.remove("tmp.ico")

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
        self.screenshot_previous = None
        self.screenshot_current = None
        self.alert_window = None
        self.alert_open = False

        self.network_health = True
        self.network_timeout = 10
        # 1000 ms * 60 * 30
        self.check_network_interval = 1800000
        # self.check_network_interval = 6000

        self.root.geometry('1200x800')
        # 1000 ms * 60 = 1 min
        self.screenshot_interval = 1000

        # in second
        self.beep_interval = 3
        self.beep_freq = 440
        self.beep_duration = 2000

        ttk.Button(root, text="Config", command=self.open_fullscreen).grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.start_stop_button = ttk.Button(root, text="Start", command=self.toggle_loop)
        self.start_stop_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Allow columns to expand
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        
        # Allow rows to expand
        root.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(2, weight=8)
        
        self.ping_server_with_retry()

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
        self.top.destroy()  # Close the overlay after drawing the rectangle

    def toggle_loop(self):
        if not self.running:
            self.running = True
            self.start_stop_button.config(text="Stop")
            self.capture_loop()
        else:
            self.running = False
            self.start_stop_button.config(text="Start")
            if self.alert_open and self.alert_window:
                self.alert_open = False
                self.display_image(self.screenshot_previous, False)
                self.alert_window.destroy()
                self.alert_window = None

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

        self.alert_open = True
        self.alert_window = tk.Toplevel(root)
        self.alert_window.title("Alert")
        self.alert_window.geometry("300x200")
        # Make the window stay on top
        self.alert_window.wm_attributes("-topmost", 1)
        if change_detected_alert:
            alert_label = tk.Label(self.alert_window, text="Detected Something Changed.\nClose the window to stop.")
        else:
            alert_label = tk.Label(self.alert_window, text="Network unhealthy.\nClose the window to stop.")
        alert_label.pack(expand=True)
        self.alert_window.protocol("WM_DELETE_WINDOW", on_close)

        threading.Thread(target=beep, daemon=True).start()

    def capture_loop(self):
        if self.running and self.rect_start and self.rect_end:
            x1, y1 = self.rect_start
            x2, y2 = self.rect_end
            screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
            if self.screenshot_previous:
                if not np.array_equal(np.array(self.screenshot_previous), np.array(screenshot)):
                    print(str(datetime.now()) + ": change detected...")
                    self.screenshot_current = screenshot
                    self.display_image(screenshot, True)
                    self.create_alert(True)
                    
                    # 更新前一次的截图
                    self.screenshot_previous = screenshot
                else:
                    if not self.screenshot_current:
                        self.screenshot_current = screenshot
                        self.display_image(screenshot, True)
            else:
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

    def ping_server_with_retry(self, host='www.google.com', retries=3, delay=60):
        attempts = 0
        print(str(datetime.now()) + ": checking network...")
        while attempts < retries:
            try:
                response = ping(host, timeout=self.network_timeout)
                if not response:
                    print(f"No response from {host}. Retrying...")
                else:
                    print(f"Response time from {host}: {response} seconds")
                    self.network_health = True
                    self.root.after(self.check_network_interval, self.ping_server_with_retry)
                    return
            except errors as e:
                print(f"Failed to ping {host}: {str(e)}. Retrying...")

            attempts += 1
            time.sleep(delay)

        print(f"Failed to ping {host} after {retries} retries.")
        self.create_alert(False)
        self.root.after(self.check_network_interval, self.ping_server_with_retry)

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenMonitor(root)
    root.mainloop()
