import { ChatMessage, AssistantState } from '../types/assistant';

export interface IAssistantService {
  getMessages(): ChatMessage[];
  sendMessage(
    text: string,
    onStateChange: (state: AssistantState) => void,
    onChunk: (partialText: string) => void
  ): Promise<ChatMessage>;
  clearHistory(): void;
  startNewSession(): void;
}

// Sample intelligent, local-first responses that showcase Choomba's personality
const MOCK_KNOWLEDGE_RESPONSES: Record<string, string> = {
  status:
    'All local subsystems nominal. Ollama inference engine loaded on RTX 3060. PostgreSQL memory store active with 1,420 relational facts. Privacy fence intact: zero external traffic.',
  system:
    'Host environment: Fedora 40 Linux (x86_64), GNOME Shell 46. GPU: NVIDIA GeForce RTX 3060 12GB VRAM. System memory: 16GB DDR4. Obsidian vault synced at ~/Documents/Obsidian/Vault.',
  obsidian:
    'Obsidian vault index contains 348 markdown notes. Recent updates include your hardware architecture specs, daily logbook, and project roadmap for Choomba daemon integration.',
  database:
    'PostgreSQL database "choomba" connected on localhost:5432. Active tables: users, conversation_sessions, memory_nodes, audio_profiles. Relational integrity verified.',
  who:
    'I am Choomba, your local-first personal AI assistant. I run entirely on your hardware without transmitting audio, telemetry, or text to external servers.',
};

class MockAssistantService implements IAssistantService {
  private messages: ChatMessage[] = [
    {
      id: 'init-msg-1',
      role: 'assistant',
      content:
        'Greetings. Choomba core initialized. Local model qwen3.5:9b active on RTX 3060. Standing by for voice or command input.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      tokens: 28,
      speaker: 'Choomba Core',
      modelUsed: 'qwen3.5:9b',
      simulated: true,
    },
  ];

  public getMessages(): ChatMessage[] {
    return [...this.messages];
  }

  public clearHistory(): void {
    this.messages = [];
  }

  public startNewSession(): void {
    this.messages = [
      {
        id: `session-restart-${Date.now()}`,
        role: 'system',
        content: 'New session started. Working memory buffer cleared. Relational context retained.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        simulated: true,
      },
      {
        id: `init-msg-${Date.now()}`,
        role: 'assistant',
        content: 'Choomba standing by. Ready for your directive.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        tokens: 11,
        speaker: 'Choomba Core',
        modelUsed: 'qwen3.5:9b',
        simulated: true,
      },
    ];
  }

  public async sendMessage(
    text: string,
    onStateChange: (state: AssistantState) => void,
    onChunk: (partialText: string) => void
  ): Promise<ChatMessage> {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    // 1. Record User Message
    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp,
      tokens: Math.ceil(text.length / 4),
      speaker: 'Joshua (Recognized)',
    };
    this.messages.push(userMsg);

    // 2. State sequence: IDENTIFYING -> THINKING -> SPEAKING -> IDLE
    onStateChange('IDENTIFYING');
    await new Promise((r) => setTimeout(r, 650));

    onStateChange('THINKING');
    await new Promise((r) => setTimeout(r, 1200));

    // Choose relevant response
    const lower = text.toLowerCase();
    let reply = 'Acknowledged. Local command processed. Working memory updated in PostgreSQL.';
    for (const [key, val] of Object.entries(MOCK_KNOWLEDGE_RESPONSES)) {
      if (lower.includes(key)) {
        reply = val;
        break;
      }
    }
    if (lower.includes('hello') || lower.includes('hi')) {
      reply = 'Good day. Audio input channels active and local memory accessible. How can I assist you today?';
    } else if (lower.includes('model') || lower.includes('ollama')) {
      reply =
        'Current active Ollama model is qwen3.5:9b running 4-bit quantization with a 32k context window on NVIDIA RTX 3060.';
    }

    onStateChange('SPEAKING');

    // Stream text in small chunks to simulate real streaming inference
    let accumulated = '';
    const words = reply.split(' ');
    for (let i = 0; i < words.length; i++) {
      accumulated += (i > 0 ? ' ' : '') + words[i];
      onChunk(accumulated);
      await new Promise((r) => setTimeout(r, 45 + Math.random() * 35));
    }

    // Brief dwell in speaking state
    await new Promise((r) => setTimeout(r, 400));
    onStateChange('IDLE');

    const assistantMsg: ChatMessage = {
      id: `asst-${Date.now()}`,
      role: 'assistant',
      content: reply,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      tokens: Math.ceil(reply.length / 4),
      speaker: 'Choomba Core',
      modelUsed: 'qwen3.5:9b',
      simulated: true,
    };
    this.messages.push(assistantMsg);

    return assistantMsg;
  }
}

export const assistantService = new MockAssistantService();
