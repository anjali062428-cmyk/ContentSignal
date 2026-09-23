"use client";

import React, { useState, useRef, useEffect } from "react";
import { Bot, Send, User, ShieldCheck, Loader2, Database } from "lucide-react";
import { api } from "@/lib/api";
import { useDataset } from "@/context/DatasetContext";

interface Message {
  role: "user" | "assistant";
  text: string;
  isGrounded?: boolean;
}

function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*.*?\*\*|`.*?`|\*.*?\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      parts.push(
        <strong key={key++} className="font-semibold text-slate-900 dark:text-white">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith("`") && token.endsWith("`")) {
      parts.push(
        <code
          key={key++}
          className="px-1 py-0.5 rounded bg-slate-200/70 dark:bg-slate-800 text-teal-700 dark:text-teal-300 font-mono text-[11px]"
        >
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith("*") && token.endsWith("*")) {
      parts.push(
        <em key={key++} className="italic text-slate-700 dark:text-slate-300">
          {token.slice(1, -1)}
        </em>
      );
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

function FormattedMessage({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      elements.push(<div key={`sp-${i}`} className="h-1.5" />);
      continue;
    }

    if (trimmed.startsWith("### ")) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-sm font-bold text-slate-900 dark:text-white mt-3 mb-1.5 first:mt-0">
          {renderInline(trimmed.substring(4))}
        </h3>
      );
    } else if (trimmed.startsWith("#### ")) {
      elements.push(
        <h4 key={`h4-${i}`} className="text-xs font-bold text-slate-800 dark:text-slate-200 mt-2 mb-1">
          {renderInline(trimmed.substring(5))}
        </h4>
      );
    } else if (line.startsWith("   - ")) {
      elements.push(
        <div key={`sub-${i}`} className="pl-5 text-xs text-slate-700 dark:text-slate-300 my-0.5 flex items-start gap-1.5">
          <span className="text-teal-500 shrink-0 select-none">&bull;</span>
          <div>{renderInline(line.substring(5))}</div>
        </div>
      );
    } else if (trimmed.startsWith("- ")) {
      elements.push(
        <div key={`li-${i}`} className="pl-1.5 text-xs text-slate-700 dark:text-slate-300 my-0.5 flex items-start gap-1.5">
          <span className="text-teal-600 dark:text-teal-400 shrink-0 select-none">&bull;</span>
          <div>{renderInline(trimmed.substring(2))}</div>
        </div>
      );
    } else if (/^\d+\.\s/.test(trimmed)) {
      const match = trimmed.match(/^(\d+)\.\s(.*)$/);
      if (match) {
        elements.push(
          <div key={`num-${i}`} className="pl-1 text-xs text-slate-800 dark:text-slate-200 mt-2 mb-0.5 font-medium flex items-start gap-1.5">
            <span className="text-teal-600 dark:text-teal-400 font-bold shrink-0">{match[1]}.</span>
            <div>{renderInline(match[2])}</div>
          </div>
        );
      } else {
        elements.push(<p key={`p-${i}`} className="text-xs my-1">{renderInline(line)}</p>);
      }
    } else {
      elements.push(
        <p key={`p-${i}`} className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed my-1">
          {renderInline(line)}
        </p>
      );
    }
  }

  return <div className="space-y-0.5">{elements}</div>;
}

export default function AIAssistantPage() {
  const { activeDataset } = useDataset();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Hello! I am your ContentSignal Assistant. I provide editorial decision support grounded strictly in measurable search, traffic, and content metrics. What would you like to investigate across your content catalog?",
      isGrounded: true,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const quickPrompts = [
    "Which 5 older pages have the strongest performance in the current dataset?",
    "How many pages are in the current dataset?",
    "What are the top 5 highest-opportunity pages?",
    "Which pages have the strongest visibility but weak click performance?",
    "Explain why the highest-opportunity page received its score.",
    "What information is unavailable in this dataset?",
  ];

  const handleSend = async (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim() || loading) return;

    const userMsg: Message = { role: "user", text: query };
    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput("");
    setLoading(true);

    try {
      const activeDatasetId =
        activeDataset?.dataset_id ||
        (typeof window !== "undefined" ? localStorage.getItem("ci_active_dataset_id") : null) ||
        undefined;

      const res = await api.chatAI({
        message: query,
        dataset_id: activeDatasetId,
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: res.response,
          isGrounded: res.is_grounded,
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "AI explanation is temporarily unavailable. The application continues to operate normally.",
          isGrounded: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-display font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
            <Bot className="w-7 h-7 text-teal-600 dark:text-teal-400" />
            Content Intelligence Assistant
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Ask questions about content performance, review priority, and measurable search signals.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeDataset && (
            <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-xs border border-slate-200 dark:border-slate-700">
              <Database className="w-3 h-3 text-teal-600 dark:text-teal-400" />
              <span className="font-medium truncate max-w-[140px]">{activeDataset.name || activeDataset.dataset_id}</span>
            </div>
          )}
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 text-xs font-semibold border border-emerald-200 dark:border-emerald-800">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Strictly Grounded</span>
          </div>
        </div>
      </div>

      {/* Chat Card */}
      <div className="glass-card rounded-3xl border border-slate-200 dark:border-slate-800 flex flex-col h-[580px] shadow-sm overflow-hidden">
        {/* Messages Scroll Area */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-3 ${
                m.role === "user" ? "flex-row-reverse" : "flex-row"
              }`}
            >
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                  m.role === "user"
                    ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900"
                    : "bg-teal-600 text-white shadow-sm"
                }`}
              >
                {m.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div
                className={`max-w-xl p-4 rounded-2xl text-xs leading-relaxed ${
                  m.role === "user"
                    ? "bg-teal-600 text-white whitespace-pre-line"
                    : "bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200"
                }`}
              >
                {m.role === "user" ? m.text : <FormattedMessage content={m.text} />}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-teal-600 text-white flex items-center justify-center shrink-0">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900 text-xs text-slate-500 border border-slate-200 dark:border-slate-800">
                Retrieving observable search evidence & synthesizing response...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Prompts Bar */}
        <div className="p-3 bg-slate-50/60 dark:bg-slate-900/60 border-t border-slate-200/60 dark:border-slate-800/60 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-[11px] font-bold text-slate-400 shrink-0">Prompts:</span>
          {quickPrompts.map((p) => (
            <button
              key={p}
              onClick={() => handleSend(p)}
              disabled={loading}
              className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 hover:bg-teal-50 dark:hover:bg-teal-950/40 text-slate-600 dark:text-slate-300 hover:text-teal-600 dark:hover:text-teal-300 border border-slate-200 dark:border-slate-700 transition-colors disabled:opacity-50 text-left"
            >
              {p.length > 45 ? `${p.substring(0, 42)}...` : p}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="p-4 border-t border-slate-200 dark:border-slate-800 flex items-center gap-3"
        >
          <input
            type="text"
            placeholder="Ask a question grounded in catalog metrics..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            className="flex-1 px-4 py-2.5 text-xs rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white disabled:opacity-40 transition-colors shadow-sm"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}