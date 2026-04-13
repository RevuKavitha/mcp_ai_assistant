import { ChatApiResponse } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function sendChat(query: string, sessionId?: string): Promise<ChatApiResponse> {
  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId })
  });

  if (!res.ok) {
    const fallback = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      throw new Error(body.detail ?? fallback);
    } catch {
      throw new Error(fallback);
    }
  }

  return (await res.json()) as ChatApiResponse;
}
