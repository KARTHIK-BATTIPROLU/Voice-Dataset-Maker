# ASTA Voice Dataset Collector

A local, zero-cost voice dataset collection platform for training custom speaker verification models (SpeechBrain ECAPA-TDNN fine-tuning). The platform automatically records, transcribes (Faster Whisper locally), and labels audio samples — producing a fully structured, SpeechBrain-ready manifest with zero manual file management.

## Features

- ✅ **Automated Recording Loop**: Continuous 5-second audio chunk recording with audio cues
- ✅ **Local Transcription**: Faster Whisper integration for zero-cost speech-to-text
- ✅ **Real-Time Feedback**: WebSocket-based UI with live updates
- ✅ **Quality Safeguards**: Low confidence warnings and duplicate detection
- ✅ **Session Management**: Pause/resume with state persistence across restarts
- ✅ **SpeechBrain Compatible**: Auto-generated manifest.csv in ECAPA-TDNN format
- ✅ **Zero Cost**: Everything runs locally, no cloud dependencies
- ✅ **Dark Theme UI**: Clean, modern interface with electric blue accents

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, SoundDevice, Faster Whisper
- **Frontend**: React 18, Vite, WebSocket API
- **Storage**: File system (WAV + CSV + JSON)

## System Requirements

### Minimum
- CPU: Quad-core (Intel i5 or equivalent)
- RAM: 4GB available
- Storage: 10GB free (for ~1000 samples)
- OS: Windows 10+, Ubuntu 20.04+, macOS 11+
- Python: 3.10+
- Node.js: 16+
- Microphone with system permissions

### Recommended
- CPU: Hexa-core (Intel i7 or equivalent)
- RAM: 8GB available
- Storage: 50GB free
- GPU: Optional (Faster Whisper supports CUDA for faster transcription)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/KARTHIK-BATTIPROLU/Voice-Dataset-Maker.git
cd Voice-Dataset-Maker
```

### 2. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- FastAPI & Uvicorn (web server)
- SoundDevice & SoundFile (audio recording)
- Faster Whisper (local transcription)
- PyYAML (configuration)
- NumPy, SciPy (audio processing)

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Usage

### Quick Start

**Windows:**
```bash
start_app.bat
```

This will:
1. Start the FastAPI backend on http://localhost:8000
2. Start the React frontend on http://localhost:3000
3. Open your browser automatically

**Manual Start:**

Terminal 1 (Backend):
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

### Recording Workflow

1. **Open the App**: Navigate to http://localhost:3000
2. **Click START**: Begins a new recording session
3. **Speak into Microphone**: 
   - Listen for the beep sound (recording cue)
   - Speak clearly for 5 seconds
   - Watch the countdown timer in the orb
4. **Monitor Progress**:
   - Live transcript feed shows auto-labeled samples
   - Sample counters update in real-time
   - Quality warnings appear for low confidence samples
5. **Control Recording**:
   - **PAUSE**: Temporarily stop recording (preserves session)
   - **RESUME**: Continue from paused state
   - **STOP**: End session and finalize manifest
6. **Repeat**: The loop automatically continues until paused/stopped

### Configuration

Edit `config.yaml` to customize:

```yaml
audio:
  sample_rate: 16000        # Hz (required for SpeechBrain)
  duration: 5.0             # Seconds per sample
  beep_duration: 0.5        # Beep cue duration
  beep_frequency: 800       # Beep frequency (Hz)

transcription:
  model_size: "base"        # Options: tiny, base, small, medium, large
  confidence_threshold: 0.4 # Min confidence for valid transcripts
  device: "cpu"             # Options: cpu, cuda

quality:
  duplicate_detection_threshold: 5  # Consecutive duplicates to flag
```

## Output Files

### Directory Structure

```
Voice-Dataset-Maker/
├── data/
│   ├── session_20240115_143022/
│   │   ├── sample_0001.wav
│   │   ├── sample_0002.wav
│   │   └── ...
│   └── session_20240115_154530/
│       └── ...
├── manifest.csv              # SpeechBrain-ready manifest
├── session_state.json        # Persistent session state
└── logs/
    ├── system.log
    └── quality_warnings.log
