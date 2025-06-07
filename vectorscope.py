#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# vectorscope.py — © 2025 NaFo44 — Licensed under the MIT License

import numpy as np
import soundfile as sf
import tkinter as tk
from tkinter import messagebox, filedialog
import json

# ─────────── SETTINGS ───────────

MAT_SIZE = 16                   # Matrix dimensions (16×16)
CELL_SIZE = 20                  # Pixel size of each cell in the UI
PADDING = 1                     # Space between cells (pixels)

N_SAMPLES_PER_PIXEL = 100       # Samples per active pixel in the base block (big impact, lower values : higher framerate but bad quality, higher values : bad framerate but nice and clean pixels)
SIGMA = 0.01                    # Std dev for Gaussian noise (stereo amplitude)
SAMPLE_RATE = 44100             # Sampling rate for the WAV
FRAME_DURATION = 0.125          # Duration of each frame in seconds (~1/8 s)
IMAGE_DURATION = 30.0           # Duration in seconds for exported image WAV

WAV_SUBTYPE = "PCM_16"
DEFAULT_OUTPUT_WAV = "video_vectorscope_16x16.wav"

# ─────────── CONVERSION FUNCTIONS ───────────

def matrix_to_points(mat):
    pts = []
    H, W = len(mat), len(mat[0]) if mat else 0
    for r in range(H):
        for c in range(W):
            if mat[r][c]:
                x = (2 * c) / (W - 1) - 1.0
                y = -((2 * r) / (H - 1) - 1.0)
                pts.append((x, y))
    return pts


def xy_to_stereo(x, y):
    return (y - x) / 2.0, (x + y) / 2.0


def create_base_block(matrix):
    pts = matrix_to_points(matrix)
    if not pts:
        return None, 0
    total = len(pts) * N_SAMPLES_PER_PIXEL
    amps = [xy_to_stereo(x, y) for x, y in pts]
    L = np.zeros(total, np.float32)
    R = np.zeros(total, np.float32)
    idx = 0
    for l_amp, r_amp in amps:
        nL = np.clip(np.random.normal(l_amp, SIGMA, N_SAMPLES_PER_PIXEL), -1, 1)
        nR = np.clip(np.random.normal(r_amp, SIGMA, N_SAMPLES_PER_PIXEL), -1, 1)
        L[idx:idx+N_SAMPLES_PER_PIXEL] = nL
        R[idx:idx+N_SAMPLES_PER_PIXEL] = nR
        idx += N_SAMPLES_PER_PIXEL
    return np.vstack((L, R)).T, total


def generate_video_wav_from_frames(frames, output_wav):
    if not frames:
        messagebox.showwarning("Warning", "No frames to export!")
        return
    samples_frame = int(FRAME_DURATION * SAMPLE_RATE)
    segments = []
    for mat in frames:
        block, base_samples = create_base_block(mat)
        if base_samples == 0:
            segments.append(np.zeros((samples_frame, 2), np.float32))
        else:
            reps = int(np.ceil(samples_frame / base_samples))
            rep = np.tile(block, (reps, 1))
            segments.append(rep[:samples_frame])
    final = np.vstack(segments)
    sf.write(output_wav, final, SAMPLE_RATE, subtype=WAV_SUBTYPE)
    messagebox.showinfo("Success", f"Video WAV generated:\n{output_wav}")

