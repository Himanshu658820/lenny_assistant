const API_BASE = "/api";

const state = {
  sessions: [],
  currentSessionId: null,
  messages: [],
  provider: "ollama",
  isLoading: false,
  currentArtifact: null,
};

const sessionListEl = document.getElementById("session-list");
const chatMessagesEl = document.getElementById("chat-messages");
const emptyStateEl = document.getElementById("empty-state");
const chatFormEl = document.getElementById("chat-form");
const chatInputEl = document.getElementById("chat-input");
const btnNewChatEl = document.getElementById("btn-new-chat");
const chatTitleEl = document.getElementById("chat-title");
const providerSelectEl = document.getElementById("provider-select");

const artifactPaneEl = document.getElementById("artifact-pane");
const artifactTitleEl = document.getElementById("artifact-title");
const artifactMetaEl = document.getElementById("artifact-meta");
const artifactContentEl = document.getElementById("artifact-content");
const btnCloseArtifactEl = document.getElementById("btn-close-artifact");

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

// ---------- API ----------
async function fetchSessions() {
  const res = await fetch(`${API_BASE}/sessions`);
  state.sessions = await res.json();
  renderSessions();
}

async function fetchMessages(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
  state.messages = await res.json();
  renderMessages();
}

async function deleteSession(id) {
  if (!window.confirm("Delete this chat? This cannot be undone.")) return;

  const res = await fetch(`${API_BASE}/sessions/${id}`, { method: "DELETE" });
  if (!res.ok) {
    alert("Failed to delete chat.");
    return;
  }

  if (state.currentSessionId === id) {
    state.currentSessionId = null;
    state.messages = [];
    chatTitleEl.textContent = "New Conversation";
    renderMessages();
    closeArtifactPane();
  }

  await fetchSessions();
}

// ---------- Streaming chat ----------
async function sendMessage(text) {
  state.isLoading = true;
  state.messages.push({ role: "user", content: text, created_at: new Date().toISOString() });
  renderMessages();

  // Live assistant bubble
  const wrap = document.createElement("div");
  wrap.className = "flex gap-4 max-w-4xl mx-auto";
  const bubble = document.createElement("div");
  bubble.className = "p-4 rounded-2xl bg-white border border-slate-200 rounded-tl-none shadow-sm max-w-[80%]";
  const liveEl = document.createElement("div");
  liveEl.className = "whitespace-pre-wrap text-[15px] leading-7 text-slate-700";
  bubble.appendChild(liveEl);
  wrap.appendChild(bubble);
  chatMessagesEl.appendChild(wrap);
  chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;

  let donePayload = null;
  let errorText = null;

  const handleEvent = (name, payload) => {
    if (name === "session") {
      state.currentSessionId = payload.session_id;
    } else if (name === "token") {
      liveEl.textContent += payload.text;
      chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
    } else if (name === "sources") {
      if (payload && payload.length) {
        const src = document.createElement("div");
        src.className = "mt-3 pt-3 border-t border-slate-200 text-xs text-slate-500";
        src.innerHTML =
          `<strong>Sources:</strong> ` +
          payload.map((s) => `<span class="inline-block bg-slate-100 px-2 py-0.5 rounded mr-1 mb-1">${escapeHtml(s.title)}</span>`).join("");
        bubble.appendChild(src);
      }
    } else if (name === "artifact") {
      state.currentArtifact = payload;
      renderArtifact();
      showArtifactPane();
    } else if (name === "error") {
      errorText = payload.message;
      liveEl.textContent = "⚠️ " + payload.message;
      bubble.classList.add("border-red-200");
    } else if (name === "done") {
      donePayload = payload;
    }
  };

  try {
    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: state.currentSessionId,
        llm_provider: state.provider,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.error?.message || `Request failed (${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);

        let name = "message";
        let data = "";
        for (const line of raw.split("\n")) {
          if (line.startsWith("event:")) name = line.slice(6).trim();
          else if (line.startsWith("data:")) data += line.slice(5).trim();
        }
        if (data) {
          try {
            handleEvent(name, JSON.parse(data));
          } catch (_) {}
        }
      }
    }
  } catch (err) {
    errorText = err.message;
    liveEl.textContent = "⚠️ Error: " + err.message;
  }

  if (donePayload) {
    state.messages.push({
      role: "assistant",
      content: donePayload.answer,
      sources: donePayload.sources,
      meta: {
        artifact: donePayload.artifact,
        skill: donePayload.skill,
        supported: donePayload.supported,
        provider: donePayload.provider,
      },
      created_at: new Date().toISOString(),
    });
  }

  else {
    state.messages.push({
        role: "assistant",
        content: `⚠️ **Error:** ${errorText || "The response stream ended unexpectedly. Check backend logs."}`,
        meta: { error: true },
        created_at: new Date().toISOString(),
    });
  }

  state.isLoading = false;
  await fetchSessions();

  const cur = state.sessions.find((s) => s.id === state.currentSessionId);
  if (cur) chatTitleEl.textContent = cur.title || "Conversation";

  renderMessages();
}

// ---------- Rendering ----------
function renderSessions() {
  sessionListEl.innerHTML = "";

  state.sessions.forEach((s) => {
    const row = document.createElement("div");
    row.className = "group flex items-center gap-1";

    const btn = document.createElement("button");
    btn.className = `flex-1 text-left px-3 py-2 rounded-lg text-sm truncate transition ${
      s.id === state.currentSessionId ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800"
    }`;
    btn.textContent = s.title || "New Chat";
    btn.onclick = () => selectSession(s.id, s.title);

    const del = document.createElement("button");
    del.className =
      "opacity-0 group-hover:opacity-100 shrink-0 p-1.5 rounded-md text-slate-500 hover:text-red-400 hover:bg-slate-800 transition";
    del.setAttribute("aria-label", "Delete chat");
    del.title = "Delete chat";
    del.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>`;
    del.onclick = (e) => {
      e.stopPropagation();
      deleteSession(s.id);
    };

    row.appendChild(btn);
    row.appendChild(del);
    sessionListEl.appendChild(row);
  });
}

