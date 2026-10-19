# Choomba — Local-First AI Assistant Interface

Choomba is a desktop-style prototype for a personal, private AI assistant inspired by Tony Stark's JARVIS interface, centered around an interactive holographic animated cyan-blue orb and built upon a modular architecture designed for local Linux/Ollama/PostgreSQL operation.

## User Review & Critical Decisions

> [!IMPORTANT]
> The following architectural and UX choices have been confirmed and integrated into this blueprint:

- **Confirmed Decision 1 (Orb Rendering Engine)**: Pure layered SVG with CSS transformations and keyframe animations for crisp geometric vector scaling, smooth 60fps performance, and complete isolation from the assistant state logic.
- **Confirmed Decision 2 (Auditory Feedback)**: Integrated Web Audio API synthesized harmonic sci-fi chimes for state transitions (e.g., wake activation, listening acknowledgment, thinking chord, speaking pulse, and error tone) with a persistent mute toggle in the top bar.
- **Confirmed Decision 3 (Drawer Layout)**: Translucent slide-out side drawers (`backdrop-blur-md` with subtle hairline border styling) for conversation history, system health telemetry, and settings that keep the central holographic orb as the undisputed focal anchor.
- **Confirmed Decision 4 (Zero Cloud Leakage)**: Fully simulated, mock-driven local service adapter pattern (`AssistantService`, `ModelService`, `VoiceService`, `MemoryService`, `SystemStatusService`) that requires no external network requests or API keys, with clear visual disclaimers on simulated responses.

---

## 1. Overview & Core Concept

- **What It Does**: A personal AI assistant desktop interface tailored for local-first systems. The interface responds dynamically through an animated holographic energy core, status indicators, and subtle acoustic feedback across distinct operational states (`IDLE`, `ACTIVATED`, `LISTENING`, `IDENTIFYING`, `THINKING`, `SPEAKING`, `ERROR`, `OFFLINE`). Users can interact via simulated voice activation or text input, switch active Ollama models, inspect local memory/context, and configure system preferences.
- **Target Audience / Persona**: Power users, developers, and makers running Linux workstations who demand private, self-hosted AI assistance with the polished aesthetics of an advanced command console.
- **Key Value**: Provides a visual and tactile identity for an offline AI agent, avoiding generic chat windows and messy dashboards while providing clear, typed interfaces for plug-and-play backend replacement.

---

## 2. User Experience & Visual Design

### Key User Flows
1. **Orb & State Observation**: On initial load, Choomba resides in `IDLE` with a gentle pulsing breathing glow and slow orbital rotation. The user can use the quick Dev State Trigger bar to manually simulate any phase (`ACTIVATED` -> `LISTENING` -> `IDENTIFYING` -> `THINKING` -> `SPEAKING` -> `OFFLINE` -> `ERROR`).
2. **Conversation & Interaction**: Clicking the microphone or submitting a prompt via the bottom input triggers the full conversational loop:
   - Voice trigger chime sounds.
   - Core expands into brighter cyan waveform arcs (`LISTENING`).
   - Core tightens into focused radial scanning ticks (`IDENTIFYING`).
   - Faster counter-rotating rings and traveling highlights engage (`THINKING`).
   - Rhythmic acoustic modulation and response preview stream under the orb (`SPEAKING`).
   - Transcript and response auto-append to the collapsible Conversation Drawer.
3. **Model Selection**: The top bar displays active mock model (`qwen3.5:9b`). Clicking it opens a fast model switcher supporting `qwen3.5:9b`, `qwen3.5:14b`, and `gpt-oss:20b`, showing mock status tags (`READY`, `LOADING`, `UNAVAILABLE`) and parameter sizes.
4. **Settings & Architecture Inspection**: Opening the Settings Drawer reveals modular tabs for General Appearance, Model & Inference, Voice Activation (including future double-clap / wake-word options), Database & Memory (PostgreSQL connection parameters), Privacy & Offline Guarantees, and Future Integrations (Home Assistant, Obsidian vault sync).

### Visual Identity & Theme
- **Color Palette & Atmosphere**:
  - Background Canvas: Deep void navy (`#050A12`) with subtle radial ambient glow (`rgba(67, 207, 255, 0.04)`).
  - Primary Laser Accent: Electric Cyan (`#43CFFF`).
  - Secondary Depth Accent: Deep Arc Blue (`#1677FF`).
  - Structural Hairlines: Cool Slate / Blue-Grey borders (`rgba(67, 207, 255, 0.12)`).
  - Typography: Cool White (`#E6F4FE`) for primary readouts; Muted Cyan-Slate (`#82A2BF`) for system metadata.
- **Typography**:
  - Display & Headings: `Plus Jakarta Sans` / `Outfit` (clean geometric precision).
  - System Metadata & Telemetry: Monospace tabular numerals (`JetBrains Mono`, `tabular-nums`) with small uppercase tracking (`tracking-wider text-xs`).
  - Strict Zero-Pill Discipline: System metadata formatted as clean text with typographic dividers (`·` or `/`), never rounded candy capsules.
