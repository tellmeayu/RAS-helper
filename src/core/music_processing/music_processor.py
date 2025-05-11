#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Music Processor Module

This module provides functionality for MIDI playback and tempo adjustment
for rhythmic auditory stimulation.
"""

import os
import time
import threading
import logging
import platform
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import fluidsynth
except ImportError:
    logging.warning("FluidSynth Python bindings not found. Audio playback will be unavailable.")
    fluidsynth = None

from .midi_parser import MidiParser, MidiEvent, MidiEventType
from .metronome import Metronome


class PlaybackState(Enum):
    """Enumeration of music playback states."""
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    METRONOME_INTRO = auto()


class MusicProcessor:
    """
    Class for processing and playing MIDI files with tempo adjustment.
    
    This class handles MIDI playback, tempo adjustment based on gait parameters,
    and provides metronome functionality for rhythmic auditory stimulation.
    """
    
    def __init__(self, 
                 soundfont_path: Optional[str] = None,
                 sample_rate: int = 44100,
                 midi_instrument: int = 115,  # Woodblock by default
                 metronome_enabled: bool = True,
                 gain: float = 0.7):
        """
        Initialize the music processor.
        
        Args:
            soundfont_path: Path to SoundFont file for FluidSynth
            sample_rate: Audio sample rate
            midi_instrument: MIDI instrument number for metronome
            metronome_enabled: Whether to enable metronome
            gain: Audio gain (volume) from 0.0 to 1.0
        """
        self.logger = logging.getLogger(__name__)
        
        # FluidSynth setup
        self.fs = None
        self.sfid = None
        self.midi_player = None
        self.soundfont_path = soundfont_path
        self.sample_rate = sample_rate
        self.midi_instrument = midi_instrument
        self.gain = gain
        
        # MIDI and metronome components
        self.midi_parser = MidiParser()
        # Initialize metronome with use_accents set to False for uniform beats
        self.metronome = Metronome(use_accents=False)
        self.metronome_enabled = metronome_enabled
        
        # Playback state
        self.playback_state = PlaybackState.STOPPED
        self.playback_thread = None
        self.current_position = 0.0
        self.start_time = 0.0
        self.pause_position = 0.0
        self.play_intro_bars = True  # Whether to play metronome intro
        self.intro_bars = 2  # Number of intro bars
        self._stop_event = threading.Event()
        
        # Beat timestamps (for synchronization)
        self.beat_timestamps = []
        self.beat_callback = None
        self.position_callback = None
        
        # Initialize FluidSynth if available
        self._init_fluidsynth()
        
    def _init_fluidsynth(self) -> bool:
        """
        Initialize FluidSynth for audio playback.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        if fluidsynth is None:
            self.logger.error("FluidSynth not available. Audio playback disabled.")
            return False
            
        try:
            self.fs = fluidsynth.Synth()
            self.fs.setting("synth.gain", self.gain)
            
            # Determine platform-specific audio driver
            system = platform.system()
            if system == 'Darwin':  # macOS
                audio_driver = 'coreaudio'
            elif system == 'Linux':
                audio_driver = 'pulseaudio'
            elif system == 'Windows':
                audio_driver = 'dsound'
            else:
                audio_driver = None  # Let FluidSynth choose
                
            self.logger.info(f"Using audio driver: {audio_driver if audio_driver else 'default'}")
            
            # Initialize audio driver
            if audio_driver:
                self.fs.start(driver=audio_driver)
            else:
                self.fs.start()
            
            # Load SoundFont if specified
            if self.soundfont_path:
                if not os.path.exists(self.soundfont_path):
                    self.logger.warning(f"SoundFont file not found: {self.soundfont_path}")
                    return False
                else:
                    self.sfid = self.fs.sfload(self.soundfont_path)
                    if self.sfid == -1:
                        self.logger.error("Failed to load SoundFont")
                        return False
                        
                    # Set up all channels with General MIDI programs
                    for channel in range(16):
                        if channel == 9:  # Percussion channel in GM
                            self.fs.program_select(channel, self.sfid, 128, 0)
                        else:
                            # Default to piano for melodic channels
                            self.fs.program_select(channel, self.sfid, 0, 0)
                    
                    # Use a separate channel for metronome to avoid conflicts
                    # Channel 15 is typically less used in standard MIDI files
                    metronome_channel = 15
                    self.fs.program_select(metronome_channel, self.sfid, 0, self.midi_instrument)
                    
                    self.logger.info(f"Loaded SoundFont: {self.soundfont_path}")
                    self.logger.info(f"Set up metronome on channel {metronome_channel}")
                    return True
            else:
                self.logger.warning("No SoundFont specified. Using default sounds.")
                # Set up a basic instrument without a SoundFont
                self.fs.program_select(0, 0, 0, self.midi_instrument)
                return True
                
        except Exception as e:
            self.logger.error(f"Error initializing FluidSynth: {e}")
            self.fs = None
            return False
            
    def load_midi(self, file_path: Union[str, Path]) -> bool:
        """
        Load a MIDI file for playback.
        
        Args:
            file_path: Path to the MIDI file
            
        Returns:
            True if the file was loaded successfully, False otherwise
        """
        try:
            success = self.midi_parser.load_file(file_path)
            if not success:
                return False
            
            # Get file info
            self.midi_file_path = Path(file_path)
            self.logger.info(f"Loaded MIDI file: {file_path}")
            
            # Get midi data
            tempo = self.midi_parser.current_tempo
            self.logger.info(f"Tempo: {tempo} BPM, Time Signature: {self.midi_parser.current_time_signature}")
            
            # Set metronome tempo
            self.metronome.set_tempo(tempo)
            
            # Get beat timestamps
            self.beat_timestamps = self.midi_parser.get_beat_times()
            
            # Process program changes from MIDI file
            self._process_program_changes()
            
            # Set default instruments if no program changes found
            self.set_default_instruments()
            
            return True
        except Exception as e:
            self.logger.error(f"Error loading MIDI file: {e}")
            return False
            
    def _process_program_changes(self):
        """Process program changes from the MIDI file to set up instruments correctly."""
        if not self.fs or not self.sfid:
            return
            
        # Dictionary to track applied instruments
        applied_instruments = {}
        
        # Find program change events in the MIDI file
        for event in self.midi_parser.events:
            # Safely check if this is a program change message
            try:
                is_program_change = False
                msg = event.message
                
                # Check if message has type attribute
                if hasattr(msg, 'type'):
                    is_program_change = msg.type == 'program_change'
                # Try dict() method if available
                elif hasattr(msg, 'dict'):
                    msg_dict = msg.dict()
                    is_program_change = msg_dict.get('type', '') == 'program_change'
                
                if is_program_change:
                    try:
                        # Get channel and program safely
                        if hasattr(msg, 'dict'):
                            msg_dict = msg.dict()
                            channel = msg_dict.get('channel', 0)
                            program = msg_dict.get('program', 0)
                        else:
                            channel = getattr(msg, 'channel', 0)
                            program = getattr(msg, 'program', 0)
                        
                        # Don't modify channel 15 which is reserved for metronome
                        if channel == 15:
                            continue
                            
                        # Get instrument name for logging
                        instrument_name = self._get_instrument_name(program, channel == 9)
                        applied_instruments[channel] = (program, instrument_name)
                        
                        self.logger.info(f"Setting channel {channel} to program {program} ({instrument_name})")
                        
                        try:
                            # Channel 9 is special (percussion)
                            if channel == 9:
                                bank = 128  # Percussion bank
                            else:
                                bank = 0  # Melodic bank
                                
                            self.fs.program_select(channel, self.sfid, bank, program)
                        except Exception as e:
                            self.logger.error(f"Error setting program: {e}")
                    except Exception as e:
                        self.logger.error(f"Error processing program change: {e}, Message: {event.message}")
            except Exception as e:
                self.logger.error(f"Error checking message type: {e}, Message: {event.message}")
                    
        # Log summary of applied instruments
        if applied_instruments:
            self.logger.info("MIDI file uses the following instruments:")
            for channel, (program, name) in sorted(applied_instruments.items()):
                self.logger.info(f"  Channel {channel}: {name} (Program {program})")
        
    def _get_instrument_name(self, program: int, is_percussion: bool = False) -> str:
        """
        Get a human-readable name for a MIDI program number.
        
        Args:
            program: MIDI program number (0-127)
            is_percussion: Whether this is a percussion channel
            
        Returns:
            Human-readable instrument name
        """
        if is_percussion:
            return "Percussion"
            
        # General MIDI instrument families (0-127)
        if program < 8:
            return f"Piano ({program})"
        elif program < 16:
            return f"Chromatic Percussion ({program})"
        elif program < 24:
            return f"Organ ({program})"
        elif program < 32:
            return f"Guitar ({program})"
        elif program < 40:
            return f"Bass ({program})"
        elif program < 48:
            return f"Strings ({program})"
        elif program < 56:
            return f"Ensemble ({program})"
        elif program < 64:
            return f"Brass ({program})"
        elif program < 72:
            return f"Reed ({program})"
        elif program < 80:
            return f"Pipe ({program})"
        elif program < 88:
            return f"Synth Lead ({program})"
        elif program < 96:
            return f"Synth Pad ({program})"
        elif program < 104:
            return f"Synth Effects ({program})"
        elif program < 112:
            return f"Ethnic ({program})"
        elif program < 120:
            return f"Percussive ({program})"
        else:
            return f"Sound Effects ({program})"

    def set_tempo(self, tempo: float) -> None:
        """
        Set a new tempo for playback.
        
        Args:
            tempo: New tempo in BPM (should be an integer for MIDI compatibility)
        """
        if tempo <= 0:
            self.logger.warning("Invalid tempo value. Must be positive.")
            return
            
        # Ensure tempo is an integer for MIDI compatibility
        if not isinstance(tempo, int):
            self.logger.warning(f"Tempo {tempo} is not an integer. Converting to integer for MIDI compatibility.")
            tempo = int(round(tempo))
            
        self.logger.info(f"Setting tempo to {tempo} BPM")
        self.midi_parser.adjust_tempo(tempo)
        self.metronome.set_tempo(tempo)
        
        # Update beat timestamps
        self.beat_timestamps = self.midi_parser.get_beat_times()
        
    def set_metronome_enabled(self, enabled: bool) -> None:
        """
        Enable or disable the metronome.
        
        Args:
            enabled: Whether to enable the metronome
        """
        self.metronome_enabled = enabled
        self.logger.info(f"Metronome {'enabled' if enabled else 'disabled'}")
        
    def set_intro_bars(self, enabled: bool, bars: int = 2) -> None:
        """
        Configure metronome intro settings.
        
        Args:
            enabled: Whether to play metronome intro
            bars: Number of intro bars (if enabled)
        """
        self.play_intro_bars = enabled
        self.intro_bars = max(1, bars)  # Ensure at least 1 bar
        self.logger.info(
            f"Metronome intro {'enabled' if enabled else 'disabled'}"
            f"{f', {bars} bars' if enabled else ''}"
        )
        
    def play(self, 
            beat_callback: Optional[Callable[[float, bool], None]] = None,
            position_callback: Optional[Callable[[float, float], None]] = None) -> bool:
        """
        Start playback of the loaded MIDI file.
        
        Args:
            beat_callback: Optional callback function(timestamp, is_downbeat)
            position_callback: Optional callback function(position, duration)
            
        Returns:
            True if playback started successfully, False otherwise
        """
        if self.playback_state == PlaybackState.PLAYING:
            return True
            
        if not self.midi_parser.events:
            self.logger.error("No MIDI file loaded")
            return False
            
        if self.fs is None and fluidsynth is not None:
            self._init_fluidsynth()
            
        if self.fs is None:
            self.logger.error("FluidSynth not initialized")
            return False
            
        # Set up callbacks
        self.beat_callback = beat_callback
        self.position_callback = position_callback
        
        # Start playback
        self._stop_event.clear()
        self.playback_state = PlaybackState.PLAYING
        
        if self.play_intro_bars:
            self.playback_state = PlaybackState.METRONOME_INTRO
            
        self.start_time = time.time()
        self.current_position = 0.0
        
        # Start playback in a separate thread
        self.playback_thread = threading.Thread(target=self._playback_loop)
        self.playback_thread.daemon = True
        self.playback_thread.start()
        
        return True
        
    def pause(self) -> None:
        """Pause playback."""
        if self.playback_state == PlaybackState.PLAYING:
            self.playback_state = PlaybackState.PAUSED
            self.pause_position = self.current_position
            
            # Stop any playing notes on all channels when pausing
            if self.fs:
                for channel in range(16):
                    self.fs.all_notes_off(channel)
                    
            self.logger.info(f"Playback paused at {self.pause_position:.2f}s")
            
    def resume(self) -> None:
        """Resume playback from pause."""
        if self.playback_state == PlaybackState.PAUSED:
            self.playback_state = PlaybackState.PLAYING
            self.start_time = time.time() - self.pause_position
            self.logger.info(f"Playback resumed from {self.pause_position:.2f}s")
            
    def stop(self) -> None:
        """Stop playback."""
        if self.playback_state != PlaybackState.STOPPED:
            self._stop_event.set()
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=0.5)
                
            self.playback_state = PlaybackState.STOPPED
            self.current_position = 0.0
            
            # Stop any playing notes on all channels
            if self.fs:
                for channel in range(16):
                    self.fs.all_notes_off(channel)
                
            self.logger.info("Playback stopped")
            
    def _playback_loop(self) -> None:
        """Internal method to handle MIDI playback."""
        if not self.fs:
            return
            
        # Get MIDI events and beat timestamps
        events = self.midi_parser.events
        beats = self.beat_timestamps
        
        # Handle metronome intro if enabled
        if self.playback_state == PlaybackState.METRONOME_INTRO:
            self._play_metronome_intro()
            if self._stop_event.is_set():
                return
                
            # Reset start time for main playback
            self.start_time = time.time()
            self.playback_state = PlaybackState.PLAYING
            
        # Get start position in case we're resuming
        start_position = self.pause_position if self.playback_state == PlaybackState.PAUSED else 0.0
        event_index = 0
        beat_index = 0
        
        # Skip events before start position
        while event_index < len(events) and events[event_index].time < start_position:
            event_index += 1
            
        # Skip beats before start position
        while beat_index < len(beats) and beats[beat_index][0] < start_position:
            beat_index += 1
            
        # Main playback loop
        last_metronome_time = 0.0
        metronome_interval = 60.0 / self.metronome.tempo
        metronome_channel = 15  # Use reserved channel for metronome
        
        while (not self._stop_event.is_set() and 
              self.playback_state != PlaybackState.STOPPED and
              event_index < len(events)):
            
            # Calculate current playback position
            if self.playback_state == PlaybackState.PLAYING:
                elapsed = time.time() - self.start_time
                self.current_position = start_position + elapsed
                
                # Report position
                if self.position_callback:
                    self.position_callback(self.current_position, self.midi_parser.midi_length)
                
                # Process MIDI events
                while (event_index < len(events) and 
                      events[event_index].time <= self.current_position):
                    event = events[event_index]
                    self._process_event(event)
                    event_index += 1
                    
                # Process beat events for synchronization
                while (beat_index < len(beats) and 
                      beats[beat_index][0] <= self.current_position):
                    beat_time, is_downbeat = beats[beat_index]
                    if self.beat_callback:
                        self.beat_callback(beat_time, is_downbeat)
                    beat_index += 1
                    
                # Handle metronome if enabled
                if self.metronome_enabled:
                    # Check if it's time for a metronome beat
                    metronome_time = self.current_position % metronome_interval
                    if (last_metronome_time > metronome_time):  # Wrapped around
                        beat_in_bar = int(self.current_position / metronome_interval) % self.metronome.meter[0]
                        is_accented = self.metronome.accent_pattern[beat_in_bar]
                        self._play_metronome_sound(is_accented)
                    last_metronome_time = metronome_time
                
            # Sleep to reduce CPU usage
            time.sleep(0.005)  # 5ms sleep for ~200Hz polling rate
            
        # Playback complete
        if event_index >= len(events) and self.playback_state != PlaybackState.STOPPED:
            self.playback_state = PlaybackState.STOPPED
            self.logger.info("Playback completed")
            
            # Stop any playing notes on all channels
            if self.fs:
                for channel in range(16):
                    self.fs.all_notes_off(channel)
                    
    def _process_event(self, event: MidiEvent) -> None:
        """
        Process a MIDI event during playback.
        
        Args:
            event: MIDI event to process
        """
        if not self.fs:
            return
            
        try:
            msg = event.message
            
            if event.event_type == MidiEventType.NOTE_ON:
                # Note-on events with velocity > 0
                # Use dict() or getattr to handle different mido versions
                try:
                    # First attempt with direct dict access
                    if hasattr(msg, 'dict'):
                        msg_dict = msg.dict()
                        channel = msg_dict.get('channel', 0)
                        note = msg_dict.get('note', 60)
                        velocity = msg_dict.get('velocity', 64)
                    # Second attempt with attribute access
                    else:
                        channel = getattr(msg, 'channel', 0)
                        note = getattr(msg, 'note', 60)
                        velocity = getattr(msg, 'velocity', 64)
                    
                    self.logger.debug(f"Note ON: Channel {channel}, Note {note}, Velocity {velocity}")
                    self.fs.noteon(channel, note, velocity)
                except Exception as e:
                    self.logger.error(f"Error processing NOTE_ON event: {e}, Message: {msg}")
                
            elif event.event_type == MidiEventType.NOTE_OFF:
                # Note-off events or note-on with velocity 0
                try:
                    # First attempt with direct dict access
                    if hasattr(msg, 'dict'):
                        msg_dict = msg.dict()
                        channel = msg_dict.get('channel', 0)
                        note = msg_dict.get('note', 60)
                    # Second attempt with attribute access
                    else:
                        channel = getattr(msg, 'channel', 0)
                        note = getattr(msg, 'note', 60)
                    
                    self.logger.debug(f"Note OFF: Channel {channel}, Note {note}")
                    self.fs.noteoff(channel, note)
                except Exception as e:
                    self.logger.error(f"Error processing NOTE_OFF event: {e}, Message: {msg}")
                
            else:
                # For other event types, safely check message type
                try:
                    # Safely get the message type
                    if hasattr(msg, 'type'):
                        msg_type = msg.type
                    elif hasattr(msg, 'dict'):
                        msg_dict = msg.dict()
                        msg_type = msg_dict.get('type', '')
                    else:
                        msg_type = ''
                    
                    # Handle different message types
                    if msg_type == 'program_change':
                        # Program change events
                        try:
                            if hasattr(msg, 'dict'):
                                msg_dict = msg.dict()
                                channel = msg_dict.get('channel', 0)
                                program = msg_dict.get('program', 0)
                            else:
                                channel = getattr(msg, 'channel', 0)
                                program = getattr(msg, 'program', 0)
                            
                            self.logger.info(f"Program Change: Channel {channel}, Program {program}")
                            
                            # Configure channel program
                            if self.sfid:
                                bank = 128 if channel == 9 else 0
                                self.fs.program_select(channel, self.sfid, bank, program)
                        except Exception as e:
                            self.logger.error(f"Error processing program_change event: {e}, Message: {msg}")
                        
                    elif msg_type == 'control_change':
                        # Control change events
                        try:
                            if hasattr(msg, 'dict'):
                                msg_dict = msg.dict()
                                channel = msg_dict.get('channel', 0)
                                control = msg_dict.get('control', 0)
                                value = msg_dict.get('value', 0)
                            else:
                                channel = getattr(msg, 'channel', 0)
                                control = getattr(msg, 'control', 0)
                                value = getattr(msg, 'value', 0)
                            
                            self.logger.debug(f"Control Change: Channel {channel}, Control {control}, Value {value}")
                            self.fs.cc(channel, control, value)
                        except Exception as e:
                            self.logger.error(f"Error processing control_change event: {e}, Message: {msg}")
                        
                    elif msg_type == 'pitchwheel':
                        # Pitch wheel events
                        try:
                            if hasattr(msg, 'dict'):
                                msg_dict = msg.dict()
                                channel = msg_dict.get('channel', 0)
                                pitch = msg_dict.get('pitch', 0)
                            else:
                                channel = getattr(msg, 'channel', 0)
                                pitch = getattr(msg, 'pitch', 0)
                            
                            self.logger.debug(f"Pitch Wheel: Channel {channel}, Pitch {pitch}")
                            self.fs.pitch_bend(channel, pitch)
                        except Exception as e:
                            self.logger.error(f"Error processing pitchwheel event: {e}, Message: {msg}")
                            
                except Exception as e:
                    self.logger.error(f"Error determining message type: {e}, Message: {msg}")
                
        except Exception as e:
            self.logger.error(f"Error processing MIDI event: {e}")
            
    def _play_metronome_sound(self, accented: bool) -> None:
        """
        Play a metronome sound.
        
        Args:
            accented: Whether to play accented beat (ignored in this implementation)
        """
        if not self.fs:
            return
            
        # MIDI note numbers and velocities for metronome sounds
        # Using a single sound regardless of accent pattern
        metronome_note = 76  # High wood block
        velocity = 85  # Medium-high velocity for all beats
        metronome_channel = 15  # Use reserved channel for metronome
        
        # Create local reference to FluidSynth to avoid None issues
        fs = self.fs
        if fs is None:
            return
        
        # Play the same sound for all beats, ignoring accent parameter
        fs.noteon(metronome_channel, metronome_note, velocity)
        # Schedule note off after a short duration
        # Use a local copy of fs to avoid potential None reference
        threading.Timer(0.05, lambda f=fs, c=metronome_channel, n=metronome_note: f.noteoff(c, n) if f else None).start()
            
    def _play_metronome_intro(self) -> None:
        """Play metronome introduction bars."""
        if not self.metronome_enabled or not self.play_intro_bars:
            return
            
        # Calculate intro duration
        bar_duration = self.metronome.get_bar_duration()
        total_duration = bar_duration * self.intro_bars
        
        self.logger.info(f"Playing {self.intro_bars} bar metronome intro")
        
        # Play intro
        start_time = time.time()
        elapsed = 0.0
        last_beat = -1
        
        while elapsed < total_duration and not self._stop_event.is_set():
            elapsed = time.time() - start_time
            
            # Calculate current beat
            beat_duration = 60.0 / self.metronome.tempo
            current_beat = int(elapsed / beat_duration)
            
            if current_beat > last_beat:
                # New beat
                beat_in_bar = current_beat % self.metronome.meter[0]
                is_accented = self.metronome.accent_pattern[beat_in_bar]
                self._play_metronome_sound(is_accented)
                last_beat = current_beat
                
                # Report beat via callback if provided
                if self.beat_callback:
                    self.beat_callback(elapsed, beat_in_bar == 0)
                    
            # Sleep to reduce CPU usage
            time.sleep(0.005)
            
    def set_soundfont(self, soundfont_path: str) -> bool:
        """
        Set a new SoundFont file.
        
        Args:
            soundfont_path: Path to SoundFont file
            
        Returns:
            True if the SoundFont was loaded successfully, False otherwise
        """
        if not os.path.exists(soundfont_path):
            self.logger.error(f"SoundFont file not found: {soundfont_path}")
            return False
            
        # Unload previous SoundFont if any
        if self.fs and self.sfid is not None:
            self.fs.sfunload(self.sfid)
            
        try:
            if self.fs:
                self.sfid = self.fs.sfload(soundfont_path)
                self.soundfont_path = soundfont_path
                
                # Set up instrument for metronome
                self.fs.program_select(0, self.sfid, 0, self.midi_instrument)
                self.logger.info(f"Loaded SoundFont: {soundfont_path}")
                return True
        except Exception as e:
            self.logger.error(f"Error loading SoundFont: {e}")
            return False
            
    def set_gain(self, gain: float) -> None:
        """
        Set audio gain (volume).
        
        Args:
            gain: Gain value between 0.0 and 1.0
        """
        gain = max(0.0, min(1.0, gain))  # Clamp between 0.0 and 1.0
        self.gain = gain
        
        if self.fs:
            self.fs.setting("synth.gain", gain)
            self.logger.info(f"Set gain to {gain}")
            
    def set_midi_instrument(self, instrument: int) -> None:
        """
        Set MIDI instrument for metronome.
        
        Args:
            instrument: MIDI instrument number (0-127)
        """
        self.midi_instrument = instrument
        
        if self.fs and self.sfid is not None:
            try:
                self.fs.program_select(0, self.sfid, 0, instrument)
                self.logger.info(f"Set metronome instrument to {instrument}")
            except Exception as e:
                self.logger.error(f"Error setting instrument: {e}")
                
    def adjust_tempo_to_cadence(self, cadence: float, ratio: float = 1.0) -> float:
        """
        Adjust tempo based on gait cadence.
        
        Args:
            cadence: Cadence in steps per minute
            ratio: Optional adjustment ratio (1.0 = exact match)
            
        Returns:
            The new tempo in BPM
        """
        if cadence <= 0:
            self.logger.warning("Invalid cadence value. Must be positive.")
            return self.metronome.tempo
            
        # Convert cadence to musical tempo
        # In RAS, each step typically corresponds to one beat
        # The ratio parameter allows for adjustments (e.g., 0.9 = slower tempo)
        new_tempo = cadence * ratio
        
        # Apply reasonable bounds for musical tempo
        new_tempo = max(40.0, min(208.0, new_tempo))
        
        # Set the new tempo
        self.set_tempo(new_tempo)
        return new_tempo
        
    def get_beat_timestamps(self, start_time: float = 0.0, 
                          end_time: Optional[float] = None) -> List[Tuple[float, bool]]:
        """
        Get beat timestamps for synchronization.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds, or None for all beats
            
        Returns:
            List of tuples (time, is_downbeat)
        """
        return self.midi_parser.get_beat_times(start_time, end_time)
        
    def get_music_info(self) -> Dict:
        """
        Get information about the current music.
        
        Returns:
            Dictionary containing music information
        """
        return {
            'tempo': self.metronome.tempo,
            'meter': self.metronome.meter,
            'file_info': self.midi_parser.get_midi_data(),
            'duration': self.midi_parser.midi_length,
            'metronome_enabled': self.metronome_enabled,
            'playback_state': self.playback_state.name,
            'position': self.current_position
        }
        
    def release(self) -> None:
        """Release resources used by the music processor."""
        self.stop()
        
        if self.fs:
            if self.sfid is not None:
                self.fs.sfunload(self.sfid)
            self.fs.delete()
            self.fs = None
            
    def __del__(self):
        """Destructor to ensure resources are released."""
        self.release()
        
    def __enter__(self):
        """Support for context manager protocol."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support for context manager protocol."""
        self.release()

    def test_sound(self, play_test_notes: bool = True) -> bool:
        """
        Test the audio system.
        
        Args:
            play_test_notes: If True, plays a test chord, otherwise just checks if FluidSynth is initialized
            
        Returns:
            True if audio system is ready, False otherwise
        """
        if not self.fs:
            self.logger.error("FluidSynth not initialized")
            return False
            
        if not play_test_notes:
            # Just check if FluidSynth is initialized properly
            return self.fs is not None
            
        try:
            self.logger.info("Playing test sound (C major chord)...")
            
            # Check if we have an available soundfont
            soundfont_status = ""
            if self.sfid is None:
                soundfont_status = "No SoundFont loaded. Using default instrument sounds."
                self.logger.warning(soundfont_status)
                
                # Create a placeholder SoundFont ID
                self.sfid = 0
                
                # Try to set programs without a SoundFont
                try:
                    self.fs.program_select(0, 0, 0, 0)  # Piano
                    self.fs.program_select(15, 0, 0, 115)  # Woodblock for metronome
                except Exception as e:
                    self.logger.error(f"Error setting programs: {e}")
            
            # Play a C major chord on piano (channel 0)
            try:
                self.fs.noteon(0, 60, 100)  # C4
                self.fs.noteon(0, 64, 100)  # E4
                self.fs.noteon(0, 67, 100)  # G4
                
                time.sleep(0.5)
                
                self.fs.noteoff(0, 60)
                self.fs.noteoff(0, 64)
                self.fs.noteoff(0, 67)
                
                # Also test metronome sound on its dedicated channel
                metronome_channel = 15
                self.fs.noteon(metronome_channel, 76, 100)  # High wood block
                time.sleep(0.3)
                self.fs.noteoff(metronome_channel, 76)
                
                self.logger.info("Test sound completed successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error during test sound playback: {e}")
                if soundfont_status:
                    self.logger.error(soundfont_status)
                return False
            
        except Exception as e:
            self.logger.error(f"Error playing test sound: {e}")
            return False
            
    def download_default_soundfont(self, target_path: str) -> bool:
        """
        Download a default SoundFont file.
        
        Args:
            target_path: Path where to save the downloaded SoundFont
            
        Returns:
            True if download was successful, False otherwise
        """
        self.logger.info(f"Attempting to download a default SoundFont to {target_path}")
        
        try:
            import urllib.request
            from pathlib import Path
            
            # Create directory if it doesn't exist
            target_dir = Path(target_path).parent
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # URL for Fluid GM soundfont (one of several options)
            soundfont_urls = [
                "https://archive.org/download/fluidr3-gm-gs/FluidR3_GM.sf2",  # Internet Archive
                "https://github.com/FluidSynth/fluidsynth/raw/master/sf2/GeneralUser_GS_v1.471.sf2"  # GitHub
            ]
            
            # Try each URL in turn
            for url in soundfont_urls:
                try:
                    self.logger.info(f"Downloading SoundFont from {url}")
                    
                    # Download with a timeout
                    urllib.request.urlretrieve(url, target_path)
                    
                    if Path(target_path).exists() and Path(target_path).stat().st_size > 1000000:
                        self.logger.info(f"Successfully downloaded SoundFont to {target_path}")
                        return True
                except Exception as e:
                    self.logger.warning(f"Failed to download from {url}: {e}")
            
            self.logger.error("All download attempts failed")
            return False
            
        except Exception as e:
            self.logger.error(f"Error downloading SoundFont: {e}")
            return False

    def set_channel_instrument(self, channel: int, program: int) -> bool:
        """
        Set a specific instrument for a MIDI channel.
        
        Args:
            channel: MIDI channel (0-15)
            program: MIDI program number (0-127)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.fs or not self.sfid:
            self.logger.error("FluidSynth not initialized")
            return False
        
        if channel < 0 or channel > 15:
            self.logger.error(f"Invalid channel number: {channel}. Must be 0-15.")
            return False
        
        if program < 0 or program > 127:
            self.logger.error(f"Invalid program number: {program}. Must be 0-127.")
            return False
        
        # Don't modify channel 15 which is reserved for metronome
        if channel == 15:
            self.logger.warning("Channel 15 is reserved for metronome. Not changing.")
            return False
        
        try:
            # Channel 9 is special (percussion)
            if channel == 9:
                bank = 128  # Percussion bank
            else:
                bank = 0  # Melodic bank
            
            instrument_name = self._get_instrument_name(program, channel == 9)
            self.logger.info(f"Setting channel {channel} to program {program} ({instrument_name})")
            
            self.fs.program_select(channel, self.sfid, bank, program)
            return True
        except Exception as e:
            self.logger.error(f"Error setting program: {e}")
            return False

    def set_default_instruments(self) -> None:
        """
        Set default instruments for channels if no program changes are found in the MIDI.
        This is useful for MIDI files that don't include program change events.
        """
        if not self.fs or not self.sfid or not self.midi_parser:
            return
        
        # Check if we have any program changes in the MIDI file
        program_changes_exist = False
        for event in self.midi_parser.events:
            if hasattr(event.message, 'type') and event.message.type == 'program_change':
                program_changes_exist = True
                break
            
        # If no program changes found, set default instruments
        if not program_changes_exist:
            self.logger.info("No program changes found in MIDI file. Setting default instruments.")
            
            # Set up some standard General MIDI instruments
            # Channel 0: Acoustic Grand Piano (0)
            self.set_channel_instrument(0, 0)
            
            # Channel 1: Acoustic Guitar (nylon) (24)
            self.set_channel_instrument(1, 24)
            
            # Channel 2: Acoustic Bass (32) 
            self.set_channel_instrument(2, 32)
            
            # Channel 3: String Ensemble 1 (48)
            self.set_channel_instrument(3, 48)
            
            # Channel 4: Flute (73)
            self.set_channel_instrument(4, 73)
            
            # Channel 9: Standard Drum Kit (already percussion by default)
            # Don't need to set this explicitly
        else:
            self.logger.info("Program changes found in MIDI file. Using instruments from MIDI file.")

    def set_metronome_accents(self, use_accents: bool) -> None:
        """
        Enable or disable metronome accents.
        
        Args:
            use_accents: True to use accented beats (first beat emphasis), 
                        False for uniform beats (all beats sound the same)
        """
        self.metronome.toggle_accents(use_accents)
        accent_mode = "enabled" if use_accents else "disabled" 
        self.logger.info(f"Metronome accents {accent_mode}")