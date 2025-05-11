#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rhythm Visualization

This module provides functionality for visualizing rhythm patterns and features
extracted from MIDI files.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

from .midi_feature_extractor import MidiFeatureExtractor
from ..music_processing.midi_parser import MidiEventType


def create_rhythm_visualization(midi_file_path: Union[str, Path],
                               feature_extractor: Optional[MidiFeatureExtractor] = None) -> Figure:
    """
    Create a comprehensive rhythm visualization for a MIDI file.
    
    Args:
        midi_file_path: Path to the MIDI file
        feature_extractor: Optional existing MidiFeatureExtractor instance
        
    Returns:
        Matplotlib Figure containing rhythm visualizations
    """
    # Create or use feature extractor
    extractor = feature_extractor if feature_extractor else MidiFeatureExtractor()
    
    # Load MIDI file if not already loaded
    if not feature_extractor or not feature_extractor.features:
        success = extractor.load_file(midi_file_path)
        if not success:
            raise ValueError(f"Failed to load MIDI file: {midi_file_path}")
            
        extractor.extract_all_features()
        
    # Create figure with three subplots, optimized with no title
    fig = plt.figure(figsize=(14, 18))  # Reduced height from 20 to 18 since we removed the title
    
    # Remove the main title that was causing overlap
    # Instead, add filename info as a property that can be accessed by the UI
    fig.filename = Path(midi_file_path).name
    
    # Use gridspec for more control over subplot placement
    from matplotlib.gridspec import GridSpec
    
    # Create a grid with larger vertical gaps between subplots
    # Define 3 rows with different heights - rhythm metrics needs more vertical space for explanations
    gs = GridSpec(3, 1, height_ratios=[1, 1, 1.5], figure=fig, hspace=0.4)  # Reduced hspace from 0.5 to 0.4
    
    # Add overall rhythm pattern visualization
    ax1 = fig.add_subplot(gs[0])
    create_overall_rhythm_pattern(extractor, ax1)
    
    # Add beat histogram
    ax2 = fig.add_subplot(gs[1])
    create_beat_histogram(extractor.features, ax2)
    
    # Add rhythm metrics visualization - needs more space for explanation text
    ax3 = fig.add_subplot(gs[2])
    create_rhythm_metrics_chart(extractor.features, ax3)
    
    # Add proper figure padding to ensure nothing gets cut off
    plt.subplots_adjust(top=0.99, bottom=0.05, left=0.1, right=0.9, hspace=0.4)  # Increased top margin from 0.98 to 0.99
    
    return fig


