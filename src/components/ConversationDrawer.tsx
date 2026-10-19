import React, { useRef, useEffect } from 'react';
import { X, Trash2, RotateCcw, User, ShieldCheck, Cpu } from 'lucide-react';
import { ChatMessage, OllamaModelInfo } from '../types/assistant';

interface ConversationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  messages: ChatMessage[];
  onClearSession: () => void;
  onRestartSession: () => void;
  activeModel: OllamaModelInfo;
}

export const ConversationDrawer: React.FC<ConversationDrawerProps> = ({
  isOpen,
  onClose,
  messages,
  onClearSession,
  onRestartSession,
  activeModel,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

  // Compute total session tokens
  const totalTokens = messages.reduce((acc, m) => acc + (m.tokens || 0), 0);

  if (!isOpen) return null;

  return (
    <aside
      aria-label="Conversation Activity Drawer"
      className="fixed inset-y-0 right-0 w-full sm:w-[440px] bg-[#050A12]/95 backdrop-blur-2xl border-l border-cyan-500/20 z-40 flex flex-col shadow-[-10px_0_30px_rgba(0,0,0,0.8)] transition-all duration-300"
    >
      {/* Header */}
      <div className="h-14 px-5 border-b border-cyan-500/15 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400" />
          <h2 className="text-xs font-mono font-semibold tracking-wider text-slate-100 uppercase">
            CONVERSATION BUFFER
          </h2>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800/40 transition-colors"
          title="Close conversation drawer (Esc)"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Session Metadata Strip (Zero-pill text format) */}
      <div className="px-5 py-3 border-b border-slate-800/80 bg-slate-950/40 text-xs font-mono text-slate-400 flex flex-col gap-1.5 shrink-0">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-slate-300">
            <User className="w-3.5 h-3.5 text-cyan-400" />
            OPERATOR: Joshua (Primary)
          </span>
          <span className="text-[11px] text-emerald-400 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3" />
            LOCAL PG MEMORY
          </span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-500">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-cyan-500" />
            {activeModel.id}
          </span>
          <span>SESSION TOKENS: {totalTokens}</span>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 text-xs font-mono p-6">
            <p>Session buffer empty.</p>
            <p className="mt-1 text-slate-600">
              Submit a prompt via the command deck or speak into the microphone to initiate activity.
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'user';
            const isSystem = msg.role === 'system';

            if (isSystem) {
              return (
                <div
                  key={msg.id}
                  className="py-1 px-3 rounded bg-slate-900/50 border border-slate-800/60 text-center font-mono text-[11px] text-slate-400"
                >
                  {msg.content}
                </div>
              );
            }

            return (
              <div
                key={msg.id}
                className={`flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}
              >
                {/* Meta line: speaker and timestamp */}
                <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 px-1">
                  <span>{msg.speaker || (isUser ? 'USER' : 'CHOOMBA')}</span>
                  <span aria-hidden="true">·</span>
                  <span>{msg.timestamp}</span>
                  {msg.tokens && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span>{msg.tokens} tokens</span>
                    </>
                  )}
                </div>

                {/* Message bubble */}
                <div
                  className={`max-w-[90%] rounded-lg px-3.5 py-2.5 text-xs leading-relaxed ${
                    isUser
                      ? 'bg-cyan-950/40 border border-cyan-500/30 text-slate-100'
                      : 'bg-slate-900/70 border border-slate-800 text-slate-200'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Prototype Simulated Disclaimer Note */}
      <div className="px-5 py-2 bg-cyan-950/20 border-t border-cyan-500/10 text-[10px] font-mono text-cyan-400/80 text-center shrink-0">
        PROTOTYPE SIMULATION · ZERO EXTERNAL TELEMETRY
      </div>

      {/* Drawer Action Bar */}
      <div className="p-4 border-t border-slate-800/90 flex items-center justify-between gap-3 shrink-0 bg-[#050A12]">
        <button
          onClick={onRestartSession}
          className="flex-1 py-2 px-3 rounded border border-slate-800 bg-slate-900/50 hover:bg-slate-800/60 text-slate-300 hover:text-white transition-colors font-mono text-xs flex items-center justify-center gap-2"
        >
          <RotateCcw className="w-3.5 h-3.5 text-cyan-400" />
          NEW SESSION
        </button>
        <button
          onClick={onClearSession}
          className="py-2 px-3 rounded border border-rose-950/50 bg-rose-950/20 hover:bg-rose-900/30 text-rose-300 hover:text-rose-200 transition-colors font-mono text-xs flex items-center gap-1.5"
          title="Clear all messages in buffer"
        >
          <Trash2 className="w-3.5 h-3.5" />
          CLEAR
        </button>
      </div>
    </aside>
  );
};
