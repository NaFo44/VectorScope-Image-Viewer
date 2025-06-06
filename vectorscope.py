#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Made by Spectra for theory (and chatgpt for practice xd)

"""
Usage:
1) Run : python vectorscope.py
2) Click and drag the squares to set the 16×16 pattern.
3) Click “Export WAV” to save a 30 s WAV file (you can edit the default name).
4) Import the WAV into FL Studio.
5) Add a WaveCandy plugin, choose “VectorScope” and turn the “Update” knob all the way up.
6) Play the sound: the image appears! – If it flickers or is only half displayed, “compress” the sample until the image is stable.

"""

import numpy as np
import soundfile as sf
import tkinter as tk
from tkinter import messagebox, filedialog

# ─────────── SETTINGS ───────────

MAT_SIZE = 16                 # Matrix dimension (16×16)
CELL_SIZE = 30                # Pixel size of each cell in GUI
PADDING = 2                   # Space between cells (in pixels)

N_SAMPLES_PER_PIXEL = 40      # Samples per active pixel in base block
SIGMA = 0.01                  # Gaussian noise std deviation (stereo amplitude)
SAMPLE_RATE = 44100           # WAV sample rate
DURATION_SEC = 30.0           # Total WAV length (seconds)

DEFAULT_OUTPUT_WAV = "matrice16x16_vectorscope_30s.wav"


# ─────────── CONVERSION FUNCTIONS ───────────

def matrix_to_points(mat):
    """
    Convert a MAT_SIZE×MAT_SIZE matrix to normalized (x_img, y_img) points in [-1, +1]².
    - row=0 → y_img=+1 (top), row=MAT_SIZE-1 → y_img=-1 (bottom)
    - col=0 → x_img=-1 (left), col=MAT_SIZE-1 → x_img=+1 (right)
    """
    H = len(mat)
    W = len(mat[0])
    pts = []
    for row in range(H):
        for col in range(W):
            if mat[row][col] == 1:
                x_img = (2 * col) / (W - 1) - 1.0
                y_img = -((2 * row) / (H - 1) - 1.0)
                pts.append((x_img, y_img))
    return pts

def xy_to_stereo(x_img, y_img):
    """
    For Vectorscope:
      x_img = R_amp - L_amp
      y_img = R_amp + L_amp
    → R_amp = (x_img + y_img) / 2
      L_amp = (y_img - x_img) / 2
    """
    R_amp = (x_img + y_img) / 2.0
    L_amp = (y_img - x_img) / 2.0
    return L_amp, R_amp


# ─────────── WAV GENERATION ───────────

def generate_wav_from_matrix(matrix, output_wav):
    """
    Create a 30 s stereo WAV from a binary matrix.
    - Build a short stereo block from active pixels.
    - Loop it until exactly DURATION_SEC is reached.
    """
    points_img = matrix_to_points(matrix)
    count = len(points_img)
    if count == 0:
        messagebox.showwarning("Warning", "No active pixels in the 16×16 matrix.")
        return

    # Base block length
    total_samples_base = count * N_SAMPLES_PER_PIXEL
    duration_base = total_samples_base / SAMPLE_RATE
    print(f"[INFO] Active pixels: {count}, base block duration: {duration_base:.6f} s ({total_samples_base} samples)")

    # Convert to stereo amplitudes
    stereo_amps = [xy_to_stereo(x, y) for (x, y) in points_img]

    # Allocate stereo buffers for base block
    data_L = np.zeros((total_samples_base,), dtype=np.float32)
    data_R = np.zeros((total_samples_base,), dtype=np.float32)

    idx = 0
    for (L_amp, R_amp) in stereo_amps:
        # Gaussian noise per active pixel
        noise_L = np.random.normal(loc=L_amp, scale=SIGMA, size=(N_SAMPLES_PER_PIXEL,))
        noise_R = np.random.normal(loc=R_amp, scale=SIGMA, size=(N_SAMPLES_PER_PIXEL,))

        # Clip to [-1, +1]
        noise_L = np.clip(noise_L, -1.0, +1.0)
        noise_R = np.clip(noise_R, -1.0, +1.0)

        data_L[idx : idx + N_SAMPLES_PER_PIXEL] = noise_L
        data_R[idx : idx + N_SAMPLES_PER_PIXEL] = noise_R
        idx += N_SAMPLES_PER_PIXEL

    # Stack to stereo shape (total_samples_base, 2)
    stereo_base = np.vstack((data_L, data_R)).T

    # ─────────── Loop to fill 30 s ───────────

    total_samples_target = int(DURATION_SEC * SAMPLE_RATE)
    reps = int(np.ceil(total_samples_target / total_samples_base))

    # Repeat and trim
    stereo_repeats = np.tile(stereo_base, (reps, 1))
    stereo_final = stereo_repeats[:total_samples_target, :]

    final_duration = stereo_final.shape[0] / SAMPLE_RATE
    print(f"[INFO] Repeated {reps} times → final duration: {final_duration:.6f} s ({stereo_final.shape[0]} samples)")

    # Write as 16-bit PCM
    sf.write(output_wav, stereo_final, samplerate=SAMPLE_RATE, subtype="PCM_16")
    messagebox.showinfo("Success", f"30 s WAV generated:\n{output_wav}")


