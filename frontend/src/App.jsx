import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  Send,
  Sparkles,
  TrendingUp,
  MapPin,
  ShieldCheck,
  RefreshCw,
  PhoneCall,
  PhoneOff,
  Radio,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ArrowRight
} from 'lucide-react';
import { useLiveKitVoice } from './useLiveKitVoice';
import AIBlob from './components/AIBlob';

export default function App() {
  const { status, isAgentSpeaking, isUserSpeaking, volume, error: voiceError, connect, disconnect } = useLiveKitVoice();

  const [activeTab, setActiveTab] = useState('voice'); // 'voice' | 'chat'
  const [inputText, setInputText] = useState('');
  const [blobStatePreview, setBlobStatePreview] = useState(null); // null = auto from WebRTC/AI
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'नमस्ते किसान भाई! मैं एग्री-वॉच हूँ। आप अपनी फसल और मंडी का नाम बोलकर या लिखकर आज का भाव, आसपास की मंडियों का मुनाफा और सरकारी समर्थन मूल्य (MSP) जान सकते हैं।',
      time: 'अभी'
    }
  ]);
  const [sessionContext, setSessionContext] = useState({});
  const [isTyping, setIsTyping] = useState(false);
  const [metadata, setMetadata] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  // Derive 3D AI Blob state (idle | listening | thinking | speaking)
  const activeBlobState = blobStatePreview || (
    status === 'connecting' || isTyping
      ? 'thinking'
      : status === 'connected'
        ? isAgentSpeaking
          ? 'speaking'
          : isUserSpeaking
            ? 'listening'
            : 'listening'
        : 'idle'
  );

  const chatEndRef = useRef(null);

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
  }, [messages]);

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

      // If price was returned in context, set card
      if (data.session_context?.crop && data.session_context?.district) {
        fetchPriceCard(data.session_context.crop, data.session_context.district);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'किसान भाई, संपर्क करने में समस्या हुई। कृपया दोबारा पूछें।',
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

  // Toggle Voice Call
  const handleVoiceToggle = () => {
    if (status === 'connected' || status === 'connecting') {
      disconnect();
    } else {
      connect('agri-room-1');
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#090d16] text-gray-100">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 bg-[#111827]/90 backdrop-blur-md border-b border-gray-800 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-700 flex items-center justify-center text-xl shadow-lg shadow-green-900/30">
              🌾
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-white tracking-wide">एग्री-वॉच (Agri_watch)</h1>
                <span className="text-[10px] uppercase font-semibold bg-green-500/10 text-green-400 border border-green-500/20 px-2 py-0.5 rounded-full">
                  लाइव APMC
                </span>
              </div>
              <p className="text-xs text-gray-400">संप्रभु कृषि मंडी वॉयस इंटेलिजेंस एजेंट</p>
            </div>
          </div>

          {/* Connection Status Pill */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-800/80 border border-gray-700/60 text-xs">
              <span className={`w-2 h-2 rounded-full ${status === 'connected' ? 'bg-green-400 animate-pulse' : status === 'connecting' ? 'bg-amber-400 animate-ping' : 'bg-gray-500'}`} />
              <span className="text-gray-300">
                {status === 'connected' ? 'WebRTC वॉयस सक्रिय' : status === 'connecting' ? 'कनेक्ट हो रहा है...' : 'वॉयस स्टैंडबाय'}
              </span>
            </div>

            <button
              onClick={handleVoiceToggle}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-lg transition-all ${
                status === 'connected'
                  ? 'bg-red-600 hover:bg-red-700 text-white shadow-red-900/30'
                  : 'bg-green-600 hover:bg-green-700 text-white shadow-green-900/30'
              }`}
            >
              {status === 'connected' ? (
                <>
                  <PhoneOff size={15} />
                  कॉल काटें
                </>
              ) : status === 'connecting' ? (
                <>
                  <RefreshCw size={15} className="animate-spin" />
                  जुड़ रहे हैं...
                </>
              ) : (
                <>
                  <PhoneCall size={15} />
                  वॉयस कॉल शुरू करें
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-4 md:p-6 flex flex-col gap-6">
        {/* Mode Selector Tabs */}
        <div className="flex bg-gray-900/90 p-1 rounded-2xl border border-gray-800 self-center w-full max-w-md shadow-inner">
          <button
            onClick={() => setActiveTab('voice')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
              activeTab === 'voice'
                ? 'bg-gradient-to-r from-green-600 to-emerald-600 text-white shadow-md'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Radio size={16} />
            वॉयस मोड (WebRTC)
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
              activeTab === 'chat'
                ? 'bg-gradient-to-r from-green-600 to-emerald-600 text-white shadow-md'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Sparkles size={16} />
            त्वरित खोज व चैट
          </button>
        </div>

        {/* VOICE MODE PANEL WITH 3D AI BLOB */}
        {activeTab === 'voice' && (
          <div className="flex flex-col items-center justify-center py-6 sm:py-8 glass-panel p-6 sm:p-8 text-center relative overflow-hidden">
            {/* Ambient background glows */}
            <div className="absolute -top-24 -left-24 w-72 h-72 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-24 -right-24 w-72 h-72 bg-amber-500/15 rounded-full blur-3xl pointer-events-none" />

            {/* AI Blob State Pill */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-900/90 border border-gray-700/70 text-xs shadow-md mb-2">
              <span className={`w-2 h-2 rounded-full ${
                activeBlobState === 'speaking'
                  ? 'bg-amber-400 animate-ping'
                  : activeBlobState === 'listening'
                  ? 'bg-emerald-400 animate-pulse'
                  : activeBlobState === 'thinking'
                  ? 'bg-cyan-400 animate-spin'
                  : 'bg-gray-400'
              }`} />
              <span className="text-gray-300 font-medium">
                {activeBlobState === 'speaking' && '✨ AI Blob: Speaking (एजेंट बोल रहा है)'}
                {activeBlobState === 'listening' && '🎙️ AI Blob: Listening (सुन रहा हूँ...)'}
                {activeBlobState === 'thinking' && '🧠 AI Blob: Thinking (सोच रहा हूँ...)'}
                {activeBlobState === 'idle' && '💎 AI Blob: Idle (स्टैंडबाय)'}
              </span>
            </div>

            {/* 3D AI Glass Orb / Blob Container */}
            <div className="relative my-2 flex items-center justify-center">
              <AIBlob
                state={activeBlobState}
                volume={volume}
                size={300}
                interactive={true}
                onClick={handleVoiceToggle}
                className="drop-shadow-[0_0_35px_rgba(16,185,129,0.35)]"
                colors={{
                  core: '#f59e0b',
                  body: '#10b981',
                  rim: '#06b6d4',
                  active: '#22c55e'
                }}
              />

              {/* Click-to-call Center Helper (when idle or disconnected) */}
              {status === 'disconnected' && (
                <div
                  onClick={handleVoiceToggle}
                  className="absolute pointer-events-none px-3 py-1 rounded-full bg-gray-950/80 border border-gray-700/60 backdrop-blur-sm text-[11px] text-gray-300 shadow-lg tracking-wide animate-pulse"
                >
                  टैप करके कॉल करें
                </div>
              )}
            </div>

            {/* Live Volume Audio Wave Bar (When speaking or listening) */}
            {(isAgentSpeaking || isUserSpeaking) && (
              <div className="flex items-center gap-1.5 my-2">
                {[40, 75, 100, 60, 85, 45, 90, 65, 30].map((h, i) => (
                  <div
                    key={i}
                    className="w-1 bg-gradient-to-t from-emerald-500 to-amber-400 rounded-full transition-all duration-100"
                    style={{
                      height: `${Math.max(6, Math.min(28, (volume + 0.2) * (h / 3)))}px`,
                      animationDelay: `${i * 60}ms`
                    }}
                  />
                ))}
              </div>
            )}

            {/* Voice Status Explanation */}
            <div className="max-w-md mx-auto mt-2">
              <h2 className="text-base sm:text-lg font-bold text-white">
                {status === 'connected'
                  ? isAgentSpeaking
                    ? '🌾 एग्री-वॉच जवाब दे रहा है'
                    : isUserSpeaking
                    ? '🎙️ आप बोल रहे हैं (सुन रहा हूँ)'
                    : '🎙️ अपनी भाषा (हिंदी) में निसंकोच पूछें'
                  : 'AI Blob 3D ग्लास ऑर्ब से सीधे बोलें'}
              </h2>
              <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                {status === 'connected'
                  ? 'सटीक 120ms बार्ज-इन: यदि आप बीच में टोकना चाहें, तो सीधे बोलना शुरू करें - एजेंट तुरंत रुक जाएगा।'
                  : 'थ्री.जेएस और सिम्प्लेक्स नॉइज़ 3D शेडर: आपके बोलने, सोचने और एजेंट के जवाब के साथ ऑर्ब लाइव रिएक्ट करता है।'}
              </p>
            </div>

            {/* Interactive State Demo Switcher */}
            <div className="mt-4 flex flex-wrap items-center justify-center gap-1.5 bg-gray-900/60 p-1.5 rounded-xl border border-gray-800 text-[11px]">
              <span className="text-gray-500 px-2 font-medium">Shader State:</span>
              {[
                { label: 'Auto (Live)', value: null },
                { label: 'Idle', value: 'idle' },
                { label: 'Listening', value: 'listening' },
                { label: 'Thinking', value: 'thinking' },
                { label: 'Speaking', value: 'speaking' },
              ].map((btn) => (
                <button
                  key={btn.label}
                  onClick={() => setBlobStatePreview(btn.value)}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    blobStatePreview === btn.value
                      ? 'bg-emerald-600 text-white font-semibold shadow-sm'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
                  }`}
                >
                  {btn.label}
                </button>
              ))}
            </div>

            {voiceError && (
              <div className="mt-4 flex items-center gap-2 bg-red-950/60 border border-red-800 text-red-300 text-xs px-4 py-2 rounded-xl">
                <AlertCircle size={16} />
                <span>त्रुटि: {voiceError}</span>
              </div>
            )}
          </div>
        )}

        {/* PRICE INTELLIGENCE CARD (If available) */}
        {lastResult && (
          <div className="glass-panel p-5 border-l-4 border-l-green-500 bg-gradient-to-r from-green-950/20 to-gray-900 shadow-xl">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-800/80 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🌱</span>
                <div>
                  <h3 className="font-bold text-white text-base sm:text-lg">
                    {lastResult.market || lastResult.district} मंडी
                  </h3>
                  <p className="text-xs text-gray-400 flex items-center gap-1">
                    <MapPin size={12} />
                    {lastResult.district} ({lastResult.crop} - {lastResult.variety || 'सामान्य'})
                  </p>
                </div>
              </div>

              <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${
                lastResult.is_today
                  ? 'bg-green-500/10 text-green-400 border-green-500/30'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              }`}>
                {lastResult.date_note || lastResult.reporting_date}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 my-4">
              <div className="bg-gray-800/50 p-3 rounded-xl border border-gray-700/40">
                <span className="text-[10px] text-gray-400 uppercase tracking-wider block">औसत / मॉडल भाव</span>
                <span className="text-xl sm:text-2xl font-black text-green-400 block mt-0.5">
                  ₹{Number(lastResult.modal_price || 0).toLocaleString('en-IN')}
                </span>
                <span className="text-[10px] text-gray-400">प्रति क्विंटल</span>
              </div>

              <div className="bg-gray-800/50 p-3 rounded-xl border border-gray-700/40">
                <span className="text-[10px] text-gray-400 uppercase tracking-wider block">न्यूनतम भाव</span>
                <span className="text-lg font-bold text-gray-300 block mt-0.5">
                  ₹{Number(lastResult.min_price || 0).toLocaleString('en-IN')}
                </span>
                <span className="text-[10px] text-gray-400">प्रति क्विंटल</span>
              </div>

              <div className="bg-gray-800/50 p-3 rounded-xl border border-gray-700/40">
                <span className="text-[10px] text-gray-400 uppercase tracking-wider block">अधिकतम भाव</span>
                <span className="text-lg font-bold text-gray-300 block mt-0.5">
                  ₹{Number(lastResult.max_price || 0).toLocaleString('en-IN')}
                </span>
                <span className="text-[10px] text-gray-400">प्रति क्विंटल</span>
              </div>

              <div className="bg-gray-800/50 p-3 rounded-xl border border-gray-700/40">
                <span className="text-[10px] text-gray-400 uppercase tracking-wider block">आधिकारिक स्थिति</span>
                <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1 mt-1.5">
                  <ShieldCheck size={14} />
                  Agmarknet सत्यापित
                </span>
                <span className="text-[10px] text-gray-400 block mt-1">तारीख: {lastResult.reporting_date}</span>
              </div>
            </div>
          </div>
        )}

        {/* QUICK SUGGESTION CHIPS */}
        {metadata && (
          <div className="flex flex-col gap-2">
            <span className="text-xs font-semibold text-gray-400 flex items-center gap-1.5">
              <Sparkles size={14} className="text-amber-400" />
              त्वरित सवाल (टैप करें):
            </span>
            <div className="flex flex-wrap gap-2">
              {metadata.suggestions?.slice(0, 4).map((sug, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(sug)}
                  className="text-xs bg-gray-800/70 hover:bg-gray-700 border border-gray-700/60 hover:border-green-500/40 text-gray-300 px-3 py-1.5 rounded-lg transition-all text-left flex items-center gap-1.5"
                >
                  <span>{sug}</span>
                  <ArrowRight size={12} className="text-gray-500" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* CHAT / TRANSCRIPT HISTORY STREAM */}
        <div className="glass-panel p-4 flex flex-col flex-1 min-h-[300px] max-h-[420px] overflow-y-auto">
          <div className="flex items-center justify-between border-b border-gray-800 pb-2 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
              <CheckCircle2 size={14} className="text-green-400" />
              संवाद इतिहास (Live Transcript & Chat)
            </span>
            <span className="text-[10px] text-gray-500">
              {messages.length} संदेश
            </span>
          </div>

          <div className="flex flex-col gap-3 flex-1">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex flex-col max-w-[85%] sm:max-w-[75%] ${
                  msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'
                }`}
              >
                <div
                  className={`px-4 py-2.5 rounded-2xl text-xs sm:text-sm leading-relaxed shadow-md ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-green-700 to-emerald-700 text-white rounded-tr-none'
                      : 'bg-gray-800/90 text-gray-200 border border-gray-700/60 rounded-tl-none'
                  }`}
                >
                  {msg.text}
                </div>
                <span className="text-[10px] text-gray-500 mt-1 px-1">
                  {msg.role === 'user' ? 'आप' : 'एग्री-वॉच'} • {msg.time}
                </span>
              </div>
            ))}

            {isTyping && (
              <div className="self-start flex items-center gap-2 bg-gray-800/60 border border-gray-700/40 px-3 py-2 rounded-2xl text-xs text-gray-400">
                <RefreshCw size={13} className="animate-spin text-green-400" />
                <span>एग्री-वॉच मंडी डेटाबेस से भाव जांच रहा है...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </div>

        {/* INPUT BAR (For Chat & Search Mode) */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2 bg-gray-900/90 border border-gray-700/80 rounded-2xl p-2 shadow-xl focus-within:border-green-500/80 transition-all"
        >
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="अपनी फसल और मंडी का नाम लिखें (जैसे: राठ मंडी में चना, झांसी में गेहूं)..."
            className="flex-1 bg-transparent px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isTyping}
            className="bg-green-600 hover:bg-green-700 disabled:opacity-40 disabled:hover:bg-green-600 text-white p-2.5 rounded-xl transition-all shadow-md flex items-center justify-center cursor-pointer"
          >
            <Send size={16} />
          </button>
        </form>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/80 py-4 px-4 bg-gray-950 text-center text-xs text-gray-500">
        <p className="max-w-3xl mx-auto">
          🌾 <strong>Agri_watch</strong> • आधिकारिक डेटा स्रोत:{' '}
          <a href="https://data.gov.in" target="_blank" rel="noreferrer" className="text-green-400 hover:underline">
            data.gov.in
          </a>{' '}
          व Agmarknet दैनिक थोक मूल्य • CACP न्यूनतम समर्थन मूल्य (MSP) • WebRTC वॉयस पावर्ड बाइ LiveKit
        </p>
      </footer>
    </div>
  );
}
