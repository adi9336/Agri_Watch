import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle, ArrowUpRight, BarChart3, Bell, CheckCircle2, CircleDollarSign,
  CloudSun, Leaf, MessageSquare, Mic, PhoneCall, PhoneOff, Radio, RefreshCw,
  Send, ShieldCheck, Sparkles, TrendingUp, Wheat, X
} from 'lucide-react';
import { useLiveKitVoice } from './useLiveKitVoice';
import AIOrbCSS from './components/AIOrbCSS';
import { LANGUAGES, makeT } from './i18n';

const readSavedLanguage = () => { try { return localStorage.getItem('agriwatch-language') || 'hi-IN'; } catch { return 'hi-IN'; } };

export default function App() {
  const { status, isAgentSpeaking, isUserSpeaking, volume, error: voiceError, transcript, connect, disconnect } = useLiveKitVoice();
  const [activeTab, setActiveTab] = useState('overview');
  const [language, setLanguage] = useState(readSavedLanguage);
  const [inputText, setInputText] = useState('');
  // Canned messages store a key (rendered in the current language); replies store their text
  const [messages, setMessages] = useState([{ role: 'assistant', key: 'chat_welcome', time: null }]);
  const [sessionContext, setSessionContext] = useState({});
  const [isTyping, setIsTyping] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const chatEndRef = useRef(null);
  const transcriptEndRef = useRef(null);
  const t = makeT(language);

  const orbState = status === 'connecting' || isTyping ? 'thinking' : status === 'connected' ? (isAgentSpeaking ? 'speaking' : 'listening') : 'idle';
  const clockTime = () => new Date().toLocaleTimeString(language, { hour: '2-digit', minute: '2-digit' });
  const today = new Intl.DateTimeFormat(language, { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }).format(new Date());

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isTyping]);
  useEffect(() => { transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [transcript]);
  useEffect(() => {
    document.documentElement.lang = language.split('-')[0];
    document.title = `🌾 AgriWatch · ${t('tagline')}`;
  }, [language]);

  const changeLanguage = (code) => {
    setLanguage(code);
    try { localStorage.setItem('agriwatch-language', code); } catch {}
    if (status === 'connected' || status === 'connecting') disconnect();  // voice session is per-language
  };

  const fetchPriceCard = async (crop, district) => {
    try {
      const res = await fetch(`/api/price?crop=${encodeURIComponent(crop)}&district=${encodeURIComponent(district)}`);
      const data = await res.json();
      if (res.ok && data.status === 'success') setLastResult(data);
    } catch {}
  };

  const handleSendMessage = async (customText = null) => {
    const text = customText || inputText;
    if (!text.trim() || isTyping) return;
    setMessages(prev => [...prev, { role: 'user', text: text.trim(), time: clockTime() }]);
    if (!customText) setInputText('');
    setIsTyping(true);
    try {
      const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, session_context: sessionContext, language }) });
      const data = await res.json();
      setSessionContext(data.session_context || {});
      setMessages(prev => [...prev, { role: 'assistant', text: data.response, intent: data.intent, time: clockTime() }]);
      if (data.session_context?.crop && data.session_context?.district) fetchPriceCard(data.session_context.crop, data.session_context.district);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', key: 'chat_error', time: null }]);
    } finally { setIsTyping(false); }
  };

  const handleVoiceToggle = () => {
    if (status === 'connected' || status === 'connecting') return disconnect();
    setActiveTab('voice');  // show the live transcript while the call runs
    connect('agri-room-1', language);
  };
  const voiceErrorText = voiceError ? (voiceError.startsWith('err_') ? t(voiceError) : voiceError) : null;

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><Wheat size={18} /></div><div><strong>Agri<span>Watch</span></strong><small>{t('tagline')}</small></div></div>
        <div className="topbar-meta"><select className="language-select" value={language} onChange={e => changeLanguage(e.target.value)} aria-label={t('language')}>{LANGUAGES.map(([code, label]) => <option key={code} value={code}>{label}</option>)}</select><div className="live-indicator"><span /> {t('system_active')}</div><div className="weather"><CloudSun size={16} /> 28° <span>{t('city')}</span></div><button className="icon-button" aria-label={t('notifications')}><Bell size={17} /></button><button className="avatar" aria-label={t('profile')}>AK</button></div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <div className="sidebar-label">{t('control_center')}</div>
          {[['overview', BarChart3, t('nav_overview')], ['voice', Radio, t('nav_voice')], ['chat', MessageSquare, t('nav_chat')]].map(([id, Icon, label]) => <button key={id} onClick={() => setActiveTab(id)} className={`nav-item ${activeTab === id ? 'active' : ''}`}><Icon size={17} />{label}{id === 'voice' && status === 'connected' && <i />}</button>)}
          <div className="sidebar-spacer" />
          <div className="tip-card"><Sparkles size={16} /><strong>{t('tip_title')}</strong><p>{t('tip_text')}</p><button onClick={() => { setActiveTab('chat'); handleSendMessage(t('tip_question')); }}>{t('tip_ask')} <ArrowUpRight size={13} /></button></div>
          <div className="sidebar-foot"><ShieldCheck size={14} /> {t('secure')}</div>
        </aside>

        <main className="main-content">
          <div className="page-heading"><div><p className="eyebrow">{today}</p><h1>{t('good_morning')} <span>।</span></h1><p className="subheading">{t('subheading')}</p></div><button onClick={handleVoiceToggle} className={`primary-button ${status === 'connected' ? 'danger' : ''}`}>{status === 'connected' ? <PhoneOff size={16} /> : <PhoneCall size={16} />}{status === 'connected' ? t('end_call') : t('talk_live')}</button></div>

          <section className="stats-grid"><Stat icon={CircleDollarSign} label={t('stat_avg_price')} value="₹ 2,450" note={t('stat_avg_note')} trend="+4.8%" /><Stat icon={TrendingUp} label={t('stat_msp_gap')} value="+₹ 350" note={t('stat_msp_note')} trend={t('stat_good')} positive /><Stat icon={Leaf} label={t('stat_your_crop')} value={t('crop_wheat')} note={t('stat_harvest')} /><Stat icon={CheckCircle2} label={t('stat_reliability')} value="98.4%" note={t('stat_verified')} positive /></section>

          <div className="content-grid">
            <section className="panel assistant-panel">
              <div className="panel-header"><div><p className="eyebrow">AGRI INTELLIGENCE</p><h2>{activeTab === 'voice' ? t('nav_voice') : activeTab === 'chat' ? t('panel_chat') : t('panel_today')}</h2></div><span className="status-badge"><span /> {t('online')}</span></div>
              {activeTab === 'overview' && <div className="overview-hero"><div className="orb-wrap"><AIOrbCSS state={orbState} volume={volume} size={168} onClick={handleVoiceToggle} /></div><div className="hero-copy"><h3>{t('hero_title')}</h3><p>{t('hero_text')}</p><div className="query-row">{t('quick').map(query => <button key={query} onClick={() => { setActiveTab('chat'); handleSendMessage(query); }}>{query}<ArrowUpRight size={13} /></button>)}</div></div></div>}
              {activeTab === 'voice' && <div className={`voice-view ${transcript.length || status === 'connected' ? 'with-transcript' : ''}`}><AIOrbCSS state={orbState} volume={volume} size={transcript.length || status === 'connected' ? 110 : 190} onClick={handleVoiceToggle} /><p className="voice-status"><span className={status === 'connected' ? 'pulse' : ''} />{status === 'connected' ? (isAgentSpeaking ? t('voice_replying') : isUserSpeaking ? t('voice_listening') : t('voice_mic_active')) : status === 'connecting' ? t('voice_connecting') : t('voice_tap')}</p>{(transcript.length > 0 || status === 'connected') && <div className="transcript" aria-live="polite"><p className="transcript-title">{t('transcript_title')}</p>{transcript.length === 0 && <p className="transcript-empty">{t('transcript_empty')}</p>}{transcript.map(line => <div key={line.id} className={`message ${line.role} ${line.final ? '' : 'partial'}`}><small className="speaker">{line.role === 'user' ? t('you') : t('assistant_label')}</small><div>{line.text}</div></div>)}<div ref={transcriptEndRef} /></div>}</div>}
              {activeTab === 'chat' && <Chat t={t} messages={messages} inputText={inputText} setInputText={setInputText} isTyping={isTyping} handleSendMessage={handleSendMessage} chatEndRef={chatEndRef} lastResult={lastResult} />}
              {voiceErrorText && <div className="error-banner"><AlertCircle size={16} /><span>{voiceErrorText}</span><button onClick={() => disconnect()} aria-label={t('close')}><X size={14} /></button></div>}
            </section>
            <section className="panel market-panel"><div className="panel-header"><div><p className="eyebrow">NEARBY MARKETS</p><h2>{t('nearby_title')}</h2></div><button className="text-button">{t('see_all')} <ArrowUpRight size={14} /></button></div><MarketRow t={t} name={t('mandi_sehore')} crop={t('crop_wheat')} price="₹ 2,450" change="+4.8%" /><MarketRow t={t} name={t('mandi_bhopal')} crop={t('crop_wheat')} price="₹ 2,410" change="+3.2%" /><MarketRow t={t} name={t('mandi_vidisha')} crop={t('crop_gram')} price="₹ 5,860" change="+1.7%" /><div className="market-footer"><ShieldCheck size={14} /> {t('updated_at')}</div></section>
          </div>
        </main>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, note, trend, positive }) { return <div className="stat-card"><div className="stat-icon"><Icon size={17} /></div><p>{label}</p><strong>{value}</strong><small>{note}</small>{trend && <em className={positive ? 'positive' : ''}>{trend}</em>}</div>; }
