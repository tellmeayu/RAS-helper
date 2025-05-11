"""
Music Processing Module

This module handles MIDI file parsing, tempo adjustment, and audio playback
for rhythmic auditory stimulation.
"""

from .music_processor import MusicProcessor
from .midi_parser import MidiParser, MidiEvent, MidiEventType
from .metronome import Metronome

__all__ = ['MusicProcessor', 'MidiParser', 'MidiEvent', 'MidiEventType', 'Metronome']
