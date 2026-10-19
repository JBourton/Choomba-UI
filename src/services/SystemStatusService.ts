import { SystemTelemetry } from '../types/assistant';

export interface ISystemStatusService {
  getTelemetry(): Promise<SystemTelemetry>;
  restartLocalService(): Promise<boolean>;
}

class MockSystemStatusService implements ISystemStatusService {
  private telemetry: SystemTelemetry = {
    os: 'Fedora 40 (Workstation Edition)',
    architecture: 'x86_64 / Linux 6.8.9-300.fc40',
    gpuName: 'NVIDIA GeForce RTX 3060 (12 GB GDDR6)',
    vramTotalGb: 12.0,
    vramUsedGb: 6.4,
    ramTotalGb: 16.0,
    ramUsedGb: 8.2,
    databaseStatus: 'CONNECTED',
    databaseName: 'choomba',
    ollamaStatus: 'ONLINE',
    activeUser: 'Joshua',
    voiceProfile: 'Enrolled (Cosine match 0.94)',
    obsidianVault: '~/Documents/Obsidian/Personal (Synced)',
    systemdService: 'choomba-daemon.service (Active/Running)',
    isOfflineOnly: true,
  };

  public async getTelemetry(): Promise<SystemTelemetry> {
    return { ...this.telemetry };
  }

  public async restartLocalService(): Promise<boolean> {
    await new Promise((r) => setTimeout(r, 800));
    return true;
  }
}

export const systemStatusService = new MockSystemStatusService();
