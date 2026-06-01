const shell = document.getElementById("diagramShell");
const nodeLayer = document.getElementById("nodes");
const svg = document.getElementById("connections");
const statusText = document.getElementById("statusText");
const traceList = document.getElementById("traceList");
const resetButton = document.getElementById("resetButton");

const nodes = [
  ["ui", "User + Frontend", "prompt, sessions, mobile UI, live output", 80, 76],
  ["api", "FastAPI Gateway", "routes, CORS, SSE entrypoints", 320, 76, "core"],
  ["memory", "Session Memory", "history, token counts, Postgres state", 560, 76, "data"],

  ["agent", "Agent Core", "tool choice, prompts, context budget", 190, 306, "core"],
  ["tools", "Tool Layer", "cache, rate limits, external APIs", 460, 306, "external"],
  ["model", "OpenRouter Model", "source-aware synthesis", 730, 306, "external"],

  ["output", "Stream + Storage", "SSE response, sources, saved records", 430, 532, "data"],
  ["handled", "Handled Failure", "retry, skip, fallback", 820, 136, "error"],
];

const edges = [
  ["ui", "api"],
  ["api", "memory"],
  ["memory", "agent"],
  ["agent", "tools"],
  ["tools", "agent"],
  ["agent", "model"],
  ["model", "output"],
  ["output", "ui"],
  ["memory", "output"],
  ["tools", "output"],
  ["api", "handled", "error"],
  ["tools", "handled", "error"],
  ["model", "handled", "error"],
  ["output", "handled", "error"],
  ["handled", "agent", "error"],
];

const normalFlow = [
  ["ui", "api", "user submits a topic from the frontend"],
  ["api", "memory", "backend resolves session and loads history"],
  ["memory", "agent", "agent receives selected context and token budget"],
  ["agent", "tools", "agent chooses relevant research tools"],
  ["tools", "agent", "structured sources return to the agent"],
  ["agent", "model", "model synthesizes the final answer"],
  ["model", "output", "answer, sources, and metadata are finalized"],
  ["output", "ui", "SSE stream updates the frontend"],
  ["memory", "output", "session history is kept as durable state"],
  ["tools", "output", "tool calls, cache, and usage are stored"],
];

const cacheFlow = [
  ["agent", "tools", "agent requests supporting sources"],
  ["tools", "agent", "cached tool results return without another API call"],
];

const errorFlow = [
  ["tools", "handled", "API failure or throttling becomes a safe tool result"],
  ["model", "handled", "model rate limit triggers retry/backoff"],
  ["output", "handled", "client disconnect stops unnecessary work"],
  ["api", "handled", "database or request failure is surfaced early"],
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
  const width = node.type === "error" ? 156 : 190;
  return { x: node.x + width / 2, y: node.y + 42 };
}

function makePath(from, to) {
  const a = point(from);
  const b = point(to);
  const dx = Math.abs(b.x - a.x);
  const dy = Math.abs(b.y - a.y);

  if (from === "model" && to === "handled") {
    return `M ${a.x} ${a.y} C ${a.x + 90} ${a.y - 110}, ${b.x + 90} ${b.y - 105}, ${b.x} ${b.y}`;
  }

  if (from === "handled" && to === "agent") {
    return `M ${a.x} ${a.y} C ${a.x - 155} ${a.y + 130}, ${b.x + 155} ${b.y + 130}, ${b.x} ${b.y}`;
  }

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
