# Music Analysis Workflow Diagram

The following diagram illustrates the complete workflow of music analysis in the NeuroApp_RAS system, from dataset processing to music playback during gait rehabilitation.

```mermaid
graph TD
    %% Define nodes
    Dataset[MIDI Dataset] --> DatasetManager
    
    subgraph "Preprocessing Phase - Offline"
        DatasetManager[Dataset Manager] --> |For each MIDI file| FeatureExtractor
        FeatureExtractor[Feature Extractor] --> |Extract rhythm features| Features[Feature Set]
        Features --> Categorizer[MIDI Categorizer]
        Categorizer --> |Assign tags & categories| Metadata[Metadata Catalog]
        Metadata --> |Store| MetadataDB[(Metadata JSON)]
    end

    subgraph "User Selection Phase - UI"
        PatientProfile[Patient Profile] --> |Informs selection| MusicSelection
        MusicSelection[Music Selection UI] --> |Load available options| MetadataDB
        MusicSelection --> |User selects| GenreFilter[Genre Filter]
        MusicSelection --> |User selects| RhythmFilter[Rhythm Character Filter]
        GenreFilter --> |Filter| FilteredResults
        RhythmFilter --> |Filter| FilteredResults[Filtered Music Options]
        FilteredResults --> |User chooses| SelectedMIDI[Selected MIDI File]
    end

    subgraph "Playback Phase - Real-time"
        SelectedMIDI --> MusicProcessor[Music Processor]
        GaitAnalysis[Gait Analysis] --> |Current cadence| TempoAdjustment[Tempo Adjustment]
        TempoAdjustment --> MusicProcessor
        MusicProcessor --> |Audio output| AudioPlayback[Audio Playback]
        MusicProcessor --> |Sync| MetronomeBeats[Metronome Beats]
    end

    subgraph "Analysis Phase - Optional"
        SelectedMIDI --> |User requests analysis| VisualizationButton[Visualize Button]
        VisualizationButton --> |Opens| VisualizationWindow[Rhythm Visualization Window]
        VisualizationWindow --> |Displays| PianoRoll[Piano Roll]
        VisualizationWindow --> |Displays| BeatHistogram[Beat Histogram]
        VisualizationWindow --> |Displays| RhythmMetrics[Rhythm Metrics]
        VisualizationWindow --> |Optional| CircularPlot[Circular Rhythm Plot]
    end

    %% Define relationships between subgraphs
    MetadataDB --> |Provides music options| MusicSelection
    SelectedMIDI --> |Real-time playback| MusicProcessor
```

## User Interface Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as RAS Rehab UI
    participant DM as DatasetManager
    participant MP as MusicProcessor
    participant GA as GaitAnalysis
    participant V as Visualization

    U->>UI: Launch RAS Rehab Mode
    UI->>DM: Request music categories
    DM->>UI: Return genres & rhythmic characters
    UI->>U: Display music selection options
    
    U->>UI: Select genre (e.g., "Pop")
    U->>UI: Select rhythmic character (e.g., "Clear & Steady")
    UI->>DM: Query matching music
    DM->>UI: Return matching MIDI files
    UI->>U: Display matching music options
    
    U->>UI: Select specific music
    UI->>MP: Load selected MIDI file
    UI->>GA: Start gait monitoring
    GA->>MP: Send real-time cadence
    MP->>MP: Adjust tempo to match cadence
    MP->>U: Play synchronized music
    
    U->>UI: Press "Analyze Rhythm" button
    UI->>V: Open visualization window
    V->>U: Display rhythm analysis visualizations
``` 