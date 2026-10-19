import React, { useMemo } from 'react';
import { AssistantState } from '../../types/assistant';

interface HolographicOrbProps {
  state: AssistantState;
  size?: number;
  className?: string;
  onClick?: () => void;
}

export const HolographicOrb: React.FC<HolographicOrbProps> = ({
  state,
  size = 380,
  className = '',
  onClick,
}) => {
  // Theme styling based on assistant state
  const stateTheme = useMemo(() => {
    switch (state) {
      case 'LISTENING':
        return {
          primary: '#43CFFF',
          secondary: '#38BDF8',
          glow: 'rgba(67, 207, 255, 0.45)',
          coreScale: 1.15,
          spinClass: 'animate-spin-medium',
          reverseSpinClass: 'animate-spin-reverse-medium',
          pulseClass: 'animate-pulse-listening',
          innerOpacity: 0.95,
        };
      case 'IDENTIFYING':
        return {
          primary: '#38BDF8',
          secondary: '#60A5FA',
          glow: 'rgba(56, 189, 248, 0.4)',
          coreScale: 1.05,
          spinClass: 'animate-spin-medium',
          reverseSpinClass: 'animate-spin-reverse-fast',
          pulseClass: 'animate-pulse-core',
          innerOpacity: 0.9,
        };
      case 'THINKING':
        return {
          primary: '#67E8F9',
          secondary: '#1677FF',
          glow: 'rgba(103, 232, 249, 0.55)',
          coreScale: 1.08,
          spinClass: 'animate-spin-fast',
          reverseSpinClass: 'animate-spin-reverse-fast',
          pulseClass: 'animate-pulse-core',
          innerOpacity: 0.95,
        };
      case 'SPEAKING':
        return {
          primary: '#43CFFF',
          secondary: '#0284C7',
          glow: 'rgba(67, 207, 255, 0.5)',
          coreScale: 1.12,
          spinClass: 'animate-spin-medium',
          reverseSpinClass: 'animate-spin-reverse-slow',
          pulseClass: 'animate-pulse-speaking',
          innerOpacity: 0.95,
        };
      case 'ACTIVATED':
        return {
          primary: '#43CFFF',
          secondary: '#22D3EE',
          glow: 'rgba(67, 207, 255, 0.6)',
          coreScale: 1.1,
          spinClass: 'animate-spin-medium',
          reverseSpinClass: 'animate-spin-reverse-medium',
          pulseClass: 'animate-pulse-core',
          innerOpacity: 0.9,
        };
      case 'ERROR':
        return {
          primary: '#FB7185',
          secondary: '#E11D48',
          glow: 'rgba(251, 113, 133, 0.35)',
          coreScale: 0.95,
          spinClass: 'animate-spin-slow',
          reverseSpinClass: 'animate-spin-reverse-slow',
          pulseClass: 'animate-pulse-core',
          innerOpacity: 0.7,
        };
      case 'OFFLINE':
        return {
          primary: '#475569',
          secondary: '#1E293B',
          glow: 'rgba(71, 85, 105, 0.1)',
          coreScale: 0.88,
          spinClass: '',
          reverseSpinClass: '',
          pulseClass: '',
          innerOpacity: 0.35,
        };
      case 'IDLE':
      default:
        return {
          primary: '#43CFFF',
          secondary: '#1677FF',
          glow: 'rgba(67, 207, 255, 0.25)',
          coreScale: 1.0,
          spinClass: 'animate-spin-slow',
          reverseSpinClass: 'animate-spin-reverse-slow',
          pulseClass: 'animate-pulse-core',
          innerOpacity: 0.85,
        };
    }
  }, [state]);

  // Generate 48 technical radial tick marks around 360 degrees
  const radialTicks = useMemo(() => {
    const ticks = [];
    const count = 48;
    const center = 250;
    const radius = 205;
    for (let i = 0; i < count; i++) {
      const angle = (i * 360) / count;
      const rad = (angle * Math.PI) / 180;
      const isMajor = i % 4 === 0;
      const length = isMajor ? 9 : 4.5;
      const x1 = center + radius * Math.cos(rad);
      const y1 = center + radius * Math.sin(rad);
      const x2 = center + (radius - length) * Math.cos(rad);
      const y2 = center + (radius - length) * Math.sin(rad);
      ticks.push({ x1, y1, x2, y2, isMajor, key: `tick-${i}` });
    }
    return ticks;
  }, []);

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`Holographic assistant core in ${state} state`}
      className={`relative flex items-center justify-center select-none cursor-pointer group focus:outline-none ${className}`}
      style={{ width: size, height: size }}
    >
      {/* Ambient background bloom halo */}
      <div
        className="absolute inset-0 rounded-full blur-3xl transition-all duration-700 pointer-events-none"
        style={{
          background: `radial-gradient(circle, ${stateTheme.glow} 0%, rgba(22, 119, 255, 0.08) 55%, transparent 75%)`,
          transform: `scale(${stateTheme.coreScale * 1.08})`,
        }}
      />

      {/* Main Layered SVG Orb */}
      <svg
        viewBox="0 0 500 500"
        className="w-full h-full relative z-10 transition-transform duration-700 overflow-visible"
        style={{ filter: 'drop-shadow(0 0 12px rgba(67, 207, 255, 0.15))' }}
      >
        <defs>
          {/* Luminous Core Gradient */}
          <radialGradient id="coreEnergyGradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.95" />
            <stop offset="25%" stopColor={stateTheme.primary} stopOpacity={stateTheme.innerOpacity} />
            <stop offset="65%" stopColor={stateTheme.secondary} stopOpacity="0.4" />
            <stop offset="100%" stopColor="#050A12" stopOpacity="0" />
          </radialGradient>

          {/* Hologram Arc Gradient */}
          <linearGradient id="arcSweepGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={stateTheme.primary} stopOpacity="0.85" />
            <stop offset="50%" stopColor={stateTheme.secondary} stopOpacity="0.3" />
            <stop offset="100%" stopColor={stateTheme.primary} stopOpacity="0" />
          </linearGradient>

          {/* Subtle Glow Filter */}
          <filter id="cyanGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* LAYER 1: Deep static background reticle and boundary circle */}
        <circle
          cx="250"
          cy="250"
          r="230"
          fill="none"
          stroke="rgba(67, 207, 255, 0.08)"
          strokeWidth="1"
          strokeDasharray="4 8"
        />

        {/* LAYER 2: Outermost slow orbital ring with alignment notches */}
        <g className={stateTheme.spinClass} style={{ transformOrigin: '250px 250px' }}>
          <circle
            cx="250"
            cy="250"
            r="215"
            fill="none"
            stroke={stateTheme.primary}
            strokeWidth="1.2"
            strokeOpacity="0.3"
            strokeDasharray="40 12 120 18 60 25"
          />
          {/* Orbital traveling node point */}
          {state !== 'OFFLINE' && (
            <circle
              cx="250"
              cy="35"
              r="3.5"
              fill={stateTheme.primary}
              filter="url(#cyanGlow)"
              opacity="0.9"
            />
          )}
        </g>

        {/* LAYER 3: Radial technical ticks ring (Precision instrumentation) */}
        <g className={stateTheme.reverseSpinClass} style={{ transformOrigin: '250px 250px' }}>
          {radialTicks.map((t) => (
            <line
              key={t.key}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              stroke={stateTheme.primary}
              strokeWidth={t.isMajor ? '1.5' : '1'}
              strokeOpacity={t.isMajor ? '0.55' : '0.2'}
            />
          ))}
          <circle
            cx="250"
            cy="250"
            r="192"
            fill="none"
            stroke={stateTheme.secondary}
            strokeWidth="1"
            strokeOpacity="0.25"
          />
        </g>

        {/* LAYER 4: Dynamic partial arcs (Accelerate in THINKING, expand in LISTENING) */}
        <g className={stateTheme.spinClass} style={{ transformOrigin: '250px 250px' }}>
          <path
            d="M 250,75 A 175,175 0 0,1 425,250"
            fill="none"
            stroke={stateTheme.primary}
            strokeWidth={state === 'LISTENING' || state === 'THINKING' ? '2.5' : '1.8'}
            strokeOpacity={state === 'OFFLINE' ? '0.2' : '0.8'}
            strokeLinecap="round"
            filter="url(#cyanGlow)"
          />
          <path
            d="M 250,425 A 175,175 0 0,1 75,250"
            fill="none"
            stroke={stateTheme.primary}
            strokeWidth={state === 'LISTENING' || state === 'THINKING' ? '2.5' : '1.8'}
            strokeOpacity={state === 'OFFLINE' ? '0.2' : '0.7'}
            strokeLinecap="round"
            filter="url(#cyanGlow)"
          />
        </g>

        {/* Counter-rotating segmented middle arc */}
        <g className={stateTheme.reverseSpinClass} style={{ transformOrigin: '250px 250px' }}>
          <circle
            cx="250"
            cy="250"
            r="150"
            fill="none"
            stroke={stateTheme.primary}
            strokeWidth="1.5"
            strokeOpacity="0.35"
            strokeDasharray="20 40 80 30"
          />
          {state === 'THINKING' && (
            <circle
              cx="400"
              cy="250"
              r="4"
              fill={stateTheme.primary}
              filter="url(#cyanGlow)"
            />
          )}
        </g>

        {/* LAYER 5: Inner orbital ring with technical segment markers */}
        <circle
          cx="250"
          cy="250"
          r="125"
          fill="none"
          stroke="rgba(67, 207, 255, 0.2)"
          strokeWidth="1"
          strokeDasharray="6 6"
        />

        {/* LAYER 6: Precision crosshairs & coordinate markers */}
        {state !== 'OFFLINE' && (
          <g opacity="0.35">
            <line x1="250" y1="130" x2="250" y2="155" stroke={stateTheme.primary} strokeWidth="1" />
            <line x1="250" y1="345" x2="250" y2="370" stroke={stateTheme.primary} strokeWidth="1" />
            <line x1="130" y1="250" x2="155" y2="250" stroke={stateTheme.primary} strokeWidth="1" />
            <line x1="345" y1="250" x2="370" y2="250" stroke={stateTheme.primary} strokeWidth="1" />
          </g>
        )}

        {/* LAYER 7: Central Energy Nucleus (Breathing / Pulse / Speaking modulation) */}
        <g className={stateTheme.pulseClass} style={{ transformOrigin: '250px 250px' }}>
          {/* Energy core sphere */}
          <circle
            cx="250"
            cy="250"
            r={state === 'LISTENING' ? '92' : state === 'THINKING' ? '86' : '78'}
            fill="url(#coreEnergyGradient)"
            className="transition-all duration-500"
          />

          {/* High-frequency inner core ring */}
          <circle
            cx="250"
            cy="250"
            r="54"
            fill="none"
            stroke={stateTheme.primary}
            strokeWidth="1.5"
            strokeOpacity={state === 'OFFLINE' ? '0.2' : '0.75'}
            strokeDasharray="14 18"
            className={stateTheme.spinClass}
            style={{ transformOrigin: '250px 250px' }}
          />

          {/* Dense center focal node */}
          <circle
            cx="250"
            cy="250"
            r={state === 'OFFLINE' ? '12' : state === 'ERROR' ? '16' : '18'}
            fill={stateTheme.primary}
            opacity={state === 'OFFLINE' ? '0.4' : '0.95'}
            filter={state !== 'OFFLINE' ? 'url(#cyanGlow)' : undefined}
          />
        </g>

        {/* OFFLINE INDICATOR OVERLAY: Subtle diagonal disconnect slash */}
        {state === 'OFFLINE' && (
          <g opacity="0.6">
            <line
              x1="180"
              y1="180"
              x2="320"
              y2="320"
              stroke="#64748B"
              strokeWidth="2"
              strokeDasharray="8 6"
            />
          </g>
        )}

        {/* ERROR STATE: Warning indicator accents */}
        {state === 'ERROR' && (
          <g opacity="0.8">
            <circle
              cx="250"
              cy="250"
              r="105"
              fill="none"
              stroke="#F43F5E"
              strokeWidth="1.8"
              strokeDasharray="18 12"
            />
          </g>
        )}
      </svg>
    </div>
  );
};
