/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { AssistantState, ChatMessage, OllamaModelInfo, ChoombaSettings } from './types/assistant';
import { audioSoundService } from './services/AudioSoundService';
import { modelService } from './services/ModelService';
import { assistantService } from './services/AssistantService';
import { voiceService, DaemonStatusPayload, VoiceServiceConnectionState } from './services/VoiceService';
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
  const [daemonStatus, setDaemonStatus] = useState<DaemonStatusPayload | null>(null);
  const [connectionState, setConnectionState] = useState<VoiceServiceConnectionState>('disconnected');

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

  // Connect to local voice activation daemon and subscribe to double-clap events
  useEffect(() => {
    voiceService.connect();

    const unsubConn = voiceService.onConnectionChange((status) => {
      setConnectionState(status);
    });

    const unsubStatus = voiceService.onStatus((status) => {
      setDaemonStatus(status);
    });

    const unsubActivation = voiceService.onActivation((event) => {
      setState((currentState) => {
        // Prevent duplicate activation events from triggering overlapping sessions
        if (currentState !== 'IDLE') {
          return currentState;
        }

        // Clear any running sequence timers
        sequenceTimeoutRef.current.forEach(clearTimeout);
        sequenceTimeoutRef.current = [];

        // 1. Transition to ACTIVATED
        transitionToState('ACTIVATED');
        const intervalText = event.metadata?.interval_ms
          ? ` (${Math.round(event.metadata.interval_ms)}ms)`
          : '';
        setTranscription(`Double-clap acoustic trigger detected${intervalText}. Assistant activated.`);
        setStreamingText('');

        // 2. Transition to LISTENING after holographic core flash (800ms)
        // Important: Speech recognition is not implemented in this phase.
        // LISTENING indicates Choomba is primed and ready for the next modular stage.
        const t1 = setTimeout(() => {
          transitionToState('LISTENING');
          setTranscription('Choomba activated via double-clap. Standing by for voice command or prompt...');
        }, 800);
        sequenceTimeoutRef.current.push(t1);

        // 3. Prototype timeout: return to IDLE after 8.8s if no command is entered
        const t2 = setTimeout(() => {
          setState((s) => {
            if (s === 'LISTENING') {
              transitionToState('IDLE');
              setTranscription('');
              setStreamingText('');
              return 'IDLE';
            }
            return s;
          });
        }, 8800);
        sequenceTimeoutRef.current.push(t2);

        return 'ACTIVATED';
      });
    });

    return () => {
      unsubConn();
      unsubStatus();
      unsubActivation();
      voiceService.disconnect();
    };
  }, [transitionToState]);

  // Synchronize sensitivity and activation mode changes to daemon
  useEffect(() => {
    voiceService.setSensitivity(settings.clapSensitivity);
    if (settings.activationMethod === 'double_clap') {
      voiceService.resumeMonitoring();
    } else if (settings.activationMethod === 'manual_only') {
      voiceService.pauseMonitoring();
    }
  }, [settings.clapSensitivity, settings.activationMethod]);

  // Toggle microphone monitoring between active and paused
  const handleToggleMonitoring = useCallback(() => {
    if (daemonStatus?.state === 'monitoring') {
      voiceService.pauseMonitoring();
    } else {
      voiceService.resumeMonitoring();
    }
  }, [daemonStatus]);

  // Dev helper: trigger simulated double-clap event over WebSocket
  const handleSimulateClap = useCallback(() => {
    voiceService.simulateClap();
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
        isMonitoring={connectionState === 'connected' && daemonStatus?.state === 'monitoring'}
        daemonConnected={connectionState === 'connected'}
        onToggleMonitoring={handleToggleMonitoring}
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
          onSimulateClap={handleSimulateClap}
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
        daemonStatus={daemonStatus}
        connectionState={connectionState}
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
