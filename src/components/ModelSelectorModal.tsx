import React from 'react';
import { X, Check, Cpu, HardDrive, AlertTriangle } from 'lucide-react';
import { OllamaModelInfo } from '../types/assistant';

interface ModelSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  models: OllamaModelInfo[];
  activeModelId: string;
  onSelectModel: (modelId: string) => void;
}

export const ModelSelectorModal: React.FC<ModelSelectorModalProps> = ({
  isOpen,
  onClose,
  models,
  activeModelId,
  onSelectModel,
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg bg-[#050A12] border border-cyan-500/30 rounded-xl shadow-[0_0_35px_rgba(0,0,0,0.9)] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="h-14 px-6 border-b border-cyan-500/20 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono font-bold tracking-wider text-slate-100 uppercase">
              LOCAL OLLAMA MODEL SELECTOR
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Informative banner on discovery */}
        <div className="px-6 py-2.5 bg-cyan-950/20 border-b border-cyan-500/10 text-[11px] font-mono text-cyan-400/80 flex items-center justify-between">
          <span>HOST: localhost:11434 (RTX 3060 12GB VRAM)</span>
          <span className="text-slate-500">MOCK DISCOVERY</span>
        </div>

        {/* Model List */}
        <div className="p-6 space-y-3 max-h-[60vh] overflow-y-auto">
          {models.map((model) => {
            const isSelected = model.id === activeModelId;
            const isReady = model.status === 'READY';
            const isUnavailable = model.status === 'UNAVAILABLE';

            return (
              <div
                key={model.id}
                onClick={() => {
                  if (!isUnavailable) {
                    onSelectModel(model.id);
                  }
                }}
                className={`p-4 rounded-lg border transition-all duration-200 ${
                  isSelected
                    ? 'border-cyan-400 bg-cyan-950/25 shadow-[0_0_15px_rgba(67,207,255,0.15)]'
                    : isUnavailable
                    ? 'border-slate-800/60 bg-slate-950/30 opacity-60 cursor-not-allowed'
                    : 'border-slate-800 bg-slate-900/40 hover:border-cyan-500/40 hover:bg-slate-900/70 cursor-pointer'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold font-mono text-slate-100">
                      {model.name}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.5 rounded">
                      {model.quantization}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Status Badge */}
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded font-medium ${
                        isReady
                          ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-500/30'
                          : isUnavailable
                          ? 'text-rose-400 bg-rose-950/40 border border-rose-500/30'
                          : 'text-amber-400 bg-amber-950/40 border border-amber-500/30'
                      }`}
                    >
                      {model.status}
                    </span>

                    {isSelected && <Check className="w-4 h-4 text-cyan-400" />}
                  </div>
                </div>

                <p className="mt-1.5 text-xs text-slate-400 leading-relaxed font-sans">
                  {model.description}
                </p>

                {/* Technical Footprint strip */}
                <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span className="flex items-center gap-1.5">
                    <HardDrive className="w-3 h-3 text-slate-400" />
                    FILE SIZE: {model.size}
                  </span>
                  <span className="text-slate-400">VRAM: {model.memoryFootprint}</span>
                </div>

                {isUnavailable && (
                  <div className="mt-2 text-[10px] font-mono text-rose-400/90 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    Exceeds dedicated RTX 3060 12GB ceiling without CPU spillover
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer info explaining Replaceable Service */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950/50 flex items-center justify-between text-xs font-mono text-slate-500">
          <span>Future API: GET /api/tags via ModelService</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-colors"
          >
            DISMISS
          </button>
        </div>
      </div>
    </div>
  );
};
