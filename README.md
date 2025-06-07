[![Licence: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# Video Vectorscope 16×16

A simple Python/Tkinter application that lets you draw frame-by-frame vector scopes on a 16×16 grid and export them as WAV audio files (video-style or looping image-style). A compiled `.exe` version is also available for users without Python.

## Table of Contents

* [Features](#features)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Usage](#usage)
* [Building the Executable](#building-the-executable)
* [Future Improvements](#future-improvements)
* [License](#license)

## Features

* Frame-by-frame drawing on a 16×16 grid
* Ghosting of previous frame for easier animation
* Export entire sequence as a "video" WAV file
* Export individual frames as looping image WAV files
* Save and load projects in custom `.wcv` format
* Simple and lightweight Tkinter-based GUI

## Prerequisites

* Python 3.7 or higher
* `numpy`
* `soundfile`
* `tkinter` (usually included with standard Python installs)

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/NaFo44/video-vectorscope
   cd video-vectorscope
   ```
   
2. Install dependencies:

   ```bash
   pip install numpy soundfile tkinter
   ```

## Usage

1. Launch the application:

   ```bash
   python vectorscope.py
   ```

2. Use the `File` menu to create a new project, load/save `.wcv` files, or export to WAV.

3. Draw on the grid by clicking or dragging. Use the buttons to navigate frames or clear.

## Building the Executable

For users without Python, a standalone Windows executable `.exe` is provided. To build it yourself:

1. Install `pyinstaller`:

   ```bash
   pip install pyinstaller
   ```

2. Run PyInstaller:

   ```bash
   pyinstaller --onefile --windowed vectorscope.py
   ```

3. The executable will be found in the `dist/` folder.

## Future Improvements

* Allow customizable grid size
* Add playback of generated audio/video directly in the GUI
* Implement undo/redo functionality for drawing
* Add keyboard shortcuts for faster workflow
* Support exporting to other audio or video formats

## License
This project is released under the MIT License. See [LICENSE](LICENSE) for details.
