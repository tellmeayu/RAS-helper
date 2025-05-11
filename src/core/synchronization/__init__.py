"""
Synchronization Module

This module handles the synchronization between gait parameters and auditory cues,
implementing clinical protocols for rhythmic auditory stimulation.
"""

from .synchronizer import GaitMusicSynchronizer
from ..session_management.ras_protocol import RASProtocol, RASPhase

__all__ = ['GaitMusicSynchronizer', 'RASProtocol', 'RASPhase']