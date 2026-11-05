import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  Volume2,
  Send,
  Sparkles,
  MapPin,
  ShieldCheck,
  RefreshCw,
  PhoneCall,
  PhoneOff,
  Radio,
  AlertCircle,
  TrendingUp,
  ArrowUpRight
} from 'lucide-react';
import { useLiveKitVoice } from './useLiveKitVoice';
import AIBlob from './components/AIBlob';

export default function App() {
  const { status, isAgentSpeaking, isUserSpeaking, volume, error: voiceError, connect, disconnect } = useLiveKitVoice();

  const [activeTab, setActiveTab] = useState('voice'); // 'voice' | 'chat'
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'नमस्ते किसान भाई! मैं एग्री-वॉच हूँ। अपनी फसल और मंडी का नाम बोलकर या लिखकर आज का मंडी भाव, आसपास का मुनाफा और सरकारी MSP जान सकते हैं।',
      time: 'अभी'
    }
  ]);
  const [sessionContext, setSessionContext] = useState({});
  const [isTyping, setIsTyping] = useState(false);
  const [metadata, setMetadata] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  const chatEndRef = useRef(null);

  // Derive 3D AI Blob state (idle | listening | thinking | speaking)
  const activeBlobState = 
    status === 'connecting' || isTyping
      ? 'thinking'
      : status === 'connected'
        ? isAgentSpeaking
          ? 'speaking'
          : isUserSpeaking
            ? 'listening'
            : 'listening'
        : 'idle';

  // Load metadata on mount
  useEffect(() => {
    fetch('/api/metadata')
      .then((res) => res.json())
      .then((data) => setMetadata(data))
      .catch((err) => console.log('Metadata notice:', err));
  }, []);

  // Auto scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Handle Text Query
  const handleSendMessage = async (customText = null) => {
    const textToSend = customText || inputText;
    if (!textToSend.trim() || isTyping) return;

    const userMsg = {
      role: 'user',
      text: textToSend.trim(),
      time: new Date().toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customText) setInputText('');
    setIsTyping(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: textToSend,
          session_context: sessionContext
        })
      });

      if (!res.ok) throw new Error('API request failed');
      const data = await res.json();

      setSessionContext(data.session_context || {});

      const assistantMsg = {
        role: 'assistant',
        text: data.response,
        intent: data.intent,
        time: new Date().toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // If price was returned in context, fetch card
      if (data.session_context?.crop && data.session_context?.district) {
        fetchPriceCard(data.session_context.crop, data.session_context.district);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'माफ़ करें, जानकारी प्राप्त करने में अस्थायी समस्या हुई। कृपया दोबारा पूछें।',
          time: 'अभी'
        }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const fetchPriceCard = async (crop, district) => {
    try {
      const res = await fetch(`/api/price?crop=${encodeURIComponent(crop)}&district=${encodeURIComponent(district)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') {
          setLastResult(data);
        }
      }
    } catch (e) {
      console.log('Price card notice:', e);
    }
  };

  const handleVoiceToggle = () => {
    if (status === 'connected' || status === 'connecting') {
      disconnect();
    } else {
      connect('agri-room-1');
    }
  };

  return (
    <div className="relative min-h-screen bg-[#03060d] text-zinc-100 flex flex-col justify-between selection:bg-emerald-500/20 selection:text-emerald-300">
      {/* Dynamic Ambient Glass Glow Orbs */}
      <div className="ambient-glow-emerald -top-20 left-1/4 pointer-events-none" />
      <div className="ambient-glow-amber bottom-10 -right-20 pointer-events-none" />
      <div className="ambient-glow-cyan top-1/3 -left-20 pointer-events-none" />

      {/* Floating Minimalist Island Navigation */}
      <header className="sticky top-4 z-50 max-w-4xl w-[94%] mx-auto">
        <div className="glass-surface px-4 sm:px-6 py-2.5 flex items-center justify-between">
          {/* Brand Mark */}
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)] animate-pulse" />
            <div className="flex flex-col">
              <span className="text-sm font-semibold tracking-wider text-shimmer uppercase">Agri-Watch</span>
              <span className="text-[10px] text-zinc-400 -mt-0.5 tracking-wide">कृषि मंडी वॉयस इंटेलिजेंस</span>
            </div>
          </div>

          {/* Whispering Mode Switcher Capsule */}
          <div className="flex p-0.5 rounded-full bg-white/[0.03] border border-white/[0.08] shadow-inner">
            <button
              onClick={() => setActiveTab('voice')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-300 ${
                activeTab === 'voice'
                  ? 'bg-white/[0.1] text-white shadow-[0_2px_12px_rgba(0,0,0,0.4)] border border-white/[0.12]'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Radio size={13} className={activeTab === 'voice' ? 'text-emerald-400' : ''} />
              <span>वॉयस मोड</span>
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-300 ${
                activeTab === 'chat'
                  ? 'bg-white/[0.1] text-white shadow-[0_2px_12px_rgba(0,0,0,0.4)] border border-white/[0.12]'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Sparkles size={13} className={activeTab === 'chat' ? 'text-amber-400' : ''} />
              <span>खोज व चैट</span>
            </button>
          </div>

          {/* Quick Voice Call Pill */}
          <button
            onClick={handleVoiceToggle}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-300 ${
              status === 'connected'
                ? 'glass-btn-danger text-red-200'
                : status === 'connecting'
                ? 'glass-pill text-amber-200'
                : 'glass-btn-primary text-emerald-100'
            }`}
          >
            {status === 'connected' ? (
              <>
                <PhoneOff size={13} />
                <span className="hidden sm:inline">कॉल काटें</span>
              </>
            ) : status === 'connecting' ? (
              <>
                <RefreshCw size={13} className="animate-spin" />
                <span className="hidden sm:inline">जुड़ रहे हैं...</span>
              </>
            ) : (
              <>
                <PhoneCall size={13} />
                <span>लाइव कॉल</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-[94%] mx-auto my-6 flex flex-col justify-center relative z-10">
        
        {/* ================================================================== */}
        {/* VOICE MODE: Pure Glass AI Orb Centerpiece */}
        {/* ================================================================== */}
        {activeTab === 'voice' && (
          <div className="flex flex-col items-center justify-center py-6 sm:py-10 text-center select-none">
            
            {/* The Floating 3D Glass AI Orb */}
            <div className="relative flex items-center justify-center my-2">
              <AIBlob
                state={activeBlobState}
                volume={volume}
                size={320}
                interactive={true}
                onClick={handleVoiceToggle}
                className="transition-transform duration-500 hover:scale-[1.04]"
                colors={{
                  core: '#f59e0b',
                  body: '#10b981',
                  rim: '#06b6d4',
                  active: '#22c55e'
                }}
              />
            </div>

            {/* Ethereal Floating Status Pill */}
            <div className="mt-4 flex items-center gap-2 px-4 py-2 rounded-full glass-surface-subtle border border-white/[0.08] shadow-[0_8px_24px_rgba(0,0,0,0.4)]">
              <span className={`w-2 h-2 rounded-full ${
                activeBlobState === 'speaking'
                  ? 'bg-amber-400 animate-ping'
                  : activeBlobState === 'listening'
                  ? 'bg-emerald-400 animate-pulse'
                  : activeBlobState === 'thinking'
                  ? 'bg-cyan-400 animate-spin'
                  : 'bg-zinc-500'
              }`} />
              <span className="text-xs font-medium tracking-wide text-zinc-300">
                {status === 'connected' ? (
                  isAgentSpeaking ? (
                    '🌾 एग्री-वॉच जवाब दे रहा है (टोकने के लिए बोलें)'
                  ) : isUserSpeaking ? (
                    '🎙️ सुन रहा हूँ... आप बोल रहे हैं'
                  ) : (
                    'माइक सक्रिय है · फसल व मंडी का नाम पूछें'
                  )
                ) : status === 'connecting' ? (
                  'लाइव वॉयस रूम से जुड़ रहे हैं...'
                ) : (
                  'ऑर्ब पर टैप करें या ऊपर लाइव कॉल दबाएं'
                )}
              </span>
            </div>

            {/* Subtle Audio Waveform (Only visible when active audio is moving) */}
            {(isAgentSpeaking || isUserSpeaking) && (
              <div className="flex items-center gap-1.5 mt-4 h-6">
                {[35, 70, 95, 60, 85, 40, 90, 65, 30].map((h, i) => (
                  <div
                    key={i}
                    className="w-1 bg-gradient-to-t from-emerald-400 to-amber-300 rounded-full transition-all duration-75"
                    style={{
                      height: `${Math.max(4, Math.min(24, (volume + 0.25) * (h / 3.2)))}px`,
                    }}
                  />
                ))}
              </div>
            )}

            {/* Minimal Prompt Chips */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-2 max-w-lg">
              {[
                'कल्याण मंडी में चना का भाव',
                'झांसी में गेहूं का ताजा रेट',
                'कटनी में चना का आज का भाव',
                'गेहूं का सरकारी MSP क्या है?'
              ].map((text, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setActiveTab('chat');
                    handleSendMessage(text);
                  }}
                  className="glass-pill px-3.5 py-1.5 text-xs text-zinc-400 hover:text-white flex items-center gap-1.5 group"
                >
                  <span>{text}</span>
                  <ArrowUpRight size={12} className="opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                </button>
              ))}
            </div>

            {voiceError && (
              <div className="mt-4 flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-950/40 border border-red-500/30 text-red-300 text-xs">
                <AlertCircle size={14} />
                <span>{voiceError}</span>
              </div>
            )}
          </div>
        )}

        {/* ================================================================== */}
        {/* CHAT MODE: Transparent Minimalist Stream */}
        {/* ================================================================== */}
        {activeTab === 'chat' && (
          <div className="flex flex-col flex-1 h-[68vh] justify-between">
            {/* Conversation Stream */}
            <div className="flex-1 overflow-y-auto pr-2 space-y-4 py-2">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[85%] sm:max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-emerald-500/[0.12] border border-emerald-400/[0.25] text-emerald-100 shadow-[0_4px_20px_rgba(16,185,129,0.15)] rounded-tr-sm'
                        : 'glass-surface text-zinc-200 rounded-tl-sm'
                    }`}
                  >
                    <p>{msg.text}</p>
                    <span className="block text-[10px] text-zinc-500 mt-1.5 text-right font-mono">
                      {msg.time}
                    </span>
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="flex items-center gap-2 glass-surface-subtle px-4 py-2.5 rounded-2xl w-fit">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                  <span className="text-xs text-zinc-400 ml-1">मंडी भाव खोज रहे हैं...</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Floating Glass Omnibar */}
            <div className="pt-3">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="glass-input flex items-center px-4 py-2 gap-2"
              >
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="फसल व मंडी लिखें (उदा. राठ में चना, झांसी में गेहूं)..."
                  className="flex-1 bg-transparent border-none outline-none text-sm text-zinc-100 placeholder:text-zinc-500"
                />

                <button
                  type="submit"
                  disabled={!inputText.trim() || isTyping}
                  className="glass-btn-primary p-2 text-white disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                >
                  <Send size={15} />
                </button>
              </form>
            </div>
          </div>
        )}

        {/* ================================================================== */}
        {/* MANDI PRICE CRYSTALLINE HUD (Floats above or below when active) */}
        {/* ================================================================== */}
        {lastResult && (
          <div className="mt-4 glass-surface px-5 py-4 border-l-2 border-l-emerald-400 relative overflow-hidden transition-all duration-300">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-lg">
                  🌾
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-white text-base">
                      {lastResult.crop} · {lastResult.district}
                    </h3>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25 flex items-center gap-1">
                      <ShieldCheck size={11} />
                      Agmarknet
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    मंडी: {lastResult.market} · {lastResult.reporting_date || lastResult.requested_date}
                  </p>
                </div>
              </div>

              {/* Price Highlights */}
              <div className="flex items-center gap-6">
                <div>
                  <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">मॉडल भाव</span>
                  <span className="text-xl sm:text-2xl font-bold text-emerald-shimmer font-mono">
                    ₹{Number(lastResult.modal_price).toLocaleString('en-IN')}
                    <span className="text-xs font-normal text-zinc-400 ml-1">/क्विंटल</span>
                  </span>
                </div>

                <div className="hidden sm:flex flex-col text-right text-xs text-zinc-400 border-l border-white/[0.08] pl-4">
                  <span>न्यूनतम: <strong className="text-zinc-200">₹{Number(lastResult.min_price || 0).toLocaleString('en-IN')}</strong></span>
                  <span>अधिकतम: <strong className="text-zinc-200">₹{Number(lastResult.max_price || 0).toLocaleString('en-IN')}</strong></span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Whisper Minimal Footer */}
      <footer className="max-w-4xl w-[94%] mx-auto pb-4 pt-2 text-center text-[11px] text-zinc-500 flex items-center justify-between">
        <span>© 2026 Agri-Watch · संप्रभु भारतीय कृषि वॉयस इंटेलिजेंस</span>
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          LiveKit WebRTC + Silero VAD
        </span>
      </footer>
    </div>
  );
}
