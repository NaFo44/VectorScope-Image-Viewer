#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Created by Spectra for theory (and ChatGPT for practice xd)
# Modified to handle a “video” frame-by-frame and add a clear-frame feature.

import numpy as np
import soundfile as sf
import tkinter as tk
from tkinter import messagebox, filedialog

# ─────────── SETTINGS ───────────

MAT_SIZE = 16                   # Matrix dimensions (16×16)
CELL_SIZE = 20                  # Pixel size of each cell in the UI (reduced for a lighter interface)
PADDING = 1                     # Space between cells (pixels, reduced)

N_SAMPLES_PER_PIXEL = 40        # Samples per active pixel in the base block
SIGMA = 0.01                    # Standard deviation for Gaussian noise (stereo amplitude)
SAMPLE_RATE = 44100             # Sampling rate for the WAV
FRAME_DURATION = 0.125          # Duration of each frame in seconds (~1/8 s)

DEFAULT_OUTPUT_WAV = "video_vectorscope_16x16.wav"


# ─────────── CONVERSION FUNCTIONS ───────────

def matrix_to_points(mat):
    H = len(mat)
    W = len(mat[0]) if H > 0 else 0
    pts = []
    for row in range(H):
        for col in range(W):
            if mat[row][col] == 1:
                x = (2 * col) / (W - 1) - 1.0
                y = -((2 * row) / (H - 1) - 1.0)
                pts.append((x, y))
    return pts


def xy_to_stereo(x, y):
    R_amp = (x + y) / 2.0
    L_amp = (y - x) / 2.0
    return L_amp, R_amp


def create_base_block(matrix):
    points = matrix_to_points(matrix)
    count = len(points)
    if count == 0:
        return None, 0

    total_samples_base = count * N_SAMPLES_PER_PIXEL
    stereo_amps = [xy_to_stereo(x, y) for (x, y) in points]

    data_L = np.zeros((total_samples_base,), dtype=np.float32)
    data_R = np.zeros((total_samples_base,), dtype=np.float32)

    idx = 0
    for (L_amp, R_amp) in stereo_amps:
        noise_L = np.random.normal(loc=L_amp, scale=SIGMA, size=(N_SAMPLES_PER_PIXEL,))
        noise_R = np.random.normal(loc=R_amp, scale=SIGMA, size=(N_SAMPLES_PER_PIXEL,))
        noise_L = np.clip(noise_L, -1.0, 1.0)
        noise_R = np.clip(noise_R, -1.0, 1.0)
        data_L[idx:idx + N_SAMPLES_PER_PIXEL] = noise_L
        data_R[idx:idx + N_SAMPLES_PER_PIXEL] = noise_R
        idx += N_SAMPLES_PER_PIXEL

    stereo_base = np.vstack((data_L, data_R)).T
    return stereo_base, total_samples_base


def generate_video_wav_from_frames(frames, output_wav):
    if len(frames) == 0:
        messagebox.showwarning("Warning", "No frames to export!")
        return

    total_samples_frame = int(FRAME_DURATION * SAMPLE_RATE)
    segments = []

    for mat in frames:
        stereo_base, base_samples = create_base_block(mat)
        if base_samples == 0:
            segments.append(np.zeros((total_samples_frame, 2), dtype=np.float32))
            continue

        reps = int(np.ceil(total_samples_frame / base_samples))
        repeated = np.tile(stereo_base, (reps, 1))
        frame_seg = repeated[:total_samples_frame, :]
        segments.append(frame_seg.astype(np.float32))

    stereo_final = np.vstack(segments)
    sf.write(output_wav, stereo_final, samplerate=SAMPLE_RATE, subtype="PCM_16")
    messagebox.showinfo("Success", f"Video WAV generated:\n{output_wav}")


# ─────────── GUI (Tkinter) ───────────

class MatrixGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("16×16 Video Vectorscope")
        self.root.resizable(False, False)

        # Frames storage
        self.frames = [[ [0]*MAT_SIZE for _ in range(MAT_SIZE) ]]
        self.current_frame = 0
        self.draw_value = None

        # Canvas setup
        canvas_size = MAT_SIZE * CELL_SIZE + (MAT_SIZE + 1) * PADDING
        self.canvas = tk.Canvas(self.root, width=canvas_size, height=canvas_size, bg="lightgray")
        self.canvas.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        # Frame label
        self.label_frame = tk.Label(self.root, text=self._get_frame_label(), font=("Arial", 10))
        self.label_frame.grid(row=1, column=0, columnspan=4)

        # Navigation buttons
        btn_prev = tk.Button(self.root, text="Prev Frame", command=self._prev_frame, width=10)
        btn_prev.grid(row=2, column=0, pady=5)

        btn_new = tk.Button(self.root, text="New Frame", command=self._new_frame, width=10)
        btn_new.grid(row=2, column=1, padx=5)

        btn_next = tk.Button(self.root, text="Next Frame", command=self._next_frame, width=10)
        btn_next.grid(row=2, column=2, pady=5)

        # Clear current frame button
        btn_clear = tk.Button(self.root, text="Clear Current Frame", command=self._clear_current_frame, width=14, bg="#f44336", fg="white")
        btn_clear.grid(row=2, column=3, padx=5)

        # Export button
        btn_export = tk.Button(self.root, text="Export Video WAV", command=self._on_export_click, width=18, bg="#2196f3", fg="white", font=("Arial", 10, "bold"))
        btn_export.grid(row=3, column=0, columnspan=4, pady=10)

        # Initial drawing and bindings
        self._draw_grid()
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)

    def _get_frame_label(self):
        return f"Frame {self.current_frame+1} / {len(self.frames)}"

    def _draw_grid(self):
        self.canvas.delete("all")
        mat = self.frames[self.current_frame]
        for r in range(MAT_SIZE):
            for c in range(MAT_SIZE):
                x0 = PADDING + c*(CELL_SIZE+PADDING)
                y0 = PADDING + r*(CELL_SIZE+PADDING)
                x1, y1 = x0+CELL_SIZE, y0+CELL_SIZE
                color = "white" if mat[r][c] else "black"
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="gray")

    def _on_canvas_click(self, event):
        col = (event.x - PADDING)//(CELL_SIZE+PADDING)
        row = (event.y - PADDING)//(CELL_SIZE+PADDING)
        if 0 <= row < MAT_SIZE and 0 <= col < MAT_SIZE:
            mat = self.frames[self.current_frame]
            mat[row][col] ^= 1
            self.draw_value = mat[row][col]
            self._draw_grid()

    def _on_canvas_drag(self, event):
        col = (event.x - PADDING)//(CELL_SIZE+PADDING)
        row = (event.y - PADDING)//(CELL_SIZE+PADDING)
        if 0 <= row < MAT_SIZE and 0 <= col < MAT_SIZE and self.draw_value is not None:
            mat = self.frames[self.current_frame]
            if mat[row][col] != self.draw_value:
                mat[row][col] = self.draw_value
                self._draw_grid()

    def _prev_frame(self):
        if self.current_frame > 0:
            self.current_frame -= 1
            self.label_frame.config(text=self._get_frame_label())
            self._draw_grid()
        else:
            messagebox.showinfo("Info", "Already at the first frame.")

    def _next_frame(self):
        if self.current_frame < len(self.frames)-1:
            self.current_frame += 1
        else:
            self._new_frame()
        self.label_frame.config(text=self._get_frame_label())
        self._draw_grid()

    def _new_frame(self):
        self.frames.append([[0]*MAT_SIZE for _ in range(MAT_SIZE)])
        self.current_frame = len(self.frames)-1
        self.label_frame.config(text=self._get_frame_label())
        self._draw_grid()

    def _clear_current_frame(self):
        """Clear all pixels in the current frame and redraw."""
        self.frames[self.current_frame] = [[0]*MAT_SIZE for _ in range(MAT_SIZE)]
        self._draw_grid()

    def _on_export_click(self):
        default_path = DEFAULT_OUTPUT_WAV
        out_file = filedialog.asksaveasfilename(defaultextension=".wav",
                                                filetypes=[("WAV files", "*.wav")],
                                                initialfile=default_path,
                                                title="Save Video WAV as")
        if out_file:
            try:
                generate_video_wav_from_frames(self.frames, out_file)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate video WAV:\n{e}")


def main():
    root = tk.Tk()
    app = MatrixGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