def create_piano_roll(feature_extractor: MidiFeatureExtractor, ax: Optional[plt.Axes] = None) -> plt.Axes:
    """
    Create a piano roll visualization with beat markers.
    
    Args:
        feature_extractor: MidiFeatureExtractor instance with loaded MIDI data
        ax: Optional matplotlib Axes to plot on
        
    Returns:
        Matplotlib Axes containing the piano roll visualization
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))
        
    # Extract note events and beat positions
    midi_parser = feature_extractor.midi_parser
    note_events = [event for event in midi_parser.events 
                  if event.event_type == 1]  # NOTE_ON events
    beat_positions = midi_parser.beat_positions
    
    # Extract pitch and time information
    times = []
    pitches = []
    durations = []
    velocities = []
    
    for i, event in enumerate(note_events):
        if hasattr(event.message, 'note'):
            pitch = event.message.note
        elif hasattr(event.message, 'dict') and 'note' in event.message.dict():
            pitch = event.message.dict()['note']
        else:
            continue
            
        # Get note velocity
        if hasattr(event.message, 'velocity'):
            velocity = event.message.velocity
        elif hasattr(event.message, 'dict') and 'velocity' in event.message.dict():
            velocity = event.message.dict()['velocity']
        else:
            velocity = 64  # Default velocity
            
        # Find corresponding NOTE_OFF event to determine duration
        note_off_time = None
        for off_event in midi_parser.events[i+1:]:
            if off_event.event_type == 2:  # NOTE_OFF event
                try:
                    off_pitch = None
                    if hasattr(off_event.message, 'note'):
                        off_pitch = off_event.message.note
                    elif hasattr(off_event.message, 'dict') and 'note' in off_event.message.dict():
                        off_pitch = off_event.message.dict()['note']
                        
                    if off_pitch == pitch:
                        note_off_time = off_event.time
                        break
                except Exception:
                    continue
                    
        if note_off_time is None:
            # If no NOTE_OFF found, assume short duration
            duration = 0.25
        else:
            duration = note_off_time - event.time
            
        times.append(event.time)
        pitches.append(pitch)
        durations.append(duration)
        velocities.append(velocity / 127.0)  # Normalize velocity
        
    # Plot piano roll
    if times:
        scatter = ax.scatter(times, pitches, c='blue', alpha=0.6, 
                          s=[max(20, d * 100) for d in durations])
                          
        # Add horizontal lines for octave boundaries
        for octave in range(11):
            pitch = octave * 12
            if pitch >= min(pitches) and pitch <= max(pitches):
                ax.axhline(y=pitch, color='gray', linestyle='--', alpha=0.3)
                
        # Add vertical lines for beats
        if beat_positions:
            for beat_time, _, is_downbeat in beat_positions:
                if is_downbeat:
                    ax.axvline(x=beat_time, color='red', linestyle='-', alpha=0.3)
                else:
                    ax.axvline(x=beat_time, color='gray', linestyle='-', alpha=0.2)
                    
        # Set axis labels and limits
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('MIDI Pitch')
        ax.set_title('Piano Roll with Beat Markers')
        
        # Set y-axis limits with some padding
        y_min, y_max = min(pitches), max(pitches)
        y_range = y_max - y_min
        ax.set_ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)
        
        # Set x-axis limits
        ax.set_xlim(0, midi_parser.midi_length)
        
    else:
        ax.text(0.5, 0.5, "No note events found", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes)
               
    return ax


def create_beat_histogram(features: Dict, ax: Optional[plt.Axes] = None) -> plt.Axes:
    """
    Create a beat histogram visualization.
    
    Args:
        features: Dictionary of features extracted from MIDI file
        ax: Optional matplotlib Axes to plot on
        
    Returns:
        Matplotlib Axes containing the beat histogram visualization
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 3))
        
    # Get beat histogram
    beat_histogram = features.get('beat_histogram', [])
    
    if not beat_histogram:
        ax.text(0.5, 0.5, "No beat histogram data available", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes)
        ax.set_title('Beat Distribution Histogram')
        return ax
        
    # Number of bins in histogram
    bins = len(beat_histogram)
    
    # Create bin labels
    if bins == 16:  # 16th note resolution
        bin_labels = ['1', '', '', '', '2', '', '', '', '3', '', '', '', '4', '', '', '']
    elif bins == 8:  # 8th note resolution
        bin_labels = ['1', '', '2', '', '3', '', '4', '']
    elif bins == 4:  # Quarter note resolution
        bin_labels = ['1', '2', '3', '4']
    else:
        bin_labels = [str(i+1) for i in range(bins)]
        
    # Plot histogram as bars
    bar_positions = np.arange(bins)
    bars = ax.bar(bar_positions, beat_histogram, width=0.8, color='skyblue', edgecolor='blue')
    
    # Highlight the downbeat
    if bins > 0:
        bars[0].set_color('navy')
        
    # Add beat strength labels for significant beats
    threshold = 0.1  # Only label beats with strength above threshold
    for i, strength in enumerate(beat_histogram):
        if strength >= threshold:
            ax.text(i, strength + 0.01, f'{strength:.2f}', 
                   horizontalalignment='center', verticalalignment='bottom',
                   fontsize=8)
                   
    # Set axis labels and title
    ax.set_xlabel('Beat Position')
    ax.set_ylabel('Normalized Strength')
    ax.set_title('Beat Distribution Histogram')
    
    # Set x-tick labels
    ax.set_xticks(bar_positions)
    ax.set_xticklabels(bin_labels)
    
    # Add grid for easier reading
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Set y-axis limits with some padding
    ax.set_ylim(0, max(beat_histogram) * 1.2)
    
    return ax