- **Component Styling & Layout**:
  - 1440x900 desktop-first baseline with fluid responsive scaling down to mobile viewports.
  - Three-zone Top Bar Contract: Brand mark with custom geometric icon on the left; unboxed telemetry metadata (`MODEL: QWEN3.5:9B · INFERENCE: LOCAL · DB: CONNECTED`) and state in the center; action controls (Audio toggle, Conversation drawer, Settings drawer) on the right.
  - Central Stage: Large holographic SVG orb with concentric orbital rings, radial measurement ticks, partial arcs, and a luminous energy nucleus.
  - Bottom Bar: Compact command bar with keyboard shortcut hint (`Enter` to send, `Space` for push-to-talk simulation), mic toggle, and status preview.

---

## 3. Key Product Decisions & Trade-Offs

- **Decision 1: Layered SVG Core vs. Heavy WebGL/Canvas**
  - *Chosen Approach*: Multi-layered SVG composition using independent CSS transforms for orbits, counter-rotating rings, dashed arcs, and dynamic filter glows.
  - *Why*: Delivers pin-sharp vector rendering at any scale, avoids GPU thermal spikes, runs reliably across all browser environments without external WebGL dependencies, and allows instant CSS-level state theming.
  - *Alternatives Considered*: Three.js or pure Canvas 2D were considered; SVG was selected for maximum crispness, lower overhead, and zero rendering artifacts on high-DPI displays.
- **Decision 2: Native Web Audio Synthesizer vs. Audio Asset Files**
  - *Chosen Approach*: Algorithmic Web Audio API synthesizer generating clean sine/triangle oscillator chords and filtered frequency sweeps.
  - *Why*: Zero network requests, instant latency, zero risk of missing audio asset files, and fully customizable pitch/modulation tied to assistant states.
  - *Alternatives Considered*: Bundled `.mp3`/`.wav` samples would add file weight and risk audio decoding latency.
- **Decision 3: Pluggable Frontend Service Architecture**
  - *Chosen Approach*: Clean TypeScript interfaces (`AssistantService`, `ModelService`, `VoiceService`, `MemoryService`, `SystemStatusService`) with mock implementations isolated in `src/services/`.
  - *Why*: When the user later builds the local Python/systemd daemon or Ollama/PostgreSQL bridge, they can swap out the mock services with `fetch('http://localhost:11434/...')` without touching a single UI component.

---

## 4. Technical Architecture & Data Strategy

### Component & Data Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Top Navigation Bar                              │
│  [✦ CHOOMBA] ──── [METADATA: MODEL · INFERENCE · DB] ──── [♫ / 💬 / ⚙] │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Central Stage Viewport                          │
│                                                                        │
│                       ┌──────────────────────┐                         │
│                       │   Holographic Core   │                         │
│                       │   (Pure SVG Rings,   │                         │
│                       │   Ticks & Energy)    │                         │
│                       └──────────────────────┘                         │
│                                                                        │
│                      [ STATE: ● LISTENING ]                            │
│                 "Awaiting voice prompt or input..."                    │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
          ▲                                                    ▲
          │                                                    │
┌──────────────────────┐                             ┌───────────────────┐
│ Conversation Drawer  │                             │  Settings Drawer  │
│ - Chat transcript    │                             │ - Model routing   │
│ - Speaker identity   │                             │ - Wake activation │
│ - Token count        │                             │ - Memory / DB     │
│ - Session restart    │                             │ - Offline privacy │
└──────────────────────┘                             └───────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Bottom Command & Input Deck                          │
│     [🎙 Mic Toggle]  [ > Enter command for Choomba... ]  [Send]        │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 Service Layer & State Abstraction                      │
│   AssistantService │ ModelService │ VoiceService │ SystemStatusService │
│          (TypeScript Interfaces with Mock Default Providers)           │
└────────────────────────────────────────────────────────────────────────┘
```

### State Machine Specification

$$\text{IDLE} \longrightarrow \text{ACTIVATED} \longrightarrow \text{LISTENING} \longrightarrow \text{IDENTIFYING} \longrightarrow \text{THINKING} \longrightarrow \text{SPEAKING} \longrightarrow \text{IDLE}$$
$$\text{Exceptions}: \quad \text{ANY} \longrightarrow \text{ERROR} \quad\mid\quad \text{ANY} \longrightarrow \text{OFFLINE}$$

### Service Interfaces (Ready for Local Backend Replacement)

1. `AssistantService`: Manages conversation history, message dispatch, streaming response simulation, and session reset.
2. `ModelService`: Lists available local models (`qwen3.5:9b`, `qwen3.5:14b`, `gpt-oss:20b`), active model selection, and memory footprints.
3. `VoiceService`: Coordinates audio synthesis, input detection states, speaker identification simulation, and clap/wake activation triggers.
4. `MemoryService`: Manages structured memory context simulation (PostgreSQL mock connection, Obsidian vault status, active user profile).
5. `SystemStatusService`: Reports mock GPU/RAM telemetry (RTX 3060 12GB allocation, Ollama daemon status, local network isolation).

---

## 5. Verification Plan

1. **Compilation Check**: Run `compile_applet` to ensure pristine TypeScript build with zero errors.
2. **State & Animation Verification**: Exercise all 8 assistant states via the dev controls to ensure proper SVG orbital velocity, cyan bloom intensity, audio chimes, and status typography.
3. **Conversational Loop**: Test sending messages via text input and mic trigger, verifying streaming preview, transcript rendering, and session clearing.
4. **Drawer & Responsive Layout**: Verify smooth opening/closing of Conversation and Settings drawers, responsiveness at 1440x900 down to 768px, and keyboard accessibility.
