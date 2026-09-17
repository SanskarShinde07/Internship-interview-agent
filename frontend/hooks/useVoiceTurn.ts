"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  BrowserSpeechRecognitionAdapter,
  type SpeechRecognitionErrorCode,
} from "@/lib/voice/speech-recognition";
import { BrowserSpeechSynthesisAdapter } from "@/lib/voice/speech-synthesis";

export type VoiceStatus = "idle" | "speaking" | "listening";

// If the candidate goes quiet mid-answer, keep the mic open rather than
// cutting them off - but not forever (docs/BLUEPRINT.md §10).
const SILENCE_TIMEOUT_MS = 15000;

export function useVoiceTurn() {
  const recognitionRef = useRef<BrowserSpeechRecognitionAdapter | null>(null);
  const synthesisRef = useRef<BrowserSpeechSynthesisAdapter | null>(null);
  const onFinalTranscriptRef = useRef<(text: string) => void>(() => {});

  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [interimText, setInterimText] = useState("");
  const [recognitionSupported, setRecognitionSupported] = useState(true);
  const [synthesisSupported, setSynthesisSupported] = useState(true);
  const [voiceError, setVoiceError] = useState<SpeechRecognitionErrorCode | null>(null);
  const [emptyAttempts, setEmptyAttempts] = useState(0);

  useEffect(() => {
    const recognition = new BrowserSpeechRecognitionAdapter();
    const synthesis = new BrowserSpeechSynthesisAdapter();
    recognitionRef.current = recognition;
    synthesisRef.current = synthesis;
    // Feature detection depends on `window`, which doesn't exist during SSR.
    // Setting it here (rather than as a useState initializer) is deliberate:
    // an initializer would run during hydration too and could disagree with
    // the server-rendered (window-less) output, causing a hydration mismatch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRecognitionSupported(recognition.isSupported());
    setSynthesisSupported(synthesis.isSupported());

    let accumulatedFinal = "";
    let silenceTimer: ReturnType<typeof setTimeout> | null = null;

    function clearSilenceTimer() {
      if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
      }
    }

    function resetSilenceTimer() {
      clearSilenceTimer();
      silenceTimer = setTimeout(() => {
        recognitionRef.current?.stop();
      }, SILENCE_TIMEOUT_MS);
    }

    recognition.onResult((transcript, isFinal) => {
      resetSilenceTimer();
      if (isFinal) {
        accumulatedFinal = `${accumulatedFinal} ${transcript}`.trim();
        setInterimText(accumulatedFinal);
      } else {
        setInterimText(`${accumulatedFinal} ${transcript}`.trim());
      }
    });

    recognition.onError((code) => {
      clearSilenceTimer();
      // "aborted" fires when we call stop()/abort() ourselves - expected,
      // not a real error worth surfacing to the candidate.
      if (code !== "aborted") {
        setVoiceError(code);
      }
    });

    recognition.onEnd(() => {
      clearSilenceTimer();
      setStatus("idle");
      const finalText = accumulatedFinal.trim();
      if (finalText) {
        setEmptyAttempts(0);
        onFinalTranscriptRef.current(finalText);
      } else {
        setEmptyAttempts((n) => n + 1);
      }
      accumulatedFinal = "";
      setInterimText("");
    });

    return () => {
      clearSilenceTimer();
      recognition.abort();
      synthesis.cancel();
    };
  }, []);

  const speak = useCallback((text: string, onEnd?: () => void) => {
    if (!synthesisRef.current?.isSupported()) {
      onEnd?.();
      return;
    }
    setStatus("speaking");
    synthesisRef.current.speak(text, () => {
      setStatus((prev) => (prev === "speaking" ? "idle" : prev));
      onEnd?.();
    });
  }, []);

  const stopSpeaking = useCallback(() => {
    synthesisRef.current?.cancel();
    setStatus((prev) => (prev === "speaking" ? "idle" : prev));
  }, []);

  const startListening = useCallback((onFinalTranscript: (text: string) => void) => {
    if (!recognitionRef.current?.isSupported() || status === "listening") return;
    setVoiceError(null);
    setInterimText("");
    onFinalTranscriptRef.current = onFinalTranscript;
    setStatus("listening");
    recognitionRef.current.start();
  }, [status]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  return {
    status,
    interimText,
    recognitionSupported,
    synthesisSupported,
    voiceError,
    emptyAttempts,
    speak,
    stopSpeaking,
    startListening,
    stopListening,
  };
}
