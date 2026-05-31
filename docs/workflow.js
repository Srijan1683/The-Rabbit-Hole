const shell = document.getElementById("diagramShell");
const nodeLayer = document.getElementById("nodes");
const svg = document.getElementById("connections");
const statusText = document.getElementById("statusText");
const traceList = document.getElementById("traceList");
const resetButton = document.getElementById("resetButton");

const nodes = [
  ["user", "User Prompt", "topic, follow-up, intent", 62, 52],
  ["frontend", "Frontend Chat UI", "sessions, prompt, live response", 265, 52],
  ["routes", "FastAPI Routes", "/explore, /explore/stream, /sessions", 468, 52, "core"],

  ["memory", "Session + Memory", "Postgres history + message storage", 92, 252, "data"],
  ["context", "Token Context", "budget, truncation, selected history", 295, 252, "core"],
  ["agent", "Agent Core", "prompt rules, planning, response shape", 498, 252, "core"],
  ["tools", "Tool System", "registry, cache, rate limit, APIs", 701, 252, "external"],

  ["model", "OpenRouter Model", "final synthesis + source-aware answer", 295, 522, "external"],
  ["stream", "SSE Streaming", "thinking, tool_call, content, done", 498, 522, "core"],
  ["storage", "Postgres Record", "sessions, messages, tools, cache", 701, 522, "data"],

  ["cacheHit", "Cache Hit", "skip duplicate API calls", 790, 136, "data"],
  ["handled", "Handled Error", "safe fallback, retry, or skip", 805, 382, "error"],
];

const edges = [
  ["user", "frontend"],
  ["frontend", "routes"],
  ["routes", "memory"],
  ["memory", "context"],
  ["context", "agent"],
  ["agent", "tools"],
  ["tools", "agent"],
  ["agent", "model"],
  ["model", "stream"],
  ["stream", "frontend"],
  ["model", "storage"],
  ["tools", "storage"],
  ["memory", "storage"],
  ["tools", "cacheHit"],
  ["cacheHit", "agent"],
  ["routes", "handled", "error"],
  ["tools", "handled", "error"],
  ["model", "handled", "error"],
  ["stream", "handled", "error"],
  ["handled", "agent", "error"],
];

const normalFlow = [
  ["user", "frontend", "user enters a topic or follow-up prompt"],
  ["frontend", "routes", "frontend sends request to FastAPI"],
  ["routes", "memory", "backend resolves session and stores user message"],
  ["memory", "context", "history is loaded and measured"],
  ["context", "agent", "agent receives only the safe context window"],
  ["agent", "tools", "agent selects relevant research tools"],
  ["tools", "agent", "structured sources return to the agent"],
  ["agent", "model", "agent asks the model to synthesize the response"],
  ["model", "stream", "response streams as SSE events"],
  ["stream", "frontend", "frontend renders the live answer"],
  ["model", "storage", "assistant response is stored"],
  ["tools", "storage", "tool calls, cache, and usage are logged"],
];

const cacheFlow = [
  ["agent", "tools", "agent requests supporting sources"],
  ["tools", "cacheHit", "cached response is found"],
  ["cacheHit", "agent", "cached tool result returns immediately"],
];

const errorFlow = [
  ["tools", "handled", "API failure or throttling becomes a safe tool result"],
  ["model", "handled", "model rate limit triggers retry/backoff"],
  ["stream", "handled", "client disconnect stops unnecessary work"],
  ["routes", "handled", "database startup failure is surfaced early"],
  ["handled", "agent", "agent continues with fallback context when possible"],
];

const phases = [normalFlow, cacheFlow, normalFlow, errorFlow];
const nodeMap = new Map();
const edgeMap = new Map();
let phaseIndex = 0;
let stepIndex = 0;

function createNodes() {
  nodes.forEach(([id, title, body, x, y, type = "process"], index) => {
    const node = document.createElement("div");
    node.className = `node ${type}`;
    node.id = `node-${id}`;
    node.dataset.code = `B${String(index + 1).padStart(2, "0")}`;
    node.style.left = `${x}px`;
    node.style.top = `${y}px`;
    node.innerHTML = `<strong>${title}</strong><span>${body}</span>`;
    nodeLayer.appendChild(node);
    nodeMap.set(id, { id, x, y, type, el: node });
  });
}

function point(id) {
  const node = nodeMap.get(id);
  const width = node.type === "error" ? 150 : 164;
  return { x: node.x + width / 2, y: node.y + 38 };
}

function makePath(from, to) {
  const a = point(from);
  const b = point(to);
  const dx = Math.abs(b.x - a.x);
  const dy = Math.abs(b.y - a.y);

  if (dy < 70) {
    const bend = Math.max(60, Math.min(150, dx * 0.45));
    return `M ${a.x} ${a.y} C ${a.x + bend} ${a.y}, ${b.x - bend} ${b.y}, ${b.x} ${b.y}`;
  }

  const midY = a.y + (b.y - a.y) / 2;
  return `M ${a.x} ${a.y} C ${a.x} ${midY}, ${b.x} ${midY}, ${b.x} ${b.y}`;
}

function createEdges() {
  edges.forEach(([from, to, kind]) => {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", makePath(from, to));
    path.setAttribute("class", `edge ${kind === "error" ? "error-edge" : ""}`);
    svg.appendChild(path);
    edgeMap.set(`${from}->${to}`, path);
  });
}

function fitBoard() {
  const padding = 28;
  const scaleX = (window.innerWidth - padding) / 1200;
  const scaleY = (window.innerHeight - padding) / 720;
  shell.style.transform = `translate(-50%, -50%) scale(${Math.min(scaleX, scaleY, 1)})`;
}

function resetActive() {
  document.querySelectorAll(".node.active").forEach((node) => node.classList.remove("active"));
  document.querySelectorAll(".edge.active").forEach((edge) => {
    edge.classList.remove("active");
    edge.classList.remove("error-active");
  });
}

function pushTrace(text) {
  const item = document.createElement("li");
  item.textContent = text;
  item.className = "active";
  traceList.prepend(item);
  [...traceList.children].slice(1).forEach((child) => child.classList.remove("active"));
  while (traceList.children.length > 6) {
    traceList.lastElementChild.remove();
  }
}

function activate(from, to, message) {
  resetActive();
  const edge = edgeMap.get(`${from}->${to}`);
  const isError = edge?.classList.contains("error-edge");

  nodeMap.get(from)?.el.classList.add("active", "done");
  nodeMap.get(to)?.el.classList.add("active");
  edge?.classList.add("active");
  if (isError) edge?.classList.add("error-active");

  statusText.textContent = message;
  pushTrace(message);
}

function tick() {
  const phase = phases[phaseIndex];
  const [from, to, message] = phase[stepIndex];
  activate(from, to, message);

  stepIndex += 1;
  if (stepIndex >= phase.length) {
    stepIndex = 0;
    phaseIndex = (phaseIndex + 1) % phases.length;
    if (phaseIndex === 0) {
      document.querySelectorAll(".node.done").forEach((node) => node.classList.remove("done"));
    }
  }
}

function resetSimulation() {
  phaseIndex = 0;
  stepIndex = 0;
  resetActive();
  traceList.innerHTML = "";
  document.querySelectorAll(".node.done").forEach((node) => node.classList.remove("done"));
  statusText.textContent = "simulation reset";
  tick();
}

createNodes();
createEdges();
fitBoard();
window.addEventListener("resize", fitBoard);
resetButton.addEventListener("click", resetSimulation);
tick();
setInterval(tick, 1100);
