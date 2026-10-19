import { OllamaModelInfo } from '../types/assistant';

export interface IModelService {
  getAvailableModels(): Promise<OllamaModelInfo[]>;
  getActiveModel(): OllamaModelInfo;
  setActiveModel(modelId: string): Promise<OllamaModelInfo>;
}

class MockModelService implements IModelService {
  private models: OllamaModelInfo[] = [
    {
      id: 'qwen3.5:9b',
      name: 'Qwen 3.5 9B',
      tag: 'qwen3.5:9b-instruct-q4_K_M',
      size: '5.2 GB',
      quantization: 'Q4_K_M',
      status: 'READY',
      memoryFootprint: '6.4 GB VRAM',
      description: 'Primary local reasoning engine optimized for RTX 3060 12GB VRAM.',
      contextWindow: 32768,
    },
    {
      id: 'qwen3.5:14b',
      name: 'Qwen 3.5 14B',
      tag: 'qwen3.5:14b-instruct-q4_K_M',
      size: '8.9 GB',
      quantization: 'Q4_K_M',
      status: 'READY',
      memoryFootprint: '10.8 GB VRAM',
      description: 'High-capability analytical model. Fully utilizes available 12GB VRAM.',
      contextWindow: 32768,
    },
    {
      id: 'gpt-oss:20b',
      name: 'GPT-OSS 20B',
      tag: 'gpt-oss:20b-q3_K_S',
      size: '11.8 GB',
      quantization: 'Q3_K_S',
      status: 'UNAVAILABLE',
      memoryFootprint: '13.4 GB (Exceeds VRAM)',
      description: 'Requires CPU offloading. Illustrative mock model showing spillover status.',
      contextWindow: 16384,
    },
  ];

  private activeModelId: string = 'qwen3.5:9b';

  public async getAvailableModels(): Promise<OllamaModelInfo[]> {
    // In production, this will invoke: fetch('http://localhost:11434/api/tags')
    return [...this.models];
  }

  public getActiveModel(): OllamaModelInfo {
    return this.models.find(m => m.id === this.activeModelId) || this.models[0];
  }

  public async setActiveModel(modelId: string): Promise<OllamaModelInfo> {
    const target = this.models.find(m => m.id === modelId);
    if (!target) {
      throw new Error(`Model ${modelId} not found`);
    }
    this.activeModelId = modelId;
    return target;
  }
}

export const modelService = new MockModelService();
