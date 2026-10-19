/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { AssistantState, ChatMessage, OllamaModelInfo, ChoombaSettings } from './types/assistant';
import { audioSoundService } from './services/AudioSoundService';
import { modelService } from './services/ModelService';
import { assistantService } from './services/AssistantService';
import { TopStatusBar } from './components/TopStatusBar';
import { CentralStage } from './components/CentralStage';
import { BottomCommandDeck } from './components/BottomCommandDeck';
import { DevStateSwitcher } from './components/DevStateSwitcher';
import { ConversationDrawer } from './components/ConversationDrawer';
import { SettingsDrawer } from './components/SettingsDrawer';
import { ModelSelectorModal } from './components/ModelSelectorModal';
import { ArchitectureGuideModal } from './components/ArchitectureGuideModal';

const DEFAULT_SETTINGS: ChoombaSettings = {
  theme: 'cyber-cyan',
  orbScale: 1.0,
  highContrastHud: false,
  activeModelId: 'qwen3.5:9b',
  ollamaEndpoint: 'http://localhost:11434',
  temperature: 0.7,
  streamResponses: true,
  activationMethod: 'double_clap',
  wakeWordPhrase: 'Hey Choomba',
  clapSensitivity: 0.8,
  speakerIdentificationEnabled: true,
  audioFeedbackEnabled: true,
  soundVolume: 0.4,
  speechSynthesisVoice: 'Piper / en_GB-alan-medium',
  noiseSuppression: true,
  postgresHost: 'localhost',
  postgresPort: 5432,
  postgresDatabase: 'choomba',
  autoLogConversations: true,
  encryptionAtRest: true,
  strictOfflineOnly: true,
  telemetryEnabled: false,
  allowOutboundHttp: false,
  systemdServiceName: 'choomba-daemon.service',
  autoStartOnBoot: true,
  obsidianVaultPath: '~/Documents/Obsidian/Personal',
  homeAssistantUrl: 'http://homeassistant.local:8123',
  homeAssistantEnabled: false,
};

