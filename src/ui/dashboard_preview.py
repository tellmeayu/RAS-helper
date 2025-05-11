#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAS-helper: Dashboard UI Preview

This module implements a preview version of the dashboard UI for the RAS-helper system.
It includes mock-up widgets and controls for demonstration purposes.
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QComboBox, QSlider, QFrame, QGroupBox,
    QGridLayout, QSpacerItem, QSizePolicy, QTabWidget, QTextEdit,
    QProgressBar, QDial, QSpinBox, QDoubleSpinBox, QCheckBox,
    QStackedWidget, QTableWidget, QTableWidgetItem, QLineEdit,
    QRadioButton, QButtonGroup, QFileDialog, QScrollArea, QToolButton
)
from PyQt5.QtCore import Qt, QSize, QTimer, QRect
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QIcon


class ClinicalAssessmentControls(QGroupBox):
    """Controls specific to Clinical Assessment mode."""
    
    def __init__(self, parent=None):
        """Initialize clinical assessment controls."""
        super().__init__("Clinical Assessment Controls", parent)
        
        layout = QGridLayout(self)
        
        # Assessment protocol selector
        protocol_label = QLabel("Assessment Protocol:")
        protocol_label.setToolTip("Select the type of gait assessment to perform")
        layout.addWidget(protocol_label, 0, 0)
        
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["Standard Gait", "6-Minute Walk", "10m Walk Test", "Timed Up & Go"])
        self.protocol_combo.setToolTip("Standard Gait: Customizable assessment\n"
                                 "6-Minute Walk: Measures distance walked in 6 minutes\n"
                                 "10m Walk Test: Measures time to walk 10 meters\n"
                                 "Timed Up & Go: Assesses mobility, balance and fall risk")
        layout.addWidget(self.protocol_combo, 0, 1)
        
        # Baseline comparison toggle
        baseline_label = QLabel("Compare to Baseline:")
        baseline_label.setToolTip("Enable to compare current assessment with patient's baseline data")
        layout.addWidget(baseline_label, 1, 0)
        
        self.compare_checkbox = QCheckBox()
        self.compare_checkbox.setChecked(True)
        self.compare_checkbox.setToolTip("When checked, results will be compared with previous baseline assessments")
        layout.addWidget(self.compare_checkbox, 1, 1)
        
        # Assessment duration
        self.duration_label = QLabel("Duration (minutes):")
        self.duration_label.setToolTip("Set the duration for Standard Gait assessment (disabled for other protocols)")
        layout.addWidget(self.duration_label, 2, 0)
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 30)
        self.duration_spin.setValue(5)
        self.duration_spin.setToolTip("Duration of assessment recording")
        self.duration_spin.setFocusPolicy(Qt.StrongFocus)
        layout.addWidget(self.duration_spin, 2, 1)
        
        # Control buttons and elapsed time in a compact horizontal layout
        control_layout = QHBoxLayout()
        
        # Elapsed time display - more compact
        self.elapsed_label = QLabel("Elapsed Time:")
        self.elapsed_label.setToolTip("Time elapsed in current assessment")
        control_layout.addWidget(self.elapsed_label)
        
        self.elapsed_time = QLabel("00:00")
        self.elapsed_time.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self.elapsed_time.setToolTip("Current assessment duration")
        control_layout.addWidget(self.elapsed_time)
        
        # Add spacer between time and buttons
        control_layout.addSpacing(10)
        
        # Control buttons in a horizontal layout
        self.record_button = QPushButton("Record Assessment")
        self.record_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.record_button.setToolTip("Start recording the assessment based on selected protocol")
        control_layout.addWidget(self.record_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setStyleSheet("background-color: #f44336; color: white;")
        self.stop_button.setToolTip("Manually stop the current assessment recording")
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        self.save_button = QPushButton("Save Results")
        self.save_button.setToolTip("Save the assessment results to patient record")
        self.save_button.setEnabled(False)
        control_layout.addWidget(self.save_button)
        
        # Add the control layout to the main layout
        layout.addLayout(control_layout, 3, 0, 1, 2)
        
        # Add system status indicators in a 2x2 grid with integrated system log
        self.status_group = QGroupBox("System Status")
        self.status_group.setToolTip("Current system status and log information")
        status_layout = QGridLayout(self.status_group)
        
        # Status indicators in a 2x2 grid
        camera_label = QLabel("Camera:")
        camera_label.setToolTip("Status of the video capture device")
        status_layout.addWidget(camera_label, 0, 0)
        
        camera_status = QLabel("Connected")
        camera_status.setStyleSheet("color: green; font-weight: bold;")
        camera_status.setToolTip("Green: Connected and working properly")
        status_layout.addWidget(camera_status, 0, 1)
        
        pose_label = QLabel("Pose Estimation:")
        pose_label.setToolTip("Status of the pose detection system")
        status_layout.addWidget(pose_label, 1, 0)
        
        pose_status = QLabel("Active")
        pose_status.setStyleSheet("color: green; font-weight: bold;")
        pose_status.setToolTip("Green: MediaPipe pose detection active and tracking")
        status_layout.addWidget(pose_status, 1, 1)
        
        audio_label = QLabel("Audio Output:")
        audio_label.setToolTip("Status of the audio system")
        status_layout.addWidget(audio_label, 0, 2)
        
        audio_status = QLabel("Ready")
        audio_status.setStyleSheet("color: green; font-weight: bold;")
        audio_status.setToolTip("Green: FluidSynth ready for audio playback")
        status_layout.addWidget(audio_status, 0, 3)
        
        entrainment_label = QLabel("Entrainment:")
        entrainment_label.setToolTip("How well the patient is synchronizing with the rhythm")
        status_layout.addWidget(entrainment_label, 1, 2)
        
        entrainment_status = QLabel("85%")
        entrainment_status.setStyleSheet("color: blue; font-weight: bold;")
        entrainment_status.setToolTip("Percentage of steps synchronized with the beat")
        status_layout.addWidget(entrainment_status, 1, 3)
        
        # Set column stretch to make the layout more balanced
        status_layout.setColumnStretch(0, 1)
        status_layout.setColumnStretch(1, 1)
        status_layout.setColumnStretch(2, 1)
        status_layout.setColumnStretch(3, 1)
        
        # Add the status group to the main layout
        layout.addWidget(self.status_group, 4, 0, 1, 2)
        
        # Notes field
        notes_label = QLabel("Assessment Notes:")
        notes_label.setToolTip("Add clinical observations during the assessment")
        layout.addWidget(notes_label, 5, 0)
        
        self.notes_text = QTextEdit()
        self.notes_text.setPlaceholderText("Enter clinical observations here...")
        self.notes_text.setMaximumHeight(100)
        self.notes_text.setToolTip("Record any clinical observations, patient comments, or special circumstances")
        self.notes_text.setFocusPolicy(Qt.StrongFocus)
        layout.addWidget(self.notes_text, 6, 0, 1, 2)


class DetailedMetricsWidget(QGroupBox):
    """Detailed gait metrics for Clinical Assessment mode."""
    
    def __init__(self, parent=None):
        """Initialize detailed metrics widget."""
        super().__init__("Detailed Gait Metrics", parent)
        self.setToolTip("Comprehensive measurement data from gait assessment")
        
        layout = QVBoxLayout(self)
        
        # Tabs for different metric categories
        metrics_tabs = QTabWidget()
        metrics_tabs.setToolTip("Different categories of gait measurements")
        
        # Temporal parameters tab
        temporal_tab = QWidget()
        temporal_layout = QVBoxLayout(temporal_tab)
        
        temporal_table = QTableWidget(4, 3)
        temporal_table.setHorizontalHeaderLabels(["Parameter", "Value", "Normal Range"])
        temporal_table.setToolTip("Time-based gait parameters")
        
        temporal_table.setItem(0, 0, QTableWidgetItem("Cadence (steps/min)"))
        temporal_table.setItem(0, 1, QTableWidgetItem("120"))
        temporal_table.setItem(0, 2, QTableWidgetItem("100-130"))
        
        temporal_table.setItem(1, 0, QTableWidgetItem("Step Time (s)"))
        temporal_table.setItem(1, 1, QTableWidgetItem("0.5"))
        temporal_table.setItem(1, 2, QTableWidgetItem("0.4-0.6"))
        
        temporal_table.setItem(2, 0, QTableWidgetItem("Stance Phase (%)"))
        temporal_table.setItem(2, 1, QTableWidgetItem("62"))
        temporal_table.setItem(2, 2, QTableWidgetItem("60-65"))
        
        temporal_table.setItem(3, 0, QTableWidgetItem("Swing Phase (%)"))
        temporal_table.setItem(3, 1, QTableWidgetItem("38"))
        temporal_table.setItem(3, 2, QTableWidgetItem("35-40"))
        
        temporal_layout.addWidget(temporal_table)
        
        # Spatial parameters tab
        spatial_tab = QWidget()
        spatial_layout = QVBoxLayout(spatial_tab)
        
        spatial_table = QTableWidget(3, 3)
        spatial_table.setHorizontalHeaderLabels(["Parameter", "Value", "Normal Range"])
        spatial_table.setToolTip("Distance-based gait parameters")
        
        spatial_table.setItem(0, 0, QTableWidgetItem("Step Length (m)"))
        spatial_table.setItem(0, 1, QTableWidgetItem("0.65"))
        spatial_table.setItem(0, 2, QTableWidgetItem("0.6-0.8"))
        
        spatial_table.setItem(1, 0, QTableWidgetItem("Stride Length (m)"))
        spatial_table.setItem(1, 1, QTableWidgetItem("1.3"))
        spatial_table.setItem(1, 2, QTableWidgetItem("1.2-1.6"))
        
        spatial_table.setItem(2, 0, QTableWidgetItem("Step Width (m)"))
        spatial_table.setItem(2, 1, QTableWidgetItem("0.16"))
        spatial_table.setItem(2, 2, QTableWidgetItem("0.12-0.2"))
        
        spatial_layout.addWidget(spatial_table)
        
        # Asymmetry tab
        asymmetry_tab = QWidget()
        asymmetry_layout = QVBoxLayout(asymmetry_tab)
        
        asymmetry_table = QTableWidget(3, 3)
        asymmetry_table.setHorizontalHeaderLabels(["Parameter", "L/R Ratio", "Asymmetry (%)"])
        asymmetry_table.setToolTip("Comparison between left and right sides")
        
        asymmetry_table.setItem(0, 0, QTableWidgetItem("Step Length"))
        asymmetry_table.setItem(0, 1, QTableWidgetItem("0.92"))
        asymmetry_table.setItem(0, 2, QTableWidgetItem("8%"))
        
        asymmetry_table.setItem(1, 0, QTableWidgetItem("Stance Time"))
        asymmetry_table.setItem(1, 1, QTableWidgetItem("0.95"))
        asymmetry_table.setItem(1, 2, QTableWidgetItem("5%"))
        
        asymmetry_table.setItem(2, 0, QTableWidgetItem("Swing Time"))
        asymmetry_table.setItem(2, 1, QTableWidgetItem("0.9"))
        asymmetry_table.setItem(2, 2, QTableWidgetItem("10%"))
        
        asymmetry_layout.addWidget(asymmetry_table)
        
        # Add tabs to tab widget
        metrics_tabs.addTab(temporal_tab, "Temporal")
        metrics_tabs.addTab(spatial_tab, "Spatial")
        metrics_tabs.addTab(asymmetry_tab, "Asymmetry")
        
        layout.addWidget(metrics_tabs)
        
        # Add export buttons
        button_layout = QHBoxLayout()
        
        export_csv = QPushButton("Export to CSV")
        export_csv.setToolTip("Export raw measurement data to CSV file for further analysis")
        button_layout.addWidget(export_csv)
        
        generate_report = QPushButton("Generate Report")
        generate_report.setToolTip("Create a clinical report with gait analysis results and interpretation")
        button_layout.addWidget(generate_report)
        
        layout.addLayout(button_layout)


class ColorBox(QWidget):
    """A colored rectangle widget for placeholder purposes."""
    
    def __init__(self, color, text="", parent=None):
        """Initialize with color and optional text."""
        super().__init__(parent)
        self.color = color
        self.text = text
        self.setMinimumSize(100, 70)
    
    def paintEvent(self, event):
        """Custom paint event to display color and text."""
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor(self.color))
        
        if self.text:
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            painter.drawText(event.rect(), Qt.AlignCenter, self.text)


