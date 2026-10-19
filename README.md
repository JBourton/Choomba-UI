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
**Implemented (Task 1):** The local Python activation daemon (`backend/service.py`) monitors microphone audio continuously through PipeWire / PortAudio, analyzing short-burst acoustic energy transients. On detecting a valid double-clap within 150ms–450ms, it broadcasts an `activation.detected` event over loopback WebSocket (`ws://127.0.0.1:8765`), transitioning the Choomba interface from `IDLE` to `ACTIVATED` to `LISTENING`.

### 4. PostgreSQL Memory Store (`MemoryService.ts`)
Point your local daemon or Express proxy at `postgresql://localhost:5432/choomba` using `pgvector` or standard relational schemas for user preferences, session history, and Obsidian vault notes.

---

## Where To Change The Settings

**`backend/config.py` → the `APP_SETTINGS` section** is the single place where
every knob of the activation daemon lives.  Edit the dictionary there, or
override any of it with an environment variable of the same name
(`CHOOMBA_` + the key in upper case, e.g. `CHOOMBA_CLAP_SENSITIVITY=0.5`).

The three settings that matter most in day to day use are also editable in
the app, in **Settings Drawer → 3. Voice Activation**, and they take effect
on the running daemon immediately:

| Setting | In the app | What it does |
| --- | --- | --- |
| `clap_sensitivity` | Clap Detection Sensitivity | How far above the room tone a clap has to be (2.8x … 1.5x of the ambient peak) |
| `clap_min_peak_threshold` | Minimum Clap Level | How loud a clap has to be in absolute terms (0-32767). Stops speech and typing in a quiet room |
| `clap_min_low_band_share` | Slap Strictness | How much low frequency "thud" a clap must have (rejects key clicks) |
| `clap_min_crack_band_share` | Crack Strictness | How much broadband "crack" a clap must have (rejects talking) |
| `clap_max_interval_ms` | Double Clap Window | How far apart the two strikes may be |
| `clap_min_interval_ms` | Minimum Gap | Anything faster than this is a room echo |
| `clap_pair_confirmation_ms` | Train Guard | A third sound inside this window cancels the pair (rejects a burst of key presses) |

