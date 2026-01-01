import sys
import cv2
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QFileDialog, QSlider, QVBoxLayout, QHBoxLayout,
    QCheckBox, QGroupBox, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont

from nodes import FeedbackNode, GlowNode, RGBSplitNode, ObjectTrackingNode, BlobTrackingNode
from engine import VisualEngine


class VisualApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TouchDesigner-Style Visual Engine")
        self.resize(1200, 700)

        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        # Video recording
        self.video_writer = None
        self.is_recording = False
        self.output_path = None
        self.fps = 30
        self.frame_width = 0
        self.frame_height = 0

        # Nodes
        self.feedback = FeedbackNode(0.9)
        self.glow = GlowNode(1.5)
        self.rgb = RGBSplitNode(10)
        self.object_tracking = ObjectTrackingNode(show_trail=True, trail_length=20)
        self.blob_tracking = BlobTrackingNode(min_area=100, max_area=50000)
        
        # Effect states
        self.effects_enabled = {
            'feedback': True,
            'glow': True,
            'rgb_split': True,
            'object_tracking': False,
            'blob_tracking': False
        }

        self.engine = VisualEngine([
            self.feedback,
            self.glow,
            self.rgb
        ])

        self.apply_dark_theme()
        self.init_ui()

    def apply_dark_theme(self):
        """Apply green and burgundy color scheme"""
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #d4d4d4;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #d4d4d4;
                padding: 5px;
            }
            QPushButton {
                background-color: #800020;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #a00030;
            }
            QPushButton:pressed {
                background-color: #600015;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #808080;
            }
            QCheckBox {
                color: #d4d4d4;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #228b22;
                border-color: #32cd32;
            }
            QCheckBox::indicator:hover {
                border-color: #32cd32;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #2d2d2d;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #228b22;
                border: 2px solid #32cd32;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #32cd32;
            }
            QGroupBox {
                border: 2px solid #800020;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #32cd32;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # Left panel - Controls
        control_panel = QVBoxLayout()
        
        # Video file section
        file_group = QGroupBox("Video File")
        file_layout = QVBoxLayout()
        self.load_btn = QPushButton("📁 Load Video")
        self.load_btn.clicked.connect(self.load_video)
        file_layout.addWidget(self.load_btn)
        file_group.setLayout(file_layout)
        control_panel.addWidget(file_group)
        
        # Effects menu section
        effects_group = QGroupBox("Effects Menu")
        effects_layout = QVBoxLayout()
        
        self.feedback_check = QCheckBox("Feedback Effect")
        self.feedback_check.setChecked(True)
        self.feedback_check.stateChanged.connect(self.toggle_feedback)
        effects_layout.addWidget(self.feedback_check)
        
        self.glow_check = QCheckBox("Glow Effect")
        self.glow_check.setChecked(True)
        self.glow_check.stateChanged.connect(self.toggle_glow)
        effects_layout.addWidget(self.glow_check)
        
        self.rgb_check = QCheckBox("RGB Split Effect")
        self.rgb_check.setChecked(True)
        self.rgb_check.stateChanged.connect(self.toggle_rgb)
        effects_layout.addWidget(self.rgb_check)
        
        self.object_tracking_check = QCheckBox("Object Tracking")
        self.object_tracking_check.setChecked(False)
        self.object_tracking_check.stateChanged.connect(self.toggle_object_tracking)
        effects_layout.addWidget(self.object_tracking_check)
        
        self.blob_tracking_check = QCheckBox("Blob Tracking")
        self.blob_tracking_check.setChecked(False)
        self.blob_tracking_check.stateChanged.connect(self.toggle_blob_tracking)
        effects_layout.addWidget(self.blob_tracking_check)
        
        effects_group.setLayout(effects_layout)
        control_panel.addWidget(effects_group)
        
        # Effect parameters section
        params_group = QGroupBox("Effect Parameters")
        params_layout = QVBoxLayout()
        
        # Feedback decay
        feedback_label = QLabel("Feedback Decay:")
        params_layout.addWidget(feedback_label)
        self.feedback_slider = QSlider(Qt.Horizontal)
        self.feedback_slider.setRange(50, 99)
        self.feedback_slider.setValue(90)
        self.feedback_slider.valueChanged.connect(self.update_feedback)
        params_layout.addWidget(self.feedback_slider)
        
        # Glow strength
        glow_label = QLabel("Glow Strength:")
        params_layout.addWidget(glow_label)
        self.glow_slider = QSlider(Qt.Horizontal)
        self.glow_slider.setRange(0, 300)
        self.glow_slider.setValue(150)
        self.glow_slider.valueChanged.connect(self.update_glow)
        params_layout.addWidget(self.glow_slider)
        
        # RGB shift
        rgb_label = QLabel("RGB Shift:")
        params_layout.addWidget(rgb_label)
        self.rgb_slider = QSlider(Qt.Horizontal)
        self.rgb_slider.setRange(0, 50)
        self.rgb_slider.setValue(10)
        self.rgb_slider.valueChanged.connect(self.update_rgb)
        params_layout.addWidget(self.rgb_slider)
        
        # Object tracking trail length
        trail_label = QLabel("Tracking Trail Length:")
        params_layout.addWidget(trail_label)
        self.trail_slider = QSlider(Qt.Horizontal)
        self.trail_slider.setRange(5, 50)
        self.trail_slider.setValue(20)
        self.trail_slider.valueChanged.connect(self.update_trail)
        params_layout.addWidget(self.trail_slider)
        
        # Blob tracking min area
        blob_min_label = QLabel("Blob Min Area:")
        params_layout.addWidget(blob_min_label)
        self.blob_min_slider = QSlider(Qt.Horizontal)
        self.blob_min_slider.setRange(50, 1000)
        self.blob_min_slider.setValue(100)
        self.blob_min_slider.valueChanged.connect(self.update_blob_min)
        params_layout.addWidget(self.blob_min_slider)
        
        # Blob tracking max area
        blob_max_label = QLabel("Blob Max Area:")
        params_layout.addWidget(blob_max_label)
        self.blob_max_slider = QSlider(Qt.Horizontal)
        self.blob_max_slider.setRange(1000, 100000)
        self.blob_max_slider.setValue(50000)
        self.blob_max_slider.valueChanged.connect(self.update_blob_max)
        params_layout.addWidget(self.blob_max_slider)
        
        params_group.setLayout(params_layout)
        control_panel.addWidget(params_group)
        
        # Control buttons
        control_btn_group = QGroupBox("Controls")
        control_btn_layout = QVBoxLayout()
        
        self.start_btn = QPushButton("▶ Start")
        self.start_btn.clicked.connect(self.start)
        control_btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.setEnabled(False)
        control_btn_layout.addWidget(self.stop_btn)
        
        self.save_btn = QPushButton("💾 Save Output")
        self.save_btn.clicked.connect(self.toggle_recording)
        self.save_btn.setEnabled(False)
        control_btn_layout.addWidget(self.save_btn)
        
        control_btn_group.setLayout(control_btn_layout)
        control_panel.addWidget(control_btn_group)
        
        control_panel.addStretch()
        
        # Right panel - Video display
        video_panel = QVBoxLayout()
        self.video_label = QLabel("Load a video to begin")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #0d0d0d;
                border: 2px solid #800020;
                border-radius: 5px;
            }
        """)
        video_panel.addWidget(self.video_label)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #32cd32; font-weight: bold;")
        video_panel.addWidget(self.status_label)
        
        # Combine layouts
        main_layout.addLayout(control_panel, 1)
        main_layout.addLayout(video_panel, 3)
        
        self.setLayout(main_layout)

    def load_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Video", "", "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
        )
        if path:
            self.cap = cv2.VideoCapture(path)
            if self.cap.isOpened():
                self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
                self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.status_label.setText(f"Video loaded: {os.path.basename(path)}")
                self.start_btn.setEnabled(True)
                self.save_btn.setEnabled(True)
            else:
                QMessageBox.warning(self, "Error", "Failed to open video file")

    def start(self):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to beginning
            self.timer.start(1000 // self.fps if self.fps > 0 else 30)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText("Playing...")

    def stop(self):
        self.timer.stop()
        if self.is_recording:
            self.stop_recording()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Stopped")

    def toggle_feedback(self, state):
        self.effects_enabled['feedback'] = (state == Qt.Checked)
        self.update_engine()

    def toggle_glow(self, state):
        self.effects_enabled['glow'] = (state == Qt.Checked)
        self.update_engine()

    def toggle_rgb(self, state):
        self.effects_enabled['rgb_split'] = (state == Qt.Checked)
        self.update_engine()
    
    def toggle_object_tracking(self, state):
        self.effects_enabled['object_tracking'] = (state == Qt.Checked)
        if state == Qt.Unchecked:
            # Reset tracker when disabled
            self.object_tracking.tracker_initialized = False
            self.object_tracking.tracker = None
            self.object_tracking.trail_points = []
        self.update_engine()
    
    def toggle_blob_tracking(self, state):
        self.effects_enabled['blob_tracking'] = (state == Qt.Checked)
        if state == Qt.Unchecked:
            # Reset background subtractor when disabled
            self.blob_tracking.bg_subtractor = None
        self.update_engine()

    def update_engine(self):
        """Rebuild engine with only enabled effects"""
        nodes = []
        if self.effects_enabled['feedback']:
            nodes.append(self.feedback)
        if self.effects_enabled['glow']:
            nodes.append(self.glow)
        if self.effects_enabled['rgb_split']:
            nodes.append(self.rgb)
        if self.effects_enabled['object_tracking']:
            nodes.append(self.object_tracking)
        if self.effects_enabled['blob_tracking']:
            nodes.append(self.blob_tracking)
        self.engine = VisualEngine(nodes)

    def update_feedback(self, value):
        self.feedback.decay = value / 100.0

    def update_glow(self, value):
        self.glow.strength = value / 100.0

    def update_rgb(self, value):
        self.rgb.shift = value
    
    def update_trail(self, value):
        self.object_tracking.trail_length = value
    
    def update_blob_min(self, value):
        self.blob_tracking.min_area = value
    
    def update_blob_max(self, value):
        self.blob_tracking.max_area = value

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        if not self.cap:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Video", "", "MP4 Files (*.mp4);;AVI Files (*.avi);;All Files (*)"
        )
        if path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                path, fourcc, self.fps, (self.frame_width, self.frame_height)
            )
            if self.video_writer.isOpened():
                self.is_recording = True
                self.output_path = path
                self.save_btn.setText("⏹ Stop Recording")
                self.save_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #800020;
                    }
                    QPushButton:hover {
                        background-color: #a00030;
                    }
                """)
                self.status_label.setText(f"Recording to: {os.path.basename(path)}")
            else:
                QMessageBox.warning(self, "Error", "Failed to initialize video writer")

    def stop_recording(self):
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        self.is_recording = False
        self.save_btn.setText("💾 Save Output")
        self.save_btn.setStyleSheet("")  # Reset to default style
        if self.output_path:
            self.status_label.setText(f"Saved: {os.path.basename(self.output_path)}")
            self.output_path = None

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.timer.stop()
            if self.is_recording:
                self.stop_recording()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("Video ended")
            return

        # Process frame through engine
        processed_frame = self.engine.process(frame)
        
        # Save frame if recording
        if self.is_recording and self.video_writer:
            self.video_writer.write(processed_frame)
        
        # Convert for display
        display_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = display_frame.shape
        bytes_per_line = ch * w
        img = QImage(display_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale to fit label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(img)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VisualApp()
    window.show()
    sys.exit(app.exec_())
