# Music Processing Module

This module handles all MIDI playback and rhythmic auditory stimulation (RAS) functionality for the NeuroApp.

## Overview

The Music Processing Module provides functionality for:

1. Loading and playing MIDI files
2. Synchronizing music with metronome beats
3. Adjusting tempo based on gait analysis
4. Managing audio output through FluidSynth
5. Custom instrument assignment

## Usage

Basic usage of the MusicProcessor:

```python
from core.music_processing import MusicProcessor

# Create a music processor
processor = MusicProcessor(
    soundfont_path="/path/to/soundfont.sf2",
    metronome_enabled=True,
    midi_instrument=115  # Woodblock for metronome
)

# Load a MIDI file
processor.load_midi("/path/to/midi_file.mid")

# Play the MIDI file
processor.play()

# Stop playback
processor.stop()

# Release resources when done
processor.release()
```

## Customizing Instruments

The MIDI processing system can handle instrument assignment in two ways:

1. **MIDI File Program Changes**: If your MIDI file contains program change events, these will be used to set the instruments for each channel.

2. **Manual Channel Assignment**: If your MIDI file doesn't contain program changes (like the test MIDI file), you can manually set instruments for specific channels:

```python
# Set piano for melody (channel 0)
processor.set_channel_instrument(0, 0)  # Acoustic Grand Piano

# Set string instrument for accompaniment (channel 1)
processor.set_channel_instrument(1, 48)  # String Ensemble

# Set bass instrument (channel 2)
processor.set_channel_instrument(2, 32)  # Acoustic Bass
```

The module automatically applies default instruments to MIDI files without program changes:
- Channel 0: Acoustic Grand Piano (0)
- Channel 1: Acoustic Guitar (24)
- Channel 2: Acoustic Bass (32)
- Channel 3: String Ensemble (48)
- Channel 4: Flute (73)

Channel 15 is reserved for the metronome and should not be modified.

## General MIDI Instrument Reference

General MIDI instruments are grouped by families:

- Piano (0-7): Acoustic Grand Piano, Bright Piano, Electric Grand Piano, etc.
- Chromatic Percussion (8-15): Celesta, Glockenspiel, Music Box, etc.
- Organ (16-23): Hammond Organ, Church Organ, Reed Organ, etc.
- Guitar (24-31): Acoustic Guitar, Electric Guitar, etc.
- Bass (32-39): Acoustic Bass, Electric Bass, etc.
- Strings (40-47): Violin, Viola, Cello, etc.
- Ensemble (48-55): String Ensemble, Choir, Orchestra Hit, etc.
- Brass (56-63): Trumpet, Trombone, Tuba, etc.
- Reed (64-71): Soprano Sax, Alto Sax, Oboe, etc.
- Pipe (72-79): Flute, Recorder, Pan Flute, etc.
- Synth Lead (80-87): Square Wave, Saw Wave, Calliope, etc.
- Synth Pad (88-95): New Age Pad, Warm Pad, etc.
- Synth Effects (96-103): FX 1 (rain), FX 2 (soundtrack), etc.
- Ethnic (104-111): Sitar, Banjo, Shamisen, etc.
- Percussive (112-119): Tinkle Bell, Agogo, Steel Drums, etc.
- Sound Effects (120-127): Guitar Fret Noise, Breath Noise, Seashore, etc.

Channel 9 is always reserved for percussion in the General MIDI standard.

## Platform Specific Notes

The module automatically selects the appropriate audio driver based on your operating system:
- macOS: coreaudio
- Linux: pulseaudio
- Windows: dsound

## Troubleshooting

If you encounter issues with MIDI playback:

1. Ensure the SoundFont file exists and is accessible
2. Verify FluidSynth is properly installed on your system
3. Check that the MIDI file is valid and can be loaded
4. If you hear only the metronome but no instruments, use the `set_channel_instrument()` method to manually set instruments
5. Run the `test_sound()` method to verify audio output is working

For more examples, see the `src/examples/music_example.py` and `src/examples/midi_simple_test.py` files.