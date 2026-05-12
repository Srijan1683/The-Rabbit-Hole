# 🐇 The Rabbit Hole


An AI agent that takes any topic and spirals into connected discoveries across multiple knowledge domains. Give it *"Dyson Sphere"* and it pulls the core concept from Wikipedia, finds related books on Open Library, surfaces research papers from arXiv, discovers podcast episodes, and finds YouTube talks — all while deciding which sources are relevant based on what the topic actually is.

This is not a search engine. It's a research companion that follows connections, maintains memory across a conversation, and gets smarter the deeper you go.

---

## What It Does

You type a topic. The agent:

1. Reasons about which knowledge domains are relevant
2. Searches across up to 5 external sources simultaneously
3. Follows connections it discovers (a Wikipedia article mentions Carl Sagan → it goes and finds his books)
4. Composes a structured response: Overview, Connected Concepts, Read, Listen, Watch
5. Remembers everything so you can say *"go deeper on that second point"* and it knows exactly what you mean

---

## The Five Sources

| Source | Domain | What It Provides |
|--------|--------|-----------------|
| Wikipedia API | Core knowledge | Article summaries, linked entities, structured facts |
| Open Library API | Books | Book search, author info, subjects, full metadata |
| arXiv API | Research papers | Paper search, abstracts, authors, categories |
| Podcast Index API | Audio content | Episode search across 4M+ podcasts |
| YouTube Data API | Video content | Video search, talks, documentaries, lectures |

The agent decides which ones matter. *"Quantum entanglement"* hits arXiv hard. *"History of jazz"* skips arXiv and goes heavy on YouTube and podcasts.

---

## Tech Stack

| Library | Purpose |
|---------|---------|
| `fastapi` | Web framework and API server |
| `uvicorn` | ASGI server |
| `openai` | OpenAI SDK — underlying LLM calls |
| `openai-agents` | OpenAI Agents SDK — tool calling and agent loop |
| `asyncpg` | Async PostgreSQL driver — raw SQL, no ORM |
| `httpx` | Async HTTP client for external API calls |
| `sse-starlette` | Server-Sent Events for real-time streaming |
| `tiktoken` | Token counting for context window management |
| `pydantic` | Data validation and models |
| `python-dotenv` | Environment variable management |

---

## Project Structure

```
rabbit-hole/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, startup, shutdown
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Environment variables, model names, API settings
│   │   ├── logging.py           # App logging configuration
│   │   └── errors.py            # Shared exceptions and error helpers
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py             # OpenAI Agents SDK setup and agent definition
│   │   ├── prompts.py           # System prompt and agent instructions
│   │   ├── registry.py          # Tool registration for the agent
│   │   ├── token_manager.py     # Token budget calculator, history truncation
│   │   └── rate_limiter.py      # Rate limit tracking, backoff strategies
│   ├── services/
│   │   ├── __init__.py
│   │   ├── exploration.py       # Main explore workflow: memory → agent → persistence
│   │   ├── streaming.py         # SSE event formatting and stream lifecycle
│   │   └── memory.py            # Session context loading and summarization decisions
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── wikipedia.py         # Wikipedia API wrapper
│   │   ├── open_library.py      # Open Library API wrapper
│   │   ├── arxiv.py             # arXiv API wrapper
│   │   ├── podcast_index.py     # Podcast Index API wrapper
│   │   └── youtube.py           # YouTube Data API wrapper
│   ├── db/
│   │   ├── __init__.py
│   │   ├── pool.py              # asyncpg connection pool setup
│   │   ├── sessions.py          # Session CRUD operations
│   │   ├── history.py           # Conversation history storage and retrieval
│   │   └── cache.py             # API response caching
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py           # Session Pydantic models
│   │   ├── conversation.py      # Message, ExploreRequest, ExploreResponse models
│   │   ├── tool.py              # Tool input/output and source metadata models
│   │   └── token.py             # TokenBudget, RateLimitStatus models
│   └── routes/
│       ├── __init__.py
│       ├── sessions.py          # Session and history endpoints
│       ├── explore.py           # Main explore endpoint and stream endpoint
│       └── admin.py             # Rate limit and diagnostics endpoints
├── migrations/
│   └── 001_initial_schema.sql   # Full database schema
├── docker-compose.yml           # Local Postgres service for development
├── .env.example                 # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Database Schema

Five tables. Raw SQL, no ORM.

```
sessions                  — conversation sessions with metadata
conversation_history      — all user and assistant messages with token counts
tool_call_log             — every external API call the agent made
api_usage                 — rate limit tracking and response time logging
cached_api_responses      — cached results to avoid redundant API calls
```

---

## API Endpoints

### Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sessions` | Create a new session |
| `GET` | `/sessions` | List all sessions (paginated) |
| `GET` | `/sessions/{session_id}` | Get session details |
| `DELETE` | `/sessions/{session_id}` | Delete session and all history |

