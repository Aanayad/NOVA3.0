/**
 * Nova 3.0 — Orb controller
 * Small state machine that flips the orb's `data-state` attribute, which
 * drives every animation purely through CSS (see style.css). Keeping the
 * animation logic in CSS keeps this file tiny and keeps frame rates smooth.
 */
window.NovaOrb = (() => {
  const svg = document.getElementById("orbSvg");
  const caption = document.getElementById("orbCaption");
  const statusPill = document.getElementById("statusPill");
  const statusText = document.getElementById("statusText");

  const CAPTIONS = {
    idle: 'Tap the orb, or just say <strong>“Nova”</strong>',
    listening: "Listening…",
    thinking: "Thinking…",
    speaking: "Speaking…",
  };

  let current = "idle";

  function setState(state) {
    if (!CAPTIONS[state]) state = "idle";
    current = state;
    svg.dataset.state = state;
    statusPill.dataset.state = state;
    caption.innerHTML = CAPTIONS[state];
    statusText.textContent = state.charAt(0).toUpperCase() + state.slice(1);
  }

  function getState() {
    return current;
  }

  return { setState, getState };
})();
