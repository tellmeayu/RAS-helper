#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAS-helper: Gait Analysis Widget

This module implements a PyQt5 widget for displaying real-time gait analysis data.
It presents temporal and spatial gait parameters along with visualization of gait cycle.
"""

from typing import Dict, Any, Optional
import time

from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QTableWidget, QTableWidgetItem, QTabWidget, QWidget, QPushButton,
    QFrame, QSizePolicy, QHeaderView
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PyQt5.QtCore import Qt, QRect, QTimer, pyqtSlot, QSize


class GaitCycleVisualizerWidget(QFrame):
    """Widget for visualizing the gait cycle phases."""
    
    def __init__(self, parent=None):
        """Initialize the gait cycle visualizer."""
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.setStyleSheet("background-color: #333;")
        
        # Gait cycle data
        self.left_phase = "UNKNOWN"
        self.right_phase = "UNKNOWN"
        self.gait_cycle_position = 0.0  # 0.0 to 1.0 representing position in gait cycle
        
        # Animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(50)  # 20 fps animation
        
        # Auto-advance if no real data
        self.last_update_time = time.time()
        self.auto_advance = True
    
    def set_foot_phases(self, left_phase: str, right_phase: str):
        """Set the current phase of each foot."""
        self.left_phase = left_phase
        self.right_phase = right_phase
        self.last_update_time = time.time()
        self.auto_advance = False
        self.update()
    
    def set_cycle_position(self, position: float):
        """Set the current position in the gait cycle (0.0 to 1.0)."""
        self.gait_cycle_position = max(0.0, min(1.0, position))
        self.last_update_time = time.time()
        self.auto_advance = False
        self.update()
    
    def update_animation(self):
        """Update the animation state."""
        # If no real data received for 2 seconds, auto-advance
        if time.time() - self.last_update_time > 2.0:
            self.auto_advance = True
        
        if self.auto_advance:
            self.gait_cycle_position = (self.gait_cycle_position + 0.02) % 1.0
            
            # Simulate phase changes based on position
            if self.gait_cycle_position < 0.6:
                self.left_phase = "STANCE"
            else:
                self.left_phase = "SWING"
                
            if (self.gait_cycle_position + 0.5) % 1.0 < 0.6:
                self.right_phase = "STANCE"
            else:
                self.right_phase = "SWING"
            
            self.update()
    
    def paintEvent(self, event):
        """Paint the gait cycle visualization."""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw background
        painter.fillRect(event.rect(), QColor("#333"))
        
        # Draw gait cycle timeline
        timeline_height = 20
        timeline_y = height - timeline_height - 10
        
        # Draw timeline track - ensure all arguments are integers
        painter.setPen(QPen(QColor("#777"), 2))
        painter.drawLine(20, int(timeline_y + timeline_height/2), 
                        width - 20, int(timeline_y + timeline_height/2))
        
        # Draw cycle position marker
        position_x = 20 + (width - 40) * self.gait_cycle_position
        
        painter.setBrush(QBrush(QColor("#3498db")))
        painter.setPen(QPen(QColor("#2980b9"), 2))
        painter.drawEllipse(int(position_x) - 8, int(timeline_y + timeline_height/2) - 8, 16, 16)
        
        # Draw foot phase indicators
        left_foot_x = width // 3
        right_foot_x = 2 * width // 3
        foot_y = height // 2 - 20
        
        # Left foot
        left_color = QColor("#27ae60") if self.left_phase == "SWING" else QColor("#e74c3c")
        painter.setBrush(QBrush(left_color))
        painter.setPen(QPen(QColor("black"), 1))
        painter.drawRect(left_foot_x - 40, foot_y, 80, 30)
        
        painter.setPen(QPen(QColor("white"), 1))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(
            QRect(left_foot_x - 40, foot_y, 80, 30),
            Qt.AlignCenter,
            f"Left: {self.left_phase}"
        )
        
        # Right foot
        right_color = QColor("#27ae60") if self.right_phase == "SWING" else QColor("#e74c3c")
        painter.setBrush(QBrush(right_color))
        painter.setPen(QPen(QColor("black"), 1))
        painter.drawRect(right_foot_x - 40, foot_y, 80, 30)
        
        painter.setPen(QPen(QColor("white"), 1))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(
            QRect(right_foot_x - 40, foot_y, 80, 30),
            Qt.AlignCenter,
            f"Right: {self.right_phase}"
        )
        
        # Draw labels
        painter.setPen(QPen(QColor("white"), 1))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(10, timeline_y - 5, "Gait Cycle")
        painter.drawText(20, timeline_y + timeline_height + 15, "0%")
        painter.drawText(width - 40, timeline_y + timeline_height + 15, "100%")


class GaitParametersTable(QTableWidget):
    """Table widget for displaying gait parameters."""
    
    def __init__(self, parent=None):
        """Initialize the gait parameters table."""
        super().__init__(0, 3, parent)
        
        # Set headers
        self.setHorizontalHeaderLabels(["Parameter", "Value", "Normal Range"])
        
        # Set column widths
        self.setColumnWidth(0, 150)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 150)
        
        # Style
        self.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f5f5f5;
                border: 1px solid #ddd;
            }
            QHeaderView::section {
                background-color: #4a86e8;
                color: white;
                font-weight: bold;
                border: none;
                padding: 5px;
            }
        """)
        
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Set size policy to ensure full height display without scrolling
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # Ensure that the table's vertical size hint includes all rows
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Disable scrollbars to encourage parent to provide proper space
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Initialize with empty values
        self.initialize_parameters()

    def sizeHint(self):
        """Override size hint to return a size that fits exactly the content."""
        width = self.horizontalHeader().length() + self.frameWidth() * 2
        height = self.verticalHeader().length() + self.horizontalHeader().height() + self.frameWidth() * 2
        return QSize(width, height)
    
    def initialize_parameters(self):
        """Initialize the table with default parameters."""
        self.setRowCount(0)
        
        # Add temporal parameters
        self._add_parameter("Cadence (steps/min)", "0.0", "90-130")
        self._add_parameter("Step Time (s)", "0.0", "0.4-0.6")
        self._add_parameter("Stride Time (s)", "0.0", "0.8-1.2")
        self._add_parameter("Swing Phase (%)", "0.0", "35-40")
        self._add_parameter("Stance Phase (%)", "0.0", "60-65")
        
        # Add spatial parameters
        self._add_parameter("Step Length (m)", "0.0", "0.5-0.8")
        self._add_parameter("Stride Length (m)", "0.0", "1.0-1.6")
        self._add_parameter("Walking Speed (m/s)", "0.0", "1.0-1.5")
        
        # Add asymmetry parameters
        self._add_parameter("Step Length Asymmetry (%)", "0.0", "<10")
        self._add_parameter("Stance Time Asymmetry (%)", "0.0", "<10")
    
    def _add_parameter(self, name, value, normal_range):
        """Add a parameter row to the table."""
        row = self.rowCount()
        self.insertRow(row)
        
        self.setItem(row, 0, QTableWidgetItem(name))
        self.setItem(row, 1, QTableWidgetItem(value))
        self.setItem(row, 2, QTableWidgetItem(normal_range))
    
    def update_parameter(self, name, value, format_str="{:.2f}"):
        """Update a parameter's value in the table."""
        for row in range(self.rowCount()):
            if self.item(row, 0).text() == name:
                formatted_value = format_str.format(value) if isinstance(value, (int, float)) else str(value)
                self.setItem(row, 1, QTableWidgetItem(formatted_value))
                
                # Highlight abnormal values in red
                normal_range = self.item(row, 2).text()
                if self._is_outside_normal_range(value, normal_range):
                    self.item(row, 1).setForeground(QBrush(QColor("#e74c3c")))
                else:
                    self.item(row, 1).setForeground(QBrush(QColor("#27ae60")))
                break
    
    def _is_outside_normal_range(self, value, range_str):
        """Check if a value is outside the normal range."""
        try:
            if not isinstance(value, (int, float)):
                return False
                
            if range_str.startswith("<"):
                # Format: "<10" means value should be less than 10
                threshold = float(range_str[1:])
                return value >= threshold
            elif "-" in range_str:
                # Format: "0.5-0.8" means value should be between 0.5 and 0.8
                lower, upper = map(float, range_str.split("-"))
                return value < lower or value > upper
            
            return False
        except:
            return False


