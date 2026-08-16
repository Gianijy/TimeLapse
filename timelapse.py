import tkinter as tk
from tkinter import ttk
import threading
import time
import cv2
import numpy as np
import mss

class TimelapseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mac Timelapse Recorder")
        # Set a clean, small window size
        self.root.geometry("350x250") 
        
        self.is_recording = False
        self.record_thread = None
        
        # 1. Fetch available monitors
        with mss.mss() as sct:
            # sct.monitors[0] is a composite of all screens. 
            # We skip it and only list individual physical screens.
            self.monitors = sct.monitors[1:] 
            
        self.build_ui()

    def build_ui(self):
        # Screen Selection Dropdown
        tk.Label(self.root, text="Select Screen to Record:", font=("Helvetica", 14)).pack(pady=(20, 5))
        
        self.screen_var = tk.StringVar()
        # Format the screen list to show "Screen 1 (1920x1080)"
        monitor_options = [f"Screen {i+1} ({m['width']}x{m['height']})" for i, m in enumerate(self.monitors)]
        
        if monitor_options:
            self.screen_var.set(monitor_options[0])
            
        self.dropdown = ttk.Combobox(self.root, textvariable=self.screen_var, values=monitor_options, state="readonly", width=25)
        self.dropdown.pack(pady=5)
        
        # Start/Stop Button
        self.record_btn = tk.Button(self.root, text="Start Recording", command=self.toggle_recording, width=15, height=2, font=("Helvetica", 12, "bold"))
        self.record_btn.pack(pady=20)
        
        # Status Text
        self.status_label = tk.Label(self.root, text="Ready", fg="gray")
        self.status_label.pack()

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.is_recording = True
        
        # Update UI state
        self.record_btn.config(text="Stop Recording", fg="red")
        self.status_label.config(text="Recording in progress...", fg="red")
        self.dropdown.config(state="disabled") # Prevent changing screens mid-record
        
        # Fire up the background thread
        self.record_thread = threading.Thread(target=self.video_capture_loop)
        self.record_thread.start()

    def stop_recording(self):
        self.is_recording = False
        
        # Reset UI state
        self.record_btn.config(text="Start Recording", fg="black")
        self.status_label.config(text="Processing and saving video...", fg="orange")
        
        # Wait a moment for the video file to cleanly close, then update status
        self.root.after(1500, lambda: self.status_label.config(text="Done! Saved to mac_timelapse.mp4", fg="green"))
        self.dropdown.config(state="readonly")

    def video_capture_loop(self):
        # Identify which screen the user selected
        selected_idx = self.dropdown.current()
        monitor = self.monitors[selected_idx]
        
        # Video settings
        playback_fps = 30
        capture_interval = 1.0 # 1 screenshot per second
        output_filename = "mac_timelapse.mp4"
        
        # Initialize OpenCV Video Writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_filename, fourcc, playback_fps, (monitor["width"], monitor["height"]))
        
        with mss.mss() as sct:
            # This loop runs constantly until you click the Stop button
            while self.is_recording:
                start_time = time.time()
                
                # Capture frame
                img = sct.grab(monitor)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                # Write frame to file
                out.write(frame)
                
                # Wait for the remainder of the 1-second interval
                elapsed = time.time() - start_time
                time.sleep(max(0, capture_interval - elapsed))
                
        # Safely wrap up the file when the loop breaks
        out.release()

if __name__ == "__main__":
    root = tk.Tk()
    
    # Optional Mac tweak: makes the window float above others
    root.attributes('-topmost', True) 
    
    app = TimelapseApp(root)
    root.mainloop()