class VideoFeedPlaceholder(QFrame):
    """A placeholder for the video feed with 16:9 aspect ratio."""
    
    def __init__(self, parent=None):
        """Initialize the video feed placeholder."""
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setStyleSheet("background-color: #222; color: white;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel("Video Feed (16:9)")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(self.label)
        
        # Mock timer to simulate video feed
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_placeholder)
        self.timer.start(1000)  # Update every second
        self.frame_count = 0
    
    def update_placeholder(self):
        """Update the placeholder with a frame counter."""
        self.frame_count += 1
        self.label.setText(f"Video Feed (16:9)\nFrame: {self.frame_count}")
    
    def sizeHint(self):
        """Return a size with 16:9 aspect ratio."""
        width = self.width()
        return QSize(width, int(width * 9 / 16))
    
    def resizeEvent(self, event):
        """Handle resize event to maintain aspect ratio."""
        # Allow width to be determined by layout
        # Set height based on width to maintain 16:9 ratio
        new_width = event.size().width()
        self.setMinimumHeight(int(new_width * 9 / 16))
        self.setMaximumHeight(int(new_width * 9 / 16))
        super().resizeEvent(event)


class RehabilitationControls(QGroupBox):
    """Simplified controls for Rehabilitation Training mode."""
    
    def __init__(self, parent=None):
        """Initialize rehabilitation controls."""
        super().__init__("Rehabilitation Training", parent)
        self.setToolTip("Controls for patient rehabilitation training session")
        
        layout = QVBoxLayout(self)
        
        # Large status indicator
        self.status_label = QLabel("Ready to Begin Training")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.status_label.setStyleSheet("color: #2196F3;")
        self.status_label.setToolTip("Current status of the training session")
        layout.addWidget(self.status_label)
        
        # Add protocol selector
        protocol_layout = QHBoxLayout()
        protocol_label = QLabel("Protocol:")
        protocol_label.setToolTip("Type of rehabilitation training")
        protocol_layout.addWidget(protocol_label)
        
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["Standard Training", "Obstacle Course", "Balance Training", "Endurance Training"])
        self.protocol_combo.setToolTip("Select the training protocol")
        protocol_layout.addWidget(self.protocol_combo)
        layout.addLayout(protocol_layout)
        
        # Add duration control
        duration_layout = QHBoxLayout()
        duration_label = QLabel("Duration:")
        duration_label.setToolTip("Length of training session")
        duration_layout.addWidget(duration_label)
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 60)
        self.duration_spin.setValue(15)
        self.duration_spin.setSuffix(" min")
        self.duration_spin.setToolTip("Set the duration of the training session")
        duration_layout.addWidget(self.duration_spin)
        
        # Add difficulty control
        difficulty_layout = QHBoxLayout()
        difficulty_label = QLabel("Difficulty:")
        difficulty_label.setToolTip("Training difficulty level")
        difficulty_layout.addWidget(difficulty_label)
        
        self.difficulty_slider = QSlider(Qt.Horizontal)
        self.difficulty_slider.setRange(1, 10)
        self.difficulty_slider.setValue(5)
        self.difficulty_slider.setToolTip("Set the difficulty level of the training")
        difficulty_layout.addWidget(self.difficulty_slider)
        
        difficulty_value = QLabel("5")
        difficulty_value.setMinimumWidth(20)
        difficulty_layout.addWidget(difficulty_value)
        layout.addLayout(difficulty_layout)
        
        # Add feedback options
        feedback_layout = QHBoxLayout()
        self.audio_checkbox = QCheckBox("Audio Feedback")
        self.audio_checkbox.setChecked(True)
        self.audio_checkbox.setToolTip("Enable audio feedback during training")
        feedback_layout.addWidget(self.audio_checkbox)
        
        self.visual_checkbox = QCheckBox("Visual Feedback")
        self.visual_checkbox.setChecked(True)
        self.visual_checkbox.setToolTip("Enable visual feedback during training")
        feedback_layout.addWidget(self.visual_checkbox)
        layout.addLayout(feedback_layout)
        
        # Add music selection group
        music_group = QGroupBox("Music Selection")
        music_group_layout = QVBoxLayout(music_group)
        
        # Add rhythmic style selection (previously rhythmic character, now first)
        rhythm_layout = QHBoxLayout()
        rhythm_label = QLabel("Rhythmic Style:")
        rhythm_label.setStyleSheet("font-weight: bold;")
        rhythm_layout.addWidget(rhythm_label)
        
        self.rhythm_combo = QComboBox()
        self.rhythm_combo.addItems([
            "All Types", "Clear & Steady Beat", "Moderately Rhythmic",
            "Groovy & Syncopated", "Smooth & Flowing"
        ])
        self.rhythm_combo.setToolTip("Select the rhythmic style of the music")
        self.rhythm_combo.setStyleSheet("padding: 5px;")
        rhythm_layout.addWidget(self.rhythm_combo)
        music_group_layout.addLayout(rhythm_layout)
        
        # Add instrument preference selection (new, second position)
        instrument_layout = QHBoxLayout()
        instrument_label = QLabel("Instrument Preference:")
        instrument_label.setStyleSheet("font-weight: bold;")
        instrument_layout.addWidget(instrument_label)
        
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems([
            "All Instruments", "Piano", "Guitar", "Strings", 
            "Percussion", "Woodwinds", "Brass", "Electronic"
        ])
        self.instrument_combo.setToolTip("Select preferred instruments for RAS")
        self.instrument_combo.setStyleSheet("padding: 5px;")
        instrument_layout.addWidget(self.instrument_combo)
        music_group_layout.addLayout(instrument_layout)
        
        # Add mood selection (replaces genre selection)
        mood_layout = QHBoxLayout()
        mood_label = QLabel("Mood:")
        mood_label.setStyleSheet("font-weight: bold;")
        mood_layout.addWidget(mood_label)
        
        self.mood_combo = QComboBox()
        self.mood_combo.addItems([
            "All Moods", "Energetic", "Relaxed", "Uplifting", 
            "Melancholic", "Cheerful", "Peaceful", "Intense", "Chill"
        ])
        self.mood_combo.setToolTip("Select music mood for RAS")
        self.mood_combo.setStyleSheet("padding: 5px;")
        mood_layout.addWidget(self.mood_combo)
        music_group_layout.addLayout(mood_layout)
        
        # Add music selection button
        music_buttons_layout = QHBoxLayout()
        
        self.select_music_button = QPushButton("Browse Music")
        self.select_music_button.setToolTip("Browse and select music from the processed dataset")
        self.select_music_button.setStyleSheet("background-color: #3498db; color: white; padding: 8px;")
        music_buttons_layout.addWidget(self.select_music_button)
        
        # Add analyze button
        self.analyze_button = QPushButton("Analyze Rhythm")
        self.analyze_button.setToolTip("Open the rhythm analysis window for the selected music")
        self.analyze_button.setEnabled(False)  # Initially disabled until music is selected
        self.analyze_button.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px;")
        music_buttons_layout.addWidget(self.analyze_button)
        
        music_group_layout.addLayout(music_buttons_layout)
        
        # Add currently selected music display
        music_label_layout = QHBoxLayout()
        music_label_header = QLabel("Selected Music:")
        music_label_header.setStyleSheet("font-weight: bold;")
        music_label_layout.addWidget(music_label_header)
        
        self.music_label = QLabel("No music selected")
        self.music_label.setToolTip("Currently selected music file")
        self.music_label.setStyleSheet("font-style: italic; color: #7f8c8d;")
        music_label_layout.addWidget(self.music_label)
        
        music_group_layout.addLayout(music_label_layout)
        layout.addWidget(music_group)
        
        # Simplified tempo control with larger elements
        tempo_layout = QHBoxLayout()
        
        tempo_label = QLabel("Music Tempo:")
        tempo_label.setToolTip("Speed of the rhythmic cues (beats per minute)")
        tempo_layout.addWidget(tempo_label)
        
        self.tempo_slider = QSlider(Qt.Horizontal)
        self.tempo_slider.setRange(60, 180)
        self.tempo_slider.setValue(120)
        self.tempo_slider.setMinimumHeight(40)
        self.tempo_slider.setToolTip("Adjust tempo to match patient's target cadence")
        tempo_layout.addWidget(self.tempo_slider)
        
        self.tempo_value = QLabel("120 BPM")
        self.tempo_value.setMinimumWidth(80)
        self.tempo_value.setToolTip("Current tempo in beats per minute")
        tempo_layout.addWidget(self.tempo_value)
        
        layout.addLayout(tempo_layout)
        
        # Large control buttons
        self.button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("START TRAINING")
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px; font-weight: bold; padding: 12px;")
        self.start_button.setMinimumHeight(60)
        self.start_button.setToolTip("Begin the training session with selected parameters")
        
        self.stop_button = QPushButton("STOP")
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; font-size: 16px; font-weight: bold; padding: 12px;")
        self.stop_button.setMinimumHeight(60)
        self.stop_button.setToolTip("End the current training session")
        self.stop_button.setEnabled(False)
        
        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        
        layout.addLayout(self.button_layout)
        
        # Timer display
        timer_layout = QHBoxLayout()
        
        timer_label = QLabel("Session Time:")
        timer_label.setToolTip("Duration of current training session")
        timer_layout.addWidget(timer_label)
        
        self.timer_display = QLabel("00:00")
        self.timer_display.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.timer_display.setAlignment(Qt.AlignCenter)
        self.timer_display.setToolTip("Elapsed time in current session")
        timer_layout.addWidget(self.timer_display)
        
        layout.addLayout(timer_layout)