export default function App() {
  const [state, setState] = useState<AssistantState>('IDLE');
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [activeModel, setActiveModel] = useState<OllamaModelInfo>(modelService.getActiveModel());
  const [availableModels, setAvailableModels] = useState<OllamaModelInfo[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingText, setStreamingText] = useState<string>('');
  const [transcription, setTranscription] = useState<string>('');
  const [settings, setSettings] = useState<ChoombaSettings>(DEFAULT_SETTINGS);

  // Drawers and Modals
  const [conversationOpen, setConversationOpen] = useState<boolean>(false);
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [modelSelectorOpen, setModelSelectorOpen] = useState<boolean>(false);
  const [archGuideOpen, setArchGuideOpen] = useState<boolean>(false);
  const [devStateBarOpen, setDevStateBarOpen] = useState<boolean>(true);
  const [isSequenceRunning, setIsSequenceRunning] = useState<boolean>(false);

  const sequenceTimeoutRef = useRef<NodeJS.Timeout[]>([]);

  // Initialize models and messages
  useEffect(() => {
    modelService.getAvailableModels().then((models) => {
      setAvailableModels(models);
      setActiveModel(modelService.getActiveModel());
    });
    setMessages(assistantService.getMessages());
  }, []);

  // Sync mute state with sound engine
  const handleToggleMute = useCallback(() => {
    const newMuted = audioSoundService.toggleMute();
    setIsMuted(newMuted);
  }, []);

  // Play audio chimes when state changes
  const transitionToState = useCallback((newState: AssistantState) => {
    setState(newState);
    switch (newState) {
      case 'ACTIVATED':
        audioSoundService.playActivationChime();
        break;
      case 'LISTENING':
        audioSoundService.playListeningPulse();
        break;
      case 'IDENTIFYING':
        audioSoundService.playIdentifyingScan();
        break;
      case 'THINKING':
        audioSoundService.playThinkingTone();
        break;
      case 'SPEAKING':
        audioSoundService.playSpeakingStart();
        break;
      case 'ERROR':
        audioSoundService.playErrorChime();
        break;
      case 'OFFLINE':
        audioSoundService.playOfflineTone();
        break;
      default:
        break;
    }
  }, []);

  // Submit text message flow
  const handleSubmitText = useCallback(
    async (text: string) => {
      if (state === 'OFFLINE' || state === 'THINKING') return;

      setTranscription(`"${text}"`);
      setStreamingText('');

      try {
        await assistantService.sendMessage(
          text,
          (s) => transitionToState(s),
          (chunk) => setStreamingText(chunk)
        );
        setMessages(assistantService.getMessages());
        setTranscription('');
      } catch {
        transitionToState('ERROR');
      }
    },
    [state, transitionToState]
  );

  // Microphone toggle flow (Simulated voice command)
  const handleToggleMic = useCallback(() => {
    if (state === 'LISTENING') {
      // User tapped stop listening -> trigger inference
      setTranscription('"What is the status of my local database and system?"');
      handleSubmitText('What is the status of my local database and system?');
    } else if (state === 'IDLE' || state === 'ACTIVATED') {
      transitionToState('LISTENING');
      setStreamingText('');
      setTranscription('');

      // Auto-simulate voice input after 3 seconds if user doesn't press again
      const timer = setTimeout(() => {
        setTranscription('"Choomba, verify local Ollama inference and GPU memory allocation."');
        handleSubmitText('Choomba, verify local Ollama inference and GPU memory allocation.');
      }, 3500);

      sequenceTimeoutRef.current.push(timer);
    }
  }, [state, transitionToState, handleSubmitText]);

  // Orb click triggers voice interaction or wake
  const handleOrbClick = useCallback(() => {
    if (state === 'OFFLINE') {
      transitionToState('IDLE');
    } else if (state === 'ERROR') {
      transitionToState('IDLE');
    } else {
      handleToggleMic();
    }
  }, [state, transitionToState, handleToggleMic]);

  // Automated Full Demo Loop Runner
  const handleRunFullDemoSequence = useCallback(() => {
    // Clear any pending timeouts
    sequenceTimeoutRef.current.forEach(clearTimeout);
    sequenceTimeoutRef.current = [];

    setIsSequenceRunning(true);
    setStreamingText('');
    setTranscription('');

    // IDLE -> ACTIVATED
    transitionToState('ACTIVATED');
    setTranscription('Double-clap acoustic trigger detected...');

    const t1 = setTimeout(() => {
      // -> LISTENING
      transitionToState('LISTENING');
      setTranscription('"Choomba, query Obsidian vault for project roadmap."');
    }, 1200);

    const t2 = setTimeout(() => {
      // -> IDENTIFYING
      transitionToState('IDENTIFYING');
      setTranscription('Acoustic voiceprint confirmed: Joshua (Admin)');
    }, 3200);

    const t3 = setTimeout(() => {
      // -> THINKING
      transitionToState('THINKING');
      setTranscription('Indexing PostgreSQL & generating response via Qwen 3.5 9B...');
    }, 5000);

    const t4 = setTimeout(() => {
      // -> SPEAKING
      transitionToState('SPEAKING');
      setTranscription('');
      setStreamingText('Obsidian vault indexed. Found 3 roadmap milestones for Choomba local deployment.');
    }, 7200);

    const t5 = setTimeout(() => {
      // -> IDLE
      transitionToState('IDLE');
      setIsSequenceRunning(false);
      setStreamingText('');
      setTranscription('');
    }, 11000);

    sequenceTimeoutRef.current.push(t1, t2, t3, t4, t5);
  }, [transitionToState]);

  // Model switching
  const handleSelectModel = useCallback(async (modelId: string) => {
    const updated = await modelService.setActiveModel(modelId);
    setActiveModel(updated);
    setSettings((prev) => ({ ...prev, activeModelId: modelId }));
    setModelSelectorOpen(false);
    audioSoundService.playChime(784, 0.1);
  }, []);

  // Session management
  const handleClearSession = useCallback(() => {
    assistantService.clearHistory();
    setMessages([]);
    setStreamingText('');
    setTranscription('');
    audioSoundService.playChime(350, 0.1);
  }, []);

  const handleRestartSession = useCallback(() => {
    assistantService.startNewSession();
    setMessages(assistantService.getMessages());
    setStreamingText('');
    setTranscription('');
    transitionToState('ACTIVATED');
    setTimeout(() => transitionToState('IDLE'), 800);
  }, [transitionToState]);

  // Close modals on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setConversationOpen(false);
        setSettingsOpen(false);
        setModelSelectorOpen(false);
        setArchGuideOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div
      className={`min-h-screen w-full flex flex-col bg-[#050A12] text-[#E6F4FE] relative overflow-hidden select-none font-sans ${
        settings.highContrastHud ? 'contrast-125' : ''
      }`}
      style={{
        transform: `scale(${settings.orbScale === 1.0 ? 1 : 1})`,
      }}
    >
      {/* Ambient background visual subtle noise and soft radial vignette */}
      <div
        className="fixed inset-0 pointer-events-none opacity-40 z-0"
        style={{
          background:
            'radial-gradient(ellipse at 50% 45%, rgba(67, 207, 255, 0.05) 0%, rgba(22, 119, 255, 0.02) 40%, transparent 75%)',
        }}
      />

      {/* Top Status Bar (Contract: 1 row, 3 zones, zero pills) */}
      <TopStatusBar
        state={state}
        activeModel={activeModel}
        isMuted={isMuted}
        onToggleMute={handleToggleMute}
        onOpenModelSelector={() => setModelSelectorOpen(true)}
        onToggleConversation={() => setConversationOpen((prev) => !prev)}
        onToggleSettings={() => setSettingsOpen((prev) => !prev)}
        onOpenArchitectureGuide={() => setArchGuideOpen(true)}
        conversationOpen={conversationOpen}
        settingsOpen={settingsOpen}
      />

      {/* Central Holographic Interaction Area */}
      <CentralStage
        state={state}
        streamingText={streamingText}
        transcription={transcription}
        onOrbClick={handleOrbClick}
      />

      {/* Bottom Command Deck */}
      <BottomCommandDeck
        state={state}
        isListening={state === 'LISTENING'}
        onToggleMic={handleToggleMic}
        onSubmitText={handleSubmitText}
        onToggleDevStateBar={() => setDevStateBarOpen((prev) => !prev)}
        devStateBarOpen={devStateBarOpen}
      />

      {/* Dev State Machine Trigger Bar */}
      {devStateBarOpen && (
        <DevStateSwitcher
          currentState={state}
          onSelectState={(s) => transitionToState(s)}
          onRunFullDemoSequence={handleRunFullDemoSequence}
          isSequenceRunning={isSequenceRunning}
        />
      )}

      {/* Slide-out Translucent Conversation Drawer */}
      <ConversationDrawer
        isOpen={conversationOpen}
        onClose={() => setConversationOpen(false)}
        messages={messages}
        onClearSession={handleClearSession}
        onRestartSession={handleRestartSession}
        activeModel={activeModel}
      />

      {/* Slide-out Settings Drawer */}
      <SettingsDrawer
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onUpdateSettings={(newVals) => setSettings((prev) => ({ ...prev, ...newVals }))}
        models={availableModels}
      />

      {/* Model Selector Modal */}
      <ModelSelectorModal
        isOpen={modelSelectorOpen}
        onClose={() => setModelSelectorOpen(false)}
        models={availableModels}
        activeModelId={activeModel.id}
        onSelectModel={handleSelectModel}
      />

      {/* Architecture & Backend Migration Guide Modal */}
      <ArchitectureGuideModal
        isOpen={archGuideOpen}
        onClose={() => setArchGuideOpen(false)}
      />
    </div>
  );
}
