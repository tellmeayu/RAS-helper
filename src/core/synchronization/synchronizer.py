#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gait-Music Synchronization

This module implements a user-controlled synchronization system between gait parameters
and music playback. All gait data must be confirmed by the user before being used to
control music tempo.
"""

import logging
import time
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum, auto

from ..gait_analysis import GaitAnalyzer
from ..music_processing import MusicProcessor
from ..session_management.ras_protocol import RASProtocol, RASPhase

logger = logging.getLogger(__name__)


class SyncState(Enum):
    """State of synchronization between gait and music."""
    IDLE = auto()            # No synchronization active
    WAITING_CONFIRMATION = auto()  # Waiting for user confirmation
    SYNCHRONIZING = auto()   # Music is playing with confirmed tempo
    PAUSED = auto()          # Synchronization paused
    ERROR = auto()           # Error state


@dataclass
class GaitData:
    """Container for gait analysis data."""
    cadence: float           # Steps per minute
    stride_length: float     # Meters
    velocity: float          # Meters per second
    timestamp: float         # Time of measurement
    confidence: float        # Confidence score (0-1)


class GaitMusicSynchronizer:
    """
    Implements user-controlled synchronization between gait and music.
    
    This class manages the process of:
    1. Receiving gait data from the gait analyzer
    2. Presenting the data to the user for confirmation/modification
    3. Applying confirmed tempo to music playback
    """
    
    def __init__(self,
                 min_cadence: float = 40.0,
                 max_cadence: float = 180.0,
                 update_interval: float = 0.5,
                 gait_analyzer: Optional[GaitAnalyzer] = None,
                 music_processor: Optional[MusicProcessor] = None):
        """
        Initialize the gait-music synchronizer.
        
        Args:
            min_cadence: Minimum allowed cadence in steps per minute
            max_cadence: Maximum allowed cadence in steps per minute
            update_interval: Time between gait data updates in seconds
            gait_analyzer: Optional existing GaitAnalyzer instance
            music_processor: Optional existing MusicProcessor instance
        """
        # Configuration
        self.min_cadence = min_cadence
        self.max_cadence = max_cadence
        self.update_interval = update_interval
        
        # State variables
        self.sync_state = SyncState.IDLE
        self.current_tempo = None
        self.is_playing = False
        self.last_update_time = time.time()
        
        # Data storage
        self.pending_gait_data = None
        self.confirmed_gait_data = None
        self.modified_cadence = None
        
        # External components
        self.gait_analyzer = gait_analyzer if gait_analyzer else GaitAnalyzer()
        self.music_processor = music_processor if music_processor else MusicProcessor()
        
        # Callbacks
        self.on_tempo_change = None
        self.on_gait_data_available = None
        self.on_sync_state_change = None
        
        # Protocol for session tracking
        self.protocol = RASProtocol(
            min_cadence=min_cadence,
            max_cadence=max_cadence
        )
        
        logger.info("GaitMusicSynchronizer initialized")
    
    def update_gait_data(self, gait_parameters: Dict[str, Any]) -> None:
        """
        Update with new gait data and notify user for confirmation.
        
        Args:
            gait_parameters: Current gait parameters from analyzer
        """
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return
            
        self.last_update_time = current_time
        
        # Create gait data object
        self.pending_gait_data = GaitData(
            cadence=gait_parameters.get('cadence', 0.0),
            stride_length=gait_parameters.get('stride_length', 0.0),
            velocity=gait_parameters.get('velocity', 0.0),
            timestamp=current_time,
            confidence=gait_parameters.get('confidence', 1.0)
        )
        
        # Notify that new data is available
        if self.on_gait_data_available:
            self.on_gait_data_available(self.pending_gait_data)
            
        # Update state
        self.sync_state = SyncState.WAITING_CONFIRMATION
        if self.on_sync_state_change:
            self.on_sync_state_change(self.sync_state)
    
    def get_current_gait_data(self) -> Optional[Dict[str, Any]]:
        """
        Request current gait data from the gait analyzer.
        
        Returns:
            Dictionary with current gait parameters or None if not available
        """
        try:
            gait_data = self.gait_analyzer.get_current_gait_parameters()
            if gait_data:
                self.update_gait_data(gait_data)
                return gait_data
            return None
        except Exception as e:
            logger.error(f"Error getting gait data: {str(e)}")
            return None
    
    def confirm_gait_data(self, modified_cadence: Optional[float] = None) -> bool:
        """
        Confirm the use of current gait data, optionally with modifications.
        
        Args:
            modified_cadence: Optional modified cadence value
            
        Returns:
            True if confirmation successful, False otherwise
        """
        if not self.pending_gait_data:
            logger.warning("No pending gait data to confirm")
            return False
            
        # Use modified cadence if provided
        if modified_cadence is not None:
            if not (self.min_cadence <= modified_cadence <= self.max_cadence):
                logger.warning(f"Modified cadence {modified_cadence} outside allowed range")
                return False
            self.modified_cadence = modified_cadence
        else:
            self.modified_cadence = self.pending_gait_data.cadence
            
        # Store confirmed data
        self.confirmed_gait_data = self.pending_gait_data
        self.pending_gait_data = None
        
        # Update music tempo
        self._update_music_tempo(self.modified_cadence)
        
        # Update state
        self.sync_state = SyncState.SYNCHRONIZING
        if self.on_sync_state_change:
            self.on_sync_state_change(self.sync_state)
            
        return True
    
    def adjust_tempo_percentage(self, percentage: float) -> bool:
        """
        Adjust the current tempo by a percentage.
        
        Args:
            percentage: Percentage change (-100 to 100)
            
        Returns:
            True if adjustment successful, False otherwise
        """
        if not self.confirmed_gait_data:
            logger.warning("No confirmed gait data available")
            return False
            
        if self.modified_cadence is None:
            logger.warning("No modified cadence available")
            return False
            
        new_cadence = self.modified_cadence * (1 + percentage/100)
        if not (self.min_cadence <= new_cadence <= self.max_cadence):
            logger.warning(f"Adjusted cadence {new_cadence} outside allowed range")
            return False
            
        self.modified_cadence = new_cadence
        self._update_music_tempo(new_cadence)
        return True
    
    def set_tempo_directly(self, tempo: float) -> bool:
        """
        Set tempo directly to a specific value.
        
        Args:
            tempo: Target tempo in BPM
            
        Returns:
            True if successful, False otherwise
        """
        if not (self.min_cadence <= tempo <= self.max_cadence):
            logger.warning(f"Tempo {tempo} outside allowed range")
            return False
            
        # Convert float tempo to integer for MIDI compatibility
        integer_tempo = int(round(tempo))
            
        # If we have confirmed data, treat as a modification
        if self.confirmed_gait_data:
            self.modified_cadence = integer_tempo
            self._update_music_tempo(integer_tempo)
        else:
            # Otherwise set tempo directly
            self.current_tempo = integer_tempo
            if self.on_tempo_change:
                self.on_tempo_change(integer_tempo)
                
        return True
    
    def _update_music_tempo(self, tempo: float) -> None:
        """
        Update the music tempo and notify listeners.
        
        Args:
            tempo: New tempo in BPM
        """
        # Convert float tempo to integer for MIDI compatibility
        integer_tempo = int(round(tempo))
        self.current_tempo = integer_tempo
        
        # Update music processor tempo if currently playing
        if self.is_playing:
            try:
                self.music_processor.set_tempo(integer_tempo)
            except Exception as e:
                logger.error(f"Error updating music tempo: {str(e)}")
        
        # Notify listeners
        if self.on_tempo_change:
            self.on_tempo_change(integer_tempo)
            
        # Record in protocol if we have confirmed data
        if self.confirmed_gait_data:
            self.protocol.add_therapist_note(
                f"Tempo set to {integer_tempo} BPM (modified from {self.confirmed_gait_data.cadence:.1f})"
            )
    
    def start_playback(self, midi_file: str) -> bool:
        """
        Start music playback with current tempo.
        
        Args:
            midi_file: Path to MIDI file
            
        Returns:
            True if playback started successfully
        """
        if not self.current_tempo:
            logger.warning("No tempo set for playback")
            return False
            
        try:
            # Load and start MIDI playback
            success = self.music_processor.load_midi(midi_file)
            if not success:
                logger.error(f"Failed to load MIDI file: {midi_file}")
                self.sync_state = SyncState.ERROR
                if self.on_sync_state_change:
                    self.on_sync_state_change(self.sync_state)
                return False
                
            self.music_processor.set_tempo(self.current_tempo)
            self.music_processor.play()
            self.is_playing = True
            logger.info(f"Started playback with tempo {self.current_tempo} BPM")
            return True
        except Exception as e:
            logger.error(f"Error starting playback: {str(e)}")
            self.sync_state = SyncState.ERROR
            if self.on_sync_state_change:
                self.on_sync_state_change(self.sync_state)
            return False
    
    def stop_playback(self) -> None:
        """Stop music playback."""
        if self.is_playing:
            try:
                self.music_processor.stop()
                self.is_playing = False
                logger.info("Playback stopped")
            except Exception as e:
                logger.error(f"Error stopping playback: {str(e)}")
    
    def pause_playback(self) -> None:
        """Pause music playback."""
        if self.is_playing:
            try:
                self.music_processor.pause()
                self.sync_state = SyncState.PAUSED
                if self.on_sync_state_change:
                    self.on_sync_state_change(self.sync_state)
                logger.info("Playback paused")
            except Exception as e:
                logger.error(f"Error pausing playback: {str(e)}")
    
    def resume_playback(self) -> None:
        """Resume music playback."""
        if self.sync_state == SyncState.PAUSED:
            try:
                self.music_processor.resume()
                self.sync_state = SyncState.SYNCHRONIZING
                if self.on_sync_state_change:
                    self.on_sync_state_change(self.sync_state)
                logger.info("Playback resumed")
            except Exception as e:
                logger.error(f"Error resuming playback: {str(e)}")
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get the current synchronization state.
        
        Returns:
            Dictionary containing current state
        """
        return {
            'sync_state': self.sync_state.name,
            'current_tempo': self.current_tempo,
            'is_playing': self.is_playing,
            'pending_gait_data': self.pending_gait_data.__dict__ if self.pending_gait_data else None,
            'confirmed_gait_data': self.confirmed_gait_data.__dict__ if self.confirmed_gait_data else None,
            'modified_cadence': self.modified_cadence,
            'session_notes': self.protocol.therapist_notes
        } 