class ProgressTrackingWidget(QGroupBox):
    """Progress tracking for Rehabilitation Training mode."""
    
    def __init__(self, parent=None):
        """Initialize progress tracking widget."""
        super().__init__("Your Progress", parent)
        self.setToolTip("Visual representation of patient's progress toward therapy goals")
        
        layout = QVBoxLayout(self)
        
        # Today's session progress
        today_group = QGroupBox("Today's Session")
        today_group.setToolTip("Progress in the current therapy session")
        today_layout = QVBoxLayout(today_group)
        
        # Goals visualization
        goals_label = QLabel("Goals Progress:")
        goals_label.setToolTip("Progress toward today's therapy targets")
        today_layout.addWidget(goals_label)
        
        goals_layout = QGridLayout()
        
        cadence_label = QLabel("Cadence Goal:")
        cadence_label.setToolTip("Target steps per minute")
        goals_layout.addWidget(cadence_label, 0, 0)
        
        cadence_progress = QProgressBar()
        cadence_progress.setValue(75)
        cadence_progress.setFormat("75% (90/120 steps/min)")
        cadence_progress.setToolTip("Current cadence relative to target")
        goals_layout.addWidget(cadence_progress, 0, 1)
        
        duration_label = QLabel("Duration Goal:")
        duration_label.setToolTip("Target session duration")
        goals_layout.addWidget(duration_label, 1, 0)
        
        duration_progress = QProgressBar()
        duration_progress.setValue(40)
        duration_progress.setFormat("40% (8/20 minutes)")
        duration_progress.setToolTip("Time elapsed toward target duration")
        goals_layout.addWidget(duration_progress, 1, 1)
        
        entrainment_label = QLabel("Entrainment:")
        entrainment_label.setToolTip("How well patient is synchronizing with the rhythm")
        goals_layout.addWidget(entrainment_label, 2, 0)
        
        entrainment_progress = QProgressBar()
        entrainment_progress.setValue(85)
        entrainment_progress.setFormat("85%")
        entrainment_progress.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        entrainment_progress.setToolTip("Percentage of steps that match the rhythm")
        goals_layout.addWidget(entrainment_progress, 2, 1)
        
        today_layout.addLayout(goals_layout)
        
        layout.addWidget(today_group)
        
        # Weekly progress
        week_group = QGroupBox("Weekly Progress")
        week_group.setToolTip("Summary of all sessions this week")
        week_layout = QVBoxLayout(week_group)
        
        sessions_label = QLabel("Sessions Completed: 3 of 5")
        sessions_label.setToolTip("Number of sessions completed this week")
        week_layout.addWidget(sessions_label)
        
        # Mock bar chart for sessions
        sessions_chart = ColorBox("#3F51B5", "Mock Weekly Sessions Chart")
        sessions_chart.setMinimumHeight(100)
        sessions_chart.setToolTip("Visual chart showing progress across weekly sessions")
        week_layout.addWidget(sessions_chart)
        
        layout.addWidget(week_group)
        
        # Achievements section
        achievements = QGroupBox("Your Achievements")
        achievements.setToolTip("Milestones and goals reached")
        achievements_layout = QVBoxLayout(achievements)
        
        streak_achievement = QLabel("🏆 3 Day Streak")
        streak_achievement.setToolTip("Consecutive days with completed sessions")
        achievements_layout.addWidget(streak_achievement)
        
        cadence_achievement = QLabel("🎯 Target Cadence Reached")
        cadence_achievement.setToolTip("Successfully reached the target cadence")
        achievements_layout.addWidget(cadence_achievement)
        
        sessions_achievement = QLabel("⭐ 10 Sessions Completed")
        sessions_achievement.setToolTip("Completed 10 rehabilitation sessions total")
        achievements_layout.addWidget(sessions_achievement)
        
        layout.addWidget(achievements)
        
        # Motivational message
        motivation = QLabel("Great progress! You're getting closer to your goal every day.")
        motivation.setStyleSheet("font-style: italic; color: #2196F3;")
        motivation.setWordWrap(True)
        motivation.setToolTip("Encouragement based on progress")
        layout.addWidget(motivation)


