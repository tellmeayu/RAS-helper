#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeuroApp_RAS: Direct Camera Test

This module provides a standalone tool for testing camera functionality
with OpenCV directly, bypassing the PyQt UI components.
"""

import sys
import time
import argparse
import logging
import cv2
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def test_camera(camera_idx=0, width=1280, height=720, fps=30, test_duration=0):
    """
    Test camera functionality directly with OpenCV.
    
    Args:
        camera_idx: Camera index to test
        width: Target frame width
        height: Target frame height
        fps: Target frame rate
        test_duration: Test duration in seconds (0 for indefinite)
        
    Returns:
        bool: True if camera works, False otherwise
    """
    logger.info(f"Testing camera {camera_idx} with resolution {width}x{height}")
    
    try:
        # Try to open camera
        cap = cv2.VideoCapture(camera_idx)
        if not cap.isOpened():
            logger.error(f"Failed to open camera {camera_idx}")
            return False
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        
        # Get camera properties
        actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        
        logger.info(f"Camera initialized with resolution: {actual_width}x{actual_height}, FPS: {actual_fps}")
        
        # Create window
        window_name = f"Camera {camera_idx} Test (Press ESC to exit)"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, int(actual_width), int(actual_height))
        
        # Variables for statistics
        start_time = time.time()
        frame_count = 0
        fps_update_time = start_time
        current_fps = 0
        
        # Process frames until ESC pressed or duration reached
        while True:
            # Check if test duration has been reached
            if test_duration > 0 and (time.time() - start_time) >= test_duration:
                logger.info(f"Test duration of {test_duration} seconds reached")
                break
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to read frame from camera")
                break
            
            # Update statistics
            frame_count += 1
            elapsed = time.time() - fps_update_time
            if elapsed >= 1.0:  # Update FPS once per second
                current_fps = frame_count / elapsed
                fps_update_time = time.time()
                frame_count = 0
            
            # Add statistics overlay
            cv2.putText(
                frame, 
                f"FPS: {current_fps:.1f}",
                (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                (0, 255, 0), 
                2
            )
            
            cv2.putText(
                frame, 
                f"Resolution: {int(actual_width)}x{int(actual_height)}",
                (20, 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                (0, 255, 0), 
                2
            )
            
            # Display frame
            cv2.imshow(window_name, frame)
            
            # Check for ESC key
            if cv2.waitKey(1) == 27:  # ESC key
                logger.info("Test stopped by user")
                break
        
        # Calculate overall statistics
        total_elapsed = time.time() - start_time
        logger.info(f"Camera test completed after {total_elapsed:.2f} seconds")
        
        # Release resources
        cap.release()
        cv2.destroyAllWindows()
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing camera: {e}")
        # Make sure to clean up
        try:
            if 'cap' in locals() and cap is not None:
                cap.release()
            cv2.destroyAllWindows()
        except:
            pass
        return False


def list_available_cameras(max_cameras=10):
    """
    List all available cameras.
    
    Args:
        max_cameras: Maximum number of cameras to check
        
    Returns:
        list: List of available camera indices
    """
    logger.info(f"Searching for cameras (checking indices 0-{max_cameras-1})...")
    available_cameras = []
    
    for i in range(max_cameras):
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    logger.info(f"Camera {i} is available")
                    driver_name = cap.getBackendName() if hasattr(cap, 'getBackendName') else "Unknown"
                    logger.info(f"  - Backend: {driver_name}")
                    logger.info(f"  - Frame size: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
                    available_cameras.append(i)
                else:
                    logger.warning(f"Camera {i} opened but could not read frame")
            cap.release()
        except Exception as e:
            logger.debug(f"Could not open camera {i}: {e}")
    
    if not available_cameras:
        logger.warning("No cameras found!")
    else:
        logger.info(f"Found {len(available_cameras)} camera(s): {available_cameras}")
    
    return available_cameras


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test camera functionality")
    parser.add_argument("--camera", type=int, default=0, help="Camera index to test")
    parser.add_argument("--width", type=int, default=1280, help="Target frame width")
    parser.add_argument("--height", type=int, default=720, help="Target frame height")
    parser.add_argument("--fps", type=int, default=30, help="Target frame rate")
    parser.add_argument("--duration", type=int, default=0, help="Test duration in seconds (0 for indefinite)")
    parser.add_argument("--list", action="store_true", help="List all available cameras")
    
    args = parser.parse_args()
    
    if args.list:
        list_available_cameras()
    else:
        test_camera(
            camera_idx=args.camera, 
            width=args.width, 
            height=args.height, 
            fps=args.fps,
            test_duration=args.duration
        ) 