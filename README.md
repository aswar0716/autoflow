# AutoFlow

An AI-powered digest and workflow automation platform. Define topics in plain English, and AutoFlow's agent searches the web, synthesizes findings, and emails you a clean digest — automatically, on your schedule.

---

## What it does

**Digest Engine** — Subscribe to any topic ("AI funding news", "Python jobs in Sydney", "LLM research papers"). AutoFlow searches the web, deduplicates results, synthesizes them using Claude, and delivers a formatted HTML email digest on your schedule (daily, weekly, or custom).

**Task Runner** — Describe any business task in plain English. The agent reasons through it step by step, calls tools autonomously, and streams every action to your browser in real time.

**Workflow Builder** — Visually design reusable agent workflows using a drag-and-drop canvas. Connect tools as nodes, save the workflow, and run it on demand.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent | LangGraph (ReAct loop), LangChain, Claude claude-sonnet-4-6 (Anthropic) |
| Search | Tavily — AI-native web search |
| Backend | FastAPI, SQLAlchemy (async), SQLite, APScheduler |
| Streaming | Server-Sent Events (SSE) via FastAPI `StreamingResponse` |
| Email | SendGrid (HTML digest delivery) |
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS v3 |
| Canvas | React Flow (`@xyflow/react` v12) |

---

## Project Structure

```
autoflow/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── core.py               # LangGraph ReAct agent + streaming
│   │   │   └── tools/                # search, summarize, email tools
│   │   ├── api/
│   │   │   ├── routes.py             # /run, /run/stream, /tasks, /tools
│   │   │   ├── workflow_routes.py    # /workflows CRUD + /run
│   │   │   ├── topic_routes.py       # /topics CRUD + /run + digest history
│   │   │   └── digest_routes.py      # /digests/:id (shareable page)
│   │   ├── models/
│   │   │   ├── db.py                 # TaskRecord, WorkflowRecord, TopicRecord, DigestRecord
│   │   │   └── schemas.py            # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── digest.py             # search → synthesize → HTML → send pipeline
│   │   │   └── scheduler.py          # APScheduler: per-topic cron jobs
│   │   ├── database.py               # async engine, session factory, init_db
│   │   └── main.py                   # FastAPI app, CORS, lifespan
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app/
    │   ├── page.tsx                  # Task runner
    │   ├── topics/page.tsx           # Digest topic management + history
    │   ├── digest/[id]/page.tsx      # Shareable digest page
    │   └── workflows/page.tsx        # Drag-and-drop workflow builder
    ├── components/
    │   ├── StepFeed.tsx              # Real-time agent step display
    │   ├── TaskHistory.tsx           # Past task sidebar
    │   ├── ToolSelector.tsx          # Tool toggle buttons
    │   └── workflow/
    │       ├── WorkflowCanvas.tsx    # React Flow canvas
    │       └── ToolNode.tsx          # Custom tool node cards
    └── lib/
        └── api.ts                    # Typed API client
```

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys for: Anthropic, Tavily, SendGrid

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in your API keys in .env

uvicorn app.main:app --reload --port 8000
```

Interactive API docs at **http://localhost:8000/docs**

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

---

## Usage

### Digest Topics (`/topics`)
1. Click **+ New Topic**
2. Enter a topic name and search query (e.g. `latest AI startup funding Australia 2025`)
3. Set frequency: hourly / daily / weekly
4. Add recipient emails
5. Click **Create** — the scheduler registers it immediately
6. Click **▶ Run Now** to generate the first digest without waiting
7. View past digests and preview the HTML email inline
8. Every digest gets a shareable URL at `/digest/[id]`

### Task Runner (`/`)
1. Type any task in plain English
2. Optionally select which tools the agent can use
3. `Ctrl+Enter` to run — watch each reasoning step stream live
4. Past runs saved in the sidebar

### Workflow Builder (`/workflows`)
1. **+ New Workflow** → name it, select tools
2. Nodes appear on the canvas automatically — drag to reposition, draw edges to connect
3. **Create** to save → **▶ Run** to execute with a task

**Keyboard shortcuts:** `Ctrl+Enter` to run · `Esc` to clear

---

## How the Agent Works

AutoFlow uses the **ReAct** (Reason + Act) pattern via LangGraph:

```
Task received
    ↓
[Think] What do I need to do?
    ↓
[Act]   Call a tool → search / summarize / email
    ↓
[Observe] What did the tool return?
    ↓
[Think] Do I have enough to answer?
    ├── No  → call another tool
    └── Yes → return final answer (streamed to browser)
```

For digests, the pipeline is:
```
Topic query → Tavily search → Claude synthesis → HTML template → SendGrid delivery
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/tools` | List available tools |
| `POST` | `/api/v1/run` | Run task (blocking) |
| `POST` | `/api/v1/run/stream` | Run task with SSE streaming |
| `GET` | `/api/v1/tasks` | List past tasks |
| `GET` | `/api/v1/tasks/{id}` | Get single task |
| `GET` | `/api/v1/workflows` | List saved workflows |
| `POST` | `/api/v1/workflows` | Create workflow |
| `PATCH` | `/api/v1/workflows/{id}` | Update workflow |
| `DELETE` | `/api/v1/workflows/{id}` | Delete workflow |
| `POST` | `/api/v1/workflows/{id}/run` | Run workflow with SSE streaming |
| `GET` | `/api/v1/topics` | List digest topics |
| `POST` | `/api/v1/topics` | Create topic |
| `PATCH` | `/api/v1/topics/{id}` | Update topic |
| `DELETE` | `/api/v1/topics/{id}` | Delete topic |
| `POST` | `/api/v1/topics/{id}/run` | Trigger digest immediately |
| `GET` | `/api/v1/topics/{id}/digests` | List digests for a topic |
| `GET` | `/api/v1/digests/{id}` | Get single digest (for shareable page) |

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Where to get it |
|----------|----------------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) |
| `SENDGRID_API_KEY` | [app.sendgrid.com](https://app.sendgrid.com) |
| `SENDGRID_FROM_EMAIL` | A verified sender in your SendGrid account |