class GaitAnalysisWidget(QFrame):
    """A placeholder for the gait analysis visualization."""
    
    def __init__(self, parent=None):
        """Initialize the gait analysis widget."""
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setStyleSheet("background-color: #2a3990; color: white;")
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Gait Analysis")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Mock visualization
        metrics = QHBoxLayout()
        
        cadence = QVBoxLayout()
        cadence.addWidget(QLabel("Cadence (steps/min)"))
        cadence_value = QLabel("120")
        cadence_value.setFont(QFont("Arial", 14, QFont.Bold))
        cadence_value.setAlignment(Qt.AlignCenter)
        cadence.addWidget(cadence_value)
        metrics.addLayout(cadence)
        
        stride = QVBoxLayout()
        stride.addWidget(QLabel("Stride Length (m)"))
        stride_value = QLabel("0.65")
        stride_value.setFont(QFont("Arial", 14, QFont.Bold))
        stride_value.setAlignment(Qt.AlignCenter)
        stride.addWidget(stride_value)
        metrics.addLayout(stride)
        
        symmetry = QVBoxLayout()
        symmetry.addWidget(QLabel("Symmetry (%)"))
        symmetry_value = QLabel("92%")
        symmetry_value.setFont(QFont("Arial", 14, QFont.Bold))
        symmetry_value.setAlignment(Qt.AlignCenter)
        symmetry.addWidget(symmetry_value)
        metrics.addLayout(symmetry)
        
        layout.addLayout(metrics)
        
        # Progress visualization
        layout.addWidget(QLabel("Progress:"))
        progress_bar = QProgressBar()
        progress_bar.setValue(75)
        layout.addWidget(progress_bar)


