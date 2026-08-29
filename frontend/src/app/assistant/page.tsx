"use client"

import { useState, useRef, useEffect } from "react"
import Navbar from "@/components/layout/navbar"
import { api } from "@/lib/api"
import { Send, Bot, User, Loader2, Sparkles } from "lucide-react"

interface Message {
  role: "user" | "assistant"
  content: string
  time: Date
}

const SUGGESTIONS = [
  "What are my top 5 opportunities?",
  "Which deadlines are coming up soon?",
  "Show me free tuition programmes",
  "Which countries have the most matches?",
  "Why is my top opportunity scored highest?",
]

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([{
    role: "assistant",
    content: "Hi! I'm your GuideToDream AI assistant. I know all your discovered opportunities, scores, and application status. Ask me anything.",
    time: new Date(),
  }])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function send(q: string) {
    if (!q.trim() || loading) return
    setInput("")
    setMessages(p => [...p, { role: "user", content: q.trim(), time: new Date() }])
    setLoading(true)
    try {
      const res = await api.ask(q.trim())
      setMessages(p => [...p, { role: "assistant", content: res.answer, time: new Date() }])
    } catch {
      setMessages(p => [...p, { role: "assistant", content: "Sorry, I couldn't reach the backend right now.", time: new Date() }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Navbar />
      <div className="pt-14 flex flex-col h-screen max-w-2xl mx-auto px-4">

        {/* Header */}
        <div className="py-5" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, rgba(129,140,248,0.2), rgba(99,179,237,0.2))", border: "1px solid rgba(129,140,248,0.3)" }}>
              <Sparkles className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-white font-semibold text-sm">AI Assistant</h1>
              <p className="text-slate-500 text-xs">Ask anything about your opportunities</p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
              <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                msg.role === "assistant"
                  ? "bg-indigo-500/15 border border-indigo-500/20"
                  : "bg-blue-500/15 border border-blue-500/20"
              }`}>
                {msg.role === "assistant"
                  ? <Bot className="w-3.5 h-3.5 text-indigo-400" />
                  : <User className="w-3.5 h-3.5 text-blue-400" />}
              </div>
              <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "assistant"
                  ? ""
                  : ""
              }`}
                style={msg.role === "assistant"
                  ? { background: "rgba(10,14,26,0.9)", border: "1px solid rgba(255,255,255,0.06)", color: "#cbd5e1" }
                  : { background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.25)", color: "#e2e8f0" }
                }>
                <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
                <span className="text-xs text-slate-600 mt-1 block">
                  {msg.time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-lg bg-indigo-500/15 border border-indigo-500/20 flex items-center justify-center">
                <Bot className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <div className="rounded-xl px-4 py-3" style={{ background: "rgba(10,14,26,0.9)", border: "1px solid rgba(255,255,255,0.06)" }}>
                <div className="flex gap-1.5 items-center h-4">
                  {[0,1,2].map(i => (
                    <div key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-400"
                      style={{ animation: `pulse-dot 1.2s ease-in-out ${i * 0.2}s infinite` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Suggestions */}
        {messages.length === 1 && (
          <div className="flex flex-wrap gap-2 pb-3">
            {SUGGESTIONS.map(s => (
              <button key={s} onClick={() => send(s)}
                className="text-xs px-3 py-1.5 rounded-full text-slate-400 hover:text-white transition-colors"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="py-4" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <form onSubmit={e => { e.preventDefault(); send(input) }} className="flex gap-2">
            <input type="text" value={input} onChange={e => setInput(e.target.value)}
              placeholder="Ask about your opportunities..."
              disabled={loading}
              className="flex-1 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-all disabled:opacity-50"
              style={{ background: "rgba(10,14,26,0.9)", border: "1px solid rgba(255,255,255,0.07)" }}
              onFocus={e => (e.target as HTMLElement).style.borderColor = "rgba(99,179,237,0.3)"}
              onBlur={e => (e.target as HTMLElement).style.borderColor = "rgba(255,255,255,0.07)"}
            />
            <button type="submit" disabled={loading || !input.trim()}
              className="px-4 py-3 rounded-xl text-white transition-all disabled:opacity-40"
              style={{ background: "linear-gradient(135deg, #4f46e5, #6366f1)" }}>
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </>
  )
}
