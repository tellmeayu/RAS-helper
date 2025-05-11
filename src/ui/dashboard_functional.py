#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAS-helper: Functional Dashboard

This module implements the main dashboard with functional video capture and gait analysis.
It integrates the VideoFeedWidget and GaitAnalysisWidget to provide real-time analysis.
"""

import sys
import logging
import time
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QComboBox, QSlider, QFrame, QGroupBox,
    QGridLayout, QSpacerItem, QSizePolicy, QTabWidget, QTextEdit,
    QProgressBar, QDial, QSpinBox, QDoubleSpinBox, QCheckBox,
    QStackedWidget, QTableWidget, QTableWidgetItem, QLineEdit,
    QRadioButton, QButtonGroup, QFileDialog, QScrollArea, QToolButton,
    QMessageBox, QDialog, QListWidget, QSplitter, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QSize, QTimer, QRect, pyqtSlot
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QIcon
import cv2
import os

# Try to import visualization libraries at module level
MATPLOTLIB_AVAILABLE = False
NUMPY_AVAILABLE = False
try:
    import matplotlib
    matplotlib.use('Agg')  # Use Agg backend to prevent GUI issues
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
    NUMPY_AVAILABLE = True
except ImportError:
    logging.warning("Matplotlib or numpy not available. Visualization features will be limited.")

# Import core functionality
# from core.video_input.video_capture import VideoCapture, VideoSource, AspectRatio
# from core.pose_estimation.pose_estimation import PoseEstimator
from core.gait_analysis.gait_analysis import GaitAnalyzer
from core.session_management import SessionManager, SessionState, SessionType
from core.synchronization.synchronizer import GaitMusicSynchronizer, SyncState

# Import UI components
from ui.fixed_video_feed import FixedVideoFeedWidget
from ui.gait_analysis_widget import GaitAnalysisWidget
from ui.dashboard_preview import (
    ClinicalAssessmentControls, RehabilitationControls, ResearchControlsWidget, 
    RASControlWidget, ProgressTrackingWidget, RawDataWidget, StatusWidget
)


class MusicSelectionDialog(QDialog):
    """Dialog for selecting music from a pre-analyzed dataset."""
    
    def __init__(self, parent=None):
        """Initialize the music selection dialog."""
        super().__init__(parent)
        
        self.setWindowTitle("Select Music")
        self.resize(800, 500)
        
        # Try to load the dataset manager
        self.dataset_manager = None
        try:
            from core.music_analysis import DatasetManager
            self.dataset_manager = DatasetManager()
            
            # Try to load default metadata if available
            default_metadata_path = "resources/midi_metadata.json"
            if os.path.exists(default_metadata_path):
                self.dataset_manager.load_metadata(default_metadata_path)
        except ImportError:
            logger.warning("DatasetManager not available, will use placeholder data")
        
        # Add a timer for throttling preview updates
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(300)  # 300ms delay
        self.preview_timer.timeout.connect(self._generate_preview)
        self.pending_preview_row = -1
        self.current_figure = None
        
        # Setup UI
        self._setup_ui()
        
        # Load initial data
        self._load_music_items()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Create a tab widget for different ways to browse music
        tabs = QTabWidget()
        
        # ---- Filtered Selection Tab ----
        filter_tab = QWidget()
        filter_layout = QVBoxLayout(filter_tab)
        
        # Add filter controls
        filter_controls = QHBoxLayout()
        
        # Create rhythmic style filter
        rhythm_label = QLabel("Rhythmic Style:")
        self.rhythm_combo = QComboBox()
        self.rhythm_combo.addItems([
            "All", 
            "Clear & Steady Beat", 
            "Moderately Rhythmic", 
            "Groovy & Syncopated", 
            "Smooth & Flowing"
        ])
        filter_controls.addWidget(rhythm_label)
        filter_controls.addWidget(self.rhythm_combo)
        
        # Create instrument preference filter
        instrument_label = QLabel("Instrument Preference:")
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems([
            "All", 
            "Piano", 
            "Guitar", 
            "Strings", 
            "Percussion", 
            "Woodwinds", 
            "Brass", 
            "Electronic"
        ])
        filter_controls.addWidget(instrument_label)
        filter_controls.addWidget(self.instrument_combo)
        
        # Create mood filter
        mood_label = QLabel("Mood:")
        self.mood_combo = QComboBox()
        self.mood_combo.addItems([
            "All", 
            "Energetic", 
            "Relaxed", 
            "Uplifting", 
            "Melancholic", 
            "Cheerful", 
            "Peaceful", 
            "Intense", 
            "Chill"
        ])
        filter_controls.addWidget(mood_label)
        filter_controls.addWidget(self.mood_combo)
        
        filter_layout.addLayout(filter_controls)
        
        # Create apply filters button
        apply_button = QPushButton("Apply Filters")
        apply_button.clicked.connect(self._apply_filters)
        filter_controls.addWidget(apply_button)
        
        # Create splitter for list and preview
        splitter = QSplitter(Qt.Vertical)
        
        # Create table widget for music files with headers
        self.list_widget = QTableWidget()
        self.list_widget.setColumnCount(4)
        self.list_widget.setHorizontalHeaderLabels(["Title", "Rhythmic Style", "Instrument", "Mood"])
        self.list_widget.horizontalHeader().setStretchLastSection(True)
        self.list_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.list_widget.setSelectionMode(QTableWidget.SingleSelection)
        splitter.addWidget(self.list_widget)
        
        # Create preview area
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        self.preview_label = QLabel("Select a music item to see rhythm preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        
        # Create a placeholder for the visualization
        self.preview_frame = QFrame()
        self.preview_frame.setMinimumHeight(150)
        self.preview_frame.setFrameStyle(QFrame.StyledPanel)
        preview_layout.addWidget(self.preview_frame)
        self.preview_frame_layout = QVBoxLayout(self.preview_frame)
        
        splitter.addWidget(preview_widget)
        splitter.setSizes([300, 200])
        
        filter_layout.addWidget(splitter)
        
        # ---- Upload New MIDI Tab ----
        upload_tab = QWidget()
        upload_layout = QVBoxLayout(upload_tab)
        
        # Add explanation
        explanation = QLabel(
            "Upload a new MIDI file to use for RAS. Note that uploaded files will not be analyzed "
            "for rhythm characteristics until they are added to the dataset."
        )
        explanation.setWordWrap(True)
        upload_layout.addWidget(explanation)
        
        # Add file selection button
        file_button = QPushButton("Select MIDI File")
        file_button.clicked.connect(self._select_file)
        upload_layout.addWidget(file_button)
        
        # Add selected file display
        self.selected_file_label = QLabel("No file selected")
        upload_layout.addWidget(self.selected_file_label)
        
        # Add spacer
        upload_layout.addStretch()
        
        # ---- Dataset Management Tab (if dataset manager is available) ----
        if self.dataset_manager:
            dataset_tab = QWidget()
            dataset_layout = QVBoxLayout(dataset_tab)
            
            # Add dataset information
            stats_label = QLabel("Dataset Statistics")
            stats_label.setStyleSheet("font-weight: bold;")
            dataset_layout.addWidget(stats_label)
            
            # Add dataset statistics if available
            self.stats_text = QLabel("No dataset statistics available")
            dataset_layout.addWidget(self.stats_text)
            
            # Add spacer
            dataset_layout.addStretch()
            
            # Add analyze directory button
            analyze_dir_button = QPushButton("Analyze MIDI Directory...")
            analyze_dir_button.clicked.connect(self._analyze_directory)
            dataset_layout.addWidget(analyze_dir_button)
            
            # Add individual file analysis button
            analyze_file_button = QPushButton("Analyze Individual MIDI File...")
            analyze_file_button.clicked.connect(self._open_analysis_window)
            dataset_layout.addWidget(analyze_file_button)
            
            tabs.addTab(dataset_tab, "Dataset Management")
        
        # Add tabs to dialog
        tabs.addTab(filter_tab, "Browse Music")
        tabs.addTab(upload_tab, "Upload New MIDI")
        
        layout.addWidget(tabs)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Connect list widget signals for preview - use selection change instead of hover
        if MATPLOTLIB_AVAILABLE:
            # Connect to item selection for preview generation
            self.list_widget.itemSelectionChanged.connect(self._request_preview)
        else:
            self.preview_label.setText("Matplotlib not available for rhythm preview")
        
        # Set the attribute to store the selected music info
        self.selected_music = {
            "title": "",
            "file_path": "",
            "rhythmic_style": "",
            "instrument": "",
            "mood": ""
        }
    
    def _request_preview(self):
        """Request a preview with throttling to prevent excessive updates."""
        # Get the current row
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
            
        row = self.list_widget.row(selected_items[0])
        
        # Store the pending row and start the timer
        self.pending_preview_row = row
        
        # If timer is not running, start it
        if not self.preview_timer.isActive():
            self.preview_timer.start()
    
    def _generate_preview(self):
        """Generate the rhythm preview for the selected row."""
        if self.pending_preview_row < 0:
            return
            
        row = self.pending_preview_row
        self.pending_preview_row = -1
        
        try:
            # Clear any existing preview
            self._clear_preview()
            
            # Check if matplotlib is available
            if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
                self.preview_label.setText("Visualization libraries not available")
                return
            
            # Create a visualization based on the selected music
            title = self.list_widget.item(row, 0).text()
            rhythmic_style = self.list_widget.item(row, 1).text()
            self.preview_label.setText(f"Rhythm Pattern Preview: {title} ({rhythmic_style})")
            
            # Create a new figure
            self.current_figure = plt.figure(figsize=(8, 3), dpi=72)
            ax = self.current_figure.add_subplot(111)
            
            # Simplified dummy data for visualization
            x = np.linspace(0, 10, 1000)
            
            # Pattern based on rhythmic style
            if "Clear & Steady" in rhythmic_style:
                # Regular, clear beats
                y = np.sin(2 * np.pi * x) * 0.5 + 0.5
            elif "Smooth & Flowing" in rhythmic_style:
                # More flowing, expressive
                y = np.sin(2 * np.pi * x) * 0.3 + np.sin(4 * np.pi * x + 0.5) * 0.2 + 0.5
            elif "Groovy & Syncopated" in rhythmic_style:
                # Syncopated, irregular
                y = np.sin(2 * np.pi * x) * 0.3 + np.sin(3 * np.pi * x) * 0.3 + np.sin(5 * np.pi * x) * 0.2 + 0.5
            else:
                # Moderately Rhythmic
                y = np.sin(2 * np.pi * x) * 0.4 + np.sin(3.5 * np.pi * x) * 0.15 + 0.5
            
            # Add beats
            beat_positions = np.arange(0, 10, 0.5)
            
            # Plot rhythm pattern
            ax.fill_between(x, y, alpha=0.5, color='blue', label='Rhythm Intensity')
            
            # Add beat markers
            for pos in beat_positions:
                ax.axvline(x=pos, color='gray', alpha=0.4, linewidth=1)
            
            # Add downbeats (first beat of each measure)
            for pos in beat_positions[::2]:
                ax.axvline(x=pos, color='red', alpha=0.5, linewidth=1.5)
            
            ax.set_title(f"Rhythm Pattern: {title}")
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 1.15)
            ax.set_xlabel('Time')
            ax.set_ylabel('Intensity')
            ax.grid(True, alpha=0.3)
            
            # Remove ticks for cleaner look
            ax.set_xticks([])
            ax.set_yticks([])
            
            # Make the figure tight to reduce whitespace
            self.current_figure.tight_layout()
            
            # Convert to Qt widget
            canvas = FigureCanvasQTAgg(self.current_figure)
            self.preview_frame_layout.addWidget(canvas)
            
        except Exception as e:
            logger.error(f"Error showing preview: {e}")
            self.preview_label.setText(f"Error showing preview: {str(e)}")
    
    def _clear_preview(self):
        """Clear the current preview."""
        # Clear the frame layout
        for i in reversed(range(self.preview_frame_layout.count())): 
            widget = self.preview_frame_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        
        # Close any existing figure to prevent memory leaks
        if self.current_figure is not None and MATPLOTLIB_AVAILABLE:
            plt.close(self.current_figure)
            self.current_figure = None
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Clean up resources
        self._clear_preview()
        super().closeEvent(event)

    def _show_rhythm_preview(self, row):
        """Legacy method for backward compatibility."""
        # This is now handled by _request_preview and _generate_preview
        # We'll just request a preview for the given row
        self.list_widget.selectRow(row)
    
    def _apply_filters(self):
        """Apply the selected filters to the music list."""
        try:
            # In a real implementation, this would filter the dataset based on selections
            rhythmic_style = self.rhythm_combo.currentText()
            instrument = self.instrument_combo.currentText()
            mood = self.mood_combo.currentText()
            
            # Filter the list widget
            for row in range(self.list_widget.rowCount()):
                hide_row = False
                
                # Check rhythmic style filter
                if rhythmic_style != "All" and self.list_widget.item(row, 1) and self.list_widget.item(row, 1).text() != rhythmic_style:
                    hide_row = True
                    
                # Check instrument filter
                if instrument != "All" and self.list_widget.item(row, 2) and self.list_widget.item(row, 2).text() != instrument:
                    hide_row = True
                    
                # Check mood filter
                if mood != "All" and self.list_widget.item(row, 3) and self.list_widget.item(row, 3).text() != mood:
                    hide_row = True
                    
                # Hide or show the row
                self.list_widget.setRowHidden(row, hide_row)
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
    
    def _select_file(self):
        """Select a MIDI file from the file system."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select MIDI File", "", "MIDI Files (*.mid *.midi);;All Files (*)"
        )
        
        if file_path:
            file_name = os.path.basename(file_path)
            self.selected_file_label.setText(file_name)
            
            # Store the file information
            self.selected_music["title"] = os.path.splitext(file_name)[0]
            self.selected_music["file_path"] = file_path
            self.selected_music["rhythmic_style"] = "Unknown (not analyzed)"
            self.selected_music["instrument"] = "Unknown (not analyzed)"
            self.selected_music["mood"] = "Unknown (not analyzed)"
    
    def _analyze_directory(self):
        """Open a directory to analyze multiple MIDI files."""
        if not self.dataset_manager:
            QMessageBox.warning(self, "Not Available",
                              "Dataset management functionality is not available.")
            return
            
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select MIDI Directory", ""
        )
        
        if dir_path:
            reply = QMessageBox.question(
                self, "Process Directory", 
                f"This will process all MIDI files in {dir_path}. This may take some time. Proceed?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Create and show progress dialog
                progress = ProgressDialog(
                    "Processing MIDI Files", 
                    f"Processing MIDI files in {dir_path}...",
                    self
                )
                
                # Setup processing in a timer to allow UI to update
                self.process_timer = QTimer(self)
                self.process_timer.setSingleShot(True)
                self.process_timer.timeout.connect(lambda: self._process_directory(dir_path, progress))
                self.process_timer.start(100)  # Start after 100ms
                
                # Show the dialog (modal)
                result = progress.exec_()
                
                # Check if the operation was cancelled
                if result == QDialog.Rejected:
                    QMessageBox.information(self, "Operation Cancelled",
                                         "MIDI processing was cancelled.")
                    return
    
    def _process_directory(self, dir_path, progress_dialog):
        """Process a directory of MIDI files with progress updates."""
        try:
            # Set the dataset path
            self.dataset_manager.set_dataset_path(dir_path)
            
            # Find MIDI files first to estimate work
            try:
                midi_files = self.dataset_manager.find_midi_files()
                file_count = len(midi_files)
                
                if file_count > 0:
                    progress_dialog.set_status(f"Found {file_count} MIDI files to process")
                    progress_dialog.set_progress(0, file_count)
                else:
                    progress_dialog.reject()  # Close dialog
                    QMessageBox.warning(self, "No Files Found",
                                     f"No MIDI files found in {dir_path}")
                    return
            except Exception as e:
                progress_dialog.reject()  # Close dialog
                QMessageBox.warning(self, "Error Finding Files",
                                 f"Error finding MIDI files: {str(e)}")
                return
            
            # Process the directory
            # Note: In a real implementation, this would be done in a separate thread
            # with progress updates via signals. This is a simplified version.
            success = self.dataset_manager.process_dataset()
            
            # Close the progress dialog
            progress_dialog.accept()
            
            if success:
                QMessageBox.information(self, "Processing Complete",
                                     f"Successfully processed {file_count} MIDI files in {dir_path}")
                # Refresh the list
                self._load_music_items()
            else:
                QMessageBox.warning(self, "Processing Failed",
                                 f"Failed to process MIDI files in {dir_path}")
                
        except Exception as e:
            # Close the progress dialog
            progress_dialog.reject()
            
            logger.error(f"Error processing directory: {e}")
            QMessageBox.critical(self, "Processing Error",
                              f"An error occurred while processing the directory: {str(e)}")
    
    def _open_analysis_window(self):
        """Open the rhythm analysis window for a selected MIDI file."""
        try:
            # Step 1: Get the file path using the static method
            file_path, _ = QFileDialog.getOpenFileName(
                None,  # No parent to avoid ownership issues
                "Select MIDI File to Analyze",
                "",
                "MIDI Files (*.mid *.midi);;All Files (*)"
            )
            
            if file_path:
                # Import our new launcher module
                from ui.rhythm_analyzer_launcher import launch_analyzer_as_separate_process
                
                # Launch the window as a completely separate process
                launch_analyzer_as_separate_process(file_path)
                
        except ImportError as e:
            QMessageBox.warning(self, "Module Not Available", 
                               f"The rhythm analysis module is not available: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error",
                              f"An error occurred while opening the analysis window: {str(e)}")
    
    def _show_analysis_window_for_file(self, file_path):
        """
        Create and show an analysis window for a specific file.
        This is a separate method to ensure clean separation from dialogs.
        
        Args:
            file_path: Path to the MIDI file to analyze
        """
        try:
            # Import our new launcher module
            from ui.rhythm_analyzer_launcher import launch_analyzer_as_separate_process
            
            # Launch the window as a completely separate process
            # This completely eliminates window management issues
            launch_analyzer_as_separate_process(file_path)
            
        except ImportError as e:
            QMessageBox.critical(
                self, "Module Not Available", 
                f"The rhythm analysis module is not available: {str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"An error occurred while analyzing the file: {str(e)}"
            )
    
    def get_selected_music(self):
        """Get information about the selected music."""
        try:
            # If a file was selected directly in the upload tab
            if self.selected_music["file_path"]:
                return self.selected_music
                
            # If a file was selected in the list
            selected_items = self.list_widget.selectedItems()
            if selected_items and len(selected_items) > 0:
                row = self.list_widget.row(selected_items[0])
                
                if (row >= 0 and row < self.list_widget.rowCount() and
                    self.list_widget.item(row, 0) and 
                    self.list_widget.item(row, 1) and
                    self.list_widget.item(row, 2) and
                    self.list_widget.item(row, 3)):
                    
                    self.selected_music["title"] = self.list_widget.item(row, 0).text()
                    self.selected_music["rhythmic_style"] = self.list_widget.item(row, 1).text()
                    self.selected_music["instrument"] = self.list_widget.item(row, 2).text()
                    self.selected_music["mood"] = self.list_widget.item(row, 3).text()
                    
                    # If we have real dataset info, get the file path
                    if self.dataset_manager and hasattr(self.dataset_manager, 'metadata') and self.dataset_manager.metadata:
                        # Find the matching metadata record
                        title = self.selected_music["title"]
                        for item in self.dataset_manager.metadata:
                            file_path = item.get("filePath", "")
                            if file_path and os.path.splitext(os.path.basename(file_path))[0] == title:
                                self.selected_music["file_path"] = file_path
                                break
            
            return self.selected_music
        except Exception as e:
            logger.error(f"Error getting selected music: {e}")
            # Return a default selection in case of error
            return {
                "title": "Error selecting music",
                "file_path": "",
                "rhythmic_style": "",
                "instrument": "",
                "mood": ""
            }

    def _load_music_items(self):
        """Load music items into the list widget."""
        try:
            # Clear the existing items
            self.list_widget.setRowCount(0)
            
            # Load items from dataset manager if available
            if self.dataset_manager and hasattr(self.dataset_manager, 'metadata') and self.dataset_manager.metadata:
                # Use real data from the dataset manager
                for item in self.dataset_manager.metadata:
                    file_path = item.get("filePath", "")
                    if not file_path:
                        continue
                        
                    # Extract filename as title
                    title = os.path.splitext(os.path.basename(file_path))[0]
                    
                    # Get tags
                    tags = item.get("tags", {})
                    rhythmic_style = tags.get("rhythmicCharacter", "Moderately Rhythmic")
                    instrument = tags.get("primaryInstrument", "Piano")
                    mood = tags.get("mood", "Neutral")
                    
                    # Add to list widget
                    self._add_music_item(title, rhythmic_style, instrument, mood)
            else:
                # Use placeholder data
                placeholder_data = [
                    ("Bach - Air on G String", "Smooth & Flowing", "Strings", "Peaceful"),
                    ("Beethoven - Fur Elise", "Moderately Rhythmic", "Piano", "Relaxed"),
                    ("Mozart - Eine Kleine Nachtmusik", "Clear & Steady Beat", "Strings", "Cheerful"),
                    ("Vivaldi - Spring", "Moderately Rhythmic", "Strings", "Energetic"),
                    ("Chopin - Nocturne Op. 9 No. 2", "Smooth & Flowing", "Piano", "Melancholic"),
                    ("Debussy - Clair de Lune", "Smooth & Flowing", "Piano", "Peaceful"),
                    ("Beethoven - 5th Symphony", "Clear & Steady Beat", "Orchestra", "Intense"),
                    ("Mozart - Rondo Alla Turca", "Groovy & Syncopated", "Piano", "Energetic"),
                    ("Paganini - La Campanella", "Groovy & Syncopated", "Violin", "Uplifting")
                ]
                
                # Add placeholder data to list widget
                for title, rhythmic_style, instrument, mood in placeholder_data:
                    self._add_music_item(title, rhythmic_style, instrument, mood)
                    
            # Apply initial filters
            self._apply_filters()
                
        except Exception as e:
            logger.error(f"Error loading music items: {e}")
            # Add a single error item to indicate the problem
            self.list_widget.setRowCount(1)
            self.list_widget.setItem(0, 0, QTableWidgetItem("Error loading music items"))
            self.list_widget.setItem(0, 1, QTableWidgetItem(""))
            self.list_widget.setItem(0, 2, QTableWidgetItem(""))
            self.list_widget.setItem(0, 3, QTableWidgetItem(""))
    
    def _add_music_item(self, title, rhythmic_style, instrument, mood):
        """Add a music item to the list widget."""
        row = self.list_widget.rowCount()
        self.list_widget.insertRow(row)
        self.list_widget.setItem(row, 0, QTableWidgetItem(title))
        self.list_widget.setItem(row, 1, QTableWidgetItem(rhythmic_style))
        self.list_widget.setItem(row, 2, QTableWidgetItem(instrument))
        self.list_widget.setItem(row, 3, QTableWidgetItem(mood))


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ras_application.log')
    ]
)

