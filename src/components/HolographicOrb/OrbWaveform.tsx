import React from 'react';
import { AssistantState } from '../../types/assistant';

interface OrbWaveformProps {
  state: AssistantState;
  className?: string;
}

export const OrbWaveform: React.FC<OrbWaveformProps> = ({ state, className = '' }) => {
  const isAudioActive = state === 'LISTENING' || state === 'SPEAKING';
  const barCount = 32;

  // Generate bar heights dynamically based on state
  return (
    <div
      aria-hidden="true"
      className={`flex items-center justify-center gap-[3px] h-8 transition-opacity duration-500 ${
        isAudioActive ? 'opacity-90' : 'opacity-20'
      } ${className}`}
    >
      {Array.from({ length: barCount }).map((_, i) => {
        // Compute pseudo-symmetrical wave
        const distFromCenter = Math.abs(i - barCount / 2) / (barCount / 2);
        const baseFactor = 1 - distFromCenter * 0.7;

        // Dynamic style based on state
        let heightClass = 'h-1.5';
        let bgClass = 'bg-cyan-500/30';
        let animStyle: React.CSSProperties = {};

        if (state === 'LISTENING') {
          bgClass = 'bg-[#43CFFF]';
          animStyle = {
            height: `${Math.max(4, Math.sin((i / 4) + Date.now() / 200) * 16 * baseFactor + 10)}px`,
            transition: 'height 120ms ease-in-out',
          };
        } else if (state === 'SPEAKING') {
          bgClass = 'bg-[#43CFFF] shadow-[0_0_6px_rgba(67,207,255,0.8)]';
          animStyle = {
            height: `${Math.max(4, ((i * 7) % 24 + 6) * baseFactor)}px`,
            transition: 'height 90ms ease-in-out',
          };
        } else if (state === 'ERROR') {
          bgClass = 'bg-rose-500/40';
          animStyle = { height: '3px' };
        } else if (state === 'OFFLINE') {
          bgClass = 'bg-slate-700/30';
          animStyle = { height: '2px' };
        } else {
          // Idle subtle resting bar
          bgClass = 'bg-cyan-500/25';
          animStyle = { height: `${Math.max(2, 4 * baseFactor)}px` };
        }

        return (
          <div
            key={i}
            className={`w-[2.5px] rounded-full transition-colors duration-300 ${bgClass} ${heightClass}`}
            style={animStyle}
          />
        );
      })}
    </div>
  );
};
