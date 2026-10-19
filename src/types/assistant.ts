export type AssistantState =
  | 'IDLE'
  | 'ACTIVATED'
  | 'LISTENING'
  | 'IDENTIFYING'
  | 'THINKING'
  | 'SPEAKING'
  | 'ERROR'
  | 'OFFLINE';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  tokens?: number;
  speaker?: string;
  modelUsed?: string;
  simulated?: boolean;
}

export type ModelStatus = 'READY' | 'LOADING' | 'UNAVAILABLE';

export interface OllamaModelInfo {
  id: string;
  name: string;
  tag: string;
  size: string;
  quantization: string;
  status: ModelStatus;
  memoryFootprint: string;
  description: string;
  contextWindow: number;
}

export interface SystemTelemetry {
  os: string;
  architecture: string;
  gpuName: string;
  vramTotalGb: number;
  vramUsedGb: number;
  ramTotalGb: number;
  ramUsedGb: number;
  databaseStatus: 'CONNECTED' | 'DISCONNECTED' | 'AUTHENTICATING';
  databaseName: string;
  ollamaStatus: 'ONLINE' | 'OFFLINE' | 'UNREACHABLE';
  activeUser: string;
  voiceProfile: string;
  obsidianVault: string;
  systemdService: string;
  isOfflineOnly: boolean;
}

export interface ChoombaSettings {
  // 1. General Appearance
  theme: 'cyber-cyan' | 'deep-navy' | 'stealth-monochrome';
  orbScale: number;
  highContrastHud: boolean;
  
  // 2. Model & Inference
  activeModelId: string;
  ollamaEndpoint: string;
  temperature: number;
  streamResponses: boolean;
  
  // 3. Voice Activation
  activationMethod: 'double_clap' | 'wake_word' | 'manual_only';
  wakeWordPhrase: string;
  clapSensitivity: number;
  speakerIdentificationEnabled: boolean;
  
  // 4. Audio Input & Output
  audioFeedbackEnabled: boolean;
  soundVolume: number;
  speechSynthesisVoice: string;
  noiseSuppression: boolean;
  
  // 5. Database & Memory
  postgresHost: string;
  postgresPort: number;
  postgresDatabase: string;
  autoLogConversations: boolean;
  encryptionAtRest: boolean;
  
  // 6. Privacy & Offline Operation
  strictOfflineOnly: boolean;
  telemetryEnabled: boolean;
  allowOutboundHttp: boolean;
  
  // 7. System & Daemon
  systemdServiceName: string;
  autoStartOnBoot: boolean;
  
  // 8. Future Integrations
  obsidianVaultPath: string;
  homeAssistantUrl: string;
  homeAssistantEnabled: boolean;
}
