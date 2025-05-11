#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pose Estimation Module for NeuroApp_RAS

This module provides functionality to detect human pose from video frames using MediaPipe.
It focuses on extracting and filtering lower limb keypoints for gait analysis.
"""

import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import mediapipe as mp

logger = logging.getLogger(__name__)


class KeypointType(Enum):
    """Enumeration of keypoint types relevant for gait analysis.
    refer https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
    """
    # Upper body keypoints
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    
    # Lower body keypoints (primary focus)
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


class PoseEstimator:
    """Handles human pose estimation using MediaPipe."""
    
    def __init__(self, 
                 model_complexity: int = 1,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 enable_segmentation: bool = False,
                 smooth_landmarks: bool = True,
                 static_image_mode: bool = False,
                 filter_window_size: int = 5,
                 orientation_flip: bool = False):
        """
        Initialize the pose estimator with specified parameters.
        
        Args:
            model_complexity: MediaPipe model complexity (0, 1, or 2)
            min_detection_confidence: Minimum confidence for pose detection
            min_tracking_confidence: Minimum confidence for pose tracking
            enable_segmentation: Enable person segmentation
            smooth_landmarks: Apply temporal filtering to landmarks
            static_image_mode: Process each frame independently
            filter_window_size: Window size for temporal filtering
            orientation_flip: Flip left/right orientation of keypoints (useful when input is flipped)
        """
        self.model_complexity = model_complexity
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.enable_segmentation = enable_segmentation
        self.smooth_landmarks = smooth_landmarks
        self.static_image_mode = static_image_mode
        self.filter_window_size = filter_window_size
        self.orientation_flip = orientation_flip
        
        # Initialize MediaPipe Pose
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.pose = self.mp_pose.Pose(
            model_complexity=self.model_complexity,
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
            enable_segmentation=self.enable_segmentation,
            smooth_landmarks=self.smooth_landmarks,
            static_image_mode=self.static_image_mode
        )
        
        # Initialize landmark history for temporal filtering
        self.landmark_history = {}
        for keypoint in KeypointType:
            self.landmark_history[keypoint] = []
        
        self.processing_time = 0
        self.frame_count = 0
        self.last_detection_time = 0
        
        logger.info(f"Pose estimator initialized with model complexity {model_complexity}")
        if self.orientation_flip:
            logger.info("Left/right orientation flipping is enabled")
    
    def process_frame(self, frame: np.ndarray) -> Tuple[Optional[Dict], Optional[np.ndarray]]:
        """
        Process a video frame to detect human pose.
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Tuple containing:
                - Dict or None: Detected pose data with keypoints and confidence scores
                - np.ndarray or None: Visualization frame with pose overlay
        """
        if frame is None:
            return None, None
        
        start_time = time.time()
        self.frame_count += 1
        
        try:
            # Convert BGR to RGB for MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame with MediaPipe Pose
            results = self.pose.process(frame_rgb) # return mp data incl. landmark list (x,y,z,visibility)
            
            # Calculate processing time
            self.processing_time = time.time() - start_time
            self.last_detection_time = time.time()
            
            if not results.pose_landmarks:
                logger.debug("No pose detected in frame")
                return None, None
            
            # Extract keypoints and apply temporal filtering
            keypoints = self._extract_keypoints(results.pose_landmarks)
            
            # Create visualization if needed
            visualization = self._create_visualization(frame, results)
            
            return keypoints, visualization
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return None, None
    
    def _extract_keypoints(self, pose_landmarks) -> Dict:
        """
        Extract relevant keypoints from pose landmarks and apply temporal filtering.
        
        Args:
            pose_landmarks: MediaPipe pose landmarks
            
        Returns:
            Dict containing filtered keypoints with coordinates and confidence scores
        """
        keypoints = {}
        
        for keypoint in KeypointType:
            idx = keypoint.value
            landmark = pose_landmarks.landmark[idx]
            
            # Store raw keypoint data
            raw_data = {
                'x': landmark.x,
                'y': landmark.y,
                'z': landmark.z,
                'visibility': landmark.visibility
            }
            
            # Add to history for filtering
            if len(self.landmark_history[keypoint]) >= self.filter_window_size:
                self.landmark_history[keypoint].pop(0)
            self.landmark_history[keypoint].append(raw_data)
            
            # Apply temporal filtering
            filtered_data = self._apply_temporal_filter(keypoint)
            
            keypoints[keypoint.name] = filtered_data
        
        return keypoints
    
    def _apply_temporal_filter(self, keypoint: KeypointType) -> Dict:
        """
        Apply temporal filtering to smooth keypoint data.
        
        Args:
            keypoint: The keypoint type to filter
            
        Returns:
            Dict containing filtered keypoint data
        """
        history = self.landmark_history[keypoint]
        
        if not history:
            return {'x': 0, 'y': 0, 'z': 0, 'visibility': 0, 'filtered': False}
        
        # If not enough history for filtering, return the latest raw data
        if len(history) < 3:
            latest = history[-1]
            latest['filtered'] = False
            return latest
        
        # Apply weighted average filter with more weight to recent frames
        # and considering visibility as confidence
        total_weight = 0
        filtered_x = 0
        filtered_y = 0
        filtered_z = 0
        
        for i, data in enumerate(history):
            # Higher weight for more recent and more visible points
            weight = (i + 1) * data['visibility']
            filtered_x += data['x'] * weight
            filtered_y += data['y'] * weight
            filtered_z += data['z'] * weight
            total_weight += weight
        
        # Avoid division by zero
        if total_weight > 0:
            filtered_x /= total_weight
            filtered_y /= total_weight
            filtered_z /= total_weight
        else:
            # Fallback to latest data if weights sum to zero
            filtered_x = history[-1]['x']
            filtered_y = history[-1]['y']
            filtered_z = history[-1]['z']
        
        # Average visibility
        avg_visibility = sum(data['visibility'] for data in history) / len(history)
        
        return {
            'x': filtered_x,
            'y': filtered_y,
            'z': filtered_z,
            'visibility': avg_visibility,
            'filtered': True
        }
    
    def _flip_keypoint_orientation(self, keypoints: Dict) -> Dict:
        """
        Flip left/right orientation of keypoints.
        
        This is useful when the input video is horizontally flipped (e.g., webcam mirror effect)
        to ensure that the labeled left/right sides match what the user sees.
        
        Note: This function is currently unused as we only swap the display labels in the
        visualization, not the actual keypoint data. It's preserved for potential future use.
        
        Args:
            keypoints: Dictionary of keypoints
            
        Returns:
            Dictionary with left/right keypoints swapped
        """
        flipped_keypoints = keypoints.copy()
        
        # Define pairs of left/right keypoints to swap
        swap_pairs = [
            ('LEFT_SHOULDER', 'RIGHT_SHOULDER'),
            ('LEFT_HIP', 'RIGHT_HIP'),
            ('LEFT_KNEE', 'RIGHT_KNEE'),
            ('LEFT_ANKLE', 'RIGHT_ANKLE'),
            ('LEFT_HEEL', 'RIGHT_HEEL'),
            ('LEFT_FOOT_INDEX', 'RIGHT_FOOT_INDEX')
        ]
        
        # Swap each pair
        for left, right in swap_pairs:
            if left in keypoints and right in keypoints:
                flipped_keypoints[left] = keypoints[right]
                flipped_keypoints[right] = keypoints[left]
        
        return flipped_keypoints
    
    def _create_visualization(self, frame: np.ndarray, results) -> np.ndarray:
        """
        Create visualization frame with pose landmarks and connections.
        
        Args:
            frame: Input frame
            results: MediaPipe pose results
            
        Returns:
            Visualization frame with pose overlay
        """
        # Create a copy of the frame for visualization
        vis_frame = frame.copy()
        
        # Draw pose landmarks and connections
        self.mp_drawing.draw_landmarks(
            vis_frame,
            results.pose_landmarks,
            self.mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
        )
        
        # Highlight lower body keypoints with different colors
        if results.pose_landmarks:
            h, w, _ = vis_frame.shape  # height, width, channel
            landmarks = results.pose_landmarks.landmark
            
            # Draw circles for lower body keypoints with color based on visibility
            lower_body_keypoints = [
                KeypointType.LEFT_HIP, KeypointType.RIGHT_HIP,
                KeypointType.LEFT_KNEE, KeypointType.RIGHT_KNEE,
                KeypointType.LEFT_ANKLE, KeypointType.RIGHT_ANKLE,
                KeypointType.LEFT_HEEL, KeypointType.RIGHT_HEEL,
                KeypointType.LEFT_FOOT_INDEX, KeypointType.RIGHT_FOOT_INDEX
            ]
            
            for kp in lower_body_keypoints:
                idx = kp.value
                landmark = landmarks[idx]
                
                # Skip if visibility is too low
                if landmark.visibility < 0.5:
                    continue
                
                # Convert normalized coordinates to pixel coordinates
                cx, cy = int(landmark.x * w), int(landmark.y * h)
                
                # Color based on visibility (green to red)
                color = (0, int(255 * landmark.visibility), int(255 * (1 - landmark.visibility)))
                
                # Draw circle
                cv2.circle(vis_frame, (cx, cy), 10, color, -1)
                
                # Add keypoint name - if orientation is flipped, swap LEFT/RIGHT in display names
                display_name = kp.name
                if self.orientation_flip:
                    if "LEFT" in display_name:
                        display_name = display_name.replace("LEFT", "RIGHT")
                    elif "RIGHT" in display_name:
                        display_name = display_name.replace("RIGHT", "LEFT")
                
                cv2.putText(vis_frame, display_name, (cx + 10, cy), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add processing info
        fps_text = f"FPS: {1.0/self.processing_time:.1f}" if self.processing_time > 0 else "FPS: N/A"
        cv2.putText(vis_frame, fps_text, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Add orientation information if flipping is enabled
        if self.orientation_flip:
            cv2.putText(
                vis_frame,
                "L/R Labels: Flipped for Display",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )
        
        return vis_frame
    
    def get_lower_limb_angles(self, keypoints: Dict) -> Dict[str, float]:
        """
        Calculate joint angles for lower limbs.
        
        Args:
            keypoints: Dictionary of detected keypoints
            
        Returns:
            Dict containing joint angles in degrees
        """
        if not keypoints:
            return {}
        
        angles = {}
        
        # Calculate left knee angle
        if all(k in keypoints for k in ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE']):
            hip = np.array([keypoints['LEFT_HIP']['x'], keypoints['LEFT_HIP']['y']])
            knee = np.array([keypoints['LEFT_KNEE']['x'], keypoints['LEFT_KNEE']['y']])
            ankle = np.array([keypoints['LEFT_ANKLE']['x'], keypoints['LEFT_ANKLE']['y']])
            
            angles['left_knee_angle'] = self._calculate_angle(hip, knee, ankle)
        
        # Calculate right knee angle
        if all(k in keypoints for k in ['RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE']):
            hip = np.array([keypoints['RIGHT_HIP']['x'], keypoints['RIGHT_HIP']['y']])
            knee = np.array([keypoints['RIGHT_KNEE']['x'], keypoints['RIGHT_KNEE']['y']])
            ankle = np.array([keypoints['RIGHT_ANKLE']['x'], keypoints['RIGHT_ANKLE']['y']])
            
            angles['right_knee_angle'] = self._calculate_angle(hip, knee, ankle)
        
        # Calculate hip angles
        if all(k in keypoints for k in ['LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE']):
            shoulder = np.array([keypoints['LEFT_SHOULDER']['x'], keypoints['LEFT_SHOULDER']['y']])
            hip = np.array([keypoints['LEFT_HIP']['x'], keypoints['LEFT_HIP']['y']])
            knee = np.array([keypoints['LEFT_KNEE']['x'], keypoints['LEFT_KNEE']['y']])
            
            angles['left_hip_angle'] = self._calculate_angle(shoulder, hip, knee)
        
        if all(k in keypoints for k in ['RIGHT_SHOULDER', 'RIGHT_HIP', 'RIGHT_KNEE']):
            shoulder = np.array([keypoints['RIGHT_SHOULDER']['x'], keypoints['RIGHT_SHOULDER']['y']])
            hip = np.array([keypoints['RIGHT_HIP']['x'], keypoints['RIGHT_HIP']['y']])
            knee = np.array([keypoints['RIGHT_KNEE']['x'], keypoints['RIGHT_KNEE']['y']])
            
            angles['right_hip_angle'] = self._calculate_angle(shoulder, hip, knee)
        
        return angles
    
    def _calculate_angle(self, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        """
        Calculate the angle between three points in 2D space.
        
        Args:
            a: First point coordinates
            b: Middle point coordinates (vertex)
            c: Third point coordinates
            
        Returns:
            Angle in degrees
        """
        ba = a - b
        bc = c - b
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)  # Ensure domain of arccos
        
        angle = np.degrees(np.arccos(cosine_angle))
        return angle
    
    def detect_occlusion(self, keypoints: Dict) -> Dict[str, bool]:
        """
        Detect occlusion of key body parts based on visibility scores.
        
        Args:
            keypoints: Dictionary of detected keypoints
            
        Returns:
            Dict containing occlusion status for different body parts
        """
        if not keypoints:
            return {'left_leg': True, 'right_leg': True, 'upper_body': True}
        
        occlusion = {}
        
        # Check left leg occlusion
        left_leg_keypoints = ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE', 'LEFT_HEEL', 'LEFT_FOOT_INDEX']
        left_leg_visibility = [keypoints[k]['visibility'] if k in keypoints else 0 for k in left_leg_keypoints]
        occlusion['left_leg'] = sum(left_leg_visibility) / len(left_leg_visibility) < 0.5
        
        # Check right leg occlusion
        right_leg_keypoints = ['RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE', 'RIGHT_HEEL', 'RIGHT_FOOT_INDEX']
        right_leg_visibility = [keypoints[k]['visibility'] if k in keypoints else 0 for k in right_leg_keypoints]
        occlusion['right_leg'] = sum(right_leg_visibility) / len(right_leg_visibility) < 0.5
        
        # Check upper body occlusion
        upper_body_keypoints = ['NOSE', 'LEFT_SHOULDER', 'RIGHT_SHOULDER']
        upper_body_visibility = [keypoints[k]['visibility'] if k in keypoints else 0 for k in upper_body_keypoints]
        occlusion['upper_body'] = sum(upper_body_visibility) / len(upper_body_visibility) < 0.5
        
        return occlusion
    
    def detect_subject_out_of_frame(self, keypoints: Dict) -> bool:
        """
        Detect if the subject is out of frame based on keypoint visibility.
        
        Args:
            keypoints: Dictionary of detected keypoints
            
        Returns:
            bool: True if subject is likely out of frame, False otherwise
        """
        if not keypoints:
            return True
        
        # Check visibility of key points
        key_points = ['NOSE', 'LEFT_HIP', 'RIGHT_HIP', 'LEFT_ANKLE', 'RIGHT_ANKLE']
        visible_count = sum(1 for k in key_points if k in keypoints and keypoints[k]['visibility'] > 0.3)
        
        # If less than 3 key points are visible, consider subject out of frame
        return visible_count < 3
    
    def detect_fall(self, keypoints: Dict, prev_keypoints: Optional[Dict] = None) -> bool:
        """
        Detect potential falls based on multiple criteria including vertical displacement,
        posture changes, and keypoint visibility changes.
        
        Args:
            keypoints: Current frame keypoints
            prev_keypoints: Previous frame keypoints for comparison
            
        Returns:
            bool: True if fall is detected, False otherwise
        """
        if not keypoints or not prev_keypoints:
            return False
        
        # Initialize fall detection score
        fall_score = 0
        fall_threshold = 2  # Need at least 2 criteria to trigger fall detection
        detection_reasons = []
        
        # Criterion 1: Check for sudden loss of upper body keypoints
        upper_body_keypoints = ['NOSE', 'LEFT_SHOULDER', 'RIGHT_SHOULDER']
        prev_visible = sum(1 for k in upper_body_keypoints if k in prev_keypoints and prev_keypoints[k]['visibility'] > 0.5)
        curr_visible = sum(1 for k in upper_body_keypoints if k in keypoints and keypoints[k]['visibility'] > 0.5)
        
        if prev_visible >= 2 and curr_visible <= 1:
            fall_score += 1
            detection_reasons.append("Loss of upper body keypoints")
        
        # Criterion 2: Check for sudden vertical displacement of head/nose
        if 'NOSE' in keypoints and 'NOSE' in prev_keypoints:
            prev_y = prev_keypoints['NOSE']['y']
            curr_y = keypoints['NOSE']['y']
            
            # If nose position suddenly moves down significantly (lowered threshold)
            if curr_y - prev_y > 0.15:  # More sensitive threshold
                fall_score += 1
                detection_reasons.append(f"Vertical head displacement: {(curr_y - prev_y):.3f}")
        
        # Criterion 3: Check for sudden change in body orientation
        # Calculate the angle between shoulders and hips before and after
        if all(k in keypoints and k in prev_keypoints for k in ['LEFT_SHOULDER', 'RIGHT_SHOULDER', 'LEFT_HIP', 'RIGHT_HIP']):
            # Get shoulder midpoint
            prev_shoulder_mid_x = (prev_keypoints['LEFT_SHOULDER']['x'] + prev_keypoints['RIGHT_SHOULDER']['x']) / 2
            prev_shoulder_mid_y = (prev_keypoints['LEFT_SHOULDER']['y'] + prev_keypoints['RIGHT_SHOULDER']['y']) / 2
            curr_shoulder_mid_x = (keypoints['LEFT_SHOULDER']['x'] + keypoints['RIGHT_SHOULDER']['x']) / 2
            curr_shoulder_mid_y = (keypoints['LEFT_SHOULDER']['y'] + keypoints['RIGHT_SHOULDER']['y']) / 2
            
            # Get hip midpoint
            prev_hip_mid_x = (prev_keypoints['LEFT_HIP']['x'] + prev_keypoints['RIGHT_HIP']['x']) / 2
            prev_hip_mid_y = (prev_keypoints['LEFT_HIP']['y'] + prev_keypoints['RIGHT_HIP']['y']) / 2
            curr_hip_mid_x = (keypoints['LEFT_HIP']['x'] + keypoints['RIGHT_HIP']['x']) / 2
            curr_hip_mid_y = (keypoints['LEFT_HIP']['y'] + keypoints['RIGHT_HIP']['y']) / 2
            
            # Calculate torso vector angle with vertical
            prev_dx = prev_shoulder_mid_x - prev_hip_mid_x
            prev_dy = prev_shoulder_mid_y - prev_hip_mid_y
            curr_dx = curr_shoulder_mid_x - curr_hip_mid_x
            curr_dy = curr_shoulder_mid_y - curr_hip_mid_y
            
            prev_angle = np.degrees(np.arctan2(prev_dx, -prev_dy))  # Negative dy because y increases downward
            curr_angle = np.degrees(np.arctan2(curr_dx, -curr_dy))
            
            angle_change = abs(curr_angle - prev_angle)
            if angle_change > 30:  # Significant change in torso orientation
                fall_score += 1
                detection_reasons.append(f"Body orientation change: {angle_change:.1f} degrees")
        
        # Criterion 4: Check for sudden increase in body width (falling sideways)
        if all(k in keypoints and k in prev_keypoints for k in ['LEFT_HIP', 'RIGHT_HIP']):
            prev_hip_width = abs(prev_keypoints['LEFT_HIP']['x'] - prev_keypoints['RIGHT_HIP']['x'])
            curr_hip_width = abs(keypoints['LEFT_HIP']['x'] - keypoints['RIGHT_HIP']['x'])
            
            width_change_ratio = curr_hip_width / max(prev_hip_width, 0.01)  # Avoid division by zero
            
            if width_change_ratio > 1.5 or width_change_ratio < 0.5:  # Significant change in width
                fall_score += 1
                detection_reasons.append(f"Body width change ratio: {width_change_ratio:.2f}")
        
        # Criterion 5: Check for floor proximity (head or hips close to bottom of frame)
        if 'NOSE' in keypoints and keypoints['NOSE']['y'] > 0.8:
            fall_score += 1
            detection_reasons.append(f"Head near bottom of frame: y={keypoints['NOSE']['y']:.2f}")
        
        # Determine if a fall is detected based on the score
        fall_detected = fall_score >= fall_threshold
        
        if fall_detected:
            reasons_str = ", ".join(detection_reasons)
            logger.warning(f"Fall detected! Score: {fall_score}/{fall_threshold}. Reasons: {reasons_str}")
        
        return fall_detected
    
    def interpolate_missing_keypoints(self, keypoints: Dict) -> Dict:
        """
        Interpolate missing keypoints based on biomechanical models and available keypoints.
        
        Args:
            keypoints: Dictionary of detected keypoints
            
        Returns:
            Dict: Updated keypoints with interpolated values for missing points
        """
        if not keypoints:
            return {}
        
        updated_keypoints = keypoints.copy()
        
        # Interpolate left ankle if missing but knee and foot index are available
        if ('LEFT_KNEE' in keypoints and 'LEFT_FOOT_INDEX' in keypoints and 
            ('LEFT_ANKLE' not in keypoints or keypoints['LEFT_ANKLE']['visibility'] < 0.3)):
            
            knee = np.array([keypoints['LEFT_KNEE']['x'], keypoints['LEFT_KNEE']['y']])
            foot = np.array([keypoints['LEFT_FOOT_INDEX']['x'], keypoints['LEFT_FOOT_INDEX']['y']])
            
            # Interpolate ankle position (70% from knee to foot)
            ankle_pos = knee + 0.7 * (foot - knee)
            
            updated_keypoints['LEFT_ANKLE'] = {
                'x': float(ankle_pos[0]),
                'y': float(ankle_pos[1]),
                'z': 0.0,  # Z-coordinate is less reliable for interpolation
                'visibility': 0.5,  # Medium confidence for interpolated point
                'interpolated': True
            }
        
        # Similar interpolation for right ankle
        if ('RIGHT_KNEE' in keypoints and 'RIGHT_FOOT_INDEX' in keypoints and 
            ('RIGHT_ANKLE' not in keypoints or keypoints['RIGHT_ANKLE']['visibility'] < 0.3)):
            
            knee = np.array([keypoints['RIGHT_KNEE']['x'], keypoints['RIGHT_KNEE']['y']])
            foot = np.array([keypoints['RIGHT_FOOT_INDEX']['x'], keypoints['RIGHT_FOOT_INDEX']['y']])
            
            ankle_pos = knee + 0.7 * (foot - knee)
            
            updated_keypoints['RIGHT_ANKLE'] = {
                'x': float(ankle_pos[0]),
                'y': float(ankle_pos[1]),
                'z': 0.0,
                'visibility': 0.5,
                'interpolated': True
            }
        
        return updated_keypoints
    
    def analyze_lighting_conditions(self, frame: np.ndarray) -> Dict:
        """
        Analyze lighting conditions in the frame.
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Dict containing lighting analysis results
        """
        if frame is None:
            return {'sufficient_lighting': False, 'brightness': 0}
        
        # Convert to grayscale for histogram analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # using COLOR_BGR2GRAY color space
        
        # Calculate histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]) # image, channel, mask, histSize, ranges
        
        # Calculate average brightness
        brightness = np.mean(gray)
        
        # Analyze histogram distribution
        hist_normalized = hist.flatten() / hist.sum() 
        dark_pixels_ratio = np.sum(hist_normalized[:50])  # Ratio of dark pixels
        bright_pixels_ratio = np.sum(hist_normalized[200:])  # Ratio of bright pixels
        
        # Determine if lighting is sufficient
        sufficient_lighting = brightness > 40 and dark_pixels_ratio < 0.5
        
        return {
            'sufficient_lighting': sufficient_lighting,
            'brightness': brightness,
            'dark_pixels_ratio': float(dark_pixels_ratio),
            'bright_pixels_ratio': float(bright_pixels_ratio)
        }
    
    def release(self) -> None:
        """
        Release resources used by the pose estimator.
        """
        if hasattr(self, 'pose') and self.pose:
            self.pose.close()
        logger.info("Pose estimator resources released")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()