logger = logging.getLogger(__name__)


class FocusHandlingWidget(QWidget):
    """Custom widget that handles focus events properly."""
    
    def __init__(self, parent=None):
        """Initialize the widget."""
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Track whether we're currently handling a click
        self.handling_click = False
        
    def mousePressEvent(self, event):
        """Handle mouse press events to clear focus from all widgets."""
        # Take focus first
        self.setFocus()
        
        # Set flag to prevent infinite recursion
        if self.handling_click:
            super().mousePressEvent(event)
            return
            
        self.handling_click = True
        
        try:
            # Clear focus from any other widget
            focused_widget = QApplication.focusWidget()
            if focused_widget and focused_widget is not self and hasattr(focused_widget, 'clearFocus'):
                focused_widget.clearFocus()
        finally:
            # Reset flag
            self.handling_click = False
            
        # Continue normal event processing
        super().mousePressEvent(event)


class DashboardWindow(QMainWindow):
    """Main dashboard window for the RAS-helper application with functional components."""
    
    def __init__(self):
        """Initialize the dashboard window."""
        super().__init__()
        
        # Create a menu bar but don't set it as the window's menu bar yet
        self._create_menu_bar()
        
        # Set window title and size
        self.setWindowTitle("RAS Helper - Gait Analysis & Rehabilitation")
        self.resize(1200, 900)
        
        # Enable tracking mouse events for focus management
        self.setMouseTracking(True)
        
        # Make the window resizable and maximize it to fit screen
        self.resize(1280, 800)
        self.setMinimumSize(1024, 600)  # Set a reasonable minimum size
        
        # Main widget and layout
        main_widget = FocusHandlingWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Create core components
        self.gait_analyzer = GaitAnalyzer()
        self.session_manager = SessionManager()
        
        # Create synchronizer for RAS
        self.synchronizer = GaitMusicSynchronizer(
            min_cadence=60.0,
            max_cadence=180.0,
            update_interval=0.5,
            gait_analyzer=self.gait_analyzer
        )
        
        # Register synchronizer callbacks
        self.synchronizer.on_tempo_change = self.handle_tempo_change
        self.synchronizer.on_gait_data_available = self.handle_gait_data_available
        self.synchronizer.on_sync_state_change = self.handle_sync_state_change
        
        # Create and connect session manager callbacks
        self.session_manager.on_state_changed(self.handle_session_state_changed)
        self.session_manager.on_time_updated(self.handle_session_time_updated)
        self.session_manager.on_session_saved(self.handle_session_saved)
        
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
        settings_button.clicked.connect(self.open_settings)
        top_layout.addWidget(settings_button)
        
        main_layout.addLayout(top_layout)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Create a scroll area for the whole content
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QFrame.NoFrame)
        
        # Create container for scrollable content
        scroll_content = QWidget()
        scroll_content_layout = QHBoxLayout(scroll_content)
        scroll_content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left panel with video feed and mode-specific controls
        left_panel = QVBoxLayout()
        
        # Create a container for the video feed to better control resizing
        video_container = QFrame()
        video_container.setFrameStyle(QFrame.StyledPanel)
        video_container.setStyleSheet("background-color: #333333;")
        video_container_layout = QVBoxLayout(video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Video feed with actual functionality - using the more robust fixed video feed implementation
        self.video_feed = FixedVideoFeedWidget()
        self.video_feed.setToolTip("Live video feed with pose estimation and gait analysis")
        
        # Ensure the video feed widget maintains 16:9 aspect ratio
        self.video_feed.setMinimumWidth(640)
        self.video_feed.setMinimumHeight(360)  # 16:9 ratio (640×360)
        
        # Add the video feed to its container
        video_container_layout.addWidget(self.video_feed)
        
        # Add the container to the left panel
        left_panel.addWidget(video_container, 3)  # 3:1 ratio with controls
        
        # Add camera control buttons
        camera_controls = QHBoxLayout()
        
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("Default Camera (0)")
        self.camera_combo.setToolTip("Select video source")
        camera_controls.addWidget(self.camera_combo)
        
        self.start_button = QPushButton("Start Camera")
        self.start_button.setToolTip("Start video capture")
        self.start_button.clicked.connect(self.start_video_capture)
        camera_controls.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Camera")
        self.stop_button.setToolTip("Stop video capture")
        self.stop_button.clicked.connect(self.stop_video_capture)
        self.stop_button.setEnabled(False)
        camera_controls.addWidget(self.stop_button)
        
        left_panel.addLayout(camera_controls)
        
        # Stacked widget for mode-specific controls
        self.controls_stack = QStackedWidget()
        self.controls_stack.setToolTip("Mode-specific controls that change based on selected mode")
        
        # Clinical Assessment controls
        self.clinical_controls = FunctionalClinicalAssessmentControls()
        self.controls_stack.addWidget(self.clinical_controls)
        
        # Rehabilitation Training controls
        self.rehab_controls = RehabilitationControlsExtended()
        self.controls_stack.addWidget(self.rehab_controls)
        
        # Research Mode controls
        self.research_controls = ResearchControlsWidget()
        self.controls_stack.addWidget(self.research_controls)
        
        # RAS controls
        self.ras_controls = RASControlWidgetExtended()
        self.controls_stack.addWidget(self.ras_controls)
        
        left_panel.addWidget(self.controls_stack, 1)  # Smaller portion
        
        # Add the left panel to the scroll content
        scroll_content_layout.addLayout(left_panel, 7)  # 70% of width
        
        # Right panel with mode-specific views
        right_panel = QVBoxLayout()
        
        # Splitter for better control of panel heights
        right_splitter = QSplitter(Qt.Vertical)
        
        # Stacked widget for mode-specific data views
        self.data_stack = QStackedWidget()
        self.data_stack.setToolTip("Mode-specific data visualization")
        
        # Clinical Assessment data view - use actual gait analysis widget from gait_analysis_widget.py
        self.clinical_data = GaitAnalysisWidget()
        self.data_stack.addWidget(self.clinical_data)
        
        # Rehabilitation Training data view
        self.rehab_data = ProgressTrackingWidget()
        self.data_stack.addWidget(self.rehab_data)
        
        # Research Mode data view
        self.research_data = RawDataWidget()
        self.data_stack.addWidget(self.research_data)
        
        # Add the data stack to the right splitter
        right_splitter.addWidget(self.data_stack)
        
        # Status information (common to all modes)
        self.status_widget = StatusWidget()
        # Add status widget to the splitter
        right_splitter.addWidget(self.status_widget)
        
        # Tabs for additional information
        info_tabs = QTabWidget()
        
        # Patient info tab
        patient_tab = QWidget()
        patient_layout = QVBoxLayout(patient_tab)
        patient_layout.addWidget(QLabel("Patient ID: PT12345"))
        patient_layout.addWidget(QLabel("Name: John Doe"))
        patient_layout.addWidget(QLabel("Age: 45"))
        patient_layout.addWidget(QLabel("Diagnosis: Post-Stroke Gait"))
        patient_layout.addWidget(QLabel("Height: 175 cm"))
        patient_layout.addWidget(QLabel("Weight: 70 kg"))
        patient_layout.addStretch()
        info_tabs.addTab(patient_tab, "Patient Info")
        
        # Protocol tab
        protocol_tab = QWidget()
        protocol_layout = QVBoxLayout(protocol_tab)
        protocol_layout.addWidget(QLabel("Protocol: Standard RAS"))
        protocol_layout.addWidget(QLabel("Duration: 15 minutes"))
        protocol_layout.addWidget(QLabel("Target Cadence: 110 steps/min"))
        protocol_layout.addWidget(QLabel("Session: 3 of 12"))
        protocol_layout.addStretch()
        info_tabs.addTab(protocol_tab, "Protocol")
        
        # Add tabs to the splitter
        right_splitter.addWidget(info_tabs)
        
        # Set the initial sizes for the splitter sections - adjust for better proportions
        # Reduce the parameter panel height to just fit the content, increase system log height
        right_splitter.setSizes([300, 250, 150])
        
        # Add the splitter to the right panel
        right_panel.addWidget(right_splitter)
        
        # Add right panel to the scroll content
        scroll_content_layout.addLayout(right_panel, 3)  # 30% of width
        
        # Set the widget for the scroll area
        content_scroll.setWidget(scroll_content)
        
        # Add the scroll area to the main layout
        main_layout.addWidget(content_scroll)
        
        # Status bar
        self.statusBar().showMessage("Ready | Session Duration: 00:00")
        
        # Connect signals from video feed to gait analysis widget
        # Enable direct connection between video feed and gait analysis widget
        self.video_feed.pose_data_updated.connect(self.handle_pose_data)
        self.video_feed.frame_updated.connect(self.process_frame_for_gait_analysis)
        
        # Connect assessment control buttons
        self.clinical_controls.record_button.clicked.connect(self.start_assessment)
        self.clinical_controls.stop_button.clicked.connect(self.stop_assessment)
        self.clinical_controls.save_button.clicked.connect(self.save_assessment)
        
        # Connect RAS buttons
        self._connect_ras_buttons()
        
        # Setup camera options
        self.setup_camera_sources()
        
        # Initialize timers
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self.update_session_time)
        self.session_start_time = 0
        self.session_duration = 0
        
        # Setup session timer
        self.session_update_timer = QTimer(self)
        self.session_update_timer.timeout.connect(self.update_session_manager)
        self.session_update_timer.start(200)  # Update 5 times per second
        
        # Install a global event filter to properly manage focus
        app = QApplication.instance()
        app.installEventFilter(self)
        
        # Set initial mode
        self.switch_mode(0)  # Clinical Assessment mode by default
        
        # Add initial log message
        self.add_log_message("[INFO] System initialized successfully")

    # Add new method to handle log messages
    def add_log_message(self, message):
        """
        Add a message to the system log.
        
        Args:
            message: The log message to add
        """
        logger.info(message.replace('[INFO] ', '').replace('[ERROR] ', '').replace('[WARNING] ', ''))
        
        # Add to status widget log
        if hasattr(self, 'status_widget') and hasattr(self.status_widget, 'log_text'):
            self.status_widget.log_text.append(message)
            
        # Add to clinical assessment controls log if it exists
        if hasattr(self, 'clinical_controls') and hasattr(self.clinical_controls, 'log_text'):
            self.clinical_controls.log_text.append(message)
            
    def handle_pose_data(self, keypoints, gait_data=None):
        """
        Process pose keypoints and gait data from the video feed.
        
        Args:
            keypoints: Pose keypoints from pose estimation
            gait_data: Optional gait parameters if available
        """
        try:
            # If we received keypoints but no gait data, analyze them
            if keypoints and not gait_data and self.gait_analyzer:
                try:
                    gait_data = self.gait_analyzer.process_keypoints(keypoints, time.time())
                except Exception as e:
                    logger.error(f"Error analyzing gait data: {e}")
            
            # Ensure we have a dictionary to avoid type errors
            if gait_data is None:
                gait_data = {}
            
            # Store last gait data for session manager updates
            self.last_gait_data = gait_data
            
            # If we have an active session, add the data
            if self.session_manager.get_current_state() == SessionState.RECORDING:
                if keypoints:
                    self.session_manager.add_keypoint_data(keypoints)
                
                if gait_data:
                    self.session_manager.add_gait_data(gait_data)
                    
                    # If we're in RAS mode and the synchronizer is not paused, update gait data
                    current_session = self.session_manager.get_current_session()
                    if current_session and current_session.session_type == SessionType.RAS:
                        if self.synchronizer.sync_state not in [SyncState.PAUSED, SyncState.ERROR]:
                            self.synchronizer.update_gait_data(gait_data)
            
            # Update the gait analysis widget with keypoints and gait data
            if hasattr(self.clinical_data, 'update_gait_data'):
                self.clinical_data.update_gait_data(keypoints or {}, gait_data)
        
        except Exception as e:
            logger.error(f"Error handling pose data: {e}")
            
    def process_frame_for_gait_analysis(self, frame):
        """Process frames from the video feed for gait analysis."""
        # This method is kept for backward compatibility, but pose estimation is now handled
        # directly in the FixedVideoFeedWidget, so we don't need to do anything here.
        pass
    
    def _connect_ras_buttons(self):
        """Connect RAS control buttons to handlers."""
        # Clinical Assessment mode buttons - now directly connected in constructor
        # Skip this part now since we directly connect in the constructor
        
        # Rehabilitation Training mode buttons
        rehab_buttons = getattr(self.rehab_controls, 'button_layout', None)
        if rehab_buttons:
            for i in range(rehab_buttons.count()):
                widget = rehab_buttons.itemAt(i).widget()
                if isinstance(widget, QPushButton):
                    if "START" in widget.text():
                        widget.clicked.connect(self.start_rehabilitation)
                    elif "STOP" in widget.text():
                        widget.clicked.connect(self.stop_rehabilitation)
        
        # RAS control buttons (common)
        ras_buttons = getattr(self.ras_controls, 'button_layout', None)
        if ras_buttons:
            for i in range(ras_buttons.count()):
                widget = ras_buttons.itemAt(i).widget()
                if isinstance(widget, QPushButton):
                    if "Start" in widget.text():
                        widget.clicked.connect(self.start_ras)
                    elif "Stop" in widget.text():
                        widget.clicked.connect(self.stop_ras)
                    elif "Reset" in widget.text():
                        widget.clicked.connect(self.reset_ras)
        
        # Connect sync-specific buttons
        if hasattr(self.ras_controls, 'confirm_button'):
            self.ras_controls.confirm_button.clicked.connect(self.confirm_gait_tempo)
            
        if hasattr(self.ras_controls, 'modify_button'):
            self.ras_controls.modify_button.clicked.connect(self.open_modify_tempo_dialog)
            
        if hasattr(self.ras_controls, 'decrease_button'):
            self.ras_controls.decrease_button.clicked.connect(lambda: self.adjust_tempo_percentage(-10))
            
        if hasattr(self.ras_controls, 'increase_button'):
            self.ras_controls.increase_button.clicked.connect(lambda: self.adjust_tempo_percentage(10))
            
        if hasattr(self.ras_controls, 'pause_button'):
            self.ras_controls.pause_button.clicked.connect(self.pause_ras)
            
        if hasattr(self.ras_controls, 'resume_button'):
            self.ras_controls.resume_button.clicked.connect(self.resume_ras)
    
    def start_assessment(self):
        """Start a clinical assessment session."""
        if not self.video_feed.is_running:
            QMessageBox.warning(self, "Camera Required", 
                              "Please start the camera before beginning an assessment.")
            return
        
        logger.info("Starting clinical assessment")
        
        # Get selected protocol
        protocol_text = self.clinical_controls.protocol_combo.currentText()
        duration = self.clinical_controls.duration_spin.value()
        
        # Map protocol text to session type
        session_type_map = {
            "Standard Gait": SessionType.STANDARD_GAIT,
            "6-Minute Walk": SessionType.SIX_MINUTE_WALK, 
            "10m Walk Test": SessionType.TEN_METER_WALK,
            "Timed Up & Go": SessionType.TIMED_UP_AND_GO
        }
        
        session_type = session_type_map.get(protocol_text, SessionType.ASSESSMENT)
        
        # Set up parameters for the session
        parameters = {
            "duration_minutes": duration,
            "compare_to_baseline": self.clinical_controls.compare_checkbox.isChecked()
        }
        
        # Create dummy patient info (would come from patient database in a real app)
        patient_info = {
            "id": "PT12345",
            "name": "John Doe",
            "age": 45,
            "diagnosis": "Post-Stroke Gait",
            "height": 175,
            "weight": 70
        }
        
        # Start the session using the session manager
        success = self.session_manager.start_session(
            session_type=session_type,
            protocol_name=protocol_text,
            parameters=parameters,
            patient_info=patient_info
        )
        
        if success:
            # Update UI to show recording state
            self.clinical_controls.start_recording()
            
            # Notify the gait analysis widget that recording has started
            if hasattr(self.clinical_data, 'set_recording_status'):
                self.clinical_data.set_recording_status(True)
            
            # Additional UI updates specific to assessment
            self.statusBar().showMessage(f"Recording {protocol_text} assessment")
        else:
            QMessageBox.warning(self, "Session Error", 
                              "Could not start assessment session. Check the logs for details.")
    
    def stop_assessment(self):
        """Stop the current clinical assessment session."""
        logger.info("Stopping clinical assessment")
        
        # Stop the session using the session manager
        success = self.session_manager.stop_session()
        
        if success:
            # Update UI components
            self.clinical_controls.stop_recording()
            
            # Notify the gait analysis widget that recording has stopped
            if hasattr(self.clinical_data, 'set_recording_status'):
                self.clinical_data.set_recording_status(False)
            
            # Reset the gait analysis widget visualization (optional)
            if hasattr(self.clinical_data, 'reset'):
                self.clinical_data.reset()
        else:
            QMessageBox.warning(self, "Session Error", 
                              "Could not stop assessment session. Check the logs for details.")
    
    def save_assessment(self):
        """Save the results of a clinical assessment."""
        logger.info("Saving clinical assessment results")
        
        # Get notes from the text field
        notes = self.clinical_controls.notes_text.toPlainText()
        
        # Save the session using the session manager
        success = self.session_manager.save_session(notes=notes)
        
        if success:
            # Update UI after saving
            # Most UI updates are now handled by the session state change callback
            self.clinical_controls.save_results()
        else:
            QMessageBox.warning(self, "Session Error", 
                              "Could not save assessment results. Check the logs for details.")
    
    def start_rehabilitation(self):
        """Start a rehabilitation training session."""
        if not self.video_feed.is_running:
            QMessageBox.warning(self, "Camera Required", 
                              "Please start the camera before beginning rehabilitation training.")
            return
            
        logger.info("Starting rehabilitation training")
        
        # Get selected training protocol and parameters
        protocol_text = self.rehab_controls.protocol_combo.currentText()
        duration = self.rehab_controls.duration_spin.value()
        difficulty = self.rehab_controls.difficulty_slider.value()
        
        # Map protocol text to session type
        session_type_map = {
            "Standard Training": SessionType.STANDARD_TRAINING,
            "Obstacle Course": SessionType.OBSTACLE_COURSE,
            "Balance Training": SessionType.BALANCE_TRAINING,
            "Endurance Training": SessionType.ENDURANCE_TRAINING
        }
        
        session_type = session_type_map.get(protocol_text, SessionType.REHABILITATION)
        
        # Get selected music information
        selected_music = "Default Music"
        if hasattr(self.rehab_controls, 'music_label'):
            current_music = self.rehab_controls.music_label.text()
            if current_music != "No music selected":
                selected_music = current_music
        
        # Set up parameters for the session
        parameters = {
            "duration_minutes": duration,
            "difficulty_level": difficulty,
            "selected_music": selected_music,
            "audio_feedback": self.rehab_controls.audio_checkbox.isChecked(),
            "visual_feedback": self.rehab_controls.visual_checkbox.isChecked()
        }
        
        # Create dummy patient info (would come from patient database in a real app)
        patient_info = {
            "id": "PT12345",
            "name": "John Doe",
            "age": 45,
            "diagnosis": "Post-Stroke Gait",
            "height": 175,
            "weight": 70
        }
        
        # Start the session using the session manager
        success = self.session_manager.start_session(
            session_type=session_type,
            protocol_name=protocol_text,
            parameters=parameters,
            patient_info=patient_info
        )
        
        if success:
            # Update UI to show training state
            # Most UI updates are handled by the session state change callback
            self.rehab_controls.start_training()
            
            # Additional UI updates specific to rehabilitation (not handled by session manager)
            self.statusBar().showMessage(f"Rehabilitation training: {protocol_text}")
        else:
            QMessageBox.warning(self, "Session Error", 
                              "Could not start rehabilitation session. Check the logs for details.")
    
    def stop_rehabilitation(self):
        """Stop the current rehabilitation training session."""
        logger.info("Stopping rehabilitation training")
        
        # Stop the session using the session manager
        success = self.session_manager.stop_session()
        
        if success:
            # Additional UI updates specific to stopping rehabilitation
            # Most UI updates are now handled by the session state change callback
            self.rehab_controls.stop_training()
        else:
            QMessageBox.warning(self, "Session Error", 
                              "Could not stop rehabilitation session. Check the logs for details.")
    
    def start_ras(self):
        """Start rhythmic auditory stimulation (RAS)."""
        if not self.video_feed.is_running:
            QMessageBox.warning(self, "Camera Required", 
                              "Please start the camera before beginning RAS.")
            return
            
        logger.info("Starting rhythmic auditory stimulation (RAS)")
        
        # Get RAS parameters
        bpm = self.ras_controls.bpm_spin.value()
        sound_type = self.ras_controls.sound_combo.currentText()
        duration = self.ras_controls.duration_spin.value()
        
        # Set up parameters for the session
        parameters = {
            "duration_minutes": duration,
            "bpm": bpm,
            "sound_type": sound_type,
            "adaptive": self.ras_controls.adaptive_checkbox.isChecked(),
            "volume": self.ras_controls.volume_slider.value()
        }
        
        # Create dummy patient info (would come from patient database in a real app)
        patient_info = {
            "id": "PT12345",
            "name": "John Doe",
            "age": 45,
            "diagnosis": "Post-Stroke Gait",
            "height": 175,
            "weight": 70
        }
        
        # Reset synchronizer and set initial tempo
        self.synchronizer.set_tempo_directly(bpm)
        
        # Start the session using the session manager
        success = self.session_manager.start_session(
            session_type=SessionType.RAS,
            protocol_name="Rhythmic Auditory Stimulation",
            parameters=parameters,
            patient_info=patient_info
        )
        
        if success:
            # Initialize the music processor with default MIDI file
            midi_file = "resources/metronome.mid"  # Default MIDI file path
            if sound_type == "Drum Beat":
                midi_file = "resources/drums.mid"
            elif "Music Track" in sound_type:
                track_num = sound_type.split()[-1]
                midi_file = f"resources/music_track_{track_num}.mid"
                
            # Start playback with current tempo
            playback_success = self.synchronizer.start_playback(midi_file)
            
            if not playback_success:
                QMessageBox.warning(self, "Playback Error", 
                                  "Failed to start music playback. Check MIDI file availability.")
                self.session_manager.cancel_session()
                return
            
            # Update UI to show RAS is active
            self.ras_controls.start_ras()
            
            # Additional UI updates specific to RAS
            self.statusBar().showMessage(f"RAS active: {bpm} BPM, {sound_type}")
        else:
            QMessageBox.warning(self, "Session Error", 
                              "Could not start RAS session. Check the logs for details.")
    
    def stop_ras(self):
        """Stop rhythmic auditory stimulation (RAS)."""
        logger.info("Stopping rhythmic auditory stimulation (RAS)")
        
        # Stop the synchronizer playback
        self.synchronizer.stop_playback()
        
        # Stop the session using the session manager
        success = self.session_manager.stop_session()
        
        if success:
            # Additional UI updates specific to stopping RAS
            self.ras_controls.stop_ras()
        else:
            QMessageBox.warning(self, "Session Error", 
                              "Could not stop RAS session. Check the logs for details.")
    
    def reset_ras(self):
        """Reset the RAS module to default settings."""
        logger.info("Resetting RAS module")
        
        # Only reset if not in an active session
        if self.session_manager.get_current_state() != SessionState.IDLE:
            QMessageBox.warning(self, "Session Active", 
                              "Please stop the current session before resetting RAS settings.")
            return
            
        # Reset RAS controls to default values
        self.ras_controls.reset_controls()
        
        # Reset synchronizer
        self.synchronizer.stop_playback()
        self.synchronizer.set_tempo_directly(120)  # Reset to default 120 BPM
        
        self.statusBar().showMessage("RAS settings reset to defaults", 3000)
    
    def setup_camera_sources(self):
        """Detect and populate available camera sources."""
        try:
            # List available cameras
            available_cameras = []
            for i in range(5):  # Check first 5 camera indices
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available_cameras.append(i)
                    cap.release()
            
            # Clear and update combo box
            self.camera_combo.clear()
            
            if not available_cameras:
                self.camera_combo.addItem("Default Camera (0)")
            else:
                for idx in available_cameras:
                    self.camera_combo.addItem(f"Camera {idx}")
            
        except Exception as e:
            logger.error(f"Error detecting cameras: {e}")
            self.camera_combo.clear()
            self.camera_combo.addItem("Default Camera (0)")
    
    def start_video_capture(self):
        """Start video capture from selected source."""
        if self.video_feed.is_running:
            return
            
        try:
            self.video_feed.start_capture()
            
            # Update UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
            # Log event
            self.add_log_message("[INFO] Camera started")
            
        except Exception as e:
            # Log error
            self.add_log_message(f"[ERROR] Failed to start camera: {e}")
            logger.error(f"Failed to start video capture: {e}")
            
    def stop_video_capture(self):
        """Stop video capture."""
        if not self.video_feed.is_running:
            return
            
        try:
            self.video_feed.stop_capture()
            
            # Update UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            # Log event
            self.add_log_message("[INFO] Camera stopped")
            
        except Exception as e:
            # Log error
            self.add_log_message(f"[ERROR] Failed to stop camera: {e}")
            logger.error(f"Failed to stop video capture: {e}")
    
    def update_session_time(self):
        """Update the session duration timer."""
        self.session_duration += 1
        minutes = self.session_duration // 60
        seconds = self.session_duration % 60
        
        time_str = f"{minutes:02d}:{seconds:02d}"
        self.statusBar().showMessage(f"Session Duration: {time_str}")
    
    def switch_mode(self, mode_index):
        """Switch between different application modes."""
        # Update control panel
        self.controls_stack.setCurrentIndex(mode_index)
        
        # Update data display
        self.data_stack.setCurrentIndex(mode_index)
        
        # Update video feed label based on mode
        mode_names = ["Clinical Assessment", "Rehabilitation Training", "Research"]
        self.video_feed.feed_label.setText(f"Video Feed - {mode_names[mode_index]} Mode")
        
        # Update window title
        self.setWindowTitle(f"RAS-helper - {mode_names[mode_index]} Mode")
        
        # If in Clinical Assessment mode, hide the status widget since it's already in the controls
        if mode_index == 0:
            self.status_widget.hide()
        else:
            self.status_widget.show()
        
        # Update status bar
        mode_status = [
            "Ready for patient assessment",
            "Ready to begin rehabilitation session",
            "Research mode active - data collection ready"
        ]
        self.statusBar().showMessage(f"{mode_status[mode_index]} | Session Duration: 00:00")
        
        logger.info(f"Switched to {mode_names[mode_index]} mode")
    
    def open_settings(self):
        """Open settings dialog."""
        QMessageBox.information(self, "Settings", "Settings dialog will be implemented here.")
    
    def handle_session_state_changed(self, old_state, new_state):
        """
        Handle session state changes.
        
        Args:
            old_state: Previous session state
            new_state: New session state
        """
        logger.info(f"Session state changed: {old_state} -> {new_state}")
        
        # Log the state change
        self.add_log_message(f"[INFO] Session state: {new_state}")
        
        # Update UI based on new state
        if new_state == SessionState.RECORDING:
            # Session is actively recording
            self.statusBar().showMessage(f"Recording in progress")
            
            # Update clinical controls if in assessment mode
            if self.mode_combo.currentIndex() == 0:
                self.clinical_controls.record_button.setEnabled(False)
                self.clinical_controls.stop_button.setEnabled(True)
                self.clinical_controls.save_button.setEnabled(False)
                
                # Update recording indicator in gait analysis widget
                if hasattr(self.clinical_data, 'set_recording_status'):
                    self.clinical_data.set_recording_status(True)
                    
        elif new_state == SessionState.PAUSED:
            # Session is paused
            self.statusBar().showMessage("Recording paused")
            
        elif new_state == SessionState.STOPPED or new_state == SessionState.COMPLETED:
            # Session has stopped or completed
            if new_state == SessionState.STOPPED:
                self.statusBar().showMessage("Recording stopped")
            else:
                self.statusBar().showMessage("Recording completed")
                
            # Update clinical controls if in assessment mode
            if self.mode_combo.currentIndex() == 0:
                self.clinical_controls.record_button.setEnabled(True)
                self.clinical_controls.stop_button.setEnabled(False)
                self.clinical_controls.save_button.setEnabled(True)
                
                # Update recording indicator in gait analysis widget
                if hasattr(self.clinical_data, 'set_recording_status'):
                    self.clinical_data.set_recording_status(False)
                    
        elif new_state == SessionState.SAVING:
            # Session is being saved
            self.statusBar().showMessage("Saving session data...")
            
        elif new_state == SessionState.IDLE:
            # No active session
            self.statusBar().showMessage("Ready")
            
            # Reset UI elements if coming from a completed session
            if old_state in [SessionState.SAVING, SessionState.STOPPED, SessionState.COMPLETED]:
                if self.mode_combo.currentIndex() == 0:
                    self.clinical_controls.record_button.setEnabled(True)
                    self.clinical_controls.stop_button.setEnabled(False)
                    self.clinical_controls.save_button.setEnabled(False)
                    
                    # Reset recording indicator in gait analysis widget
                    if hasattr(self.clinical_data, 'set_recording_status'):
                        self.clinical_data.set_recording_status(False)
    
    def handle_session_time_updated(self, seconds, formatted_time):
        """
        Handle session time updates.
        
        Args:
            seconds: Elapsed time in seconds
            formatted_time: Formatted time string (MM:SS)
        """
        # Update elapsed time display in clinical controls if in assessment mode
        if self.mode_combo.currentIndex() == 0:
            self.clinical_controls.elapsed_time.setText(formatted_time)
            
        # Update status bar
        current_message = self.statusBar().currentMessage()
        if "Recording" in current_message:
            # Keep the current message but append the time
            base_message = current_message.split(" | ")[0]
            self.statusBar().showMessage(f"{base_message} | Time: {formatted_time}")
    
    def handle_session_saved(self, file_path):
        """
        Handle session saved event.
        
        Args:
            file_path: Path where the session was saved
        """
        logger.info(f"Session saved to: {file_path}")
        QMessageBox.information(self, "Session Saved", 
                              f"Session data has been saved to:\n{file_path}")
    
    def update_session_manager(self):
        """Update the session manager timer and process any gait data."""
        # Update the session timer
        self.session_manager.update_timer()
        
        # If we have gait data and a recording session, add the data
        if hasattr(self, 'gait_analyzer') and hasattr(self, 'last_gait_data'):
            if self.session_manager.get_current_state() == SessionState.RECORDING:
                self.session_manager.add_gait_data(self.last_gait_data)
    
    def eventFilter(self, obj, event):
        """Global event filter to manage focus."""
        if event.type() == event.MouseButtonPress:
            # Check if clicking outside of text edit or spin box
            clicked_widget = QApplication.widgetAt(event.globalPos())
            focused_widget = QApplication.focusWidget()
            
            # If we have a focused input widget and we click outside any input widgets
            if (focused_widget and 
                isinstance(focused_widget, (QTextEdit, QSpinBox, QDoubleSpinBox)) and
                (not clicked_widget or not isinstance(clicked_widget, (QTextEdit, QSpinBox, QDoubleSpinBox)))):
                # Clear focus from the input widget
                focused_widget.clearFocus()
                
                # Set focus to the main widget if possible
                if hasattr(self, 'centralWidget') and self.centralWidget():
                    self.centralWidget().setFocus()
                    
        return super().eventFilter(obj, event)
    
    def mousePressEvent(self, event):
        """Handle mouse press events to manage focus."""
        # Clear focus from any widget to prevent "always active" input fields
        focused_widget = QApplication.focusWidget()
        if focused_widget:
            focused_widget.clearFocus()
        
        # Allow normal event processing to continue
        super().mousePressEvent(event)
    
    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Stop any active sessions
            if self.session_manager.get_current_state() != SessionState.IDLE:
                # Ask user if they want to save before closing
                reply = QMessageBox.question(
                    self, 'Confirm Close', 
                    'There is an active session. Would you like to save before closing?',
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, 
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Cancel:
                    event.ignore()
                    return
                
                if reply == QMessageBox.Yes:
                    self.session_manager.stop_session()
                    self.session_manager.save_session()
                else:
                    self.session_manager.cancel_session()
            
            # Stop video feed
            if self.video_feed.is_running:
                self.video_feed.stop_capture()
                
            # Stop synchronizer playback if active
            self.synchronizer.stop_playback()
            
            # Accept the close event
            event.accept()
            
        except Exception as e:
            logger.error(f"Error during window close: {e}")
            event.accept()  # Always close, even if error

    def pause_ras(self):
        """Pause RAS playback."""
        logger.info("Pausing RAS playback")
        self.synchronizer.pause_playback()
        self.ras_controls.pause_ras()
        self.statusBar().showMessage("RAS playback paused")
    
    def resume_ras(self):
        """Resume RAS playback."""
        logger.info("Resuming RAS playback")
        self.synchronizer.resume_playback()
        self.ras_controls.resume_ras()
        self.statusBar().showMessage("RAS playback resumed")
    
    def confirm_gait_tempo(self, modified_cadence=None):
        """
        Confirm the pending gait tempo for RAS.
        
        Args:
            modified_cadence: Optional modified cadence value
        """
        if self.synchronizer.sync_state != SyncState.WAITING_CONFIRMATION:
            logger.warning("No gait tempo waiting for confirmation")
            return
            
        success = self.synchronizer.confirm_gait_data(modified_cadence)
        if success:
            logger.info(f"Confirmed gait tempo: {self.synchronizer.current_tempo} BPM")
            
            # Update the UI with the confirmed tempo
            if self.ras_controls.bpm_spin:
                self.ras_controls.bpm_spin.setValue(self.synchronizer.current_tempo)
                
            self.statusBar().showMessage(f"Tempo confirmed: {self.synchronizer.current_tempo} BPM")
        else:
            logger.warning("Failed to confirm gait tempo")
            self.statusBar().showMessage("Failed to confirm tempo")
    
    def open_modify_tempo_dialog(self):
        """Open a dialog to modify detected tempo before confirming."""
        if self.synchronizer.sync_state != SyncState.WAITING_CONFIRMATION or not self.synchronizer.pending_gait_data:
            return
            
        # Get current detected cadence
        current_cadence = self.synchronizer.pending_gait_data.cadence
        
        # Create simple number input dialog
        from PyQt5.QtWidgets import QInputDialog
        modified_cadence, ok = QInputDialog.getDouble(
            self, "Modify Tempo", 
            "Enter modified tempo (BPM):", 
            current_cadence, 
            self.synchronizer.min_cadence, 
            self.synchronizer.max_cadence, 
            1
        )
        
        if ok:
            self.confirm_gait_tempo(modified_cadence)
    
    def adjust_tempo_percentage(self, percentage):
        """
        Adjust the current tempo by a percentage.
        
        Args:
            percentage: Percentage change (-100 to 100)
        """
        success = self.synchronizer.adjust_tempo_percentage(percentage)
        if success:
            logger.info(f"Adjusted tempo by {percentage}%: {self.synchronizer.current_tempo} BPM")
            
            # Update the UI with the new tempo
            if self.ras_controls.bpm_spin:
                self.ras_controls.bpm_spin.setValue(self.synchronizer.current_tempo)
                
            self.statusBar().showMessage(f"Tempo adjusted: {self.synchronizer.current_tempo} BPM")
        else:
            logger.warning(f"Failed to adjust tempo by {percentage}%")
            self.statusBar().showMessage("Failed to adjust tempo")
    
    def handle_tempo_change(self, new_tempo):
        """
        Handle tempo change events from the synchronizer.
        
        Args:
            new_tempo: New tempo in BPM
        """
        # Update the tempo spinner if available
        if self.ras_controls.bpm_spin:
            self.ras_controls.bpm_spin.setValue(new_tempo)
            
        # Update status bar
        self.statusBar().showMessage(f"Tempo updated: {new_tempo} BPM")
    
    def handle_gait_data_available(self, gait_data):
        """
        Handle gait data available events from the synchronizer.
        
        Args:
            gait_data: GaitData object with current gait parameters
        """
        # Update the RAS controls to show pending gait data
        self.ras_controls.update_pending_gait_data(gait_data)
        
        # Show notification in status bar
        if gait_data:
            self.statusBar().showMessage(
                f"New gait data available: {gait_data.cadence:.1f} steps/min, "
                f"confidence: {gait_data.confidence:.2f}"
            )
    
    def handle_sync_state_change(self, new_state):
        """
        Handle synchronization state change events from the synchronizer.
        
        Args:
            new_state: New SyncState value
        """
        # Update the RAS controls based on sync state
        self.ras_controls.update_sync_state(new_state)
        
        # Update status bar
        self.statusBar().showMessage(f"RAS state: {new_state.name}")
        
        # Handle specific state transitions
        if new_state == SyncState.ERROR:
            QMessageBox.warning(self, "RAS Error", 
                              "An error occurred in the RAS synchronization. Check the logs for details.")

    def _create_menu_bar(self):
        """Create the menu bar with all menus and actions."""
        self.menu_bar = self.menuBar()
        
        # File menu
        file_menu = self.menu_bar.addMenu("&File")
        
        # File actions
        new_session_action = file_menu.addAction("&New Session")
        new_session_action.setStatusTip("Create a new session")
        
        open_session_action = file_menu.addAction("&Open Session...")
        open_session_action.setStatusTip("Open an existing session")
        
        file_menu.addSeparator()
        
        save_session_action = file_menu.addAction("&Save Session")
        save_session_action.setStatusTip("Save the current session")
        
        save_as_action = file_menu.addAction("Save Session &As...")
        save_as_action.setStatusTip("Save the current session with a new name")
        
        file_menu.addSeparator()
        
        export_data_action = file_menu.addAction("&Export Data...")
        export_data_action.setStatusTip("Export session data to various formats")
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("E&xit")
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        
        # Edit menu
        edit_menu = self.menu_bar.addMenu("&Edit")
        
        preferences_action = edit_menu.addAction("&Preferences...")
        preferences_action.setStatusTip("Configure application settings")
        preferences_action.triggered.connect(self.open_settings)
        
        # View menu
        view_menu = self.menu_bar.addMenu("&View")
        
        fullscreen_action = view_menu.addAction("&Fullscreen")
        fullscreen_action.setStatusTip("Toggle fullscreen mode")
        
        # Tools menu
        tools_menu = self.menu_bar.addMenu("&Tools")
        
        # MIDI Player action
        midi_player_action = tools_menu.addAction("MIDI &Player")
        midi_player_action.setStatusTip("Open the standalone MIDI player")
        midi_player_action.triggered.connect(self._launch_midi_player)
        
        # Rhythm Analysis action
        rhythm_analysis_action = tools_menu.addAction("&Rhythm Analyzer")
        rhythm_analysis_action.setStatusTip("Open the music rhythm analysis tool")
        rhythm_analysis_action.triggered.connect(self._launch_rhythm_analyzer)
        
        # Help menu
        help_menu = self.menu_bar.addMenu("&Help")
        
        help_action = help_menu.addAction("&Help Contents")
        help_action.setStatusTip("Show the help contents")
        
        about_action = help_menu.addAction("&About")
        about_action.setStatusTip("Show information about the application")
        
        return self.menu_bar
    
    def _launch_midi_player(self):
        """Launch the standalone MIDI player."""
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            # Get the Python executable path
            python_executable = sys.executable
            
            # Get path to the run_midi_player.py script
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            player_script = project_root / "src" / "a_quick_player" / "run_midi_player.py"
            
            if not player_script.exists():
                logging.error(f"MIDI player script not found at {player_script}")
                QMessageBox.critical(self, "Error", "MIDI player executable not found.")
                return
            
            # Launch the player as a separate process
            subprocess.Popen([python_executable, str(player_script)])
            
        except Exception as e:
            logging.error(f"Error launching MIDI player: {e}")
            QMessageBox.critical(self, "Error", f"Could not launch MIDI player: {str(e)}")
    
    def _launch_rhythm_analyzer(self):
        """Launch the rhythm analyzer tool."""
        try:
            from ui.rhythm_analyzer_launcher import launch_analyzer_as_separate_process
            
            # Launch the analyzer without a specific file
            launch_analyzer_as_separate_process(None)
            
        except Exception as e:
            logging.error(f"Error launching rhythm analyzer: {e}")
            QMessageBox.critical(self, "Error", f"Could not launch rhythm analyzer: {str(e)}")


def main():
    """Launch the functional dashboard."""
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec_())


