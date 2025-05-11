#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rhythm Analyzer Launcher

This module provides a separate process launcher for the MusicRhythmAnalysisWindow.
This completely avoids any window management issues when launched from dialogs.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path when imported
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def launch_analyzer_as_separate_process(file_path):
    """
    Launch the music rhythm analysis window as a completely separate process.
    
    This is the most reliable solution to window management issues, as it
    completely separates the window from the parent application process.
    
    Args:
        file_path: Path to the MIDI file to analyze, or None to launch without a file
    
    Returns:
        The subprocess.Popen object representing the launched process
    """
    # Get the Python executable path that's currently running
    python_executable = sys.executable
    
    # Get the project structure paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_dir)  # Parent of ui directory
    standalone_script = os.path.join(src_dir, "standalone_rhythm_analyzer.py")
    
    # Make sure the standalone script exists
    if not os.path.exists(standalone_script):
        raise FileNotFoundError(f"Could not find standalone script: {standalone_script}")
    
    # Check if a file path was provided
    if file_path is not None:
        # Make sure the MIDI file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Could not find MIDI file: {file_path}")
        
        # Launch the standalone script as a separate process with the file path
        process = subprocess.Popen([
            python_executable,
            standalone_script,
            file_path
        ])
    else:
        # Launch the standalone script as a separate process without a file path
        process = subprocess.Popen([
            python_executable,
            standalone_script
        ])
    
    return process


if __name__ == "__main__":
    # Example usage when run directly
    if len(sys.argv) > 1:
        midi_file = sys.argv[1]
        launch_analyzer_as_separate_process(midi_file)
    else:
        print("Usage: python rhythm_analyzer_launcher.py <midi_file_path>") 