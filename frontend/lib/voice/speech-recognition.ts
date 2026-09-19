// Adapter around the browser's Web Speech Recognition API (docs/BLUEPRINT.md
// §10). The interview UI depends only on `SpeechRecognitionAdapter` below,
// not on this browser implementation, so swapping in a server-side Whisper
// adapter later doesn't require touching any page or component code.

export type SpeechRecognitionErrorCode =
  | "not-allowed"
  | "no-speech"
  | "audio-capture"
  | "network"
  | "aborted"
  | "other";

export interface SpeechRecognitionAdapter {
  isSupported(): boolean;
  start(): void;
  stop(): void;
  abort(): void;
  // finalTranscript/interimTranscript are always the browser's CURRENT
  // full transcript for this recognition session, not a fragment to
  // append - see the comment on onresult below for why.
  onResult(callback: (finalTranscript: string, interimTranscript: string) => void): void;
  onError(callback: (code: SpeechRecognitionErrorCode) => void): void;
  onEnd(callback: () => void): void;
}

// The DOM lib doesn't ship types for this non-standard, vendor-prefixed API,
// so we declare only the surface we actually use.
interface SpeechRecognitionResultLike {
  isFinal: boolean;
  0: { transcript: string };
}

interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: ArrayLike<SpeechRecognitionResultLike>;
}

interface SpeechRecognitionErrorEventLike {
  error: string;
}

interface NativeSpeechRecognition {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
}

function getConstructor(): (new () => NativeSpeechRecognition) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => NativeSpeechRecognition;
    webkitSpeechRecognition?: new () => NativeSpeechRecognition;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function isSpeechRecognitionSupported(): boolean {
  return getConstructor() !== null;
}

function mapErrorCode(error: string): SpeechRecognitionErrorCode {
  switch (error) {
    case "not-allowed":
    case "service-not-allowed":
      return "not-allowed";
    case "no-speech":
      return "no-speech";
    case "audio-capture":
      return "audio-capture";
    case "network":
      return "network";
    case "aborted":
      return "aborted";
    default:
      return "other";
  }
}

export class BrowserSpeechRecognitionAdapter implements SpeechRecognitionAdapter {
  private recognition: NativeSpeechRecognition | null = null;
  private resultCallback: ((finalTranscript: string, interimTranscript: string) => void) | null =
    null;
  private errorCallback: ((code: SpeechRecognitionErrorCode) => void) | null = null;
  private endCallback: (() => void) | null = null;

  constructor() {
    const Ctor = getConstructor();
    if (!Ctor) return;

    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      // Rebuild the full transcript from the *entire* results array every
      // time, rather than only processing event.resultIndex onward and
      // appending fragments. Chrome doesn't reliably honor resultIndex -
      // it can (and does) re-fire onresult with the same already-final
      // result included again, which made a naive "append on isFinal"
      // consumer duplicate the candidate's words 4-5x over. Reconstructing
      // from scratch each time is idempotent: however many times this
      // fires, or whatever range it reports, the concatenation of every
      // currently-final result is the same string.
      let finalTranscript = "";
      let interimTranscript = "";
      for (let i = 0; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += `${result[0].transcript} `;
        } else {
          interimTranscript += result[0].transcript;
        }
      }
      this.resultCallback?.(finalTranscript.trim(), interimTranscript.trim());
    };
    recognition.onerror = (event) => {
      this.errorCallback?.(mapErrorCode(event.error));
    };
    recognition.onend = () => {
      this.endCallback?.();
    };

    this.recognition = recognition;
  }

  isSupported(): boolean {
    return this.recognition !== null;
  }

  start(): void {
    this.recognition?.start();
  }

  stop(): void {
    this.recognition?.stop();
  }

  abort(): void {
    this.recognition?.abort();
  }

  onResult(callback: (finalTranscript: string, interimTranscript: string) => void): void {
    this.resultCallback = callback;
  }

  onError(callback: (code: SpeechRecognitionErrorCode) => void): void {
    this.errorCallback = callback;
  }

  onEnd(callback: () => void): void {
    this.endCallback = callback;
  }
}
