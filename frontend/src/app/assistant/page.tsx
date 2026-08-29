"use client"

import { useState, useRef, useEffect } from "react"
import Navbar from "@/components/layout/navbar"
import { api } from "@/lib/api"
import { Send, Bot, User, Loader2, MessageSquare } from "lucide-react"

interface Message {
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

const SUGGESTIONS = [
  "What are my top 5 opportunities right now?",
  "Which deadlines are coming up in 30 days?",
  "Show me the cheapest programmes I'm eligible for",
  "Why is my top opportunity ranked so high?",
  "Which countries have the most opportunities for me?",
]

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! I'm your GuideToDream assistant. I have access to all your discovered opportunities, eligibility assessments, and application pipeline. Ask me anything about your European Master's journey.",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function send(question: string) {
    if (!question.trim() || loading) return
    const q = question.trim()
    setInput("")
    setMessages((prev) => [
      ...prev,
      { role: "user", content: q, timestamp: new Date() },
    ])
    setLoading(true)
    try {
      const res = await api.ask(q)
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, timestamp: new Date() },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I couldn't reach the backend. Make sure the API is running.",
          timestamp: new Date(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Navbar />
      <main className="pt-14 flex flex-col h-screen max-w-3xl mx-auto px-4">
        {/* Header */}
        <div className="py-6 border-b border-white/5">
          <h1 className="text-white text-2xl font-bold flex items-center gap-2">
            <MessageSquare className="w-6 h-6 text-purple-400" />
            Assistant
          </h1>
          <p className="text-zinc-500 text-sm mt-1">
            Ask anything about your opportunities in plain English
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto py-6 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                  msg.role === "assistant" ? "bg-purple-500/20" : "bg-blue-500/20"
                }`}
              >
                {msg.role === "assistant" ? (
                  <Bot className="w-4 h-4 text-purple-400" />
                ) : (
                  <User className="w-4 h-4 text-blue-400" />
                )}
              </div>
              <div
                className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "assistant"
                    ? "bg-[#0d1117] border border-white/5 text-zinc-300"
                    : "bg-blue-600/20 border border-blue-500/30 text-white"
                }`}
              >
                <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
                <span className="text-xs text-zinc-600 mt-1 block">
                  {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-purple-500/20 flex items-center justify-center">
                <Bot className="w-4 h-4 text-purple-400" />
              </div>
              <div className="bg-[#0d1117] border border-white/5 rounded-xl px-4 py-3">
                <Loader2 className="w-4 h-4 text-zinc-500 animate-spin" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Suggestions */}
        {messages.length === 1 && (
          <div className="flex flex-wrap gap-2 pb-3">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="text-xs px-3 py-1.5 bg-white/5 border border-white/10 rounded-full text-zinc-400 hover:text-white hover:border-white/20 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="py-4 border-t border-white/5">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              send(input)
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your opportunities..."
              disabled={loading}
              className="flex-1 bg-[#0d1117] border border-white/5 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 outline-none focus:border-white/10 transition-colors disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </main>
    </>
  )
}
