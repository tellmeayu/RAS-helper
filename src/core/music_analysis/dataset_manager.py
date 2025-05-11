#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIDI Dataset Manager

This module provides functionality for managing MIDI datasets.
"""

import os
import json
import glob
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path
import random

from .midi_categorizer import MidiCategorizer


class DatasetManager:
    """
    Class for managing MIDI datasets, including batch processing and metadata management.
    
    This class provides functionality for:
    1. Loading and organizing MIDI datasets
    2. Batch processing MIDI files to extract features and categorize them
    3. Generating and managing metadata for the dataset
    4. Querying the dataset based on musical characteristics
    """
    
    def __init__(self, dataset_path: Optional[Union[str, Path]] = None):
        """
        Initialize the dataset manager.
        
        Args:
            dataset_path: Optional path to the MIDI dataset directory
        """
        self.dataset_path = Path(dataset_path) if dataset_path else None
        self.categorizer = MidiCategorizer()
        self.metadata = []
        self.metadata_file_path = None
        
    def set_dataset_path(self, dataset_path: Union[str, Path]) -> None:
        """
        Set the path to the MIDI dataset.
        
        Args:
            dataset_path: Path to the MIDI dataset directory
        """
        self.dataset_path = Path(dataset_path)
        
    def load_metadata(self, metadata_path: Union[str, Path]) -> bool:
        """
        Load existing metadata from a JSON file.
        
        Args:
            metadata_path: Path to the metadata JSON file
            
        Returns:
            True if the metadata was loaded successfully, False otherwise
        """
        try:
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
                
            self.metadata_file_path = Path(metadata_path)
            return True
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return False
            
    def save_metadata(self, metadata_path: Optional[Union[str, Path]] = None) -> bool:
        """
        Save the current metadata to a JSON file.
        
        Args:
            metadata_path: Optional path to save the metadata (uses stored path if None)
            
        Returns:
            True if the metadata was saved successfully, False otherwise
        """
        path = metadata_path if metadata_path else self.metadata_file_path
        
        if not path:
            # If no path is specified and none is stored, create one in the dataset directory
            if self.dataset_path:
                path = self.dataset_path / "midi_metadata.json"
            else:
                print("Error: No metadata path specified")
                return False
                
        try:
            with open(path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
                
            self.metadata_file_path = Path(path)
            return True
        except Exception as e:
            print(f"Error saving metadata: {e}")
            return False
            
    def find_midi_files(self) -> List[Path]:
        """
        Find all MIDI files in the dataset directory.
        
        Returns:
            List of paths to MIDI files
        """
        if not self.dataset_path:
            raise ValueError("Dataset path not set")
            
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset directory not found: {self.dataset_path}")
            
        # Find all .mid and .midi files
        mid_files = list(self.dataset_path.glob("**/*.mid"))
        midi_files = list(self.dataset_path.glob("**/*.midi"))
        
        return mid_files + midi_files
        
    def process_dataset(self, 
                       output_metadata_path: Optional[Union[str, Path]] = None,
                       extract_features: bool = True,
                       categorize: bool = True) -> bool:
        """
        Process all MIDI files in the dataset, extracting features and categorizing.
        
        Args:
            output_metadata_path: Optional path to save the metadata
            extract_features: Whether to extract features from MIDI files
            categorize: Whether to categorize MIDI files based on features
            
        Returns:
            True if the dataset was processed successfully, False otherwise
        """
        if not self.dataset_path:
            print("Error: Dataset path not set")
            return False
            
        try:
            # Find all MIDI files
            midi_files = self.find_midi_files()
            
            if not midi_files:
                print("No MIDI files found in the dataset directory")
                return False
                
            print(f"Found {len(midi_files)} MIDI files in the dataset")
            
            # Process each file
            self.metadata = []
            for file_path in midi_files:
                try:
                    # Extract features and categorize
                    metadata = self.categorizer.categorize_file(file_path)
                    
                    # Make file path relative to dataset directory for portability
                    try:
                        rel_path = file_path.relative_to(self.dataset_path)
                        metadata["relativeFilePath"] = str(rel_path)
                    except ValueError:
                        # If the file is not within the dataset directory, use absolute path
                        metadata["relativeFilePath"] = str(file_path)
                        
                    self.metadata.append(metadata)
                    
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
                    continue
                    
            # Save the metadata
            if output_metadata_path:
                self.save_metadata(output_metadata_path)
            else:
                self.save_metadata(self.dataset_path / "midi_metadata.json")
                
            print(f"Processed {len(self.metadata)} MIDI files successfully")
            return True
            
        except Exception as e:
            print(f"Error processing dataset: {e}")
            return False
            
    def query_midi_files(self, 
                        genre: Optional[str] = None,
                        rhythmic_character: Optional[str] = None,
                        min_tempo: Optional[float] = None,
                        max_tempo: Optional[float] = None,
                        **kwargs) -> List[Dict]:
        """
        Query the dataset for MIDI files matching specified criteria.
        
        Args:
            genre: Optional genre filter
            rhythmic_character: Optional rhythmic character filter
            min_tempo: Optional minimum tempo filter
            max_tempo: Optional maximum tempo filter
            **kwargs: Additional filters for any metadata field
            
        Returns:
            List of metadata records for matching MIDI files
        """
        if not self.metadata:
            print("Warning: No metadata loaded. Load metadata first or process dataset.")
            return []
            
        results = self.metadata.copy()
        
        # Apply filters
        if genre:
            results = [r for r in results if r.get("tags", {}).get("genre") == genre]
            
        if rhythmic_character:
            results = [r for r in results if r.get("tags", {}).get("rhythmicCharacter") == rhythmic_character]
            
        if min_tempo is not None:
            results = [r for r in results if r.get("originalTempo", 0) >= min_tempo]
            
        if max_tempo is not None:
            results = [r for r in results if r.get("originalTempo", 0) <= max_tempo]
            
        # Apply any additional filters
        for key, value in kwargs.items():
            # For nested keys like "rhythmicFeatures.noteDensity"
            if "." in key:
                parent_key, child_key = key.split(".", 1)
                results = [r for r in results if r.get(parent_key, {}).get(child_key) == value]
            else:
                results = [r for r in results if r.get(key) == value]
                
        return results
        
    def get_unique_values(self, field: str) -> Set:
        """
        Get all unique values for a specific field in the metadata.
        
        Args:
            field: Field name (can be nested using dot notation, e.g., "tags.genre")
            
        Returns:
            Set of unique values for the field
        """
        if not self.metadata:
            return set()
            
        # For nested fields like "tags.genre"
        if "." in field:
            parent_key, child_key = field.split(".", 1)
            values = {r.get(parent_key, {}).get(child_key) for r in self.metadata if r.get(parent_key)}
        else:
            values = {r.get(field) for r in self.metadata}
            
        # Remove None values
        return {v for v in values if v is not None}
        
    def get_dataset_statistics(self) -> Dict:
        """
        Calculate statistics about the dataset.
        
        Returns:
            Dictionary containing dataset statistics
        """
        if not self.metadata:
            return {"file_count": 0}
            
        stats = {
            "file_count": len(self.metadata),
            "genre_distribution": {},
            "rhythmic_character_distribution": {},
            "average_tempo": 0.0,
        }
        
        # Calculate genre distribution
        genres = [r.get("tags", {}).get("genre") for r in self.metadata]
        genres = [g for g in genres if g is not None]
        
        for genre in set(genres):
            count = genres.count(genre)
            stats["genre_distribution"][genre] = {
                "count": count,
                "percentage": count / len(genres) * 100 if genres else 0
            }
            
        # Calculate rhythmic character distribution
        chars = [r.get("tags", {}).get("rhythmicCharacter") for r in self.metadata]
        chars = [c for c in chars if c is not None]
        
        for char in set(chars):
            count = chars.count(char)
            stats["rhythmic_character_distribution"][char] = {
                "count": count,
                "percentage": count / len(chars) * 100 if chars else 0
            }
            
        # Calculate average tempo
        tempos = [r.get("originalTempo") for r in self.metadata if r.get("originalTempo")]
        if tempos:
            stats["average_tempo"] = sum(tempos) / len(tempos)
            stats["min_tempo"] = min(tempos)
            stats["max_tempo"] = max(tempos)
            
        return stats
        
    def get_file_path(self, metadata_record: Dict) -> Path:
        """
        Get the full file path for a metadata record.
        
        Args:
            metadata_record: Metadata record from the dataset
            
        Returns:
            Path object for the MIDI file
        """
        if "relativeFilePath" in metadata_record and self.dataset_path:
            return self.dataset_path / metadata_record["relativeFilePath"]
        elif "filePath" in metadata_record:
            return Path(metadata_record["filePath"])
        else:
            raise ValueError("No file path in metadata record")
            
    def get_random_file(self, 
                       genre: Optional[str] = None,
                       rhythmic_character: Optional[str] = None,
                       **kwargs) -> Optional[Dict]:
        """
        Get a random MIDI file matching specified criteria.
        
        Args:
            genre: Optional genre filter
            rhythmic_character: Optional rhythmic character filter
            **kwargs: Additional filters
            
        Returns:
            Metadata record for a random matching MIDI file, or None if no match
        """
        matching_files = self.query_midi_files(
            genre=genre,
            rhythmic_character=rhythmic_character,
            **kwargs
        )
        
        if not matching_files:
            return None
            
        return random.choice(matching_files) 