class GaitAnalysisWidget(QGroupBox):
    """Widget for displaying gait analysis data."""
    
    def __init__(self, parent=None):
        """Initialize the gait analysis widget."""
        super().__init__("Gait Analysis", parent)
        
        # Set size policy to ensure widget expands to fit content
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)  # Reduce spacing between elements
        main_layout.setContentsMargins(9, 9, 9, 9)  # Reduce margins slightly
        
        # Recording indicator
        self.recording_indicator = QLabel("Recording Status: Inactive")
        self.recording_indicator.setStyleSheet("color: gray; font-weight: bold;")
        self.recording_indicator.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.recording_indicator)
        
        # Create tabs for different parameter sets
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        
        # Temporal parameters tab
        temporal_tab = QWidget()
        temporal_layout = QVBoxLayout(temporal_tab)
        temporal_layout.setContentsMargins(6, 6, 6, 6)  # Reduce margins
        temporal_layout.setSpacing(4)  # Reduce spacing
        
        # Create a wrapper widget for the parameters table
        self.temporal_table = GaitParametersTable()
        temporal_layout.addWidget(self.temporal_table)
        
        self.tabs.addTab(temporal_tab, "Parameters")
        
        # Visualizations tab with more compact layout
        viz_tab = QWidget()
        viz_layout = QVBoxLayout(viz_tab)
        viz_layout.setContentsMargins(6, 6, 6, 6)  # Reduce margins
        viz_layout.setSpacing(4)  # Reduce spacing
        
        # Add gait cycle visualizer with reduced height
        self.gait_cycle_viz = GaitCycleVisualizerWidget()
        self.gait_cycle_viz.setMinimumHeight(80)  # Reduced from 100
        viz_layout.addWidget(self.gait_cycle_viz)
        
        # Add symmetry visualization with compact layout
        symmetry_layout = QHBoxLayout()
        symmetry_layout.setSpacing(4)  # Reduce spacing
        
        self.symmetry_label = QLabel("Gait Symmetry:")
        self.symmetry_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        symmetry_layout.addWidget(self.symmetry_label)
        
        self.symmetry_bar = QProgressBar()
        self.symmetry_bar.setRange(0, 100)
        self.symmetry_bar.setValue(90)
        self.symmetry_bar.setFormat("%v%")
        self.symmetry_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
            }
        """)
        symmetry_layout.addWidget(self.symmetry_bar, 2)
        
        viz_layout.addLayout(symmetry_layout)
        
        # Add entrainment visualization with compact layout
        entrainment_layout = QHBoxLayout()
        entrainment_layout.setSpacing(4)  # Reduce spacing
        
        self.entrainment_label = QLabel("Entrainment:")
        self.entrainment_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        entrainment_layout.addWidget(self.entrainment_label)
        
        self.entrainment_bar = QProgressBar()
        self.entrainment_bar.setRange(0, 100)
        self.entrainment_bar.setValue(0)
        self.entrainment_bar.setFormat("%v%")
        self.entrainment_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)
        entrainment_layout.addWidget(self.entrainment_bar, 2)
        
        viz_layout.addLayout(entrainment_layout)
        viz_layout.addStretch()
        
        self.tabs.addTab(viz_tab, "Visualization")
        
        # Add tabs to main layout - use less space compared to before
        main_layout.addWidget(self.tabs, 5)
        
        # Add controls for gait analysis - reduce height by using a more compact layout
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(4)  # Reduce button spacing
        
        # Use smaller buttons
        button_style = "padding: 4px 8px;"  # Reduce padding
        
        self.calibrate_button = QPushButton("Calibrate")
        self.calibrate_button.setToolTip("Calibrate stride length measurement")
        self.calibrate_button.setStyleSheet(button_style)
        controls_layout.addWidget(self.calibrate_button)
        
        self.reset_button = QPushButton("Reset Analysis")
        self.reset_button.setToolTip("Reset all gait analysis parameters")
        self.reset_button.setStyleSheet(button_style)
        controls_layout.addWidget(self.reset_button)
        
        self.export_button = QPushButton("Export Data")
        self.export_button.setToolTip("Export gait analysis data to CSV")
        self.export_button.setStyleSheet(button_style)
        controls_layout.addWidget(self.export_button)
        
        main_layout.addLayout(controls_layout)
        
        # Status label
        self.status_label = QLabel("Ready for gait analysis")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #3498db; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
        # Initialize update counter
        self.update_counter = 0
        
        # Placeholder keypoint and gait data for demo
        self.keypoints = {}
        self.gait_data = {}
        
        # Recording flag
        self.is_recording = False
    
    def set_recording_status(self, is_recording: bool):
        """
        Set the recording status indicator.
        
        Args:
            is_recording: Whether recording is active
        """
        self.is_recording = is_recording
        
        if is_recording:
            self.recording_indicator.setText("Recording Status: ACTIVE")
            self.recording_indicator.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 14px;")
        else:
            self.recording_indicator.setText("Recording Status: Inactive")
            self.recording_indicator.setStyleSheet("color: gray; font-weight: bold;")
    
    @pyqtSlot(dict, dict)
    def update_gait_data(self, keypoints: Dict, gait_data: Dict):
        """Update the widget with new gait analysis data."""
        try:
            # Update status
            if gait_data.get('is_walking', False):
                self.status_label.setText("Walking detected")
                self.status_label.setStyleSheet("color: #27ae60; font-style: italic;")
            else:
                self.status_label.setText("No walking detected")
                self.status_label.setStyleSheet("color: #e74c3c; font-style: italic;")
            
            # Update parameters table
            self.temporal_table.update_parameter("Cadence (steps/min)", gait_data.get('cadence', 0))
            
            # Stride time calculation (default to 0 if no cadence)
            cadence = gait_data.get('cadence', 0)
            stride_time = 120 / cadence if cadence > 0 else 0  # Two steps per stride, convert to seconds
            self.temporal_table.update_parameter("Stride Time (s)", stride_time)
            
            # Step time (half of stride time)
            self.temporal_table.update_parameter("Step Time (s)", stride_time / 2 if stride_time > 0 else 0)
            
            # Spatial parameters
            self.temporal_table.update_parameter("Stride Length (m)", gait_data.get('stride_length', 0))
            self.temporal_table.update_parameter("Step Length (m)", gait_data.get('stride_length', 0) / 2)  # Approximate
            self.temporal_table.update_parameter("Walking Speed (m/s)", gait_data.get('walking_velocity', 0))
            
            # Phase percentages
            # These are often estimated in real-time systems
            self.temporal_table.update_parameter("Swing Phase (%)", 40)  # Default approximation
            self.temporal_table.update_parameter("Stance Phase (%)", 60)  # Default approximation
            
            # Asymmetry
            if gait_data.get('gait_asymmetry') is not None:
                asymmetry = gait_data.get('gait_asymmetry', 0) * 100  # Convert to percentage
                self.temporal_table.update_parameter("Step Length Asymmetry (%)", asymmetry)
                self.temporal_table.update_parameter("Stance Time Asymmetry (%)", asymmetry)  # Use same value as approximation
                
                # Update symmetry bar (invert asymmetry for symmetry)
                symmetry = max(0, 100 - asymmetry)
                self.symmetry_bar.setValue(int(symmetry))
                
                # Change color based on symmetry level
                if symmetry > 90:
                    self.symmetry_bar.setStyleSheet("QProgressBar::chunk { background-color: #27ae60; }")
                elif symmetry > 70:
                    self.symmetry_bar.setStyleSheet("QProgressBar::chunk { background-color: #f39c12; }")
                else:
                    self.symmetry_bar.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
            
            # Update gait cycle visualization
            left_phase = gait_data.get('left_foot_phase', None)
            right_phase = gait_data.get('right_foot_phase', None)
            
            if left_phase and right_phase:
                self.gait_cycle_viz.set_foot_phases(
                    left_phase.name if hasattr(left_phase, 'name') else str(left_phase),
                    right_phase.name if hasattr(right_phase, 'name') else str(right_phase)
                )
            
            # Estimate position in gait cycle based on step detection
            if gait_data.get('step_detected', False):
                foot = gait_data.get('step_foot', '')
                if foot == 'LEFT':
                    self.gait_cycle_viz.set_cycle_position(0.0)  # Start of cycle
                elif foot == 'RIGHT':
                    self.gait_cycle_viz.set_cycle_position(0.5)  # Mid-cycle
                    
            # Update entrainment if available (only relevant during RAS stimulation)
            if 'entrainment' in gait_data:
                entrainment = gait_data['entrainment'] * 100  # Convert to percentage
                self.entrainment_bar.setValue(int(entrainment))
                
                # Change color based on entrainment level
                if entrainment > 90:
                    self.entrainment_bar.setStyleSheet("QProgressBar::chunk { background-color: #27ae60; }")
                elif entrainment > 70:
                    self.entrainment_bar.setStyleSheet("QProgressBar::chunk { background-color: #f39c12; }")
                else:
                    self.entrainment_bar.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
        
        except Exception as e:
            print(f"Error updating gait data: {e}")
    
    def reset(self):
        """Reset all gait analysis parameters."""
        self.temporal_table.initialize_parameters()
        self.symmetry_bar.setValue(90)
        self.entrainment_bar.setValue(0)
        self.status_label.setText("Analysis reset")
        self.status_label.setStyleSheet("color: #3498db; font-style: italic;") 