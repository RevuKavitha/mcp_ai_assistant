"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { sendChat } from "@/lib/api";
import { Message } from "@/lib/types";

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const query = input.trim();
    if (!query || loading) {
      return;
    }

    setError(null);
    setLoading(true);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: query }]);

    try {
      const response = await sendChat(query, sessionId);
      const uniqueTools = Array.from(new Set(response.tools_used));
      setSessionId(response.session_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          toolsUsed: uniqueTools
        }
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unexpected error";
      setError(message);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I hit an error while processing your request. Please try again."
        }
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="premium-shell shine-border mx-auto flex h-[88vh] w-full max-w-5xl flex-col rounded-[28px]">
      <div className="flex items-center justify-between border-b border-slate-200/80 px-5 py-4 md:px-7">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[#102130] md:text-2xl">MCP AI Research Assistant</h1>
          <p className="text-sm text-slate-600">Tool-aware chat powered by Ollama + MCP orchestration</p>
        </div>
        <div className="soft-pulse hidden rounded-full border border-[#9fdcff] bg-[#eefaff] px-3 py-1 text-xs font-medium text-[#0284c7] md:block">
          Live Agent
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5 md:px-7">
        {messages.length === 0 ? (
          <div className="enter-up rounded-2xl border border-dashed border-[#9fdcff] bg-white/75 p-5 text-sm text-slate-700 backdrop-blur-sm">
            Ask anything. The assistant can choose tools like web search, documents, or notes DB.
          </div>
        ) : null}

        {messages.map((msg, idx) => (
          <div
            key={`${msg.role}-${idx}`}
            className={`enter-up flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            style={{ animationDelay: `${Math.min(idx * 45, 260)}ms` }}
          >
            <div
              className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-7 shadow-sm md:max-w-[82%] md:px-5 ${
                msg.role === "user"
                  ? "border border-[#0369a1] bg-gradient-to-br from-[#0ea5e9] to-[#0c4a6e] text-white"
                  : "border border-[#d8efff] bg-[#f5fbff]/95 text-[#102130]"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.role === "assistant" && msg.toolsUsed && msg.toolsUsed.length > 0 ? (
                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                  {Array.from(new Set(msg.toolsUsed)).map((tool) => (
                    <span
                      key={`${idx}-${tool}`}
                      className="rounded-full border border-[#b6e6ff] bg-gradient-to-r from-[#f0fbff] to-[#e6f7ff] px-2.5 py-1 text-[#0369a1]"
                    >
                      Used {tool}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        ))}

        {loading ? (
          <div className="enter-up inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/85 px-3 py-2 text-sm text-slate-600">
            <span className="typing" aria-hidden>
              <span />
              <span />
              <span />
            </span>
            Thinking and selecting tools...
          </div>
        ) : null}
        <div ref={endRef} />
      </div>

      <form onSubmit={onSubmit} className="border-t border-slate-200/80 bg-white/65 p-4 md:p-5">
        {error ? <p className="mb-2 text-sm text-red-600">{error}</p> : null}
        <div className="flex gap-2 md:gap-3">
          <input
            className="flex-1 rounded-xl border border-[#cfe9ff] bg-white/95 px-4 py-3 text-sm text-[#102130] outline-none transition focus:border-[#0ea5e9] focus:ring-2 focus:ring-[#0ea5e9]/20"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a research question..."
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-gradient-to-r from-[#0ea5e9] to-[#0284c7] px-5 py-2 text-sm font-medium text-white shadow-[0_8px_24px_rgba(14,165,233,0.34)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
