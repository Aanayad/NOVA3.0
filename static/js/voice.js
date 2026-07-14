/**
 * Nova 3.0 — Voice engine
 * - Continuous "Nova" wake-word listening using the Web Speech API
 * - Streaming speech-to-text once woken
 * - Natural text-to-speech with interrupt + queueing
 * - Premium UI sound effects synthesized on the fly with the Web Audio API
 *   (no binary asset files needed, so there is nothing to "fake")
 *
 * Browser support: Chrome, Edge, and other Chromium browsers expose
 * webkitSpeechRecognition. Firefox/Safari have partial/no support for
 * continuous recognition; Nova falls back to push-to-talk (mic button)
 * automatically when the API is unavailable.
 */
window.NovaVoice = (() => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const synth = window.speechSynthesis;
  const WAKE_WORD = "nova";

  let recognizer = null;
  let isWakeListening = false;
  let isCommandListening = false;
  let onWake = () => {};
  let onCommand = () => {};
  let speechQueue = [];
  let isSpeaking = false;
  let preferredVoice = null;

  // ------------------------------------------------------------------ //
  // Synthesized sound effects (Web Audio API — no mp3 files required)
  // ------------------------------------------------------------------ //
  const audioCtx = window.AudioContext ? new AudioContext() : null;

  function tone(freq, duration, type = "sine", gainValue = 0.08, delay = 0) {
    if (!audioCtx) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.value = gainValue;
    osc.connect(gain).connect(audioCtx.destination);
    const start = audioCtx.currentTime + delay;
    osc.start(start);
    gain.gain.exponentialRampToValueAtTime(0.001, start + duration);
    osc.stop(start + duration + 0.02);
  }

  const sounds = {
    wake: () => { tone(660, 0.09); tone(880, 0.12, "sine", 0.08, 0.09); },
    listening: () => tone(520, 0.08, "sine", 0.05),
    thinking: () => { tone(440, 0.05, "triangle", 0.04); tone(440, 0.05, "triangle", 0.04, 0.12); },
    speaking: () => tone(600, 0.06, "sine", 0.04),
    success: () => { tone(700, 0.08, "sine", 0.07); tone(950, 0.1, "sine", 0.07, 0.08); },
    error: () => { tone(220, 0.18, "sawtooth", 0.05); },
  };

  // ------------------------------------------------------------------ //
  // Text-to-speech (natural voice, Alexa-like cadence)
  // ------------------------------------------------------------------ //
  function pickVoice() {
    const voices = synth.getVoices();
    if (!voices.length) return null;
    // Prefer a natural-sounding "female" English voice if available (closest
    // free equivalent to a premium assistant voice in-browser).
    return (
      voices.find((v) => /en-US/i.test(v.lang) && /female|natural|aria|jenny|zira/i.test(v.name)) ||
      voices.find((v) => /en/i.test(v.lang)) ||
      voices[0]
    );
  }
  if (synth) {
    synth.onvoiceschanged = () => { preferredVoice = pickVoice(); };
    preferredVoice = pickVoice();
  }

  function speak(text, { rate = 1, pitch = 1, volume = 1, onEnd } = {}) {
    if (!synth || !text) return;
    speechQueue.push({ text, rate, pitch, volume, onEnd });
    if (!isSpeaking) _drainQueue();
  }

  function _drainQueue() {
    if (!speechQueue.length) {
      isSpeaking = false;
      return;
    }
    isSpeaking = true;
    const { text, rate, pitch, volume, onEnd } = speechQueue.shift();
    const utter = new SpeechSynthesisUtterance(text);
    utter.voice = preferredVoice;
    utter.rate = rate;
    utter.pitch = pitch;
    utter.volume = volume;
    utter.onend = () => { onEnd && onEnd(); _drainQueue(); };
    utter.onerror = () => { onEnd && onEnd(); _drainQueue(); };
    synth.speak(utter);
  }

  function stopSpeaking() {
    speechQueue = [];
    if (synth) synth.cancel();
    isSpeaking = false;
  }

  // ------------------------------------------------------------------ //
  // Speech recognition (wake word + command capture)
  // ------------------------------------------------------------------ //
  function isSupported() {
    return !!SpeechRecognition;
  }

  function startWakeWordListening(onWakeCb) {
    if (!isSupported()) return false;
    onWake = onWakeCb || onWake;
    if (isWakeListening) return true;

    recognizer = new SpeechRecognition();
    recognizer.continuous = true;
    recognizer.interimResults = true;
    recognizer.lang = "en-US";

    recognizer.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((r) => r[0].transcript)
        .join(" ")
        .toLowerCase();

      if (transcript.includes(WAKE_WORD)) {
        sounds.wake();
        stopWakeWordListening();
        onWake();
      }
    };

    recognizer.onend = () => {
      if (isWakeListening) {
        try { recognizer.start(); } catch (_e) { /* already running */ }
      }
    };

    recognizer.onerror = (e) => {
      if (e.error === "no-speech" || e.error === "aborted") return;
      console.warn("Wake-word recognizer error:", e.error);
    };

    isWakeListening = true;
    try { recognizer.start(); } catch (_e) { /* noop */ }
    return true;
  }

  function stopWakeWordListening() {
    isWakeListening = false;
    if (recognizer) {
      try { recognizer.stop(); } catch (_e) { /* noop */ }
    }
  }

  function listenForCommand(onCommandCb, { timeoutMs = 7000 } = {}) {
    if (!isSupported()) {
      onCommandCb(null, "Speech recognition isn't supported in this browser.");
      return;
    }
    onCommand = onCommandCb;
    isCommandListening = true;
    sounds.listening();

    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = "en-US";

    let finalTranscript = "";
    const timer = setTimeout(() => { try { rec.stop(); } catch (_e) {} }, timeoutMs);

    rec.onresult = (event) => {
      let interim = "";
      for (const result of event.results) {
        if (result.isFinal) finalTranscript += result[0].transcript;
        else interim += result[0].transcript;
      }
      document.getElementById("orbTranscript").textContent = finalTranscript + interim;
    };

    rec.onend = () => {
      clearTimeout(timer);
      isCommandListening = false;
      onCommand(finalTranscript.trim() || null);
    };

    rec.onerror = (e) => {
      clearTimeout(timer);
      isCommandListening = false;
      if (e.error !== "no-speech") sounds.error();
      onCommand(null, e.error);
    };

    try { rec.start(); } catch (_e) { onCommandCb(null, "mic-busy"); }
  }

  return {
    isSupported,
    startWakeWordListening,
    stopWakeWordListening,
    listenForCommand,
    speak,
    stopSpeaking,
    sounds,
  };
})();
