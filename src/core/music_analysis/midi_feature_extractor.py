#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIDI Feature Extractor

This module provides functionality for extracting rhythmic and musical features from MIDI files.
"""

import os
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

# Import existing MIDI parser
from ..music_processing.midi_parser import MidiParser, MidiEvent, MidiEventType


class MidiFeatureExtractor:
    """
    Class for extracting rhythmic and other musical features from MIDI files.
    
    This class analyzes MIDI files to extract features relevant for rhythmic auditory
    stimulation, with a focus on rhythm characterization for gait rehabilitation.
    """
    
    def __init__(self, midi_parser: Optional[MidiParser] = None):
        """
        Initialize the MIDI feature extractor.
        
        Args:
            midi_parser: Optional existing MidiParser instance
        """
        self.midi_parser = midi_parser if midi_parser else MidiParser()
        self.features = {}
        
    def load_file(self, file_path: Union[str, Path]) -> bool:
        """
        Load a MIDI file for feature extraction.
        
        Args:
            file_path: Path to the MIDI file
            
        Returns:
            True if the file was loaded successfully, False otherwise
        """
        return self.midi_parser.load_file(file_path)
        
    def extract_all_features(self) -> Dict:
        """
        Extract all rhythmic and musical features from the loaded MIDI file.
        
        Returns:
            Dictionary containing all extracted features
        """
        self.features = {}
        
        # Basic MIDI information
        self.features.update(self._extract_basic_info())
        
        # Extract rhythm features
        self.features.update(self._extract_rhythm_features())
        
        # Extract melodic features
        self.features.update(self._extract_melodic_features())
        
        # Extract style/mood features
        self.features.update(self._extract_style_mood_features())
        
        return self.features
        
    def _extract_basic_info(self) -> Dict:
        """
        Extract basic information from the MIDI file.
        
        Returns:
            Dictionary containing basic MIDI file information
        """
        return {
            'original_tempo': self.midi_parser.current_tempo,
            'time_signature': self.midi_parser.current_time_signature,
            'duration': self.midi_parser.midi_length,
            'beat_count': len(self.midi_parser.beat_positions),
            'track_count': len(self.midi_parser.tracks) if hasattr(self.midi_parser, 'tracks') else 0,
        }
        
    def _extract_rhythm_features(self) -> Dict:
        """
        Extract rhythm-related features from the MIDI file.
        
        Returns:
            Dictionary containing rhythm features
        """
        features = {}
        
        # Get note events (filtered to note_on with velocity > 0)
        note_events = [event for event in self.midi_parser.events 
                      if event.event_type == MidiEventType.NOTE_ON]
        
        if not note_events:
            return {'note_count': 0}
            
        # Calculate Inter-Onset Intervals (IOIs)
        note_times = [event.time for event in note_events]
        iois = np.diff(note_times)
        
        if len(iois) == 0:
            return {'note_count': len(note_events)}
            
        # Basic IOI statistics
        features['note_count'] = len(note_events)
        features['ioi_mean'] = float(np.mean(iois))
        features['ioi_std'] = float(np.std(iois))
        features['ioi_min'] = float(np.min(iois))
        features['ioi_max'] = float(np.max(iois))
        
        # Calculate note density (notes per second)
        if self.midi_parser.midi_length > 0:
            features['note_density'] = len(note_events) / self.midi_parser.midi_length
        else:
            features['note_density'] = 0
            
        # Calculate note density per beat
        if len(self.midi_parser.beat_positions) > 0:
            features['notes_per_beat'] = len(note_events) / len(self.midi_parser.beat_positions)
        else:
            features['notes_per_beat'] = 0
            
        # Calculate rhythm regularity (lower std/mean ratio indicates more regular rhythm)
        if features['ioi_mean'] > 0:
            features['rhythm_regularity'] = 1.0 - min(1.0, features['ioi_std'] / features['ioi_mean'])
        else:
            features['rhythm_regularity'] = 0
            
        # Calculate beat histogram
        features.update(self._calculate_beat_histogram())
        
        # Calculate metrical strength
        features.update(self._calculate_metrical_strength(note_events))
        
        # Calculate syncopation measure
        features.update(self._calculate_syncopation())
        
        return features
        
    def _extract_melodic_features(self) -> Dict:
        """
        Extract melodic features from the MIDI file.
        
        Returns:
            Dictionary containing melodic features
        """
        features = {}
        
        # Get note events (filtered to note_on with velocity > 0)
        note_events = [event for event in self.midi_parser.events 
                      if event.event_type == MidiEventType.NOTE_ON]
        
        if not note_events:
            return {'pitch_range': 0}
            
        # Extract pitch information
        pitches = []
        for event in note_events:
            if hasattr(event.message, 'note'):
                pitches.append(event.message.note)
            elif hasattr(event.message, 'dict') and 'note' in event.message.dict():
                pitches.append(event.message.dict()['note'])
        
        if not pitches:
            return {'pitch_range': 0}
            
        # Calculate pitch range and average
        features['pitch_min'] = min(pitches)
        features['pitch_max'] = max(pitches)
        features['pitch_range'] = features['pitch_max'] - features['pitch_min']
        features['pitch_mean'] = float(np.mean(pitches))
        
        return features
        
    def _extract_style_mood_features(self) -> Dict:
        """
        Extract features related to musical style and mood.
        
        This analyzes various aspects of the MIDI file to determine style and mood
        characteristics, which can be used for categorization.
        
        Returns:
            Dictionary containing style and mood features
        """
        features = {}
        
        # Get note events
        note_events = [event for event in self.midi_parser.events 
                      if event.event_type == MidiEventType.NOTE_ON]
        
        if not note_events:
            return {'emotional_intensity': 0.0}
        
        # Extract velocity information (loudness) for dynamic range analysis
        velocities = []
        for event in note_events:
            if hasattr(event.message, 'velocity'):
                velocities.append(event.message.velocity)
            elif hasattr(event.message, 'dict') and 'velocity' in event.message.dict():
                velocities.append(event.message.dict()['velocity'])
        
        if not velocities:
            return {'emotional_intensity': 0.0}
            
        # Calculate dynamic range (for emotional intensity)
        features['velocity_mean'] = float(np.mean(velocities))
        features['velocity_std'] = float(np.std(velocities))
        features['dynamic_range'] = float(max(velocities) - min(velocities))
        
        # Calculate velocity distribution (for intensity and mood)
        # High velocity notes with low variability often indicate higher energy/intensity
        if features['velocity_mean'] > 0:
            features['velocity_variation'] = features['velocity_std'] / features['velocity_mean']
        else:
            features['velocity_variation'] = 0.0
        
        # Derive emotional intensity from dynamics and rhythm features
        # Combine: velocity mean, dynamic range, rhythm regularity, note density
        emotional_intensity = (
            0.3 * (features['velocity_mean'] / 127.0) +
            0.2 * (features['dynamic_range'] / 127.0) +
            0.2 * (1.0 - self.features.get('rhythm_regularity', 0.5)) +
            0.3 * min(1.0, self.features.get('note_density', 0.0) / 8.0)
        )
        features['emotional_intensity'] = float(emotional_intensity)
        
        # Calculate tempo stability for mood analysis (stable = calm/controlled, variable = more excited/dramatic)
        tempo_changes = 0
        prev_tempo = None
        
        for event in self.midi_parser.events:
            # Check for tempo change meta events (META type with set_tempo subtype)
            if hasattr(event, 'event_type') and hasattr(event.message, 'type'):
                # Check for tempo change meta events
                if getattr(event.message, 'type', None) == 'set_tempo':
                    if prev_tempo is not None:
                        tempo_changes += 1
                    prev_tempo = event.message.tempo
        
        # Normalize tempo changes based on song length
        song_duration = self.midi_parser.midi_length
        if song_duration > 0:
            features['tempo_change_rate'] = tempo_changes / song_duration
        else:
            features['tempo_change_rate'] = 0.0
        
        # Feature to indicate if the piece tends toward relaxed vs energetic
        # Combine rhythm complexity, tempo, and note density
        # Higher values = more energetic, lower = more relaxed
        tempo_factor = min(1.0, self.midi_parser.current_tempo / 160.0)
        energetic_factor = (
            0.3 * tempo_factor +
            0.3 * self.features.get('syncopation_index', 0.0) +
            0.2 * min(1.0, self.features.get('note_density', 0.0) / 6.0) +
            0.2 * emotional_intensity
        )
        features['energetic_factor'] = float(energetic_factor)
        
        # Calculate how much the composition tends toward bright vs dark based on:
        # 1. Average pitch (higher = brighter)
        # 2. Major/minor mode detection
        # For simplicity, we'll mostly use pitch information since mode detection is complex
        avg_pitch = self.features.get('pitch_mean', 60)
        pitch_brightness = (avg_pitch - 40) / 45.0  # Normalize to 0-1 range over typical range
        features['brightness_factor'] = max(0.0, min(1.0, float(pitch_brightness)))
        
        return features
        
    def _calculate_beat_histogram(self) -> Dict:
        """
        Calculate beat histogram showing note distribution relative to beat positions.
        
        Returns:
            Dictionary containing beat histogram features
        """
        features = {}
        
        # Get beat positions and note events
        beats = self.midi_parser.beat_positions
        note_events = [event for event in self.midi_parser.events 
                      if event.event_type == MidiEventType.NOTE_ON]
        
        if not beats or not note_events:
            return {'beat_histogram': []}
            
        # Create a beat histogram with 16 bins per beat (to capture 16th note level precision)
        bins_per_beat = 16
        beat_histogram = np.zeros(bins_per_beat)
        
        # Calculate the average beat duration
        beat_times = [beat[0] for beat in beats]
        if len(beat_times) <= 1:
            avg_beat_duration = 60.0 / self.midi_parser.current_tempo  # fallback
        else:
            avg_beat_duration = np.mean(np.diff(beat_times))
            
        # Assign each note to a position within a beat
        for event in note_events:
            # Find the preceding beat
            preceding_beat_idx = 0
            for i, (beat_time, _, _) in enumerate(beats):
                if beat_time <= event.time:
                    preceding_beat_idx = i
                else:
                    break
                    
            if preceding_beat_idx >= len(beats) - 1:
                # Note is after the last beat, use the last beat
                preceding_beat_time = beats[preceding_beat_idx][0]
            else:
                preceding_beat_time = beats[preceding_beat_idx][0]
                
            # Calculate position within the beat (0.0 to 1.0)
            position_in_beat = (event.time - preceding_beat_time) / avg_beat_duration
            position_in_beat = position_in_beat % 1.0  # Wrap around to handle notes after the beat
            
            # Determine histogram bin
            bin_idx = min(int(position_in_beat * bins_per_beat), bins_per_beat - 1)
            beat_histogram[bin_idx] += 1
            
        # Normalize the histogram
        if np.sum(beat_histogram) > 0:
            beat_histogram = beat_histogram / np.sum(beat_histogram)
            
        features['beat_histogram'] = beat_histogram.tolist()
        
        # Calculate beat histogram statistics
        if len(beat_histogram) > 0:
            # First bin represents downbeat, higher value indicates stronger downbeats
            features['downbeat_strength'] = float(beat_histogram[0])
            
            # Calculate entropy of the histogram (higher entropy = more diverse rhythm)
            non_zero_bins = beat_histogram[beat_histogram > 0]
            if len(non_zero_bins) > 0:
                entropy = -np.sum(non_zero_bins * np.log2(non_zero_bins))
                features['beat_entropy'] = float(entropy)
            else:
                features['beat_entropy'] = 0.0
        
        return features
        
    def _calculate_metrical_strength(self, note_events: List[MidiEvent]) -> Dict:
        """
        Calculate how well notes align with the metrical grid.
        
        Args:
            note_events: List of note on events
            
        Returns:
            Dictionary containing metrical strength features
        """
        features = {}
        
        # Get beat positions
        beats = self.midi_parser.beat_positions
        
        if not beats or not note_events:
            return {'metrical_strength': 0.0}
            
        total_alignment = 0.0
        total_notes = len(note_events)
        
        # Calculate the average beat duration
        beat_times = [beat[0] for beat in beats]
        if len(beat_times) <= 1:
            avg_beat_duration = 60.0 / self.midi_parser.current_tempo  # fallback
        else:
            avg_beat_duration = np.mean(np.diff(beat_times))
            
        # For each note, find how close it is to a beat or sub-beat
        for event in note_events:
            # Find the closest beat
            closest_beat_time = min(beat_times, key=lambda x: abs(x - event.time))
            distance_to_beat = abs(event.time - closest_beat_time)
            
            # Calculate normalized distance (0.0 = perfect alignment, 1.0 = furthest from any beat)
            normalized_distance = min(distance_to_beat / (avg_beat_duration / 2), 1.0)
            alignment = 1.0 - normalized_distance
            total_alignment += alignment
            
        # Calculate average alignment score
        if total_notes > 0:
            features['metrical_strength'] = total_alignment / total_notes
        else:
            features['metrical_strength'] = 0.0
            
        return features
        
    def _calculate_syncopation(self) -> Dict:
        """
        Calculate the syncopation index of the MIDI file.
        
        Returns:
            Dictionary containing syncopation features
        """
        features = {}
        
        # Get beat positions and note events
        beats = self.midi_parser.beat_positions
        note_events = [event for event in self.midi_parser.events 
                      if event.event_type == MidiEventType.NOTE_ON]
        
        if not beats or not note_events:
            return {'syncopation_index': 0.0}
            
        # Create beat weights based on metrical strength
        # In 4/4 time, beat 1 is strongest, followed by beat 3, then 2 and 4
        # We'll use the time signature information to adjust
        time_sig = self.midi_parser.current_time_signature
        beats_per_bar = time_sig[0]
        
        # Create weight distribution based on time signature
        beat_weights = np.ones(beats_per_bar)
        if beats_per_bar == 4:  # 4/4 time
            beat_weights = np.array([1.0, 0.5, 0.75, 0.5])
        elif beats_per_bar == 3:  # 3/4 time
            beat_weights = np.array([1.0, 0.5, 0.75])
        elif beats_per_bar == 2:  # 2/4 time
            beat_weights = np.array([1.0, 0.5])
            
        # Calculate expected vs actual note distribution
        expected_distribution = beat_weights / np.sum(beat_weights)
        
        # Count notes on each beat position
        beat_counts = np.zeros(beats_per_bar)
        
        for event in note_events:
            # Find which beat this note is closest to
            closest_beat_idx = -1
            min_distance = float('inf')
            
            for i, (beat_time, _, _) in enumerate(beats):
                distance = abs(event.time - beat_time)
                if distance < min_distance:
                    min_distance = distance
                    closest_beat_idx = i
                    
            if closest_beat_idx >= 0:
                # Determine the beat position within the bar
                beat_in_bar = closest_beat_idx % beats_per_bar
                beat_counts[beat_in_bar] += 1
                
        # Normalize to get actual distribution
        total_notes = np.sum(beat_counts)
        if total_notes > 0:
            actual_distribution = beat_counts / total_notes
        else:
            actual_distribution = np.zeros_like(expected_distribution)
            
        # Calculate difference between expected and actual distribution
        # The more it differs from expected, the more syncopated it is
        distribution_diff = np.sum(np.abs(expected_distribution - actual_distribution)) / 2.0
        
        # Higher values indicate more syncopation (0.0 to 1.0 scale)
        features['syncopation_index'] = float(distribution_diff)
        
        # Also calculate off-beat note ratio
        on_beat_threshold = 0.125  # 1/8th note threshold
        on_beat_notes = 0
        
        for event in note_events:
            # Find the closest beat time
            closest_beat_time = min([beat[0] for beat in beats], key=lambda x: abs(x - event.time))
            
            # If the note is within the threshold of a beat, it's "on the beat"
            if abs(event.time - closest_beat_time) <= on_beat_threshold:
                on_beat_notes += 1
                
        if total_notes > 0:
            features['off_beat_ratio'] = 1.0 - (on_beat_notes / total_notes)
        else:
            features['off_beat_ratio'] = 0.0
            
        return features 