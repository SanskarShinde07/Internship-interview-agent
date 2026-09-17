import type { SpeechRecognitionErrorCode } from "@/lib/voice/speech-recognition";
import type { VoiceStatus } from "@/hooks/useVoiceTurn";

const ERROR_MESSAGES: Record<SpeechRecognitionErrorCode, string> = {
  "not-allowed": "Microphone access was denied. You can still type your answer below.",
  "no-speech": "I didn't catch that — try again, or type your answer below.",
  "audio-capture": "No microphone was found. You can type your answer below.",
  network: "A network issue interrupted voice input. Try again, or type below.",
  aborted: "Recording stopped.",
  other: "Something went wrong with voice input. You can type your answer below.",
};

export function MicButton({
  status,
  interimText,
  recognitionSupported,
  voiceError,
  onStart,
  onStop,
}: {
  status: VoiceStatus;
  interimText: string;
  recognitionSupported: boolean;
  voiceError: SpeechRecognitionErrorCode | null;
  onStart: () => void;
  onStop: () => void;
}) {
  if (!recognitionSupported) {
    return (
      <p className="text-center text-xs text-neutral-500">
        Voice input isn&apos;t supported in this browser. Chrome or Edge are recommended for
        voice — you can still type your answer below.
      </p>
    );
  }

  const isListening = status === "listening";

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={isListening ? onStop : onStart}
        disabled={status === "speaking"}
        aria-label={isListening ? "Stop recording" : "Start recording your answer"}
        className={`flex h-16 w-16 items-center justify-center rounded-full text-2xl transition disabled:cursor-not-allowed disabled:opacity-40 ${
          isListening
            ? "animate-pulse bg-red-500 text-white"
            : "bg-neutral-900 text-white hover:bg-neutral-700 dark:bg-white dark:text-neutral-900"
        }`}
      >
        {isListening ? "■" : "🎤"}
      </button>
      <p className="min-h-[1.25rem] max-w-sm text-center text-sm text-neutral-500">
        {isListening
          ? interimText || "Listening..."
          : status === "speaking"
            ? "Interviewer is speaking..."
            : "Tap to answer by voice"}
      </p>
      {voiceError && (
        <p className="max-w-sm text-center text-xs text-red-600">
          {ERROR_MESSAGES[voiceError]}
        </p>
      )}
    </div>
  );
}
