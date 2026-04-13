export type Role = "user" | "assistant";

export type Message = {
  role: Role;
  content: string;
  toolsUsed?: string[];
};

export type ChatApiResponse = {
  session_id: string;
  answer: string;
  tools_used: string[];
  trace: Array<Record<string, unknown>>;
};
