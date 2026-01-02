import sys
import cv2
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QFileDialog, QSlider, QVBoxLayout, QHBoxLayout,
    QCheckBox, QGroupBox, QMessageBox, QScrollArea,
    QSizePolicy
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont

from nodes import FeedbackNode, GlowNode, RGBSplitNode, ObjectTrackingNode, BlobTrackingNode
from engine import VisualEngine


class VisualApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TouchVisual")
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
                margin-top: 5px;
                padding-top: 8px;
                font-weight: bold;
                color: #32cd32;
                font-size: 11pt;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QScrollArea {
                border: none;
            }
        """)

    def create_slider_with_label(self, label_text, min_val, max_val, default_val, callback):
        """Create a compact slider with label and value display"""
        container = QHBoxLayout()
        container.setSpacing(5)
        
        label = QLabel(label_text)
        label.setMinimumWidth(100)
        label.setMaximumWidth(100)
        container.addWidget(label)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        container.addWidget(slider)
        
        value_label = QLabel(str(default_val))
        value_label.setMinimumWidth(45)
        value_label.setMaximumWidth(45)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Update value label and call callback when slider changes
        def update_label_and_callback(val):
            value_label.setText(str(val))
            callback(val)
        slider.valueChanged.connect(update_label_and_callback)
        
        container.addWidget(value_label)
        return container, slider
    
    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left panel - Controls (fixed width)
        control_widget = QWidget()
        control_widget.setMaximumWidth(320)
        control_widget.setMinimumWidth(320)
        control_panel = QVBoxLayout()
        control_panel.setSpacing(8)
        control_panel.setContentsMargins(5, 5, 5, 5)
        
        # Video file section
        file_group = QGroupBox("Video File")
        file_layout = QVBoxLayout()
        file_layout.setContentsMargins(8, 12, 8, 8)
        self.load_btn = QPushButton("📁 Load Video")
        self.load_btn.clicked.connect(self.load_video)
        file_layout.addWidget(self.load_btn)
        file_group.setLayout(file_layout)
        control_panel.addWidget(file_group)
        
        # Effects menu section
        effects_group = QGroupBox("Effects")
        effects_layout = QVBoxLayout()
        effects_layout.setContentsMargins(8, 12, 8, 8)
        effects_layout.setSpacing(5)
        
        self.feedback_check = QCheckBox("Feedback")
        self.feedback_check.setChecked(True)
        self.feedback_check.stateChanged.connect(self.toggle_feedback)
        effects_layout.addWidget(self.feedback_check)
        
        self.glow_check = QCheckBox("Glow")
        self.glow_check.setChecked(True)
        self.glow_check.stateChanged.connect(self.toggle_glow)
        effects_layout.addWidget(self.glow_check)
        
        self.rgb_check = QCheckBox("RGB Split")
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
        
        # Effect parameters section - Scrollable
        params_group = QGroupBox("Parameters")
        params_container = QVBoxLayout()
        params_container.setContentsMargins(8, 12, 8, 8)
        params_container.setSpacing(6)
        
        # Feedback parameters
        feedback_slider_layout, self.feedback_slider = self.create_slider_with_label(
            "Feedback:", 50, 99, 90, self.update_feedback
        )
        params_container.addLayout(feedback_slider_layout)
        
        # Glow parameters
        glow_slider_layout, self.glow_slider = self.create_slider_with_label(
            "Glow:", 0, 300, 150, self.update_glow
        )
        params_container.addLayout(glow_slider_layout)
        
        # RGB parameters
        rgb_slider_layout, self.rgb_slider = self.create_slider_with_label(
            "RGB Shift:", 0, 50, 10, self.update_rgb
        )
        params_container.addLayout(rgb_slider_layout)
        
        # Object tracking parameters
        trail_slider_layout, self.trail_slider = self.create_slider_with_label(
            "Trail Length:", 5, 50, 20, self.update_trail
        )
        params_container.addLayout(trail_slider_layout)
        
        # Blob tracking parameters
        blob_min_slider_layout, self.blob_min_slider = self.create_slider_with_label(
            "Blob Min:", 50, 1000, 100, self.update_blob_min
        )
        params_container.addLayout(blob_min_slider_layout)
        
        blob_max_slider_layout, self.blob_max_slider = self.create_slider_with_label(
            "Blob Max:", 1000, 100000, 50000, self.update_blob_max
        )
        params_container.addLayout(blob_max_slider_layout)
        
        # Create scrollable area for parameters
        scroll_widget = QWidget()
        scroll_widget.setLayout(params_container)
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #800020;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a00030;
            }
        """)
        
        params_group_layout = QVBoxLayout()
        params_group_layout.setContentsMargins(0, 0, 0, 0)
        params_group_layout.addWidget(scroll_area)
        params_group.setLayout(params_group_layout)
        control_panel.addWidget(params_group)
        
        # Control buttons
        control_btn_group = QGroupBox("Controls")
        control_btn_layout = QVBoxLayout()
        control_btn_layout.setContentsMargins(8, 12, 8, 8)
        control_btn_layout.setSpacing(8)
        
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
        
        control_widget.setLayout(control_panel)
        main_layout.addWidget(control_widget)
        
        # Right panel - Video display
        video_panel = QVBoxLayout()
        video_panel.setSpacing(10)
        self.video_label = QLabel("Load a video to begin")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        self.status_label.setStyleSheet("color: #32cd32; font-weight: bold; padding: 5px;")
        self.status_label.setMaximumHeight(30)
        video_panel.addWidget(self.status_label)
        
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
