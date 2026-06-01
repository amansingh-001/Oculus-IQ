import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Bot, Power, Sparkles } from 'lucide-react';

import {
  getAgentStatus,
  getClientSlaOverview,
  getDisruptions,
  sendCopilotMessage,
  toggleAgent,
  QUERY_KEYS,
} from '../api/client';

function CopilotPage() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [streamText, setStreamText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef(null);

  const { data: disruptions } = useQuery({ queryKey: QUERY_KEYS.disruptions, queryFn: getDisruptions });
  const { data: slaOverview } = useQuery({ queryKey: QUERY_KEYS.slaOverview, queryFn: getClientSlaOverview });
  const { data: agentData, refetch: refetchAgent } = useQuery({
    queryKey: QUERY_KEYS.agentStatus,
    queryFn: getAgentStatus,
    refetchInterval: 30000,
  });

  const agentStatus = agentData?.data || {};
  const topDisruption = disruptions?.data?.[0];
  const topClient = slaOverview?.data?.[0];

  const dynamicPrompts = useMemo(() => [
    'Which of my clients are at SLA risk right now?',
    topClient ? `Draft a WhatsApp alert for ${topClient.client_name}` : 'Which clients should I call today?',
    topDisruption ? `What is the client impact of ${topDisruption.title}?` : 'What are my biggest client risks right now?',
    'What is the tariff impact on my highest-risk clients?',
    'Generate a weekly performance summary for all clients',
  ], [topClient, topDisruption]);

  const conversationHistory = useMemo(
    () => messages.slice(-10).map((msg) => ({ role: msg.role, content: msg.content })),
    [messages]
  );

  const streamResponse = useCallback((fullText) => {
    setIsStreaming(true);
    setStreamText('');
    let i = 0;
    const interval = setInterval(() => {
      if (i < fullText.length) {
        setStreamText(fullText.substring(0, i + 1));
        i += 1;
      } else {
        clearInterval(interval);
        setIsStreaming(false);
        setMessages((prev) => [...prev, { role: 'assistant', content: fullText, ts: new Date().toISOString() }]);
        setStreamText('');
      }
    }, 12);
    return () => clearInterval(interval);
  }, []);

  const chatMutation = useMutation({
    mutationFn: ({ message, history }) => sendCopilotMessage(message, history),
    onSuccess: (payload, variables) => {
      setMessages((prev) => [...prev, { role: 'user', content: variables.message, ts: new Date().toISOString() }]);
      streamResponse(payload.data?.response || payload.data || '');
    },
  });

  const agentToggle = useMutation({
    mutationFn: toggleAgent,
    onSuccess: () => refetchAgent(),
  });

  const sendMessage = (text) => {
    const trimmed = (text || input).trim();
    if (!trimmed || chatMutation.isPending || isStreaming) return;
    chatMutation.mutate({ message: trimmed, history: conversationHistory });
    setInput('');
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamText]);

  return (
    <div className="copilot-shell">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[color:var(--glass-border)]">
        <div className="flex items-center gap-2">
          <Bot size={16} color="var(--ocean-teal)" />
          <span className="text-xs font-semibold text-[color:var(--text-primary)]">OculusIQ Intelligence Officer</span>
        </div>
        <button
          type="button"
          onClick={() => agentToggle.mutate()}
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-[0.1em] transition-all"
          style={{
            background: agentStatus.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.05)',
            border: `1px solid ${agentStatus.is_active ? '#10B981' : 'var(--glass-border)'}`,
            color: agentStatus.is_active ? '#10B981' : 'var(--text-muted)',
          }}
        >
          <Power size={10} />
          {agentStatus.is_active ? 'Agent Active' : 'Autonomous Mode'}
          {agentStatus.is_active && (
            <span className="pulse-dot" style={{ background: '#10B981', width: 6, height: 6 }} />
          )}
        </button>
      </div>

      {agentStatus.is_active && agentStatus.actions_today > 0 && (
        <div className="px-4 py-1.5 bg-[rgba(16,185,129,0.08)] text-[10px] text-[#10B981] font-semibold">
          Agent took {agentStatus.actions_today} action(s) today
        </div>
      )}

      <div className="copilot-body">
        {messages.length === 0 && !chatMutation.isPending && !isStreaming ? (
          <div className="copilot-empty">
            <div className="radar-animation">
              <svg viewBox="0 0 80 80" aria-hidden="true">
                <circle cx="40" cy="40" r="36" stroke="#00C8E0" strokeWidth="0.6" fill="none" opacity="0.3" />
                <circle cx="40" cy="40" r="24" stroke="#00C8E0" strokeWidth="0.8" fill="none" opacity="0.5" />
                <circle cx="40" cy="40" r="12" stroke="#00C8E0" strokeWidth="1.2" fill="none" opacity="0.8" />
                <line x1="40" y1="40" x2="40" y2="6" stroke="#00C8E0" strokeWidth="1.2" className="radar-sweep" />
                <circle cx="40" cy="40" r="3" fill="#00C8E0" />
              </svg>
            </div>
            <h2>OculusIQ Intelligence Officer</h2>
            <p>Your AI-powered freight intelligence officer.</p>
            <p className="sub">
              Ask about client SLA risk, tariff exposure, route alternatives, or ready-to-send client updates.
            </p>
            <div className="suggestions">
              {dynamicPrompts.map((suggestion) => (
                <button key={suggestion} type="button" onClick={() => sendMessage(suggestion)}>
                  <Sparkles size={10} style={{ opacity: 0.5 }} />
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="copilot-messages">
            {messages.map((msg, idx) => (
              <div key={`${msg.ts}-${idx}`} className={`message ${msg.role === 'user' ? 'user' : 'assistant'}`}>
                {msg.content}
              </div>
            ))}
            {isStreaming && streamText && (
              <div className="message assistant">
                {streamText}
                <span className="inline-block w-1.5 h-4 ml-0.5 bg-[color:var(--ocean-teal)] animate-pulse" />
              </div>
            )}
            {chatMutation.isPending && !isStreaming && (
              <div className="thinking">
                Analyzing client portfolio...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="copilot-input">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') sendMessage();
          }}
          placeholder="Ask which client needs action now..."
          disabled={chatMutation.isPending || isStreaming}
        />
        <button onClick={() => sendMessage()} disabled={chatMutation.isPending || isStreaming}>
          Send
        </button>
      </div>
    </div>
  );
}

export default CopilotPage;
