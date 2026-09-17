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

// Voice name substrings that reliably identify a female English voice across
// Chrome/Edge (Microsoft/Google voice packs) and Safari (Apple voices).
// Browsers don't expose a standard "gender" field, so this is a best-effort
// name match, ordered roughly by how natural/clear each one sounds.
const PREFERRED_FEMALE_VOICE_NAMES = [
  "samantha", // Apple (macOS/iOS default en-US)
  "google us english", // Chrome/Android
  "microsoft aria", // Edge (US)
  "microsoft jenny", // Edge (US)
  "microsoft zira", // Windows legacy
  "victoria",
  "karen",
  "moira",
  "tessa",
  "female",
];

function pickFemaleEnglishVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const englishVoices = voices.filter((v) => v.lang.toLowerCase().startsWith("en"));
  const pool = englishVoices.length > 0 ? englishVoices : voices;

  for (const name of PREFERRED_FEMALE_VOICE_NAMES) {
    const match = pool.find((v) => v.name.toLowerCase().includes(name));
    if (match) return match;
  }
  return pool[0] ?? null;
}

export class BrowserSpeechSynthesisAdapter implements SpeechSynthesisAdapter {
  private voice: SpeechSynthesisVoice | null = null;

  constructor() {
    if (!this.isSupported()) return;
    this.loadVoice();
    // Chrome loads its voice list asynchronously; the first call to
    // getVoices() right after page load can return an empty array.
    window.speechSynthesis.onvoiceschanged = () => this.loadVoice();
  }

  private loadVoice(): void {
    const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) {
      this.voice = pickFemaleEnglishVoice(voices);
    }
  }

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
    if (this.voice) utterance.voice = this.voice;
    // Slightly below natural pace and a touch higher pitch reads as
    // clearer and more distinct over typical laptop/phone speakers than
    // the browser's rate=1/pitch=1 defaults.
    utterance.rate = 0.95;
    utterance.pitch = 1.05;
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
