/**
 * Nova 3.0 — App glue
 * Single-view, voice-first assistant. No chat history is persisted anywhere -
 * the on-screen transcript is purely in-memory and clears on refresh, by design.
 */
(() => {
  const API = { command: "/api/command" };

  const $ = (id) => document.getElementById(id);
  const splash = $("splash");
  const appShell = $("appShell");
  const chatMessages = $("chatMessages");
  const chatForm = $("chatForm");
  const chatInput = $("chatInput");
  const micBtn = $("micBtn");
  const orbButton = $("orbButton");
  const orbTranscript = $("orbTranscript");
  const settingsBtn = $("settingsBtn");
  const bgParticles = $("bgParticles");

  const SESSION_ID = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`; // in-memory only

  // ------------------------------------------------------------------ //
  // Ambient background particles (purely decorative, CSS-driven)
  // ------------------------------------------------------------------ //
  function spawnParticles(count = 26) {
    for (let i = 0; i < count; i++) {
      const p = document.createElement("div");
      p.className = "particle";
      p.style.left = `${Math.random() * 100}%`;
      p.style.bottom = `-10px`;
      p.style.animationDuration = `${8 + Math.random() * 14}s`;
      p.style.animationDelay = `${Math.random() * 10}s`;
      bgParticles.appendChild(p);
    }
  }

  // ------------------------------------------------------------------ //
  // Boot
  // ------------------------------------------------------------------ //
  window.addEventListener("load", () => {
    setTimeout(() => {
      splash.style.display = "none";
      appShell.hidden = false;
    }, 1400);

    spawnParticles();

    if (window.NovaVoice.isSupported()) {
      window.NovaVoice.startWakeWordListening(onWake);
    } else {
      orbTranscript.textContent = "Voice not supported in this browser — use the mic button or type instead.";
    }
  });

  settingsBtn.addEventListener("click", () => {
    alert(
      "Settings panel is coming soon.\n\nPlanned: voice speed/pitch, male/female voice, dark/light theme.\nSystem control (shutdown, open apps, etc.) is toggled via ENABLE_SYSTEM_CONTROL in your .env file."
    );
  });

  // ------------------------------------------------------------------ //
  // Chat rendering (in-memory only)
  // ------------------------------------------------------------------ //
  function renderMessage(role, text) {
    const bubble = document.createElement("div");
    bubble.className = `msg ${role}`;
    bubble.innerHTML = formatMarkdownish(text);
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
  }

  function formatMarkdownish(text) {
    const escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return escaped
      .replace(/```([\s\S]*?)```/g, (_m, code) => `<pre><code>${code.trim()}</code></pre>`)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\n/g, "<br/>");
  }

  // ------------------------------------------------------------------ //
  // Sending messages / commands
  // ------------------------------------------------------------------ //
  async function sendToNova(text, { spoken = false } = {}) {
    if (!text || !text.trim()) return;

    // Open a blank tab immediately, while this still counts as a direct
    // user action - opening it later (after an await) gets silently
    // blocked as a popup by most browsers.
    const pendingTab = window.open("", "_blank");

    renderMessage("user", text);
    window.NovaOrb.setState("thinking");
    window.NovaVoice.sounds.thinking();

    try {
      const res = await fetch(API.command, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: text, session_id: SESSION_ID }),
      });
      const routed = await res.json();

      const isEmbeddableVideo = routed.type === "browser" && routed.url && routed.url.includes("youtube.com/watch");

      if (routed.type === "browser" && routed.url && !isEmbeddableVideo) {
        if (pendingTab && !pendingTab.closed) pendingTab.location.href = routed.url;
        else window.open(routed.url, "_blank", "noopener,noreferrer");
      } else if (pendingTab && !pendingTab.closed) {
        pendingTab.close();
      }

      window.NovaCommands.execute(routed); // handles the auto-playing YouTube embed + system/screenshot cases

      const replyText = routed.reply || routed.spoken_reply || routed.result || "Done.";
      renderMessage("assistant", replyText);

      if (spoken) {
        window.NovaOrb.setState("speaking");
        window.NovaVoice.sounds.speaking();
        window.NovaVoice.speak(replyText, { onEnd: () => window.NovaOrb.setState("idle") });
      } else {
        window.NovaOrb.setState("idle");
      }
      window.NovaVoice.sounds.success();
    } catch (err) {
      console.error(err);
      if (pendingTab && !pendingTab.closed) pendingTab.close();
      window.NovaVoice.sounds.error();
      renderMessage("assistant", "Something went wrong reaching Nova's brain. Please try again.");
      window.NovaOrb.setState("idle");
    }
  }

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = chatInput.value;
    chatInput.value = "";
    sendToNova(text, { spoken: false });
  });

  // ------------------------------------------------------------------ //
  // Voice: wake word -> listen -> route
  // ------------------------------------------------------------------ //
  function onWake() {
    window.NovaOrb.setState("listening");
    orbTranscript.textContent = "";
    window.NovaVoice.listenForCommand((transcript) => {
      if (!transcript) {
        window.NovaOrb.setState("idle");
        window.NovaVoice.startWakeWordListening(onWake);
        return;
      }
      orbTranscript.textContent = transcript;
      sendToNova(transcript, { spoken: true }).finally(() => {
        window.NovaVoice.startWakeWordListening(onWake);
      });
    });
  }

  orbButton.addEventListener("click", () => {
    window.NovaVoice.stopWakeWordListening();
    onWake();
  });

  micBtn.addEventListener("click", () => {
    micBtn.classList.add("active");
    window.NovaVoice.stopWakeWordListening();
    window.NovaOrb.setState("listening");
    window.NovaVoice.listenForCommand((transcript) => {
      micBtn.classList.remove("active");
      if (transcript) {
        chatInput.value = transcript;
        sendToNova(transcript, { spoken: true });
      } else {
        window.NovaOrb.setState("idle");
      }
      window.NovaVoice.startWakeWordListening(onWake);
    });
  });
})();
