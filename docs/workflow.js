const board = document.getElementById("board");
const shell = document.getElementById("diagramShell");
const nodeLayer = document.getElementById("nodes");
const svg = document.getElementById("connections");
const statusText = document.getElementById("statusText");
const traceList = document.getElementById("traceList");

const nodes = [
  ["user", "User", 58, 42],
  ["frontend", "Frontend UI", 204, 42],
  ["prompt", "Prompt / follow-up", 350, 42],
  ["stream", "POST /explore/stream", 520, 18],
  ["rest", "POST /explore", 520, 82],
  ["explore", "Exploration service", 690, 50],
  ["session", "Existing session?", 850, 32, "decision"],
  ["create", "Create session title", 1000, 24],
  ["load", "Load session", 1000, 90],
  ["userMsg", "Store user message", 1160, 56, "store"],

  ["history", "Load history", 92, 235, "store"],
  ["tokens", "Token budget", 248, 235],
  ["select", "Select safe history", 404, 235],
  ["agent", "Agent pipeline", 560, 235],
  ["tools", "Choose tools", 716, 235],
  ["registry", "Tool registry", 872, 235],
  ["allowed", "API allowed?", 1030, 218, "decision"],
  ["cache", "Cached response?", 1190, 218, "decision"],
  ["cached", "Return cached result", 1340, 200, "store"],

  ["external", "Call external API", 80, 420, "external"],
  ["wiki", "Wikipedia", 240, 365, "external"],
  ["books", "Open Library", 240, 420, "external"],
  ["arxiv", "arXiv", 240, 475, "external"],
  ["youtube", "YouTube", 390, 392, "external"],
  ["podcast", "Podcast Index", 390, 455, "external"],
  ["saveCache", "Save cache + usage", 560, 420, "store"],
  ["toolResults", "Structured tool results", 720, 420],
  ["trimTools", "Trim large tool output", 884, 420],
  ["model", "OpenRouter model", 1048, 420, "external"],
  ["response", "Agent response", 1212, 420],

  ["assistantMsg", "Store assistant message", 72, 642, "store"],
  ["toolCalls", "Store tool calls", 240, 642, "store"],
  ["postgres", "Postgres", 408, 642, "store"],
  ["sse", "SSE events", 576, 642],
  ["sessions", "Session history + sources", 744, 642, "store"],

  ["skip", "Skip throttled tool", 1190, 330, "error"],
  ["backoff", "429 retry + jitter", 80, 548, "error"],
  ["malformed", "Malformed response -> safe result", 390, 548, "error"],
  ["modelRetry", "Model rate limit -> retry", 1048, 548, "error"],
  ["disconnect", "Client disconnect -> stop stream", 744, 724, "error"],
  ["dbError", "DB unavailable -> startup fails fast", 408, 724, "error"],
];

const edges = [
  ["user", "frontend"], ["frontend", "prompt"], ["prompt", "stream"], ["prompt", "rest"],
  ["stream", "explore"], ["rest", "explore"], ["explore", "session"],
  ["session", "create"], ["session", "load"], ["create", "userMsg"], ["load", "userMsg"],
  ["userMsg", "history"], ["history", "tokens"], ["tokens", "select"], ["select", "agent"],
  ["agent", "tools"], ["tools", "registry"], ["registry", "allowed"], ["allowed", "cache"],
  ["cache", "cached"], ["cache", "external"], ["external", "wiki"], ["external", "books"],
  ["external", "arxiv"], ["external", "youtube"], ["external", "podcast"],
  ["wiki", "saveCache"], ["books", "saveCache"], ["arxiv", "saveCache"], ["youtube", "saveCache"],
  ["podcast", "saveCache"], ["saveCache", "toolResults"], ["cached", "toolResults"],
  ["toolResults", "trimTools"], ["trimTools", "model"], ["model", "response"],
  ["response", "assistantMsg"], ["assistantMsg", "toolCalls"], ["toolCalls", "postgres"],
  ["response", "sse"], ["sse", "frontend"], ["postgres", "sessions"], ["sessions", "frontend"],
  ["allowed", "skip", "error"], ["skip", "toolResults", "error"], ["external", "backoff", "error"],
  ["backoff", "external", "error"], ["external", "malformed", "error"], ["malformed", "toolResults", "error"],
  ["model", "modelRetry", "error"], ["modelRetry", "model", "error"], ["sse", "disconnect", "error"],
  ["postgres", "dbError", "error"],
];

const timeline = [
  ["user", "frontend", "client enters query"],
  ["frontend", "prompt", "frontend builds request payload"],
  ["prompt", "stream", "streaming route selected for live output"],
  ["stream", "explore", "FastAPI hands off to exploration service"],
  ["explore", "session", "session is resolved"],
  ["session", "create", "new sessions get a compact title"],
  ["create", "userMsg", "user message is persisted"],
  ["userMsg", "history", "history is loaded from Postgres"],
  ["history", "tokens", "messages are token counted"],
  ["tokens", "select", "context window is protected"],
  ["select", "agent", "agent receives selected context"],
  ["agent", "tools", "model chooses relevant tool set"],
  ["tools", "registry", "tool registry maps names to functions"],
  ["registry", "allowed", "rate limiter checks API state"],
  ["allowed", "cache", "API is allowed"],
  ["cache", "external", "cache miss calls external API"],
  ["external", "wiki", "article lookup"],
  ["external", "arxiv", "paper lookup"],
  ["external", "youtube", "video lookup"],
  ["external", "podcast", "podcast lookup"],
  ["wiki", "saveCache", "responses are cached"],
  ["youtube", "saveCache", "usage is logged"],
  ["saveCache", "toolResults", "tool outputs become structured sources"],
  ["toolResults", "trimTools", "large tool output is trimmed"],
  ["trimTools", "model", "final prompt is sent to model"],
  ["model", "response", "agent generates answer"],
  ["response", "sse", "content chunks stream to browser"],
  ["response", "assistantMsg", "final answer is stored"],
  ["assistantMsg", "toolCalls", "tool calls are stored"],
  ["toolCalls", "postgres", "database becomes source of record"],
  ["postgres", "sessions", "session history can be reloaded"],
  ["sessions", "frontend", "frontend shows thread + sources"],
];

