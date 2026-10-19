/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export interface ActivationEventPayload {
  type: 'activation.detected';
  method: 'double_clap' | 'wake_word';
  timestamp: string;
  metadata?: {
    interval_ms?: number;
    confidence?: number;
    first_clap_rms?: number;
    second_clap_rms?: number;
    noise_floor?: number;
    simulated?: boolean;
  };
}

export interface DaemonStatusPayload {
  type: 'status';
  state: 'monitoring' | 'paused' | 'stopped';
  method: string;
  sensitivity: number;
  connected_clients: number;
  audio_device: string;
  sample_rate: number;
  noise_floor?: number;
}

export type VoiceServiceConnectionState = 'connected' | 'disconnected' | 'connecting' | 'error';

type ActivationListener = (event: ActivationEventPayload) => void;
type StatusListener = (status: DaemonStatusPayload) => void;
type ConnectionListener = (state: VoiceServiceConnectionState) => void;

class VoiceService {
  private socket: WebSocket | null = null;
  private wsUrl: string;
  private connectionState: VoiceServiceConnectionState = 'disconnected';
  private daemonStatus: DaemonStatusPayload | null = null;

  private activationListeners: Set<ActivationListener> = new Set();
  private statusListeners: Set<StatusListener> = new Set();
  private connectionListeners: Set<ConnectionListener> = new Set();

  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 8000;
  private isExplicitlyClosed = false;

  constructor(wsUrl = 'ws://127.0.0.1:8765') {
    this.wsUrl = wsUrl;
  }

  public getConnectionState(): VoiceServiceConnectionState {
    return this.connectionState;
  }

  public getDaemonStatus(): DaemonStatusPayload | null {
    return this.daemonStatus;
  }

  public isMonitoring(): boolean {
    return this.connectionState === 'connected' && this.daemonStatus?.state === 'monitoring';
  }

  public connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    this.setConnectionState('connecting');

    try {
      this.socket = new WebSocket(this.wsUrl);

      this.socket.onopen = () => {
        this.reconnectAttempts = 0;
        this.setConnectionState('connected');
        // Request current status immediately upon connection
        this.sendCommand({ action: 'get_status' });
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleIncomingMessage(data);
        } catch {
          // Ignore invalid frame
        }
      };

      this.socket.onclose = () => {
        this.socket = null;
        this.setConnectionState('disconnected');
        this.scheduleReconnect();
      };

      this.socket.onerror = () => {
        this.setConnectionState('error');
      };
    } catch {
      this.setConnectionState('error');
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.setConnectionState('disconnected');
  }

  public setSensitivity(value: number): void {
    this.sendCommand({ action: 'set_sensitivity', value: Math.max(0.1, Math.min(1.0, value)) });
  }

  public pauseMonitoring(): void {
    this.sendCommand({ action: 'pause' });
  }

  public resumeMonitoring(): void {
    this.sendCommand({ action: 'resume' });
  }

  public simulateClap(): void {
    this.sendCommand({ action: 'simulate_clap' });
  }

  public onActivation(listener: ActivationListener): () => void {
    this.activationListeners.add(listener);
    return () => this.activationListeners.delete(listener);
  }

  public onStatus(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    if (this.daemonStatus) {
      listener(this.daemonStatus);
    }
    return () => this.statusListeners.delete(listener);
  }

  public onConnectionChange(listener: ConnectionListener): () => void {
    this.connectionListeners.add(listener);
    listener(this.connectionState);
    return () => this.connectionListeners.delete(listener);
  }

  private handleIncomingMessage(data: any): void {
    if (!data || typeof data !== 'object') return;

    if (data.type === 'activation.detected') {
      const payload = data as ActivationEventPayload;
      this.activationListeners.forEach((l) => l(payload));
    } else if (data.type === 'status') {
      this.daemonStatus = data as DaemonStatusPayload;
      this.statusListeners.forEach((l) => l(this.daemonStatus!));
    }
  }

  private sendCommand(cmd: Record<string, any>): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify(cmd));
      } catch {
        // Send failure
      }
    }
  }

  private setConnectionState(newState: VoiceServiceConnectionState): void {
    if (this.connectionState !== newState) {
      this.connectionState = newState;
      this.connectionListeners.forEach((l) => l(newState));
    }
  }

  private scheduleReconnect(): void {
    if (this.isExplicitlyClosed) return;
    if (this.reconnectTimer) return;

    this.reconnectAttempts++;
    // Exponential backoff: 1s, 2s, 4s, up to maxReconnectDelay
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts - 1), this.maxReconnectDelay);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }
}

export const voiceService = new VoiceService();