class FunctionalClinicalAssessmentControls(ClinicalAssessmentControls):
    """Functional extension of the ClinicalAssessmentControls UI component.
    """
    
    def __init__(self, parent=None):
        """Initialize clinical assessment controls with functional additions."""
        super().__init__(parent)
        
        # Install event filter for better focus management
        self.installEventFilter(self)
        
        # Connect protocol change signal
        if self.protocol_combo:
            self.protocol_combo.currentIndexChanged.connect(self.on_protocol_changed)
        
        # Timer for recording
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self.update_elapsed_time)
        self.recording_seconds = 0
        
        # Add system log to status group
        if hasattr(self, 'status_group') and self.status_group:
            status_layout = self.status_group.layout()
            
            # Add log label
            log_label = QLabel("System Log:")
            log_label.setToolTip("Recent system messages and events")
            status_layout.addWidget(log_label, 2, 0, 1, 4)
            
            # Add log text field
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setMaximumHeight(80)  # Increase from 60 to 80
            self.log_text.setToolTip("Log of system events and notifications")
            self.log_text.append("[INFO] System initialized")
            self.log_text.append("[INFO] Camera connected")
            self.log_text.append("[INFO] MediaPipe pose estimation ready")
            self.log_text.append("[INFO] FluidSynth audio engine loaded")
            status_layout.addWidget(self.log_text, 3, 0, 1, 4)
        
        # Initial state
        self.is_recording = False
        self.on_protocol_changed(0)  # Initialize UI based on default protocol
    
    def eventFilter(self, obj, event):
        """Filter events to handle focus."""
        if obj is self and event.type() == event.MouseButtonPress:
            # When clicking on empty areas of the group box, clear focus
            focused_widget = QApplication.focusWidget()
            if focused_widget and isinstance(focused_widget, (QTextEdit, QSpinBox, QDoubleSpinBox)):
                focused_widget.clearFocus()
                self.setFocus()
        return super().eventFilter(obj, event)
    
    def update_elapsed_time(self):
        """Update the elapsed time display during recording."""
        self.recording_seconds += 1
        minutes = self.recording_seconds // 60
        seconds = self.recording_seconds % 60
        self.elapsed_time.setText(f"{minutes:02d}:{seconds:02d}")
    
    def start_recording(self):
        """Start recording an assessment."""
        self.is_recording = True
        self.recording_seconds = 0
        self.elapsed_time.setText("00:00")
        self.recording_timer.start(1000)  # Update every second
        
        # Update button states
        self.record_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.save_button.setEnabled(False)
        
        # Disable protocol selection during recording
        self.protocol_combo.setEnabled(False)
        self.duration_spin.setEnabled(False)
    
    def stop_recording(self):
        """Stop recording the assessment."""
        self.is_recording = False
        self.recording_timer.stop()
        
        # Update button states
        self.record_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.save_button.setEnabled(True)
        
        # Re-enable protocol selection
        self.protocol_combo.setEnabled(True)
        # Only enable duration spin if Standard Gait is selected
        self.on_protocol_changed(self.protocol_combo.currentIndex())
    
    def save_results(self):
        """Save the assessment results."""
        # Reset UI after saving
        self.save_button.setEnabled(False)
        self.elapsed_time.setText("00:00")
    
    def on_protocol_changed(self, index):
        """Enable/disable duration input based on selected protocol."""
        # Only enable duration input for Standard Gait assessment
        is_standard_gait = index == 0
        self.duration_spin.setEnabled(is_standard_gait and not self.is_recording)
        self.duration_label.setEnabled(is_standard_gait)
        
        # Set duration based on protocol
        if index == 1:  # 6-Minute Walk
            self.duration_spin.setValue(6)
            self.duration_spin.setToolTip("Fixed 6-minute duration for 6-Minute Walk Test")
        elif index == 2:  # 10m Walk
            self.duration_spin.setValue(1)
            self.duration_spin.setToolTip("Typically short duration (measures time to walk 10 meters)")
        elif index == 3:  # Timed Up & Go
            self.duration_spin.setValue(1)
            self.duration_spin.setToolTip("Typically short duration (measures time to complete the task)")
        else:  # Standard Gait
            self.duration_spin.setToolTip("Customizable duration for Standard Gait assessment")

    def keyPressEvent(self, event):
        """Handle key events to properly manage focus with Tab navigation."""
        # Handle Tab key for better focus navigation
        if event.key() == Qt.Key_Tab:
            # Determine the currently focused widget
            focused_widget = QApplication.focusWidget()
            
            # Find the next focusable widget
            if focused_widget == self.duration_spin:
                # From duration spin, move to notes
                self.notes_text.setFocus()
                return
            elif focused_widget == self.notes_text:
                # From notes, move back to protocol combo
                self.protocol_combo.setFocus()
                return
        
        # For all other keys, use normal behavior
        super().keyPressEvent(event)


