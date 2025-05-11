#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Music Rhythm Analysis Window

This module provides a separate window for detailed visualization of MIDI rhythm patterns.
"""

import sys
import os
from pathlib import Path

# Add path handling for direct execution
if __name__ == "__main__":
    # Get the project root directory (two levels up from this file)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    
    # Add to Python path if not already there
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QComboBox, QFrame, QSplitter, QTabWidget,
    QGroupBox, QFileDialog, QScrollArea, QSizePolicy, QSpacerItem,
    QMessageBox, QDialog, QDialogButtonBox, QGridLayout
)
from PyQt5.QtCore import Qt, QSize, pyqtSlot, QTimer
from PyQt5.QtGui import QIcon, QFont

from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
import matplotlib.pyplot as plt

# Import from core modules
from core.music_analysis import create_rhythm_visualization
from core.music_analysis.rhythm_visualization import (
    get_visualization_as_qt_widget, create_beat_histogram,
    create_rhythm_metrics_chart, create_circular_rhythm_plot, save_visualization,
    create_overall_rhythm_pattern
)
from core.music_analysis.midi_feature_extractor import MidiFeatureExtractor
from core.music_analysis.midi_categorizer import MidiCategorizer
from core.music_analysis.dataset_manager import DatasetManager


class ExplanationDialog(QDialog):
    """Dialog for displaying rhythm analysis explanations."""
    
    def __init__(self, parent=None):
        """Initialize the explanation dialog."""
        super().__init__(parent)
        
        self.setWindowTitle("Rhythm Analysis Explanations")
        self.resize(600, 500)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Create a scroll area for the content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Content widget
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Add explanations for different visualization types
        self._add_rhythm_pattern_explanation(content_layout)
        self._add_beat_histogram_explanation(content_layout)
        self._add_rhythm_metrics_explanation(content_layout)
        self._add_circular_plot_explanation(content_layout)
        
        # Add content to scroll area
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _add_rhythm_pattern_explanation(self, layout):
        """Add explanation for rhythm pattern visualization."""
        group = QGroupBox("Overall Rhythm Pattern")
        group_layout = QVBoxLayout(group)
        
        text = """
        <p><b>Overall Rhythm Pattern</b> shows how rhythm intensity varies throughout a piece:</p>
        <ul>
            <li>The <b>blue area</b> represents the <b>rhythm intensity</b> at each moment in the music</li>
            <li><b>Red vertical lines</b> mark <b>downbeats</b> (first beat of each measure)</li>
            <li><b>Gray vertical lines</b> indicate regular <b>beats</b> within measures</li>
            <li>Higher values show stronger rhythmic emphasis at that moment</li>
            <li>The numbers at the top indicate <b>measure numbers</b></li>
        </ul>
        <p>This visualization helps you understand how rhythm varies and flows throughout the piece.</p>
        """
        
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        group_layout.addWidget(label)
        
        layout.addWidget(group)
    
    def _add_beat_histogram_explanation(self, layout):
        """Add explanation for beat histogram visualization."""
        group = QGroupBox("Beat Histogram")
        group_layout = QVBoxLayout(group)
        
        text = """
        <p><b>Beat Histogram</b> shows the relative strength of different beat positions within a measure:</p>
        <ul>
            <li>The numbers (1,2,3,4) represent <b>beat positions</b> in a measure</li>
            <li>The <b>height of each bar</b> shows how strongly that beat position is emphasized in the music</li>
            <li>The <b>darker blue bar</b> typically marks the <b>downbeat</b> (first beat)</li>
            <li>The values above each bar show the <b>normalized strength</b> of that beat position</li>
        </ul>
        <p>This visualization helps identify which beats are emphasized in the music, revealing important rhythmic patterns.</p>
        """
        
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        group_layout.addWidget(label)
        
        layout.addWidget(group)
    
    def _add_rhythm_metrics_explanation(self, layout):
        """Add explanation for rhythm metrics visualization."""
        group = QGroupBox("Rhythm Metrics")
        group_layout = QVBoxLayout(group)
        
        text = """
        <p><b>Rhythm Metrics</b> quantifies different aspects of rhythm on a 0-1 scale:</p>
        <ul>
            <li><b>Metrical Strength:</b> How well notes align with the beat grid (higher = more aligned)</li>
            <li><b>Rhythm Regularity:</b> Consistency of rhythmic patterns (higher = more regular)</li>
            <li><b>Downbeat Strength:</b> Emphasis on the first beat of each measure (higher = stronger downbeats)</li>
            <li><b>Syncopation Index:</b> Prevalence of unexpected note placements (higher = more syncopated)</li>
            <li><b>Off-Beat Ratio:</b> Proportion of notes occurring between beats (higher = more off-beat notes)</li>
        </ul>
        <p>These metrics provide objective measurements of rhythmic characteristics useful for comparison between pieces.</p>
        """
        
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        group_layout.addWidget(label)
        
        layout.addWidget(group)
    
    def _add_circular_plot_explanation(self, layout):
        """Add explanation for circular rhythm plot visualization."""
        group = QGroupBox("Circular Rhythm Plot")
        group_layout = QVBoxLayout(group)
        
        text = """
        <p><b>Circular Rhythm Plot</b> shows rhythmic patterns as a circular representation:</p>
        <ul>
            <li>Each <b>angle</b> corresponds to a position within a measure</li>
            <li>The <b>distance from center</b> represents the relative strength or frequency of notes at that position</li>
            <li>The numbers (1,2,3,4) mark the <b>main beats</b> in a measure</li>
            <li><b>Stronger peaks</b> indicate more rhythmic emphasis at that position</li>
            <li><b>Evenly distributed</b> values indicate a regular rhythm</li>
            <li><b>Concentrated values</b> in specific regions indicate a more distinctive rhythmic pattern</li>
        </ul>
        <p>This circular representation is particularly useful for seeing recurring rhythmic patterns and the overall rhythmic character of the music.</p>
        """
        
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        group_layout.addWidget(label)
        
        layout.addWidget(group)


class MusicRhythmAnalysisWindow(QMainWindow):
    """Window for detailed visualization of music rhythm patterns."""
    
    def __init__(self, midi_file_path=None, parent=None):
        """
        Initialize the music rhythm analysis window.
        
        Args:
            midi_file_path: Optional path to a MIDI file to analyze
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.setWindowTitle("Music Rhythm Analysis")
        self.resize(1000, 950)  # Increased height from 900 to 950 for better visualization
        
        # Component instances
        self.midi_file_path = None  # Don't store the path yet
        self.feature_extractor = MidiFeatureExtractor()
        self.midi_categorizer = MidiCategorizer(self.feature_extractor)
        self.current_fig = None  # Store the current figure for saving
        
        # Initialize the UI
        self._init_ui()
        
        # If a MIDI file was provided, load it after UI is ready
        if midi_file_path:
            # Use a single-shot timer to load the file after window is shown
            QTimer.singleShot(100, lambda: self.load_midi_file(midi_file_path))
    
    def _init_ui(self):
        """Initialize the UI components."""
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(5)  # Reduce spacing between elements
        main_layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        
        # Top controls
        top_controls = QHBoxLayout()
        top_controls.setSpacing(5)  # Reduce spacing
        
        # File selection
        file_button = QPushButton("Open MIDI File")
        file_button.setToolTip("Select a MIDI file for rhythm analysis")
        file_button.clicked.connect(self.select_midi_file)
        top_controls.addWidget(file_button)
        
        # File information display
        self.file_info_label = QLabel("No file loaded")
        self.file_info_label.setStyleSheet("font-weight: bold;")
        top_controls.addWidget(self.file_info_label)
        
        top_controls.addStretch()
        
        # Visualization type selector
        viz_label = QLabel("Visualization:")
        top_controls.addWidget(viz_label)
        
        self.viz_combo = QComboBox()
        self.viz_combo.addItems([
            "All Visualizations", 
            "Overall Rhythm Pattern",
            "Beat Histogram", 
            "Rhythm Metrics",
            "Circular Rhythm Plot"
        ])
        self.viz_combo.setToolTip("Select which visualization to display")
        self.viz_combo.currentIndexChanged.connect(self.update_visualization)
        top_controls.addWidget(self.viz_combo)
        
        # Add explanations button
        explain_button = QPushButton("Explanations")
        explain_button.setToolTip("Show detailed explanations of the visualizations")
        explain_button.clicked.connect(self.show_explanations)
        top_controls.addWidget(explain_button)
        
        # Save visualization button
        save_button = QPushButton("Save Visualization")
        save_button.setToolTip("Save the current visualization as an image")
        save_button.clicked.connect(self.save_visualization)
        top_controls.addWidget(save_button)
        
        main_layout.addLayout(top_controls)
        
        # Tab widget for different views
        self.tabs = QTabWidget()
        
        # Visualization tab
        viz_tab = QWidget()
        viz_layout = QVBoxLayout(viz_tab)
        viz_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        viz_layout.setSpacing(0)  # Remove spacing
        
        # Create scroll area for visualization
        self.scroll_area = QScrollArea()
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setWidgetResizable(True)
        
        # Container for the visualization
        self.viz_container = QWidget()
        self.viz_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.viz_layout = QVBoxLayout(self.viz_container)
        self.viz_layout.setAlignment(Qt.AlignTop)
        self.viz_layout.setSpacing(0)  # Remove spacing
        self.viz_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        # Add placeholder text
        placeholder = QLabel("Select a MIDI file to view rhythm analysis")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("font-size: 14px; color: gray;")
        self.viz_layout.addWidget(placeholder)
        
        # Set the widget for scroll area
        self.scroll_area.setWidget(self.viz_container)
        viz_layout.addWidget(self.scroll_area)
        
        self.tabs.addTab(viz_tab, "Visualization")
        
        # Feature details tab
        features_tab = QWidget()
        features_layout = QVBoxLayout(features_tab)
        
        # Create a group box for features
        features_group = QGroupBox("Rhythm Features")
        features_group_layout = QVBoxLayout(features_group)
        
        # Add feature text display
        self.features_label = QLabel("No features extracted yet")
        self.features_label.setWordWrap(True)
        self.features_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.features_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        features_group_layout.addWidget(self.features_label)
        
        features_layout.addWidget(features_group)
        
        # Add categorization group
        category_group = QGroupBox("Music Categorization")
        category_layout = QVBoxLayout(category_group)
        
        # Add category text display
        self.category_label = QLabel("No categorization performed yet")
        self.category_label.setWordWrap(True)
        self.category_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.category_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        category_layout.addWidget(self.category_label)
        
        features_layout.addWidget(category_group)
        
        # Add style and mood information group to features tab
        style_mood_group = QGroupBox("Style & Mood")
        style_mood_layout = QVBoxLayout(style_mood_group)
        
        # Add style/mood text display
        self.style_mood_label = QLabel("No style/mood analysis performed yet")
        self.style_mood_label.setWordWrap(True)
        self.style_mood_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.style_mood_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        style_mood_layout.addWidget(self.style_mood_label)
        
        features_layout.addWidget(style_mood_group)
        
        self.tabs.addTab(features_tab, "Features & Categorization")
        
        main_layout.addWidget(self.tabs)
        
        # Status bar for information
        self.statusBar().showMessage("Ready")
    
    def show_explanations(self):
        """Show the explanations dialog."""
        dialog = ExplanationDialog(self)
        dialog.exec_()
    
    def select_midi_file(self):
        """Open a file dialog to select a MIDI file."""
        # Use the static method instead of creating a QFileDialog instance
        # This prevents dialog ownership issues
        file_path, _ = QFileDialog.getOpenFileName(
            None,  # No parent to avoid ownership issues
            "Select MIDI File",
            "",
            "MIDI Files (*.mid *.midi);;All Files (*)"
        )
        
        if file_path:
            # Make sure this window is active before loading the file
            self.show()
            self.raise_()
            self.activateWindow()
            QApplication.processEvents()
            
            # Now load the file
            self.load_midi_file(file_path)
            
            # Ensure window stays on top after loading
            self.raise_()
            self.activateWindow()
    
    def load_midi_file(self, file_path):
        """
        Load and analyze a MIDI file.
        
        Args:
            file_path: Path to the MIDI file
        """
        try:
            # Update the file path
            self.midi_file_path = file_path
            
            # Show file info
            file_name = os.path.basename(file_path)
            self.file_info_label.setText(f"File: {file_name}")
            self.setWindowTitle(f"Music Rhythm Analysis - {file_name}")
            
            # Load and analyze the file
            self.statusBar().showMessage(f"Loading {file_name}...")
            success = self.feature_extractor.load_file(file_path)
            
            if not success:
                self.statusBar().showMessage(f"Failed to load {file_name}")
                return
                
            # Extract features
            features = self.feature_extractor.extract_all_features()
            
            # Get categorization
            metadata = self.midi_categorizer.categorize_file(file_path, extract_features=False)
            
            # Update the features display
            self.update_features_display(features, metadata)
            
            # Create and display the visualization
            self.update_visualization()
            
            # Update status
            self.statusBar().showMessage(f"Loaded {file_name}")
            
            # Make sure window is visible and on top
            self.show()
            self.raise_()
            self.activateWindow()
            
        except Exception as e:
            self.statusBar().showMessage(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error Loading File", 
                               f"An error occurred while loading the file: {str(e)}")
    
    def update_features_display(self, features, metadata):
        """
        Update the features and categorization display.
        
        Args:
            features: Dictionary of extracted features
            metadata: Dictionary of metadata including categorization
        """
        # Format features as text
        feature_text = "<b>Rhythm Features:</b><br>"
        feature_text += f"Original Tempo: {features.get('original_tempo', 'Unknown')} BPM<br>"
        feature_text += f"Time Signature: {features.get('time_signature', 'Unknown')}<br>"
        feature_text += f"Note Count: {features.get('note_count', 0)}<br>"
        feature_text += f"Note Density: {features.get('note_density', 0):.2f} notes/second<br>"
        feature_text += f"Notes per Beat: {features.get('notes_per_beat', 0):.2f}<br>"
        feature_text += f"Rhythm Regularity: {features.get('rhythm_regularity', 0):.2f}<br>"
        feature_text += f"Metrical Strength: {features.get('metrical_strength', 0):.2f}<br>"
        feature_text += f"Syncopation Index: {features.get('syncopation_index', 0):.2f}<br>"
        feature_text += f"Off-Beat Ratio: {features.get('off_beat_ratio', 0):.2f}<br>"
        feature_text += f"Downbeat Strength: {features.get('downbeat_strength', 0):.2f}<br>"
        
        # Update features label
        self.features_label.setText(feature_text)
        
        # Format categorization as text
        category_text = "<b>Categorization:</b><br>"
        if 'tags' in metadata:
            tags = metadata['tags']
            category_text += f"Genre: {tags.get('genre', 'Unknown')}<br>"
            category_text += f"Rhythmic Character: {tags.get('rhythmicCharacter', 'Unknown')}<br>"
        else:
            category_text += "No categorization data available"
        
        # Update category label
        self.category_label.setText(category_text)
        
        # Format style/mood information
        style_mood_text = "<b>Style & Mood Features:</b><br>"
        style_mood_text += f"Emotional Intensity: {features.get('emotional_intensity', 0):.2f}<br>"
        style_mood_text += f"Energy Level: {features.get('energetic_factor', 0):.2f}<br>"
        style_mood_text += f"Brightness: {features.get('brightness_factor', 0):.2f}<br>"
        style_mood_text += f"Dynamic Range: {features.get('dynamic_range', 0):.2f}<br>"
        
        # Add mood classification from metadata if available
        if 'tags' in metadata and 'mood' in metadata['tags']:
            style_mood_text += f"<br><b>Mood Classification:</b> {metadata['tags']['mood']}<br>"
            
            # Add mood description based on classification
            mood_descriptions = {
                "Energetic": "Lively and dynamic with strong rhythms and bright character.",
                "Relaxed": "Calm and smooth, with regular rhythms and moderate tempo.",
                "Uplifting": "Positive and elevating, with clear beats and bright tonality.",
                "Melancholic": "Reflective or somber, with deeper tones and moderate intensity.",
                "Cheerful": "Light and happy, with bouncy rhythms and bright character.",
                "Peaceful": "Serene and gentle, with flowing rhythm and minimal tension.",
                "Intense": "Powerful and dramatic, with wide dynamic range and strong expression.",
                "Chill": "Cool and laid-back, with smooth flow and moderate brightness."
            }
            
            mood = metadata['tags']['mood']
            if mood in mood_descriptions:
                style_mood_text += f"<i>{mood_descriptions[mood]}</i>"
        
        # Update style/mood label
        self.style_mood_label.setText(style_mood_text)
    
    def update_visualization(self):
        """Update the visualization based on the selected type."""
        if not self.midi_file_path or not hasattr(self.feature_extractor, 'features'):
            return
            
        # Clear previous visualization
        for i in reversed(range(self.viz_layout.count())):
            widget = self.viz_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Show processing message
        self.statusBar().showMessage("Generating visualization...")
        
        viz_type = self.viz_combo.currentText()
        
        try:
            # Close any previous figures
            if hasattr(self, 'current_fig'):
                if isinstance(self.current_fig, list):
                    # Close each figure in the list
                    for fig in self.current_fig:
                        plt.close(fig)
                elif self.current_fig is not None:
                    # Close the single figure
                    plt.close(self.current_fig)
                self.current_fig = None
            
            if viz_type == "All Visualizations":
                # For "All Visualizations", create a 2x2 grid of smaller visualizations
                grid_container = QWidget()
                grid_layout = QGridLayout(grid_container)
                grid_layout.setContentsMargins(0, 0, 0, 0)
                grid_layout.setSpacing(5)  # Small spacing between grid items
                
                # 1. Overall Rhythm Pattern (top left)
                fig1, ax1 = plt.subplots(figsize=(6, 4))
                create_overall_rhythm_pattern(self.feature_extractor, ax1)
                # Remove redundant suptitle, we'll use axis titles only
                ax1.set_title("Overall Rhythm Pattern", fontsize=10)
                fig1.tight_layout(pad=0.2)
                canvas1 = get_visualization_as_qt_widget(fig1)
                
                container1 = QWidget()
                container1_layout = QVBoxLayout(container1)
                container1_layout.setContentsMargins(0, 0, 0, 0)
                container1_layout.setSpacing(0)
                toolbar1 = NavigationToolbar2QT(canvas1, self)
                toolbar1.setIconSize(QSize(16, 16))  # Smaller toolbar icons
                container1_layout.addWidget(toolbar1)
                container1_layout.addWidget(canvas1)
                
                grid_layout.addWidget(container1, 0, 0)
                
                # 2. Beat Histogram (top right)
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                create_beat_histogram(self.feature_extractor.features, ax2)
                # Use axis title instead of figure title
                ax2.set_title("Beat Histogram", fontsize=10)
                fig2.tight_layout(pad=0.2)
                canvas2 = get_visualization_as_qt_widget(fig2)
                
                container2 = QWidget()
                container2_layout = QVBoxLayout(container2)
                container2_layout.setContentsMargins(0, 0, 0, 0)
                container2_layout.setSpacing(0)
                toolbar2 = NavigationToolbar2QT(canvas2, self)
                toolbar2.setIconSize(QSize(16, 16))
                container2_layout.addWidget(toolbar2)
                container2_layout.addWidget(canvas2)
                
                grid_layout.addWidget(container2, 0, 1)
                
                # 3. Rhythm Metrics (bottom left)
                fig3, ax3 = plt.subplots(figsize=(6, 4))
                # Use standard function call without extra parameters
                create_rhythm_metrics_chart(self.feature_extractor.features, ax3, show_explanation=False)
                # Use axis title instead of figure title
                ax3.set_title("Rhythm Metrics", fontsize=10)
                fig3.tight_layout(pad=0.2)
                canvas3 = get_visualization_as_qt_widget(fig3)
                
                container3 = QWidget()
                container3_layout = QVBoxLayout(container3)
                container3_layout.setContentsMargins(0, 0, 0, 0)
                container3_layout.setSpacing(0)
                toolbar3 = NavigationToolbar2QT(canvas3, self)
                toolbar3.setIconSize(QSize(16, 16))
                container3_layout.addWidget(toolbar3)
                container3_layout.addWidget(canvas3)
                
                grid_layout.addWidget(container3, 1, 0)
                
                # 4. Circular Rhythm Plot (bottom right)
                fig4 = plt.figure(figsize=(6, 4))
                ax4 = fig4.add_subplot(111, polar=True)
                # Use standard function call without extra parameters
                create_circular_rhythm_plot(self.feature_extractor.features, ax4, show_explanation=False)
                # Use axis title instead of figure title
                ax4.set_title("Circular Rhythm Plot", fontsize=10)
                fig4.tight_layout(pad=0.2)
                canvas4 = get_visualization_as_qt_widget(fig4)
                
                container4 = QWidget()
                container4_layout = QVBoxLayout(container4)
                container4_layout.setContentsMargins(0, 0, 0, 0)
                container4_layout.setSpacing(0)
                toolbar4 = NavigationToolbar2QT(canvas4, self)
                toolbar4.setIconSize(QSize(16, 16))
                container4_layout.addWidget(toolbar4)
                container4_layout.addWidget(canvas4)
                
                grid_layout.addWidget(container4, 1, 1)
                
                # Store all figures for saving
                self.current_fig = [fig1, fig2, fig3, fig4]
                
                # Add the grid container to the visualization layout
                self.viz_layout.addWidget(grid_container)
                
                # Force scroll to top
                QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(0))
                
            elif viz_type == "Overall Rhythm Pattern":
                # Create figure with maximized space usage
                fig, ax = plt.subplots(figsize=(12, 7))  # Increased height
                self.current_fig = fig
                
                # Create visualization
                create_overall_rhythm_pattern(self.feature_extractor, ax)
                
                # Maximize plot area
                fig.tight_layout(pad=0.2)
                
                # Create canvas
                canvas = get_visualization_as_qt_widget(fig)
                canvas.setMinimumHeight(600)  # Increased height
                
                # Add container with toolbar
                container = QWidget()
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(0)
                
                toolbar = NavigationToolbar2QT(canvas, self)
                container_layout.addWidget(toolbar)
                container_layout.addWidget(canvas)
                
                self.viz_layout.addWidget(container)
                
            elif viz_type == "Beat Histogram":
                # Create figure with maximized space
                fig, ax = plt.subplots(figsize=(12, 7))
                self.current_fig = fig
                
                # Create visualization
                create_beat_histogram(self.feature_extractor.features, ax)
                
                # Maximize plot area
                fig.tight_layout(pad=0.2)
                
                # Create canvas
                canvas = get_visualization_as_qt_widget(fig)
                canvas.setMinimumHeight(600)
                
                # Add container with toolbar
                container = QWidget()
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(0)
                
                toolbar = NavigationToolbar2QT(canvas, self)
                container_layout.addWidget(toolbar)
                container_layout.addWidget(canvas)
                
                self.viz_layout.addWidget(container)
                
            elif viz_type == "Rhythm Metrics":
                # Create figure with maximized space
                fig, ax = plt.subplots(figsize=(12, 7))
                self.current_fig = fig
                
                # Create visualization - standard call, no explanation text
                create_rhythm_metrics_chart(self.feature_extractor.features, ax, show_explanation=False)
                
                # Maximize plot area
                fig.tight_layout(pad=0.2)
                
                # Create canvas
                canvas = get_visualization_as_qt_widget(fig)
                canvas.setMinimumHeight(600)
                
                # Add container with toolbar
                container = QWidget()
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(0)
                
                toolbar = NavigationToolbar2QT(canvas, self)
                container_layout.addWidget(toolbar)
                container_layout.addWidget(canvas)
                
                self.viz_layout.addWidget(container)
                
            elif viz_type == "Circular Rhythm Plot":
                # Create figure with maximized space
                fig = plt.figure(figsize=(12, 9))
                self.current_fig = fig
                
                # Add top margin space for title
                plt.subplots_adjust(top=0.85)  # Leave 15% space at top for title
                
                # Create a polar plot that's smaller than default
                ax = plt.subplot2grid((1, 1), (0, 0), polar=True)
                
                # Create visualization - standard call, no explanation text
                create_circular_rhythm_plot(self.feature_extractor.features, ax, show_explanation=False)
                
                # Set title with larger padding to avoid overlap
                ax.set_title('Circular Rhythm Plot', pad=20, fontsize=14)
                
                # Create canvas
                canvas = get_visualization_as_qt_widget(fig)
                canvas.setMinimumHeight(700)
                
                # Add container with toolbar
                container = QWidget()
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(0)
                
                toolbar = NavigationToolbar2QT(canvas, self)
                container_layout.addWidget(toolbar)
                container_layout.addWidget(canvas)
                
                self.viz_layout.addWidget(container)
            
            # Make sure window is visible and on top
            self.show()
            self.raise_()
            self.activateWindow()
            
            # Force scroll to top
            QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(0))
            
            self.statusBar().showMessage("Visualization updated")
            
        except Exception as e:
            self.statusBar().showMessage(f"Error creating visualization: {str(e)}")
            
            # Add error message to viz container
            error_label = QLabel(f"Error creating visualization: {str(e)}")
            error_label.setWordWrap(True)
            error_label.setStyleSheet("color: red;")
            self.viz_layout.addWidget(error_label)
    
    def save_visualization(self):
        """Save the current visualization as an image file."""
        if not self.current_fig:
            QMessageBox.warning(self, "No Visualization", 
                             "No visualization to save. Please load a MIDI file first.")
            return
        
        # Use static method to avoid window management issues
        file_path, _ = QFileDialog.getSaveFileName(
            None,  # No parent to avoid ownership issues
            "Save Visualization", 
            "", 
            "PNG Files (*.png);;PDF Files (*.pdf);;All Files (*)"
        )
        
        if file_path:
            try:
                # Make sure the window stays on top before/after saving
                self.raise_()
                self.activateWindow()
                
                # Save the visualization
                self.statusBar().showMessage(f"Saving visualization to {file_path}...")
                
                # Make sure file has the right extension
                if not file_path.lower().endswith(('.png', '.pdf')):
                    file_path += '.png'  # Default to PNG
                
                # Save the current figure
                if isinstance(self.current_fig, list):
                    # For "All Visualizations" mode, create and save a single combined figure
                    # Create a new figure for combined output
                    combined_fig = plt.figure(figsize=(12, 10))
                    
                    # Set up a 2x2 grid
                    gs = combined_fig.add_gridspec(2, 2)
                    
                    # Copy content from the individual figures to the combined figure
                    for i, fig in enumerate(self.current_fig):
                        row = i // 2
                        col = i % 2
                        
                        # Create a new subplot
                        ax = combined_fig.add_subplot(gs[row, col])
                        
                        # Get the content from the original figure
                        original_ax = fig.axes[0]
                        
                        # Copy the content (this is a simplified approach)
                        if i == 3:  # Circular plot
                            ax = combined_fig.add_subplot(gs[row, col], polar=True)
                            # Copy data from polar plot
                            for line in original_ax.lines:
                                ax.plot(line.get_xdata(), line.get_ydata(), 
                                        color=line.get_color(), 
                                        linestyle=line.get_linestyle(),
                                        linewidth=line.get_linewidth())
                        else:
                            # Copy data from regular plots
                            for line in original_ax.lines:
                                ax.plot(line.get_xdata(), line.get_ydata(), 
                                        color=line.get_color(), 
                                        linestyle=line.get_linestyle(),
                                        linewidth=line.get_linewidth())
                            
                            # Copy bar charts if present
                            for collection in original_ax.collections:
                                if hasattr(collection, 'get_offsets'):
                                    ax.scatter(collection.get_offsets()[:, 0], 
                                            collection.get_offsets()[:, 1],
                                            color=collection.get_facecolor()[0])
                            
                            # Copy patches (for bar charts)
                            for patch in original_ax.patches:
                                if hasattr(patch, 'get_x') and hasattr(patch, 'get_height'):
                                    ax.bar(patch.get_x() + patch.get_width()/2, 
                                        patch.get_height(), 
                                        width=patch.get_width(),
                                        color=patch.get_facecolor())
                        
                        # Copy title
                        ax.set_title(fig._suptitle.get_text() if fig._suptitle else "")
                        
                        # Copy axis labels if they exist
                        if original_ax.get_xlabel():
                            ax.set_xlabel(original_ax.get_xlabel())
                        if original_ax.get_ylabel():
                            ax.set_ylabel(original_ax.get_ylabel())
                    
                    # Add an overall title
                    combined_fig.suptitle(f"Rhythm Analysis: {os.path.basename(self.midi_file_path)}", 
                                       fontsize=14)
                    
                    # Adjust layout
                    combined_fig.tight_layout(rect=[0, 0, 1, 0.95])  # Make room for suptitle
                    
                    # Save the combined figure
                    combined_fig.savefig(file_path, dpi=300)
                    plt.close(combined_fig)
                else:
                    # For single visualization, save directly
                    save_visualization(self.current_fig, file_path)
                
                # Make sure window stays on top after saving
                self.statusBar().showMessage(f"Visualization saved to {file_path}")
                self.raise_()
                self.activateWindow()
                
            except Exception as e:
                QMessageBox.critical(self, "Save Error", 
                                  f"An error occurred while saving the visualization: {str(e)}")
                self.statusBar().showMessage("Failed to save visualization")
                
                # Make sure window stays on top even after error
                self.raise_()
                self.activateWindow()


# Add a standalone launcher script that can be used to open the window
# in a completely separate process
def launch_analysis_window():
    """Launch the analysis window as a standalone application."""
    app = QApplication(sys.argv)
    
    # If a file path is provided as a command-line argument, use it
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Create and show the window
    window = MusicRhythmAnalysisWindow(file_path)
    window.show()
    
    sys.exit(app.exec_())


# Allow running this module as a script
if __name__ == "__main__":
    launch_analysis_window() 