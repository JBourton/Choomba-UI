import React from 'react';
import { AssistantState } from '../types/assistant';
import { HolographicOrb } from './HolographicOrb/HolographicOrb';
import { OrbWaveform } from './HolographicOrb/OrbWaveform';

interface CentralStageProps {
  state: AssistantState;
  streamingText: string;
  transcription: string;
  onOrbClick: () => void;
}

export const CentralStage: React.FC<CentralStageProps> = ({
  state,
  streamingText,
  transcription,
  onOrbClick,
}) => {
  // Map internal state to user-facing JARVIS-style label
  const getStatusDisplay = (s: AssistantState) => {
    switch (s) {
      case 'ACTIVATED':
        return { label: 'ACTIVATED', color: 'text-cyan-300' };
      case 'LISTENING':
        return { label: 'LISTENING', color: 'text-cyan-400' };
      case 'IDENTIFYING':
        return { label: 'IDENTIFYING SPEAKER', color: 'text-sky-300' };
      case 'THINKING':
        return { label: 'PROCESSING', color: 'text-cyan-300' };
      case 'SPEAKING':
        return { label: 'SPEAKING', color: 'text-cyan-300' };
      case 'ERROR':
        return { label: 'ERROR DETECTED', color: 'text-rose-400' };
      case 'OFFLINE':
        return { label: 'OFFLINE', color: 'text-slate-500' };
      case 'IDLE':
      default:
        return { label: 'STANDBY', color: 'text-cyan-400/80' };
    }
  };

  const statusInfo = getStatusDisplay(state);

  // Determine what text preview to show
  const activePreview = streamingText || transcription || (
    state === 'LISTENING'
      ? 'Awaiting voice input or prompt...'
      : state === 'IDENTIFYING'
      ? 'Analyzing vocal acoustic signature (Joshua · 94% match)...'
      : state === 'THINKING'
      ? 'Executing local inference on RTX 3060...'
      : state === 'OFFLINE'
      ? 'Choomba daemon is disconnected. Click to reconnect.'
      : state === 'ERROR'
      ? 'Inference execution interrupted. Subsystems intact.'
      : 'Click the core or microphone to initiate voice command.'
  );

  return (
    <main className="flex-1 flex flex-col items-center justify-center p-4 relative z-10 overflow-hidden">
      {/* Background ambient circular grids for subtle depth */}
      <div
        className="absolute w-[620px] h-[620px] rounded-full border border-cyan-500/5 pointer-events-none select-none"
        aria-hidden="true"
      />
      <div
        className="absolute w-[860px] h-[860px] rounded-full border border-cyan-500/[0.03] pointer-events-none select-none"
        aria-hidden="true"
      />

      {/* Dominant Centered Holographic Core */}
      <div className="relative flex flex-col items-center">
        <HolographicOrb
          state={state}
          size={360}
          onClick={onOrbClick}
          className="hover:scale-[1.01] transition-transform duration-300"
        />

        {/* Audio waveform visualization beneath orb */}
        <div className="mt-3">
          <OrbWaveform state={state} />
        </div>

        {/* Contextual Status Label */}
        <div className="mt-4 flex flex-col items-center text-center">
          <div className="flex items-center gap-2 font-mono text-xs tracking-[0.25em] uppercase font-semibold">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                state === 'ERROR'
                  ? 'bg-rose-500'
                  : state === 'OFFLINE'
                  ? 'bg-slate-600'
                  : 'bg-cyan-400 shadow-[0_0_8px_#43CFFF]'
              }`}
            />
            <span className={statusInfo.color}>{statusInfo.label}</span>
          </div>

          {/* Transcription / Response Preview */}
          <div className="mt-3 max-w-xl px-6 min-h-[44px] flex items-center justify-center">
            <p
              className={`text-sm text-center font-light leading-relaxed transition-all duration-300 ${
                streamingText || transcription
                  ? 'text-slate-100 font-normal tracking-wide'
                  : 'text-slate-400 font-light'
              }`}
            >
              {activePreview}
              {state === 'THINKING' && (
                <span className="inline-block w-1.5 h-3 ml-1 bg-cyan-400 animate-pulse" />
              )}
            </p>
          </div>
        </div>
      </div>
    </main>
  );
};
