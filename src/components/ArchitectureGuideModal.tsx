import React, { useState } from 'react';
import { X, Code, Terminal, Database, Cpu, Shield, Copy, Check } from 'lucide-react';

interface ArchitectureGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ArchitectureGuideModal: React.FC<ArchitectureGuideModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  if (!isOpen) return null;

  const copyCode = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const SNIPPET_OLLAMA = `// How to replace MockModelService with real local Ollama API
export async function fetchOllamaModels(): Promise<OllamaModelInfo[]> {
  const res = await fetch('http://localhost:11434/api/tags');
  const data = await res.json();
  return data.models.map((m: any) => ({
    id: m.name,
    name: m.name.split(':')[0],
    tag: m.name,
    size: (m.size / (1024 ** 3)).toFixed(1) + ' GB',
    status: 'READY',
  }));
}`;

  const SNIPPET_STREAM = `// How to replace MockAssistantService with real Ollama streaming
export async function streamOllamaResponse(prompt: string, onChunk: (text: string) => void) {
  const response = await fetch('http://localhost:11434/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: 'qwen3.5:9b',
      prompt: prompt,
      stream: true,
    }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let accumulated = '';

  while (reader) {
    const { done, value } = await reader.read();
    if (done) break;
    const jsonLines = decoder.decode(value, { stream: true }).trim().split('\\n');
    for (const line of jsonLines) {
      if (line) {
        const parsed = JSON.parse(line);
        accumulated += parsed.response;
        onChunk(accumulated);
      }
    }
  }
}`;

  const SNIPPET_SYSTEMD = `# /etc/systemd/system/choomba-daemon.service
[Unit]
Description=Choomba Local AI Assistant Daemon
After=network.target postgresql.service ollama.service

[Service]
Type=simple
User=joshua
WorkingDirectory=/home/joshua/choomba
ExecStart=/home/joshua/choomba/venv/bin/python main.py
Restart=on-failure
Environment="DATABASE_URL=postgresql://choomba:pass@localhost:5432/choomba"
Environment="OLLAMA_HOST=http://localhost:11434"

[Install]
WantedBy=multi-user.target`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl max-h-[85vh] bg-[#050A12] border border-cyan-500/30 rounded-xl shadow-[0_0_50px_rgba(0,0,0,0.9)] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="h-14 px-6 border-b border-cyan-500/20 flex items-center justify-between bg-slate-950/70 shrink-0">
          <div className="flex items-center gap-2.5">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono font-bold tracking-wider text-slate-100 uppercase">
              CHOOMBA LOCAL ARCHITECTURE & SERVICE MIGRATION GUIDE
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs text-slate-300 font-sans leading-relaxed">
          {/* Section 1: Separation of Concerns */}
          <div>
            <h4 className="font-mono text-sm font-semibold text-cyan-300 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              1. Modular Service Layer Architecture
            </h4>
            <p className="mt-1 text-slate-400">
              The interface is strictly decoupled from mock data through TypeScript service interfaces located in <code className="text-cyan-300 bg-slate-900 px-1 py-0.5 rounded">src/services/</code>:
            </p>
            <ul className="mt-2 space-y-1.5 font-mono text-[11px] text-slate-300 list-disc list-inside">
              <li><strong className="text-slate-100">ModelService</strong>: Replace with Ollama <code className="text-cyan-400">GET /api/tags</code> for dynamic model discovery.</li>
              <li><strong className="text-slate-100">AssistantService</strong>: Replace with Ollama <code className="text-cyan-400">POST /api/generate</code> streaming reader.</li>
              <li><strong className="text-slate-100">VoiceService</strong>: Replace with local whisper.cpp / Piper TTS daemon or PulseAudio/PipeWire socket.</li>
              <li><strong className="text-slate-100">MemoryService</strong>: Connect to your existing PostgreSQL database <code className="text-cyan-400">choomba</code> and Obsidian vault.</li>
            </ul>
          </div>

          {/* Section 2: Code Snippets */}
          <div className="space-y-4">
            <h4 className="font-mono text-sm font-semibold text-cyan-300 flex items-center gap-2">
              <Code className="w-4 h-4 text-cyan-400" />
              2. Production Backend Drop-In Patterns
            </h4>

            {/* Snippet 1 */}
            <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 relative">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[11px] text-cyan-400">Ollama Model Discovery (ModelService.ts)</span>
                <button
                  onClick={() => copyCode(SNIPPET_OLLAMA, 1)}
                  className="p-1 rounded text-slate-400 hover:text-white"
                >
                  {copiedIndex === 1 ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
              <pre className="font-mono text-[11px] text-slate-300 overflow-x-auto p-2 bg-slate-900/60 rounded">
                {SNIPPET_OLLAMA}
              </pre>
            </div>

            {/* Snippet 2 */}
            <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 relative">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[11px] text-cyan-400">Ollama Streamed Inference (AssistantService.ts)</span>
                <button
                  onClick={() => copyCode(SNIPPET_STREAM, 2)}
                  className="p-1 rounded text-slate-400 hover:text-white"
                >
                  {copiedIndex === 2 ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
              <pre className="font-mono text-[11px] text-slate-300 overflow-x-auto p-2 bg-slate-900/60 rounded">
                {SNIPPET_STREAM}
              </pre>
            </div>

            {/* Snippet 3 */}
            <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 relative">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[11px] text-cyan-400">Fedora Linux systemd Daemon</span>
                <button
                  onClick={() => copyCode(SNIPPET_SYSTEMD, 3)}
                  className="p-1 rounded text-slate-400 hover:text-white"
                >
                  {copiedIndex === 3 ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
              <pre className="font-mono text-[11px] text-slate-300 overflow-x-auto p-2 bg-slate-900/60 rounded">
                {SNIPPET_SYSTEMD}
              </pre>
            </div>
          </div>

          {/* Section 3: Hardware Budget */}
          <div>
            <h4 className="font-mono text-sm font-semibold text-cyan-300 flex items-center gap-2">
              <Shield className="w-4 h-4 text-cyan-400" />
              3. Hardware Allocation on NVIDIA RTX 3060 12GB
            </h4>
            <p className="mt-1 text-slate-400">
              The RTX 3060 delivers 12GB VRAM. Recommended parameter configurations:
            </p>
            <div className="mt-2 grid grid-cols-2 gap-3 font-mono text-[11px]">
              <div className="p-3 rounded bg-slate-900/60 border border-slate-800">
                <div className="text-cyan-300 font-semibold">Qwen 3.5 9B (Q4_K_M)</div>
                <div className="text-slate-400">~6.4 GB VRAM — 45 tokens/sec</div>
                <div className="text-emerald-400 mt-1">Leaves 5.6 GB for KV cache + system</div>
              </div>
              <div className="p-3 rounded bg-slate-900/60 border border-slate-800">
                <div className="text-cyan-300 font-semibold">Qwen 3.5 14B (Q4_K_M)</div>
                <div className="text-slate-400">~10.8 GB VRAM — 24 tokens/sec</div>
                <div className="text-amber-400 mt-1">Near maximum 12GB capacity</div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="h-14 px-6 border-t border-slate-800/80 bg-slate-950/60 flex items-center justify-end shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/30 text-xs font-mono transition-colors"
          >
            CLOSE GUIDE
          </button>
        </div>
      </div>
    </div>
  );
};
