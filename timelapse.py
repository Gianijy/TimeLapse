import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
import cv2
import numpy as np
import mss

class TimelapseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mac Timelapse Recorder")
        self.root.geometry("350x250") 
        
        self.is_recording = False
        self.record_thread = None
        self.current_filename = ""
        
        with mss.mss() as sct:
            self.monitors = sct.monitors[1:] 
            
        self.build_ui()

    def build_ui(self):
        tk.Label(self.root, text="Select Screen to Record:", font=("Helvetica", 14)).pack(pady=(20, 5))
        
        self.screen_var = tk.StringVar()
        monitor_options = [f"Screen {i+1} ({m['width']}x{m['height']})" for i, m in enumerate(self.monitors)]
        
        if monitor_options:
            self.screen_var.set(monitor_options[0])
            
        self.dropdown = ttk.Combobox(self.root, textvariable=self.screen_var, values=monitor_options, state="readonly", width=25)
        self.dropdown.pack(pady=5)
        
        self.record_btn = tk.Button(self.root, text="Start Recording", command=self.toggle_recording, width=15, height=2, font=("Helvetica", 12, "bold"))
        self.record_btn.pack(pady=20)
        
        self.status_label = tk.Label(self.root, text="Ready", fg="gray")
        self.status_label.pack()

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.is_recording = True
        
        # Generate a unique filename using the current date and time
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_filename = f"timelapse_{timestamp}.mp4"
        
        self.record_btn.config(text="Stop Recording", fg="red")
        self.status_label.config(text="Recording in progress...", fg="red")
        self.dropdown.config(state="disabled") 
        
        self.record_thread = threading.Thread(target=self.video_capture_loop)
        self.record_thread.start()

    def stop_recording(self):
        self.is_recording = False
        
        self.record_btn.config(text="Start Recording", fg="black")
        self.status_label.config(text="Processing and saving video...", fg="orange")
        
        self.root.after(1500, lambda: self.status_label.config(text=f"Done! Saved to {self.current_filename}", fg="green"))
        self.dropdown.config(state="readonly")

    def video_capture_loop(self):
        selected_idx = self.dropdown.current()
        monitor = self.monitors[selected_idx]
        
        # --- NEW SPEED SETTINGS ---
        playback_fps = 15           # Standard, slightly slower playback
        capture_interval = 0.5      # Captures 2 times per second
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.current_filename, fourcc, playback_fps, (monitor["width"], monitor["height"]))
        
        with mss.mss() as sct:
            while self.is_recording:
                start_time = time.time()
                
                img = sct.grab(monitor)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                out.write(frame)
                
                elapsed = time.time() - start_time
                time.sleep(max(0, capture_interval - elapsed))
                
        out.release()

if __name__ == "__main__":
    root = tk.Tk()
    root.attributes('-topmost', True) 
    app = TimelapseApp(root)
    root.mainloop()