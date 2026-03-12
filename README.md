# AutoFlow

An AI-powered workflow automation agent. Describe a task in plain English, watch the agent think and use tools in real time, and save reusable workflows you can run again with one click.

Built as a learning project across 4 phases — backend agent core → task history & streaming → Next.js UI → drag-and-drop workflow builder.

---

## Features

- **ReAct agent** — uses LangGraph to reason step-by-step and call tools autonomously
- **Real-time streaming** — Server-Sent Events push each agent step to the browser as it happens
- **Task history** — every run is saved to SQLite; browse and replay past tasks
- **Drag-and-drop workflow builder** — visually connect tools with React Flow, save named workflows, run them on demand

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent | LangGraph (ReAct loop), LangChain tools, Claude claude-sonnet-4-6 |
| Backend | FastAPI, SQLAlchemy (async), SQLite, Python 3.11 |
| Streaming | Server-Sent Events (SSE) via FastAPI `StreamingResponse` |
| Frontend | Next.js 14 (App Router), React 18, TypeScript |
| Styling | Tailwind CSS v3 |
| Workflow canvas | React Flow (`@xyflow/react` v12) |

---

## Project Structure

```
autoflow/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── core.py          # LangGraph ReAct agent + tool registry
│   │   │   └── tools.py         # search, summarize, email tools
│   │   ├── api/
│   │   │   ├── routes.py        # /run, /run/stream, /tasks, /tools
│   │   │   └── workflow_routes.py  # /workflows CRUD + /run
│   │   ├── models/
│   │   │   ├── db.py            # SQLAlchemy ORM (TaskRecord, WorkflowRecord)
│   │   │   └── schemas.py       # Pydantic request/response schemas
│   │   ├── database.py          # async engine, session factory, init_db
│   │   └── main.py              # FastAPI app, CORS, lifespan
│   └── requirements.txt
└── frontend/
    ├── app/
    │   ├── page.tsx             # Task runner (main page)
    │   └── workflows/
    │       └── page.tsx         # Drag-and-drop workflow builder
    ├── components/
    │   ├── StepFeed.tsx         # Real-time step display
    │   ├── TaskHistory.tsx      # Past runs sidebar
    │   ├── ToolSelector.tsx     # Tool toggle buttons
    │   └── workflow/
    │       ├── WorkflowCanvas.tsx  # React Flow canvas
    │       └── ToolNode.tsx        # Custom tool node component
    └── lib/
        └── api.ts               # All API calls (typed)
```

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- An Anthropic API key

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

uvicorn app.main:app --reload --port 8000
```

API docs available at **http://localhost:8000/docs**

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

---

## Usage

### Task Runner (`/`)
1. Type a task in plain English
2. Optionally select which tools to enable (leave empty = all tools)
3. Click **Run** or press `Ctrl+Enter`
4. Watch each agent step stream in real time
5. Browse past runs in the sidebar — click any to replay it

### Workflow Builder (`/workflows`)
1. Click **+ New Workflow**
2. Name it and select tools — nodes appear on the canvas automatically
3. Drag nodes to reposition; draw edges to show the intended flow
4. Click **Create** to save
5. Click **▶ Run**, enter a task, and the agent executes with that tool set

**Keyboard shortcuts:** `Ctrl+Enter` to run · `Esc` to clear

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

---

## How the Agent Works

AutoFlow uses the **ReAct** (Reason + Act) pattern via LangGraph:

```
User task
    ↓
[Think] — what do I need to do?
    ↓
[Act]   — call a tool (search / summarize / email)
    ↓
[Observe] — what did the tool return?
    ↓
[Think] — do I have enough to answer?
    ↓
[Final answer] → streamed to browser
```

Each step is streamed to the browser via SSE as it happens — no polling, no waiting for the full response.

---

## Build Phases

| Phase | Commit | What was built |
|-------|--------|---------------|
| 1 | `17aa538` | FastAPI backend + LangGraph ReAct agent + tools |
| 2 | `872260a` | SQLite task history + SSE streaming |
| 3 | `f6d59aa` | Next.js 14 frontend with real-time step feed |
| 4 | `593ac9c` | Drag-and-drop React Flow workflow builder |
