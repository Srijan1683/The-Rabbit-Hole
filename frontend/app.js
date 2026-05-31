const API_BASE =
  localStorage.getItem("rabbitHoleApiBase") ||
  window.RABBIT_HOLE_CONFIG?.API_BASE ||
  "http://127.0.0.1:8000";

const sessionList = document.querySelector("#sessionList");
const sessionTitle = document.querySelector("#sessionTitle");
const connectionStatus = document.querySelector("#connectionStatus");
const responsePanel = document.querySelector("#responsePanel");
const emptyState = document.querySelector("#emptyState");
const chatThread = document.querySelector("#chatThread");
const sources = document.querySelector("#sources");
const activityList = document.querySelector("#activityList");
const exploreForm = document.querySelector("#exploreForm");
const queryInput = document.querySelector("#queryInput");
const submitButton = document.querySelector("#submitButton");
const newSessionButton = document.querySelector("#newSessionButton");

let activeSessionId = null;
let activeStream = null;
let responseText = "";
let currentQuery = "";
let renderQueued = false;
let streamFinished = false;
let activeAssistantMessage = null;

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

function decodeHtml(value) {
  const textarea = document.createElement("textarea");
  textarea.innerHTML = String(value || "");
  return textarea.value;
}

function buildPromptTitle(query) {
  let titleSeed = query.replace(/[?.!]+$/g, "").trim();
  const howToMatch = titleSeed.match(/\bhow to use\s+(.+?)(?:\s+on\s+.+)?$/i);
  const aboutMatch = titleSeed.match(/\b(?:about|on|related to)\s+(.+)$/i);

  if (howToMatch) {
    titleSeed = howToMatch[1];
  } else if (aboutMatch) {
    titleSeed = aboutMatch[1];
  }

  const cleaned = titleSeed
    .replace(/[?.!]+$/g, "")
    .replace(/\b(can you|could you|please|kindly|explain me|explain|tell me|give me|suggest|provide|show me|find|search|what is|who is|how to use|i want|i need|to explore|explore more|explore)\b/gi, " ")
    .replace(/\b(videos?|podcasts?|books?|articles?|papers?|lectures?|documentaries?|talks?|recommendations?|sources?|commands?|important|using|used|related to|on it|about it|and|with|for|me|some|more|in|it)\b/gi, " ")
    .replace(/\s+/g, " ")
    .trim();

  const fallback = query
    .replace(/[?.!]+$/g, "")
    .split(/\s+/)
    .slice(0, 6)
    .join(" ");

  const title = cleaned || fallback || "Untitled session";

  return title
    .split(" ")
    .slice(0, 8)
    .join(" ")
    .replace(/^./, (char) => char.toUpperCase());
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
  if (activeAssistantMessage) {
    activeAssistantMessage.classList.remove("thinking");
    activeAssistantMessage.innerHTML = renderMarkdown(responseText);
  }
  responsePanel.scrollTop = responsePanel.scrollHeight;
}

function scheduleAnswerRender() {
  if (renderQueued) {
    return;
  }

  renderQueued = true;

  requestAnimationFrame(() => {
    renderQueued = false;
    showAnswer();
  });
}

function clearWorkspace() {
  responseText = "";
  currentQuery = "";
  renderQueued = false;
  streamFinished = false;
  activeAssistantMessage = null;
  chatThread.innerHTML = "";
  sources.innerHTML = "";
  activityList.innerHTML = "";
  emptyState.style.display = "";
}

function appendMessage(role, content = "") {
  emptyState.style.display = "none";

  const message = document.createElement("article");
  message.className = `chat-message ${role}`;

  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : "The Rabbit Hole";

  const body = document.createElement("div");
  body.className = "message-body";

  if (role === "assistant") {
    body.innerHTML = renderMarkdown(content);
  } else {
    body.textContent = content;
  }

  message.appendChild(label);
  message.appendChild(body);
  chatThread.appendChild(message);
  responsePanel.scrollTop = responsePanel.scrollHeight;

  return body;
}

