#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAS-helper: Video Feed Widget

This module implements a PyQt5 widget for displaying video feed with integrated
pose estimation and real-time gait analysis visualization.
"""

import time
import logging
from typing import Optional, Dict, Tuple

import cv2
import numpy as np
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtGui import QImage, QPixmap, QPainter, QFont, QColor
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QMutex

from core.video_input.video_capture import VideoCapture, VideoSource, AspectRatio
from core.pose_estimation.pose_estimation import PoseEstimator
from core.gait_analysis.gait_analysis import GaitAnalyzer

# Set up module logger
logger = logging.getLogger(__name__)


class VideoFeedWidget(QFrame):
    """Widget for displaying video feed with pose estimation overlay."""
    
    # Signal emitted when new pose and gait data is available
    data_updated = pyqtSignal(dict, dict)
    
    def __init__(self, parent=None):
        """Initialize the video feed widget."""
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setStyleSheet("background-color: #222; color: white;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Initialize layout and UI components
        layout = QVBoxLayout(self)
        
        self.feed_label = QLabel("Initializing Video Feed...")
        self.feed_label.setAlignment(Qt.AlignCenter)
        self.feed_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(self.feed_label)
        
        # Initialize video capture and processing components
        self.video_capture = None
        self.pose_estimator = None
        self.gait_analyzer = None
        
        # FPS tracking
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.frame_count = 0
        self.fps = 0
        self.last_fps_time = time.time()
        
        # Thread safety
        self.frame_mutex = QMutex()
        self.current_frame = None
        self.current_keypoints = None
        self.current_gait_data = None
        
        # Display options
        self.show_pose = True
        self.show_gait_markers = True
        self.show_stats = True
        
        # Update timer for refreshing the display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        
        # Set 16:9 aspect ratio constraint
        self.setMinimumSize(640, 360)  # Minimum HD resolution with 16:9 ratio
        
        # Flag to track if we're awaiting first frame
        self.awaiting_first_frame = False
        
        logger.info("VideoFeedWidget initialized")
    
    def initialize_capture(self, source=0, width=1280, height=720, fps=30):
        """Initialize video capture with the specified parameters."""
        try:
            logger.info(f"Initializing video capture with source={source}, width={width}, height={height}, fps={fps}")
            
            # If we already have a capture instance, stop it
            if self.video_capture is not None:
                self.stop_capture()
            
            # Configure video preprocessor for proper 16:9 display
            preprocessor_config = {
                'resize': (width, height),
                'maintain_aspect': True,
                'letterbox': True,
                'flip_horizontal': True  # Mirror display for more intuitive movements
            }
            
            # Create video capture instance
            self.video_capture = VideoCapture(
                source=source,
                frame_width=width,
                frame_height=height,
                fps=fps,
                aspect_ratio=AspectRatio.RATIO_16_9,
                preprocessor_config=preprocessor_config
            )
            
            # Create pose estimator instance
            self.pose_estimator = PoseEstimator(
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                smooth_landmarks=True
            )
            
            # Create gait analyzer instance
            self.gait_analyzer = GaitAnalyzer(
                history_size=90,  # 3 seconds at 30fps
                step_detection_threshold=0.03,
                smoothing_window=5
            )
            
            # Reset the feed label to show we're waiting for video
            self.feed_label.setText("Waiting for video feed...")
            # Make sure to clear any previous pixmap first, to avoid setPixmap errors
            self.feed_label.setPixmap(None)  
            self.awaiting_first_frame = True
            
            # Test camera before starting capture thread
            logger.info("Testing camera connection...")
            test_cap = cv2.VideoCapture(source)
            if not test_cap.isOpened():
                logger.error(f"Failed to open camera {source} in test")
                self.feed_label.setText(f"Failed to open camera {source}")
                test_cap.release()
                return False
                
            # Read one test frame to verify camera works
            ret, test_frame = test_cap.read()
            test_cap.release()
            
            if not ret or test_frame is None:
                logger.error("Could not read frame from camera in test")
                self.feed_label.setText("Could not read frame from camera")
                return False
                
            logger.info(f"Camera test successful, frame shape: {test_frame.shape}")
            
            # Start video capture
            success = self.video_capture.start()
            if not success:
                self.feed_label.setText("Failed to start video capture")
                logger.error("Failed to start video capture")
                return False
            
            # Register frame callback
            self.video_capture.add_frame_callback(self.process_frame)
            logger.info("Frame callback registered")
            
            # Start timers
            self.fps_timer.start(1000)  # Update FPS once per second
            self.update_timer.start(33)  # ~30 fps display refresh
            logger.info("Timers started: fps_timer and update_timer")
            
            return True
            
        except Exception as e:
            error_msg = f"Error initializing capture: {e}"
            self.feed_label.setText(error_msg)
            logger.error(error_msg)
            # Make sure any partial initialization is cleaned up
            if hasattr(self, 'video_capture') and self.video_capture is not None:
                try:
                    self.video_capture.stop()
                except:
                    pass
            return False
    
    def process_frame(self, frame):
        """Process a new video frame with pose estimation and gait analysis."""
        if frame is None:
            logger.warning("Received None frame in process_frame")
            return
        
        try:
            # If this is our first frame, log it
            if self.awaiting_first_frame:
                logger.info(f"First frame received! Shape: {frame.shape}")
                self.awaiting_first_frame = False
            
            # Make a copy to avoid modifying the original
            frame_copy = frame.copy()
            
            # Apply pose estimation
            keypoints, visualization = None, None
            try:
                keypoints, visualization = self.pose_estimator.process_frame(frame_copy)
            except Exception as e:
                logger.error(f"Error in pose estimation: {e}")
                # If pose estimation fails, use original frame
                visualization = frame_copy
            
            # If pose detected, apply gait analysis
            gait_data = None
            if keypoints:
                try:
                    gait_data = self.gait_analyzer.process_keypoints(keypoints, time.time())
                except Exception as e:
                    logger.error(f"Error in gait analysis: {e}")
            
            # Store the processed frame and data safely
            self.frame_mutex.lock()
            self.current_frame = visualization if visualization is not None else frame_copy
            self.current_keypoints = keypoints
            self.current_gait_data = gait_data
            self.frame_count += 1
            self.frame_mutex.unlock()
            
            # Emit signal with new data if available
            if keypoints and gait_data:
                self.data_updated.emit(keypoints, gait_data)
            
            # Log periodically
            if self.frame_count % 100 == 0:
                logger.info(f"Processed {self.frame_count} frames. Current FPS: {self.fps:.1f}")
                
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            # Store original frame as fallback
            self.frame_mutex.lock()
            self.current_frame = frame
            self.frame_mutex.unlock()
    
    def update_display(self):
        """Update the displayed frame with overlays."""
        if not hasattr(self, 'frame_mutex') or not hasattr(self, 'current_frame'):
            logger.error("Invalid state: Missing required attributes for display update")
            return
            
        self.frame_mutex.lock()
        
        try:
            if self.current_frame is not None:
                frame = self.current_frame.copy()
                
                # Add overlays if enabled
                if self.show_stats:
                    self._add_stats_overlay(frame)
                
                if self.show_gait_markers and self.current_gait_data:
                    self._add_gait_markers(frame)
                
                # Convert to QImage and display
                try:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame_rgb.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    
                    if not qt_image.isNull():
                        pixmap = QPixmap.fromImage(qt_image)
                        if not pixmap.isNull():
                            self.feed_label.setPixmap(pixmap)
                            self.feed_label.setScaledContents(True)
                        else:
                            logger.warning("Created pixmap is null")
                            self.feed_label.setText("Error: Invalid video frame")
                    else:
                        logger.warning("Created QImage is null")
                        self.feed_label.setText("Error: Invalid video frame")
                except Exception as e:
                    logger.error(f"Error converting frame to QImage/QPixmap: {e}")
                    self.feed_label.setText(f"Error displaying frame: {str(e)}")
                
                # Periodically log that frames are being displayed (every 30 frames)
                if self.frame_count % 30 == 0:
                    logger.debug(f"Displaying frame, count: {self.frame_count}, shape: {frame.shape}")
            elif self.awaiting_first_frame and self.video_capture and self.video_capture.is_running:
                # Still waiting for first frame but capture is running
                logger.debug("Waiting for first frame...")
                # Make sure text is displayed
                self.feed_label.setText("Waiting for first frame...")
                if hasattr(self.feed_label, 'setPixmap'):
                    self.feed_label.setPixmap(None)  # Clear any previous pixmap explicitly
            else:
                # No frames are available and we're not waiting for the first frame
                # This should only happen when video is stopped
                self.feed_label.setText("No video feed available")
                if hasattr(self.feed_label, 'setPixmap'):
                    self.feed_label.setPixmap(None)  # Clear any previous pixmap explicitly
                logger.debug("No frames to display, label set to 'No video feed available'")
        except Exception as e:
            logger.error(f"Error updating display: {e}")
            if hasattr(self.feed_label, 'setText'):
                self.feed_label.setText(f"Error: {str(e)}")
            if hasattr(self.feed_label, 'setPixmap'):
                self.feed_label.setPixmap(None)  # Clear any previous pixmap
        
        self.frame_mutex.unlock()
    
    def _add_stats_overlay(self, frame):
        """Add FPS and gait statistics overlay to the frame."""
        try:
            h, w = frame.shape[:2]
            
            # Create semi-transparent overlay for text background
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 10), (300, 120), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
            
            # Add FPS
            cv2.putText(frame, f"FPS: {self.fps:.1f}", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Add gait stats if available
            if self.current_gait_data:
                gait_data = self.current_gait_data
                cv2.putText(frame, f"Cadence: {gait_data['cadence']:.1f} steps/min", 
                           (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                          
                cv2.putText(frame, f"Step Count: {gait_data['step_count']}", 
                           (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        except Exception as e:
            logger.error(f"Error adding stats overlay: {e}")
    
    def _add_gait_markers(self, frame):
        """Add gait analysis markers to the frame."""
        try:
            if self.current_gait_data and self.current_gait_data.get('is_walking', False):
                # Add step phase indicators
                left_phase = self.current_gait_data.get('left_foot_phase', None)
                right_phase = self.current_gait_data.get('right_foot_phase', None)
                
                h, w = frame.shape[:2]
                
                # Left foot phase indicator
                phase_color = (0, 255, 0) if left_phase and left_phase.name == 'SWING' else (0, 0, 255)
                cv2.circle(frame, (80, h - 50), 15, phase_color, -1)
                cv2.putText(frame, "L", (75, h - 45), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Right foot phase indicator
                phase_color = (0, 255, 0) if right_phase and right_phase.name == 'SWING' else (0, 0, 255)
                cv2.circle(frame, (120, h - 50), 15, phase_color, -1)
                cv2.putText(frame, "R", (115, h - 45), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Add indicator for latest step detection
                if self.current_gait_data.get('step_detected', False):
                    foot = self.current_gait_data.get('step_foot', None)
                    if foot:
                        step_text = f"Step: {foot}"
                        cv2.putText(frame, step_text, (w - 150, h - 50), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        except Exception as e:
            logger.error(f"Error adding gait markers: {e}")
    
    def update_fps(self):
        """Update the calculated FPS based on processed frames."""
        current_time = time.time()
        elapsed = current_time - self.last_fps_time
        
        if elapsed > 0:
            self.fps = self.frame_count / elapsed
            # Log FPS periodically
            logger.debug(f"Current FPS: {self.fps:.2f}")
            self.frame_count = 0
            self.last_fps_time = current_time
    
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
    
    def stop_capture(self):
        """Stop video capture and release resources."""
        logger.info("Stopping video capture...")
        
        # Stop timers first
        if self.update_timer.isActive():
            self.update_timer.stop()
            logger.debug("Update timer stopped")
        
        if self.fps_timer.isActive():
            self.fps_timer.stop()
            logger.debug("FPS timer stopped")
        
        # Stop video capture and release resources
        if self.video_capture:
            try:
                # Clear the callback before stopping
                if hasattr(self.video_capture, 'remove_frame_callback'):
                    self.video_capture.remove_frame_callback(self.process_frame)
                    logger.debug("Frame callback removed")
                
                self.video_capture.stop()
                logger.debug("Video capture stopped")
            except Exception as e:
                logger.error(f"Error stopping video capture: {e}")
            finally:
                self.video_capture = None
        
        # Release pose estimator resources
        if self.pose_estimator:
            try:
                self.pose_estimator.release()
                logger.debug("Pose estimator released")
            except Exception as e:
                logger.error(f"Error releasing pose estimator: {e}")
            finally:
                self.pose_estimator = None
        
        # Clear UI
        self.frame_mutex.lock()
        self.current_frame = None
        self.current_keypoints = None
        self.current_gait_data = None
        self.frame_mutex.unlock()
        
        # Update label
        self.feed_label.setPixmap(None)  # Clear any image
        self.feed_label.setText("Video Capture Stopped")
        logger.info("Video capture resources released")
    
    def toggle_pose_visualization(self, enabled):
        """Toggle the display of pose estimation visualization."""
        self.show_pose = enabled
    
    def toggle_gait_markers(self, enabled):
        """Toggle the display of gait analysis markers."""
        self.show_gait_markers = enabled
    
    def toggle_stats_overlay(self, enabled):
        """Toggle the display of statistics overlay."""
        self.show_stats = enabled
    
    def closeEvent(self, event):
        """Handle widget close event to properly release resources."""
        self.stop_capture()
        super().closeEvent(event) 