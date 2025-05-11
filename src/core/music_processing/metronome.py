#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metronome Module

This module provides metronome functionality for rhythmic auditory stimulation.
"""

import time
import threading
from typing import Callable, List, Optional, Tuple

import numpy as np


class Metronome:
    """
    Class implementing a flexible metronome for rhythmic stimulation.
    
    This class provides accurate timing for generating metronome clicks
    with configurable tempo, meter, and accents.
    """
    
    def __init__(self, 
                 tempo: float = 120.0,
                 meter: Tuple[int, int] = (4, 4),
                 accent_pattern: Optional[List[bool]] = None,
                 use_accents: bool = True):
        """
        Initialize the metronome.
        
        Args:
            tempo: Initial tempo in beats per minute (BPM)
            meter: Time signature as tuple (numerator, denominator)
            accent_pattern: Optional custom accent pattern (list of booleans)
            use_accents: Whether to use accented beats (first beat emphasis)
        """
        self.tempo = tempo
        self.meter = meter
        self.beat_duration = 60.0 / tempo  # in seconds
        self.use_accents = use_accents
        
        # Set accent pattern (default: accent on first beat)
        if accent_pattern is None:
            self.accent_pattern = [True] + [False] * (meter[0] - 1)
        else:
            self.accent_pattern = accent_pattern
            
        # Runtime variables
        self.is_running = False
        self.thread = None
        self.last_beat_time = 0.0
        self.current_beat = 0
        self.beat_callback = None
        self.start_time = 0.0
        self._stop_event = threading.Event()
        
    def start(self, callback: Optional[Callable[[int, bool], None]] = None) -> None:
        """
        Start the metronome.
        
        Args:
            callback: Optional callback function(beat_index, is_accented)
        """
        if self.is_running:
            return
            
        self.beat_callback = callback
        self.is_running = True
        self._stop_event.clear()
        self.start_time = time.time()
        self.last_beat_time = self.start_time
        self.current_beat = 0
        
        # Start the metronome thread
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self) -> None:
        """Stop the metronome."""
        if not self.is_running:
            return
            
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=0.5)
        self.is_running = False
        
    def set_tempo(self, tempo: float) -> None:
        """
        Set a new tempo.
        
        Args:
            tempo: New tempo in BPM (should be an integer for MIDI compatibility)
        """
        if tempo <= 0:
            raise ValueError("Tempo must be positive")
            
        # Ensure tempo is an integer for MIDI compatibility
        if not isinstance(tempo, int):
            print(f"Warning: Tempo {tempo} is not an integer. Converting to integer for MIDI compatibility.")
            tempo = int(round(tempo))
            
        self.tempo = tempo
        self.beat_duration = 60.0 / tempo
        
    def set_meter(self, meter: Tuple[int, int], 
                 accent_pattern: Optional[List[bool]] = None) -> None:
        """
        Set a new meter and optional accent pattern.
        
        Args:
            meter: Time signature as tuple (numerator, denominator)
            accent_pattern: Optional custom accent pattern
        """
        self.meter = meter
        
        if accent_pattern is None:
            self.accent_pattern = [True] + [False] * (meter[0] - 1)
        else:
            # Ensure accent pattern matches meter
            if len(accent_pattern) != meter[0]:
                raise ValueError(
                    f"Accent pattern length ({len(accent_pattern)}) "
                    f"must match meter numerator ({meter[0]})"
                )
            self.accent_pattern = accent_pattern
            
    def toggle_accents(self, use_accents: bool) -> None:
        """
        Enable or disable accented beats.
        
        Args:
            use_accents: Whether to use accented beats (True) or use uniform beats (False)
        """
        self.use_accents = use_accents
        
    def _run(self) -> None:
        """Internal method to run the metronome loop."""
        while not self._stop_event.is_set():
            current_time = time.time()
            elapsed = current_time - self.start_time
            
            # Calculate expected beat time
            expected_beats = elapsed / self.beat_duration
            next_beat = int(expected_beats) + 1
            
            if next_beat > self.current_beat:
                # New beat should trigger
                beat_in_bar = next_beat % self.meter[0]
                
                # Determine if this beat should be accented
                is_accented = False
                if self.use_accents:
                    is_accented = self.accent_pattern[beat_in_bar]
                
                if self.beat_callback:
                    self.beat_callback(beat_in_bar, is_accented)
                    
                self.current_beat = next_beat
                self.last_beat_time = current_time
                
            # Calculate sleep time until next beat
            next_beat_time = self.start_time + next_beat * self.beat_duration
            sleep_time = next_beat_time - time.time()
            
            # Sleep until just before next beat
            # Use shorter sleep times for better accuracy
            if sleep_time > 0:
                # Sleep in shorter chunks to improve responsiveness to stop requests
                chunk_time = min(0.01, sleep_time / 2)
                time.sleep(chunk_time)
            else:
                # In case we're behind, yield to avoid CPU hogging
                time.sleep(0.001)
                
    def get_beat_times(self, duration: float) -> List[Tuple[float, bool]]:
        """
        Calculate expected beat times for a given duration.
        
        Args:
            duration: Duration in seconds
            
        Returns:
            List of tuples (time_offset, is_accented)
        """
        beat_times = []
        beats_per_bar = self.meter[0]
        
        # Calculate number of beats in the duration
        num_beats = int(duration / self.beat_duration) + 1
        
        for i in range(num_beats):
            time_offset = i * self.beat_duration
            if time_offset <= duration:
                beat_in_bar = i % beats_per_bar
                is_accented = self.accent_pattern[beat_in_bar]
                beat_times.append((time_offset, is_accented))
                
        return beat_times
    
    def get_bar_duration(self) -> float:
        """
        Calculate the duration of one complete bar.
        
        Returns:
            Duration of one bar in seconds
        """
        return self.beat_duration * self.meter[0]