# MCP-Based AI Research Assistant

Full-stack AI Research Assistant with MCP-style tool-calling architecture.

## Tech Stack
- Frontend: Next.js (App Router) + Tailwind CSS
- Backend: FastAPI (Python)
- LLM: Ollama (`llama3`)
- MCP behavior: custom tool registry + structured tool-calling loop
- Tools: Web search, document reader, notes database

## Project Structure
```text
mcp_ai_assistant/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── mcp/
│   │   │   ├── registry.py
│   │   │   └── agent.py
│   │   ├── services/
│   │   │   ├── ollama_client.py
│   │   │   └── notes_store.py
│   │   └── tools/
│   │       ├── web_search.py
│   │       ├── document_tool.py
│   │       └── notes_tool.py
│   ├── docs/
│   │   └── sample_notes.md
│   ├── data/
│   ├── logs/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   └── chat-window.tsx
│   │   └── lib/
│   │       ├── api.ts
│   │       └── types.ts
│   ├── package.json
│   ├── tailwind.config.ts
│   └── .env.local.example
└── README.md
```

## MCP Flow (Tool-Calling Architecture)
1. User sends query to `POST /chat`
2. Backend asks Ollama planner for next action (`tool` or `final`)
3. If `tool`, backend executes tool from MCP registry
4. Tool result is added to loop context
5. Loop repeats until model returns `final` answer or max steps reached
6. Backend returns final answer + `tools_used` + execution trace

Main MCP orchestration code: `backend/app/mcp/agent.py`

## Implemented Tools
1. **Web Search Tool (`web_search`)**
- Scrapes DuckDuckGo HTML endpoint
- Returns top results + summary
- Falls back to mock result if network unavailable

2. **Document Reader Tool (`document_reader`)**
- Reads local `.txt`, `.md`, `.pdf`
- Extracts relevant snippets by keyword overlap

3. **Notes Database Tool (`notes_db`)**
- SQLite-backed notes storage
- Actions: `add`, `search`, `recent`

## Backend Setup (FastAPI)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Run Ollama locally:
```bash
ollama serve
ollama pull llama3
```

Start backend:
```bash
uvicorn app.main:app --reload --port 8000
```

## Frontend Setup (Next.js)
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Frontend URL: `http://localhost:3000`
Backend URL: `http://localhost:8000`

## API Contract
### `POST /chat`
Input:
```json
{
  "query": "Find latest trends in MCP",
  "session_id": "optional-session-id"
}
```

Output:
```json
{
  "session_id": "uuid",
  "answer": "...",
  "tools_used": ["web_search"],
  "trace": [{"step": 1, "planner_decision": {"action": "tool"}}]
}
```

## Extra Features Included
- Tool usage badges in UI (`Used web_search`, etc.)
- Backend chat memory by `session_id`
- Basic rotating file logging (`backend/logs/app.log`)
- Error handling on backend and frontend
- Scrollable chat history + loading indicator

## Notes
- The web tool may return mocked data if external internet is blocked.
- For document retrieval, place files under `backend/docs/` or pass a direct path through tool args.
# mcp_ai_assistant
