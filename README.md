[![Licence: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Libraries
**Don't forget to :**
```
pip install numpy
```
 and 
```
pip install soundfile
```

## Image:
1) Run vectorscope.py
2) Click the squares to set the 16×16 pattern.
3) Click “Export WAV” to save a 30 s WAV file (you can edit the default name).
4) Import the WAV into FL Studio.
5) Add a WaveCandy plugin, choose “VectorScope” and turn the “Update” knob all the way up.
6) Play the sound: the image appears! – If it flickers or is only half displayed, “compress” the sample until the image is stable.

You can try a pre-generated image (example.wav) before downloading the program

## Video:
1) Run: python vectorscope.py
2) Click “New Frame” to create a blank 16×16 frame. Use “Prev Frame” and “Next Frame” to navigate and edit each frame.
3) For each frame, click or drag to toggle cells on (white) or off (black).
4) Click “Export Video WAV” to generate a .wav file: each frame lasts ≈0.125 s and frames are joined sequentially.
   If a frame is empty, it produces 0.125 s of silence.
5) Import the WAV into FL Studio, add WaveCandy → VectorScope, set “Update” to max, and play: images appear 1/8 s per frame.

If you only need a single static sound (30 s) for one matrix, keep the original generate_wav_from_matrix function, but here we focus on video export.
