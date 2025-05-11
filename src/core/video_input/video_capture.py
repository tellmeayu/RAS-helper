#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Capture Module for NeuroApp_RAS

This module provides functionality to capture video frames from webcams or video files.
It includes preprocessing capabilities and a clean interface for the Pose Estimation Module.
"""

import logging
import time
import sys
import os
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class VideoSource(Enum):
    """Enumeration of video source types."""
    WEBCAM = 1
    VIDEO_FILE = 2


class AspectRatio(Enum):
    """Enumeration of common aspect ratios."""
    RATIO_16_9 = (16, 9)    # Widescreen (1.78:1)
    RATIO_4_3 = (4, 3)      # Standard (1.33:1)
    RATIO_21_9 = (21, 9)    # Ultra-widescreen (2.33:1)
    RATIO_1_1 = (1, 1)      # Square (1:1)


class FramePreprocessor:
    """Handles preprocessing operations on video frames."""
    
    def __init__(self, config: Dict = None):
        """
        Initialize the frame preprocessor with configuration.
        
        Args:
            config: Dictionary containing preprocessing parameters:
                - resize: Tuple[int, int] for target resolution (width, height)
                - color_conversion: cv2 color conversion code
                - flip_horizontal: bool to mirror the image horizontally
                - crop: Tuple[int, int, int, int] for (x, y, width, height)
                - maintain_aspect: bool to maintain aspect ratio when resizing
                - letterbox: bool to add letterboxing when maintaining aspect ratio
        """
        self.config = config or {}
    
    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply preprocessing operations to a frame.
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Processed frame as numpy array
        """
        if frame is None:
            return None
        
        # Apply preprocessing operations based on configuration
        processed_frame = frame.copy()
        
        # Crop if specified
        if 'crop' in self.config:
            x, y, w, h = self.config['crop']
            processed_frame = processed_frame[y:y+h, x:x+w]
        
        # Resize if specified
        if 'resize' in self.config:
            target_width, target_height = self.config['resize']
            
            # Check if we need to maintain aspect ratio
            if self.config.get('maintain_aspect', False):
                current_height, current_width = processed_frame.shape[:2]
                current_ratio = current_width / current_height
                target_ratio = target_width / target_height
                
                if self.config.get('letterbox', True):
                    # Use letterboxing/pillarboxing to maintain aspect ratio
                    if current_ratio > target_ratio:
                        # Image is wider than target, use letterboxing (black bars top/bottom)
                        new_height = int(target_width / current_ratio)
                        resized = cv2.resize(processed_frame, (target_width, new_height))
                        processed_frame = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                        y_offset = (target_height - new_height) // 2
                        processed_frame[y_offset:y_offset+new_height, :] = resized
                    else:
                        # Image is taller than target, use pillarboxing (black bars left/right)
                        new_width = int(target_height * current_ratio)
                        resized = cv2.resize(processed_frame, (new_width, target_height))
                        processed_frame = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                        x_offset = (target_width - new_width) // 2
                        processed_frame[:, x_offset:x_offset+new_width] = resized
                else:
                    # Crop to maintain aspect ratio instead of letterboxing
                    if current_ratio > target_ratio:
                        # Image is wider, crop width
                        new_width = int(current_height * target_ratio)
                        x_offset = (current_width - new_width) // 2
                        processed_frame = processed_frame[:, x_offset:x_offset+new_width]
                    else:
                        # Image is taller, crop height
                        new_height = int(current_width / target_ratio)
                        y_offset = (current_height - new_height) // 2
                        processed_frame = processed_frame[y_offset:y_offset+new_height, :]
                    
                    # Now resize to target dimensions
                    processed_frame = cv2.resize(processed_frame, (target_width, target_height))
            else:
                # Simple resize without maintaining aspect ratio
                processed_frame = cv2.resize(processed_frame, (target_width, target_height))
        
        # Color conversion if specified
        if 'color_conversion' in self.config:
            processed_frame = cv2.cvtColor(processed_frame, self.config['color_conversion'])
        
        # Horizontal flip if specified
        if self.config.get('flip_horizontal', False):
            processed_frame = cv2.flip(processed_frame, 1)
        
        return processed_frame


