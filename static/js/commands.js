/**
 * Nova 3.0 — Command executor
 * Takes the structured action returned by /api/command (see
 * automation/command_router.py) and performs it in the browser.
 *
 * IMPORTANT: opening real browser tabs (websites, Google/YouTube searches)
 * is handled in app.js, not here — it has to open the tab synchronously on
 * the user's click/voice action, or browsers silently block it as a popup.
 * This file only handles things that happen INSIDE the page: the embedded
 * YouTube player for a known video, system-command confirmations, and
 * screenshots.
 */
window.NovaCommands = (() => {
  const ytModal = document.getElementById("ytModal");
  const ytFrame = document.getElementById("ytFrame");
  const ytClose = document.getElementById("ytModalClose");

  ytClose.addEventListener("click", closeYoutube);

  function execute(routed) {
    switch (routed.type) {
      case "browser":
        return handleBrowser(routed);
      case "player_control":
        return handlePlayerControl(routed.action);
      case "client_action":
        return handleClientAction(routed.action);
      default:
        return; // "system", "info_lookup", "chat" etc. need no client action
    }
  }

  function handleBrowser(routed) {
    const url = routed.url;
    // Only a SPECIFIC known video (a real /watch?v=... URL) gets the inline
    // player. Search-result URLs are opened as a real tab by app.js instead,
    // because YouTube does not reliably support embedding search results.
    if (url && url.includes("youtube.com/watch")) {
      openYoutube(url);
    }
  }

  function openYoutube(watchUrl) {
    let videoId = null;
    try {
      videoId = new URL(watchUrl).searchParams.get("v");
    } catch (_e) { /* ignore malformed URL */ }

    if (!videoId) return; // let app.js's normal tab-open handle it instead

    ytFrame.src = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
    ytModal.hidden = false;
  }

  function closeYoutube() {
    ytFrame.src = "";
    ytModal.hidden = true;
  }

  function handlePlayerControl(action) {
    if (ytModal.hidden) return;
    if (action === "fullscreen" && ytFrame.requestFullscreen) {
      ytFrame.requestFullscreen();
    } else if (action === "exit fullscreen" && document.exitFullscreen) {
      document.exitFullscreen();
    } else {
      console.info(`Player control "${action}" requested — full play/pause/next control needs the YouTube IFrame Player API (not yet wired up).`);
    }
  }

  function handleClientAction(action) {
    if (action === "screenshot") takeScreenshot();
  }

  async function takeScreenshot() {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        alert("Screenshot requires a browser that supports screen capture.");
        return;
      }
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      const track = stream.getVideoTracks()[0];
      const capture = new ImageCapture(track);
      const bitmap = await capture.grabFrame();
      track.stop();

      const canvas = document.createElement("canvas");
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      canvas.getContext("2d").drawImage(bitmap, 0, 0);

      const link = document.createElement("a");
      link.download = `nova-screenshot-${Date.now()}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
    } catch (err) {
      console.warn("Screenshot cancelled or failed:", err);
    }
  }

  return { execute, openYoutube, closeYoutube };
})();