class RehabilitationControlsExtended(RehabilitationControls):
    """Extension of RehabilitationControls with session management methods."""
    
    def __init__(self, parent=None):
        """Initialize the rehabilitation controls."""
        super().__init__(parent)
        
        # Connect signals
        self.select_music_button.clicked.connect(self.select_music)
        self.analyze_button.clicked.connect(self.analyze_music)
        
        # Hide the analyze button by default - it should only appear when needed
        if hasattr(self, 'analyze_button'):
            self.analyze_button.setVisible(False)
    
    def select_music(self):
        """Open the music selection dialog."""
        try:
            # Import all necessary widgets to ensure they're available
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QTableWidget, 
                QTableWidgetItem, QSplitter, QFileDialog, QMessageBox, QFrame,
                QPushButton, QTabWidget, QDialogButtonBox, QWidget
            )
            from PyQt5.QtCore import Qt
            
            # Create and show the custom music selection dialog
            dialog = MusicSelectionDialog(self)
            
            if dialog.exec_() == QDialog.Accepted:
                # Get the selected music information
                music_info = dialog.get_selected_music()
                
                if music_info["title"]:
                    self.music_label.setText(music_info["title"])
                    
                    # In a real implementation, store the file path and other info
                    self._selected_music_path = music_info.get("file_path", "")
                    
                    # Set visibility of analyze button based on whether the file has been analyzed
                    if hasattr(self, 'analyze_button'):
                        if "Unknown (not analyzed)" in music_info.get("rhythmic_style", ""):
                            # Only show analyze button for unanalyzed files
                            self.analyze_button.setVisible(True)
                            self.analyze_button.setEnabled(True)
                            self.analyze_button.setText("Analyze This MIDI")
                        else:
                            # Hide analyze button for pre-analyzed files
                            self.analyze_button.setVisible(False)
                            self.analyze_button.setEnabled(False)
        except Exception as e:
            logger.error(f"Error in music selection: {e}")
            QMessageBox.warning(self, "Error", f"Error in music selection: {str(e)}")
    
    def analyze_music(self):
        """Open the music rhythm analysis window for the selected music."""
        try:
            # Only show this if we have an unanalyzed file
            if not hasattr(self, '_selected_music_path') or not self._selected_music_path:
                QMessageBox.warning(
                    self, "No Music Selected", 
                    "Please select a music file first using the 'Browse Music' button."
                )
                return
                
            # Use the improved approach to open the analysis window
            self._show_analysis_window_for_file(self._selected_music_path)
            
        except Exception as e:
            # Handle any other errors
            QMessageBox.critical(
                self, "Error", 
                f"An error occurred while opening the music rhythm analysis window: {str(e)}"
            )
    
    def _show_analysis_window_for_file(self, file_path):
        """
        Create and show an analysis window for a specific file.
        This is a separate method to ensure clean separation from dialogs.
        
        Args:
            file_path: Path to the MIDI file to analyze
        """
        try:
            # Import our new launcher module
            from ui.rhythm_analyzer_launcher import launch_analyzer_as_separate_process
            
            # Launch the window as a completely separate process
            # This completely eliminates window management issues
            launch_analyzer_as_separate_process(file_path)
            
        except ImportError as e:
            QMessageBox.critical(
                self, "Module Not Available", 
                f"The rhythm analysis module is not available: {str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"An error occurred while analyzing the file: {str(e)}"
            )
    
    def start_training(self):
        """Prepare UI for active training."""
        if self.status_label:
            self.status_label.setText("Training in Progress")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
        
        if self.start_button:
            self.start_button.setEnabled(False)
        
        if self.stop_button:
            self.stop_button.setEnabled(True)
            
        # Disable music selection during training
        if hasattr(self, 'select_music_button'):
            self.select_music_button.setEnabled(False)
        
        if hasattr(self, 'analyze_button'):
            self.analyze_button.setEnabled(False)
    
    def stop_training(self):
        """Update UI after training is stopped."""
        if self.status_label:
            self.status_label.setText("Training Completed")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 14px; font-weight: bold;")
        
        if self.start_button:
            self.start_button.setEnabled(True)
        
        if self.stop_button:
            self.stop_button.setEnabled(False)
            
        # Re-enable music selection after training
        if hasattr(self, 'select_music_button'):
            self.select_music_button.setEnabled(True)
        
        if hasattr(self, 'analyze_button') and self.music_label.text() != "No music selected":
            self.analyze_button.setEnabled(True)
    
    def update_timer_display(self, time_text):
        """Update the timer display with the current elapsed time."""
        if self.timer_display:
            self.timer_display.setText(time_text)