### Explore
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/explore` | Send a query to the agent (streaming or non-streaming) |
| `GET` | `/explore/{session_id}/stream` | SSE stream of agent execution |

### History
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sessions/{session_id}/history` | Get conversation history |
| `GET` | `/sessions/{session_id}/tool-calls` | Get all tool calls for a session |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/rate-limits` | Current rate limit status for all external APIs |

---

## SSE Event Types

When streaming, the client receives real-time events as the agent works:

| Event | Meaning |
|-------|---------|
| `thinking` | Agent is reasoning about which tools to use |
| `tool_call` | Agent is calling an external API |
| `tool_result` | Tool returned results |
| `content` | Agent is generating response text |
| `sources` | Final list of all sources used |
| `done` | Response complete |
| `error` | Something went wrong |

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Srijan1683/rabbit-hole.git
cd rabbit-hole
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up Postgres

```bash
docker compose up -d
```

The migration in `migrations/001_initial_schema.sql` runs automatically the first time the Docker database is created.

Useful Docker commands:

```bash
docker compose ps
docker compose logs -f db
docker exec -it rabbithole-db psql -U postgres -d rabbithole
docker compose down
```

Inside `psql`, list tables with:

```sql
\dt
```

### 3. Configure environment

```bash
cp .env.example .env
# Fill in your API keys
```

Environment variables are documented in `.env.example`. The local `.env` file is ignored by Git and should never be committed.

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

---

## Implementation Phases

### Phase 1 — Postgres + Session Management
- Set up asyncpg connection pool on app startup
- Implement session CRUD with raw SQL
- Store and retrieve conversation history with token counts
- Auto-update `last_active_at` and `message_count` on every interaction

### Phase 2 — External API Tool Functions
- Build async wrapper for each of the 5 APIs
- Each wrapper handles errors, logs to `api_usage`, checks cache before calling
- Cache every response with TTLs (Wikipedia: 24h, YouTube: 6h, arXiv: 7d)
- Return structured Pydantic models from every tool

### Phase 3 — Agent Setup with OpenAI Agents SDK
- Define agent with a system prompt that instructs it to reason before calling tools
- Register each API wrapper as a named tool with descriptive docstrings
- Wire agent to `/explore`: load history → build context → run agent → store results
- Test with diverse queries to verify intelligent tool selection

### Phase 4 — Token Counting + Context Window Management
- Build token budget calculator per model (e.g., gpt-4o = 128K context)
- Allocate tokens: system prompt → current query → reserve for response → fill with history
- Implement history truncation: recency-first, always keep first message, summarize overflow
- Cap per-tool output token size to prevent tool results from flooding context

### Phase 5 — Rate Limit Management
- Track rate limit headers after every external API call
- Implement exponential backoff with jitter on 429 responses
- Proactively slow down when quota drops below 10%
- Expose `/rate-limits` endpoint showing live status for all APIs

### Phase 6 — SSE Streaming
- Stream agent execution in real-time using `sse-starlette`
- Emit typed events: `thinking`, `tool_call`, `tool_result`, `content`, `sources`, `done`
- Handle client disconnection mid-stream — stop agent, don't waste API calls
- Always persist full response to Postgres regardless of streaming

---

## Key Concepts

### How Tool Calling Works

The agent does not execute tools itself. The loop is:

```
1. Model receives: system prompt + history + available tools
2. Model outputs: "I want to call Wikipedia with query X"
3. Your code: executes the Wikipedia API call
4. Model receives: the results
5. Model decides: call another tool OR generate final response
6. Repeat until response is generated
```

Tool descriptions are prompts. How you describe each tool directly determines when the agent uses it.

### Why Context Window Management Matters

gpt-4o has 128K tokens. That sounds like a lot until a long session has 20 conversation messages, 5 tool results, and a detailed system prompt. Without token budgeting, the agent silently loses earlier context, hallucinates about past conversation, or errors out entirely. Every production agent needs this.

### Why Sessions Matter

A session isn't just chat history. It's the full research journey — what was asked, what tools were called, what was found, what connections were made. When you say *"go deeper on that"*, the agent needs the entire journey to know what *"that"* refers to.

---

## Stretch Goals

- **Exploration graph** — Mermaid diagram showing which topics branched into which discoveries
- **"Surprise me" mode** — Agent picks a random connected concept and explores it unprompted
- **Depth control** — `go shallow` (overview + top 3 links) vs `go deep` (follow every thread)
- **Export session** — Download the full exploration as a formatted markdown research report
- **Multi-user sessions** — Multiple users exploring the same topic together

---
