# Choomba — Local-First AI Assistant Interface

Choomba is an interactive desktop prototype for a personal, private AI assistant inspired by Tony Stark's JARVIS interface. Centred around a luminous cyan animated holographic core, it features an offline-first architecture designed for a local Linux workstation running Ollama (with models such as Qwen 3.5 9B on an NVIDIA RTX 3060 12GB) and PostgreSQL for structured memory.

---

## Key Features

1. **Holographic SVG/CSS Energy Core**:
   - Multi-layered vector composition: concentric orbital rings, 48 radial calibration ticks, partial high-speed arcs, inner breathing nucleus, and crosshair reticles.
   - Dynamic states:
     - `IDLE`: Calibrated calm breathing glow and slow orbital rotation.
     - `ACTIVATED`: Core flash, alignment chime, and energetic focus.
     - `LISTENING`: Cyan expansion, audio responsive rings, and pulsing waveform.
     - `IDENTIFYING`: Focused radial ticks rotate to simulate acoustic voiceprint matching.
     - `THINKING`: Fast counter-rotating arcs and traveling highlights simulating RTX 3060 local inference.
     - `SPEAKING`: Rhythmic modulation and streamed response preview.
     - `ERROR`: Restrained warning state with amber/coral indicator.
     - `OFFLINE`: Dimmed slate appearance with broken ring indicator.

2. **Web Audio Harmonic Synthesizer**:
   - Zero external audio assets; uses algorithmic Web Audio API sine/triangle oscillators to generate restrained, subtle sci-fi chimes.
   - Includes mute toggle in top bar.

3. **Pluggable Modular Service Layer**:
   - `src/services/ModelService.ts`: Model discovery, model switching (`qwen3.5:9b`, `qwen3.5:14b`, `gpt-oss:20b`).
   - `src/services/AssistantService.ts`: Streaming inference reader, conversation history, session clearing.
   - `src/services/MemoryService.ts`: PostgreSQL memory store simulation & Obsidian Markdown vault index.
   - `src/services/SystemStatusService.ts`: Telemetry for Fedora 40, RTX 3060 12GB VRAM allocation, and systemd daemon.
   - `src/services/AudioSoundService.ts`: Web Audio chime engine.

4. **Expandable Translucent Drawers**:
   - **Conversation Drawer**: Live conversation buffer, token counter, active operator profile, and session restart/clear controls.
   - **Settings Drawer**: 8 dedicated sections (General Appearance, Model & Inference, Voice Activation with double-clap toggle, Audio I/O, Database & Memory for PostgreSQL `choomba`, Privacy & Offline Enforcement, System Status, Future Local Integrations).
   - **Architecture & Backend Readiness Guide**: Accessible directly via the `ARCH` button in the top bar with ready-to-use code snippets for local backend integration.

5. **Developer State Switcher**:
   - Manual override buttons for all 8 states to test animations and transitions.
   - "Test Full Loop" button that runs the entire sequence automatically.

---

## Directory Structure

```
├── index.html                   # HTML entry point with metadata & fonts
├── metadata.json                # AI Studio application metadata
├── package.json                 # Dependencies & scripts
├── README.md                    # Project documentation & migration guide
├── tsconfig.json                # TypeScript compiler configuration
├── vite.config.ts               # Vite configuration
└── src/
    ├── App.tsx                  # Main application shell & state orchestration
    ├── main.tsx                 # React DOM mount
    ├── index.css                # Tailwind CSS v4 imports & custom orbital keyframes
    ├── types/
    │   └── assistant.ts         # TypeScript definitions for states, models, & settings
    ├── services/
    │   ├── AssistantService.ts  # Interface & mock streaming conversation service
    │   ├── ModelService.ts      # Interface & mock Ollama model discovery
    │   ├── VoiceService.ts      # Voice activity & trigger interfaces
    │   ├── MemoryService.ts     # PostgreSQL & Obsidian vault memory interface
    │   ├── SystemStatusService.ts # Local system telemetry & hardware monitoring
    │   └── AudioSoundService.ts # Web Audio API harmonic chime synthesizer
    └── components/
        ├── TopStatusBar.tsx     # One-row, 3-zone contract with zero-pill metadata
        ├── CentralStage.tsx     # Dominant holographic orb & status label
        ├── BottomCommandDeck.tsx# Keyboard-friendly command input & mic toggle
        ├── DevStateSwitcher.tsx # Interactive 8-state tester & automated loop
        ├── ConversationDrawer.tsx # Slide-out chat history & token counts
        ├── SettingsDrawer.tsx   # 8-tab configuration matrix
        ├── ModelSelectorModal.tsx # Ollama model switcher & VRAM allocation
        ├── ArchitectureGuideModal.tsx # Drop-in local backend code snippets
        └── HolographicOrb/
            ├── HolographicOrb.tsx # Pure SVG & CSS animated core
            └── OrbWaveform.tsx  # Reactive audio visualization bar
```

---

## Replacing Mock Services with Real Local Implementations

When deploying to your local Fedora Linux workstation with Ollama and PostgreSQL:

### 1. Model Discovery (`ModelService.ts`)
Replace mock array with local Ollama API call:
```typescript
const response = await fetch('http://localhost:11434/api/tags');
const data = await response.json();
```

