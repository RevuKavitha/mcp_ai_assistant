from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.mcp.agent import MCPAgent
from app.mcp.registry import MCPTool, ToolRegistry
from app.schemas import ChatRequest, ChatResponse
from app.services.ollama_client import OllamaClient
from app.tools.document_tool import document_tool
from app.tools.notes_tool import NotesTool
from app.tools.web_search import web_search_tool


# --- logging setup ---
logger = logging.getLogger("mcp_assistant")
logger.setLevel(logging.INFO)
if not logger.handlers:
    os.makedirs("logs", exist_ok=True)
    file_handler = RotatingFileHandler("logs/app.log", maxBytes=2_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(file_handler)
    logger.addHandler(logging.StreamHandler())


# --- app setup ---
app = FastAPI(title="MCP AI Research Assistant", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- shared services ---
ollama = OllamaClient(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    model=os.getenv("OLLAMA_MODEL", "llama3"),
)
registry = ToolRegistry()
notes_tool = NotesTool(db_path=os.getenv("NOTES_DB_PATH", "data/notes.db"))

# In-memory chat memory (session_id -> conversation list)
session_memory: Dict[str, List[Dict[str, str]]] = {}


def register_tools() -> None:
    registry.register(
        MCPTool(
            name="web_search",
            description="Search the web for current information and summarize top results.",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            handler=web_search_tool,
        )
    )
    registry.register(
        MCPTool(
            name="document_reader",
            description="Read local text/markdown/pdf documents and extract relevant snippets.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "path": {"type": "string"},
                    "docs_root": {"type": "string"},
                },
            },
            handler=document_tool,
        )
    )
    registry.register(
        MCPTool(
            name="notes_db",
            description="Store, search, or fetch recent personal notes.",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "search", "recent"]},
                    "content": {"type": "string"},
                    "query": {"type": "string"},
                    "tags": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
            handler=notes_tool,
        )
    )


register_tools()
agent = MCPAgent(llm=ollama, registry=registry)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or str(uuid4())
    memory = session_memory.setdefault(session_id, [])
    memory.append({"role": "user", "content": req.query})

    logger.info("Incoming query session=%s query=%s", session_id, req.query)

    try:
        result = await agent.run(query=req.query, memory=memory)
        answer = result["answer"]
        memory.append({"role": "assistant", "content": answer})

        return ChatResponse(
            session_id=session_id,
            answer=answer,
            tools_used=result.get("tools_used", []),
            trace=result.get("trace", []),
        )
    except Exception as exc:
        logger.exception("/chat failed")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {exc}") from exc
