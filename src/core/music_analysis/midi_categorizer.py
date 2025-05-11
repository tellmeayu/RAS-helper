#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIDI Categorizer

This module provides functionality for categorizing MIDI files based on their features.
"""

import json
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

from .midi_feature_extractor import MidiFeatureExtractor


class RhythmicCharacter(Enum):
    """Enumeration of different rhythmic characters for categorization."""
    CLEAR_STEADY = "Clear & Steady Beat"
    MODERATELY_RHYTHMIC = "Moderately Rhythmic"  
    GROOVY_SYNCOPATED = "Groovy & Syncopated"
    SMOOTH_FLOWING = "Smooth & Flowing"


class GenreCategory(Enum):
    """Enumeration of common musical genres for categorization."""
    POP = "Pop"
    ROCK = "Rock"
    CLASSICAL = "Classical"
    JAZZ = "Jazz"
    ELECTRONIC = "Electronic"
    FOLK = "Folk"
    WORLD = "World Music"
    AMBIENT = "Ambient"
    OTHER = "Other"


class MoodCategory(Enum):
    """Enumeration of mood categories for music classification."""
    ENERGETIC = "Energetic"
    RELAXED = "Relaxed"
    UPLIFTING = "Uplifting"
    MELANCHOLIC = "Melancholic"
    CHEERFUL = "Cheerful"
    PEACEFUL = "Peaceful"
    INTENSE = "Intense"
    CHILL = "Chill"


class MidiCategorizer:
    """
    Class for categorizing MIDI files based on extracted features.
    
    This class analyzes MIDI features to assign appropriate tags and categories
    for use in the music selection interface of the NeuroApp.
    """
    
    def __init__(self, feature_extractor: Optional[MidiFeatureExtractor] = None):
        """
        Initialize the MIDI categorizer.
        
        Args:
            feature_extractor: Optional existing MidiFeatureExtractor instance
        """
        self.feature_extractor = feature_extractor if feature_extractor else MidiFeatureExtractor()
        self.categories = {}
        
    def categorize_file(self, file_path: Union[str, Path], 
                       extract_features: bool = True) -> Dict:
        """
        Categorize a MIDI file based on its features.
        
        Args:
            file_path: Path to the MIDI file
            extract_features: Whether to extract features (or use previously extracted)
            
        Returns:
            Dictionary containing assigned categories and features
        """
        if extract_features:
            success = self.feature_extractor.load_file(file_path)
            if not success:
                return {"error": "Failed to load MIDI file"}
                
            features = self.feature_extractor.extract_all_features()
        else:
            features = self.feature_extractor.features
            
        # Assign categories based on features
        self.categories = self._assign_categories(features)
        
        # Create metadata record
        metadata = {
            "filePath": str(file_path),
            "originalTempo": features.get("original_tempo", 120),
            "timeSignature": features.get("time_signature", (4, 4)),
            "duration": features.get("duration", 0),
            "rhythmicFeatures": {
                "noteDensity": features.get("note_density", 0),
                "notesPerBeat": features.get("notes_per_beat", 0),
                "rhythmRegularity": features.get("rhythm_regularity", 0),
                "metricalStrength": features.get("metrical_strength", 0),
                "syncopationIndex": features.get("syncopation_index", 0),
                "offBeatRatio": features.get("off_beat_ratio", 0),
                "downbeatStrength": features.get("downbeat_strength", 0)
            },
            "tags": self.categories
        }
        
        return metadata
        
    def _assign_categories(self, features: Dict) -> Dict:
        """
        Assign categories based on extracted features.
        
        Args:
            features: Dictionary of features extracted from MIDI file
            
        Returns:
            Dictionary of assigned categories
        """
        categories = {}
        
        # Determine mood/style first as it can influence rhythmic style
        categories["mood"] = self._determine_mood(features)
        
        # Assign rhythmic character
        # If the suggested rhythmic style from mood doesn't conflict with feature-based analysis,
        # we can use it as a hint, but the feature-based analysis takes precedence
        rhythmic_style = self._determine_rhythmic_character(features)
        categories["rhythmicCharacter"] = rhythmic_style
        
        # Attempt to determine genre 
        # (In a real implementation, this would likely use a trained classifier)
        # For demonstration, we'll use a simple rule-based approach
        categories["genre"] = self._determine_genre(features)
        
        return categories
        
    def _determine_rhythmic_character(self, features: Dict) -> str:
        """
        Determine the rhythmic character of a MIDI file based on its features.
        
        Args:
            features: Dictionary of features extracted from MIDI file
            
        Returns:
            String representing the rhythmic character category
        """
        # Extract relevant features with default values
        metrical_strength = features.get("metrical_strength", 0.5)
        syncopation_index = features.get("syncopation_index", 0.0)
        rhythm_regularity = features.get("rhythm_regularity", 0.5)
        off_beat_ratio = features.get("off_beat_ratio", 0.0)
        downbeat_strength = features.get("downbeat_strength", 0.0)
        
        # Define thresholds for categories
        # These thresholds should be tuned based on actual analysis of MIDI files
        
        # Clear & Steady Beat: high metrical strength, low syncopation, high regularity
        if (metrical_strength > 0.7 and 
            syncopation_index < 0.3 and 
            rhythm_regularity > 0.7 and
            downbeat_strength > 0.2):
            return RhythmicCharacter.CLEAR_STEADY.value
            
        # Groovy & Syncopated: medium-high syncopation, medium metrical strength
        elif (syncopation_index > 0.4 and 
              off_beat_ratio > 0.3 and
              metrical_strength > 0.4):
            return RhythmicCharacter.GROOVY_SYNCOPATED.value
            
        # Smooth & Flowing: high regularity, medium-low note density, medium syncopation
        elif (rhythm_regularity > 0.6 and 
              features.get("note_density", 0) < 4.0 and
              syncopation_index < 0.4):
            return RhythmicCharacter.SMOOTH_FLOWING.value
            
        # Default to Moderately Rhythmic
        else:
            return RhythmicCharacter.MODERATELY_RHYTHMIC.value
            
    def _determine_genre(self, features: Dict) -> str:
        """
        Attempt to determine the musical genre based on features.
        
        This is a simplified rule-based approach and would ideally be replaced
        with a trained classifier in a production system.
        
        Args:
            features: Dictionary of features extracted from MIDI file
            
        Returns:
            String representing the genre category
        """
        # Note: This is a simplistic approach for demonstration purposes.
        # In reality, genre classification is complex and would require
        # a more sophisticated model, likely a neural network or ensemble classifier.
        
        # Extract relevant features
        note_density = features.get("note_density", 0)
        metrical_strength = features.get("metrical_strength", 0.5)
        syncopation_index = features.get("syncopation_index", 0.0)
        pitch_range = features.get("pitch_range", 60)
        
        # Simple rule-based classification
        # Classical often has high note density and wide pitch range
        if note_density > 5.0 and pitch_range > 50:
            return GenreCategory.CLASSICAL.value
            
        # Jazz typically has high syncopation and moderate-high note density
        elif syncopation_index > 0.5 and note_density > 3.0:
            return GenreCategory.JAZZ.value
            
        # Electronic often has very regular beats and moderate note density
        elif metrical_strength > 0.8 and 2.0 < note_density < 5.0:
            return GenreCategory.ELECTRONIC.value
            
        # Pop tends to have medium metrical strength and moderate note density
        elif 0.6 < metrical_strength < 0.8 and 2.0 < note_density < 4.0:
            return GenreCategory.POP.value
            
        # Rock often has strong beats but moderate syncopation
        elif metrical_strength > 0.7 and 0.2 < syncopation_index < 0.4:
            return GenreCategory.ROCK.value
            
        # Folk often has lower note density and moderate metrical strength
        elif note_density < 3.0 and 0.5 < metrical_strength < 0.7:
            return GenreCategory.FOLK.value
            
        # Default to "Other" if no clear pattern emerges
        else:
            return GenreCategory.OTHER.value
            
    def _determine_mood(self, features: Dict) -> str:
        """
        Determine the mood/style of a MIDI file based on its features.
        
        Args:
            features: Dictionary of features extracted from MIDI file
            
        Returns:
            String representing the mood category
        """
        # Extract relevant features with default values
        emotional_intensity = features.get("emotional_intensity", 0.5)
        energetic_factor = features.get("energetic_factor", 0.5)
        brightness_factor = features.get("brightness_factor", 0.5)
        tempo = features.get("original_tempo", 120)
        rhythm_regularity = features.get("rhythm_regularity", 0.5)
        
        # Determine mood based on a combination of factors
        
        # Energetic: high energy, high tempo, often higher intensity
        if energetic_factor > 0.7 and tempo > 120:
            mood = MoodCategory.ENERGETIC.value
        
        # Relaxed: lower energy, smoother rhythms, more regular
        elif energetic_factor < 0.4 and rhythm_regularity > 0.6:
            mood = MoodCategory.RELAXED.value
        
        # Uplifting: moderate-high energy, brighter character
        elif 0.5 < energetic_factor < 0.8 and brightness_factor > 0.6:
            mood = MoodCategory.UPLIFTING.value
        
        # Melancholic: lower brightness, moderate intensity
        elif brightness_factor < 0.4 and 0.3 < emotional_intensity < 0.6:
            mood = MoodCategory.MELANCHOLIC.value
        
        # Cheerful: high brightness, moderate energy
        elif brightness_factor > 0.7 and 0.4 < energetic_factor < 0.7:
            mood = MoodCategory.CHEERFUL.value
        
        # Peaceful: very low energy, high regularity
        elif energetic_factor < 0.3 and rhythm_regularity > 0.7:
            mood = MoodCategory.PEACEFUL.value
        
        # Intense: high emotional intensity, regardless of brightness
        elif emotional_intensity > 0.7:
            mood = MoodCategory.INTENSE.value
        
        # Chill: moderate-low energy, moderate brightness
        elif energetic_factor < 0.5 and 0.4 < brightness_factor < 0.7:
            mood = MoodCategory.CHILL.value
        
        # Default to "Relaxed" if no clear pattern emerges
        else:
            mood = MoodCategory.RELAXED.value
        
        # Update rhythmic character based on mood if appropriate
        features["suggested_rhythmic_style"] = self._map_mood_to_rhythmic_style(mood)
            
        return mood
    
    def _map_mood_to_rhythmic_style(self, mood: str) -> str:
        """
        Map a mood to an appropriate rhythmic style.
        
        This provides a suggested rhythmic style based on the mood, which can be
        used in the music selection interface for better filtering.
        
        Args:
            mood: String representing the mood category
            
        Returns:
            String representing the suggested rhythmic style
        """
        # Map moods to appropriate rhythmic styles
        mood_to_style = {
            MoodCategory.ENERGETIC.value: RhythmicCharacter.GROOVY_SYNCOPATED.value,
            MoodCategory.INTENSE.value: RhythmicCharacter.GROOVY_SYNCOPATED.value,
            MoodCategory.CHEERFUL.value: RhythmicCharacter.CLEAR_STEADY.value,
            MoodCategory.UPLIFTING.value: RhythmicCharacter.CLEAR_STEADY.value,
            MoodCategory.RELAXED.value: RhythmicCharacter.SMOOTH_FLOWING.value,
            MoodCategory.PEACEFUL.value: RhythmicCharacter.SMOOTH_FLOWING.value,
            MoodCategory.MELANCHOLIC.value: RhythmicCharacter.SMOOTH_FLOWING.value,
            MoodCategory.CHILL.value: RhythmicCharacter.MODERATELY_RHYTHMIC.value
        }
        
        return mood_to_style.get(mood, RhythmicCharacter.MODERATELY_RHYTHMIC.value)
            
    def batch_categorize_files(self, file_paths: List[Union[str, Path]]) -> List[Dict]:
        """
        Categorize multiple MIDI files in batch.
        
        Args:
            file_paths: List of paths to MIDI files
            
        Returns:
            List of dictionaries containing assigned categories and features
        """
        results = []
        
        for file_path in file_paths:
            metadata = self.categorize_file(file_path)
            results.append(metadata)
            
        return results
        
    def save_categories_to_json(self, file_path: Union[str, Path], 
                               categories: Optional[List[Dict]] = None) -> bool:
        """
        Save categorization results to a JSON file.
        
        Args:
            file_path: Path to save the JSON file
            categories: Optional list of categories to save (uses stored categories if None)
            
        Returns:
            True if the file was saved successfully, False otherwise
        """
        try:
            if categories is None:
                categories = [{"filePath": "unknown", "tags": self.categories}]
                
            with open(file_path, 'w') as f:
                json.dump(categories, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving categories to JSON: {e}")
            return False 