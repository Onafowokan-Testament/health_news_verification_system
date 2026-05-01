(function () {
  const messagesEl = document.getElementById("chat-messages-inner");
  const composerForm = document.getElementById("chat-composer-form");
  const textarea = document.getElementById("chat-input");
  const btnSend = document.getElementById("btn-send");
  const btnMic = document.getElementById("btn-mic");
  const btnNewChat = document.getElementById("btn-new-chat");
  const sidebar = document.getElementById("chat-sidebar");
  const btnMenu = document.getElementById("btn-menu-toggle");

  const langSelect = document.getElementById("chat-language");
  const optSlow = document.getElementById("opt-slow");
  const optAudioOut = document.getElementById("opt-audio-out");

  let mediaRecorder = null;
  let recordedChunks = [];
  let recording = false;

  function scrollToBottom() {
    const wrap = document.getElementById("chat-messages");
    if (wrap) wrap.scrollTop = wrap.scrollHeight;
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
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
      escapeHtml(content) +
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
    if (!base64 || !bubbleEl) return;
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.className = "chat-audio-inline";
    audio.src = "data:audio/mpeg;base64," + base64;
    bubbleEl.appendChild(audio);
  }

  async function sendText(text) {
    const body = {
      message: text,
      language: langSelect.value,
      slow_speech: optSlow.checked,
      audio_response: optAudioOut.checked,
    };
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
        return;
      }
      const bubble = appendAssistant(data.response, data.verdict);
      if (data.audio_base64) attachAudio(bubble, data.audio_base64);
    } catch (e) {
      removeLoading();
      appendError(String(e.message || e));
    } finally {
      btnSend.disabled = false;
      scrollToBottom();
    }
  }

  async function sendVoice(blob) {
    appendLoading();
    btnMic.disabled = true;
    const fd = new FormData();
    fd.append("audio", blob, "voice.webm");
    fd.append("language", langSelect.value);
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
        return;
      }
      if (data.transcription) appendUser(data.transcription);
      const bubble = appendAssistant(data.response, data.verdict);
      if (data.audio_base64) attachAudio(bubble, data.audio_base64);
    } catch (e) {
      removeLoading();
      appendError(String(e.message || e));
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
})();
