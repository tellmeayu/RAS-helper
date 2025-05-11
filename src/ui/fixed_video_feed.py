#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAS-helper: Fixed Video Feed Widget

This module provides an improved video feed widget with stable aspect ratio
and integrated pose estimation visualization.
"""

import time
import logging
import traceback

import cv2
import numpy as np
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtGui import QImage, QPixmap, QPainter, QFont, QColor, QPen
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QMutex

# from core.video_input.video_capture import VideoCapture, VideoSource, AspectRatio
from core.pose_estimation.pose_estimation import PoseEstimator, KeypointType

# Set up module logger
logger = logging.getLogger(__name__)


class FixedVideoFeedWidget(QFrame):
    """Simplified widget for displaying video feed with robust error handling."""
    
    # Signal emitted when a new frame is available
    frame_updated = pyqtSignal(np.ndarray)
    # Signal emitted when pose data is available
    pose_data_updated = pyqtSignal(dict, dict)
    
    def __init__(self, parent=None):
        """Initialize the video feed widget."""
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setStyleSheet("background-color: #222; color: white;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Initialize layout and UI components
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for better fitting
        
        self.feed_label = QLabel("Video Feed - Not Started")
        self.feed_label.setAlignment(Qt.AlignCenter)
        self.feed_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.feed_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # This ensures the QLabel maintains aspect ratio of its pixmap
        self.feed_label.setScaledContents(False)  # Don't stretch content
        self.feed_label.setAlignment(Qt.AlignCenter)  # Center the content
        
        layout.addWidget(self.feed_label)
        
        # Initialize video capture
        self.video_capture = None
        self.is_running = False
        
        # Initialize pose estimator
        self.pose_estimator = None
        self.enable_pose_estimation = True
        self.last_keypoints = None
        
        # Frame tracking
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.fps = 0
        self.current_frame = None
        
        # Thread safety
        self.frame_mutex = QMutex()
        
        # Display options
        self.show_fps = True
        
        # Update timer for refreshing the display
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.setInterval(33)  # ~30 fps
        
        logger.info("FixedVideoFeedWidget initialized")
    
    def initialize_pose_estimator(self):
        """Initialize the pose estimator with default settings."""
        try:
            self.pose_estimator = PoseEstimator(
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                smooth_landmarks=True,
                orientation_flip=True  # Flip orientation because we mirror the video feed
            )
            logger.info("Pose estimator initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing pose estimator: {e}")
            return False
    
    def start_capture(self, camera_index=0, width=1280, height=720):
        """
        Start video capture with the specified camera.
        
        Args:
            camera_index: Index of camera to use
            width: Desired capture width (default: 1280 for 16:9 HD)
            height: Desired capture height (default: 720 for 16:9 HD)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.is_running:
            logger.info("Video capture already running")
            return True
            
        try:
            # Test camera access first with OpenCV directly
            logger.info(f"Testing camera {camera_index}")
            cap = cv2.VideoCapture(camera_index)
            
            if not cap.isOpened():
                logger.error(f"Failed to open camera {camera_index}")
                self.feed_label.setText(f"Failed to open camera {camera_index}")
                return False
            
            # Try to read a test frame
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                logger.error("Failed to read frame from camera")
                self.feed_label.setText("Failed to read frame from camera")
                return False
                
            logger.info(f"Camera test successful, frame shape: {frame.shape}")
            
            # Initialize video capture
            self.video_capture = cv2.VideoCapture(camera_index)
            
            # Set camera properties - use provided width/height
            self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.video_capture.set(cv2.CAP_PROP_FPS, 30)
            
            # Get actual properties
            actual_width = self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {fps}fps")
            
            # Initialize pose estimator if enabled
            if self.enable_pose_estimation and not self.pose_estimator:
                if not self.initialize_pose_estimator():
                    logger.warning("Pose estimation will not be available")
            
            # Start the update timer
            self.is_running = True
            self.update_timer.start()
            
            self.feed_label.setText("Video feed running...")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting capture: {e}")
            logger.error(traceback.format_exc())
            self.feed_label.setText(f"Error: {str(e)}")
            
            # Clean up on error
            if self.video_capture and self.video_capture.isOpened():
                self.video_capture.release()
                self.video_capture = None
                
            return False
    
    def stop_capture(self):
        """Stop the current video capture."""
        if not self.is_running:
            return
            
        logger.info("Stopping video capture")
        
        # Stop the update timer
        self.update_timer.stop()
        
        # Release the video capture
        if self.video_capture and self.video_capture.isOpened():
            self.video_capture.release()
            self.video_capture = None
        
        self.is_running = False
        self.feed_label.setText("Video feed stopped")
        
        # Clear the current frame
        self.frame_mutex.lock()
        self.current_frame = None
        self.frame_mutex.unlock()
    
    def update_display(self):
        """Read a frame from the camera and update the display."""
        if not self.is_running or not self.video_capture or not self.video_capture.isOpened():
            return
            
        try:
            # Read a frame from the camera
            ret, frame = self.video_capture.read()
            
            if not ret or frame is None:
                logger.warning("Failed to read frame in update_display")
                return
                
            # Update FPS calculation
            current_time = time.time()
            self.frame_count += 1
            
            if current_time - self.last_frame_time >= 1.0:
                self.fps = self.frame_count / (current_time - self.last_frame_time)
                self.frame_count = 0
                self.last_frame_time = current_time
            
            # Flip the frame horizontally for a mirror effect
            frame = cv2.flip(frame, 1)
            
            # Process frame with pose estimation if enabled
            visualization_frame = frame.copy()
            keypoints = None
            gait_data = None
            
            if self.enable_pose_estimation and self.pose_estimator:
                try:
                    # Process frame with pose estimator
                    keypoints, visualization = self.pose_estimator.process_frame(frame)
                    
                    if keypoints:
                        self.last_keypoints = keypoints
                        
                        # If we have a visualization with pose markers, use it
                        if visualization is not None:
                            visualization_frame = visualization
                            # Disable our own FPS overlay since pose estimator already adds it
                            show_fps_here = False
                        else:
                            show_fps_here = self.show_fps
                            
                        # Emit pose data for other widgets to use
                        # Create an empty dict for gait_data if None to avoid type error
                        self.pose_data_updated.emit(keypoints, {})
                except Exception as pose_error:
                    logger.error(f"Error in pose estimation: {pose_error}")
                    show_fps_here = self.show_fps
            else:
                show_fps_here = self.show_fps
            
            # Add FPS overlay if enabled and not already added by pose estimator
            if show_fps_here:
                cv2.putText(
                    visualization_frame,
                    f"FPS: {self.fps:.1f}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )
            
            # Store the current frame safely
            self.frame_mutex.lock()
            self.current_frame = frame.copy()
            
            # Convert to QImage and display - careful with error handling
            try:
                h, w, ch = visualization_frame.shape
                bytes_per_line = ch * w
                
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(visualization_frame, cv2.COLOR_BGR2RGB)
                
                # Create QImage
                qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                if not qimg.isNull():
                    # Create QPixmap
                    pixmap = QPixmap.fromImage(qimg)
                    
                    if not pixmap.isNull():
                        # Scale the pixmap to fit the width while preserving aspect ratio
                        label_width = self.feed_label.width()
                        if pixmap.width() > label_width:
                            pixmap = pixmap.scaledToWidth(label_width, Qt.SmoothTransformation)
                        
                        # Set the pixmap on the label
                        self.feed_label.setPixmap(pixmap)
                        # Don't use setScaledContents as it would stretch the image
                    else:
                        logger.warning("Created pixmap is null")
                        # Don't change the label text here to avoid flickering
                else:
                    logger.warning("Created QImage is null")
                    # Don't change the label text here to avoid flickering
                
            except Exception as e:
                logger.error(f"Error creating QImage/QPixmap: {e}")
                # Don't change the label text here to avoid flickering
            
            self.frame_mutex.unlock()
            
            # Emit the frame updated signal
            self.frame_updated.emit(frame)
            
        except Exception as e:
            logger.error(f"Error in update_display: {e}")
    
    def get_current_frame(self):
        """Get the current frame safely."""
        self.frame_mutex.lock()
        frame = self.current_frame.copy() if self.current_frame is not None else None
        self.frame_mutex.unlock()
        return frame
    
    def sizeHint(self):
        """Return a size with 16:9 aspect ratio."""
        width = 640  # Default width
        return QSize(width, int(width * 9 / 16))
    
    def resizeEvent(self, event):
        """Handle resize events to maintain aspect ratio."""
        # First, maintain the widget's 16:9 aspect ratio
        width = event.size().width()
        target_height = int(width * 9 / 16)
        
        if abs(event.size().height() - target_height) > 10:  # Allow small variations
            self.setFixedHeight(target_height)
        
        super().resizeEvent(event)
        
        # If we have a current pixmap, update its scaling when the widget is resized
        if hasattr(self.feed_label, 'pixmap') and self.feed_label.pixmap() and not self.feed_label.pixmap().isNull():
            # Get the current pixmap
            current_pixmap = self.feed_label.pixmap()
            
            # Scale it to the new width while maintaining aspect ratio
            label_width = self.feed_label.width()
            if current_pixmap.width() > label_width:
                scaled_pixmap = current_pixmap.scaledToWidth(label_width, Qt.SmoothTransformation)
                self.feed_label.setPixmap(scaled_pixmap)
    
    def paintEvent(self, event):
        """Custom paint event to ensure proper frame display."""
        super().paintEvent(event)
        # The QFrame will draw its own background and border
        # We let the QLabel handle the video display with proper aspect ratio
    
    def closeEvent(self, event):
        """Handle close events to clean up resources."""
        self.stop_capture()
        
        # Clean up pose estimator
        if self.pose_estimator:
            self.pose_estimator.release()
            self.pose_estimator = None
            
        super().closeEvent(event) 