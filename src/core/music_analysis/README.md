# Music Analysis Module

This module provides functionality for analyzing, categorizing, and visualizing MIDI files for the NeuroApp_RAS project, with a focus on rhythm characterization for gait rehabilitation.

## Overview

The Music Analysis Module provides functionality for:

1. Extracting rhythmic and musical features from MIDI files
2. Categorizing MIDI files based on their musical characteristics
3. Managing MIDI datasets and metadata
4. Visualizing rhythm patterns and features

## Components

The module consists of the following components:

### MidiFeatureExtractor

The `MidiFeatureExtractor` class extracts various features from MIDI files, including:

- Basic MIDI information (tempo, time signature, etc.)
- Rhythm features:
  - Inter-Onset Interval (IOI) statistics
  - Note density
  - Rhythm regularity
  - Beat histogram
  - Metrical strength
  - Syncopation measures

Example usage:

```python
from core.music_analysis import MidiFeatureExtractor

# Create a feature extractor
extractor = MidiFeatureExtractor()

# Load and analyze a MIDI file
extractor.load_file("path/to/midi_file.mid")
features = extractor.extract_all_features()

# Access specific features
metrical_strength = features['metrical_strength']
syncopation_index = features['syncopation_index']
```

### MidiCategorizer

The `MidiCategorizer` class analyzes MIDI features to assign appropriate tags and categories:

- Rhythmic character (Clear & Steady Beat, Moderately Rhythmic, Groovy & Syncopated, Smooth & Flowing)
- Genre (Pop, Rock, Classical, Jazz, etc.)

Example usage:

```python
from core.music_analysis import MidiCategorizer

# Create a categorizer
categorizer = MidiCategorizer()

# Categorize a MIDI file
metadata = categorizer.categorize_file("path/to/midi_file.mid")

# Access categorization results
rhythmic_character = metadata['tags']['rhythmicCharacter']
genre = metadata['tags']['genre']
```

### DatasetManager

The `DatasetManager` class handles batch processing of MIDI datasets and metadata management:

- Processing entire MIDI datasets
- Generating and storing metadata
- Querying the dataset based on musical characteristics
- Computing dataset statistics

Example usage:

```python
from core.music_analysis import DatasetManager

# Create a dataset manager
manager = DatasetManager("path/to/midi_dataset")

# Process the dataset
manager.process_dataset(output_metadata_path="path/to/metadata.json")

# Query for specific music
matching_files = manager.query_midi_files(
    genre="Pop", 
    rhythmic_character="Clear & Steady Beat"
)

# Get dataset statistics
stats = manager.get_dataset_statistics()
```

### Rhythm Visualization

The module provides functions for visualizing rhythm patterns and features:

- Piano roll with beat markers
- Beat histogram
- Rhythm metrics chart
- Circular rhythm plot

Example usage:

```python
from core.music_analysis import create_rhythm_visualization

# Create visualization
fig = create_rhythm_visualization("path/to/midi_file.mid")

# Save to file
from core.music_analysis.rhythm_visualization import save_visualization
save_visualization(fig, "rhythm_analysis.png")
```

## Integration with NeuroApp_RAS

This module integrates with the existing NeuroApp_RAS system to provide enhanced music selection functionality for gait rehabilitation:

1. **Preprocessing Phase**:
   - The dataset manager processes all available MIDI files
   - Features are extracted and files are categorized
   - A metadata catalog is generated

2. **User Selection Phase**:
   - The RAS user interface displays musical options based on categorization
   - Users can select music by genre and rhythmic character

3. **Playback Phase**:
   - Selected music is played using the existing `MusicProcessor`
   - Tempo is automatically adjusted to match the patient's cadence

4. **Analysis Phase**:
   - Users can view detailed rhythm visualizations
   - This provides insights into the rhythm patterns of selected music

## Requirements

The module requires the following dependencies:

- numpy
- matplotlib
- PyQt5 (for visualization widgets)

## Platform Support

The Music Analysis Module is designed to work on all platforms supported by the NeuroApp_RAS project:

- macOS
- Windows
- Linux 