# ─────────── GUI ───────────
class MatrixGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("16×16 Video Vectorscope")
        self.root.resizable(False, False)

        self.project_path = None
        self.frames = [[[0]*MAT_SIZE for _ in range(MAT_SIZE)]]
        self.current_frame = 0
        self.draw_value = None

        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Project", command=self._new_project)
        file_menu.add_command(label="Open...", command=self._load_project)
        file_menu.add_command(label="Save", command=self._save_project)
        file_menu.add_command(label="Save As...", command=self._save_as_project)
        file_menu.add_separator()
        file_menu.add_command(label="Export Video WAV...", command=self._export_wav)
        file_menu.add_command(label="Export Image WAV...", command=self._export_image)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

        size = MAT_SIZE * CELL_SIZE + (MAT_SIZE + 1) * PADDING
        self.canvas = tk.Canvas(self.root, width=size, height=size, bg="lightgray")
        self.canvas.grid(row=0, column=0, columnspan=4, padx=10, pady=10)
        self.label = tk.Label(self.root, text=self._frame_label(), font=("Arial", 10))
        self.label.grid(row=1, column=0, columnspan=4)

        btn_prev = tk.Button(self.root, text="Prev Frame", width=10, command=self._prev_frame)
        btn_prev.grid(row=2, column=0)
        btn_new = tk.Button(self.root, text="New Frame", width=10, command=self._new_frame)
        btn_new.grid(row=2, column=1)
        btn_next = tk.Button(self.root, text="Next Frame", width=10, command=self._next_frame)
        btn_next.grid(row=2, column=2)
        btn_clear = tk.Button(self.root, text="Clear Frame", width=14, bg="#f44336", fg="white", command=self._clear_frame)
        btn_clear.grid(row=2, column=3)

        self._draw()
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)

    def _frame_label(self):
        return f"Frame {self.current_frame+1} / {len(self.frames)}"

    def _draw(self):
        self.canvas.delete("all")
        prev = self.frames[self.current_frame-1] if self.current_frame>0 else None
        for r in range(MAT_SIZE):
            for c in range(MAT_SIZE):
                x0 = PADDING + c*(CELL_SIZE+PADDING)
                y0 = PADDING + r*(CELL_SIZE+PADDING)
                x1, y1 = x0+CELL_SIZE, y0+CELL_SIZE
                self.canvas.create_rectangle(x0, y0, x1, y1, fill="black", outline="gray")
        if prev:
            for r in range(MAT_SIZE):
                for c in range(MAT_SIZE):
                    if prev[r][c]:
                        x0 = PADDING + c*(CELL_SIZE+PADDING)
                        y0 = PADDING + r*(CELL_SIZE+PADDING)
                        x1, y1 = x0+CELL_SIZE, y0+CELL_SIZE
                        self.canvas.create_rectangle(x0, y0, x1, y1, fill="#4A4A4A", outline="gray")
        mat = self.frames[self.current_frame]
        for r in range(MAT_SIZE):
            for c in range(MAT_SIZE):
                if mat[r][c]:
                    x0 = PADDING + c*(CELL_SIZE+PADDING)
                    y0 = PADDING + r*(CELL_SIZE+PADDING)
                    x1, y1 = x0+CELL_SIZE, y0+CELL_SIZE
                    self.canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="gray")
        self.label.config(text=self._frame_label())

    def _on_click(self, e):
        c = (e.x - PADDING)//(CELL_SIZE+PADDING)
        r = (e.y - PADDING)//(CELL_SIZE+PADDING)
        if 0<=r<MAT_SIZE and 0<=c<MAT_SIZE:
            m = self.frames[self.current_frame]
            m[r][c] ^= 1
            self.draw_value = m[r][c]
            self._draw()

    def _on_drag(self, e):
        c = (e.x - PADDING)//(CELL_SIZE+PADDING)
        r = (e.y - PADDING)//(CELL_SIZE+PADDING)
        if 0<=r<MAT_SIZE and 0<=c<MAT_SIZE and self.draw_value is not None:
            m = self.frames[self.current_frame]
            if m[r][c]!=self.draw_value:
                m[r][c]=self.draw_value
                self._draw()

    def _prev_frame(self):
        if self.current_frame>0:
            self.current_frame-=1
            self._draw()
        else:
            messagebox.showinfo("Info", "Already first frame.")

    def _next_frame(self):
        if self.current_frame<len(self.frames)-1:
            self.current_frame+=1
        else:
            self._new_frame()
        self._draw()

    def _new_frame(self):
        self.frames.append([[0]*MAT_SIZE for _ in range(MAT_SIZE)])
        self.current_frame=len(self.frames)-1
        self._draw()

    def _clear_frame(self):
        self.frames[self.current_frame]=[[0]*MAT_SIZE for _ in range(MAT_SIZE)]
        self._draw()

    def _new_project(self):
        if messagebox.askyesno("New Project","All unsaved changes will be lost. Continue?"):
            self.frames=[[[0]*MAT_SIZE for _ in range(MAT_SIZE)]]
            self.current_frame=0
            self.project_path=None
            self._draw()

    def _save_project(self):
        if not self.project_path:
            return self._save_as_project()
        try:
            with open(self.project_path,'w') as f:
                json.dump({"MAT_SIZE":MAT_SIZE,"frames":self.frames},f)
            messagebox.showinfo("Project Saved",f"Saved to:\n{self.project_path}")
        except Exception as e:
            messagebox.showerror("Error",f"Failed to save:\n{e}")

    def _save_as_project(self):
        path=filedialog.asksaveasfilename(defaultextension=".wcv",filetypes=[("WaveCandyVideo files","*.wcv")],title="Save As...")
        if not path: return
        self.project_path=path
        return self._save_project()

    def _load_project(self):
        path=filedialog.askopenfilename(defaultextension=".wcv",filetypes=[("WaveCandyVideo files","*.wcv")],title="Open...")
        if not path: return
        try:
            with open(path,'r') as f:
                data=json.load(f)
            fr=data.get("frames")
            if not isinstance(fr,list): raise ValueError
            self.frames=fr
            self.current_frame=0
            self.project_path=path
            self._draw()
            messagebox.showinfo("Project Loaded",f"Loaded:\n{path}")
        except Exception as e:
            messagebox.showerror("Error",f"Failed to load:\n{e}")

    def _export_wav(self):
        out=filedialog.asksaveasfilename(defaultextension=".wav",filetypes=[("WAV files","*.wav")],initialfile=DEFAULT_OUTPUT_WAV,title="Export Video WAV...")
        if out:
            try: generate_video_wav_from_frames(self.frames, out)
            except Exception as e: messagebox.showerror("Error",f"Failed to export WAV:\n{e}")

    def _export_image(self):
        """Export current frame as a looped WAV (~IMAGE_DURATION seconds)"""
        default_name = f"frame{self.current_frame+1}.wav"
        path = filedialog.asksaveasfilename(defaultextension=".wav",
                                            filetypes=[("WAV files","*.wav")],
                                            initialfile=default_name,
                                            title="Export Image WAV...")
        if not path:
            return
        mat = self.frames[self.current_frame]
        block, base = create_base_block(mat)
        total_samples = int(IMAGE_DURATION * SAMPLE_RATE)
        if base == 0:
            data = np.zeros((total_samples, 2), np.float32)
        else:
            reps = int(np.ceil(total_samples / base))
            rep = np.tile(block, (reps, 1))
            data = rep[:total_samples]
        sf.write(path, data, SAMPLE_RATE, subtype=WAV_SUBTYPE)
        messagebox.showinfo("Success", f"Image WAV generated:\n{path}")


def main():
    root = tk.Tk()
    MatrixGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