class RASControlWidgetExtended(RASControlWidget):
    """Extension of RASControlWidget with session management methods."""
    
    def __init__(self, parent=None):
        """Initialize the RAS control widget."""
        super().__init__(parent)
        
        # Connect signals for UI functionality
        from PyQt5.QtCore import pyqtSignal
        self.confirm_tempo_signal = pyqtSignal(float)
        self.adjust_tempo_signal = pyqtSignal(float)
        self.pause_signal = pyqtSignal()
        self.resume_signal = pyqtSignal()
        
        # Connect music selection button signals
        self.music_button.clicked.connect(self.select_music)
        self.analyze_button.clicked.connect(self.analyze_rhythm)
        
        # Hide the analyze button by default - it should only appear when needed
        if hasattr(self, 'analyze_button'):
            self.analyze_button.setVisible(False)
    
    def select_music(self):
        """Open dialog to select music from the dataset."""
        try:
            # Import all necessary widgets to ensure they're available
            from PyQt5.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QTableWidget, 
                QTableWidgetItem, QSplitter, QFileDialog, QMessageBox, QFrame,
                QPushButton, QTabWidget, QDialogButtonBox, QWidget
            )
            from PyQt5.QtCore import Qt
            
            # Create and show the custom music selection dialog
            dialog = MusicSelectionDialog(self)
            
            if dialog.exec_() == QDialog.Accepted:
                # Get the selected music information
                music_info = dialog.get_selected_music()
                
                if music_info["title"]:
                    self.music_label.setText(music_info["title"])
                    
                    # In a real implementation, store the file path and other info
                    self._selected_music_path = music_info.get("file_path", "")
                    
                    # Set visibility of analyze button based on whether the file has been analyzed
                    if hasattr(self, 'analyze_button'):
                        if "Unknown (not analyzed)" in music_info.get("rhythmic_style", ""):
                            # Only show analyze button for unanalyzed files
                            self.analyze_button.setVisible(True)
                            self.analyze_button.setEnabled(True)
                            self.analyze_button.setText("Analyze This MIDI")
                        else:
                            # Hide analyze button for pre-analyzed files
                            self.analyze_button.setVisible(False)
                            self.analyze_button.setEnabled(False)
        except Exception as e:
            logger.error(f"Error in music selection: {e}")
            QMessageBox.warning(self, "Error", f"Error in music selection: {str(e)}")
    
    def analyze_rhythm(self):
        """Open the rhythm analysis window for a specific unanalyzed MIDI file."""
        try:
            # Only show this if we have an unanalyzed file
            if not hasattr(self, '_selected_music_path') or not self._selected_music_path:
                QMessageBox.warning(
                    self, "No Music Selected", 
                    "Please select a music file first using the 'Browse Music' button."
                )
                return
                
            # Use the same robust approach to open the analysis window
            self._show_analysis_window_for_file(self._selected_music_path)
            
        except Exception as e:
            # Handle any other errors
            QMessageBox.critical(
                self, "Error", 
                f"An error occurred while opening the music rhythm analysis window: {str(e)}"
            )
    
    def _show_analysis_window_for_file(self, file_path):
        """
        Create and show an analysis window for a specific file.
        This is a separate method to ensure clean separation from dialogs.
        
        Args:
            file_path: Path to the MIDI file to analyze
        """
        try:
            # Import our new launcher module
            from ui.rhythm_analyzer_launcher import launch_analyzer_as_separate_process
            
            # Launch the window as a completely separate process
            # This completely eliminates window management issues
            launch_analyzer_as_separate_process(file_path)
            
        except ImportError as e:
            QMessageBox.critical(
                self, "Module Not Available", 
                f"The rhythm analysis module is not available: {str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"An error occurred while analyzing the file: {str(e)}"
            )
    
    def start_ras(self):
        """Update UI for active RAS session."""
        if self.start_button:
            self.start_button.setEnabled(False)
        
        if self.stop_button:
            self.stop_button.setEnabled(True)
        
        if self.reset_button:
            self.reset_button.setEnabled(False)
        
        # Disable music selection controls during RAS
        if hasattr(self, 'music_button'):
            self.music_button.setEnabled(False)
        
        if hasattr(self, 'analyze_button'):
            self.analyze_button.setEnabled(False)
        
        # Enable sync controls
        self.sync_frame.setVisible(True)
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
    
    def stop_ras(self):
        """Update UI after RAS is stopped."""
        if self.start_button:
            self.start_button.setEnabled(True)
        
        if self.stop_button:
            self.stop_button.setEnabled(False)
        
        if self.reset_button:
            self.reset_button.setEnabled(True)
        
        # Re-enable music selection controls after RAS
        if hasattr(self, 'music_button'):
            self.music_button.setEnabled(True)
        
        if hasattr(self, 'analyze_button') and hasattr(self, 'music_label') and self.music_label.text() != "No music selected":
            self.analyze_button.setEnabled(True)
        
        # Disable sync controls
        self.sync_frame.setVisible(False)
        self.confirm_button.setEnabled(False)
        self.modify_button.setEnabled(False)
        self.decrease_button.setEnabled(False)
        self.increase_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        
        # Reset indicators
        self.gait_data_label.setText("No gait data available")
        self.status_label.setText("Status: IDLE")
    
    def pause_ras(self):
        """Update UI for paused RAS."""
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)
        self.status_label.setText("Status: PAUSED")
    
    def resume_ras(self):
        """Update UI for resumed RAS."""
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.status_label.setText("Status: SYNCHRONIZING")
    
    def update_pending_gait_data(self, gait_data):
        """
        Update UI with pending gait data.
        
        Args:
            gait_data: GaitData object with current gait parameters
        """
        if not gait_data:
            self.gait_data_label.setText("No gait data available")
            self.confirm_button.setEnabled(False)
            self.modify_button.setEnabled(False)
            return
            
        # Update label with gait data information
        self.gait_data_label.setText(
            f"Detected Cadence: {gait_data.cadence:.1f} steps/min\n"
            f"Confidence: {gait_data.confidence:.2f}\n"
            f"Confirm to use this tempo?"
        )
        
        # Enable confirmation buttons
        self.confirm_button.setEnabled(True)
        self.modify_button.setEnabled(True)
    
    def update_sync_state(self, sync_state):
        """
        Update UI based on synchronization state.
        
        Args:
            sync_state: SyncState enum value
        """
        # Update status label
        self.status_label.setText(f"Status: {sync_state.name}")
        
        # Enable/disable controls based on state
        if sync_state == SyncState.SYNCHRONIZING:
            self.confirm_button.setEnabled(False)
            self.modify_button.setEnabled(False)
            self.decrease_button.setEnabled(True)
            self.increase_button.setEnabled(True)
            self.pause_button.setEnabled(True)
            self.resume_button.setEnabled(False)
            
        elif sync_state == SyncState.WAITING_CONFIRMATION:
            self.confirm_button.setEnabled(True)
            self.modify_button.setEnabled(True)
            self.decrease_button.setEnabled(False)
            self.increase_button.setEnabled(False)
            
        elif sync_state == SyncState.PAUSED:
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(True)
            
        elif sync_state == SyncState.ERROR:
            self.confirm_button.setEnabled(False)
            self.modify_button.setEnabled(False)
            self.decrease_button.setEnabled(False)
            self.increase_button.setEnabled(False)
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)
    
    def reset_controls(self):
        """Reset all controls to default values."""
        if self.bpm_spin:
            self.bpm_spin.setValue(120)
        
        if self.sound_combo:
            self.sound_combo.setCurrentIndex(0)
        
        if self.duration_spin:
            self.duration_spin.setValue(10)
        
        if self.adaptive_checkbox:
            self.adaptive_checkbox.setChecked(True)
        
        if self.volume_slider:
            self.volume_slider.setValue(80)
            
        # Reset music selection controls
        if hasattr(self, 'rhythm_combo'):
            self.rhythm_combo.setCurrentIndex(0)
            
        if hasattr(self, 'instrument_combo'):
            self.instrument_combo.setCurrentIndex(0)
            
        if hasattr(self, 'mood_combo'):
            self.mood_combo.setCurrentIndex(0)
            
        if hasattr(self, 'music_label'):
            self.music_label.setText("No music selected")
            
        if hasattr(self, 'analyze_button'):
            self.analyze_button.setEnabled(False)
        
        # Hide sync frame
        self.sync_frame.setVisible(False)
        
        # Reset indicators
        self.gait_data_label.setText("No gait data available")
        self.status_label.setText("Status: IDLE")


class ProgressDialog(QDialog):
    """Simple progress dialog for long-running operations."""
    
    def __init__(self, title, message, parent=None):
        """Initialize the progress dialog."""
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(300)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add message label
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        # Add status label
        self.status_label = QLabel("Starting...")
        layout.addWidget(self.status_label)
        
        # Add cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button, alignment=Qt.AlignRight)
        
        # Setup timer for updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_progress)
        self.start_time = time.time()
        self.update_timer.start(500)  # Update every 500ms
        
    def _update_progress(self):
        """Update the elapsed time in the progress dialog."""
        elapsed = time.time() - self.start_time
        self.status_label.setText(f"Time elapsed: {int(elapsed)}s")
        
    def set_status(self, status):
        """Update the status message."""
        self.status_label.setText(status)
        
    def set_progress(self, value, maximum=100):
        """Set determinate progress value."""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)
        
    def closeEvent(self, event):
        """Handle dialog close event."""
        self.update_timer.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    main()