class RASControlWidget(QGroupBox):
    """Controls for RAS parameters."""
    
    def __init__(self, parent=None):
        """Initialize the RAS control widget."""
        super().__init__("RAS Controls", parent)
        self.setToolTip("Controls for Rhythmic Auditory Stimulation parameters")
        
        layout = QGridLayout(self)
        
        # Tempo controls
        tempo_label = QLabel("Base Tempo (BPM):")
        tempo_label.setToolTip("Base speed of rhythmic cues in beats per minute")
        layout.addWidget(tempo_label, 0, 0)
        
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(60, 180)
        self.bpm_spin.setValue(120)
        self.bpm_spin.setToolTip("Adjust the base tempo of rhythmic cues")
        layout.addWidget(self.bpm_spin, 0, 1)
        
        # Adaptation mode
        adaptation_label = QLabel("Adaptation Mode:")
        adaptation_label.setToolTip("How the system adjusts tempo to match the patient")
        layout.addWidget(adaptation_label, 1, 0)
        
        self.adaptation_combo = QComboBox()
        self.adaptation_combo.addItems(["None", "Fixed", "Adaptive", "SLICE"])
        self.adaptation_combo.setToolTip("None: No adaptation\n"
                                   "Fixed: Predetermined changes\n"
                                   "Adaptive: Gradually adjusts to patient\n"
                                   "SLICE: Advanced algorithm for gait rehabilitation")
        layout.addWidget(self.adaptation_combo, 1, 1)
        
        # Adjustments
        adjustment_label = QLabel("Adjustment (%):")
        adjustment_label.setToolTip("Maximum percentage of tempo adjustment")
        layout.addWidget(adjustment_label, 2, 0)
        
        self.adjustment_slider = QSlider(Qt.Horizontal)
        self.adjustment_slider.setRange(0, 20)
        self.adjustment_slider.setValue(10)
        self.adjustment_slider.setToolTip("Controls how much the tempo can change from baseline")
        layout.addWidget(self.adjustment_slider, 2, 1)
        
        # Sound selection
        sound_label = QLabel("Sound Type:")
        sound_label.setToolTip("Type of auditory stimulation")
        layout.addWidget(sound_label, 3, 0)
        
        self.sound_combo = QComboBox()
        self.sound_combo.addItems(["Metronome", "Drum Beat", "Music Track 1", "Music Track 2"])
        self.sound_combo.setToolTip("Select the type of sound for rhythmic stimulation")
        layout.addWidget(self.sound_combo, 3, 1)
        
        # Duration spinner
        duration_label = QLabel("Duration:")
        duration_label.setToolTip("Set the duration of the RAS session")
        layout.addWidget(duration_label, 4, 0)
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 60)
        self.duration_spin.setValue(10)
        self.duration_spin.setSuffix(" min")
        self.duration_spin.setToolTip("Set the duration of the RAS session")
        layout.addWidget(self.duration_spin, 4, 1)
        
        # Adaptive checkbox
        self.adaptive_checkbox = QCheckBox("Adaptive Mode")
        self.adaptive_checkbox.setChecked(True)
        self.adaptive_checkbox.setToolTip("Enable adaptive tempo adjustment")
        layout.addWidget(self.adaptive_checkbox, 5, 0, 1, 2)
        
        # Volume slider
        volume_label = QLabel("Volume:")
        volume_label.setToolTip("Adjust the volume of the audio")
        layout.addWidget(volume_label, 6, 0)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setToolTip("Adjust the volume of the audio")
        layout.addWidget(self.volume_slider, 6, 1)
        
        # Add music selection controls
        self._add_music_selection_controls(layout)
        
        # Add synchronization control frame
        self.sync_frame = QFrame()
        self.sync_frame.setFrameShape(QFrame.StyledPanel)
        self.sync_frame.setVisible(False)  # Initially hidden until RAS starts
        sync_layout = QVBoxLayout(self.sync_frame)
        
        # Add gait data display
        self.gait_data_label = QLabel("No gait data available")
        self.gait_data_label.setAlignment(Qt.AlignCenter)
        sync_layout.addWidget(self.gait_data_label)
        
        # Add confirmation buttons
        confirm_layout = QHBoxLayout()
        
        self.confirm_button = QPushButton("Confirm Tempo")
        self.confirm_button.setToolTip("Use detected cadence as music tempo")
        self.confirm_button.setEnabled(False)
        confirm_layout.addWidget(self.confirm_button)
        
        self.modify_button = QPushButton("Modify")
        self.modify_button.setToolTip("Modify detected cadence before confirming")
        self.modify_button.setEnabled(False)
        confirm_layout.addWidget(self.modify_button)
        
        sync_layout.addLayout(confirm_layout)
        
        # Add adjustment controls
        adjust_layout = QHBoxLayout()
        
        self.decrease_button = QPushButton("-10%")
        self.decrease_button.setToolTip("Decrease tempo by 10%")
        self.decrease_button.setEnabled(False)
        adjust_layout.addWidget(self.decrease_button)
        
        self.increase_button = QPushButton("+10%")
        self.increase_button.setToolTip("Increase tempo by 10%")
        self.increase_button.setEnabled(False)
        adjust_layout.addWidget(self.increase_button)
        
        sync_layout.addLayout(adjust_layout)
        
        # Add playback control buttons
        playback_layout = QHBoxLayout()
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.setToolTip("Pause music playback")
        self.pause_button.setEnabled(False)
        playback_layout.addWidget(self.pause_button)
        
        self.resume_button = QPushButton("Resume")
        self.resume_button.setToolTip("Resume music playback")
        self.resume_button.setEnabled(False)
        playback_layout.addWidget(self.resume_button)
        
        sync_layout.addLayout(playback_layout)
        
        # Add sync status indicator
        self.status_label = QLabel("Status: IDLE")
        self.status_label.setAlignment(Qt.AlignCenter)
        sync_layout.addWidget(self.status_label)
        
        # Add frame to main layout
        row_count = layout.rowCount()
        layout.addWidget(self.sync_frame, row_count, 0, 1, 2)
        
        # Control buttons
        self.button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start RAS")
        self.start_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.start_button.setToolTip("Begin rhythmic auditory stimulation")
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setStyleSheet("background-color: #f44336; color: white;")
        self.stop_button.setToolTip("Stop the current stimulation")
        self.stop_button.setEnabled(False)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Reset all parameters to default values")
        
        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.reset_button)
        
        layout.addLayout(self.button_layout, layout.rowCount(), 0, 1, 2)
    
    def _add_music_selection_controls(self, grid_layout):
        """
        Add music selection controls to the RAS widget.
        
        Args:
            grid_layout: Grid layout to add controls to
        """
        # Calculate the next row for adding new controls
        row = grid_layout.rowCount()
        
        # Add music selection label
        grid_layout.addWidget(QLabel("Music Selection:"), row, 0)
        
        # Add music selection button
        self.music_button = QPushButton("Browse Music...")
        self.music_button.setToolTip("Browse and select music from the categorized dataset")
        grid_layout.addWidget(self.music_button, row, 1)
        
        # Add rhythmic style filter (previously rhythm character, now first)
        row += 1
        grid_layout.addWidget(QLabel("Rhythmic Style:"), row, 0)
        
        self.rhythm_combo = QComboBox()
        self.rhythm_combo.addItems([
            "All Types", "Clear & Steady Beat", "Moderately Rhythmic",
            "Groovy & Syncopated", "Smooth & Flowing"
        ])
        self.rhythm_combo.setToolTip("Filter music by rhythmic style")
        grid_layout.addWidget(self.rhythm_combo, row, 1)
        
        # Add instrument preference (new, second position)
        row += 1
        grid_layout.addWidget(QLabel("Instrument Preference:"), row, 0)
        
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems([
            "All Instruments", "Piano", "Guitar", "Strings", 
            "Percussion", "Woodwinds", "Brass", "Electronic"
        ])
        self.instrument_combo.setToolTip("Filter music by preferred instruments")
        grid_layout.addWidget(self.instrument_combo, row, 1)
        
        # Add mood filter (replaces genre filter)
        row += 1
        grid_layout.addWidget(QLabel("Mood:"), row, 0)
        
        self.mood_combo = QComboBox()
        self.mood_combo.addItems([
            "All Moods", "Energetic", "Relaxed", "Uplifting", 
            "Melancholic", "Cheerful", "Peaceful", "Intense", "Chill"
        ])
        self.mood_combo.setToolTip("Filter music by mood")
        grid_layout.addWidget(self.mood_combo, row, 1)
        
        # Add currently selected music display
        row += 1
        grid_layout.addWidget(QLabel("Current Music:"), row, 0)
        
        self.selected_music_label = QLabel("No music selected")
        self.selected_music_label.setToolTip("Currently selected music file")
        self.selected_music_label.setWordWrap(True)
        grid_layout.addWidget(self.selected_music_label, row, 1)
        
        # Add analyze button
        row += 1
        self.analyze_button = QPushButton("Analyze Rhythm")
        self.analyze_button.setToolTip("Open detailed rhythm analysis for selected music")
        self.analyze_button.setEnabled(False)  # Initially disabled
        grid_layout.addWidget(self.analyze_button, row, 0, 1, 2)


