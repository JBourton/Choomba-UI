import React, { useState } from 'react';
import {
  X,
  Sliders,
  Cpu,
  Mic,
  Volume2,
  Database,
  Shield,
  Activity,
  Layers,
  Check,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { ChoombaSettings, OllamaModelInfo } from '../types/assistant';
import {
  DaemonStatusPayload,
  DaemonSettings,
  VoiceServiceConnectionState,
  voiceService,
} from '../services/VoiceService';

interface SettingsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  settings: ChoombaSettings;
  onUpdateSettings: (newSettings: Partial<ChoombaSettings>) => void;
  models: OllamaModelInfo[];
  daemonStatus?: DaemonStatusPayload | null;
  connectionState?: VoiceServiceConnectionState;
}

type TabKey =
  | 'appearance'
  | 'model'
  | 'voice'
  | 'audio'
  | 'database'
  | 'privacy'
  | 'system'
  | 'integrations';

export const SettingsDrawer: React.FC<SettingsDrawerProps> = ({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
  models,
  daemonStatus,
  connectionState = 'disconnected',
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>('appearance');
  const [savedBanner, setSavedBanner] = useState(false);

  // The daemon owns the detector settings; it reports the current values and
  // applies any change sent with `set_settings`.
  const daemonSettings: DaemonSettings | undefined = daemonStatus?.settings;

  const showSaveNotice = () => {
    setSavedBanner(true);
    setTimeout(() => setSavedBanner(false), 2000);
  };

  if (!isOpen) return null;

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'appearance', label: '1. General Appearance', icon: <Sliders className="w-4 h-4" /> },
    { key: 'model', label: '2. Model & Inference', icon: <Cpu className="w-4 h-4" /> },
    { key: 'voice', label: '3. Voice Activation', icon: <Mic className="w-4 h-4" /> },
    { key: 'audio', label: '4. Audio Input & Output', icon: <Volume2 className="w-4 h-4" /> },
    { key: 'database', label: '5. Database & Memory', icon: <Database className="w-4 h-4" /> },
    { key: 'privacy', label: '6. Privacy & Offline', icon: <Shield className="w-4 h-4" /> },
    { key: 'system', label: '7. System Status', icon: <Activity className="w-4 h-4" /> },
    { key: 'integrations', label: '8. Future Integrations', icon: <Layers className="w-4 h-4" /> },
  ];

  return (
    <aside
      aria-label="Choomba Settings Drawer"
      className="fixed inset-y-0 right-0 w-full md:w-[600px] lg:w-[680px] bg-[#050A12]/98 backdrop-blur-2xl border-l border-cyan-500/20 z-50 flex flex-col shadow-[-15px_0_40px_rgba(0,0,0,0.9)] transition-all duration-300"
    >
      {/* Header */}
      <div className="h-14 px-6 border-b border-cyan-500/20 flex items-center justify-between shrink-0 bg-slate-950/60">
        <div className="flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-cyan-400" />
          <h2 className="text-xs font-mono font-bold tracking-widest text-slate-100 uppercase">
            CHOOMBA CONFIGURATION MATRIX
          </h2>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded text-slate-400 hover:text-white transition-colors"
          title="Close Settings (Esc)"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Main Body with Sidebar Tabs + Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Tab List */}
        <nav className="w-48 sm:w-56 border-r border-slate-800/80 bg-slate-950/40 p-2 overflow-y-auto space-y-1 shrink-0">
          {tabs.map((t) => {
            const isActive = activeTab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-mono flex items-center gap-2.5 transition-colors ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 border border-transparent'
                }`}
              >
                <span className={isActive ? 'text-cyan-400' : 'text-slate-500'}>{t.icon}</span>
                <span className="truncate">{t.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Tab Content Panel */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {savedBanner && (
            <div className="p-3 rounded bg-cyan-950/40 border border-cyan-500/30 text-xs font-mono text-cyan-300 flex items-center gap-2">
              <Check className="w-4 h-4 text-cyan-400" />
              Settings updated in local state store.
            </div>
          )}

          {/* TAB 1: General Appearance */}
          {activeTab === 'appearance' && (
            <section className="space-y-5">
              <header className="border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-100">1. General Appearance</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Visual theme and holographic core scaling.
                </p>
              </header>

              <div className="space-y-4 text-xs font-mono">
                <div>
                  <label className="block text-slate-300 mb-1.5">Color Palette Preset</label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {[
                      { id: 'cyber-cyan', name: 'Electric Cyan (#43CFFF)' },
                      { id: 'deep-navy', name: 'Deep Arc (#1677FF)' },
                      { id: 'stealth-monochrome', name: 'Stealth Obsidian' },
                    ].map((theme) => (
                      <button
                        key={theme.id}
                        onClick={() => {
                          onUpdateSettings({ theme: theme.id as ChoombaSettings['theme'] });
                          showSaveNotice();
                        }}
                        className={`p-2.5 rounded border text-left transition-all ${
                          settings.theme === theme.id
                            ? 'border-cyan-400 bg-cyan-950/30 text-cyan-200'
                            : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        <div className="font-semibold">{theme.name}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-slate-300">Holographic Orb Scale</label>
                    <span className="text-cyan-400">{Math.round(settings.orbScale * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.8"
                    max="1.25"
                    step="0.05"
                    value={settings.orbScale}
                    onChange={(e) => {
                      onUpdateSettings({ orbScale: parseFloat(e.target.value) });
                      showSaveNotice();
                    }}
                    className="w-full accent-cyan-400 bg-slate-800"
                  />
                </div>

                <div className="pt-2 flex items-center justify-between">
                  <div>
                    <div className="text-slate-200 font-medium">High Contrast HUD</div>
                    <div className="text-[11px] text-slate-500">
                      Renders darker backgrounds with sharper edge hairlines
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.highContrastHud}
                    onChange={(e) => {
                      onUpdateSettings({ highContrastHud: e.target.checked });
                      showSaveNotice();
                    }}
                    className="w-4 h-4 accent-cyan-400"
                  />
                </div>
              </div>
            </section>
          )}

          {/* TAB 2: Model & Inference */}
          {activeTab === 'model' && (
            <section className="space-y-5">
              <header className="border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-100">2. Model Selection & Inference</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Configure local Ollama REST daemon and parameter boundaries.
                </p>
              </header>

              <div className="space-y-4 text-xs font-mono">
                <div>
                  <label className="block text-slate-300 mb-1.5">Active Local Model</label>
                  <select
                    value={settings.activeModelId}
                    onChange={(e) => {
                      onUpdateSettings({ activeModelId: e.target.value });
                      showSaveNotice();
                    }}
                    className="w-full h-10 bg-slate-900 border border-slate-800 rounded px-3 text-slate-200 focus:border-cyan-400 focus:outline-none"
                  >
                    {models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.quantization}) — {m.size}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 mb-1.5">Ollama REST Daemon Endpoint</label>
                  <input
                    type="text"
                    value={settings.ollamaEndpoint}
                    onChange={(e) => {
                      onUpdateSettings({ ollamaEndpoint: e.target.value });
                      showSaveNotice();
                    }}
                    placeholder="http://localhost:11434"
                    className="w-full h-10 bg-slate-900 border border-slate-800 rounded px-3 text-slate-200 focus:border-cyan-400 focus:outline-none"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    Default Ollama Linux daemon port (Must be strictly localhost).
                  </span>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-slate-300">Temperature</label>
                    <span className="text-cyan-400">{settings.temperature}</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="1.2"
                    step="0.05"
                    value={settings.temperature}
                    onChange={(e) => {
                      onUpdateSettings({ temperature: parseFloat(e.target.value) });
                      showSaveNotice();
                    }}
                    className="w-full accent-cyan-400 bg-slate-800"
                  />
                </div>

                <div className="pt-2 flex items-center justify-between">
                  <div>
                    <div className="text-slate-200 font-medium">Stream Token Responses</div>
                    <div className="text-[11px] text-slate-500">
                      Renders response tokens progressively as they are generated
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.streamResponses}
                    onChange={(e) => {
                      onUpdateSettings({ streamResponses: e.target.checked });
                      showSaveNotice();
                    }}
                    className="w-4 h-4 accent-cyan-400"
                  />
                </div>
              </div>
            </section>
          )}

          {/* TAB 3: Voice Activation */}
          {activeTab === 'voice' && (
            <section className="space-y-5">
              <header className="border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-100">3. Voice Activation</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Hardware trigger modes and acoustic voiceprint identification.
                </p>
              </header>

              <div className="space-y-4 text-xs font-mono">
                <div>
                  <label className="block text-slate-300 mb-1.5">Activation Trigger Method</label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {[
                      { id: 'double_clap', title: 'Double Clap (Recommended)' },
                      { id: 'wake_word', title: 'Wake Word ("Hey Choomba")' },
                      { id: 'manual_only', title: 'Manual Hotkey / Push-to-Talk' },
                    ].map((mode) => (
                      <button
                        key={mode.id}
                        onClick={() => {
                          onUpdateSettings({ activationMethod: mode.id as ChoombaSettings['activationMethod'] });
                          showSaveNotice();
                        }}
                        className={`p-2.5 rounded border text-left transition-all ${
                          settings.activationMethod === mode.id
                            ? 'border-cyan-400 bg-cyan-950/30 text-cyan-200'
                            : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        <div className="font-semibold">{mode.title}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {settings.activationMethod === 'double_clap' && (
                  <div className="space-y-4">
                    <p className="text-[10px] text-slate-500 leading-relaxed">
                      The detector only fires on a real double clap: two loud
                      strikes, of comparable level, close together, each with
                      both a low frequency thud and a broadband crack. Speech
                      and key presses do not have that shape. Raise the
                      settings below if the assistant still reacts to noise.
                    </p>

                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <label className="text-slate-300">Clap Detection Sensitivity</label>
                        <span className="text-cyan-400">
                          {Math.round((daemonSettings?.clap_sensitivity ?? settings.clapSensitivity) * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.05"
                        value={daemonSettings?.clap_sensitivity ?? settings.clapSensitivity}
                        onChange={(e) => {
                          const value = parseFloat(e.target.value);
                          onUpdateSettings({ clapSensitivity: value });
                          voiceService.setSettings({ clap_sensitivity: value });
                          showSaveNotice();
                        }}
                        className="w-full accent-cyan-400 bg-slate-800"
                      />
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        How far above the room tone a clap has to be. Lower values
                        demand a louder clap, so speech and typing are ignored.
                        Currently {daemonSettings?.detection_ratio?.toFixed(2) ?? '2.0'}x
                        the ambient level.
                      </span>
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <label className="text-slate-300">Minimum Clap Level</label>
                        <span className="text-cyan-400">
                          {Math.round(daemonSettings?.clap_min_peak_threshold ?? 6000)}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="20000"
                        step="250"
                        value={daemonSettings?.clap_min_peak_threshold ?? 6000}
                        onChange={(e) => {
                          voiceService.setSettings({
                            clap_min_peak_threshold: parseFloat(e.target.value),
                          });
                        }}
                        className="w-full accent-cyan-400 bg-slate-800"
                      />
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        How loud a clap has to be in absolute terms (0-32767).
                        This is what stops the detector reacting to speech or key
                        presses in a quiet room.
                      </span>
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <label className="text-slate-300">Slap Strictness (low thud)</label>
                        <span className="text-cyan-400">
                          {Math.round((daemonSettings?.clap_min_low_band_share ?? 0.4) * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="0.8"
                        step="0.05"
                        value={daemonSettings?.clap_min_low_band_share ?? 0.4}
                        onChange={(e) => {
                          voiceService.setSettings({
                            clap_min_low_band_share: parseFloat(e.target.value),
                          });
                        }}
                        className="w-full accent-cyan-400 bg-slate-800"
                      />
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        How much low frequency &ldquo;thud&rdquo; a clap must have. A
                        hand clap slaps, a key press ticks - raise this to
                        ignore more noise.
                      </span>
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <label className="text-slate-300">Crack Strictness (high crack)</label>
                        <span className="text-cyan-400">
                          {Math.round((daemonSettings?.clap_min_crack_band_share ?? 0.2) * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="0.8"
                        step="0.02"
                        value={daemonSettings?.clap_min_crack_band_share ?? 0.2}
                        onChange={(e) => {
                          voiceService.setSettings({
                            clap_min_crack_band_share: parseFloat(e.target.value),
                          });
                        }}
                        className="w-full accent-cyan-400 bg-slate-800"
                      />
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        How much broadband &ldquo;crack&rdquo; a clap must have. A voice
                        has a thud but hardly any crack, so this is what keeps
                        talking from waking the assistant.
                      </span>
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <label className="text-slate-300">Double Clap Window</label>
                        <span className="text-cyan-400">
                          {Math.round(daemonSettings?.clap_max_interval_ms ?? 450)}ms
                        </span>
                      </div>
                      <input
                        type="range"
                        min="200"
                        max="800"
                        step="10"
                        value={daemonSettings?.clap_max_interval_ms ?? 450}
                        onChange={(e) => {
                          voiceService.setSettings({
                            clap_max_interval_ms: parseFloat(e.target.value),
                          });
                        }}
                        className="w-full accent-cyan-400 bg-slate-800"
                      />
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        The maximum gap between the two strikes. A normal double
                        clap is 150-450ms apart.
                      </span>
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <label className="text-slate-300">Minimum Gap</label>
                        <span className="text-cyan-400">
                          {Math.round(daemonSettings?.clap_min_interval_ms ?? 150)}ms
                        </span>
                      </div>
                      <input
                        type="range"
                        min="80"
                        max="400"
                        step="10"
                        value={daemonSettings?.clap_min_interval_ms ?? 150}
                        onChange={(e) => {
                          voiceService.setSettings({
                            clap_min_interval_ms: parseFloat(e.target.value),
                          });
                        }}
                        className="w-full accent-cyan-400 bg-slate-800"
                      />
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        Anything faster than this is a room echo rather than a
                        second strike.
                      </span>
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <label className="text-slate-300">Train Guard</label>
                        <span className="text-cyan-400">
                          {Math.round(daemonSettings?.clap_pair_confirmation_ms ?? 450)}ms
                        </span>
                      </div>
                      <input
                        type="range"
                        min="150"
                        max="900"
                        step="10"
                        value={daemonSettings?.clap_pair_confirmation_ms ?? 450}
                        onChange={(e) => {
                          voiceService.setSettings({
                            clap_pair_confirmation_ms: parseFloat(e.target.value),
                          });
                        }}
                        className="w-full accent-cyan-400 bg-slate-800"
                      />
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        A third sound inside this window cancels the pair, so a
                        burst of key presses is not a double clap. It also delays
                        the activation by the same amount.
                      </span>
                    </div>
                  </div>
                )}

                {/* Live Activation Daemon Telemetry */}
                <div className="mt-4 p-3 rounded-lg border border-cyan-500/20 bg-slate-900/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 font-semibold flex items-center gap-1.5">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          connectionState === 'connected'
                            ? daemonStatus?.state === 'monitoring'
                              ? 'bg-cyan-400 animate-pulse shadow-[0_0_6px_#43CFFF]'
                              : 'bg-amber-400'
                            : 'bg-slate-600'
                        }`}
                      />
                      LOCAL ACTIVATION DAEMON
                    </span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                        connectionState === 'connected'
                          ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-500/30'
                          : 'bg-slate-950/60 text-slate-500 border border-slate-800'
                      }`}
                    >
                      {connectionState === 'connected'
                        ? daemonStatus?.state === 'monitoring'
                          ? 'ACTIVE (LOOPBACK)'
                          : 'PAUSED'
                        : 'OFFLINE (DISCONNECTED)'}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-1 text-[11px] text-slate-400 font-mono">
                    <div>
                      <span className="text-slate-500">DAEMON ENDPOINT: </span>
                      <span className="text-slate-300">ws://127.0.0.1:8765</span>
                    </div>
                    <div>
                      <span className="text-slate-500">AUDIO HARDWARE: </span>
                      <span className="text-slate-300 truncate block">
                        {daemonStatus?.audio_device || 'PipeWire / Default'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">SAMPLE RATE: </span>
                      <span className="text-slate-300">
                        {daemonStatus?.sample_rate ? `${daemonStatus.sample_rate} Hz` : '44,100 Hz'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">AMBIENT NOISE: </span>
                      <span className="text-cyan-400">
                        {daemonStatus?.noise_floor ? `${daemonStatus.noise_floor} RMS` : 'Calibrated'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-2 flex items-center justify-between">
                  <div>
                    <div className="text-slate-200 font-medium">Speaker Identification (Voiceprint)</div>
                    <div className="text-[11px] text-slate-500">
                      Matches incoming audio embedding against enrolled user profile (Joshua)
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.speakerIdentificationEnabled}
                    onChange={(e) => {
                      onUpdateSettings({ speakerIdentificationEnabled: e.target.checked });
                      showSaveNotice();
                    }}
                    className="w-4 h-4 accent-cyan-400"
                  />
                </div>
              </div>
            </section>
          )}

          {/* TAB 4: Audio Input & Output */}
          {activeTab === 'audio' && (
            <section className="space-y-5">
              <header className="border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-100">4. Audio Input & Output</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Web Audio harmonic feedback chimes and local speech synthesis.
                </p>
              </header>

              <div className="space-y-4 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-slate-200 font-medium">Web Audio Harmonic Chimes</div>
                    <div className="text-[11px] text-slate-500">
                      Algorithmic JARVIS-style synthesizer tones during state changes
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.audioFeedbackEnabled}
                    onChange={(e) => {
                      onUpdateSettings({ audioFeedbackEnabled: e.target.checked });
                      showSaveNotice();
                    }}
                    className="w-4 h-4 accent-cyan-400"
                  />
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-slate-300">Feedback Volume</label>
                    <span className="text-cyan-400">{Math.round(settings.soundVolume * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={settings.soundVolume}
                    onChange={(e) => {
                      onUpdateSettings({ soundVolume: parseFloat(e.target.value) });
                      showSaveNotice();
                    }}
                    className="w-full accent-cyan-400 bg-slate-800"
                  />
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div>
                    <div className="text-slate-200 font-medium">Noise Suppression & Echo Cancellation</div>
                    <div className="text-[11px] text-slate-500">
                      Applies browser / PulseAudio WebRTC filter to capture clean voice
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.noiseSuppression}
                    onChange={(e) => {
                      onUpdateSettings({ noiseSuppression: e.target.checked });
                      showSaveNotice();
                    }}
                    className="w-4 h-4 accent-cyan-400"
                  />
                </div>
              </div>
            </section>
          )}

          {/* TAB 5: Database & Memory */}
          {activeTab === 'database' && (
            <section className="space-y-5">
              <header className="border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-100">5. Database & Memory Store</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  PostgreSQL relational schema and vector memory parameters.
                </p>
              </header>

              <div className="space-y-4 text-xs font-mono">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 mb-1">Host</label>
                    <input
                      type="text"
                      value={settings.postgresHost}
                      onChange={(e) => {
                        onUpdateSettings({ postgresHost: e.target.value });
                        showSaveNotice();
                      }}
                      className="w-full h-10 bg-slate-900 border border-slate-800 rounded px-3 text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 mb-1">Port</label>
                    <input
                      type="number"
                      value={settings.postgresPort}
                      onChange={(e) => {
                        onUpdateSettings({ postgresPort: parseInt(e.target.value, 10) });
                        showSaveNotice();
                      }}
                      className="w-full h-10 bg-slate-900 border border-slate-800 rounded px-3 text-slate-200"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 mb-1">Database Name</label>
                  <input
                    type="text"
                    value={settings.postgresDatabase}
                    onChange={(e) => {
                      onUpdateSettings({ postgresDatabase: e.target.value });
                      showSaveNotice();
                    }}
                    className="w-full h-10 bg-slate-900 border border-slate-800 rounded px-3 text-slate-200"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    Existing PostgreSQL database on Fedora Linux host: "choomba"
                  </span>
                </div>

                <div className="pt-2 flex items-center justify-between">
                  <div>
                    <div className="text-slate-200 font-medium">Local Database Encryption at Rest</div>
                    <div className="text-[11px] text-slate-500">
                      Encrypts dialogue turns and user embeddings with LUKS / AES-256
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.encryptionAtRest}
                    onChange={(e) => {
                      onUpdateSettings({ encryptionAtRest: e.target.checked });
                      showSaveNotice();
                    }}
                    className="w-4 h-4 accent-cyan-400"
                  />
                </div>
              </div>
            </section>
          )}

          {/* TAB 6: Privacy & Offline Operation */}
          {activeTab === 'privacy' && (
            <section className="space-y-5">
              <header className="border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-100">6. Privacy & Offline Operation</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Strict local execution fence and telemetry eradication.
                </p>
              </header>

              <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-500/30 text-xs font-mono text-emerald-300 space-y-2">
                <div className="flex items-center gap-2 font-semibold">
                  <Shield className="w-4 h-4 text-emerald-400" />
                  STRICT OFFLINE GUARANTEE ACTIVE
                </div>
                <p className="text-[11px] leading-relaxed text-slate-300">
                  Choomba is architected to operate with zero outbound external network communication. All inference runs via local Ollama weights on the RTX 3060.
                </p>
              </div>

              <div className="space-y-4 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-slate-200 font-medium">Strict Localhost-Only Firewall</div>
                    <div className="text-[11px] text-slate-500">
                      Disallows any network sockets outside 127.0.0.1
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.strictOfflineOnly}
                    onChange={(e) => {
                      onUpdateSettings({ strictOfflineOnly: e.target.checked });
                      showSaveNotice();
                    }}
                    className="w-4 h-4 accent-cyan-400"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-slate-200 font-medium">Analytics & Tracking Telemetry</div>
                    <div className="text-[11px] text-slate-500">
                      Permanently disabled (Zero tracking scripts, zero metrics outbound)
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    disabled
                    checked={false}
                    className="w-4 h-4 opacity-50 cursor-not-allowed"
                  />
                </div>
              </div>
            </section>
          )}

          {/* TAB 7: System Status */}
          {activeTab === 'system' && (
            <section className="space-y-5">
              <header className="border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-100">7. Host Environment & System Status</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Fedora Linux workstation specifications and systemd daemon inspection.
                </p>
              </header>

              <div className="space-y-3 text-xs font-mono">
                <div className="p-3 rounded bg-slate-900/60 border border-slate-800 space-y-1.5">
                  <div className="text-slate-400">OPERATING SYSTEM:</div>
                  <div className="text-slate-100 font-medium">Fedora 40 (GNOME 46 / Wayland)</div>
                </div>

                <div className="p-3 rounded bg-slate-900/60 border border-slate-800 space-y-1.5">
                  <div className="text-slate-400">GPU ACCELERATION:</div>
                  <div className="text-slate-100 font-medium">NVIDIA GeForce RTX 3060 (12 GB VRAM)</div>
                  <div className="text-[11px] text-cyan-400">Active allocation: ~6.4 GB for Qwen 3.5 9B Q4</div>
                </div>

                <div className="p-3 rounded bg-slate-900/60 border border-slate-800 space-y-1.5">
                  <div className="text-slate-400">SYSTEM MEMORY:</div>
                  <div className="text-slate-100 font-medium">16 GB DDR4 (8.2 GB In Use)</div>
                </div>

                <div className="p-3 rounded bg-slate-900/60 border border-slate-800 space-y-1.5">
                  <div className="text-slate-400">SYSTEMD SERVICE:</div>
                  <div className="text-emerald-400 font-medium">choomba-daemon.service (Active / Running)</div>
                </div>
              </div>
            </section>
          )}

          {/* TAB 8: Future Integrations */}
          {activeTab === 'integrations' && (
            <section className="space-y-5">
              <header className="border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-slate-100">8. Future Local Integrations</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  External tools connecting locally to Choomba.
                </p>
              </header>

              <div className="space-y-4 text-xs font-mono">
                {/* Obsidian Vault */}
                <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-100 flex items-center gap-2">
                      <Layers className="w-4 h-4 text-cyan-400" />
                      Obsidian Knowledge Vault
                    </span>
                    <span className="text-[10px] text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30">
                      SYNC READY
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 font-sans">
                    Indexes markdown notes, research logs, and project blueprints into PostgreSQL embeddings.
                  </p>
                  <div>
                    <label className="block text-[11px] text-slate-500 mb-1">Local Vault Directory</label>
                    <input
                      type="text"
                      value={settings.obsidianVaultPath}
                      onChange={(e) => {
                        onUpdateSettings({ obsidianVaultPath: e.target.value });
                        showSaveNotice();
                      }}
                      className="w-full h-9 bg-slate-950 border border-slate-800 rounded px-3 text-slate-300 text-xs"
                    />
                  </div>
                </div>

                {/* Home Assistant */}
                <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-100 flex items-center gap-2">
                      <ExternalLink className="w-4 h-4 text-cyan-400" />
                      Home Assistant (Local Webhook)
                    </span>
                    <span className="text-[10px] text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-500/30">
                      OPTIONAL
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 font-sans">
                    Allows Choomba to dispatch local smart home actions (lights, climate) over LAN without cloud services.
                  </p>
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-slate-300">Enable Local HA Webhook</span>
                    <input
                      type="checkbox"
                      checked={settings.homeAssistantEnabled}
                      onChange={(e) => {
                        onUpdateSettings({ homeAssistantEnabled: e.target.checked });
                        showSaveNotice();
                      }}
                      className="w-4 h-4 accent-cyan-400"
                    />
                  </div>
                </div>
              </div>
            </section>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="h-14 px-6 border-t border-slate-800/90 flex items-center justify-between shrink-0 bg-[#050A12] text-xs font-mono text-slate-400">
        <span>CHOOMBA v0.1.0-PROTOTYPE</span>
        <button
          onClick={onClose}
          className="px-4 py-1.5 rounded bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/30 transition-colors"
        >
          CLOSE SETTINGS
        </button>
      </div>
    </aside>
  );
};
