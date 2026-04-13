from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from app.mcp.registry import ToolRegistry
from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class MCPAgent:
    """Structured MCP interaction loop:
    1) Ask model for next action (tool call or final answer)
    2) Execute tool if requested
    3) Feed tool result back into loop
    4) Return final answer
    """

    def __init__(self, llm: OllamaClient, registry: ToolRegistry, max_steps: int = 4) -> None:
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps

    async def run(self, query: str, memory: List[Dict[str, str]]) -> Dict[str, Any]:
        trace: List[Dict[str, Any]] = []
        tools_used: List[str] = []
        tool_context: List[Dict[str, Any]] = []
        seen_calls: set[str] = set()
        style_directive = self._extract_style_directive(query)

        # For rewrite/simplify prompts, answer directly from conversation context.
        if self._is_style_rewrite_request(query) and not self._needs_external_lookup(query):
            trace.append(
                {
                    "step": 0,
                    "decision": "style_rewrite_shortcut",
                    "style_directive": style_directive,
                }
            )
            answer = await self._generate_final_answer(
                query=query,
                memory=memory,
                tool_context=tool_context,
                style_directive=style_directive,
                prioritize_memory=True,
            )
            return {"answer": answer, "tools_used": [], "trace": trace}

        # For general knowledge questions, avoid unnecessary tool calls.
        if self._is_general_knowledge_query(query) and not self._needs_external_lookup(query):
            trace.append({"step": 0, "decision": "general_knowledge_shortcut"})
            answer = await self._generate_final_answer(
                query=query,
                memory=memory,
                tool_context=tool_context,
                style_directive=style_directive,
                prioritize_memory=False,
                allow_general_knowledge=True,
            )
            return {"answer": answer, "tools_used": [], "trace": trace}

        for step in range(1, self.max_steps + 1):
            planner_prompt = self._build_planner_prompt(query, memory, tool_context)
            decision = await self.llm.generate_json(planner_prompt)
            trace.append({"step": step, "planner_decision": decision})
            logger.info("Planner step %s decision: %s", step, decision)

            action = str(decision.get("action", "final")).lower()
            if action == "final":
                answer = str(decision.get("answer", "")).strip()
                if answer:
                    return {"answer": answer, "tools_used": list(dict.fromkeys(tools_used)), "trace": trace}

                # If model didn't provide final answer in planner JSON, ask directly.
                answer = await self._generate_final_answer(query, memory, tool_context)
                return {"answer": answer, "tools_used": list(dict.fromkeys(tools_used)), "trace": trace}

            if action != "tool":
                trace.append({"step": step, "warning": f"Unknown action '{action}', forcing final"})
                answer = await self._generate_final_answer(query, memory, tool_context)
                return {"answer": answer, "tools_used": list(dict.fromkeys(tools_used)), "trace": trace}

            tool_name = str(decision.get("tool", "")).strip()
            args = decision.get("args", {})
            if not tool_name:
                trace.append({"step": step, "warning": "Missing tool name"})
                answer = await self._generate_final_answer(query, memory, tool_context)
                return {"answer": answer, "tools_used": list(dict.fromkeys(tools_used)), "trace": trace}

            try:
                tool = self.registry.get(tool_name)
                safe_args = args if isinstance(args, dict) else {}
                call_sig = json.dumps({"tool": tool_name, "args": safe_args}, sort_keys=True)
                if call_sig in seen_calls:
                    trace.append(
                        {
                            "step": step,
                            "warning": "Repeated identical tool call detected; forcing final answer",
                            "tool": tool_name,
                            "args": safe_args,
                        }
                    )
                    answer = await self._generate_final_answer(query, memory, tool_context)
                    return {"answer": answer, "tools_used": list(dict.fromkeys(tools_used)), "trace": trace}

                seen_calls.add(call_sig)
                result = tool.handler(safe_args)
                tools_used.append(tool_name)
                tool_context.append({"tool": tool_name, "args": args, "result": result})
                trace.append({"step": step, "tool": tool_name, "result": result})
                logger.info("Executed tool %s with args=%s", tool_name, args)
            except Exception as exc:
                err = {"tool": tool_name, "error": str(exc)}
                tool_context.append(err)
                trace.append({"step": step, "tool_error": err})
                logger.exception("Tool execution failed")

        answer = await self._generate_final_answer(query, memory, tool_context)
        return {"answer": answer, "tools_used": list(dict.fromkeys(tools_used)), "trace": trace}

    def _build_planner_prompt(
        self, query: str, memory: List[Dict[str, str]], tool_context: List[Dict[str, Any]]
    ) -> str:
        tools_json = json.dumps(self.registry.list_for_prompt(), indent=2)
        memory_json = json.dumps(memory[-8:], indent=2)
        context_json = json.dumps(tool_context[-3:], indent=2)
        return f"""
You are an MCP planner for a research assistant.
Decide the NEXT action only:
- Use a tool when needed.
- Return final answer when enough information is available.
- Do not call the exact same tool with the exact same args more than once.
- Prefer one focused tool call, then finalize. Use multiple calls only if each adds new evidence.
- If user asks to save/find/list notes, use `notes_db`.
- If user asks for latest/current news, use `web_search` once, then finalize.
- If user asks about local files/PDFs, use `document_reader`.

Available tools (JSON):
{tools_json}

Conversation memory:
{memory_json}

Tool results so far:
{context_json}

User query: {query}

Return STRICT JSON with one of these shapes:
1) Tool call:
{{"action":"tool","tool":"<tool_name>","args":{{...}}}}
2) Final answer:
{{"action":"final","answer":"<final response>"}}
""".strip()

    async def _generate_final_answer(
        self,
        query: str,
        memory: List[Dict[str, str]],
        tool_context: List[Dict[str, Any]],
        style_directive: str = "",
        prioritize_memory: bool = False,
        allow_general_knowledge: bool = False,
    ) -> str:
        memory_json = json.dumps(memory[-8:], indent=2)
        context_json = json.dumps(tool_context, indent=2)
        memory_hint = (
            "This is a style/rewrite request. Prefer rewriting relevant conversation context directly."
            if prioritize_memory
            else "Use tool outputs when available, and conversation memory for continuity."
        )
        fallback_hint = (
            "If tool outputs are empty, answer directly using strong general knowledge without saying "
            "'no information available' or asking for external sources."
            if allow_general_knowledge
            else "If tool outputs are empty, be explicit about uncertainty."
        )
        style_hint = f"Follow this response style exactly: {style_directive}" if style_directive else ""
        prompt = f"""
You are a helpful AI research assistant.
Use the tool outputs as primary evidence and provide a concise, accurate answer.
If tool output is missing or uncertain, say so explicitly.
Do not invent dates, releases, or facts that are not present in the tool outputs.
If a claim is uncertain, explicitly label it as uncertain.
{memory_hint}
{fallback_hint}
{style_hint}

Conversation memory:
{memory_json}

Tool outputs:
{context_json}

User query: {query}
""".strip()
        return await self.llm.generate_text(prompt)

    def _is_style_rewrite_request(self, query: str) -> bool:
        q = query.lower().strip()
        style_tokens = [
            "explain in simple",
            "simple words",
            "simplify",
            "rewrite",
            "rephrase",
            "shorter",
            "make it short",
            "in bullet",
            "bullet points",
            "for kids",
            "eli5",
            "easy language",
            "one sentence",
            "single sentence",
            "two lines",
            "2 lines",
            "in simple terms",
            "make it simpler",
        ]
        if any(token in q for token in style_tokens):
            return True

        # Handle short follow-up formatting commands like "now concise", "only 1 sentence".
        short_followup_tokens = ["now", "only", "just", "concise", "brief", "short", "summarize"]
        if len(q.split()) <= 6 and any(token in q for token in short_followup_tokens):
            return True

        return False

    def _needs_external_lookup(self, query: str) -> bool:
        q = query.lower()
        lookup_tokens = [
            "latest",
            "current",
            "today",
            "news",
            "search the web",
            "look up",
            "find online",
            "according to documents",
            "read pdf",
            "read file",
            "store note",
            "save note",
            "search notes",
            "source",
            "citation",
            "reference",
            "compare latest",
            "real-time",
            "today's",
            "todays",
        ]
        return any(token in q for token in lookup_tokens)

    def _extract_style_directive(self, query: str) -> str:
        q = query.strip()
        q_lower = q.lower()
        directives: List[str] = []

        if "simple" in q_lower or "easy" in q_lower:
            directives.append("Use plain language at around middle-school reading level.")
        if "bullet" in q_lower:
            directives.append("Use short bullet points.")
        if "2 lines" in q_lower or "two lines" in q_lower:
            directives.append("Keep the answer to two lines.")
        if "short" in q_lower or "brief" in q_lower:
            directives.append("Keep it concise.")
        if "for kids" in q_lower or "eli5" in q_lower:
            directives.append("Explain as if speaking to a child.")
        if "formal" in q_lower:
            directives.append("Use a formal tone.")

        # Capture explicit format requests like: "in 3 points", "in one sentence".
        points_match = re.search(r"in\s+(\d+)\s+points", q_lower)
        if points_match:
            directives.append(f"Use exactly {points_match.group(1)} bullet points.")
        if "one sentence" in q_lower:
            directives.append("Use exactly one sentence.")

        return " ".join(directives).strip()

    def _is_general_knowledge_query(self, query: str) -> bool:
        q = query.lower().strip()
        general_patterns = [
            r"^what is [\w\s\-]+[?]?$",
            r"^who is [\w\s\-]+[?]?$",
            r"^define [\w\s\-]+[?]?$",
            r"^explain [\w\s\-]+[?]?$",
            r"^[\w\s\-]+ meaning[?]?$",
        ]
        if any(re.match(pattern, q) for pattern in general_patterns):
            # Keep tools for explicitly local/notes/doc intents.
            blocked_tokens = [
                "file",
                "pdf",
                "document",
                "notes",
                "database",
                "web",
                "search",
                "news",
                "latest",
            ]
            return not any(token in q for token in blocked_tokens)
        return False