def create_rhythm_metrics_chart(features: Dict, ax: Optional[plt.Axes] = None, show_explanation: bool = False) -> plt.Axes:
    """
    Create a visualization of rhythm metrics.
    
    Args:
        features: Dictionary of features extracted from MIDI file
        ax: Optional matplotlib Axes to plot on
        show_explanation: Whether to show explanation text (default: False)
        
    Returns:
        Matplotlib Axes containing the rhythm metrics visualization
    """
    standalone_mode = ax is None
    
    if standalone_mode:
        fig, ax = plt.subplots(figsize=(10, 6))  # Increase height for explanations
    else:
        fig = ax.figure
        
    # Extract rhythm metrics
    metrics = [
        ('Metrical Strength', features.get('metrical_strength', 0)),
        ('Rhythm Regularity', features.get('rhythm_regularity', 0)),
        ('Downbeat Strength', features.get('downbeat_strength', 0)),
        ('Syncopation Index', features.get('syncopation_index', 0)),
        ('Off-Beat Ratio', features.get('off_beat_ratio', 0))
    ]
    
    # Sort metrics by value for better visualization
    metrics.sort(key=lambda x: x[1], reverse=True)
    
    # Extract names and values
    names = [m[0] for m in metrics]
    values = [m[1] for m in metrics]
    
    # Create horizontal bar chart
    bars = ax.barh(names, values, color='green', alpha=0.7)
    
    # Add value labels
    for i, v in enumerate(values):
        ax.text(max(v + 0.01, 0.05), i, f'{v:.2f}', 
               verticalalignment='center')
               
    # Set axis limits and title
    ax.set_xlim(0, 1)
    ax.set_title('Rhythm Metrics (0-1 scale)')
    
    # Add grid for easier reading
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Only add explanations if requested
    if show_explanation:
        # Add explanations
        explanations = {
            'Metrical Strength': 'How well notes align with the beat grid (higher = more aligned)',
            'Rhythm Regularity': 'Consistency of rhythmic patterns (higher = more regular)',
            'Downbeat Strength': 'Emphasis on the first beat of a bar (higher = stronger downbeats)',
            'Syncopation Index': 'Prevalence of unexpected note placements (higher = more syncopated)',
            'Off-Beat Ratio': 'Proportion of notes occurring between beats (higher = more off-beat notes)'
        }
        
        # Create explanation text
        explanation_text = '\n'.join([f"{k}: {explanations.get(k, '')}" for k, _ in metrics])
        
        # Different positioning depending on whether this is standalone or part of a larger figure
        if standalone_mode:
            # In standalone mode, we have more control over the figure
            # Add explanations as a figure text at the bottom
            fig.text(0.5, 0.01, explanation_text, 
                    fontsize=9,
                    ha='center',
                    va='bottom',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.4))
            
            # Adjust figure to make room for the explanation
            fig.subplots_adjust(bottom=0.25)
        else:
            # When part of a larger figure, use a more compact approach
            # Add explanations directly to the axis with a smaller fontsize
            ax.text(0.5, -0.15, explanation_text, 
                transform=ax.transAxes,
                fontsize=8,
                ha='center',
                va='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.4))
    
    return ax


def create_circular_rhythm_plot(features: Dict, ax: Optional[plt.Axes] = None, show_explanation: bool = False) -> plt.Axes:
    """
    Create a circular plot visualizing rhythm patterns.
    
    Args:
        features: Dictionary of features extracted from MIDI file
        ax: Optional matplotlib Axes to plot on
        show_explanation: Whether to show explanation text (default: False)
        
    Returns:
        Matplotlib Axes containing the circular rhythm visualization
    """
    standalone_mode = ax is None
    
    if standalone_mode:
        # Create a figure with two subplots side by side
        fig, (ax, text_ax) = plt.subplots(1, 2, figsize=(12, 6), 
                                        gridspec_kw={'width_ratios': [1, 1]},
                                        subplot_kw={'polar': True})
        text_ax.axis('off')
    else:
        # Get the current figure and check if it has a suitable layout
        fig = ax.figure
        
        # Try to find or create text_ax for explanations, but only if we need it
        text_ax = None
        if show_explanation:
            # Try to find or create text_ax for explanations
            if len(fig.axes) > 1 and fig.axes[1] != ax:
                # Use the second subplot if available
                text_ax = fig.axes[1]
                if not hasattr(text_ax, '_is_setup_for_circular_plot'):
                    text_ax.clear()
                    text_ax.axis('off')
                    text_ax._is_setup_for_circular_plot = True
            else:
                # Create a second axes if needed for text
                from matplotlib.gridspec import GridSpec
                gs = GridSpec(1, 2, width_ratios=[1, 1], figure=fig)
                
                # Save the original position
                original_pos = ax.get_position()
                
                # Adjust the main plot position
                ax.set_position(gs[0].get_position(fig))
                
                # Create the text axes
                text_ax = fig.add_subplot(gs[1])
                text_ax.axis('off')
                text_ax._is_setup_for_circular_plot = True
    
    # Extract beat pattern
    beat_pattern = features.get('beat_pattern', {})
    if not beat_pattern:
        # Create some default data
        beat_pattern = {
            '1': 1.0, '1.5': 0.2, '2': 0.7, '2.5': 0.3,
            '3': 0.8, '3.5': 0.2, '4': 0.6, '4.5': 0.3
        }
    
    # Convert to arrays for plotting
    beat_positions = []
    beat_strengths = []
    
    # Get time signature for proper angle mapping
    time_sig_num = features.get('time_sig_num', 4)
    beat_fractions = []
    
    for pos_str, strength in beat_pattern.items():
        try:
            # Handle decimal positions (e.g., "1.5")
            pos = float(pos_str)
            beat_positions.append(pos)
            beat_strengths.append(strength)
            
            # Calculate beat fraction (0-1 range for full measure)
            beat_fraction = (pos - 1) / time_sig_num
            beat_fractions.append(beat_fraction)
        except ValueError:
            continue
    
    # Convert beat fractions to angles (0-2π)
    angles = [fraction * 2 * np.pi for fraction in beat_fractions]
    
    # Ensure we have data to plot
    if not angles:
        angles = np.linspace(0, 2*np.pi, 8, endpoint=False)
        beat_strengths = [0.5] * 8
        beat_positions = [i+1 for i in range(8)]
    
    # Create circular plot
    ax.plot(angles, beat_strengths, color='blue', linewidth=2)
    ax.fill(angles, beat_strengths, alpha=0.3, color='skyblue')
    
    # Add radial grid
    ax.set_rgrids([0.25, 0.5, 0.75, 1.0], angle=0, labels=['0.25', '0.5', '0.75', '1.0'])
    
    # Add circular grid
    ax.set_thetagrids(
        np.arange(0, 360, 360/time_sig_num),
        labels=[str(i+1) for i in range(time_sig_num)]
    )
    
    # Set direction to clockwise and start from top
    ax.set_theta_direction(-1)
    ax.set_theta_offset(np.pi/2.0)
    
    # Set title and styling
    ax.set_title('Circular Rhythm Pattern', pad=15)
    ax.grid(True, alpha=0.3)
    
    # Add annotations for main beats
    for i, angle in enumerate(angles):
        if i % (len(angles) // 4) == 0:
            # Only annotate main beats (1, 2, 3, 4)
            beat_num = 1 + i // (len(angles) // 4)
            ax.annotate(f"{beat_num}", 
                       xy=(angle, ax.get_ylim()[1] * 1.05), 
                       xytext=(angle, ax.get_ylim()[1] * 1.15),
                       arrowprops=dict(arrowstyle="-"),
                       ha='center',
                       va='center',
                       fontsize=12,
                       fontweight='bold')
    
    # Only add explanation if requested
    if show_explanation and text_ax is not None:
        # Add rhythm characteristics explanation
        
        # Base explanation text with auto formatting for better rendering
        explanation_text = """
        Circular Rhythm Plot Explanation:
        
        • Each angle corresponds to a beat position within a measure
        • Distance from center shows rhythm intensity at that position
        • Main beats are labeled with numbers (1,2,3,4)
        
        Patterns Revealed:
        """
        
        # Add pattern analysis based on features
        if features.get('downbeat_strength', 0) > 0.7:
            explanation_text += "\n• Strong downbeat emphasis (beat 1)"
        elif features.get('downbeat_strength', 0) < 0.3:
            explanation_text += "\n• Weak downbeat emphasis (unusual pattern)"
        
        if features.get('off_beat_ratio', 0) > 0.5:
            explanation_text += "\n• Significant off-beat emphasis (syncopated)"
        else:
            explanation_text += "\n• Emphasis on primary beats (steady rhythm)"
        
        # Add rhythmic character based on features
        explanation_text += "\n\nRhythmic Character:"
        
        if features.get('syncopation_index', 0) > 0.7:
            explanation_text += "\n• Highly syncopated rhythm"
        elif features.get('syncopation_index', 0) > 0.4:
            explanation_text += "\n• Moderately syncopated rhythm"
        else:
            explanation_text += "\n• Straight rhythm with limited syncopation"
        
        if features.get('metrical_strength', 0) > 0.8:
            explanation_text += "\n• Very clear and regular meter"
        elif features.get('metrical_strength', 0) < 0.4:
            explanation_text += "\n• Irregular or fluid meter"
        
        # Add the explanation text to the text axes
        text_ax.text(0.05, 0.95, explanation_text,
                    transform=text_ax.transAxes,
                    fontsize=11,
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='#dddddd'))
    
    return ax


def create_overall_rhythm_pattern(feature_extractor: MidiFeatureExtractor, 
                                ax: Optional[plt.Axes] = None) -> plt.Axes:
    """
    Create a visualization showing the overall rhythm pattern across the entire piece.
    This shows how strong beats are distributed throughout the composition.
    
    Args:
        feature_extractor: MidiFeatureExtractor instance with loaded MIDI data
        ax: Optional matplotlib Axes to plot on
        
    Returns:
        Matplotlib Axes containing the overall rhythm pattern visualization
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 3))
        
    # Get beat positions and note events
    midi_parser = feature_extractor.midi_parser
    beats = midi_parser.beat_positions
    note_events = [event for event in midi_parser.events 
                  if event.event_type == MidiEventType.NOTE_ON]
    
    if not beats or not note_events:
        ax.text(0.5, 0.5, "No beat or note data available", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes)
        ax.set_title('Overall Rhythm Pattern')
        return ax
    
    # Total duration of the piece in seconds
    total_duration = midi_parser.midi_length
    
    # Create a density array to represent rhythm intensity over time
    # Use higher resolution for smoother visualization
    resolution = 1000  # points for visualization
    time_points = np.linspace(0, total_duration, resolution)
    rhythm_intensity = np.zeros(resolution)
    
    # Calculate event density at each time point
    # Use a gaussian kernel to smooth the distribution
    sigma = resolution / 300  # Width of the gaussian kernel
    
    # Process note events for intensity
    for event in note_events:
        # Get note velocity (loudness)
        velocity = 64  # Default velocity
        if hasattr(event.message, 'velocity'):
            velocity = event.message.velocity
        elif hasattr(event.message, 'dict') and 'velocity' in event.message.dict():
            velocity = event.message.dict()['velocity']
        
        # Calculate the event's position in the time array
        event_idx = int((event.time / total_duration) * (resolution - 1))
        if 0 <= event_idx < resolution:
            # Apply gaussian weighting around the event based on its velocity
            weight = velocity / 127.0  # Normalize velocity to 0-1
            
            # Create gaussian kernel around the event
            for i in range(resolution):
                dist = abs(i - event_idx)
                gaussian_value = weight * np.exp(-(dist**2) / (2 * sigma**2))
                rhythm_intensity[i] += gaussian_value
    
    # Normalize intensity to 0-1 range
    if np.max(rhythm_intensity) > 0:
        rhythm_intensity = rhythm_intensity / np.max(rhythm_intensity)
    
    # Create beat markers
    beat_times = [beat[0] for beat in beats]
    beat_positions = [(beat[0] / total_duration) * (resolution - 1) for beat in beats]
    beat_markers = np.zeros(resolution)
    
    # Mark beats with different heights based on measure position
    for i, (beat_time, beat_num, is_downbeat) in enumerate(beats):
        beat_idx = int((beat_time / total_duration) * (resolution - 1))
        if 0 <= beat_idx < resolution:
            # Downbeats (first beat of measure) are taller
            if is_downbeat:
                beat_markers[beat_idx] = 1.0
            else:
                beat_markers[beat_idx] = 0.7
    
    # Plot rhythm intensity
    ax.fill_between(time_points, rhythm_intensity, alpha=0.5, color='blue', 
                   label='Rhythm Intensity')
    
    # Plot beat markers
    for i, marker_val in enumerate(beat_markers):
        if marker_val > 0:
            if marker_val > 0.9:  # Downbeat
                ax.axvline(x=time_points[i], color='red', alpha=0.5, linewidth=1.5)
            else:  # Regular beat
                ax.axvline(x=time_points[i], color='gray', alpha=0.4, linewidth=1)
    
    # Add measure numbers at downbeats
    measure_count = 0
    for i, (beat_time, beat_num, is_downbeat) in enumerate(beats):
        if is_downbeat:
            # Place measure numbers at regular intervals to avoid clutter
            if measure_count % 4 == 0:  # Show every 4th measure number
                ax.text(beat_time, 1.05, str(measure_count + 1), 
                       horizontalalignment='center', verticalalignment='bottom',
                       fontsize=8, color='red')
            measure_count += 1
    
    # Set axis labels and title
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Rhythm Intensity')
    ax.set_title('Overall Rhythm Pattern')
    
    # Set axis limits
    ax.set_xlim(0, total_duration)
    ax.set_ylim(0, 1.15)  # Leave space for measure numbers
    
    # Add grid for easier reading
    ax.grid(True, alpha=0.3)
    
    return ax


def save_visualization(fig: Figure, output_path: Union[str, Path]) -> bool:
    """
    Save a visualization figure to a file.
    
    Args:
        fig: Matplotlib Figure to save
        output_path: Path to save the figure
        
    Returns:
        True if the figure was saved successfully, False otherwise
    """
    try:
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error saving visualization: {e}")
        return False


def get_visualization_as_qt_widget(fig: Figure) -> FigureCanvasQTAgg:
    """
    Convert a matplotlib figure to a Qt widget for embedding in a PyQt interface.
    
    Args:
        fig: Matplotlib Figure
        
    Returns:
        QWidget containing the figure canvas
    """
    return FigureCanvasQTAgg(fig) 