class VideoCapture:
    """Handles video capture from webcam or video file sources."""
    
    def __init__(self, 
                 source: Union[int, str, Path] = 0, 
                 source_type: Optional[VideoSource] = None,
                 frame_width: int = 1280,  # Changed default to 16:9 HD resolution
                 frame_height: int = 720,  # Changed default to 16:9 HD resolution
                 fps: int = 30,
                 aspect_ratio: AspectRatio = AspectRatio.RATIO_16_9,
                 preprocessor_config: Dict = None):
        """
        Initialize video capture with specified source and parameters.
        
        Args:
            source: Camera index (int) or video file path (str or Path)
            source_type: Explicitly specify source type (auto-detected if None)
            frame_width: Target frame width for capture
            frame_height: Target frame height for capture
            fps: Target frames per second (for webcam)
            aspect_ratio: Target aspect ratio for capture (default 16:9)
            preprocessor_config: Configuration for frame preprocessor
        """
        self.source = source
        self.aspect_ratio = aspect_ratio
        self.is_running = False
        self.cap = None
        self.frame_count = 0
        self.current_fps = 0
        self.last_frame_time = 0
        self.frame_callbacks = []
        
        # Ensure frame dimensions match aspect ratio
        self.frame_width, self.frame_height = self._adjust_dimensions_to_aspect_ratio(
            frame_width, frame_height, aspect_ratio)
        self.fps = fps
        
        # Auto-detect source type if not specified
        if source_type is None:
            if isinstance(source, (str, Path)):
                self.source_type = VideoSource.VIDEO_FILE
            else:
                self.source_type = VideoSource.WEBCAM
        else:
            # Ensure source_type is a valid VideoSource enum
            if not isinstance(source_type, VideoSource):
                logger.warning(f"Invalid source_type: {source_type}. Using auto-detection instead.")
                # Auto-detect based on source type
                if isinstance(source, (str, Path)):
                    self.source_type = VideoSource.VIDEO_FILE
                else:
                    self.source_type = VideoSource.WEBCAM
            else:
                self.source_type = source_type
        
        # Initialize frame preprocessor with default config for maintaining aspect ratio
        default_config = {
            'resize': (self.frame_width, self.frame_height),
            'maintain_aspect': True,
            'letterbox': True
        }
        
        # Merge with provided config, with provided values taking precedence
        if preprocessor_config:
            default_config.update(preprocessor_config)
            
        self.preprocessor = FramePreprocessor(default_config)
    
    def _adjust_dimensions_to_aspect_ratio(self, width: int, height: int, 
                                          aspect_ratio: AspectRatio) -> Tuple[int, int]:
        """
        Adjust dimensions to match the specified aspect ratio.
        
        Args:
            width: Target width
            height: Target height
            aspect_ratio: Target aspect ratio
            
        Returns:
            Tuple of (width, height) adjusted to match the aspect ratio
        """
        ratio_width, ratio_height = aspect_ratio.value
        target_ratio = ratio_width / ratio_height
        
        current_ratio = width / height
        
        if abs(current_ratio - target_ratio) < 0.01:
            # Close enough to the target ratio
            return width, height
        
        # Adjust dimensions to match aspect ratio
        if current_ratio > target_ratio:
            # Too wide, adjust width based on height
            return int(height * target_ratio), height
        else:
            # Too tall, adjust height based on width
            return width, int(width / target_ratio)
    
    def set_aspect_ratio(self, aspect_ratio: AspectRatio) -> None:
        """
        Set a new aspect ratio for video capture.
        
        Args:
            aspect_ratio: The new aspect ratio to use
        """
        self.aspect_ratio = aspect_ratio
        self.frame_width, self.frame_height = self._adjust_dimensions_to_aspect_ratio(
            self.frame_width, self.frame_height, aspect_ratio)
            
        # Update preprocessor config
        if hasattr(self, 'preprocessor') and self.preprocessor:
            self.preprocessor.config['resize'] = (self.frame_width, self.frame_height)
            
        # If already running, restart capture with new dimensions
        if self.is_running:
            was_running = True
            self.stop()
        else:
            was_running = False
            
        if was_running:
            self.start()
            
        logger.info(f"Aspect ratio set to {aspect_ratio.name}: {self.frame_width}x{self.frame_height}")
    
    def list_available_cameras(self) -> List[int]:
        """
        List all available camera devices.
        
        Returns:
            List of camera indices that are available
        """
        available_cameras = []
        for i in range(10):  # Check first 10 camera indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
                
        return available_cameras
    
    def get_camera_capabilities(self, camera_index: int) -> Dict:
        """
        Get capabilities of a specific camera.
        
        Args:
            camera_index: Index of the camera to check
            
        Returns:
            Dictionary with camera capabilities (resolutions, etc.)
        """
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logger.error(f"Could not open camera {camera_index}")
            return {}
            
        # Try to get supported resolutions
        # This is not guaranteed to work on all platforms
        resolutions = []
        for width, height in [
            (320, 240), (640, 480), (800, 600), (1024, 768),
            (1280, 720), (1920, 1080), (2560, 1440), (3840, 2160)
        ]:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Only add if it's a unique resolution
            resolution = (actual_width, actual_height)
            if resolution not in resolutions and resolution != (0, 0):
                resolutions.append(resolution)
                
        cap.release()
        
        return {
            'resolutions': resolutions
        }
    
    def start(self) -> bool:
        """
        Start video capture.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.is_running:
            logger.info("Video capture already running")
            return True
        
        try:
            # Initialize OpenCV capture
            if self.source_type == VideoSource.WEBCAM:
                logger.info(f"Opening webcam source {self.source}")
                
                # MacOS and Linux often have camera permission issues, try checking if camera is accessible
                if sys.platform == 'darwin' or sys.platform.startswith('linux'):
                    logger.info(f"Running on {sys.platform}, checking camera permissions")
                    
                    # Try opening camera with default settings first just to check permissions
                    test_cap = cv2.VideoCapture(self.source)
                    if not test_cap.isOpened():
                        logger.error(f"Failed to open camera {self.source}. Check camera permissions.")
                        return False
                    
                    # Get basic info
                    width = test_cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                    height = test_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    logger.info(f"Camera opened with default settings: {width}x{height}")
                    
                    # Release test capture
                    test_cap.release()
                
                # Now open with our desired settings
                self.cap = cv2.VideoCapture(self.source)
                
                if not self.cap.isOpened():
                    logger.error(f"Failed to open camera {self.source}")
                    return False
                
                # Configure camera settings
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                
                # Verify settings were applied
                actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                
                logger.info(f"Camera configured - Requested: {self.frame_width}x{self.frame_height} @ {self.fps}fps")
                logger.info(f"Camera actual settings: {actual_width}x{actual_height} @ {actual_fps}fps")
                
                # Some cameras don't support setting properties - make sure we got something reasonable
                if actual_width < 1 or actual_height < 1:
                    logger.warning("Camera properties could not be set properly. Using default camera settings.")
                
            elif self.source_type == VideoSource.VIDEO_FILE:
                logger.info(f"Opening video file: {self.source}")
                
                # Ensure the file exists
                if not isinstance(self.source, (str, Path)) or not os.path.exists(str(self.source)):
                    logger.error(f"Video file not found: {self.source}")
                    return False
                
                self.cap = cv2.VideoCapture(str(self.source))
                
                if not self.cap.isOpened():
                    logger.error(f"Failed to open video file: {self.source}")
                    return False
                
                # Get video file properties
                actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                
                logger.info(f"Video file properties: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            # Start processing thread or timer
            self.is_running = True
            self.frame_count = 0
            self.last_frame_time = time.time()
            
            # Read one test frame to verify everything is working
            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                logger.error("Failed to read first frame - camera may be in use by another application")
                self.stop()
                return False
                
            logger.info(f"Successfully read first frame: {test_frame.shape}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting video capture: {e}")
            
            # Clean up on error
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            self.is_running = False
            return False
    
    def stop(self) -> None:
        """
        Stop video capture and release resources.
        """
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        logger.info("Video capture stopped")
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read a single frame from the video source.
        
        Returns:
            Tuple of (success_flag, frame) where frame is None if read failed
        """
        # Check if we are running and have a valid capture object
        if not self.is_running:
            logger.warning("Cannot read frame: Video capture is not running")
            return False, None
            
        if self.cap is None:
            logger.error("Cannot read frame: Video capture object is None")
            return False, None
            
        # Verify the capture object is still open
        if not hasattr(self.cap, 'isOpened') or not self.cap.isOpened():
            logger.error("Cannot read frame: Video capture is closed or invalid")
            self.is_running = False  # Update state to reflect reality
            return False, None
        
        try:
            # Read frame from capture
            if not hasattr(self.cap, 'read'):
                logger.error("Invalid video capture object: Missing 'read' method")
                return False, None
                
            ret, frame = self.cap.read()
            
            # Update frame count and timing
            current_time = time.time()
            if ret and frame is not None:
                self.frame_count += 1
                elapsed = current_time - self.last_frame_time
                if elapsed >= 1.0:
                    self.current_fps = self.frame_count / elapsed
                    self.frame_count = 0
                    self.last_frame_time = current_time
                
                # Process the frame through preprocessor
                if self.preprocessor:
                    try:
                        processed_frame = self.preprocessor.process(frame)
                        
                        # Call all registered callbacks
                        for callback in self.frame_callbacks:
                            try:
                                callback(processed_frame)
                            except Exception as e:
                                logger.error(f"Error in frame callback: {e}")
                        
                        return ret, processed_frame
                    except Exception as e:
                        logger.error(f"Error in frame preprocessing: {e}")
                        # Fall back to original frame if preprocessing fails
                        for callback in self.frame_callbacks:
                            try:
                                callback(frame)
                            except Exception as e:
                                logger.error(f"Error in frame callback: {e}")
                        return ret, frame
                else:
                    # Call all registered callbacks
                    for callback in self.frame_callbacks:
                        try:
                            callback(frame)
                        except Exception as e:
                            logger.error(f"Error in frame callback: {e}")
                    
                    return ret, frame
            else:
                if not ret:
                    logger.warning("Failed to read frame (ret=False)")
                if frame is None:
                    logger.warning("Frame is None despite ret=True")
                
                # To ensure consistency, return both flags
                return False, None
                
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return False, None
    
    def get_frame_iterator(self) -> Iterator[np.ndarray]:
        """
        Get an iterator that yields frames from the video source.
        
        Yields:
            np.ndarray: Processed video frames
        """
        if not self.is_running:
            if not self.start():
                return
        
        while self.is_running:
            ret, frame = self.read_frame()
            if ret and frame is not None:
                yield frame
            else:
                break
    
    def add_frame_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        """
        Add a callback function to be called when a new frame is processed.
        
        Args:
            callback: Function that takes a frame (np.ndarray) as argument
        """
        self.frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        """
        Remove a previously added frame callback.
        
        Args:
            callback: The callback function to remove
        """
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)
    
    def get_info(self) -> Dict:
        """
        Get information about the current video capture.
        
        Returns:
            Dict containing video capture properties
        """
        return {
            'source_type': self.source_type.name,
            'width': self.frame_width,
            'height': self.frame_height,
            'aspect_ratio': f"{self.aspect_ratio.value[0]}:{self.aspect_ratio.value[1]}",
            'fps': self.fps,
            'current_fps': self.current_fps,
            'frame_count': self.frame_count if self.source_type == VideoSource.VIDEO_FILE else None,
            'is_running': self.is_running
        }
    
    def __enter__(self):
        """
Context manager entry.
        """
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
Context manager exit.
        """
        self.stop()