const API_BASE = localStorage.getItem("rabbitHoleApiBase") || "http://127.0.0.1:8000";

const sessionList = document.querySelector("#sessionList");
const sessionTitle = document.querySelector("#sessionTitle");
const connectionStatus = document.querySelector("#connectionStatus");
const responsePanel = document.querySelector("#responsePanel");
const emptyState = document.querySelector("#emptyState");
const answer = document.querySelector("#answer");
const sources = document.querySelector("#sources");
const activityList = document.querySelector("#activityList");
const exploreForm = document.querySelector("#exploreForm");
const queryInput = document.querySelector("#queryInput");
const submitButton = document.querySelector("#submitButton");
const newSessionButton = document.querySelector("#newSessionButton");

let activeSessionId = null;
let activeStream = null;
let responseText = "";

function setStatus(label, state = "idle") {
  connectionStatus.textContent = label;
  connectionStatus.classList.toggle("busy", state === "busy");
  connectionStatus.classList.toggle("error", state === "error");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMarkdown(text) {
  let html = escapeHtml(text);

  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noreferrer">$1</a>',
  );
  html = html.replace(/^### (.*)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.*)$/gm, "<h3>$1</h3>");
  html = html.replace(/^# (.*)$/gm, "<h3>$1</h3>");

  const blocks = html
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      if (block.startsWith("<h3>")) {
        return block;
      }

      return `<p>${block.replace(/\n/g, "<br>")}</p>`;
    });

  return blocks.join("");
}

function showAnswer() {
  emptyState.style.display = "none";
  answer.innerHTML = renderMarkdown(responseText);
  responsePanel.scrollTop = responsePanel.scrollHeight;
}

function clearWorkspace() {
  responseText = "";
  answer.innerHTML = "";
  sources.innerHTML = "";
  activityList.innerHTML = "";
  emptyState.style.display = "";
}

function addActivity(type, payload) {
  const item = document.createElement("div");
  const status = payload.status || type;

  item.className = `activity-item ${status}`;
  item.innerHTML = `
    <span class="activity-tag">${escapeHtml(type)}</span>
    <span>${escapeHtml(payload.tool_name || payload.message || status)}</span>
  `;

  activityList.appendChild(item);
  activityList.scrollTop = activityList.scrollHeight;
}

function renderSources(sourceList) {
  sources.innerHTML = "";

  for (const source of sourceList || []) {
    const card = document.createElement("article");
    card.className = "source-card";

    const title = escapeHtml(source.title || "Untitled source");
    const provider = escapeHtml(source.provider || "source");
    const sourceType = escapeHtml(source.source_type || "web");
    const summary = source.summary ? escapeHtml(source.summary) : "";
    const url = source.url ? escapeHtml(source.url) : "";

    card.innerHTML = `
      <span class="source-tag">${provider} / ${sourceType}</span>
      <h4>
        ${
          url
            ? `<a href="${url}" target="_blank" rel="noreferrer">${title}</a>`
            : title
        }
      </h4>
      ${summary ? `<p>${summary}</p>` : ""}
    `;

    sources.appendChild(card);
  }
}

function buildStreamUrl(query) {
  const encodedQuery = encodeURIComponent(query);

  if (activeSessionId) {
    return `${API_BASE}/explore/${activeSessionId}/stream?query=${encodedQuery}`;
  }

  return `${API_BASE}/explore/stream?query=${encodedQuery}`;
}

function closeActiveStream() {
  if (activeStream) {
    activeStream.close();
    activeStream = null;
  }
}

function parseEvent(event) {
  if (!event.data) {
    return {};
  }

  try {
    return JSON.parse(event.data);
  } catch {
    return { message: event.data };
  }
}

async function loadSessions() {
  try {
    const response = await fetch(`${API_BASE}/sessions?limit=30`);

    if (!response.ok) {
      throw new Error(`Sessions request failed with ${response.status}`);
    }

    const data = await response.json();
    renderSessions(data.sessions || []);
  } catch {
    sessionList.innerHTML = '<div class="session-meta">Sessions unavailable</div>';
  }
}

