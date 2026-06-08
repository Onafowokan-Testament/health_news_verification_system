(function () {
  const messagesEl = document.getElementById("chat-messages-inner");
  const composerForm = document.getElementById("chat-composer-form");
  const textarea = document.getElementById("chat-input");
  const btnSend = document.getElementById("btn-send");
  const btnMic = document.getElementById("btn-mic");
  const btnNewChat = document.getElementById("btn-new-chat");
  const sidebar = document.getElementById("chat-sidebar");
  const btnMenu = document.getElementById("btn-menu-toggle");
  const statusEl = document.getElementById("chat-status");

  const optSlow = document.getElementById("opt-slow");
  const optAudioOut = document.getElementById("opt-audio-out");
  const LANGUAGE = "English"; // English only

  let mediaRecorder = null;
  let recordedChunks = [];
  let recording = false;

  function setStatus(message, state) {
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.classList.remove("is-busy", "is-error");
    if (state === "busy") {
      statusEl.classList.add("is-busy");
    } else if (state === "error") {
      statusEl.classList.add("is-error");
    }
  }

  function scrollToBottom() {
    const wrap = document.getElementById("chat-messages");
    if (wrap) wrap.scrollTop = wrap.scrollHeight;
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function linkifyUrls(text) {
    // Convert URLs in text to clickable links
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const escaped = escapeHtml(text);
    return escaped.replace(urlRegex, function(url) {
      // Remove trailing punctuation that shouldn't be part of URL
      const trimmed = url.replace(/[.,;:!?)\]]*$/, '');
      return '<a href="' + escapeHtml(trimmed) + '" target="_blank" rel="noopener noreferrer" style="color: #0066cc; text-decoration: underline;">' + escapeHtml(trimmed) + '</a>';
    });
  }

  function verdictClass(v) {
    const x = (v || "").toUpperCase();
    if (x === "TRUE") return "true";
    if (x === "FALSE") return "false";
    if (x === "PARTIALLY TRUE") return "partial";
    return "unclear";
  }

  function appendUser(text) {
    const row = document.createElement("div");
    row.className = "chat-msg-row user";
    row.innerHTML =
      '<div class="chat-avatar">You</div><div class="chat-bubble"><div class="msg-body">' +
      escapeHtml(text) +
      "</div></div>";
    messagesEl.appendChild(row);
    scrollToBottom();
  }

  function appendAssistant(content, verdict) {
    const row = document.createElement("div");
    row.className = "chat-msg-row assistant";
    let tag = "";
    if (verdict) {
      tag =
        '<span class="chat-verdict-tag ' +
        verdictClass(verdict) +
        '">' +
        escapeHtml(verdict) +
        "</span>";
    }
    row.innerHTML =
      '<div class="chat-avatar">M</div><div class="chat-bubble">' +
      tag +
      '<div class="msg-body">' +
      linkifyUrls(content) +
      "</div></div>";
    messagesEl.appendChild(row);
    scrollToBottom();
    return row.querySelector(".chat-bubble");
  }

  function appendLoading() {
    const row = document.createElement("div");
    row.className = "chat-msg-row assistant chat-msg-loading";
    row.id = "chat-loading-row";
    row.innerHTML =
      '<div class="chat-avatar">M</div><div class="chat-bubble"><div class="msg-body">Thinking…</div></div>';
    messagesEl.appendChild(row);
    scrollToBottom();
    return row;
  }

  function removeLoading() {
    const el = document.getElementById("chat-loading-row");
    if (el) el.remove();
  }

  function appendError(msg) {
    const row = document.createElement("div");
    row.className = "chat-msg-row assistant chat-msg-error";
    row.innerHTML =
      '<div class="chat-avatar">!</div><div class="chat-bubble"><div class="msg-body">' +
      escapeHtml(msg) +
      "</div></div>";
    messagesEl.appendChild(row);
    scrollToBottom();
  }

  function attachAudio(bubbleEl, base64) {
    if (!base64 || !bubbleEl) {
      return; // No audio available - that's OK
    }
    try {
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.className = "chat-audio-inline";
      audio.src = "data:audio/mpeg;base64," + base64;
      bubbleEl.appendChild(audio);
    } catch (e) {
      // Audio attachment failed silently - response text is still available
      console.warn("Audio attachment failed:", e);
    }
  }

  async function sendText(text) {
    const body = {
      message: text,
      language: LANGUAGE,
      slow_speech: optSlow.checked,
      audio_response: optAudioOut.checked,
    };
    setStatus("Sending message...", "busy");
    appendLoading();
    btnSend.disabled = true;
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(body),
      });
      let data;
      try {
        data = await res.json();
      } catch {
        removeLoading();
        appendError("Unexpected response from server.");
        return;
      }
      removeLoading();
      if (res.status === 401) {
        window.location.href = "/login?next=/chat";
        return;
      }
      if (!res.ok) {
        let detail = data.detail ?? data.error ?? "Request failed.";
        if (Array.isArray(detail)) {
          detail = detail
            .map(function (x) {
              return typeof x === "object" && x !== null ? x.msg || JSON.stringify(x) : String(x);
            })
            .join(" ");
        }
        appendError(String(detail));
        setStatus("Message failed to process.", "error");
        return;
      }
      const bubble = appendAssistant(data.response, data.verdict);
      if (data.audio_base64) {
        attachAudio(bubble, data.audio_base64);
      }
      setStatus("Reply received.", "");
    } catch (e) {
      removeLoading();
      appendError(String(e.message || e));
      setStatus("Could not reach the server.", "error");
    } finally {
      btnSend.disabled = false;
      scrollToBottom();
    }
  }

  async function sendVoice(blob) {
    setStatus("Sending voice note...", "busy");
    appendLoading();
    btnMic.disabled = true;
    const fd = new FormData();
    fd.append("audio", blob, "voice.webm");
    fd.append("language", LANGUAGE);
    fd.append("slow_speech", optSlow.checked ? "true" : "false");
    fd.append("audio_response", optAudioOut.checked ? "true" : "false");
    try {
      const res = await fetch("/api/chat-voice", {
        method: "POST",
        credentials: "same-origin",
        body: fd,
      });
      let data;
      try {
        data = await res.json();
      } catch {
        removeLoading();
        appendError("Unexpected response from server.");
        return;
      }
      removeLoading();
      if (res.status === 401) {
        window.location.href = "/login?next=/chat";
        return;
      }
      if (!res.ok) {
        let detail = data.detail ?? data.error ?? "Voice request failed.";
        if (Array.isArray(detail)) {
          detail = detail
            .map(function (x) {
              return typeof x === "object" && x !== null ? x.msg || JSON.stringify(x) : String(x);
            })
            .join(" ");
        }
        appendError(String(detail));
        setStatus("Voice message failed to process.", "error");
        return;
      }
      if (data.transcription) appendUser(data.transcription);
      const bubble = appendAssistant(data.response, data.verdict);
      if (data.audio_base64) {
        attachAudio(bubble, data.audio_base64);
      }
      setStatus("Reply received.", "");
    } catch (e) {
      removeLoading();
      appendError(String(e.message || e));
      setStatus("Could not reach the server.", "error");
    } finally {
      btnMic.disabled = false;
      scrollToBottom();
    }
  }

  composerForm.addEventListener("submit", function (e) {
    e.preventDefault();
    const t = textarea.value.trim();
    if (!t) return;
    appendUser(t);
    textarea.value = "";
    textarea.style.height = "auto";
    sendText(t);
  });

  textarea.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      composerForm.dispatchEvent(new Event("submit", { cancelable: true }));
    }
  });

  textarea.addEventListener("input", function () {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + "px";
  });

  btnMic.addEventListener("click", async function () {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      appendError("Your browser does not support microphone recording.");
      return;
    }
    if (recording && mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      recording = false;
      btnMic.classList.remove("recording");
      btnMic.setAttribute("aria-label", "Record voice");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordedChunks = [];
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = function (ev) {
        if (ev.data.size > 0) recordedChunks.push(ev.data);
      };
      mediaRecorder.onstop = async function () {
        stream.getTracks().forEach(function (t) {
          t.stop();
        });
        const blob = new Blob(recordedChunks, { type: "audio/webm" });
        if (blob.size < 500) {
          appendError("Recording too short. Hold the mic and speak, then tap again to stop.");
          return;
        }
        await sendVoice(blob);
      };
      mediaRecorder.start();
      recording = true;
      btnMic.classList.add("recording");
      btnMic.setAttribute("aria-label", "Stop recording");
    } catch (err) {
      appendError("Microphone permission denied or unavailable.");
    }
  });

  btnNewChat.addEventListener("click", function () {
    messagesEl.innerHTML = document.getElementById("chat-welcome-template").innerHTML;
    textarea.value = "";
    textarea.style.height = "auto";
    sidebar.classList.remove("open");
    setStatus("Ready", "");
  });

  if (btnMenu && sidebar) {
    btnMenu.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });
  }

  document.addEventListener("click", function (e) {
    if (!sidebar || window.innerWidth > 860) return;
    if (
      sidebar.classList.contains("open") &&
      !sidebar.contains(e.target) &&
      e.target !== btnMenu &&
      !btnMenu.contains(e.target)
    ) {
      sidebar.classList.remove("open");
    }
  });

  setStatus("Ready", "");
})();