const handledErrors = [
  ["allowed", "skip", "rate limited API is skipped cleanly"],
  ["skip", "toolResults", "agent receives a safe skipped-tool result"],
  ["external", "backoff", "429 triggers exponential backoff with jitter"],
  ["backoff", "external", "tool retries after cooldown"],
  ["external", "malformed", "bad API payload becomes safe error output"],
  ["malformed", "toolResults", "failed tool does not crash exploration"],
  ["model", "modelRetry", "OpenAI/OpenRouter limit triggers retry"],
  ["modelRetry", "model", "model call resumes after delay"],
  ["sse", "disconnect", "client disconnect stops streaming work"],
  ["postgres", "dbError", "database startup error fails fast"],
];

const nodeMap = new Map();
const edgeMap = new Map();
let step = 0;
let errorStep = 0;
let cycle = 0;

function createNodes() {
  nodes.forEach(([id, label, x, y, type = "process"], index) => {
    const node = document.createElement("div");
    node.className = `node ${type}`;
    node.id = `node-${id}`;
    node.dataset.code = `N${String(index + 1).padStart(2, "0")}`;
    node.style.left = `${x}px`;
    node.style.top = `${y}px`;
    node.innerHTML = `<span>${label}</span>`;
    nodeLayer.appendChild(node);
    nodeMap.set(id, { id, label, x, y, type, el: node });
  });
}

function point(id) {
  const node = nodeMap.get(id);
  const width = node.type === "decision" ? 78 : 118;
  const height = node.type === "decision" ? 78 : 44;
  return { x: node.x + width / 2, y: node.y + height / 2 };
}

function makePath(from, to) {
  const a = point(from);
  const b = point(to);
  const dx = Math.abs(b.x - a.x);
  const bend = Math.max(45, Math.min(140, dx * 0.42));
  return `M ${a.x} ${a.y} C ${a.x + bend} ${a.y}, ${b.x - bend} ${b.y}, ${b.x} ${b.y}`;
}

function createEdges() {
  edges.forEach(([from, to, kind]) => {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", makePath(from, to));
    path.setAttribute("class", `edge ${kind === "error" ? "error-edge" : ""}`);
    path.setAttribute("id", `edge-${from}-${to}`);
    svg.appendChild(path);
    edgeMap.set(`${from}->${to}`, path);
  });
}

function fitBoard() {
  const padding = 28;
  const scaleX = (window.innerWidth - padding) / 1500;
  const scaleY = (window.innerHeight - padding) / 880;
  const scale = Math.min(scaleX, scaleY, 1);
  shell.style.transform = `translate(-50%, -50%) scale(${scale})`;
}

function resetActive() {
  document.querySelectorAll(".node.active").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".edge.active").forEach((el) => {
    el.classList.remove("active");
    el.classList.remove("error-active");
  });
}

function markDone(id) {
  const node = nodeMap.get(id)?.el;
  if (node) node.classList.add("done");
}

function pushTrace(text) {
  const item = document.createElement("li");
  item.textContent = text;
  item.className = "active";
  traceList.prepend(item);
  [...traceList.children].slice(1).forEach((child) => child.classList.remove("active"));
  while (traceList.children.length > 8) {
    traceList.lastElementChild.remove();
  }
}

function activate(from, to, message, isError = false) {
  resetActive();
  const fromNode = nodeMap.get(from)?.el;
  const toNode = nodeMap.get(to)?.el;
  const edge = edgeMap.get(`${from}->${to}`);

  fromNode?.classList.add("active");
  toNode?.classList.add("active");
  edge?.classList.add("active");
  if (isError) edge?.classList.add("error-active");

  markDone(from);
  statusText.textContent = message;
  pushTrace(message);
}

function tick() {
  const useErrorLane = cycle % 3 === 2;

  if (useErrorLane && errorStep < handledErrors.length) {
    const [from, to, message] = handledErrors[errorStep];
    activate(from, to, message, true);
    errorStep += 1;
    return;
  }

  if (useErrorLane && errorStep >= handledErrors.length) {
    errorStep = 0;
    cycle += 1;
  }

  const [from, to, message] = timeline[step];
  activate(from, to, message);
  step += 1;

  if (step >= timeline.length) {
    step = 0;
    cycle += 1;
    document.querySelectorAll(".node.done").forEach((el) => el.classList.remove("done"));
  }
}

createNodes();
createEdges();
fitBoard();
window.addEventListener("resize", fitBoard);
tick();
setInterval(tick, 950);
