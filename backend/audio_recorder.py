"""
Audio Recorder Component

Captures 5-second audio chunks at 16kHz mono using the system microphone.
Uses SoundDevice library for audio recording and playback.
"""

import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path
from typing import Optional
import logging


logger = logging.getLogger(__name__)


class AudioRecordingError(Exception):
    """Custom exception for audio recording failures"""
    pass


class AudioRecorder:
    """
    Audio recorder for capturing 5-second voice samples.
    
    Provides methods for recording audio, saving WAV files, and playing beep cues.
    All audio is captured at 16kHz sample rate in mono format.
    """
    
    def __init__(self, sample_rate: int = 16000, duration: float = 5.0):
        """
        Initialize recorder with configurable parameters.
        
        Args:
            sample_rate: Audio sample rate in Hz (default: 16000)
            duration: Recording duration in seconds (default: 5.0)
        
        Raises:
            AudioRecordingError: If audio device initialization fails
        """
        self.sample_rate = sample_rate
        self.duration = duration
        self.channels = 1  # Mono audio
        
        # Verify that a microphone is available
        try:
            devices = sd.query_devices()
            input_device = sd.query_devices(kind='input')
            logger.info(f"Audio recorder initialized with device: {input_device['name']}")
        except Exception as e:
            logger.error(f"Failed to initialize audio device: {e}")
            raise AudioRecordingError(f"Microphone not accessible: {e}")
    
    def record_sample(self) -> np.ndarray:
        """
        Record a single 5-second audio sample.
        
        Captures audio from the default system microphone at the configured
        sample rate and duration.
        
        Returns:
            numpy.ndarray: Audio samples as 1D array (shape: [sample_rate * duration])
            
        Raises:
            AudioRecordingError: If audio capture fails
        """
        try:
            logger.info(f"Recording {self.duration} seconds of audio at {self.sample_rate}Hz...")
            
            # Record audio using sounddevice (blocking)
            audio_data = sd.rec(
                int(self.sample_rate * self.duration),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32'
            )
            
            # Wait for recording to complete
            sd.wait()
            
            # Flatten to 1D array if needed
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()
            
            logger.info(f"Successfully recorded {len(audio_data)} samples")
            return audio_data
            
        except Exception as e:
            logger.error(f"Audio recording failed: {e}")
            raise AudioRecordingError(f"Failed to record audio: {e}")
    
    def save_wav(self, audio_data: np.ndarray, file_path: Path) -> None:
        """
        Save audio data as 16-bit PCM WAV file.
        
        Args:
            audio_data: Audio samples as numpy array
            file_path: Output path for WAV file
            
        Raises:
            AudioRecordingError: If file write fails
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save as 16-bit PCM WAV file
            sf.write(
                file_path,
                audio_data,
                self.sample_rate,
                subtype='PCM_16'
            )
            
            logger.info(f"Audio saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save WAV file: {e}")
            raise AudioRecordingError(f"Failed to save audio to {file_path}: {e}")
    
    def play_beep(self, duration: float = 0.5, frequency: int = 800) -> None:
        """
        Play audio beep cue before recording.
        
        Generates and plays a pure tone at the specified frequency and duration
        to signal the start of recording.
        
        Args:
            duration: Beep duration in seconds (default: 0.5)
            frequency: Beep frequency in Hz (default: 800)
            
        Raises:
            AudioRecordingError: If beep playback fails
        """
        try:
            # Generate beep tone (sine wave)
            t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
            beep_signal = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            # Play beep (blocking)
            sd.play(beep_signal, self.sample_rate)
            sd.wait()
            
            logger.debug(f"Played beep: {frequency}Hz for {duration}s")
            
        except Exception as e:
            logger.error(f"Failed to play beep: {e}")
            raise AudioRecordingError(f"Failed to play beep cue: {e}")
