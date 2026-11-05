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

export default function App() {
  const { status, isAgentSpeaking, isUserSpeaking, error: voiceError, connect, disconnect } = useLiveKitVoice();

  const [activeTab, setActiveTab] = useState('voice'); // 'voice' | 'chat'
  const [inputText, setInputText] = useState('');
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

        {/* VOICE MODE PANEL */}
        {activeTab === 'voice' && (
          <div className="flex flex-col items-center justify-center py-6 sm:py-10 glass-panel p-6 sm:p-8 text-center relative overflow-hidden">
            {/* Ambient background glows */}
            <div className="absolute -top-20 -left-20 w-64 h-64 bg-green-600/10 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-20 -right-20 w-64 h-64 bg-amber-600/10 rounded-full blur-3xl pointer-events-none" />

            {/* Giant Animated Voice Orb */}
            <div className="relative my-4 sm:my-6 flex items-center justify-center">
              <button
                onClick={handleVoiceToggle}
                className={`w-40 h-40 sm:w-48 sm:h-48 rounded-full flex flex-col items-center justify-center text-white transition-all cursor-pointer relative z-10 ${
                  status === 'connected'
                    ? isAgentSpeaking
                      ? 'orb-speaking'
                      : isUserSpeaking
                      ? 'orb-listening'
                      : 'orb-listening'
                    : status === 'connecting'
                    ? 'orb-connecting'
                    : 'orb-idle hover:scale-105'
                }`}
              >
                {status === 'connected' ? (
                  isAgentSpeaking ? (
                    <>
                      <Volume2 size={44} className="mb-2 animate-bounce" />
                      <span className="text-xs font-bold tracking-wider uppercase">एजेंट बोल रहा है</span>
                      <span className="text-[10px] text-amber-200 mt-1">(रोकने के लिए बोलें)</span>
                    </>
                  ) : isUserSpeaking ? (
                    <>
                      <Mic size={44} className="mb-2 text-white animate-pulse" />
                      <span className="text-xs font-bold tracking-wider uppercase">सुन रहा हूँ...</span>
                      <span className="text-[10px] text-green-200 mt-1">आप बोल रहे हैं</span>
                    </>
                  ) : (
                    <>
                      <Mic size={44} className="mb-2 text-white" />
                      <span className="text-xs font-bold tracking-wider uppercase">माइक ऑन है</span>
                      <span className="text-[10px] text-green-200 mt-1">पूछिए (जैसे चना या गेहूं)</span>
                    </>
                  )
                ) : status === 'connecting' ? (
                  <>
                    <RefreshCw size={40} className="mb-2 animate-spin text-sky-200" />
                    <span className="text-xs font-bold">जुड़ रहा है...</span>
                  </>
                ) : (
                  <>
                    <Mic size={44} className="mb-2 text-green-300" />
                    <span className="text-xs font-bold tracking-wide">माइक दबाएं</span>
                    <span className="text-[10px] text-gray-300 mt-1">बोलकर भाव जानें</span>
                  </>
                )}
              </button>
            </div>

            {/* Voice Status Explanation */}
            <div className="max-w-md mx-auto mt-2">
              <h2 className="text-base sm:text-lg font-bold text-white">
                {status === 'connected'
                  ? isAgentSpeaking
                    ? '🌾 एग्री-वॉच जवाब दे रहा है'
                    : '🎙️ अपनी भाषा (हिंदी) में निसंकोच बोलें'
                  : 'टैप करके सीधे आवाज़ में भाव पूछें'}
              </h2>
              <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                {status === 'connected'
                  ? 'सटीक 120ms बार्ज-इन: यदि आप बीच में टोकना चाहें, तो सीधे बोलना शुरू करें - एजेंट तुरंत रुक जाएगा।'
                  : 'WebRTC लाइव ऑडियो से जुड़ें: देश भर की 2,800+ APMC मंडियों के ताज़ा भाव, न्यूनतम समर्थन मूल्य और मुनाफा तुलना।'}
              </p>
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
