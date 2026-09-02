"use client"

import { useState, useRef, useEffect } from "react"
import Navbar from "@/components/layout/navbar"
import { api } from "@/lib/api"
import { Send, Bot, User, Loader2, RotateCcw, MessageSquare } from "lucide-react"

interface Message {
  role: "user" | "assistant"
  content: string
  time: Date
  error?: boolean
}

const SUGGESTIONS = [
  "What are my top 5 opportunities?",
  "Which deadlines are coming up soon?",
  "Show me free tuition programmes",
  "Which countries have the most matches?",
  "Why is my top opportunity ranked highest?",
]

const INITIAL: Message = {
  role: "assistant",
  content: "Hi! I'm your GuideToDream assistant.\n\nAsk me anything about your opportunities, scores, deadlines, or application status.",
  time: new Date(0),
}

function Bubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user"
  const t = msg.time.getTime() === 0 ? "" : msg.time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })

  return (
    <div style={{
      display: "flex", gap: 10, alignItems: "flex-start",
      flexDirection: isUser ? "row-reverse" : "row",
    }}>
      <div style={{
        width: 30, height: 30, borderRadius: "var(--r-md)", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: isUser ? "var(--navy)" : "var(--navy-faint)",
        border: `1px solid ${isUser ? "var(--navy)" : "var(--border)"}`,
      }}>
        {isUser
          ? <User style={{ width: 13, height: 13, color: "#fff" }} />
          : <Bot  style={{ width: 13, height: 13, color: "var(--navy)" }} />}
      </div>
      <div style={{ maxWidth: "78%", display: "flex", flexDirection: "column", gap: 4, alignItems: isUser ? "flex-end" : "flex-start" }}>
        <div style={{
          padding: "11px 15px",
          borderRadius: isUser ? "12px 3px 12px 12px" : "3px 12px 12px 12px",
          background: isUser ? "var(--navy)" : "var(--bg-card)",
          border: `1px solid ${isUser ? "var(--navy)" : msg.error ? "var(--red-border)" : "var(--border)"}`,
          boxShadow: "var(--shadow-sm)",
          fontSize: "0.875rem",
          color: isUser ? "#fff" : msg.error ? "var(--red)" : "var(--navy)",
          lineHeight: 1.65,
        }}>
          <pre style={{ margin: 0, fontFamily: "inherit", fontSize: "inherit", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {msg.content}
          </pre>
        </div>
        {t && <span style={{ fontSize: "0.62rem", color: "var(--gray-400)" }}>{t}</span>}
      </div>
    </div>
  )
}

function TypingDots() {
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
      <div style={{
        width: 30, height: 30, borderRadius: "var(--r-md)", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: "var(--navy-faint)", border: "1px solid var(--border)",
      }}>
        <Bot style={{ width: 13, height: 13, color: "var(--navy)" }} />
      </div>
      <div style={{
        padding: "13px 16px", borderRadius: "3px 12px 12px 12px",
        background: "var(--bg-card)", border: "1px solid var(--border)",
        boxShadow: "var(--shadow-sm)",
        display: "flex", alignItems: "center", gap: 5,
      }}>
        {[0,1,2].map(i => (
          <span key={i} style={{
            width: 6, height: 6, borderRadius: "50%", background: "var(--navy)",
            opacity: 0.4, display: "block",
            animation: `dot-pulse 1.3s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
    </div>
  )
}

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([INITIAL])
  const [input, setInput]       = useState("")
  const [loading, setLoading]   = useState(false)
  const bottomRef               = useRef<HTMLDivElement>(null)
  const inputRef                = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    setMessages([{ ...INITIAL, time: new Date() }])
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  async function send(q: string) {
    const t = q.trim()
    if (!t || loading) return
    setInput("")
    setMessages(p => [...p, { role: "user", content: t, time: new Date() }])
    setLoading(true)
    try {
      const res = await api.ask(t)
      setMessages(p => [...p, { role: "assistant", content: res.answer, time: new Date() }])
    } catch {
      setMessages(p => [...p, { role: "assistant", content: "Couldn't reach the backend. Make sure the API is running.", time: new Date(), error: true }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input) }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100dvh", background: "var(--bg-page)" }}>
      <Navbar />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", maxWidth: 800, width: "100%", margin: "0 auto", padding: "0 20px", minHeight: 0 }}>

        {/* Header */}
        <div style={{
          padding: "18px 0 14px",
          borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 40, height: 40, borderRadius: "var(--r-md)",
              background: "var(--navy)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "var(--shadow-sm)",
            }}>
              <MessageSquare style={{ width: 18, height: 18, color: "var(--gold-border)" }} />
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: "1rem", fontWeight: 700, color: "var(--navy)" }}>
                Assistant
              </h1>
              <p style={{ margin: 0, fontSize: "0.72rem", color: "var(--gray-500)" }}>
                Knows your opportunities, scores and deadlines
              </p>
            </div>
          </div>
          {messages.length > 1 && (
            <button onClick={() => { setMessages([{ ...INITIAL, time: new Date() }]); setInput("") }}
              className="btn-ghost" style={{ padding: "6px 12px", fontSize: "0.78rem" }}>
              <RotateCcw style={{ width: 12, height: 12 }} /> Clear
            </button>
          )}
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px 0", display: "flex", flexDirection: "column", gap: 16, minHeight: 0 }}>
          {messages.map((msg, i) => <Bubble key={i} msg={msg} />)}
          {loading && <TypingDots />}
          <div ref={bottomRef} />
        </div>

        {/* Suggestions */}
        {messages.length === 1 && !loading && (
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12, paddingBottom: 10, flexShrink: 0 }}>
            <p style={{ fontSize: "0.68rem", fontWeight: 700, color: "var(--gray-400)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
              Try asking
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => send(s)} style={{
                  padding: "6px 12px", borderRadius: 999,
                  fontSize: "0.78rem", fontWeight: 500,
                  color: "var(--gray-600)", background: "var(--white)",
                  border: "1px solid var(--border)", cursor: "pointer",
                  transition: "all 0.12s",
                }}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLElement).style.background = "var(--navy-faint)"
                    ;(e.currentTarget as HTMLElement).style.color = "var(--navy)"
                    ;(e.currentTarget as HTMLElement).style.borderColor = "var(--navy)"
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLElement).style.background = "var(--white)"
                    ;(e.currentTarget as HTMLElement).style.color = "var(--gray-600)"
                    ;(e.currentTarget as HTMLElement).style.borderColor = "var(--border)"
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div style={{ padding: "12px 0 20px", borderTop: "1px solid var(--border)", flexShrink: 0 }}>
          <div style={{
            display: "flex", gap: 8, alignItems: "flex-end",
            background: "var(--white)", border: "1px solid var(--border)",
            borderRadius: "var(--r-lg)", padding: "8px 8px 8px 14px",
            boxShadow: "var(--shadow-sm)",
            transition: "border-color 0.15s, box-shadow 0.15s",
          }}
            onFocusCapture={e => {
              const el = e.currentTarget as HTMLElement
              el.style.borderColor = "var(--navy)"
              el.style.boxShadow = "0 0 0 3px rgba(26,45,74,0.10)"
            }}
            onBlurCapture={e => {
              const el = e.currentTarget as HTMLElement
              el.style.borderColor = "var(--border)"
              el.style.boxShadow = "var(--shadow-sm)"
            }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about your opportunities… (Enter to send)"
              disabled={loading}
              rows={1}
              style={{
                flex: 1, background: "transparent", border: "none", outline: "none",
                color: "var(--navy)", fontSize: "0.875rem", lineHeight: 1.6,
                resize: "none", fontFamily: "inherit", paddingTop: 4,
                maxHeight: 120, overflowY: "auto",
              }}
              onInput={e => {
                const el = e.currentTarget
                el.style.height = "auto"
                el.style.height = `${Math.min(el.scrollHeight, 120)}px`
              }}
            />
            <button onClick={() => send(input)} disabled={loading || !input.trim()} style={{
              width: 36, height: 36, borderRadius: "var(--r-md)", border: "none", flexShrink: 0,
              cursor: loading || !input.trim() ? "not-allowed" : "pointer",
              background: input.trim() && !loading ? "var(--navy)" : "var(--gray-100)",
              display: "flex", alignItems: "center", justifyContent: "center", transition: "all 0.15s",
            }}>
              {loading
                ? <Loader2 style={{ width: 14, height: 14, color: "var(--navy)" }} className="animate-spin" />
                : <Send    style={{ width: 14, height: 14, color: input.trim() ? "#fff" : "var(--gray-400)" }} />}
            </button>
          </div>
          <p style={{ margin: "5px 0 0 2px", fontSize: "0.62rem", color: "var(--gray-400)" }}>
            Shift+Enter for new line · Enter to send
          </p>
        </div>
      </div>
    </div>
  )
}
