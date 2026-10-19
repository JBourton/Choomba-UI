import React from 'react';
import { Play, Sparkles } from 'lucide-react';
import { AssistantState } from '../types/assistant';

interface DevStateSwitcherProps {
  currentState: AssistantState;
  onSelectState: (state: AssistantState) => void;
  onRunFullDemoSequence: () => void;
  isSequenceRunning: boolean;
  onSimulateClap?: () => void;
}

const STATES: { id: AssistantState; label: string; desc: string }[] = [
  { id: 'IDLE', label: 'IDLE', desc: 'Calm breathing glow & slow orbits' },
  { id: 'ACTIVATED', label: 'ACTIVATED', desc: 'Core flash & alignment' },
  { id: 'LISTENING', label: 'LISTENING', desc: 'Luminous cyan & audio pulse' },
  { id: 'IDENTIFYING', label: 'IDENTIFYING', desc: 'Speaker voice print match' },
  { id: 'THINKING', label: 'THINKING', desc: 'Fast counter-rotation arcs' },
  { id: 'SPEAKING', label: 'SPEAKING', desc: 'Rhythmic pulsing & waveform' },
  { id: 'ERROR', label: 'ERROR', desc: 'Restrained amber/coral warning' },
  { id: 'OFFLINE', label: 'OFFLINE', desc: 'Dimmed slate & disconnect mark' },
];

export const DevStateSwitcher: React.FC<DevStateSwitcherProps> = ({
  currentState,
  onSelectState,
  onRunFullDemoSequence,
  isSequenceRunning,
  onSimulateClap,
}) => {
  return (
    <div className="w-full bg-[#050A12]/95 border-t border-cyan-500/20 px-4 py-2.5 backdrop-blur-md relative z-20">
      <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-mono text-cyan-400 font-semibold tracking-wider text-[11px] uppercase flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse" />
            DEV STATE MACHINE:
          </span>
          <span className="text-[11px] text-slate-500 hidden sm:inline">
            (Manual override for UI testing)
          </span>
        </div>

        {/* State Buttons */}
        <div className="flex flex-wrap items-center gap-1.5">
          {STATES.map((s) => {
            const isActive = currentState === s.id;
            return (
              <button
                key={s.id}
                onClick={() => onSelectState(s.id)}
                disabled={isSequenceRunning}
                title={s.desc}
                className={`px-2.5 py-1 rounded font-mono text-[11px] transition-all cursor-pointer border ${
                  isActive
                    ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_8px_rgba(67,207,255,0.3)] font-semibold'
                    : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                } ${isSequenceRunning ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {s.label}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2">
          {onSimulateClap && (
            <button
              onClick={onSimulateClap}
              disabled={isSequenceRunning}
              title="Send a simulated double-clap event to test activation roundtrip without physical microphone"
              className="px-2.5 py-1 rounded font-mono text-[11px] flex items-center gap-1.5 border border-cyan-500/30 bg-slate-900/60 text-cyan-300 hover:border-cyan-400 hover:text-white transition-all cursor-pointer"
            >
              <span>👏</span>
              <span>SIMULATE CLAP</span>
            </button>
          )}

          {/* Automated Full Loop Sequence Trigger */}
          <button
            onClick={onRunFullDemoSequence}
            disabled={isSequenceRunning}
            title="Run complete automated JARVIS interaction loop"
            className={`px-3 py-1 rounded font-mono text-[11px] flex items-center gap-1.5 border transition-all ${
              isSequenceRunning
                ? 'bg-cyan-500/30 border-cyan-400 text-cyan-200 animate-pulse'
                : 'bg-gradient-to-r from-cyan-950/60 to-blue-950/60 border-cyan-500/40 text-cyan-300 hover:border-cyan-400 hover:text-white'
            }`}
          >
            {isSequenceRunning ? (
              <>
                <Sparkles className="w-3.5 h-3.5 text-cyan-300 animate-spin" />
                <span>RUNNING SEQUENCE...</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 text-cyan-400" />
                <span>TEST FULL LOOP</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
