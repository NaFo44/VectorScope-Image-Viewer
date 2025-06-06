#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Created by Spectra for theory (and ChatGPT for practice xd)
# Modified to handle a “video” frame-by-frame: each frame is converted to audio (≈0.125 s) and WAVs are concatenated.

"""
Usage (video):
1) Run: python vectorscope.py
2) Click “New Frame” to create a blank 16×16 frame. Use “Prev Frame” and “Next Frame” to navigate and edit each frame.
3) For each frame, click or drag to toggle cells on (white) or off (black).
4) Click “Export Video WAV” to generate a .wav file: each frame lasts ≈0.125 s and frames are joined sequentially.
   If a frame is empty, it produces 0.125 s of silence.
5) Import the WAV into FL Studio, add WaveCandy → VectorScope, set “Update” to max, and play: images appear 1/8 s per frame.

If you only need a single static sound (30 s) for one matrix, keep the original generate_wav_from_matrix function, but here we focus on video export.
"""

import numpy as np
import soundfile as sf
import tkinter as tk
from tkinter import messagebox, filedialog

# ─────────── SETTINGS ───────────

MAT_SIZE = 16                   # Matrix dimensions (16×16)
CELL_SIZE = 30                  # Pixel size of each cell in the UI
PADDING = 2                     # Space between cells (pixels)

N_SAMPLES_PER_PIXEL = 40        # Samples per active pixel in the base block
SIGMA = 0.01                    # Standard deviation for Gaussian noise (stereo amplitude)
SAMPLE_RATE = 44100             # Sampling rate for the WAV
FRAME_DURATION = 0.125          # Duration of each frame in seconds (~1/8 s)

DEFAULT_OUTPUT_WAV = "video_vectorscope_16x16.wav"


# ─────────── CONVERSION FUNCTIONS ───────────

def matrix_to_points(mat):
    """
    Convert a MAT_SIZE×MAT_SIZE binary matrix into normalized points in [-1, +1]².
    - row=0 → y=+1 (top), row=MAT_SIZE-1 → y=-1 (bottom)
    - col=0 → x=-1 (left), col=MAT_SIZE-1 → x=+1 (right)
    Returns a list of (x, y) for each cell == 1.
    """
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
    """
    For a Vectorscope:
      x = R_amp - L_amp
      y = R_amp + L_amp
    → R_amp = (x + y) / 2
      L_amp = (y - x) / 2
    Returns (L_amp, R_amp).
    """
    R_amp = (x + y) / 2.0
    L_amp = (y - x) / 2.0
    return L_amp, R_amp

def create_base_block(matrix):
    """
    Given a 16×16 binary matrix, create a base stereo block:
    - Convert each active pixel to (L_amp, R_amp).
    - For each, generate N_SAMPLES_PER_PIXEL samples of Gaussian noise
      centered on (L_amp, R_amp), clipped to [-1, +1].
    - Stack into a (total_samples_base, 2) array.
    Returns (stereo_base, total_samples_base). If matrix is empty, returns (None, 0).
    """
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

    stereo_base = np.vstack((data_L, data_R)).T  # shape=(total_samples_base, 2)
    return stereo_base, total_samples_base


def generate_video_wav_from_frames(frames, output_wav):
    """
    Create a stereo WAV from a list of 16×16 matrices (frames):
    - For each frame, generate its base block. If empty, create silence.
    - Repeat or trim the block to exactly FRAME_DURATION seconds:
      total_samples_frame = int(FRAME_DURATION * SAMPLE_RATE)
    - Concatenate segments for all frames.
    - Write the final WAV (PCM_16).
    """
    if len(frames) == 0:
        messagebox.showwarning("Warning", "No frames to export!")
        return

    total_samples_frame = int(FRAME_DURATION * SAMPLE_RATE)
    segments = []

    for idx_frame, mat in enumerate(frames):
        stereo_base, base_samples = create_base_block(mat)
        if base_samples == 0:
            # Empty frame → silence
            silence = np.zeros((total_samples_frame, 2), dtype=np.float32)
            segments.append(silence)
            continue

        reps = int(np.ceil(total_samples_frame / base_samples))
        repeated = np.tile(stereo_base, (reps, 1))
        frame_seg = repeated[:total_samples_frame, :]
        segments.append(frame_seg.astype(np.float32))

    stereo_final = np.vstack(segments)  # shape=(num_frames * total_samples_frame, 2)
    total_duration = stereo_final.shape[0] / SAMPLE_RATE
    print(f"[INFO] Video generation: {len(frames)} frames × {FRAME_DURATION:.3f} s → total {total_duration:.3f} s "
          f"({stereo_final.shape[0]} samples)")

    sf.write(output_wav, stereo_final, samplerate=SAMPLE_RATE, subtype="PCM_16")
    messagebox.showinfo("Success", f"Video WAV generated:\n{output_wav}")


# ─────────── GUI (Tkinter) ───────────

class MatrixGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("16×16 Video Vectorscope")
        self.root.resizable(False, False)

        # List of frames (each is a 16×16 matrix)
        self.frames = []
        # Start with one empty frame
        self.frames.append([[0] * MAT_SIZE for _ in range(MAT_SIZE)])
        self.current_frame = 0

        # Value to draw during drag (0 or 1)
        self.draw_value = None

        # Canvas for drawing the grid
        canvas_size = MAT_SIZE * CELL_SIZE + (MAT_SIZE + 1) * PADDING
        self.canvas = tk.Canvas(
            self.root,
            width=canvas_size,
            height=canvas_size,
            bg="lightgray"
        )
        self.canvas.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        # Label showing “Frame X/Y”
        self.label_frame = tk.Label(self.root, text=self._get_frame_label(), font=("Arial", 12))
        self.label_frame.grid(row=1, column=0, columnspan=4)

        # Prev / New / Next frame buttons
        btn_prev = tk.Button(self.root, text="Prev Frame", command=self._prev_frame, width=12)
        btn_prev.grid(row=2, column=0, pady=5)

        btn_new = tk.Button(self.root, text="New Frame", command=self._new_frame, width=12)
        btn_new.grid(row=2, column=1, padx=5)

        btn_next = tk.Button(self.root, text="Next Frame", command=self._next_frame, width=12)
        btn_next.grid(row=2, column=2, pady=5)

        # Export video button
        btn_export = tk.Button(
            self.root,
            text="Export Video WAV",
            command=self._on_export_click,
            width=20,
            bg="#2196f3",
            fg="white",
            font=("Arial", 12, "bold")
        )
        btn_export.grid(row=2, column=3, padx=10)

        # Draw the initial grid
        self._draw_grid()

        # Bind click and drag for drawing
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)

    def _get_frame_label(self):
        """Return “Frame X / Y”."""
        return f"Frame {self.current_frame + 1} / {len(self.frames)}"

    def _draw_grid(self):
        """Draw the 16×16 grid: white for 1, black for 0."""
        self.canvas.delete("all")
        mat = self.frames[self.current_frame]
        for row in range(MAT_SIZE):
            for col in range(MAT_SIZE):
                x0 = PADDING + col * (CELL_SIZE + PADDING)
                y0 = PADDING + row * (CELL_SIZE + PADDING)
                x1 = x0 + CELL_SIZE
                y1 = y0 + CELL_SIZE
                color = "white" if mat[row][col] == 1 else "black"
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="gray")

    def _on_canvas_click(self, event):
        """
        On click, determine the cell, toggle its state (0↔1),
        and store draw_value so dragging uses the same.
        """
        x, y = event.x, event.y
        col = (x - PADDING) // (CELL_SIZE + PADDING)
        row = (y - PADDING) // (CELL_SIZE + PADDING)

        if 0 <= row < MAT_SIZE and 0 <= col < MAT_SIZE:
            mat = self.frames[self.current_frame]
            mat[row][col] ^= 1
            self.draw_value = mat[row][col]
            self._draw_grid()

    def _on_canvas_drag(self, event):
        """
        On drag, apply draw_value to each hovered cell.
        """
        x, y = event.x, event.y
        col = (x - PADDING) // (CELL_SIZE + PADDING)
        row = (y - PADDING) // (CELL_SIZE + PADDING)

        if (0 <= row < MAT_SIZE and 0 <= col < MAT_SIZE and
                self.draw_value is not None):
            mat = self.frames[self.current_frame]
            if mat[row][col] != self.draw_value:
                mat[row][col] = self.draw_value
                self._draw_grid()

    def _prev_frame(self):
        """
        Switch to the previous frame (if any). Matrices are updated live in self.frames.
        """
        if self.current_frame > 0:
            self.current_frame -= 1
            self.label_frame.config(text=self._get_frame_label())
            self._draw_grid()
        else:
            messagebox.showinfo("Info", "Already at the first frame.")

    def _next_frame(self):
        """
        Switch to the next frame if it exists, otherwise create a new empty frame.
        """
        if self.current_frame < len(self.frames) - 1:
            self.current_frame += 1
            self.label_frame.config(text=self._get_frame_label())
            self._draw_grid()
        else:
            self._new_frame()

    def _new_frame(self):
        """Create a new empty 16×16 frame and switch to it."""
        new_mat = [[0] * MAT_SIZE for _ in range(MAT_SIZE)]
        self.frames.append(new_mat)
        self.current_frame = len(self.frames) - 1
        self.label_frame.config(text=self._get_frame_label())
        self._draw_grid()

    def _on_export_click(self):
        """
        Open a dialog to choose the output filename and
        call generate_video_wav_from_frames.
        """
        default_path = DEFAULT_OUTPUT_WAV
        out_file = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav")],
            initialfile=default_path,
            title="Save Video WAV as"
        )
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