function MarketRow({ t, name, crop, price, change }) { return <div className="market-row"><div className="market-symbol"><Wheat size={15} /></div><div><strong>{name}</strong><small>{crop} · {t('todays_price')}</small></div><div className="market-price"><strong>{price}</strong><small>{change}</small></div></div>; }
function Chat({ t, messages, inputText, setInputText, isTyping, handleSendMessage, chatEndRef, lastResult }) { return <div className="chat-wrap"><div className="messages">{messages.map((msg, i) => <div key={i} className={`message ${msg.role}`}><div>{msg.key ? t(msg.key) : msg.text}</div><small>{msg.time || t('now')}</small></div>)}{isTyping && <div className="message assistant typing">{t('typing')}</div>}<div ref={chatEndRef} /></div>{lastResult && <div className="result-strip"><div><strong>{lastResult.crop} · {lastResult.district}</strong><small>{lastResult.market}</small></div><b>₹{Number(lastResult.modal_price).toLocaleString('en-IN')}<small>{t('per_quintal')}</small></b></div>}<form className="chat-input" onSubmit={e => { e.preventDefault(); handleSendMessage(); }}><input value={inputText} onChange={e => setInputText(e.target.value)} placeholder={t('input_placeholder')} /><button disabled={!inputText.trim() || isTyping} aria-label={t('send')}><Send size={16} /></button></form></div>; }
