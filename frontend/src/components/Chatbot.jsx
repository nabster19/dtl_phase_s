// Chatbot.jsx — CuraAI AI Healthcare Chatbot Component
import React, { useState, useEffect, useRef } from 'react';
import { api } from '../utils/api';

// ── Markdown-style renderer for bold/bullets ──────────────────────────────────
function renderMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>');
}

// ── Urgency color map ─────────────────────────────────────────────────────────
const urgencyColor = {
  'Emergency': 'border-red-400 bg-red-50 dark:bg-red-950/20',
  'Severe':    'border-orange-400 bg-orange-50 dark:bg-orange-950/20',
  'Moderate':  'border-amber-300 bg-amber-50 dark:bg-amber-950/20',
  'Mild':      'border-emerald-300 bg-emerald-50 dark:bg-emerald-950/20',
};

// ── Type badge color ──────────────────────────────────────────────────────────
const typeBadge = {
  emergency:       'bg-red-100 text-red-700',
  symptom_analysis:'bg-sky-100 text-sky-700',
  drug_info:       'bg-violet-100 text-violet-700',
  doctor_recommend:'bg-teal-100 text-teal-700',
  health_tip:      'bg-emerald-100 text-emerald-700',
  greeting:        'bg-slate-100 text-slate-600',
  help:            'bg-indigo-100 text-indigo-700',
};

// ── Suggested quick prompts ───────────────────────────────────────────────────
const QUICK_PROMPTS = [
  "I have fever and headache for 2 days",
  "What are the side effects of Metformin?",
  "Which doctor should I see for chest pain?",
  "Give me diet tips for diabetes",
  "I feel dizzy and nauseous after meals",
  "Tell me about Paracetamol dosage",
];

