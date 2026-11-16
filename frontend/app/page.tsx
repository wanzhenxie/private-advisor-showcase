"use client";

import { useEffect, useState } from "react";
import {
  api, clearToken, Conversation, MemoryItem, Message, setToken, token
} from "../lib/api";

type Tab = "chat" | "memory" | "profile" | "usage";

export default function HomePage() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [tab, setTab] = useState<Tab>("chat");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const [displayName, setDisplayName] = useState("");
  const [timezone, setTimezone] = useState("America/New_York");
  const [locale, setLocale] = useState("zh-CN");
  const [preferenceText, setPreferenceText] = useState("{}");

  const [usage, setUsage] = useState({ input_tokens: 0, output_tokens: 0, calls: 0 });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // The login token is stored in sessionStorage for this local MVP.
  // Read it after the component mounts, not during server-side rendering.
  useEffect(() => { setLoggedIn(Boolean(token())); }, []);
  useEffect(() => { if (loggedIn) void refreshCore(); }, [loggedIn]);

  async function refreshCore() {
    try {
      setError("");
      // Conversations and memories are independent requests, so load them together.
      const [cs, ms] = await Promise.all([
        api<Conversation[]>("/api/conversations"),
        api<MemoryItem[]>("/api/memories")
      ]);
      setConversations(cs);
      setMemories(ms);
      // TODO: Restore the last selected conversation after a page refresh.
      // For now we open the first one returned by the API.
      if (cs.length > 0 && !conversationId) {
        setConversationId(cs[0].id);
        await loadMessages(cs[0].id);
      }
    } catch (e) { setError((e as Error).message); }
  }

  async function submitAuth() {
    setBusy(true); setError("");
    try {
      const path = mode === "register" ? "/api/auth/register" : "/api/auth/login";
      const result = await api<{ access_token: string }>(path, {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      setToken(result.access_token);
      setLoggedIn(true);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  function logout() {
    clearToken();
    setLoggedIn(false);
    setConversations([]); setMessages([]); setMemories([]);
    setConversationId(null);
  }

  async function createConversation() {
    try {
      const c = await api<Conversation>("/api/conversations", {
        method: "POST", body: JSON.stringify({ title: "新对话" })
      });
      setConversations(old => [c, ...old]);
      setConversationId(c.id); setMessages([]); setTab("chat");
    } catch (e) { setError((e as Error).message); }
  }

  async function loadMessages(id: string) {
    try {
      setConversationId(id); setError("");
      setMessages(await api<Message[]>(`/api/conversations/${id}/messages`));
      setTab("chat");
    } catch (e) { setError((e as Error).message); }
  }

  async function sendMessage() {
    const content = draft.trim();
    if (!content || busy) return;
    let id = conversationId;

    try {
      if (!id) {
        const c = await api<Conversation>("/api/conversations", {
          method: "POST", body: JSON.stringify({ title: "新对话" })
        });
        setConversations(old => [c, ...old]);
        id = c.id; setConversationId(id);
      }

      setDraft(""); setBusy(true); setError("");
      // Show the user's message immediately instead of waiting for the model.
      // The temporary ID gives this optimistic entry a stable React key.
      // Reloading a conversation later replaces the temporary view with saved messages.
      setMessages(old => [...old, {
        id: `temp-${Date.now()}`, role: "user",
        content, created_at: new Date().toISOString()
      }]);

      const reply = await api<{
        assistant_message: Message;
        memory_candidates: MemoryItem[];
      }>(`/api/conversations/${id}/messages`, {
        method: "POST", body: JSON.stringify({ content })
      });

      setMessages(old => [...old, reply.assistant_message]);

      // Memory suggestions are NOT active yet. They must be confirmed by the user.
      if (reply.memory_candidates.length) {
        setMemories(old => [...reply.memory_candidates, ...old]);
        setNotice(`发现 ${reply.memory_candidates.length} 条候选长期记忆，请到“记忆”页面确认。`);
      }

      setConversations(await api<Conversation[]>("/api/conversations"));
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  // A successful API call changes the database status from pending to active.
  // The local list is updated too, so the user sees the result without refreshing.
  async function confirmMemory(id: string) {
    try {
      const updated = await api<MemoryItem>(`/api/memories/${id}/confirm`, { method: "POST" });
      setMemories(old => old.map(m => m.id === id ? updated : m));
      // TODO: Clear the old "new memory candidates" notice when none remain pending.
    } catch (e) { setError((e as Error).message); }
  }

  async function deleteMemory(id: string) {
    if (!confirm("确定删除这条记忆吗？")) return;
    try {
      await api<void>(`/api/memories/${id}`, { method: "DELETE" });
      setMemories(old => old.filter(m => m.id !== id));
    } catch (e) { setError((e as Error).message); }
  }

  async function loadProfile() {
    try {
      const p = await api<{
        display_name?: string | null;
        timezone: string;
        locale: string;
        advisor_preferences: Record<string, unknown>;
      }>("/api/profile");
      setDisplayName(p.display_name || "");
      setTimezone(p.timezone); setLocale(p.locale);
      setPreferenceText(JSON.stringify(p.advisor_preferences || {}, null, 2));
      setTab("profile");
    } catch (e) { setError((e as Error).message); }
  }

  async function saveProfile() {
    try {
      setError(""); setNotice("");
      const prefs = preferenceText.trim() ? JSON.parse(preferenceText) : {};
      await api("/api/profile", {
        method: "PUT",
        body: JSON.stringify({
          display_name: displayName || null,
          timezone, locale, advisor_preferences: prefs
        })
      });
      setNotice("档案已保存。");
    } catch (e) {
      setError(e instanceof SyntaxError ? "智囊偏好必须是合法 JSON" : (e as Error).message);
    }
  }

  async function loadUsage() {
    try {
      setUsage(await api<typeof usage>("/api/usage"));
      setTab("usage");
    } catch (e) { setError((e as Error).message); }
  }

  if (!loggedIn) {
    return (
      <main className="main">
        <div className="card auth">
          <h1>私人智囊</h1>
          <p className="muted">v0.1 — 对话 + 用户可控长期记忆</p>
          {error && <div className="error">{error}</div>}
          <label>邮箱</label>
          <input value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" />
          <label>密码（至少10位）</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} />
          <button className="action" onClick={submitAuth} disabled={busy}>
            {busy ? "请稍候…" : mode === "register" ? "注册并进入" : "登录"}
          </button>
          <p>
            <button className="ghost" onClick={() => setMode(mode === "register" ? "login" : "register")}>
              {mode === "register" ? "已有账号？登录" : "没有账号？注册"}
            </button>
          </p>
        </div>
      </main>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">私人智囊</div>
        <div className="muted">Private Advisor v0.1</div>
        <button className="primary" onClick={createConversation}>＋ 新对话</button>
        <button className="secondary" onClick={() => setTab("memory")}>
          长期记忆 ({memories.filter(m => m.status === "pending").length} 待确认)
        </button>
        <button className="secondary" onClick={loadProfile}>私人档案</button>
        <button className="secondary" onClick={loadUsage}>API 用量</button>
        <div style={{ marginTop: 22 }} className="muted">对话</div>
        {conversations.map(c => (
          <button className="secondary conversationButton" key={c.id}
            onClick={() => loadMessages(c.id)} title={c.title}>
            {c.title}
          </button>
        ))}
        <button className="secondary" onClick={logout}>退出登录</button>
      </aside>

      <main className="main">
        {error && <div className="error">{error}</div>}
        {notice && <div className="success" onClick={() => setNotice("")}>{notice}</div>}

        <div className="tabs">
          <button className={`tab ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")}>对话</button>
          <button className={`tab ${tab === "memory" ? "active" : ""}`} onClick={() => setTab("memory")}>记忆</button>
        </div>

        {tab === "chat" && (
          <div className="card">
            <h2>和私人智囊对话</h2>
            <div className="messages">
              {messages.length === 0 &&
                <p className="muted">先告诉智囊一个你正在思考的问题。确认过的长期记忆会在相关时被使用。</p>}
              {messages.map(m =>
                <div className={`message ${m.role}`} key={m.id}>{m.content}</div>
              )}
            </div>
            <div className="composer">
              <textarea value={draft} onChange={e => setDraft(e.target.value)}
                placeholder="输入你的问题……"
                onKeyDown={e => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault(); void sendMessage();
                  }
                }} />
              <button className="action" onClick={sendMessage} disabled={busy}>
                {busy ? "思考中…" : "发送"}
              </button>
            </div>
          </div>
        )}

        {tab === "memory" && (
          <div className="card">
            <h2>长期记忆</h2>
            <p className="muted">候选记忆只有经你确认后才会用于未来回答。</p>
            {memories.length === 0 && <p>还没有任何记忆。</p>}
            {memories.map(m => (
              <div className="memory" key={m.id}>
                <div className="memoryMeta">
                  <span className="pill">{m.category}</span>
                  <span className={`pill ${m.status === "pending" ? "pending" : ""}`}>{m.status}</span>
                  <span className="pill">confidence {m.confidence.toFixed(2)}</span>
                </div>
                <div>{m.content}</div>
                <div className="row" style={{ marginTop: 10 }}>
                  {m.status === "pending" &&
                    <button className="action" onClick={() => confirmMemory(m.id)}>确认记住</button>}
                  <button className="ghost" onClick={() => deleteMemory(m.id)}>删除</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "profile" && (
          <div className="card">
            <h2>私人档案</h2>
            <label>称呼</label>
            <input value={displayName} onChange={e => setDisplayName(e.target.value)} />
            <label>语言区域</label>
            <input value={locale} onChange={e => setLocale(e.target.value)} />
            <label>时区</label>
            <input value={timezone} onChange={e => setTimezone(e.target.value)} />
            <label>智囊偏好（JSON，开发版）</label>
            <textarea value={preferenceText} onChange={e => setPreferenceText(e.target.value)}
              style={{ minHeight: 180 }} />
            <button className="action" onClick={saveProfile}>保存档案</button>
          </div>
        )}

        {tab === "usage" && (
          <div className="card">
            <h2>API 用量</h2>
            <p>模型调用次数：{usage.calls}</p>
            <p>输入 tokens：{usage.input_tokens.toLocaleString()}</p>
            <p>输出 tokens：{usage.output_tokens.toLocaleString()}</p>
            <p className="muted">v0.1 不硬编码美元单价，因为模型价格会变化。</p>
          </div>
        )}
      </main>
    </div>
  );
}
