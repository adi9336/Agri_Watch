import React, { useState, useEffect, useRef } from 'react';
import {
  Mic, Volume2, Send, Sparkles, ShieldCheck,
  RefreshCw, PhoneCall, PhoneOff, Radio,
  AlertCircle, ArrowUpRight, MessageSquare, Wheat
} from 'lucide-react';
import { useLiveKitVoice } from './useLiveKitVoice';
import AIOrbCSS from './components/AIOrbCSS';

export default function App() {
  const { status, isAgentSpeaking, isUserSpeaking, volume, error: voiceError, connect, disconnect } = useLiveKitVoice();

  const [activeTab, setActiveTab] = useState('voice');
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'नमस्ते किसान भाई! फसल और मंडी का नाम बोलें या लिखें — मैं आज का APMC मंडी भाव, MSP, और आसपास की मंडियों में मुनाफा तुरंत बताऊंगा।',
      time: 'अभी'
    }
  ]);
  const [sessionContext, setSessionContext] = useState({});
  const [isTyping, setIsTyping] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const chatEndRef = useRef(null);

  // Derive orb state
  const orbState =
    status === 'connecting' || isTyping ? 'thinking'
    : status === 'connected'
      ? isAgentSpeaking ? 'speaking'
      : isUserSpeaking  ? 'listening'
      : 'listening'
    : 'idle';

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSendMessage = async (customText = null) => {
    const text = customText || inputText;
    if (!text.trim() || isTyping) return;

    setMessages(prev => [...prev, {
      role: 'user', text: text.trim(),
      time: new Date().toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' })
    }]);
    if (!customText) setInputText('');
    setIsTyping(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_context: sessionContext })
      });
      const data = await res.json();
      setSessionContext(data.session_context || {});
      setMessages(prev => [...prev, {
        role: 'assistant', text: data.response, intent: data.intent,
        time: new Date().toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' })
      }]);
      if (data.session_context?.crop && data.session_context?.district) {
        fetchPriceCard(data.session_context.crop, data.session_context.district);
      }
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: 'अस्थायी समस्या हुई। कृपया दोबारा पूछें।',
        time: 'अभी'
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const fetchPriceCard = async (crop, district) => {
    try {
      const res = await fetch(`/api/price?crop=${encodeURIComponent(crop)}&district=${encodeURIComponent(district)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') setLastResult(data);
      }
    } catch {}
  };

  const handleVoiceToggle = () => {
    if (status === 'connected' || status === 'connecting') disconnect();
    else connect('agri-room-1');
  };

  const chips = [
    'कल्याण में चने का भाव',
    'झांसी में गेहूं का रेट',
    'कटनी में चना आज का',
    'गेहूं का MSP क्या है?',
  ];

  return (
    <div className="relative h-full bg-[#060b14] bg-grid overflow-hidden flex flex-col">
      {/* ── Scene ambient lights ── */}
      <div className="scene-light w-[600px] h-[600px] bg-emerald-500/20 -top-32 left-1/2 -translate-x-1/2" />
      <div className="scene-light w-[400px] h-[400px] bg-indigo-500/15 bottom-0 -right-32" />
      <div className="scene-light w-[300px] h-[300px] bg-amber-500/12 top-1/2 -left-24" />

      {/* ── Floating Island Nav ── */}
      <div className="relative z-50 max-w-3xl w-full mx-auto px-4 pt-3 shrink-0">
        <div className="glass rounded-2xl px-4 py-2.5 flex items-center justify-between gap-3">
          {/* Brand */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-900/50">
              <Wheat size={14} className="text-white" />
            </div>
            <div className="leading-tight">
              <div className="text-[13px] font-semibold tracking-wide text-g-white">Agri-Watch</div>
              <div className="text-[10px] text-white/35 tracking-wide">कृषि वॉयस इंटेलिजेंस</div>
            </div>
          </div>

          {/* Tab switcher */}
          <div className="flex p-0.5 rounded-xl bg-white/[0.04] border border-white/[0.06] gap-0.5">
            {[
              { id: 'voice', label: 'वॉयस', Icon: Radio },
              { id: 'chat',  label: 'चैट',  Icon: MessageSquare },
            ].map(({ id, label, Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[10px] text-xs font-medium transition-all duration-200 ${
                  activeTab === id
                    ? 'bg-white/[0.1] text-white border border-white/[0.1] shadow-sm'
                    : 'text-white/40 hover:text-white/70'
                }`}
              >
                <Icon size={12} />
                {label}
              </button>
            ))}
          </div>

          {/* Voice CTA */}
          <button
            onClick={handleVoiceToggle}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium cursor-pointer shrink-0 ${
              status === 'connected' ? 'btn-red text-red-200'
              : status === 'connecting' ? 'glass-pill text-white/60'
              : 'btn-emerald text-emerald-100'
            }`}
          >
            {status === 'connected' ? <><PhoneOff size={12} /><span className="hidden sm:inline">काटें</span></>
            : status === 'connecting' ? <><RefreshCw size={12} className="animate-spin" /><span className="hidden sm:inline">जुड़ रहे हैं</span></>
            : <><PhoneCall size={12} /><span>लाइव कॉल</span></>}
          </button>
        </div>
      </div>

      {/* ── Main Content ── */}
      <main className="relative z-10 flex-1 min-h-0 max-w-3xl w-full mx-auto px-4 pt-3 pb-2 flex flex-col overflow-hidden">

        {/* ============================================================
            VOICE TAB — Centered orb experience
            ============================================================ */}
        {activeTab === 'voice' && (
          <div className="flex flex-col items-center justify-center flex-1 min-h-0 gap-3 overflow-hidden">

            {/* Orb area */}
            <div className="relative flex items-center justify-center">
              {/* Pulsing ring behind orb when active */}
              {status === 'connected' && (
                <div className="absolute inset-0 rounded-full"
                  style={{
                    animation: 'ringPulse 2.4s ease-out infinite',
                    border: `1px solid ${isAgentSpeaking ? 'rgba(245,158,11,0.3)' : 'rgba(52,211,153,0.3)'}`,
                    borderRadius: '50%',
                    inset: '-20px',
                    position: 'absolute',
                  }}
                />
              )}

              <div className="orb-float">
                <AIOrbCSS
                  state={orbState}
                  volume={volume}
                  size={200}
                  onClick={handleVoiceToggle}
                />
              </div>
            </div>

            {/* Status text */}
            <div className="flex flex-col items-center gap-2">
              <div className="flex items-center gap-2 glass-pill px-4 py-2">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                  orbState === 'speaking'  ? 'bg-amber-400 animate-ping'
                  : orbState === 'listening' ? 'bg-emerald-400 animate-pulse'
                  : orbState === 'thinking'  ? 'bg-indigo-400 animate-spin'
                  : 'bg-white/25'
                }`} />
                <span className="text-sm text-white/75 font-medium">
                  {status === 'connected'
                    ? isAgentSpeaking ? '🌾 जवाब दे रहा हूँ — बोलकर रोक सकते हैं'
                    : isUserSpeaking  ? '🎙️ सुन रहा हूँ...'
                    : 'माइक सक्रिय है · अपनी बात कहें'
                    : status === 'connecting' ? '🔄 LiveKit से जुड़ रहे हैं...'
                    : 'ऑर्ब पर टैप करें · या ऊपर "लाइव कॉल" दबाएं'}
                </span>
              </div>

              {/* Audio waveform — only when speaking */}
              {(isAgentSpeaking || isUserSpeaking) && (
                <div className="flex items-end gap-1 h-6">
                  {[0.4, 0.75, 1, 0.6, 0.85, 0.45, 0.9, 0.65, 0.3].map((h, i) => (
                    <div
                      key={i}
                      className="wave-bar"
                      style={{
                        height: `${Math.max(4, Math.min(22, (volume + 0.3) * h * 22))}px`,
                        animationDelay: `${i * 70}ms`,
                        animation: 'waveBar 0.9s ease-in-out infinite alternate',
                        animationDelay: `${i * 65}ms`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Quick chips */}
            <div className="flex flex-wrap justify-center gap-2 max-w-md">
              {chips.map((chip, i) => (
                <button
                  key={i}
                  onClick={() => { setActiveTab('chat'); handleSendMessage(chip); }}
                  className="glass-pill px-3 py-1.5 text-xs text-white/50 hover:text-white/90 flex items-center gap-1 group transition-all"
                >
                  {chip}
                  <ArrowUpRight size={11} className="opacity-0 group-hover:opacity-60 transition-opacity" />
                </button>
              ))}
            </div>

            {voiceError && (
              <div className="flex items-start gap-2 glass-sm px-4 py-3 rounded-2xl border border-red-500/20 max-w-sm text-center">
                <AlertCircle size={15} className="text-red-400 mt-0.5 shrink-0" />
                <div>
                  <div className="text-xs font-medium text-red-300 mb-0.5">वॉयस कनेक्शन त्रुटि</div>
                  <div className="text-xs text-red-300/70 leading-relaxed">{voiceError}</div>
                  <div className="text-[11px] text-white/30 mt-1.5">
                    चैट मोड में टेक्स्ट से भी भाव पूछ सकते हैं →
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================
            CHAT TAB
            ============================================================ */}
        {activeTab === 'chat' && (
          <div className="flex flex-col flex-1 min-h-0 gap-3">

            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-1 pb-2 min-h-0">
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                    msg.role === 'user' ? 'bubble-user text-emerald-100 rounded-br-sm'
                    : 'bubble-ai text-white/80 rounded-bl-sm'
                  }`}>
                    {msg.text}
                    <div className="text-[10px] text-white/25 mt-1 text-right font-mono">{msg.time}</div>
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="flex justify-start">
                  <div className="bubble-ai px-4 py-2.5 rounded-2xl rounded-bl-sm flex items-center gap-1.5">
                    {[0, 150, 300].map(d => (
                      <span
                        key={d}
                        className="w-1.5 h-1.5 rounded-full bg-white/40 animate-bounce"
                        style={{ animationDelay: `${d}ms` }}
                      />
                    ))}
                    <span className="text-xs text-white/35 ml-1">मंडी भाव खोज रहे हैं...</span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Price result card */}
            {lastResult && (
              <div className="glass rounded-2xl px-5 py-4 border-l-2 border-l-emerald-500/60 shrink-0">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-base font-semibold text-white">{lastResult.crop} · {lastResult.district}</span>
                      <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                        <ShieldCheck size={10} /> Agmarknet
                      </span>
                    </div>
                    <div className="text-xs text-white/35">{lastResult.market} · {lastResult.reporting_date || lastResult.requested_date}</div>
                  </div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-bold text-g-emerald font-mono">
                      ₹{Number(lastResult.modal_price).toLocaleString('en-IN')}
                    </span>
                    <span className="text-xs text-white/35">/क्विंटल</span>
                  </div>
                </div>
              </div>
            )}

            {/* Input bar */}
            <form
              onSubmit={e => { e.preventDefault(); handleSendMessage(); }}
              className="glass-input rounded-2xl flex items-center px-4 py-2.5 gap-3 shrink-0"
            >
              <input
                type="text"
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                placeholder="फसल व मंडी लिखें — जैसे झांसी में गेहूं..."
                className="flex-1 bg-transparent border-none outline-none text-sm text-white placeholder:text-white/25"
              />
              <button
                type="submit"
                disabled={!inputText.trim() || isTyping}
                className="btn-emerald p-2 rounded-xl text-white disabled:opacity-25 cursor-pointer"
              >
                <Send size={15} />
              </button>
            </form>
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <div className="relative z-10 max-w-3xl w-full mx-auto px-4 py-2 flex justify-between text-[11px] text-white/20 shrink-0">
        <span>© 2026 Agri-Watch</span>
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400/70" />
          LiveKit WebRTC · Silero VAD · Gnani.ai
        </span>
      </div>
    </div>
  );
}
