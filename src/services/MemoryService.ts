export interface MemoryFact {
  id: string;
  category: 'preference' | 'project' | 'people' | 'system' | 'note';
  subject: string;
  detail: string;
  source: 'postgresql' | 'obsidian' | 'conversation';
  confidence: number;
  lastAccessed: string;
}

export interface IMemoryService {
  getRecentFacts(): Promise<MemoryFact[]>;
  searchMemory(term: string): Promise<MemoryFact[]>;
  getObsidianVaultNotes(): Promise<Array<{ title: string; path: string; modified: string }>>;
}

class MockMemoryService implements IMemoryService {
  private facts: MemoryFact[] = [
    {
      id: 'fact-1',
      category: 'system',
      subject: 'Inference Device',
      detail: 'Local workstation running Fedora 40 with NVIDIA RTX 3060 12GB VRAM.',
      source: 'postgresql',
      confidence: 1.0,
      lastAccessed: 'Just now',
    },
    {
      id: 'fact-2',
      category: 'project',
      subject: 'Choomba Architecture',
      detail: 'Local-first assistant daemon utilizing systemd, Ollama REST API, and PostgreSQL choomba database.',
      source: 'obsidian',
      confidence: 0.98,
      lastAccessed: '2 hours ago',
    },
    {
      id: 'fact-3',
      category: 'preference',
      subject: 'Activation Mode',
      detail: 'Prefers double-clap activation for desk convenience or quick shortcut.',
      source: 'conversation',
      confidence: 0.92,
      lastAccessed: 'Yesterday',
    },
    {
      id: 'fact-4',
      category: 'note',
      subject: 'Obsidian Daily Log',
      detail: 'Tracked GPU memory benchmarks across Qwen3.5 9B vs 14B under 12GB ceiling.',
      source: 'obsidian',
      confidence: 0.95,
      lastAccessed: '3 hours ago',
    },
    {
      id: 'fact-5',
      category: 'people',
      subject: 'Primary Operator',
      detail: 'Joshua (Admin / Authorized voice profile).',
      source: 'postgresql',
      confidence: 0.99,
      lastAccessed: '1 hour ago',
    },
  ];

  public async getRecentFacts(): Promise<MemoryFact[]> {
    return [...this.facts];
  }

  public async searchMemory(term: string): Promise<MemoryFact[]> {
    if (!term.trim()) return [...this.facts];
    const q = term.toLowerCase();
    return this.facts.filter(
      (f) =>
        f.subject.toLowerCase().includes(q) ||
        f.detail.toLowerCase().includes(q) ||
        f.category.toLowerCase().includes(q)
    );
  }

  public async getObsidianVaultNotes(): Promise<Array<{ title: string; path: string; modified: string }>> {
    return [
      { title: 'Choomba System Architecture.md', path: 'Projects/Choomba/Architecture.md', modified: 'Today 11:20' },
      { title: 'Local AI GPU Benchmarks.md', path: 'Research/GPU_Benchmarks.md', modified: 'Yesterday 18:45' },
      { title: 'Home Assistant Automation Rules.md', path: 'SmartHome/Rules.md', modified: '3 days ago' },
      { title: 'PostgreSQL Vector Memory Schema.md', path: 'Projects/Choomba/DB_Schema.md', modified: '5 days ago' },
    ];
  }
}

export const memoryService = new MockMemoryService();
