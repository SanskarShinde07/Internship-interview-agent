// Adapter around the browser's Web Speech Synthesis API (docs/BLUEPRINT.md
// §10). Kept behind the same kind of interface as the recognition adapter
// so a future cloud TTS provider is a drop-in replacement.

export interface SpeechSynthesisAdapter {
  isSupported(): boolean;
  speak(text: string, onEnd?: () => void): void;
  cancel(): void;
}

export function isSpeechSynthesisSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export class BrowserSpeechSynthesisAdapter implements SpeechSynthesisAdapter {
  isSupported(): boolean {
    return isSpeechSynthesisSupported();
  }

  speak(text: string, onEnd?: () => void): void {
    if (!this.isSupported()) {
      onEnd?.();
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.onend = () => onEnd?.();
    utterance.onerror = () => onEnd?.();
    window.speechSynthesis.speak(utterance);
  }

  cancel(): void {
    if (this.isSupported()) {
      window.speechSynthesis.cancel();
    }
  }
}
