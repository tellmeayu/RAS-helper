#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synchronization Data Collection

This module implements data collection and storage for therapeutic evaluation
of rhythmic auditory stimulation sessions.
"""

import csv
import json
import logging
import os
import time
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, TypedDict, cast

import numpy as np

from ..session_management.ras_protocol import RASPhase

logger = logging.getLogger(__name__)


class TimestampDict(TypedDict):
    """Type definition for timestamp data."""
    timestamp: float
    elapsed_time: float


class GaitRecordDict(TimestampDict):
    """Type definition for gait data records."""
    cadence: Optional[float]
    stride_length: Optional[float]
    walking_speed: Optional[float]
    is_walking: bool


class SyncRecordDict(TimestampDict):
    """Type definition for synchronization data records."""
    sync_state: Optional[str]
    protocol_phase: Optional[str]
    current_tempo: Optional[float]
    target_tempo: Optional[float]
    current_cadence: Optional[float]
    therapist_override: bool


class SynchronizationData:
    """
    Stores and manages synchronization data for therapeutic evaluation.
    
    This class records gait parameters, synchronization metrics, and protocol
    information during RAS sessions for later analysis and evaluation.
    """
    
    def __init__(self, 
                 session_id: Optional[str] = None,
                 patient_id: Optional[str] = None,
                 data_dir: str = "data/sessions",
                 sampling_rate: float = 2.0):
        """
        Initialize synchronization data collection.
        
        Args:
            session_id: Unique identifier for the session (generated if None)
            patient_id: Patient identifier
            data_dir: Directory for storing session data
            sampling_rate: Number of data points to collect per second
        """
        # Session identification
        self.session_id = session_id or f"session_{int(time.time())}"
        self.patient_id = patient_id
        self.start_time = time.time()
        self.session_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Storage settings
        self.data_dir = data_dir
        self.sampling_rate = sampling_rate
        self.sampling_interval = 1.0 / sampling_rate
        
        # Data collection
        self.last_sample_time = 0
        self.gait_data: List[GaitRecordDict] = []
        self.sync_data: List[SyncRecordDict] = []
        self.events: List[Dict[str, Any]] = []
        self.phase_history: List[Dict[str, Any]] = []
        
        # Session metadata
        self.metadata = {
            "session_id": self.session_id,
            "patient_id": self.patient_id,
            "session_date": self.session_date,
            "sampling_rate": self.sampling_rate,
            "session_duration": 0.0,
            "protocol_phases": [],
            "baseline_metrics": {},
            "outcome_metrics": {}
        }
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Initialized data collection for session {self.session_id}")
    
    def update(self, 
              gait_parameters: Dict[str, Any], 
              sync_state: Dict[str, Any]) -> None:
        """
        Update data collection with current parameters and state.
        
        Args:
            gait_parameters: Current gait parameters from analysis
            sync_state: Current synchronization state
        """
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        # Only record at specified sampling rate
        if current_time - self.last_sample_time < self.sampling_interval:
            return
            
        self.last_sample_time = current_time
        
        # Extract and record relevant data
        timestamp: TimestampDict = {
            "timestamp": current_time,
            "elapsed_time": elapsed_time
        }
        
        # Record gait data
        gait_record: GaitRecordDict = cast(GaitRecordDict, timestamp.copy())
        gait_record.update({
            "cadence": gait_parameters.get("cadence"),
            "stride_length": gait_parameters.get("stride_length"),
            "walking_speed": gait_parameters.get("walking_speed"),
            "is_walking": gait_parameters.get("is_walking", False)
        })
        self.gait_data.append(gait_record)
        
        # Record synchronization data
        sync_record: SyncRecordDict = cast(SyncRecordDict, timestamp.copy())
        sync_record.update({
            "sync_state": sync_state.get("sync_state"),
            "protocol_phase": sync_state.get("protocol_phase"),
            "current_tempo": sync_state.get("current_tempo"),
            "target_tempo": sync_state.get("target_tempo"),
            "current_cadence": sync_state.get("current_cadence"),
            "therapist_override": sync_state.get("therapist_override", False)
        })
        self.sync_data.append(sync_record)
        
        # Update metadata
        self.metadata["session_duration"] = elapsed_time
        
        # Record phase changes
        current_phase = sync_state.get("protocol_phase")
        if current_phase and (not self.phase_history or self.phase_history[-1]["phase"] != current_phase):
            phase_record = {
                "phase": current_phase,
                "timestamp": current_time,
                "elapsed_time": elapsed_time
            }
            self.phase_history.append(phase_record)
            
            # Update protocol phases in metadata
            if current_phase not in self.metadata["protocol_phases"]:
                self.metadata["protocol_phases"].append(current_phase)
    
    def add_event(self, event_type: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a timestamped event to the session record.
        
        Args:
            event_type: Type of event (e.g., "calibration_start", "playback_start")
            details: Additional details about the event
        """
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        event = {
            "event_type": event_type,
            "timestamp": current_time,
            "elapsed_time": elapsed_time,
            "details": details or {}
        }
        
        self.events.append(event)
        logger.info(f"Recorded event: {event_type}")
    
    def set_baseline_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Set baseline gait metrics from initial assessment.
        
        Args:
            metrics: Dictionary of baseline metrics
        """
        self.metadata["baseline_metrics"] = metrics
        logger.info("Recorded baseline metrics")
    
    def set_outcome_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Set outcome metrics from final assessment.
        
        Args:
            metrics: Dictionary of outcome metrics
        """
        self.metadata["outcome_metrics"] = metrics
        logger.info("Recorded outcome metrics")
    
    def save_session_data(self) -> str:
        """
        Save all session data to files.
        
        Returns:
            Path to the session directory
        """
        # Create session directory
        session_dir = os.path.join(self.data_dir, self.session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # Save metadata
        self.metadata["session_duration"] = time.time() - self.start_time
        with open(os.path.join(session_dir, "metadata.json"), "w") as f:
            json.dump(self.metadata, f, indent=2)
            
        # Save gait data
        self._save_data_to_csv(self.gait_data, os.path.join(session_dir, "gait_data.csv"))
        
        # Save synchronization data
        self._save_data_to_csv(self.sync_data, os.path.join(session_dir, "sync_data.csv"))
        
        # Save events
        with open(os.path.join(session_dir, "events.json"), "w") as f:
            json.dump(self.events, f, indent=2)
        
        # Save phase history
        with open(os.path.join(session_dir, "phase_history.json"), "w") as f:
            json.dump(self.phase_history, f, indent=2)
            
        logger.info(f"Saved session data to {session_dir}")
        return session_dir
    
    def _save_data_to_csv(self, data: List[Dict[str, Any]], filepath: str) -> None:
        """
        Save list of dictionaries to CSV file.
        
        Args:
            data: List of data records (dictionaries)
            filepath: Path to save the CSV file
        """
        if not data:
            logger.warning(f"No data to save to {filepath}")
            return
            
        # Get all unique keys from the data
        fieldnames = set()
        for record in data:
            fieldnames.update(record.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    
    def compute_summary_metrics(self) -> Dict[str, Any]:
        """
        Compute summary metrics for the session.
        
        Returns:
            Dictionary of summary metrics
        """
        if not self.sync_data:
            return {}
            
        # Extract data for analysis
        cadences = [d.get("current_cadence", 0.0) for d in self.gait_data 
                   if d.get("current_cadence") is not None]
        tempos = [d.get("current_tempo", 0.0) for d in self.sync_data 
                 if d.get("current_tempo") is not None]
        
        # Safety check for empty lists
        if not cadences or not tempos:
            return {
                "session_duration": self.metadata["session_duration"],
                "data_points": len(self.sync_data)
            }
        
        # Calculate key metrics
        cadence_variability = np.std(cadences) if len(cadences) > 1 else 0.0
        tempo_variability = np.std(tempos) if len(tempos) > 1 else 0.0
        
        # Phase durations
        phase_durations = {}
        for i, phase_record in enumerate(self.phase_history):
            phase = phase_record["phase"]
            start_time = phase_record["elapsed_time"]
            
            # Calculate end time
            if i < len(self.phase_history) - 1:
                end_time = self.phase_history[i+1]["elapsed_time"]
            else:
                end_time = self.metadata["session_duration"]
                
            duration = end_time - start_time
            phase_durations[phase] = duration
        
        # Compute baseline vs current differences if available
        baseline_cadence = self.metadata.get("baseline_metrics", {}).get("cadence")
        final_cadence = cadences[-1] if cadences else None
        cadence_change = None
        if baseline_cadence is not None and final_cadence is not None:
            cadence_change = final_cadence - baseline_cadence
        
        return {
            "session_duration": self.metadata["session_duration"],
            "data_points": len(self.sync_data),
            "cadence_variability": cadence_variability,
            "tempo_variability": tempo_variability,
            "phase_durations": phase_durations,
            "baseline_cadence": baseline_cadence,
            "final_cadence": final_cadence,
            "cadence_change": cadence_change
        }


class SessionAnalyzer:
    """
    Analyzes RAS session data for therapeutic evaluation.
    
    This class provides methods to analyze and visualize data from 
    rhythmic auditory stimulation sessions.
    """
    
    def __init__(self, data_dir: str = "data/sessions"):
        """
        Initialize session analyzer.
        
        Args:
            data_dir: Directory containing session data
        """
        self.data_dir = data_dir
        
    def load_session(self, session_id: str) -> Dict[str, Any]:
        """
        Load session data for analysis.
        
        Args:
            session_id: Identifier for the session to load
            
        Returns:
            Dictionary containing loaded session data
        """
        session_dir = os.path.join(self.data_dir, session_id)
        
        # Check if session exists
        if not os.path.exists(session_dir):
            logger.error(f"Session directory not found: {session_dir}")
            return {}
            
        # Load metadata
        try:
            with open(os.path.join(session_dir, "metadata.json"), "r") as f:
                metadata = json.load(f)
        except Exception as e:
            logger.error(f"Error loading metadata: {str(e)}")
            metadata = {}
            
        # Load CSV data
        try:
            gait_data = self._load_csv(os.path.join(session_dir, "gait_data.csv"))
            sync_data = self._load_csv(os.path.join(session_dir, "sync_data.csv"))
        except Exception as e:
            logger.error(f"Error loading CSV data: {str(e)}")
            gait_data = []
            sync_data = []
            
        # Load events
        try:
            with open(os.path.join(session_dir, "events.json"), "r") as f:
                events = json.load(f)
        except Exception as e:
            logger.error(f"Error loading events: {str(e)}")
            events = []
            
        # Load phase history
        try:
            with open(os.path.join(session_dir, "phase_history.json"), "r") as f:
                phase_history = json.load(f)
        except Exception as e:
            logger.error(f"Error loading phase history: {str(e)}")
            phase_history = []
        
        return {
            "metadata": metadata,
            "gait_data": gait_data,
            "sync_data": sync_data,
            "events": events,
            "phase_history": phase_history
        }
    
    def _load_csv(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Load CSV file into list of dictionaries.
        
        Args:
            filepath: Path to the CSV file
            
        Returns:
            List of data records
        """
        if not os.path.exists(filepath):
            return []
            
        records = []
        with open(filepath, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric strings to appropriate types
                processed_row = {}
                for key, value in row.items():
                    if value == "":
                        processed_row[key] = None
                    elif value == "True":
                        processed_row[key] = True
                    elif value == "False":
                        processed_row[key] = False
                    else:
                        try:
                            # Try to convert to float
                            processed_row[key] = float(value)
                        except ValueError:
                            # Keep as string
                            processed_row[key] = value
                records.append(processed_row)
        return records
    
    def list_sessions(self) -> List[str]:
        """
        List available session IDs.
        
        Returns:
            List of session IDs
        """
        if not os.path.exists(self.data_dir):
            return []
            
        # Get subdirectories (session IDs)
        return [d for d in os.listdir(self.data_dir) 
                if os.path.isdir(os.path.join(self.data_dir, d))]
    
    def analyze_session(self, session_id: str) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a session.
        
        Args:
            session_id: Identifier for the session to analyze
            
        Returns:
            Dictionary with analysis results
        """
        # Load session data
        session_data = self.load_session(session_id)
        if not session_data:
            return {}
            
        # Extract relevant data
        metadata = session_data.get("metadata", {})
        gait_data = session_data.get("gait_data", [])
        sync_data = session_data.get("sync_data", [])
        
        # Basic validation
        if not gait_data or not sync_data:
            logger.warning(f"Insufficient data for session analysis: {session_id}")
            return {
                "session_id": session_id,
                "success": False,
                "error": "Insufficient data for analysis"
            }
        
        # Calculate phase metrics
        phase_metrics = self._analyze_phases(session_data)
        
        # Calculate gait parameter metrics
        gait_metrics = self._analyze_gait_parameters(session_data)
        
        # Combine all metrics
        analysis_results = {
            "session_id": session_id,
            "success": True,
            "session_date": metadata.get("session_date"),
            "patient_id": metadata.get("patient_id"),
            "session_duration": metadata.get("session_duration", 0.0),
            "phase_metrics": phase_metrics,
            "gait_metrics": gait_metrics
        }
        
        return analysis_results
        
    def _analyze_phases(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze effectiveness of different protocol phases.
        
        Args:
            session_data: Loaded session data
            
        Returns:
            Dictionary with phase analysis metrics
        """
        phase_history = session_data.get("phase_history", [])
        sync_data = session_data.get("sync_data", [])
        
        if not phase_history or not sync_data:
            return {}
            
        # Get elapsed times for all data points
        elapsed_times = [record.get("elapsed_time", 0) for record in sync_data]
        
        # Calculate phase time ranges
        phase_ranges = []
        for i, phase_record in enumerate(phase_history):
            phase = phase_record["phase"]
            start_time = phase_record["elapsed_time"]
            
            # Calculate end time
            if i < len(phase_history) - 1:
                end_time = phase_history[i+1]["elapsed_time"]
            else:
                # For the last phase, use the last data point time
                if elapsed_times:
                    end_time = elapsed_times[-1]
                else:
                    end_time = start_time
                    
            phase_ranges.append({
                "phase": phase,
                "start_time": start_time,
                "end_time": end_time
            })
        
        # Analyze metrics for each phase
        phase_metrics = {}
        for phase_range in phase_ranges:
            phase = phase_range["phase"]
            start_time = phase_range["start_time"]
            end_time = phase_range["end_time"]
            
            # Filter data for this phase
            phase_data = [record for record in sync_data 
                         if start_time <= record.get("elapsed_time", 0) <= end_time]
            
            if not phase_data:
                continue
                
            phase_metrics[phase] = {
                "duration": end_time - start_time,
                "data_points": len(phase_data)
            }
        
        return phase_metrics
        
    def _analyze_gait_parameters(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze changes in gait parameters during the session.
        
        Args:
            session_data: Loaded session data
            
        Returns:
            Dictionary with gait parameter analysis metrics
        """
        metadata = session_data.get("metadata", {})
        gait_data = session_data.get("gait_data", [])
        
        if not gait_data:
            return {}
            
        # Extract baseline values
        baseline_metrics = metadata.get("baseline_metrics", {})
        baseline_cadence = baseline_metrics.get("cadence")
        baseline_stride_length = baseline_metrics.get("stride_length")
        baseline_walking_speed = baseline_metrics.get("walking_speed")
        
        # Filter out invalid values
        filtered_cadences = [d.get("cadence") for d in gait_data if d.get("cadence") is not None]
        filtered_stride_lengths = [d.get("stride_length") for d in gait_data if d.get("stride_length") is not None]
        filtered_walking_speeds = [d.get("walking_speed") for d in gait_data if d.get("walking_speed") is not None]
        
        if not filtered_cadences:
            return {}
            
        # Calculate final values (average of last 10 samples)
        final_samples = min(10, len(filtered_cadences))
        final_cadence = np.mean(filtered_cadences[-final_samples:]) if filtered_cadences else None
        final_stride_length = np.mean(filtered_stride_lengths[-final_samples:]) if filtered_stride_lengths else None
        final_walking_speed = np.mean(filtered_walking_speeds[-final_samples:]) if filtered_walking_speeds else None
        
        # Calculate changes
        cadence_change = None
        if baseline_cadence is not None and final_cadence is not None:
            cadence_change = final_cadence - baseline_cadence
            
        stride_length_change = None
        if baseline_stride_length is not None and final_stride_length is not None:
            stride_length_change = final_stride_length - baseline_stride_length
            
        walking_speed_change = None
        if baseline_walking_speed is not None and final_walking_speed is not None:
            walking_speed_change = final_walking_speed - baseline_walking_speed
        
        # Calculate percent changes
        cadence_percent_change = None
        if baseline_cadence is not None and final_cadence is not None and baseline_cadence > 0:
            cadence_percent_change = (cadence_change / baseline_cadence) * 100
            
        stride_length_percent_change = None
        if baseline_stride_length is not None and final_stride_length is not None and baseline_stride_length > 0:
            stride_length_percent_change = (stride_length_change / baseline_stride_length) * 100
            
        walking_speed_percent_change = None
        if baseline_walking_speed is not None and final_walking_speed is not None and baseline_walking_speed > 0:
            walking_speed_percent_change = (walking_speed_change / baseline_walking_speed) * 100
        
        return {
            "baseline_cadence": baseline_cadence,
            "final_cadence": final_cadence,
            "cadence_change": cadence_change,
            "cadence_percent_change": cadence_percent_change,
            
            "baseline_stride_length": baseline_stride_length,
            "final_stride_length": final_stride_length,
            "stride_length_change": stride_length_change,
            "stride_length_percent_change": stride_length_percent_change,
            
            "baseline_walking_speed": baseline_walking_speed,
            "final_walking_speed": final_walking_speed,
            "walking_speed_change": walking_speed_change,
            "walking_speed_percent_change": walking_speed_percent_change,
            
            "cadence_variability": np.std(filtered_cadences) if len(filtered_cadences) > 1 else 0.0,
            "stride_length_variability": np.std(filtered_stride_lengths) if len(filtered_stride_lengths) > 1 else 0.0,
            "walking_speed_variability": np.std(filtered_walking_speeds) if len(filtered_walking_speeds) > 1 else 0.0
        } 