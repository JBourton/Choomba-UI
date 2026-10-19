/**
 * Pure Web Audio API synthesized harmonic sci-fi audio feedback.
 * Generates restrained, JARVIS-inspired clean chimes without external audio assets.
 */
class SoundEngine {
  private ctx: AudioContext | null = null;
  private isMuted: boolean = false;
  private volume: number = 0.3;

  private initContext() {
    if (!this.ctx && typeof window !== 'undefined') {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
  }

  public setMuted(muted: boolean) {
    this.isMuted = muted;
  }

  public getMuted(): boolean {
    return this.isMuted;
  }

  public toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    if (!this.isMuted) {
      this.playChime(660, 0.1, 'sine');
    }
    return this.isMuted;
  }

  public setVolume(val: number) {
    this.volume = Math.max(0, Math.min(1, val));
  }

  private playTone(freq: number, duration: number, type: OscillatorType = 'sine', rampTo?: number) {
    if (this.isMuted) return;
    try {
      this.initContext();
      if (!this.ctx) return;

      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
      if (rampTo !== undefined) {
        osc.frequency.exponentialRampToValueAtTime(rampTo, this.ctx.currentTime + duration);
      }

      // Smooth envelope to avoid clicks
      const now = this.ctx.currentTime;
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(this.volume * 0.4, now + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + duration);
    } catch {
      // AudioContext policy suppression gracefully handled
    }
  }

  public playActivationChime() {
    if (this.isMuted) return;
    // Ascending pure dual chime (E5 -> A5)
    this.playTone(659.25, 0.18, 'sine');
    setTimeout(() => {
      this.playTone(880.0, 0.28, 'sine');
    }, 70);
  }

  public playListeningPulse() {
    if (this.isMuted) return;
    this.playTone(740.0, 0.15, 'sine');
  }

  public playIdentifyingScan() {
    if (this.isMuted) return;
    this.playTone(587.33, 0.1, 'triangle', 784.0);
  }

  public playThinkingTone() {
    if (this.isMuted) return;
    this.playTone(440.0, 0.35, 'sine', 554.37);
  }

  public playSpeakingStart() {
    if (this.isMuted) return;
    this.playTone(523.25, 0.12, 'sine');
    setTimeout(() => {
      this.playTone(659.25, 0.15, 'sine');
    }, 60);
  }

  public playErrorChime() {
    if (this.isMuted) return;
    // Subtle low minor second dissonance
    this.playTone(330, 0.25, 'triangle', 290);
  }

  public playOfflineTone() {
    if (this.isMuted) return;
    // Diminuendo descending tone
    this.playTone(440, 0.3, 'sine', 220);
  }

  public playChime(freq = 660, dur = 0.15, type: OscillatorType = 'sine') {
    this.playTone(freq, dur, type);
  }
}

export const audioSoundService = new SoundEngine();