```

### Manifest Format

`manifest.csv` contains all sample metadata:

```csv
sample_id,file_path,transcript,duration_sec,sample_rate,session_id,timestamp,whisper_confidence
0001,data/session_20240115_143022/sample_0001.wav,hey ASTA,5.0,16000,session_20240115_143022,2024-01-15T14:30:27Z,0.89
0002,data/session_20240115_143022/sample_0002.wav,yo ASTA,5.0,16000,session_20240115_143022,2024-01-15T14:30:35Z,0.91
```

**Column Specifications:**
- `sample_id`: Zero-padded 4-digit (0001-9999)
- `file_path`: Relative path from project root
- `transcript`: Transcribed text or `__unclear__` for low confidence
- `duration_sec`: Always 5.0
- `sample_rate`: Always 16000 (required by SpeechBrain)
- `session_id`: Session identifier (session_YYYYMMDD_HHMMSS)
- `timestamp`: ISO 8601 format
- `whisper_confidence`: Float 0.0-1.0

## Training with SpeechBrain

Once you've collected 500+ samples, use the manifest directly with SpeechBrain:

```python
from speechbrain.dataio.dataio import read_audio
import pandas as pd

# Load manifest
manifest = pd.read_csv('manifest.csv')

# Filter valid samples (optional)
valid_samples = manifest[manifest['whisper_confidence'] >= 0.4]

# Use with SpeechBrain ECAPA-TDNN
# Your training code here...
```

## API Endpoints

### REST API

- `POST /api/session/start` - Start recording session
- `POST /api/session/pause` - Pause recording
- `POST /api/session/resume` - Resume recording
- `POST /api/session/stop` - Stop and finalize session
- `GET /api/session/status` - Get current session state
- `GET /api/stats` - Get collection statistics
- `GET /api/manifest/validate` - Validate manifest integrity
- `GET /health` - Health check

### WebSocket

- `ws://localhost:8000/ws` - Real-time event stream

**Event Types:**
- `BEEP` - Recording cue fired
- `RECORDING_START` - 5-second recording started
- `sample_recorded` - Sample saved to disk
- `transcription_complete` - Transcription finished
- `stats_update` - Sample counts updated
- `state_change` - Session state changed
- `quality_warning` - Low confidence or duplicate detected
- `error` - System error occurred

## Troubleshooting

### Microphone Not Accessible
- Ensure microphone permissions are granted
- Check system audio settings
- Test with: `python -c "import sounddevice as sd; print(sd.query_devices())"`

### Transcription Slow
- Use GPU if available: Set `device: "cuda"` in config.yaml
- Use smaller model: Set `model_size: "tiny"` in config.yaml
- Close other applications to free RAM

### WebSocket Connection Fails
- Check backend is running on port 8000
- Verify no firewall blocking localhost connections
- Check browser console for errors

### Frontend Won't Start
- Delete `frontend/node_modules` and run `npm install` again
- Check Node.js version: `node --version` (should be 16+)
- Try: `npm cache clean --force`

## Performance

- **Transcription**: <2 seconds per 5-second sample (base model, CPU)
- **Manifest Update**: <100ms per append
- **WebSocket Latency**: <500ms event delivery
- **Max Session Duration**: 4+ hours continuous recording
- **Sample Limit**: 9999 samples per project (4-digit IDs)

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review troubleshooting section

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Faster Whisper](https://github.com/guillaumekln/faster-whisper)
- [SoundDevice](https://python-sounddevice.readthedocs.io/)
- [React](https://react.dev/)
- [Vite](https://vitejs.dev/)

---

**Target**: 2000+ labeled 5-second voice samples  
**Cost**: ₹0 (everything runs locally)  
**Zero manual file management** ✨
