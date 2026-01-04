# TouchVisual

A **node-based, visual processing engine** built in Python using **OpenCV, NumPy, and PyQt**, inspired by **TouchDesigner**.

This project demonstrates how generative visuals, feedback systems, motion analysis, and creative-coding workflows can be implemented **programmatically without TouchDesigner**.

---

## Features

- **Video Input**
  - Load video files via desktop UI
  - Frame-by-frame real-time processing

- **Node-Based Architecture**
  - Modular visual nodes
  - Sequential processing pipeline
  - Each effect is isolated, reusable, and stateful

- **Visual Effects (Nodes)**
  - Feedback / Motion Echo
  - Glow / Bloom
  - RGB Split / Glitch
  - Extensible architecture for motion detection, noise, tracking, audio reactivity

- **Desktop GUI**
  - Built using PyQt
  - Live preview window
  - Real-time parameter control
  - Start / Stop playback

- **Real-Time Rendering**
  - Preserves original resolution
  - Designed for generative visuals and experimentation

---

## Tech Stack

| Technology | Purpose |
|----------|--------|
| Python | Core language |
| OpenCV | Video processing |
| NumPy | Numerical operations |
| PyQt5 | Desktop UI |
| OOP Design | Node-based architecture |

---

## Project Structure
TouchVisual/
│
├── app.py # Desktop GUI (main entry point)
├── engine.py # VisualEngine pipeline logic
├── nodes.py # All visual effect nodes
├── requirements.txt
└── README.md

## Installation

### 1. Install Dependencies
pip install -r requirements.txt


### 2. Run the Application
python app.py


---

## Usage

1. Click **Load Video**
2. Press **Start**
3. Adjust visual parameters in real time
4. Press **Stop** to pause playback


---

## Design Goals

- Recreate TouchDesigner-style workflows in Python
- Emphasize modularity and extensibility
- Keep the code beginner-readable yet professional
- Build a strong creative-coding portfolio project

---

## Possible Extensions

- Audio-reactive visuals (FFT-driven effects)
- Live webcam input
- OSC / MIDI control
- Perlin noise-based distortion
- Motion tracking-driven visuals
- Visual node graph editor
- GPU acceleration (CUDA / GLSL)

---

## Use Cases

- Creative coding experiments
- Generative visuals
- VJ tools and visualizers
- Motion graphics prototyping
- Computer vision + art projects

---




