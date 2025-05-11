#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIDI Parser

This module handles MIDI file parsing and manipulation.
"""

import os
import time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import mido
import numpy as np


class MidiEventType(Enum):
    """Enumeration of MIDI event types relevant for rhythm extraction."""
    NOTE_ON = 0
    NOTE_OFF = 1
    TEMPO_CHANGE = 2
    TIME_SIGNATURE = 3
    KEY_SIGNATURE = 4
    OTHER = 5


class MidiEvent:
    """Class representing a MIDI event with timing information."""
    
    def __init__(self, 
                 event_type: MidiEventType, 
                 time: float, 
                 tick: int,
                 message: mido.Message):
        """
        Initialize a MIDI event.
        
        Args:
            event_type: Type of the MIDI event
            time: Absolute time in seconds
            tick: MIDI tick position
            message: Original MIDI message
        """
        self.event_type = event_type
        self.time = time
        self.tick = tick
        self.message = message
        
    def __repr__(self) -> str:
        """String representation of the MIDI event."""
        return f"MidiEvent({self.event_type}, time={self.time:.3f}, tick={self.tick})"


class MidiParser:
    """
    Class for parsing and manipulating MIDI files.
    
    This class handles MIDI file loading, parsing, and extraction of rhythmic elements
    for auditory stimulation purposes.
    """
    
    def __init__(self):
        """Initialize the MIDI parser."""
        self.midi_file = None
        self.events = []
        self.tempo_changes = []
        self.time_signatures = []
        self.beat_positions = []
        self.midi_length = 0.0
        self.current_tempo = 120.0  # Default tempo (BPM)
        self.current_ppq = 480      # Default pulses per quarter note
        self.current_time_signature = (4, 4)  # Default time signature
        self.tracks = []            # Initialize tracks list
        
    def load_file(self, file_path: Union[str, Path]) -> bool:
        """
        Load a MIDI file for processing.
        
        Args:
            file_path: Path to the MIDI file
            
        Returns:
            True if the file was loaded successfully, False otherwise
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"MIDI file not found: {file_path}")
                
            self.midi_file = mido.MidiFile(str(file_path))
            self.current_ppq = self.midi_file.ticks_per_beat
            self._parse_midi()
            return True
            
        except Exception as e:
            print(f"Error loading MIDI file: {e}")
            return False
            
    def _parse_midi(self) -> None:
        """
        Parse the MIDI file and extract events, tempo changes, and beat positions.
        """
        if not self.midi_file:
            return
            
        self.events = []
        self.tempo_changes = []
        self.time_signatures = []
        self.tracks = []            # Reset tracks list
        
        # Store all tracks for reference
        if hasattr(self.midi_file, 'tracks'):
            self.tracks = self.midi_file.tracks
        
        # Parse all tracks
        absolute_time = 0.0
        cumulative_ticks = 0
        current_tempo_us = mido.tempo2bpm(500000)  # Default tempo in microseconds per beat
        
        for track in self.midi_file.tracks:
            track_absolute_time = 0.0
            track_cumulative_ticks = 0
            
            for msg in track:
                # Convert delta time to seconds
                delta_seconds = mido.tick2second(msg.time, self.current_ppq, current_tempo_us)
                track_absolute_time += delta_seconds
                track_cumulative_ticks += msg.time
                
                # Process message based on type
                if msg.type == 'note_on' and msg.velocity > 0:
                    event_type = MidiEventType.NOTE_ON
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    event_type = MidiEventType.NOTE_OFF
                elif msg.type == 'set_tempo':
                    event_type = MidiEventType.TEMPO_CHANGE
                    current_tempo_us = msg.tempo
                    self.tempo_changes.append((track_absolute_time, mido.tempo2bpm(msg.tempo)))
                elif msg.type == 'time_signature':
                    event_type = MidiEventType.TIME_SIGNATURE
                    self.time_signatures.append((
                        track_absolute_time, 
                        (msg.numerator, msg.denominator)
                    ))
                    self.current_time_signature = (msg.numerator, msg.denominator)
                elif msg.type == 'key_signature':
                    event_type = MidiEventType.KEY_SIGNATURE
                else:
                    event_type = MidiEventType.OTHER
                    
                # Create and store the event
                event = MidiEvent(
                    event_type=event_type,
                    time=track_absolute_time,
                    tick=track_cumulative_ticks,
                    message=msg
                )
                self.events.append(event)
        
        # Sort events by absolute time
        self.events.sort(key=lambda e: e.time)
        
        # Calculate MIDI file length
        if self.events:
            self.midi_length = self.events[-1].time
        else:
            self.midi_length = 0.0
            
        # Update current tempo
        if self.tempo_changes:
            self.current_tempo = self.tempo_changes[0][1]
        
        # Extract beat positions
        self._extract_beat_positions()
            
    def _extract_beat_positions(self) -> None:
        """
        Extract beat positions from the MIDI file.
        """
        self.beat_positions = []
        
        if not self.midi_file or not self.events:
            return
            
        # Find initial tempo and time signature
        tempo = 120.0  # Default tempo in BPM
        time_sig = (4, 4)  # Default time signature
        
        if self.tempo_changes:
            tempo = self.tempo_changes[0][1]
            
        if self.time_signatures:
            time_sig = self.time_signatures[0][1]
            
        # Calculate beat duration
        beat_duration = 60.0 / tempo  # in seconds
        
        # Generate beat positions
        current_time = 0.0
        beats_per_bar = time_sig[0]
        
        while current_time <= self.midi_length:
            for beat in range(beats_per_bar):
                beat_time = current_time + beat * beat_duration
                if beat_time <= self.midi_length:
                    # Add tuple (time, beat_in_bar, is_downbeat)
                    is_downbeat = (beat == 0)
                    self.beat_positions.append((beat_time, beat, is_downbeat))
            
            current_time += beats_per_bar * beat_duration
            
            # Check for tempo changes
            for change_time, new_tempo in self.tempo_changes:
                if change_time <= current_time and change_time > (current_time - beats_per_bar * beat_duration):
                    # Recalculate beat duration after this point
                    tempo = new_tempo
                    beat_duration = 60.0 / tempo
                    break
                    
            # Check for time signature changes
            for sig_time, new_sig in self.time_signatures:
                if sig_time <= current_time and sig_time > (current_time - beats_per_bar * beat_duration):
                    time_sig = new_sig
                    beats_per_bar = time_sig[0]
                    break
    
    def adjust_tempo(self, new_tempo: float) -> None:
        """
        Adjust the tempo of the MIDI file.
        
        Args:
            new_tempo: New tempo in beats per minute (BPM) (should be an integer for MIDI compatibility)
        """
        if not self.midi_file or not self.events:
            return
            
        if new_tempo <= 0:
            raise ValueError("Tempo must be positive")
            
        # Ensure tempo is an integer for MIDI compatibility
        if not isinstance(new_tempo, int):
            print(f"Warning: Tempo {new_tempo} is not an integer. Converting to integer for MIDI compatibility.")
            new_tempo = int(round(new_tempo))
            
        # Calculate tempo ratio
        tempo_ratio = new_tempo / self.current_tempo
        
        # Update timing of all events
        for event in self.events:
            event.time /= tempo_ratio
            
        # Update tempo changes
        self.tempo_changes = [(t / tempo_ratio, tempo * tempo_ratio) 
                             for t, tempo in self.tempo_changes]
            
        # Update beat positions
        self._extract_beat_positions()
        
        # Update current tempo
        self.current_tempo = new_tempo
        
    def get_beat_times(self, start_time: float = 0.0, end_time: Optional[float] = None) -> List[Tuple[float, bool]]:
        """
        Get beat timestamps within the specified time range.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds, or None for all beats
            
        Returns:
            List of tuples (time, is_downbeat)
        """
        if not end_time:
            end_time = self.midi_length
            
        return [(time, is_downbeat) 
                for time, _, is_downbeat in self.beat_positions 
                if start_time <= time <= end_time]
    
    def get_midi_data(self) -> Dict:
        """
        Get MIDI file metadata.
        
        Returns:
            Dictionary containing MIDI metadata
        """
        return {
            'tempo': self.current_tempo,
            'time_signature': self.current_time_signature,
            'length': self.midi_length,
            'ticks_per_beat': self.current_ppq,
            'beat_count': len(self.beat_positions),
            'tempo_changes': len(self.tempo_changes),
            'track_count': len(self.tracks),
            'file_name': os.path.basename(self.midi_file.filename) if self.midi_file else None
        }