class ResearchControlsWidget(QGroupBox):
    """Advanced controls for Research Mode."""
    
    def __init__(self, parent=None):
        """Initialize research controls widget."""
        super().__init__("Advanced RAS Parameters", parent)
        self.setToolTip("Detailed control panel for research experiments with advanced parameters")
        
        layout = QGridLayout(self)
        
        # Advanced tempo controls with fine adjustments
        tempo_label = QLabel("Base Tempo (BPM):")
        tempo_label.setToolTip("Base tempo for rhythmic cues with precise control")
        layout.addWidget(tempo_label, 0, 0)
        
        tempo_layout = QHBoxLayout()
        
        tempo_spin = QDoubleSpinBox()
        tempo_spin.setRange(40.0, 200.0)
        tempo_spin.setValue(120.0)
        tempo_spin.setDecimals(1)
        tempo_spin.setSingleStep(0.1)
        tempo_spin.setToolTip("Set precise tempo value with decimal precision")
        tempo_layout.addWidget(tempo_spin)
        
        fine_adjust_button = QPushButton("Fine Adjust")
        fine_adjust_button.setToolTip("Open dialog for micro-adjustments to tempo")
        tempo_layout.addWidget(fine_adjust_button)
        
        layout.addLayout(tempo_layout, 0, 1)
        
        # Algorithm selection with advanced options
        algorithm_label = QLabel("Algorithm:")
        algorithm_label.setToolTip("Select the adaptation algorithm for rhythmic stimulation")
        layout.addWidget(algorithm_label, 1, 0)
        
        algorithm_combo = QComboBox()
        algorithm_combo.addItems([
            "Fixed Tempo", 
            "Linear Adaptation", 
            "Exponential Adaptation", 
            "SLICE", 
            "Custom Algorithm..."
        ])
        algorithm_combo.setToolTip("Fixed: No adaptation\n"
                                  "Linear: Constant rate adaptation\n"
                                  "Exponential: Variable rate adaptation\n"
                                  "SLICE: Sophisticated adaptation algorithm\n"
                                  "Custom: Define your own algorithm")
        layout.addWidget(algorithm_combo, 1, 1)
        
        # Algorithm parameters
        param_label = QLabel("Parameters:")
        param_label.setToolTip("Algorithm-specific parameters")
        layout.addWidget(param_label, 2, 0)
        
        param_layout = QHBoxLayout()
        
        alpha_label = QLabel("α:")
        alpha_label.setToolTip("Alpha parameter (adaptation rate)")
        param_layout.addWidget(alpha_label)
        
        alpha_spin = QDoubleSpinBox()
        alpha_spin.setRange(0.0, 1.0)
        alpha_spin.setValue(0.3)
        alpha_spin.setSingleStep(0.01)
        alpha_spin.setToolTip("Controls adaptation sensitivity (0-1)")
        param_layout.addWidget(alpha_spin)
        
        beta_label = QLabel("β:")
        beta_label.setToolTip("Beta parameter (memory factor)")
        param_layout.addWidget(beta_label)
        
        beta_spin = QDoubleSpinBox()
        beta_spin.setRange(0.0, 1.0)
        beta_spin.setValue(0.7)
        beta_spin.setSingleStep(0.01)
        beta_spin.setToolTip("Controls influence of past data (0-1)")
        param_layout.addWidget(beta_spin)
        
        gamma_label = QLabel("γ:")
        gamma_label.setToolTip("Gamma parameter (scaling factor)")
        param_layout.addWidget(gamma_label)
        
        gamma_spin = QDoubleSpinBox()
        gamma_spin.setRange(0.0, 2.0)
        gamma_spin.setValue(1.0)
        gamma_spin.setSingleStep(0.1)
        gamma_spin.setToolTip("Controls adaptation magnitude (0-2)")
        param_layout.addWidget(gamma_spin)
        
        layout.addLayout(param_layout, 2, 1)
        
        # Advanced audio settings
        audio_label = QLabel("Audio Settings:")
        audio_label.setToolTip("Configure detailed audio parameters")
        layout.addWidget(audio_label, 3, 0)
        
        audio_button = QPushButton("Advanced Audio Configuration...")
        audio_button.setToolTip("Open dialog for detailed audio settings (MIDI, synthesis, etc.)")
        layout.addWidget(audio_button, 3, 1)
        
        # Data collection
        data_label = QLabel("Data Collection:")
        data_label.setToolTip("Settings for experimental data recording")
        layout.addWidget(data_label, 4, 0)
        
        data_layout = QHBoxLayout()
        
        record_checkbox = QCheckBox("Record Raw Data")
        record_checkbox.setChecked(True)
        record_checkbox.setToolTip("Save all raw sensor data during experiment")
        data_layout.addWidget(record_checkbox)
        
        interval_label = QLabel("Interval:")
        interval_label.setToolTip("Sampling interval for data collection")
        data_layout.addWidget(interval_label)
        
        interval_spin = QSpinBox()
        interval_spin.setRange(10, 1000)
        interval_spin.setValue(100)
        interval_spin.setSuffix(" ms")
        interval_spin.setToolTip("Time between data samples (milliseconds)")
        data_layout.addWidget(interval_spin)
        
        layout.addLayout(data_layout, 4, 1)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        start_button = QPushButton("Start Experiment")
        start_button.setStyleSheet("background-color: #4CAF50; color: white;")
        start_button.setToolTip("Begin the experiment with current parameters")
        
        stop_button = QPushButton("Stop")
        stop_button.setStyleSheet("background-color: #f44336; color: white;")
        stop_button.setToolTip("End the current experiment")
        
        export_button = QPushButton("Export Data")
        export_button.setToolTip("Export collected data for analysis")
        
        button_layout.addWidget(start_button)
        button_layout.addWidget(stop_button)
        button_layout.addWidget(export_button)
        
        layout.addLayout(button_layout, 5, 0, 1, 2)


class RawDataWidget(QGroupBox):
    """Raw data view for Research Mode."""
    
    def __init__(self, parent=None):
        """Initialize raw data widget."""
        super().__init__("Real-time Data Stream", parent)
        self.setToolTip("View and analyze raw experimental data in real-time")
        
        layout = QVBoxLayout(self)
        
        # Data type selector
        data_layout = QHBoxLayout()
        
        data_type_label = QLabel("Data Type:")
        data_type_label.setToolTip("Select which type of data to display")
        data_layout.addWidget(data_type_label)
        
        data_combo = QComboBox()
        data_combo.addItems([
            "Gait Temporal Parameters", 
            "Joint Angles", 
            "Acceleration", 
            "Audio Sync Data",
            "All Parameters"
        ])
        data_combo.setToolTip("Choose specific data streams to view")
        data_layout.addWidget(data_combo)
        
        filter_label = QLabel("Filter:")
        filter_label.setToolTip("Apply signal processing filters to the data")
        data_layout.addWidget(filter_label)
        
        filter_combo = QComboBox()
        filter_combo.addItems([
            "None", 
            "Moving Average", 
            "Low Pass", 
            "High Pass",
            "Custom..."
        ])
        filter_combo.setToolTip("None: Raw data\n"
                               "Moving Average: Smooth noise\n"
                               "Low Pass: Remove high frequency noise\n"
                               "High Pass: Remove low frequency drift\n"
                               "Custom: Define custom filters")
        data_layout.addWidget(filter_combo)
        
        layout.addLayout(data_layout)
        
        # Raw data display
        data_text = QTextEdit()
        data_text.setReadOnly(True)
        data_text.setFont(QFont("Courier New", 10))
        data_text.setStyleSheet("background-color: #f0f0f0;")
        data_text.setToolTip("Real-time data stream with selected parameters")
        
        # Sample data
        sample_data = """t=0.00s  cadence=118.2  stride=0.64  angle=12.3  accel=0.98
t=0.10s  cadence=118.5  stride=0.65  angle=13.1  accel=1.05
t=0.20s  cadence=119.0  stride=0.67  angle=14.2  accel=1.12
t=0.30s  cadence=119.2  stride=0.68  angle=15.0  accel=1.15
t=0.40s  cadence=119.5  stride=0.68  angle=15.5  accel=1.10
t=0.50s  cadence=119.8  stride=0.67  angle=15.2  accel=1.05
t=0.60s  cadence=120.0  stride=0.66  angle=14.8  accel=0.98
t=0.70s  cadence=120.2  stride=0.65  angle=14.0  accel=0.92
t=0.80s  cadence=120.3  stride=0.64  angle=13.2  accel=0.88
t=0.90s  cadence=120.5  stride=0.63  angle=12.5  accel=0.85"""
        
        data_text.setText(sample_data)
        layout.addWidget(data_text)
        
        # Visualization options
        viz_layout = QHBoxLayout()
        
        plot_button = QPushButton("Plot Data")
        plot_button.setToolTip("Create visual graph of selected data parameters")
        viz_layout.addWidget(plot_button)
        
        export_button = QPushButton("Export CSV")
        export_button.setToolTip("Save raw data to CSV file for external analysis")
        viz_layout.addWidget(export_button)
        
        clear_button = QPushButton("Clear")
        clear_button.setToolTip("Clear the current data display")
        viz_layout.addWidget(clear_button)
        
        layout.addLayout(viz_layout)
        
        # Protocol editor button
        protocol_button = QPushButton("Protocol Editor")
        protocol_button.setStyleSheet("background-color: #2196F3; color: white;")
        protocol_button.setToolTip("Open the protocol editor to modify experimental parameters")
        layout.addWidget(protocol_button)


