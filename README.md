# The Rabbit Hole

The Rabbit Hole is a personal AI agent that explores any topic through connected sources instead of returning a flat search result. It combines a FastAPI backend, Postgres session memory, external research tools, token-aware context management, rate-limit handling, live SSE streaming, and a responsive browser UI.

Give it a topic like `Dyson Sphere`, `Quantum entanglement`, or `The history of jazz`, and it can pull together articles, books, papers, podcasts, and videos while keeping the conversation history available for follow-up questions.

---

## What It Does

The agent:

1. Reads the user query and conversation context.
2. Selects relevant tools instead of calling every source blindly.
3. Searches external APIs for articles, books, papers, podcasts, and videos.
4. Caches API responses to avoid redundant calls.
5. Tracks rate limits and handles throttled APIs safely.
6. Streams the answer to the frontend in real time.
7. Stores sessions, messages, tool calls, sources, and token usage in Postgres.

---

## Sources

| Source | Purpose |
| --- | --- |
| Wikipedia API | Article summaries and core topic context |
| Open Library API | Books, authors, subjects, and reading paths |
| arXiv API | Research papers, abstracts, authors, and categories |
| Podcast Index API | Podcast episodes and audio sources |
| YouTube Data API | Videos, lectures, explainers, and talks |

---

## Tech Stack

| Library / Tool | Purpose |
| --- | --- |
| `fastapi` | API server and route layer |
| `uvicorn` | ASGI server |
| `openai` | OpenRouter/OpenAI-compatible model calls |
| `asyncpg` | Async PostgreSQL access with raw SQL |
| `httpx` | Async external API requests |
| `sse-starlette` | Server-Sent Events for streaming |
| `tiktoken` | Token counting and context budgeting |
| `pydantic` | Request, response, and domain models |
| `python-dotenv` | Local environment variable loading |
| Docker Compose | Local Postgres database |
| Render | Backend and hosted Postgres deployment |
| Netlify | Static frontend deployment |

---

## Project Structure

```text
The Rabbit Hole/
├── app/
│   ├── main.py                         # FastAPI app, CORS, lifespan, routers
│   ├── agent/
│   │   ├── agent.py                    # Agent runner, tool selection, model calls
│   │   ├── prompts.py                  # System prompt and response rules
│   │   ├── rate_limiter.py             # In-memory rate-limit state and backoff
│   │   ├── registry.py                 # Tool registry and tool metadata
│   │   └── token_manager.py            # Token budgets and truncation helpers
│   ├── core/
│   │   ├── config.py                   # Environment-backed settings
│   │   ├── errors.py                   # Shared application exceptions
│   │   └── logging.py                  # Logging setup
│   ├── db/
│   │   ├── cache.py                    # Cached API response helpers
│   │   ├── history.py                  # Messages, tool calls, API usage SQL
│   │   ├── pool.py                     # asyncpg pool lifecycle
│   │   └── sessions.py                 # Session CRUD SQL
│   ├── models/
│   │   ├── conversation.py             # Messages and explore request/response models
│   │   ├── session.py                  # Session models
│   │   ├── token.py                    # Token and rate-limit models
│   │   └── tool.py                     # Source and tool result models
│   ├── routes/
│   │   ├── admin.py                    # Health, tools, rate-limit endpoints
│   │   ├── explore.py                  # Explore and SSE endpoints
│   │   └── sessions.py                 # Session/history endpoints
│   ├── services/
│   │   ├── exploration.py              # Non-streaming explore workflow
│   │   ├── memory.py                   # Token counting and history storage
│   │   └── streaming.py                # SSE explore workflow
│   └── tools/
│       ├── arxiv.py                    # arXiv wrapper
│       ├── open_library.py             # Open Library wrapper
│       ├── podcast_index.py            # Podcast Index wrapper
│       ├── wikipedia.py                # Wikipedia wrapper
│       └── youtube.py                  # YouTube wrapper
├── docs/
│   ├── workflow.md                     # Mermaid workflow diagrams
│   ├── workflow.html                   # Animated workflow webpage
│   ├── workflow.css
│   └── workflow.js
├── frontend/
│   ├── app.js                          # Chat UI, SSE client, sessions, source cards
│   ├── config.js                       # Frontend API base URL
│   ├── index.html                      # Frontend shell
│   └── styles.css                      # Responsive UI styling
├── migrations/
│   └── 001_initial_schema.sql          # Initial Postgres schema
├── scripts/
│   └── apply_migrations.py             # One-time migration runner
├── .env.example                        # Local environment template
├── docker-compose.yml                  # Local Postgres service
├── LICENSE                             # Restrictive project license
├── netlify.toml                        # Netlify frontend config
├── render.yaml                         # Render backend/Postgres blueprint
├── requirements.txt
└── README.md
```

---

## Database

The project uses raw SQL with `asyncpg`, no ORM.

| Table | Purpose |
| --- | --- |
| `sessions` | Conversation sessions and metadata |
| `conversation_history` | User and assistant messages with token counts |
| `tool_call_log` | Tool calls made during exploration |
| `api_usage` | External API status, latency, and rate-limit metadata |
| `cached_api_responses` | Cached external API responses with TTLs |

---

## API

### Sessions

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/sessions` | Create a session |
| `GET` | `/sessions` | List sessions |
| `GET` | `/sessions/{session_id}` | Get one session |
| `DELETE` | `/sessions/{session_id}` | Delete a session and its history |
| `GET` | `/sessions/{session_id}/history` | Get conversation history |
| `GET` | `/sessions/{session_id}/tool-calls` | Get stored tool calls |

### Explore

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/explore` | Run a non-streaming exploration |
| `GET` | `/explore/stream` | Stream a new exploration with SSE |
| `GET` | `/explore/{session_id}/stream` | Stream a follow-up exploration in an existing session |

### Admin

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `GET` | `/tools` | Available tool names |
| `GET` | `/rate-limits` | Current in-memory rate-limit status |

---

## SSE Events

| Event | Meaning |
| --- | --- |
| `thinking` | Exploration has started |
| `tool_call` | A tool is about to run |
| `tool_result` | A tool returned, skipped, or failed safely |
| `content` | A chunk of assistant response text |
| `sources` | Final source list |
| `done` | Stream completed |
| `error` | Stream failed |

---

## Frontend

The frontend is a static HTML/CSS/JS app. It supports:

- Live streaming responses
- Session list and session deletion
- Follow-up prompts in the same session
- Source cards ordered by query intent
- Responsive mobile layout with a sessions drawer
- A separate animated workflow page under `docs/workflow.html`

The frontend API target is configured in `frontend/config.js`.

---

## Deployment

The deployment files are included in the repo:

- `render.yaml` creates the backend service and Postgres database on Render.
- `netlify.toml` deploys the static frontend from `frontend/`.
- `scripts/apply_migrations.py` applies the initial schema to the deployed database.

Backend secrets are kept on Render. The frontend only stores the public backend URL in `frontend/config.js`.

---

## License

This project is all rights reserved. See `LICENSE`.
