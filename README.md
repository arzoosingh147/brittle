# Brittle — AI Pull Request & Codebase Reviewer

Brittle is a high-performance, production-ready AI Pull Request and Codebase Reviewer. It indexes GitHub repositories into a `pgvector` PostgreSQL store for cross-file context, listens to GitHub Pull Request webhooks, executes a parallel multi-agent AI code review pipeline using **LangGraph** and **Google Gemini** (with **Groq** fallback), posts line-specific inline review comments with code suggestions directly to GitHub PR diffs, and provides a SaaS dashboard to manage repositories, custom rules, and review metrics.

---

## 🌟 Key Highlights & Engineering Standards

- **Parallel Specialist Review Agents:** Uses LangGraph state graphs with fan-out edges to run `SecurityAgent`, `PerformanceAgent`, and `CodeQualityAgent` concurrently (`asyncio.gather`), reducing review latency from ~45s to ~12s.
- **pgvector HNSW Code Search:** Indexes repository AST chunks using `gemini-embedding-001` (768 dimensions) with PostgreSQL 16 `HNSW` cosine vector indexes (`<=>`), enabling fast cross-file context retrieval.
- **Exact Line-Specific Diff Mapping:** Parses unified git diffs, extracts line numbers and hunk contexts, and automatically maps suggestions to valid GitHub comment lines.
- **Smart Filtering & Token Budgeting:** Filters out lockfiles (`package-lock.json`, `poetry.lock`, etc.), minified bundles, images, and binaries before sending context to LLMs.
- **Zero-Drop Idempotency & Concurrency:** Utilizes Redis locks and deterministic idempotency keys (`repo_id:pr_number:head_sha`) to guarantee duplicate webhooks never trigger duplicate LLM reviews.
- **Hybrid Queue Dispatcher:** Seamlessly dispatches background tasks via **Celery + Redis** in distributed environments, or falls back to asynchronous **FastAPI BackgroundTasks** for lightweight, $0 deployments.
- **Modern Next.js 15+ Frontend:** Dark-themed UI with Tailwind CSS, TypeScript strict mode, responsive Metrics Grid, inline diff review comments, and repository rules editor.

---

## 🏗️ Architecture Overview

```
                      +-----------------------------+
                      |   GitHub Pull Request Event |
                      +--------------+--------------+
                                     |
                                     v [HMAC SHA-256 Webhook]
                      +-----------------------------+
                      |   FastAPI /api/v1/webhooks  |
                      +--------------+--------------+
                                     |
                        [Idempotency & Lock Check]
                                     |
                                     v
                      +-----------------------------+
                      |       QueueDispatcher       |
                      |   (Celery / BackgroundTask) |
                      +--------------+--------------+
                                     |
                       +-------------+-------------+
                       |                           |
                       v                           v
             [DiffParserService]         [Vector Search pgvector]
             • Filter lockfiles/min      • Top-K semantic context
             • Map diff lines & hunks    • HNSW cosine similarity
                       |                           |
                       +-------------+-------------+
                                     |
                                     v
                 +---------------------------------------+
                 |    LangGraph Multi-Agent Pipeline     |
                 +-------------------+-------------------+
                                     |
                 +-------------------+-------------------+
                 |                   |                   |
                 v                   v                   v
        [Security Agent]     [Performance Agent]  [Quality Agent]
       (OWASP, injections)    (N+1, memory, async)  (Clean code, rules)
                 |                   |                   |
                 +-------------------+-------------------+
                                     |
                                     v
                             [Aggregator Node]
                         • Deduplicate inline issues
                         • Calculate 1-10 PR Risk Score
                         • Synthesize Executive Summary
                                     |
                                     v
                       +-------------+-------------+
                       |                           |
                       v                           v
         [GitHub PR Review API]           [PostgreSQL & Redis]
      • Line comments with suggestions  • Persist review & comments
      • APPROVE / REQUEST_CHANGES       • Mark idempotency key
```

---

## 📂 Project Structure

