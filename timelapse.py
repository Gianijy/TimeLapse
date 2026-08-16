import tkinter as tk
from tkinter import ttk
import threading
import time
from datetime import datetime
import cv2
import numpy as np
import mss
import os
import shutil

class TimelapseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mac Timelapse Recorder")
        self.root.geometry("350x250") 
        
        self.is_recording = False
        self.record_thread = None
        self.current_filename = ""
        self.temp_dir = "temp_timelapse_frames"
        
        with mss.mss() as sct:
            self.monitors = sct.monitors[1:] 
            
        self.build_ui()

    def build_ui(self):
        tk.Label(self.root, text="Select Screen:", font=("Helvetica", 14)).pack(pady=(20, 5))
        
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
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_filename = f"timelapse_{timestamp}.mp4"
        
        self.record_btn.config(text="Stop Recording", fg="red")
        self.status_label.config(text="Recording...", fg="red")
        self.dropdown.config(state="disabled") 
        
        self.record_thread = threading.Thread(target=self.iphone_capture_loop)
        self.record_thread.start()

    def stop_recording(self):
        self.is_recording = False
        self.record_btn.config(state="disabled")
        self.status_label.config(text="Stitching final frames...", fg="orange")

    def iphone_capture_loop(self):
        selected_idx = self.dropdown.current()
        monitor = self.monitors[selected_idx]
        
        # Fresh temporary directory for images
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)
        
        # --- SMOOTHNESS MULTIPLIER ---
        # 1 = Exact iPhone logic (30 FPS, choppy screen). 
        # 2 = Double frame data (60 FPS, incredibly smooth, exact same video length).
        smooth = 2 
        playback_fps = 30 * smooth
        
        # Apple's Tier System adjusted for smoothness
        # Tier 0 (< 10 mins): Captures 2 frames per second (1 frame every 0.5 seconds).
        # Tier 1 (10-20 mins): Captures 1 frame per second.
        # Tier 2 (20-40 mins): Captures 1 frame every 2 seconds.
        # Tier 3 (40-80 mins): Captures 1 frame every 4 seconds.
        # Tier 4 (> 80 mins): Captures 1 frame every 8 seconds.
        base_intervals = [0.5, 1.0, 2.0, 4.0, 8.0]
        intervals = [i / smooth for i in base_intervals]
        
        tier = 0
        frame_counter = 0
        start_time = time.time()
        
        with mss.mss() as sct:
            while self.is_recording:
                loop_start = time.time()
                elapsed_seconds = loop_start - start_time
                
                # Dynamic Interval Engine: Checks if we crossed an iPhone time boundary
                if elapsed_seconds >= 80 * 60 and tier == 3:
                    self.drop_half_frames()
                    tier = 4
                elif elapsed_seconds >= 40 * 60 and tier == 2:
                    self.drop_half_frames()
                    tier = 3
                elif elapsed_seconds >= 20 * 60 and tier == 1:
                    self.drop_half_frames()
                    tier = 2
                elif elapsed_seconds >= 10 * 60 and tier == 0:
                    self.drop_half_frames()
                    tier = 1
                    
                current_interval = intervals[tier]
                
                # Capture and format
                img = sct.grab(monitor)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                # Save to disk
                filepath = os.path.join(self.temp_dir, f"frame_{frame_counter:08d}.jpg")
                cv2.imwrite(filepath, frame)
                frame_counter += 1
                
                # Sleep accurately
                loop_duration = time.time() - loop_start
                time.sleep(max(0, current_interval - loop_duration))
                
        self.compile_final_video(monitor["width"], monitor["height"], playback_fps)

    def drop_half_frames(self):
        """This mimics the iOS logic: delete 50% of the past frames to maintain a small file size."""
        files = sorted(os.listdir(self.temp_dir))
        for index, filename in enumerate(files):
            # Delete every odd-numbered frame
            if index % 2 != 0:
                os.remove(os.path.join(self.temp_dir, filename))

    def compile_final_video(self, width, height, fps):
        """Stitch the surviving frames into the final video."""
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.current_filename, fourcc, fps, (width, height))
        
        files = sorted(os.listdir(self.temp_dir))
        for filename in files:
            filepath = os.path.join(self.temp_dir, filename)
            frame = cv2.imread(filepath)
            if frame is not None:
                out.write(frame)
                
        out.release()
        
        # Clean up temporary hard drive data
        shutil.rmtree(self.temp_dir)
        
        # Return to UI safely
        self.root.after(0, self.finish_processing)

    def finish_processing(self):
        self.status_label.config(text=f"Done! Saved to {self.current_filename}", fg="green")
        self.record_btn.config(text="Start Recording", fg="black", state="normal")
        self.dropdown.config(state="readonly")

if __name__ == "__main__":
    root = tk.Tk()
    root.attributes('-topmost', True) 
    app = TimelapseApp(root)
    root.mainloop()