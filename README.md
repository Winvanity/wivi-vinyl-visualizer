# Wivi Vinyl Visualizer

**Wivi Vinyl Visualizer** is a modern, standalone desktop application built with Python and Tkinter for generating high-aesthetic music visualization videos featuring a spinning vinyl record, reactive audio equalizers, and dynamic particle effects.

Created by **Winvanity (Damian Rzepczyński)** in **2026**.

---

## Key Features

- **Real-time Audio Analysis (FFT):** Generates responsive equalizer bars and bass-reactive background pulsing based on your audio track.
- **Vinyl Animation & Sleeve Logic:** Smooth vinyl disc insertion and removal animations for intros and outros, paired with customizable RPM rotation control.
- **Particle Effects:** Optional falling dust particles with adjustable count and speed settings.
- **Modern Dark UI:** Built using a custom-styled, responsive two-column layout with real-time frame previews.
- **High-Resolution Export:** Renders final videos in 720p, Full HD (1080p), 2K, or 4K UHD via MoviePy.

---

## Tech Stack

- **Python 3.12**
- **Tkinter & TTK** (Modernized GUI & Scrollable Layout)
- **MoviePy & NumPy** (Video rendering & FFT audio processing)
- **Pillow (PIL)** (Image processing, effects, and text rendering)
- **Pygame** (Local audio preview handler)

---

## Getting Started & Installation

If you want to run or build the project from source, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/wivi-vinyl-visualizer.git
   cd wivi-vinyl-visualizer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python vinyl_gui.py
   ```

---

## Building to Standalone `.exe`

To compile the application into a portable Windows executable (`.exe`) with a custom icon, use **PyInstaller**:

```bash
py -3.12 -m PyInstaller --onefile --noconsole --icon=vinyl.ico --name="Wivi Vinyl Visualizer" vinyl_gui.py
```

The compiled executable will be generated inside the `dist/` folder.

---

## License

This project is open-source and available under the [MIT License](LICENSE).
