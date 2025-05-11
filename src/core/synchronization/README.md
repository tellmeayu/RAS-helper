# Synchronization Module

## Overview

The Synchronization Module provides a user-controlled system for synchronizing gait analysis with rhythmic auditory stimulation (RAS). It implements the SLICE (Stepwise Limit Cycle Entrainment) protocol for gait rehabilitation, allowing therapists to:

1. Measure a patient's current gait parameters
2. Introduce rhythmic cues matching the patient's natural cadence
3. Gradually adapt the rhythm toward therapeutic targets
4. Collect and analyze session data for clinical evaluation

The module is designed with a user-confirmation workflow where all gait measurements must be confirmed by a clinician before being used for music tempo control, ensuring professional oversight of the therapeutic process.

## Components

The module consists of several key components:

### GaitMusicSynchronizer

The central component that manages the synchronization between gait parameters and music playback. It implements a user-controlled workflow:

1. Receives gait data from the gait analyzer
2. Presents the data to the user for confirmation/modification
3. Applies confirmed tempo to music playback

```python
# Example initialization
synchronizer = GaitMusicSynchronizer(
    gait_analyzer=gait_analyzer,
    music_processor=music_processor,
    min_cadence=60.0,
    max_cadence=180.0,
    update_interval=0.5
)
```

### SLICEProtocol

Implements the clinical SLICE protocol for rhythmic auditory stimulation. SLICE is based on the concept that biological movement systems have preferred frequencies (limit cycles) at which they operate optimally. The protocol:

1. Starts at the patient's current natural frequency
2. Stabilizes movement patterns at this frequency
3. Gradually entrains new, increasingly optimal frequencies
4. Systematically fades cues to promote independent motor control

```python
# The protocol phases
EntrainmentPhase.BASELINE         # Assessment of natural gait parameters
EntrainmentPhase.INTRODUCE_CUEING # Initial introduction of rhythmic cues
EntrainmentPhase.CALIBRATE        # Gradual adaptation toward target
EntrainmentPhase.LOTS_OF_CUEING   # High intensity rhythmic stimulation
EntrainmentPhase.STABLE_CUES      # Stabilization at achieved cadence
EntrainmentPhase.ENHANCE          # Progressive improvement beyond initial targets
```

### SynchronizationData

Handles data collection and storage for therapeutic evaluation of RAS sessions. Features:

- Records all gait parameters and synchronization states
- Tracks protocol transitions and events
- Provides metrics and summary statistics
- Saves session data for later analysis

## Workflow

The typical workflow for using the synchronization module follows these steps:

1. **Initialization**: Create the necessary components and configure the synchronizer
2. **Baseline Assessment**: Collect baseline gait parameters in the BASELINE phase
3. **Introduction of Cueing**: Introduce rhythmic cueing matched to the patient's current cadence
4. **Calibration and Adaptation**: Gradually adapt the tempo toward therapeutic targets
5. **Stabilization**: Stabilize movement at the target cadence
6. **Data Analysis**: Analyze session data to evaluate therapeutic progress

## Usage Example

Below is a simplified example of using the synchronization module:

```python
# Initialize components
gait_analyzer = GaitAnalyzer()
music_processor = MusicProcessor()

# Create synchronizer
synchronizer = GaitMusicSynchronizer(
    gait_analyzer=gait_analyzer,
    music_processor=music_processor
)

# Create data collector
data_collector = SynchronizationData(
    session_id="patient_001_session_1",
    patient_id="patient_001"
)

# Set protocol to baseline phase
synchronizer.protocol.set_phase(EntrainmentPhase.BASELINE)

# Get current gait data
gait_data = gait_analyzer.get_current_gait_parameters()

# Update synchronizer with gait data (pending confirmation)
synchronizer.update_gait_data(gait_data)

# Confirm gait data (optionally with modifications)
synchronizer.confirm_gait_data(modified_cadence=110.0)

# Start music playback with confirmed tempo
synchronizer.start_playback("path/to/midi_file.mid")

# Adjust tempo (e.g., during CALIBRATE phase)
synchronizer.adjust_tempo_percentage(5.0)  # Increase by 5%

# Record data
state = synchronizer.get_current_state()
data_collector.update(gait_data, state)

# Save session data
data_collector.save_session_data()
```

## Key Features

- **User Confirmation Model**: All gait data must be confirmed by the user before affecting music tempo
- **Tempo Adjustment**: Multiple methods for precise control over music tempo
- **Protocol Phases**: Support for all phases of the SLICE protocol
- **Data Collection**: Comprehensive data collection for clinical evaluation
- **Flexible Configuration**: Configurable parameters for different therapeutic needs

## Notes for Developers

- Cadence values are stored as floats for precision in gait parameters
- Tempo values are converted to integers when sent to the MIDI music processor
- The synchronizer provides callback hooks for UI integration:
  - `on_gait_data_available`: Called when new gait data is available
  - `on_tempo_change`: Called when the tempo changes
  - `on_sync_state_change`: Called when the synchronization state changes

## Advanced Usage

For more advanced usage examples, see the `sync_example.py` script, which demonstrates:

1. Automated simulation of a full SLICE protocol session
2. Interactive user-controlled session with keyboard commands
3. Integration with data collection and analysis

## References

For more information on the SLICE protocol and RAS therapy, see:
- [RAS_Neurological_Mechanisms_and_Protocols.md](../../docs/references/RAS_Neurological_Mechanisms_and_Protocols.md) 