`clap_max_transient_duration_ms`, `clap_cooldown_ms`, `sample_rate`,
`chunk_size`, `audio_device`, `host` and `port` are code side only.

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
    "confidence": 0.82,
    "first_clap_rms": 1420.0,
    "second_clap_rms": 1680.0,
    "noise_floor": 210.0,
    "first_clap_peak": 9120.0,
    "second_clap_peak": 10440.0
  }
}
```

* `*_rms` values are short-window (1.45 ms) RMS levels, `*_peak` values are the
  sample peaks the detection is actually based on. All amplitudes are 16-bit
  linear units (full scale = 32768).
* `confidence` is a bounded score in `[0, 0.99]` that combines how far the
  second clap stood above the detection threshold with how centred the
  inter-clap interval was inside the allowed window. It is *not* a constant:
  a marginal event scores noticeably lower than a clear one.

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

Double-clap detection evaluates acoustic transients against an adaptive
background estimate. A hand clap is a *short, high-amplitude impulse*, so the
detector tests three independent properties of every 11.6 ms frame:

1. **Amplitude**: the frame peak must clear *both* the tracked ambient peak
   level (1.76x at the default sensitivity) and an absolute floor
   (`clap_min_peak_threshold`, default 6000). The peak is used rather than
   an energy average because an 11.6 ms average dilutes a 1–3 ms clap by
   roughly 8x while leaving continuous background noise untouched.
   The absolute floor is what stops the detector reacting to speech or key
   presses in a *quiet* room, where a relative threshold has nothing to
   compare against.
2. **Concentration**: the loud energy must sit in only a few of the frame's
   1.45 ms analysis windows. A clap lights up one or two windows; speech,
   music, a fan or a passing car fill all of them and are rejected whatever
   their level is.
3. **Duration**: a burst that stays loud for longer than 60 ms is continuous
   sound, not a clap.
4. **The slap**: a hand clap is a *collision*.  It has two spectral
   signatures at once:
   - a strong low frequency pressure wave (the thud of the palms,
     60-300 Hz) - `CHOOMBA_MIN_LOW_BAND_SHARE`, default 0.35
   - a broadband crack (1.2-12 kHz) - `CHOOMBA_MIN_CRACK_BAND_SHARE`,
     default 0.18

   A mechanical key click only has the crack, an unvoiced speech sound
   ("t", "k", "p") only has the crack, and a voiced sound ("d", a vowel)
   only has the thud.  A clap is the only thing that has **both**, which is
   what separates it from typing and from talking.  The detector's 350 Hz
   high-pass throws this information away, so both bands are measured in
   parallel filter paths.

### The shape of a double clap

A double clap is *two comparable strikes*, not "any two loud sounds". The
detector therefore also checks the structure of the pair:

5. **Burst width**: the transient has to exceed the ambient peak level for
   more than one sample, which rejects single-sample USB/ALSA glitches.
6. **Matching strikes**: the two strikes of a pair have to be within a factor
   of each other in level. A single loud clap followed by some unrelated (and
   much quieter) background noise therefore never forms a pair.
7. **Tempo bounds**: two claps must occur within 150 ms-450 ms. A transient
   that arrives sooner than the minimum interval is discarded as a room
   reverberation or echo - it can never be paired with a later, unrelated
   sound.
8. **No train**: a pair is held for a short confirmation window
   (`CHOOMBA_PAIR_CONFIRMATION_MS`, default 450 ms) before it is reported.
   If a third burst of comparable level follows within that window, the pair
   is cancelled - a mechanical keyboard produces a whole *train* of key
   presses, a double clap produces exactly two. The same window also keeps a
   strike that follows another comparable strike from starting a new pair, so
   the second and third key press of a typing burst can never pair up.
9. **Cooldown**: after a successful trigger, a 1500 ms cooldown prevents
   cheering, applause, or echo from triggering duplicate activations.

10. **Where to change the settings**:
    - **In the code**: everything lives in the `APP_SETTINGS` section of
      `backend/config.py` - one dictionary with every knob, each of which can
      also be overridden with an environment variable of the same name
      (`CHOOMBA_CLAP_SENSITIVITY`, `CHOOMBA_MIN_LOW_BAND_SHARE`, ...).
    - **In the app**: *Settings Drawer -> 3. Voice Activation* exposes the
      three settings that matter most - *Clap Detection Sensitivity* (how far
      above the room tone a clap has to be), *Slap Strictness* (how much low
      frequency thud a clap must have) and *Double Clap Window* (how far
      apart the two strikes may be).  They are applied to the running daemon
      immediately, no restart needed.

11. **Limitations**:
    - The activation is reported ~450 ms after the second strike (the
      confirmation window). Lower `CHOOMBA_PAIR_CONFIRMATION_MS` to trade
      that latency against robustness against fast trains of sounds.
    - The band tests need the actual slap to reach the microphone. The
      measured values are printed with every `Clap 1 registered` line and in
      the rejection messages; if they are below the thresholds for your real
      claps, lower `clap_min_low_band_share` / `clap_min_crack_band_share` in
      the app, or set them to 0 in `APP_SETTINGS` to switch the tests off.
   - If the detector now ignores your claps, the absolute floor is the
      first thing to lower (`clap_min_peak_threshold` in the app, or
      `CHOOMBA_MIN_CLAP_PEAK_THRESHOLD` in the environment).
    - Hard surface reflections (tile/glass) may create reverberant tails; reducing room gain or positioning the mic helps.
    - Sharp mechanical sounds (dropping a ceramic mug, hard desk slap) can mimic a clap transient - they are acoustically the same kind of event.
    - Two comparable impulses 150-450 ms apart are, by definition, a double clap. A keyboard whose clicks are as loud as a hand clap can therefore still produce a rare activation; a lower ambient level (or a quieter keyboard) is the only reliable remedy.
    - The ambient level is tracked as the *median* of the last 32 frames (~0.37 s) and has **no absolute ceiling**, so a loud room raises the threshold instead of pinning it, and a burst of key presses cannot inflate the estimate underneath itself. The detector needs the clap's peak to be roughly 2x the ambient peak, which in practice means the room tone has to stay below about -16 dBFS.
    - If ambient room noise changes, the adaptive background tracks the change within ~0.4 s.
    - Tuning: Use the sensitivity slider in **Settings Drawer -> 3. Voice Activation** (default 80%). It only changes the amplitude margin (2.8x at 10% ... 1.8x at 100% of the ambient peak); the range is deliberately narrow so that turning it down cannot push a genuine double clap out of the detection window. Continuous sound, key presses and speech are rejected on *shape* and *spectrum*, not on level, so they cannot be "tuned in" either.
    - The clap detector only runs while **Activation Trigger Method** is set to *Double Clap*; selecting *Wake Word* or *Manual Hotkey* pauses the microphone analysis in the daemon.