export default function Chatbot({ darkMode }) {
  const [messages, setMessages]         = useState([]);
  const [input, setInput]               = useState('');
  const [loading, setLoading]           = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [showPrompts, setShowPrompts]   = useState(true);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  // Load history on mount
  useEffect(() => {
    loadHistory();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadHistory = async () => {
    try {
      const res = await api.getChatHistory();
      if (res.history && res.history.length > 0) {
        setMessages(res.history.map(h => ({
          role: h.role,
          text: h.message,
          type: h.metadata?.type || 'general',
          data: h.metadata?.data || {},
          time: h.created_at,
        })));
        setShowPrompts(false);
      } else {
        // Show welcome message
        setMessages([{
          role: 'assistant',
          text: "👋 **Hello! I'm CuraAI Assistant** — your AI-powered health companion.\n\nI can analyze your symptoms, recommend doctors, provide drug information, and give personalized health tips.\n\nDescribe how you're feeling or ask me anything health-related!",
          type: 'greeting',
          data: {},
          time: new Date().toISOString(),
        }]);
      }
    } catch (e) {
      console.error('Chat history error:', e);
    }
    setHistoryLoaded(true);
  };

  const sendMessage = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput('');
    setShowPrompts(false);

    // Append user message immediately
    const userMsg = { role: 'user', text: msg, type: 'user', data: {}, time: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await api.sendChatMessage(msg);
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: res.reply,
        type: res.type || 'general',
        data: res.data || {},
        time: new Date().toISOString(),
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: `⚠ Sorry, I encountered an error: ${err.message}. Please try again.`,
        type: 'error',
        data: {},
        time: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const clearHistory = async () => {
    if (!window.confirm('Clear all chat history?')) return;
    try {
      await api.clearChatHistory();
      setMessages([{
        role: 'assistant',
        text: "Chat history cleared. How can I help you today?",
        type: 'greeting', data: {}, time: new Date().toISOString(),
      }]);
      setShowPrompts(true);
    } catch (e) { console.error(e); }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  return (
    <div className="flex flex-col h-full" style={{ minHeight: '75vh' }}>
      {/* Header */}
      <div className="bg-gradient-to-r from-sky-600 to-indigo-600 rounded-2xl p-4 mb-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center text-xl">🤖</div>
          <div>
            <h2 className="font-bold text-white text-lg">CuraAI Medical Assistant</h2>
            <div className="flex items-center space-x-1.5">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
              <span className="text-sky-200 text-xs">AI Online · Powered by CuraAI NLP Engine</span>
            </div>
          </div>
        </div>
        <button onClick={clearHistory}
          className="text-white/70 hover:text-white text-xs bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition font-medium">
          Clear History
        </button>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 pb-4" style={{ maxHeight: '55vh' }}>
        {!historyLoaded && (
          <div className="text-center text-slate-400 text-sm py-8">Loading chat history...</div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 bg-gradient-to-br from-sky-500 to-indigo-600 rounded-full flex items-center justify-center text-white text-sm mr-2 mt-1 flex-shrink-0">
                🤖
              </div>
            )}
            <div className={`max-w-[80%] ${msg.role === 'user' ? 'max-w-[70%]' : ''}`}>
              {/* Type badge for assistant */}
              {msg.role === 'assistant' && msg.type && msg.type !== 'general' && (
                <div className="mb-1">
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${typeBadge[msg.type] || 'bg-slate-100 text-slate-600'}`}>
                    {msg.type.replace(/_/g, ' ')}
                  </span>
                </div>
              )}
              <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-sky-500 text-white rounded-tr-sm'
                  : `bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-tl-sm shadow-sm border ${
                      msg.type === 'emergency' ? 'border-red-300' : 'border-slate-100 dark:border-slate-700'
                    }`
              }`}>
                {msg.role === 'assistant' ? (
                  <span dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }} />
                ) : (
                  msg.text
                )}
              </div>

              {/* Prediction pills */}
              {msg.data?.predictions?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {msg.data.predictions.slice(0, 3).map((p, i) => (
                    <span key={i} className={`text-[10px] font-semibold px-2 py-1 rounded-full ${
                      i === 0 ? 'bg-sky-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                    }`}>
                      {p.disease} · {p.confidence}%
                    </span>
                  ))}
                </div>
              )}

              {/* Urgency badge */}
              {msg.data?.urgency && msg.data.urgency !== 'Mild' && (
                <div className={`mt-2 text-xs font-semibold px-3 py-1.5 rounded-xl border ${urgencyColor[msg.data.urgency] || ''}`}>
                  ⚡ {msg.data.urgency} Urgency
                  {msg.data.urgency === 'Emergency' && ' — Call 108 immediately'}
                </div>
              )}

              <div className="text-[10px] text-slate-400 mt-1 px-1">
                {new Date(msg.time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
            {msg.role === 'user' && (
              <div className="w-8 h-8 bg-sky-100 dark:bg-sky-900/30 rounded-full flex items-center justify-center text-sky-600 text-sm ml-2 mt-1 flex-shrink-0">
                👤
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="w-8 h-8 bg-gradient-to-br from-sky-500 to-indigo-600 rounded-full flex items-center justify-center text-white text-sm mr-2 mt-1">🤖</div>
            <div className="bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <div className="flex space-x-1 items-center h-4">
                <div className="w-2 h-2 bg-sky-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-sky-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-sky-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      {showPrompts && messages.length <= 1 && (
        <div className="mb-3">
          <p className="text-xs text-slate-400 font-semibold mb-2">💡 Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {QUICK_PROMPTS.map((p, i) => (
              <button key={i} onClick={() => sendMessage(p)}
                className="text-xs bg-slate-100 dark:bg-slate-800 hover:bg-sky-100 dark:hover:bg-sky-900/30 hover:text-sky-600 text-slate-600 dark:text-slate-300 px-3 py-1.5 rounded-xl transition font-medium border border-slate-200 dark:border-slate-700">
                {p}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-xl px-4 py-2 mb-3 text-[11px] text-amber-700 dark:text-amber-400">
        ⚕ <strong>Disclaimer:</strong> CuraAI responses are for informational purposes only. Always consult a licensed medical professional for diagnosis and treatment.
      </div>

      {/* Input box */}
      <div className="flex items-end space-x-3">
        <div className="flex-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl px-4 py-3 flex items-end shadow-sm focus-within:ring-2 focus-within:ring-sky-500 focus-within:border-transparent transition">
          <textarea
            ref={inputRef}
            rows={1}
            placeholder="Describe your symptoms or ask a health question..."
            className="flex-1 bg-transparent text-sm text-slate-800 dark:text-slate-200 outline-none resize-none placeholder-slate-400 leading-relaxed"
            style={{ maxHeight: '120px' }}
            value={input}
            onChange={e => {
              setInput(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
            onKeyDown={handleKeyDown}
          />
        </div>
        <button
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
          className="w-12 h-12 bg-sky-500 hover:bg-sky-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-2xl flex items-center justify-center transition shadow-sm flex-shrink-0"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
    </div>
  );
}
