import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Send, Sliders } from 'lucide-react';
import { AssistantState } from '../types/assistant';

interface BottomCommandDeckProps {
  state: AssistantState;
  isListening: boolean;
  onToggleMic: () => void;
  onSubmitText: (text: string) => void;
  onToggleDevStateBar: () => void;
  devStateBarOpen: boolean;
}

export const BottomCommandDeck: React.FC<BottomCommandDeckProps> = ({
  state,
  isListening,
  onToggleMic,
  onSubmitText,
  onToggleDevStateBar,
  devStateBarOpen,
}) => {
  const [inputText, setInputText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim()) return;
    onSubmitText(inputText.trim());
    setInputText('');
  };

  // Keyboard shortcut: focus input on '/' or hotkey
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === '/' &&
        document.activeElement?.tagName !== 'INPUT' &&
        document.activeElement?.tagName !== 'TEXTAREA'
      ) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const isBusy = state === 'THINKING' || state === 'IDENTIFYING';

  return (
    <footer className="w-full bg-[#050A12]/90 backdrop-blur-md border-t border-cyan-500/15 py-3 px-4 md:px-8 select-none relative z-20">
      <div className="max-w-3xl mx-auto flex items-center gap-3">
        {/* Microphone Toggle (Push to talk or toggle listening) */}
        <button
          type="button"
          onClick={onToggleMic}
          disabled={state === 'OFFLINE'}
          title={isListening ? 'Click to stop listening' : 'Click to start voice input'}
          className={`relative p-3 rounded-lg border transition-all duration-200 flex items-center justify-center shrink-0 focus:outline-none focus:ring-1 focus:ring-cyan-400 ${
            isListening
              ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_12px_rgba(67,207,255,0.4)]'
              : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:border-cyan-500/30 hover:text-cyan-400'
          } ${state === 'OFFLINE' ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          {isListening ? (
            <>
              <Mic className="w-5 h-5 animate-pulse text-cyan-300" />
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-cyan-400 rounded-full animate-ping" />
            </>
          ) : (
            <Mic className="w-5 h-5" />
          )}
        </button>

        {/* Command Form */}
        <form onSubmit={handleSubmit} className="flex-1 flex items-center gap-2 relative">
          <div className="relative flex-1">
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isBusy || state === 'OFFLINE'}
              placeholder={
                state === 'OFFLINE'
                  ? 'Choomba is offline. Connect daemon in settings.'
                  : isListening
                  ? 'Listening for voice command...'
                  : 'Enter command or inquiry (Press / to focus)...'
              }
              className="w-full h-11 bg-slate-950/70 border border-slate-800/90 rounded-lg px-4 pr-10 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/40 transition-colors font-sans"
            />
            {inputText && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-slate-500 hidden sm:inline">
                ENTER ↵
              </span>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!inputText.trim() || isBusy || state === 'OFFLINE'}
            title="Submit command"
            className={`h-11 px-4 rounded-lg border font-mono text-xs flex items-center gap-2 transition-all shrink-0 ${
              inputText.trim() && !isBusy && state !== 'OFFLINE'
                ? 'bg-cyan-500/20 border-cyan-500/60 text-cyan-200 hover:bg-cyan-500/30 cursor-pointer shadow-[0_0_10px_rgba(67,207,255,0.2)]'
                : 'bg-slate-900/30 border-slate-800 text-slate-600 cursor-not-allowed'
            }`}
          >
            <span className="hidden sm:inline font-medium">SEND</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>

        {/* Dev State Controller Toggle */}
        <button
          type="button"
          onClick={onToggleDevStateBar}
          title="Toggle developer state simulation bar"
          className={`p-2.5 rounded-lg border transition-colors shrink-0 text-xs font-mono flex items-center gap-1.5 ${
            devStateBarOpen
              ? 'border-cyan-500/40 bg-cyan-950/30 text-cyan-300'
              : 'border-slate-800 text-slate-500 hover:text-slate-300 hover:border-slate-700 bg-slate-950/30'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span className="hidden md:inline text-[11px]">DEV STATES</span>
        </button>
      </div>
    </footer>
  );
};