function renderSessions(sessions) {
  sessionList.innerHTML = "";

  if (!sessions.length) {
    sessionList.innerHTML = '<div class="session-meta">No saved sessions yet</div>';
    return;
  }

  for (const session of sessions) {
    const item = document.createElement("div");
    item.className = `session-item ${
      session.session_id === activeSessionId ? "active" : ""
    }`;

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "session-open";
    openButton.innerHTML = `
      <div class="session-name">${escapeHtml(session.title || "Untitled session")}</div>
      <div class="session-meta">${session.message_count || 0} messages</div>
    `;

    openButton.addEventListener("click", () => {
      activeSessionId = session.session_id;
      sessionTitle.textContent = session.title || "Untitled session";
      clearWorkspace();
      loadHistory(session.session_id);
      renderSessions(sessions);
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "session-delete";
    deleteButton.title = "Delete session";
    deleteButton.setAttribute("aria-label", `Delete ${session.title || "session"}`);
    deleteButton.textContent = "×";

    deleteButton.addEventListener("click", () => {
      deleteSession(session.session_id);
    });

    item.appendChild(openButton);
    item.appendChild(deleteButton);
    sessionList.appendChild(item);
  }
}

async function deleteSession(sessionId) {
  const shouldDelete = window.confirm("Delete this session and its history?");

  if (!shouldDelete) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error(`Delete request failed with ${response.status}`);
    }

    if (activeSessionId === sessionId) {
      closeActiveStream();
      activeSessionId = null;
      sessionTitle.textContent = "Untitled session";
      clearWorkspace();
      setStatus("Idle");
    }

    await loadSessions();
  } catch {
    addActivity("error", { message: "Could not delete session" });
  }
}

async function loadHistory(sessionId) {
  try {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/history`);

    if (!response.ok) {
      throw new Error(`History request failed with ${response.status}`);
    }

    const messages = await response.json();
    const lastAssistant = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");

    if (lastAssistant) {
      responseText = lastAssistant.content;
      showAnswer();
    }
  } catch {
    addActivity("error", { message: "History unavailable" });
  }
}

function startExploration(query) {
  closeActiveStream();
  clearWorkspace();
  setStatus("Streaming", "busy");
  submitButton.disabled = true;
  queryInput.disabled = true;

  const streamUrl = buildStreamUrl(query);
  activeStream = new EventSource(streamUrl);

  activeStream.addEventListener("thinking", (event) => {
    addActivity("thinking", parseEvent(event));
  });

  activeStream.addEventListener("tool_call", (event) => {
    addActivity("tool_call", parseEvent(event));
  });

  activeStream.addEventListener("tool_result", (event) => {
    addActivity("tool_result", parseEvent(event));
  });

  activeStream.addEventListener("content", (event) => {
    const data = parseEvent(event);
    responseText += data.delta || data.response || "";
    showAnswer();
  });

  activeStream.addEventListener("sources", (event) => {
    const data = parseEvent(event);
    renderSources(data.sources || []);
  });

  activeStream.addEventListener("done", (event) => {
    const data = parseEvent(event);

    if (data.session_id) {
      activeSessionId = data.session_id;
    }

    setStatus("Done");
    submitButton.disabled = false;
    queryInput.disabled = false;
    closeActiveStream();
    loadSessions();
  });

  activeStream.addEventListener("error", (event) => {
    const data = parseEvent(event);

    addActivity("error", {
      message: data.message || "Stream connection interrupted",
    });
    setStatus("Error", "error");
    submitButton.disabled = false;
    queryInput.disabled = false;
    closeActiveStream();
  });
}

exploreForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const query = queryInput.value.trim();

  if (!query) {
    return;
  }

  if (!activeSessionId) {
    sessionTitle.textContent = query;
  }

  startExploration(query);
});

newSessionButton.addEventListener("click", () => {
  closeActiveStream();
  activeSessionId = null;
  sessionTitle.textContent = "Untitled session";
  queryInput.value = "";
  clearWorkspace();
  setStatus("Idle");
  loadSessions();
});

queryInput.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    exploreForm.requestSubmit();
  }
});

loadSessions();
