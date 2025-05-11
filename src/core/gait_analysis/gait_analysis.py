#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gait Analysis Module for NeuroApp_RAS

This module provides functionality to detect steps and calculate gait parameters
such as cadence, stride length, and walking velocity based on pose keypoints.
"""

import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Any
from collections import deque
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt

logger = logging.getLogger(__name__)


class StepPhase(Enum):
    """Enumeration of gait cycle phases."""
    SWING = 0  # Foot is in the air (swing phase)
    STANCE = 1  # Foot is on the ground (stance phase)
    UNKNOWN = 2  # Phase cannot be determined


class GaitEvent(Enum):
    """Enumeration of gait events."""
    HEEL_STRIKE = 0  # Initial contact of heel with ground
    TOE_OFF = 1  # Moment when foot leaves ground
    MID_STANCE = 2  # Mid-point of stance phase
    MID_SWING = 3  # Mid-point of swing phase


class GaitAnalyzer:
    """Analyzes gait parameters from pose keypoints."""
    
    def __init__(self, 
                 history_size: int = 60,  # Default for ~2 seconds at 30 fps
                 step_detection_threshold: float = 0.03,
                 step_cooldown_frames: int = 10,
                 smoothing_window: int = 5,
                 user_height_cm: Optional[float] = None,
                 calibration_stride_length_cm: Optional[float] = None):
        """
        Initialize the gait analyzer with specified parameters.
        
        Args:
            history_size: Number of frames to keep in history for analysis
            step_detection_threshold: Threshold for vertical displacement to detect steps
            step_cooldown_frames: Minimum frames between consecutive steps
            smoothing_window: Window size for signal smoothing
            user_height_cm: User's height in centimeters (for stride length estimation)
            calibration_stride_length_cm: Known stride length for calibration
        """
        self.history_size = history_size
        self.step_detection_threshold = step_detection_threshold
        self.step_cooldown_frames = step_cooldown_frames
        self.smoothing_window = smoothing_window
        self.user_height_cm = user_height_cm
        self.calibration_stride_length_cm = calibration_stride_length_cm
        
        # Initialize keypoint history
        self.keypoint_history = deque(maxlen=history_size)
        self.timestamp_history = deque(maxlen=history_size)
        
        # Step detection state
        self.last_left_step_frame = -step_cooldown_frames
        self.last_right_step_frame = -step_cooldown_frames
        self.step_timestamps = deque(maxlen=20)  # Store timestamps of recent steps
        self.step_positions = deque(maxlen=20)  # Store steps positions with timestamp
        
        # Gait parameters
        self.cadence = 0.0  # steps per minute
        self.stride_length = 0.0  # in meters
        self.walking_velocity = 0.0  # in meters per second
        self.step_count = 0
        self.left_step_count = 0
        self.right_step_count = 0
        self.gait_asymmetry = None  # Changed from symmetry to asymmetry
        
        # Pixel to metric conversion (will be calibrated)
        self.pixel_to_meter_ratio = 0.01  # Default placeholder
        
        # For visualization
        self.left_ankle_positions = deque(maxlen=history_size)
        self.right_ankle_positions = deque(maxlen=history_size)
        
        logger.info("Gait analyzer initialized")
    
    def process_keypoints(self, keypoints: Dict, timestamp: float) -> Dict:
        """
        Process new keypoints to update gait parameters.
        
        Args:
            keypoints: Dictionary of detected keypoints
            timestamp: Time when keypoints were detected
            
        Returns:
            Dict containing gait parameters and step detection information
        """
        if not keypoints:
            return self._get_empty_result()
        
        # Store keypoints and timestamp in history
        self.keypoint_history.append(keypoints)
        self.timestamp_history.append(timestamp)
        
        # Extract and store ankle positions for visualization
        if 'LEFT_ANKLE' in keypoints and keypoints['LEFT_ANKLE']['visibility'] > 0.5:
            self.left_ankle_positions.append({
                'x': keypoints['LEFT_ANKLE']['x'],
                'y': keypoints['LEFT_ANKLE']['y']
            })
        
        if 'RIGHT_ANKLE' in keypoints and keypoints['RIGHT_ANKLE']['visibility'] > 0.5:
            self.right_ankle_positions.append({
                'x': keypoints['RIGHT_ANKLE']['x'],
                'y': keypoints['RIGHT_ANKLE']['y']
            })
        
        # Only analyze if we have enough history
        if len(self.keypoint_history) < max(self.smoothing_window, 3):
            return self._get_empty_result()
        
        # Detect steps
        current_frame = len(self.keypoint_history) - 1
        step_info = self._detect_steps(current_frame)
        
        # Update gait parameters
        self._update_gait_parameters()
        
        return {
            'step_detected': step_info['step_detected'],
            'step_foot': step_info['step_foot'],
            'cadence': self.cadence,
            'stride_length': self.stride_length,
            'walking_velocity': self.walking_velocity,
            'step_count': self.step_count,
            'left_step_count': self.left_step_count,
            'right_step_count': self.right_step_count,
            'left_foot_phase': self._get_foot_phase('LEFT'),
            'right_foot_phase': self._get_foot_phase('RIGHT'),
            'gait_asymmetry': self.gait_asymmetry,
            'vertical_displacement': step_info.get('vertical_displacement', {}),
            'is_walking': self._is_walking()
        }
    
    def _detect_steps(self, current_frame: int) -> Dict:
        """
        Detect steps based on ankle vertical displacement.
        
        Args:
            current_frame: Index of current frame in history
            
        Returns:
            Dict containing step detection results
        """
        result = {
            'step_detected': False,
            'step_foot': None,
            'vertical_displacement': {
                'left': 0.0,
                'right': 0.0
            }
        }
        
        # Get smoothed ankle vertical positions
        left_ankle_positions = self._get_smoothed_vertical_positions('LEFT_ANKLE')
        right_ankle_positions = self._get_smoothed_vertical_positions('RIGHT_ANKLE')
        
        if not left_ankle_positions or not right_ankle_positions:
            return result
        
        # Initialize displacement variables with default values
        left_displacement = 0.0
        right_displacement = 0.0
            
        # Calculate vertical displacement for recent frames
        if len(left_ankle_positions) > 1:
            left_displacement = left_ankle_positions[-2] - left_ankle_positions[-1]
            result['vertical_displacement']['left'] = left_displacement
        
        if len(right_ankle_positions) > 1:
            right_displacement = right_ankle_positions[-2] - right_ankle_positions[-1]
            result['vertical_displacement']['right'] = right_displacement
        
        # Only check for steps if we have enough data for displacement calculation    
        left_step_detected = False
        right_step_detected = False
        
        if len(left_ankle_positions) > 1:
            # Detect left step (downward movement after peak)
            left_step_detected = (
                left_displacement > self.step_detection_threshold and 
                current_frame - self.last_left_step_frame > self.step_cooldown_frames
            )
        
        if len(right_ankle_positions) > 1:
            # Detect right step (downward movement after peak)
            right_step_detected = (
                right_displacement > self.step_detection_threshold and 
                current_frame - self.last_right_step_frame > self.step_cooldown_frames
            )
        
        # Update step state
        if left_step_detected:
            self.last_left_step_frame = current_frame
            self.step_count += 1
            self.left_step_count += 1
            result['step_detected'] = True
            result['step_foot'] = 'LEFT'
            
            # Record step for cadence and stride calculations
            current_time = self.timestamp_history[-1]
            self.step_timestamps.append(current_time)
            
            # Record position for stride length calculation
            if 'LEFT_ANKLE' in self.keypoint_history[-1]:
                self.step_positions.append({
                    'foot': 'LEFT',
                    'x': self.keypoint_history[-1]['LEFT_ANKLE']['x'],
                    'y': self.keypoint_history[-1]['LEFT_ANKLE']['y'],
                    'time': current_time
                })
            
        elif right_step_detected:
            self.last_right_step_frame = current_frame
            self.step_count += 1
            self.right_step_count += 1
            result['step_detected'] = True
            result['step_foot'] = 'RIGHT'
            
            # Record step for cadence and stride calculations
            current_time = self.timestamp_history[-1]
            self.step_timestamps.append(current_time)
            
            # Record position for stride length calculation
            if 'RIGHT_ANKLE' in self.keypoint_history[-1]:
                self.step_positions.append({
                    'foot': 'RIGHT',
                    'x': self.keypoint_history[-1]['RIGHT_ANKLE']['x'],
                    'y': self.keypoint_history[-1]['RIGHT_ANKLE']['y'],
                    'time': current_time
                })
        
        return result
    
    def _get_smoothed_vertical_positions(self, keypoint_name: str) -> List[float]:
        """
        Extract smoothed vertical positions of a keypoint over time.
        
        Args:
            keypoint_name: Name of the keypoint to extract
            
        Returns:
            List of smoothed vertical positions
        """
        positions = []
        
        for keypoints in self.keypoint_history:
            if keypoint_name in keypoints and keypoints[keypoint_name]['visibility'] > 0.5:
                positions.append(keypoints[keypoint_name]['y'])
        
        if len(positions) < self.smoothing_window:
            return positions
        
        # Apply smoothing (simple moving average)
        smoothed = []
        for i in range(len(positions) - self.smoothing_window + 1):
            window = positions[i:i + self.smoothing_window]
            smoothed.append(sum(window) / len(window))
            
        return smoothed
    
    def _update_gait_parameters(self) -> None:
        """
        Update gait parameters based on recent step information.
        """
        # Update cadence
        self._update_cadence()
        
        # Update stride length
        self._update_stride_length()
        
        # Update walking velocity
        if self.cadence > 0 and self.stride_length > 0:
            # Velocity = stride length * cadence / 120 (converting steps per minute to strides per second)
            self.walking_velocity = self.stride_length * self.cadence / 120
        
        # Update gait asymmetry
        self.gait_asymmetry = self._calculate_gait_asymmetry()
    
    def _update_cadence(self) -> None:
        """
        Update cadence (steps per minute) based on recent steps.
        """
        if len(self.step_timestamps) < 2:
            self.cadence = 0.0
            return
        
        # Calculate time differences between consecutive steps
        time_diffs = []
        for i in range(1, len(self.step_timestamps)):
            time_diff = self.step_timestamps[i] - self.step_timestamps[i-1]
            if time_diff > 0:
                time_diffs.append(time_diff)
        
        if not time_diffs:
            self.cadence = 0.0
            return
        
        # Calculate average time between steps
        avg_step_time = sum(time_diffs) / len(time_diffs)
        
        # Convert to steps per minute
        if avg_step_time > 0:
            self.cadence = 60.0 / avg_step_time
        else:
            self.cadence = 0.0
    
    def _update_stride_length(self) -> None:
        """
        Update stride length based on ankle positions during steps.
        """
        # Check if we have enough step positions
        if len(self.step_positions) < 3:
            self.stride_length = 0.0
            return
        
        # Find consecutive steps with the same foot
        stride_distances = []
        
        for i in range(len(self.step_positions) - 2):
            current = self.step_positions[i]
            next_same_foot = None
            
            # Find the next step with the same foot
            for j in range(i + 1, len(self.step_positions)):
                if self.step_positions[j]['foot'] == current['foot']:
                    next_same_foot = self.step_positions[j]
                    break
            
            if next_same_foot:
                # Calculate distance between consecutive same-foot steps (stride)
                dx = next_same_foot['x'] - current['x']
                distance = abs(dx)  # Using just horizontal distance for stride
                stride_distances.append(distance)
        
        if not stride_distances:
            self.stride_length = 0.0
            return
        
        # Calculate average stride distance in normalized coordinates
        avg_stride_distance = sum(stride_distances) / len(stride_distances)
        
        # Convert to meters using calibration or estimation
        if self.calibration_stride_length_cm:
            # Use calibration value to set pixel-to-meter ratio
            self.pixel_to_meter_ratio = self.calibration_stride_length_cm / (100 * avg_stride_distance)
            self.stride_length = self.calibration_stride_length_cm / 100  # Convert cm to m
        elif self.user_height_cm:
            # Estimate stride length based on height (general anthropometric relation)
            # Typical stride length is approximately 0.8-0.85 times height
            estimated_stride_m = 0.83 * self.user_height_cm / 100
            self.pixel_to_meter_ratio = estimated_stride_m / avg_stride_distance
            self.stride_length = estimated_stride_m
        else:
            # Use default conversion (less accurate)
            self.stride_length = avg_stride_distance * self.pixel_to_meter_ratio
    
    def _get_foot_phase(self, foot: str) -> StepPhase:
        """
        Determine the current phase of a foot in the gait cycle.
        
        Args:
            foot: 'LEFT' or 'RIGHT'
            
        Returns:
            Current phase of the foot
        """
        if len(self.keypoint_history) < 3:
            return StepPhase.UNKNOWN
        
        ankle_key = f"{foot}_ANKLE"
        toe_key = f"{foot}_FOOT_INDEX"
        
        # Check if keypoints are available
        if (ankle_key not in self.keypoint_history[-1] or 
            ankle_key not in self.keypoint_history[-2] or 
            toe_key not in self.keypoint_history[-1]):
            return StepPhase.UNKNOWN
        
        current_ankle = self.keypoint_history[-1][ankle_key]
        prev_ankle = self.keypoint_history[-2][ankle_key]
        current_toe = self.keypoint_history[-1][toe_key]
        
        # Check visibility
        if (current_ankle['visibility'] < 0.5 or 
            prev_ankle['visibility'] < 0.5 or 
            current_toe['visibility'] < 0.5):
            return StepPhase.UNKNOWN
        
        # Check for stance phase - ankle has minimal vertical movement and toe is below ankle
        is_vertical_stable = abs(current_ankle['y'] - prev_ankle['y']) < 0.01
        is_toe_below = current_toe['y'] > current_ankle['y']
        
        if is_vertical_stable and is_toe_below:
            return StepPhase.STANCE
        else:
            return StepPhase.SWING
    
    def _calculate_gait_asymmetry(self) -> float:
        """Calculate walking asymmetry as percentage difference in step timing between feet.
        
        Walking asymmetry is the percentage of time that steps with one foot are faster or
        slower than the other foot. Lower values indicate a healthier walking pattern.
        
        Returns:
            float: Walking asymmetry percentage (0-100%). Lower values indicate better symmetry.
                   Returns None if insufficient steps detected.
        """
        # We need at least 2 steps from each foot to calculate asymmetry
        left_steps = [step for step in self.step_positions if step['foot'] == 'LEFT']
        right_steps = [step for step in self.step_positions if step['foot'] == 'RIGHT']
        
        if len(left_steps) < 2 or len(right_steps) < 2:
            return None
        
        # Calculate step time intervals for each foot
        left_intervals = []
        right_intervals = []
        
        for i in range(1, len(left_steps)):
            left_intervals.append(left_steps[i]['time'] - left_steps[i-1]['time'])
        
        for i in range(1, len(right_steps)):
            right_intervals.append(right_steps[i]['time'] - right_steps[i-1]['time'])
        
        # Calculate average step time for each foot
        avg_left_time = sum(left_intervals) / len(left_intervals) if left_intervals else 0
        avg_right_time = sum(right_intervals) / len(right_intervals) if right_intervals else 0
        
        # If either average is zero, we can't calculate (prevents division by zero)
        if avg_left_time == 0 or avg_right_time == 0:
            return None
        
        # Calculate the timing difference as a percentage using ASI formula
        # |Left-Right|/((Left+Right)/2) * 100%
        avg_step_time = (avg_left_time + avg_right_time) / 2
        absolute_difference = abs(avg_left_time - avg_right_time)
        asymmetry_percentage = (absolute_difference / avg_step_time) * 100
        
        return asymmetry_percentage
    
    def _is_walking(self) -> bool:
        """
        Determine if the person is currently walking.
        
        Returns:
            True if the person appears to be walking, False otherwise
        """
        # Check if we've detected steps recently
        if not self.step_timestamps:
            return False
        
        # If the last step was within 2 seconds, consider walking
        current_time = self.timestamp_history[-1] if self.timestamp_history else time.time()
        last_step_time = self.step_timestamps[-1]
        
        return (current_time - last_step_time) < 2.0
    
    def _get_empty_result(self) -> Dict:
        """
        Return empty result when analysis cannot be performed.
        
        Returns:
            Dict with default values
        """
        return {
            'step_detected': False,
            'step_foot': None,
            'cadence': 0.0,
            'stride_length': 0.0,
            'walking_velocity': 0.0,
            'step_count': self.step_count,
            'left_step_count': self.left_step_count,
            'right_step_count': self.right_step_count,
            'left_foot_phase': StepPhase.UNKNOWN,
            'right_foot_phase': StepPhase.UNKNOWN,
            'gait_asymmetry': None,
            'vertical_displacement': {'left': 0.0, 'right': 0.0},
            'is_walking': False
        }
    
    def reset(self) -> None:
        """
        Reset the gait analyzer state.
        """
        self.keypoint_history.clear()
        self.timestamp_history.clear()
        self.left_ankle_positions.clear()
        self.right_ankle_positions.clear()
        self.step_timestamps.clear()
        self.step_positions.clear()
        
        self.last_left_step_frame = -self.step_cooldown_frames
        self.last_right_step_frame = -self.step_cooldown_frames
        
        self.cadence = 0.0
        self.stride_length = 0.0
        self.walking_velocity = 0.0
        self.step_count = 0
        self.left_step_count = 0
        self.right_step_count = 0
        self.gait_asymmetry = None
        
        logger.info("Gait analyzer reset")
    
    def get_visualization_data(self) -> Dict:
        """
        Get data for visualizing gait analysis.
        
        Returns:
            Dict containing visualization data
        """
        return {
            'left_ankle_positions': list(self.left_ankle_positions),
            'right_ankle_positions': list(self.right_ankle_positions),
            'cadence': self.cadence,
            'stride_length': self.stride_length,
            'walking_velocity': self.walking_velocity,
            'step_count': self.step_count,
            'gait_asymmetry': self.gait_asymmetry
        }
    
    def get_current_gait_parameters(self) -> Dict[str, Any]:
        """
        Get current gait parameters for synchronization with music.
        
        Returns:
            Dict containing current gait parameters
        """
        return {
            'cadence': self.cadence,
            'stride_length': self.stride_length,
            'velocity': self.walking_velocity,
            'is_walking': self._is_walking(),
            'confidence': 1.0 if self._is_walking() and self.cadence > 40.0 else 0.5,
            'gait_asymmetry': self.gait_asymmetry
        }
    
    def calibrate(self, known_stride_length_cm: float) -> None:
        """
        Calibrate the analyzer with a known stride length.
        
        Args:
            known_stride_length_cm: Known stride length in centimeters
        """
        self.calibration_stride_length_cm = known_stride_length_cm
        logger.info(f"Gait analyzer calibrated with stride length: {known_stride_length_cm} cm")
        
        # Update stride length with new calibration
        self._update_stride_length()
    
    def set_user_height(self, height_cm: float) -> None:
        """
        Set user height for better stride length estimation.
        
        Args:
            height_cm: User height in centimeters
        """
        self.user_height_cm = height_cm
        logger.info(f"User height set to: {height_cm} cm")
        
        # Update stride length with new height information
        self._update_stride_length() 