class StatusWidget(QGroupBox):
    """Status and information widget."""
    
    def __init__(self, parent=None):
        """Initialize the status widget."""
        super().__init__("System Status", parent)
        self.setToolTip("Current system status and log information")
        
        layout = QVBoxLayout(self)
        
        # Status indicators
        indicators = QGridLayout()
        
        camera_label = QLabel("Camera:")
        camera_label.setToolTip("Status of the video capture device")
        indicators.addWidget(camera_label, 0, 0)
        
        camera_status = QLabel("Connected")
        camera_status.setStyleSheet("color: green; font-weight: bold;")
        camera_status.setToolTip("Green: Connected and working properly")
        indicators.addWidget(camera_status, 0, 1)
        
        pose_label = QLabel("Pose Estimation:")
        pose_label.setToolTip("Status of the pose detection system")
        indicators.addWidget(pose_label, 1, 0)
        
        pose_status = QLabel("Active")
        pose_status.setStyleSheet("color: green; font-weight: bold;")
        pose_status.setToolTip("Green: MediaPipe pose detection active and tracking")
        indicators.addWidget(pose_status, 1, 1)
        
        audio_label = QLabel("Audio Output:")
        audio_label.setToolTip("Status of the audio system")
        indicators.addWidget(audio_label, 2, 0)
        
        audio_status = QLabel("Ready")
        audio_status.setStyleSheet("color: green; font-weight: bold;")
        audio_status.setToolTip("Green: FluidSynth ready for audio playback")
        indicators.addWidget(audio_status, 2, 1)
        
        entrainment_label = QLabel("Entrainment:")
        entrainment_label.setToolTip("How well the patient is synchronizing with the rhythm")
        indicators.addWidget(entrainment_label, 3, 0)
        
        entrainment_status = QLabel("85%")
        entrainment_status.setStyleSheet("color: blue; font-weight: bold;")
        entrainment_status.setToolTip("Percentage of steps synchronized with the beat")
        indicators.addWidget(entrainment_status, 3, 1)
        
        # Set column stretch to make the layout more balanced
        indicators.setColumnStretch(0, 1)
        indicators.setColumnStretch(1, 1)
        
        layout.addLayout(indicators)
        
        # Log messages
        log_label = QLabel("System Log:")
        log_label.setToolTip("Recent system messages and events")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setToolTip("Log of system events and notifications")
        self.log_text.append("[INFO] System initialized")
        self.log_text.append("[INFO] Camera connected")
        self.log_text.append("[INFO] MediaPipe pose estimation ready")
        self.log_text.append("[INFO] FluidSynth audio engine loaded")
        layout.addWidget(self.log_text)