### 2. Streamed Local Inference (`AssistantService.ts`)
Consume the Ollama HTTP streaming endpoint directly:
```typescript
const response = await fetch('http://localhost:11434/api/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'qwen3.5:9b',
    prompt: userPrompt,
    stream: true,
  }),
});
```

### 3. Voice Activation & Double-Clap (`VoiceService.ts` & `backend/`)
**Implemented (Task 1):** The local Python activation daemon (`backend/service.py`) monitors microphone audio continuously through PipeWire / PortAudio, analyzing short-burst acoustic energy transients. On detecting a valid double-clap within 160ms–750ms, it broadcasts an `activation.detected` event over loopback WebSocket (`ws://127.0.0.1:8765`), transitioning the Choomba interface from `IDLE` to `ACTIVATED` to `LISTENING`.

### 4. PostgreSQL Memory Store (`MemoryService.ts`)
Point your local daemon or Express proxy at `postgresql://localhost:5432/choomba` using `pgvector` or standard relational schemas for user preferences, session history, and Obsidian vault notes.

---

## Running Locally

### 1. Start the Local Activation Daemon (Python 3)
```bash
# Start background double-clap monitor (Terminal 1)
python3 -m backend.service
# Or via npm:
npm run activation:start
```

To run with synthetic mock audio (for testing without microphone hardware):
```bash
python3 -m backend.service --mock
```

### 2. Start the Frontend Development Server (Node.js)
```bash
# Install dependencies (if first time)
npm install --legacy-peer-deps

# Start Vite dev server (Terminal 2)
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Running Automated Tests

```bash
# Run all backend unit and integration tests (13 tests)
python3 -m unittest discover backend/tests
# Or via npm:
npm run activation:test

# Run frontend build and typecheck
npm run lint
npm run build
```

---

## Systemd User Service Setup (Optional Persistent Startup)

To automatically launch the Choomba activation daemon on user login:

```bash
# 1. Create systemd user service directory
mkdir -p ~/.config/systemd/user

# 2. Copy the unit file
cp backend/choomba-activation.service ~/.config/systemd/user/

# 3. Reload systemd daemon
systemctl --user daemon-reload

# 4. Enable and start the service
systemctl --user enable --now choomba-activation.service

# 5. Check service status and live logs
systemctl --user status choomba-activation.service
journalctl --user -u choomba-activation.service -f

# 6. To stop or disable the service
systemctl --user stop choomba-activation.service
systemctl --user disable choomba-activation.service
```

---

## Architecture & Event Contract

### WebSocket Contract (`ws://127.0.0.1:8765`)
The service strictly binds to loopback (`127.0.0.1`) and validates the browser `Origin` header against permitted local origins (`http://localhost:3000`, `http://127.0.0.1:3000`).

#### Activation Event (Backend → Frontend):
```json
{
  "type": "activation.detected",
  "method": "double_clap",
  "timestamp": "2026-10-19T01:45:00.000Z",
  "metadata": {
    "interval_ms": 320.5,
    "confidence": 0.94,
    "first_clap_rms": 1420.0,
    "second_clap_rms": 1680.0,
    "noise_floor": 210.0
  }
}
```

#### Status Event (Backend → Frontend):
```json
{
  "type": "status",
  "state": "monitoring",
  "method": "double_clap",
  "sensitivity": 0.8,
  "connected_clients": 1,
  "audio_device": "HD-Audio Generic: ALC887-VD Analog (hw:1,0)",
  "sample_rate": 44100,
  "noise_floor": 210.0
}
```

#### Client Control Commands (Frontend → Backend):
- `{"action": "set_sensitivity", "value": 0.85}`: Adjust detection sensitivity (0.1–1.0).
- `{"action": "pause"}`: Pause microphone analysis.
- `{"action": "resume"}`: Resume microphone analysis.
- `{"action": "simulate_clap"}`: Simulate double-clap roundtrip without physical microphone.
- `{"action": "ping"}`: Heartbeat check (replies with `{"type": "pong"}`).

---

## Acoustic Physics, Limitations & Tuning

Double-clap detection evaluates acoustic transients (sudden energy jumps) against an adaptive exponential moving average (EMA) noise floor:

1. **Transient Duration Gate**: Claps are short impulses (<80ms). Sustained loud sounds (speech, singing, vacuum cleaner, fan noise) stay high for >90ms and are rejected.
2. **Tempo Bounds**: Two claps must occur within 160ms–750ms. An impulse <160ms after the first is rejected as room reverberation or echo. An impulse >750ms resets the window.
3. **Cooldown**: After a successful trigger, a 1500ms cooldown prevents cheering, applause, or echo from triggering duplicate activations.
4. **Limitations**:
   - Hard surface reflections (tile/glass) may create reverberant tails; reducing room gain or positioning the mic helps.
   - Sharp mechanical sounds (dropping a ceramic mug, hard desk slap) can mimic a clap transient.
   - If ambient room noise changes, the adaptive noise floor tracks baseline changes after 1–2 seconds.
   - Tuning: Use the sensitivity slider in **Settings Drawer → Voice Activation** (default 80%). Lower to 50–60% in noisy rooms, or raise to 90% if clapping from across the room.

