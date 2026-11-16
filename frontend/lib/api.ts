// Centralize the backend URL so pages don't need to hardcode it.
export const API_BASE =
// One helper for chat, memory, and profile calls.
// kept the token header and error text here so each page does not repeat them.
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type MemoryItem = {
  id: string;
  category: string;
  content: string;
  source: string;
  confidence: number;
  status: "pending" | "active" | "archived";
  keywords: string[];
};

export type Conversation = {
  id: string;
  title: string;
  summary?: string | null;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

// This keeps the demo simple, but is not a production session strategy.
// A deployed version would need stronger auth/session and CSRF considerations.
export function token(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("pa_token");
}

export function setToken(value: string) {
  sessionStorage.setItem("pa_token", value);
}

export function clearToken() {
  sessionStorage.removeItem("pa_token");
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  // Attach the same access token to all authenticated API requests.
  const accessToken = token();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {}
    throw new Error(message);
  }

  // DELETE endpoints may return 204 with no response body; don't parse that as JSON.
  if (response.status === 204) return undefined as T;
  return response.json();
}