```text
/Brittle
├── /frontend
│   ├── /src/app
│   │   ├── /(auth)/login/page.tsx             # GitHub OAuth Sign-in
│   │   ├── /(dashboard)/dashboard/page.tsx    # MetricsGrid & PR Reviews feed
│   │   ├── /(dashboard)/repos/page.tsx        # Repositories & Rules Editor
│   │   ├── /(dashboard)/reviews/[id]/page.tsx # Detailed Review & Inline Comments
│   │   ├── /api/auth/[...nextauth]/route.ts   # Auth.js Route Handler
│   │   └── layout.tsx                         # Header, Navigation, Status Badge
│   ├── /src/components
│   │   ├── /ui/                               # Button, Card, Badge primitives
│   │   ├── /repos/                            # RepoCard, RepoRulesForm, IndexingBadge
│   │   └── /reviews/                          # ReviewSummary, InlineCommentCard, MetricsGrid
│   ├── /src/lib
│   │   ├── auth.ts                            # NextAuth v5 configuration
│   │   └── api-client.ts                      # Strict typed fetch wrapper
│   ├── /src/utils/                            # Date, risk scores & severity helpers
│   └── /src/types/                            # Strict TypeScript interfaces
├── /backend
│   ├── /app
│   │   ├── /api/v1/
│   │   │   ├── webhooks.py                    # GitHub webhook endpoint
│   │   │   ├── repos.py                       # Repository management & re-indexing
│   │   │   └── reviews.py                     # Review history & metrics endpoints
│   │   ├── /core/
│   │   │   ├── config.py                      # Pydantic BaseSettings configuration
│   │   │   ├── security.py                    # HMAC verification & RS256 JWT
│   │   │   ├── redis.py                       # Async Redis client, locks & caching
│   │   │   └── llm.py                         # Model factory (Gemini + Groq fallback)
│   │   ├── /db/
│   │   │   ├── session.py                     # Async SQLAlchemy engine & sessionmaker
│   │   │   ├── models.py                      # Declarative models with pgvector Vector(768)
│   │   │   └── /migrations/                   # Alembic setup & migration scripts
│   │   ├── /repositories/
│   │   │   ├── repo_repository.py             # Installations & Repositories queries
│   │   │   ├── vector_repository.py           # Batched upserts & HNSW search
│   │   │   └── review_repository.py           # Reviews & Inline Comments storage
│   │   ├── /services/
│   │   │   ├── github_service.py              # GitHub App JWT & Review API Client
│   │   │   ├── diff_parser.py                 # Git unified diff parser & line mapper
│   │   │   ├── ast_chunker.py                 # Structural AST chunking in worker thread
│   │   │   └── indexer_service.py             # Codebase vector indexing orchestrator
│   │   ├── /agents/
│   │   │   ├── state.py                       # TypedDict LangGraph state
│   │   │   ├── schemas.py                     # Strict Pydantic structured output models
│   │   │   ├── prompts.py                     # Versioned specialist system prompts
│   │   │   ├── nodes.py                       # Agent execution nodes
│   │   │   └── graph.py                       # Compiled LangGraph StateGraph
│   │   ├── /workers/
│   │   │   ├── celery_app.py                  # Celery application
│   │   │   └── tasks.py                       # Background tasks & QueueDispatcher
│   │   └── main.py                            # FastAPI app, lifespan, CORS & routers
│   ├── /tests/
│   │   └── run_tests.py                       # Test suite
│   ├── alembic.ini                            # Database migration configuration
│   └── requirements.txt                       # Python dependencies
└── docker-compose.yml                         # PostgreSQL 16 (pgvector) + Redis 7
```

---

## 🚀 Quickstart & Local Development

### 1. Start Database & Redis via Docker
```bash
docker compose up -d
```
This spins up:
- **PostgreSQL 16** with `pgvector/pgvector:pg16` on `localhost:5432`
- **Redis 7** on `localhost:6379`

### 2. Configure Backend Environment
Copy `.env.example` in `backend/`:
```bash
cd backend
cp .env.example .env
```
Key configuration variables:
```ini
DATABASE_URL="postgresql+asyncpg://brittle:brittle_secret@localhost:5432/brittle_db"
REDIS_URL="redis://localhost:6379/0"
USE_CELERY=false

# Google Gemini / Groq API Keys
GEMINI_API_KEY="your-gemini-api-key"
GROQ_API_KEY="your-groq-api-key"

# GitHub App Integration
GITHUB_APP_ID="123456"
GITHUB_WEBHOOK_SECRET="development-webhook-secret"
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
```

### 3. Run Backend Server
```bash
cd backend
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend will start at: `http://localhost:8000` (Swagger UI at `/docs`).

### 4. Run Frontend Next.js App
```bash
cd frontend
npm install
npm run dev
```
Frontend will be live at `http://localhost:3000`.

---

## 🧪 Running Automated Tests
```bash
python3 backend/tests/run_tests.py -v
```

---

## 🛡️ GitHub App Webhook Setup

1. Create a GitHub App in your organization / user account.
2. Set **Webhook URL** to: `https://your-domain.com/api/v1/webhooks/github`.
3. Provide a secure random secret in **Webhook secret**, matching `GITHUB_WEBHOOK_SECRET`.
4. Subscribe to events:
   - `Pull request` (Opened, Synchronize, Reopened)
   - `Installation` and `Installation repositories`
5. Grant permissions:
   - `Pull requests`: Read & Write
   - `Repository contents`: Read-only
6. Install the App on your repositories!
