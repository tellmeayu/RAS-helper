# RAS-helper Dashboard Modes

This document describes the three main operational modes of the RAS-helper dashboard and their specific functionalities.

## 1. Clinical Assessment Mode

**Purpose**: Detailed evaluation of patient gait, establishing baselines, and generating clinical reports.

### Key Components:

#### Clinical Assessment Controls
- **Assessment Protocol Selector**: Choose from standard protocols (Standard Gait, 6-Minute Walk, 10m Walk Test, Timed Up & Go)
- **Baseline Comparison Toggle**: Enable/disable comparison with baseline measurements
- **Assessment Duration**: Set the duration of the assessment session
- **Recording Controls**: Start/stop recording of assessment data
- **Notes Field**: Enter clinical observations during assessment

#### Detailed Metrics View
- **Temporal Parameters**: Cadence, step time, stance phase, swing phase percentages
- **Spatial Parameters**: Step length, stride length, step width measurements
- **Asymmetry Analysis**: Left/right comparison for key parameters
- **Export Options**: Generate CSV exports or clinical reports

#### Patient Information
- **Detailed Clinical Data**: Patient ID, medical record number, diagnosis
- **Assessment History**: Previous assessments, referring physician
- **Clinical Protocol**: Detailed assessment protocol information

### Workflow:
1. Select assessment protocol
2. Configure assessment parameters
3. Record assessment data
4. Review detailed metrics
5. Generate clinical report

## 2. Rehabilitation Training Mode

**Purpose**: Delivering RAS therapy to patients, with simplified controls and clear feedback.

### Key Components:

#### Rehabilitation Controls
- **Simplified Interface**: Large, easy-to-read elements designed for patient use
- **Status Display**: Clear indication of current training status
- **Simple Tempo Control**: Easy-to-adjust tempo slider with large display
- **Sound Selection**: Simple sound options appropriate for therapy
- **Large Control Buttons**: Oversized start/stop buttons for ease of use
- **Timer Display**: Prominent session timer

#### Progress Tracking View
- **Goals Progress**: Visual representation of progress toward therapy goals
- **Session Metrics**: Today's performance metrics
- **Weekly Progress**: Overview of weekly session completion
- **Achievements**: Motivational elements highlighting milestones
- **Motivational Feedback**: Encouraging messages based on progress

#### Patient Information
- **Simplified Patient View**: Basic patient information
- **Session Tracking**: Current session number and schedule
- **Goal Information**: Clear statement of therapy goals
- **Rehabilitation Protocol**: Simplified protocol information

### Workflow:
1. Review patient goals
2. Start training session with large buttons
3. Monitor progress in real-time
4. Complete session and review achievements
5. Schedule next session

## 3. Research Mode

**Purpose**: Advanced data collection, experimental protocol testing, and parameter manipulation.

### Key Components:

#### Advanced RAS Controls
- **Precise Tempo Control**: Fine-grained BPM adjustment with decimal precision
- **Algorithm Selection**: Multiple adaptation algorithms with parameter tuning
- **Parameter Controls**: Detailed adjustment of algorithm parameters (α, β, γ)
- **Advanced Audio Settings**: Detailed audio configuration options
- **Data Collection Settings**: Options for raw data recording and sampling rates

#### Raw Data View
- **Data Stream Display**: Real-time visualization of raw sensor data
- **Data Type Selection**: Filter between different data streams
- **Signal Processing**: Apply filters to incoming data
- **Visualization Tools**: Plot data in various formats
- **Export Options**: Export raw data for external analysis

#### Participant Information
- **Research-Focused Fields**: Participant ID, study information, group assignment
- **Trial Information**: Current trial number, protocol variation
- **Research Protocol**: Detailed experimental protocol parameters

### Workflow:
1. Configure experimental parameters
2. Set up data collection options
3. Run experiment with precise control
4. Monitor and filter raw data streams
5. Export data for further analysis

## Shared Components

All modes share these common elements:

- **Video Feed**: 16:9 aspect ratio video display (with mode-specific overlays)
- **Status Information**: System status indicators for camera, pose estimation, audio
- **Mode Selection**: Top bar selector to switch between modes
- **Settings Access**: Universal access to system settings 