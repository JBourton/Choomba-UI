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

### 3. Voice Activation & Double-Clap (`VoiceService.ts`)
Connect the web microphone stream (`navigator.mediaDevices.getUserMedia`) to an AudioContext `AnalyserNode` detecting two transient RMS peaks within a 400ms window, or bridge to a local Python daemon handling VAD via `whisper.cpp`.

### 4. PostgreSQL Memory Store (`MemoryService.ts`)
Point your local daemon or Express proxy at `postgresql://localhost:5432/choomba` using `pgvector` or standard relational schemas for user preferences, session history, and Obsidian vault notes.

---

## Running Locally

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.