function selectSession(id, title) {
  state.currentSessionId = id;
  chatTitleEl.textContent = title || "Conversation";
  fetchMessages(id);
  closeArtifactPane();
}

function renderMessages() {
  chatMessagesEl.innerHTML = "";

  if (state.messages.length === 0 && !state.isLoading) {
    chatMessagesEl.appendChild(emptyStateEl);
    return;
  }

  state.messages.forEach((m) => {
    const div = document.createElement("div");
    div.className = `flex gap-4 max-w-4xl mx-auto ${m.role === "user" ? "justify-end" : ""}`;

    const bubble = document.createElement("div");
    bubble.className = `p-4 rounded-2xl shadow-sm max-w-[80%] ${
      m.role === "user"
        ? "bg-indigo-600 text-white rounded-tr-none"
        : m.meta?.error
          ? "bg-red-50 text-red-800 border border-red-200 rounded-tl-none"
          : "bg-white border border-slate-200 rounded-tl-none"
    }`;

    bubble.innerHTML = DOMPurify.sanitize(marked.parse(m.content));

    if (m.sources && m.sources.length > 0) {
      const sourcesDiv = document.createElement("div");
      sourcesDiv.className = "mt-3 pt-3 border-t border-slate-200 text-xs text-slate-500";
      sourcesDiv.innerHTML =
        `<strong>Sources:</strong> ` +
        m.sources.map((s) => `<span class="inline-block bg-slate-100 px-2 py-0.5 rounded mr-1 mb-1">${escapeHtml(s.title)}</span>`).join("");
      bubble.appendChild(sourcesDiv);
    }

    if (m.meta?.artifact) {
      const artBtn = document.createElement("button");
      artBtn.className = "mt-3 text-xs font-medium text-indigo-600 hover:text-indigo-800 flex items-center gap-1";
      artBtn.innerHTML = `📄 View ${escapeHtml(m.meta.artifact.type)} artifact`;
      artBtn.onclick = () => {
        state.currentArtifact = m.meta.artifact;
        renderArtifact();
        showArtifactPane();
      };
      bubble.appendChild(artBtn);
    }

    div.appendChild(bubble);
    chatMessagesEl.appendChild(div);
  });

  chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
}

// ---------- Artifact viewer (sandboxed) ----------
function renderArtifact() {
  if (!state.currentArtifact) return;

  const art = state.currentArtifact;
  artifactTitleEl.textContent = art.title;
  artifactMetaEl.textContent = `${art.type.toUpperCase()} • ${art.word_count || 0} words`;
  artifactContentEl.innerHTML = "";

  if (art.type === "markdown") {
    const cleanHtml = DOMPurify.sanitize(marked.parse(art.content), { USE_PROFILES: { html: true } });
    const container = document.createElement("div");
    container.className = "prose prose-slate max-w-none";
    container.innerHTML = cleanHtml;
    artifactContentEl.appendChild(container);
  } else if (art.type === "html") {
    // sandbox="" blocks scripts, forms, popups, top-nav: untrusted HTML is isolated
    const iframe = document.createElement("iframe");
    iframe.setAttribute("sandbox", "");
    iframe.setAttribute("srcdoc", art.content);
    iframe.className = "w-full h-full border border-slate-200 rounded-lg bg-white";
    artifactContentEl.appendChild(iframe);
  }
}

function showArtifactPane() {
  artifactPaneEl.classList.remove("hidden");
  artifactPaneEl.classList.add("flex");
}

function closeArtifactPane() {
  artifactPaneEl.classList.add("hidden");
  artifactPaneEl.classList.remove("flex");
  state.currentArtifact = null;
}

// ---------- Events ----------
chatFormEl.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInputEl.value.trim();
  if (!text || state.isLoading) return;

  chatInputEl.value = "";
  emptyStateEl.remove();
  await sendMessage(text);
});

btnNewChatEl.addEventListener("click", () => {
  state.currentSessionId = null;
  state.messages = [];
  chatTitleEl.textContent = "New Conversation";
  renderMessages();
  closeArtifactPane();
});

btnCloseArtifactEl.addEventListener("click", closeArtifactPane);

providerSelectEl.addEventListener("change", (e) => {
  state.provider = e.target.value;
});

chatInputEl.addEventListener("input", () => {
  chatInputEl.style.height = "auto";
  chatInputEl.style.height = chatInputEl.scrollHeight + "px";
});

fetchSessions();

chatInputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatFormEl.requestSubmit();
  }
});