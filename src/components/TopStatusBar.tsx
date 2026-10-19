import React from 'react';
import { Volume2, VolumeX, MessageSquare, Settings, Info, ChevronDown } from 'lucide-react';
import { AssistantState, OllamaModelInfo } from '../types/assistant';

interface TopStatusBarProps {
  state: AssistantState;
  activeModel: OllamaModelInfo;
  isMuted: boolean;
  onToggleMute: () => void;
  onOpenModelSelector: () => void;
  onToggleConversation: () => void;
  onToggleSettings: () => void;
  onOpenArchitectureGuide: () => void;
  conversationOpen: boolean;
  settingsOpen: boolean;
  isMonitoring?: boolean;
  daemonConnected?: boolean;
  onToggleMonitoring?: () => void;
}

export const TopStatusBar: React.FC<TopStatusBarProps> = ({
  state,
  activeModel,
  isMuted,
  onToggleMute,
  onOpenModelSelector,
  onToggleConversation,
  onToggleSettings,
  onOpenArchitectureGuide,
  conversationOpen,
  settingsOpen,
  isMonitoring = false,
  daemonConnected = false,
  onToggleMonitoring,
}) => {
  return (
    <header className="w-full h-14 bg-[#050A12]/80 backdrop-blur-md border-b border-cyan-500/15 px-4 md:px-6 flex items-center justify-between gap-4 select-none relative z-30">
      {/* Zone 1: Brand Wordmark with custom geometric symbol */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="relative flex items-center justify-center w-7 h-7">
          {/* Custom diamond-hex geometric emblem */}
          <svg viewBox="0 0 28 28" className="w-full h-full">
            <polygon
              points="14,2 26,8 26,20 14,26 2,20 2,8"
              fill="none"
              stroke="#43CFFF"
              strokeWidth="1.5"
              strokeOpacity="0.8"
            />
            <circle cx="14" cy="14" r="3" fill="#43CFFF" />
            <line x1="14" y1="2" x2="14" y2="7" stroke="#43CFFF" strokeWidth="1" strokeOpacity="0.6" />
            <line x1="14" y1="21" x2="14" y2="26" stroke="#43CFFF" strokeWidth="1" strokeOpacity="0.6" />
          </svg>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold tracking-wider text-slate-100 flex items-center gap-1.5 font-mono">
            CHOOMBA
            <span className="text-[10px] font-normal text-cyan-400/80 tracking-widest hidden sm:inline">
              / LOCAL ASSISTANT
            </span>
          </span>
        </div>
      </div>

      {/* Zone 2: Unboxed System Telemetry Metadata (Zero-pill discipline) */}
      <div className="hidden lg:flex items-center gap-3 text-xs font-mono text-slate-400">
        {/* Model Selector trigger */}
        <button
          onClick={onOpenModelSelector}
          title="Click to switch Ollama model"
          className="flex items-center gap-1.5 hover:text-cyan-400 transition-colors focus:outline-none cursor-pointer"
        >
          <span className="text-slate-500">MODEL:</span>
          <span className="text-slate-200 font-medium">{activeModel.name.toUpperCase()}</span>
          <ChevronDown className="w-3 h-3 text-slate-400" />
        </button>

        <span className="text-slate-600" aria-hidden="true">·</span>

        <span className="flex items-center gap-1.5">
          <span className="text-slate-500">INFERENCE:</span>
          <span className="text-cyan-400">LOCAL (RTX 3060)</span>
        </span>

        <span className="text-slate-600" aria-hidden="true">·</span>

        <span className="flex items-center gap-1.5">
          <span className="text-slate-500">DATABASE:</span>
          <span className="text-emerald-400">CONNECTED (PG)</span>
        </span>

        <span className="text-slate-600" aria-hidden="true">·</span>

        <span className="flex items-center gap-1.5">
          <span className="text-slate-500">STATE:</span>
          <span
            className={`font-medium ${
              state === 'ERROR'
                ? 'text-rose-400'
                : state === 'OFFLINE'
                ? 'text-slate-500'
                : 'text-cyan-300'
            }`}
          >
            {state}
          </span>
        </span>

        <span className="text-slate-600" aria-hidden="true">·</span>

        <button
          onClick={onToggleMonitoring}
          title={
            isMonitoring
              ? 'Microphone monitoring active (Click to pause clap detection)'
              : daemonConnected
              ? 'Microphone monitoring paused (Click to resume clap detection)'
              : 'Activation daemon offline (Run python3 -m backend.service)'
          }
          className="flex items-center gap-1.5 hover:text-cyan-400 transition-colors focus:outline-none cursor-pointer"
        >
          <span className="text-slate-500">MIC:</span>
          <span
            className={`flex items-center gap-1 font-medium ${
              isMonitoring
                ? 'text-cyan-400'
                : daemonConnected
                ? 'text-amber-400'
                : 'text-slate-500'
            }`}
          >
            {isMonitoring && (
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            )}
            {isMonitoring ? 'CLAP DETECTOR' : daemonConnected ? 'PAUSED' : 'OFFLINE'}
          </span>
        </button>
      </div>

      {/* Zone 3: Navigation and Utility Controls */}
      <div className="flex items-center gap-2 md:gap-3 shrink-0">
        {/* Audio Mute/Unmute Toggle */}
        <button
          onClick={onToggleMute}
          title={isMuted ? 'Sound muted (Click to enable audio feedback)' : 'Audio chimes active (Click to mute)'}
          className={`p-2 rounded-md transition-colors border text-xs flex items-center gap-1.5 ${
            isMuted
              ? 'border-slate-800 text-slate-500 hover:text-slate-300 hover:border-slate-700'
              : 'border-cyan-500/25 text-cyan-400 bg-cyan-950/20 hover:bg-cyan-900/30'
          }`}
        >
          {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          <span className="hidden sm:inline font-mono text-[11px]">{isMuted ? 'MUTED' : 'CHIMES'}</span>
        </button>

        {/* Architecture & Backend Readiness Guide */}
        <button
          onClick={onOpenArchitectureGuide}
          title="Inspect Local Architecture Blueprint (Ollama, PostgreSQL, systemd)"
          className="p-2 rounded-md transition-colors border border-cyan-500/20 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 bg-slate-900/40 text-xs flex items-center gap-1.5"
        >
          <Info className="w-4 h-4 text-cyan-400" />
          <span className="hidden md:inline font-mono text-[11px]">ARCH</span>
        </button>

        {/* Conversation Drawer Toggle */}
        <button
          onClick={onToggleConversation}
          title="Toggle conversation transcript drawer"
          className={`px-3 py-1.5 rounded-md transition-colors border text-xs font-mono flex items-center gap-1.5 ${
            conversationOpen
              ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300'
              : 'border-slate-800 text-slate-300 hover:border-slate-700 hover:text-slate-100 bg-slate-900/30'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5 text-cyan-400" />
          <span className="hidden sm:inline">TRANSCRIPT</span>
        </button>

        {/* Settings Drawer Toggle */}
        <button
          onClick={onToggleSettings}
          title="Open assistant settings and configuration"
          className={`p-2 rounded-md transition-colors border text-xs ${
            settingsOpen
              ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300'
              : 'border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200 bg-slate-900/30'
          }`}
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