class DashboardPreviewWindow(QMainWindow):
    """Main dashboard window for the RAS-helper application."""
    
    def __init__(self):
        """Initialize the dashboard window."""
        super().__init__()
        
        self.setWindowTitle("RAS-helper - Gait Rehabilitation System")
        self.resize(1280, 800)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Top section with title and mode selection
        top_layout = QHBoxLayout()
        
        title_label = QLabel("RAS-helper")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setToolTip("Computer Vision-Driven Rhythmic Auditory Stimulation System")
        top_layout.addWidget(title_label)
        
        top_layout.addStretch()
        
        mode_label = QLabel("Mode:")
        mode_label.setToolTip("Select application operating mode")
        top_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Clinical Assessment", "Rehabilitation Training", "Research Mode"])
        self.mode_combo.setToolTip("Clinical Assessment: For detailed evaluation\n"
                                  "Rehabilitation Training: For patient therapy\n"
                                  "Research Mode: For experimental protocols")
        self.mode_combo.currentIndexChanged.connect(self.switch_mode)
        top_layout.addWidget(self.mode_combo)
        
        settings_button = QPushButton("Settings")
        settings_button.setToolTip("Configure system settings and preferences")
        top_layout.addWidget(settings_button)
        
        main_layout.addLayout(top_layout)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left panel with video feed and mode-specific controls
        left_panel = QVBoxLayout()
        
        # Video feed (common to all modes)
        self.video_feed = VideoFeedPlaceholder()
        self.video_feed.setToolTip("Live video feed with 16:9 aspect ratio for gait analysis")
        left_panel.addWidget(self.video_feed, 3)  # 3:1 ratio with controls
        
        # Stacked widget for mode-specific controls
        self.controls_stack = QStackedWidget()
        self.controls_stack.setToolTip("Mode-specific controls that change based on selected mode")
        
        # Clinical Assessment controls
        self.clinical_controls = ClinicalAssessmentControls()
        self.controls_stack.addWidget(self.clinical_controls)
        
        # Rehabilitation Training controls
        self.rehab_controls = RehabilitationControls()
        self.controls_stack.addWidget(self.rehab_controls)
        
        # Research Mode controls
        self.research_controls = ResearchControlsWidget()
        self.controls_stack.addWidget(self.research_controls)
        
        # Standard RAS controls (as fallback)
        self.standard_controls = RASControlWidget()
        self.controls_stack.addWidget(self.standard_controls)
        
        left_panel.addWidget(self.controls_stack, 2)  # Increased proportion for controls
        
        content_layout.addLayout(left_panel, 7)  # 70% of width
        
        # Right panel with stacked widgets for different mode views
        right_panel = QVBoxLayout()
        
        # Stacked widget for mode-specific data views
        self.data_stack = QStackedWidget()
        self.data_stack.setToolTip("Mode-specific data visualization that changes based on selected mode")
        
        # Clinical Assessment data view
        self.clinical_data = DetailedMetricsWidget()
        self.data_stack.addWidget(self.clinical_data)
        
        # Rehabilitation Training data view
        self.rehab_data = ProgressTrackingWidget()
        self.data_stack.addWidget(self.rehab_data)
        
        # Research Mode data view
        self.research_data = RawDataWidget()
        self.data_stack.addWidget(self.research_data)
        
        # Standard gait analysis (as fallback)
        self.standard_data = GaitAnalysisWidget()
        self.data_stack.addWidget(self.standard_data)
        
        # Give more vertical space to the data view (parameters panel)
        right_panel.addWidget(self.data_stack, 4)  # Increased vertical space for parameters
        
        # Status information widget for non-Clinical Assessment modes
        self.status_widget = StatusWidget()
        right_panel.addWidget(self.status_widget, 2)  # Moderate space for status widget
        
        # Tabs for additional information
        self.info_tabs = QTabWidget()
        self.info_tabs.setToolTip("Additional information about patient and protocol")
        
        # Patient tab (common to all modes but with different content)
        self.patient_tabs = QStackedWidget()
        self.patient_tabs.setToolTip("Patient information specific to current mode")
        
        # Clinical Assessment patient tab
        clinical_patient_tab = QWidget()
        clinical_patient_layout = QVBoxLayout(clinical_patient_tab)
        clinical_patient_layout.addWidget(QLabel("Patient ID: PT12345"))
        clinical_patient_layout.addWidget(QLabel("Medical Record: #987654"))
        clinical_patient_layout.addWidget(QLabel("Diagnosis: Post-Stroke Gait"))
        clinical_patient_layout.addWidget(QLabel("Referring Physician: Dr. Smith"))
        clinical_patient_layout.addWidget(QLabel("Assessment Date: 2023-04-15"))
        clinical_patient_layout.addWidget(QLabel("Previous Assessments: 3"))
        clinical_patient_layout.addStretch()
        self.patient_tabs.addWidget(clinical_patient_tab)
        
        # Rehabilitation patient tab
        rehab_patient_tab = QWidget()
        rehab_patient_layout = QVBoxLayout(rehab_patient_tab)
        rehab_patient_layout.addWidget(QLabel("Patient: John D."))
        rehab_patient_layout.addWidget(QLabel("Session: 4 of 12"))
        rehab_patient_layout.addWidget(QLabel("Goal: Increase cadence by 5%"))
        rehab_patient_layout.addWidget(QLabel("Last Session: 2023-04-10"))
        rehab_patient_layout.addWidget(QLabel("Next Session: 2023-04-17"))
        rehab_patient_layout.addStretch()
        self.patient_tabs.addWidget(rehab_patient_tab)
        
        # Research participant tab
        research_patient_tab = QWidget()
        research_patient_layout = QVBoxLayout(research_patient_tab)
        research_patient_layout.addWidget(QLabel("Participant ID: R-2023-042"))
        research_patient_layout.addWidget(QLabel("Study: SLICE Protocol Efficacy"))
        research_patient_layout.addWidget(QLabel("Group: Intervention"))
        research_patient_layout.addWidget(QLabel("Trial: 2 of 10"))
        research_patient_layout.addWidget(QLabel("Consent Form: Signed"))
        research_patient_layout.addWidget(QLabel("Data Use: Anonymized"))
        research_patient_layout.addStretch()
        self.patient_tabs.addWidget(research_patient_tab)
        
        # Protocol tab (common to all modes but with different content)
        self.protocol_tabs = QStackedWidget()
        self.protocol_tabs.setToolTip("Protocol information specific to current mode")
        
        # Clinical Assessment protocol tab
        clinical_protocol_tab = QWidget()
        clinical_protocol_layout = QVBoxLayout(clinical_protocol_tab)
        clinical_protocol_layout.addWidget(QLabel("Protocol: Standard Gait Assessment"))
        clinical_protocol_layout.addWidget(QLabel("Duration: 5 minutes"))
        clinical_protocol_layout.addWidget(QLabel("Metrics: Full Gait Analysis"))
        clinical_protocol_layout.addWidget(QLabel("Normative Data: Age-Matched"))
        clinical_protocol_layout.addStretch()
        self.protocol_tabs.addWidget(clinical_protocol_tab)
        
        # Rehabilitation protocol tab
        rehab_protocol_tab = QWidget()
        rehab_protocol_layout = QVBoxLayout(rehab_protocol_tab)
        rehab_protocol_layout.addWidget(QLabel("Protocol: Progressive RAS"))
        rehab_protocol_layout.addWidget(QLabel("Duration: 20 minutes"))
        rehab_protocol_layout.addWidget(QLabel("Phase: Adaptation"))
        rehab_protocol_layout.addWidget(QLabel("Music: Personalized"))
        rehab_protocol_layout.addStretch()
        self.protocol_tabs.addWidget(rehab_protocol_tab)
        
        # Research protocol tab
        research_protocol_tab = QWidget()
        research_protocol_layout = QVBoxLayout(research_protocol_tab)
        research_protocol_layout.addWidget(QLabel("Protocol: SLICE Algorithm Test"))
        research_protocol_layout.addWidget(QLabel("Parameters: Alpha=0.3, Beta=0.7"))
        research_protocol_layout.addWidget(QLabel("Duration: 15 minutes × 3 trials"))
        research_protocol_layout.addWidget(QLabel("Control Condition: Fixed-Tempo RAS"))
        research_protocol_layout.addWidget(QLabel("Data Collection: Full Raw Data"))
        research_protocol_layout.addStretch()
        self.protocol_tabs.addWidget(research_protocol_tab)
        
        # Add tab widgets to main tabs
        tab_widget = QTabWidget()
        
        patient_container = QWidget()
        patient_layout = QVBoxLayout(patient_container)
        patient_layout.addWidget(self.patient_tabs)
        tab_widget.addTab(patient_container, "Patient Info")
        
        protocol_container = QWidget()
        protocol_layout = QVBoxLayout(protocol_container)
        protocol_layout.addWidget(self.protocol_tabs)
        tab_widget.addTab(protocol_container, "Protocol")
        
        right_panel.addWidget(tab_widget, 1)  # Less space for tabs
        
        content_layout.addLayout(right_panel, 3)  # 30% of width
        
        main_layout.addLayout(content_layout)
        
        # Bottom status bar with basic information
        self.statusBar().showMessage("Ready | Session Duration: 00:00")
        self.statusBar().setToolTip("Current system status and session information")
        
        # Set initial mode
        self.switch_mode(0)  # Clinical Assessment mode by default
    
    def switch_mode(self, mode_index):
        """Switch between different application modes."""
        # Update control panel
        self.controls_stack.setCurrentIndex(mode_index)
        
        # Update data display
        self.data_stack.setCurrentIndex(mode_index)
        
        # Update patient info tab
        self.patient_tabs.setCurrentIndex(mode_index)
        
        # Update protocol tab
        self.protocol_tabs.setCurrentIndex(mode_index)
        
        # Show/hide status widget based on mode
        # Only show status widget in non-Clinical Assessment modes since Clinical has its own status panel
        if mode_index == 0:  # Clinical Assessment mode
            self.status_widget.hide()
        else:
            self.status_widget.show()
        
        # Update video feed label based on mode
        mode_names = ["Clinical Assessment", "Rehabilitation Training", "Research"]
        self.video_feed.label.setText(f"Video Feed - {mode_names[mode_index]} Mode")
        
        # Update window title
        self.setWindowTitle(f"RAS-helper - {mode_names[mode_index]} Mode")
        
        # Update status bar
        mode_status = [
            "Ready for patient assessment",
            "Ready to begin rehabilitation session",
            "Research mode active - data collection ready"
        ]
        self.statusBar().showMessage(f"{mode_status[mode_index]} | Session Duration: 00:00")


def main():
    """Launch the UI preview."""
    app = QApplication(sys.argv)
    window = DashboardPreviewWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 