function showUserPrompt(query) {
  currentQuery = query;
  appendMessage("user", query);
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

function sourcePriority(source) {
  const query = currentQuery.toLowerCase();
  const provider = source.provider || "";
  const sourceType = source.source_type || "";

  if (/\b(video|videos|youtube|watch|lecture|documentary|talk)\b/.test(query)) {
    if (provider === "youtube" || sourceType === "video") return 0;
    if (provider === "wikipedia") return 2;
    return 1;
  }

  if (/\b(podcast|podcasts|listen|audio|episode)\b/.test(query)) {
    if (provider === "podcast_index" || sourceType === "podcast") return 0;
    if (provider === "youtube") return 2;
    return 1;
  }

  if (/\b(book|books|read|author|novel|biography)\b/.test(query)) {
    if (provider === "open_library" || sourceType === "book") return 0;
    if (provider === "arxiv" || sourceType === "paper") return 1;
    return 2;
  }

  return 1;
}

function renderSources(sourceList) {
  sources.innerHTML = "";

  const orderedSources = [...(sourceList || [])].sort(
    (a, b) => sourcePriority(a) - sourcePriority(b),
  );

  for (const source of orderedSources) {
    const card = document.createElement("article");
    card.className = "source-card";

    const title = escapeHtml(decodeHtml(source.title || "Untitled source"));
    const provider = escapeHtml(decodeHtml(source.provider || "source"));
    const sourceType = escapeHtml(decodeHtml(source.source_type || "web"));
    const summary = source.summary ? escapeHtml(decodeHtml(source.summary)) : "";
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
    const displayTitle = buildPromptTitle(session.title || "Untitled session");
    openButton.innerHTML = `
      <div class="session-name">${escapeHtml(displayTitle)}</div>
      <div class="session-meta">${session.message_count || 0} messages</div>
    `;

    openButton.addEventListener("click", () => {
      activeSessionId = session.session_id;
      sessionTitle.textContent = displayTitle;
      clearWorkspace();
      loadHistory(session.session_id);
      renderSessions(sessions);
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "session-delete";
    deleteButton.title = "Delete session";
    deleteButton.setAttribute("aria-label", `Delete ${session.title || "session"}`);
    deleteButton.innerHTML = '<span class="trash-icon" aria-hidden="true"></span>';

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
    chatThread.innerHTML = "";
    emptyState.style.display = messages.length ? "none" : "";

    for (const message of messages) {
      if (message.role === "user") {
        appendMessage("user", message.content);
        currentQuery = message.content;
      }

      if (message.role === "assistant") {
        appendMessage("assistant", message.content);
      }
    }
  } catch {
    addActivity("error", { message: "History unavailable" });
  }
}

function startExploration(query) {
  closeActiveStream();
  showUserPrompt(query);
  activeAssistantMessage = appendMessage("assistant", "");
  activeAssistantMessage.classList.add("thinking");
  activeAssistantMessage.innerHTML = `
    <span class="thinking-indicator">
      <span>Thinking</span>
      <span class="thinking-dots" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </span>
    </span>
  `;
  responseText = "";
  sources.innerHTML = "";
  activityList.innerHTML = "";
  renderQueued = false;
  streamFinished = false;
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
    scheduleAnswerRender();
  });

  activeStream.addEventListener("sources", (event) => {
    const data = parseEvent(event);
    renderSources(data.sources || []);
  });

  activeStream.addEventListener("done", (event) => {
    const data = parseEvent(event);
    streamFinished = true;

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

    if (!event.data && !streamFinished) {
      addActivity("error", {
        message: "Stream connection interrupted before completion",
      });
      responseText += "\n\nThe stream was interrupted before the response finished. Please retry the same prompt.";
      scheduleAnswerRender();
      setStatus("Interrupted", "error");
      submitButton.disabled = false;
      queryInput.disabled = false;
      closeActiveStream();
      return;
    }

    addActivity("error", {
      message: data.message || "Stream connection interrupted",
    });
    responseText += `\n\n${data.message || "The stream was interrupted before the response finished."}`;
    scheduleAnswerRender();
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
    sessionTitle.textContent = buildPromptTitle(query);
  }

  queryInput.value = "";
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