# ─────────── GUI (Tkinter) ───────────

class MatrixGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("16×16 Matrix Editor → Vectorscope (30 s)")
        self.root.resizable(False, False)

        # Initialize MAT_SIZE×MAT_SIZE matrix of zeros
        self.matrix = [[0 for _ in range(MAT_SIZE)] for _ in range(MAT_SIZE)]
        self.draw_value = None  # Will store value (0 or 1) when dragging

        # Calculate canvas size
        canvas_size = MAT_SIZE * CELL_SIZE + (MAT_SIZE + 1) * PADDING
        self.canvas = tk.Canvas(
            self.root,
            width=canvas_size,
            height=canvas_size,
            bg="lightgray"
        )
        self.canvas.grid(row=0, column=0, padx=10, pady=10)

        # Draw initial grid (all off)
        self._draw_grid()

        # Bind click to toggle cells
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        # Bind dragging to draw multiple cells
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)

        # Export button
        bottom_frame = tk.Frame(self.root, pady=5)
        bottom_frame.grid(row=1, column=0, sticky="ew")
        btn_export = tk.Button(
            bottom_frame,
            text="Export 30 s WAV",
            command=self._on_export_click,
            width=20,
            bg="#2196f3",
            fg="white",
            font=("Arial", 12, "bold")
        )
        btn_export.pack(pady=5)

    def _draw_grid(self):
        """
        Draw the grid and fill each cell:
        Inactive (0) = black, Active (1) = white.
        """
        self.canvas.delete("all")
        for row in range(MAT_SIZE):
            for col in range(MAT_SIZE):
                x0 = PADDING + col * (CELL_SIZE + PADDING)
                y0 = PADDING + row * (CELL_SIZE + PADDING)
                x1 = x0 + CELL_SIZE
                y1 = y0 + CELL_SIZE
                color = "white" if self.matrix[row][col] == 1 else "black"
                self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=color,
                    outline="gray"
                )

    def _on_canvas_click(self, event):
        """
        On click, determine cell, toggle its state, set draw_value,
        then redraw so dragging uses the same value.
        """
        x, y = event.x, event.y
        col = (x - PADDING) // (CELL_SIZE + PADDING)
        row = (y - PADDING) // (CELL_SIZE + PADDING)

        if 0 <= row < MAT_SIZE and 0 <= col < MAT_SIZE:
            # Toggle the clicked cell
            self.matrix[row][col] ^= 1  # Toggle 0↔1
            # Store the resulting state; dragging will apply this value
            self.draw_value = self.matrix[row][col]
            self._draw_grid()

    def _on_canvas_drag(self, event):
        """
        On drag, set each encountered cell to the stored draw_value
        (so cells become either active or inactive uniformly).
        """
        x, y = event.x, event.y
        col = (x - PADDING) // (CELL_SIZE + PADDING)
        row = (y - PADDING) // (CELL_SIZE + PADDING)

        if (0 <= row < MAT_SIZE and 0 <= col < MAT_SIZE and
                self.draw_value is not None and
                self.matrix[row][col] != self.draw_value):
            self.matrix[row][col] = self.draw_value
            self._draw_grid()

    def _on_export_click(self):
        """
        Open save dialog and generate WAV if filename chosen.
        """
        default_path = DEFAULT_OUTPUT_WAV
        out_file = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav")],
            initialfile=default_path,
            title="Save 30 s WAV as"
        )
        if out_file:
            try:
                generate_wav_from_matrix(self.matrix, out_file)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate WAV:\n{e}")


def main():
    root = tk.Tk()
    app = MatrixGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
