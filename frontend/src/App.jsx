import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle, ArrowUpRight, BarChart3, Bell, CheckCircle2, CircleDollarSign,
  CloudSun, Leaf, MessageSquare, Mic, PhoneCall, PhoneOff, Radio, RefreshCw,
  Send, ShieldCheck, Sparkles, TrendingUp, Wheat, X
} from 'lucide-react';
import { useLiveKitVoice } from './useLiveKitVoice';
import AIOrbCSS from './components/AIOrbCSS';

const quickQueries = ['गेहूं का आज का भाव', 'चना MSP कितना है?', 'कल्याण मंडी में भाव'];

export default function App() {
  const { status, isAgentSpeaking, isUserSpeaking, volume, error: voiceError, connect, disconnect } = useLiveKitVoice();
  const [activeTab, setActiveTab] = useState('overview');
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState([{ role: 'assistant', text: 'नमस्ते किसान भाई! फसल और मंडी का नाम बोलें या लिखें — मैं आज का भाव, MSP और आसपास की मंडियों में मुनाफा बताऊंगा।', time: 'अभी' }]);
  const [sessionContext, setSessionContext] = useState({});
  const [isTyping, setIsTyping] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const chatEndRef = useRef(null);

  const orbState = status === 'connecting' || isTyping ? 'thinking' : status === 'connected' ? (isAgentSpeaking ? 'speaking' : 'listening') : 'idle';

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isTyping]);

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
    setMessages(prev => [...prev, { role: 'user', text: text.trim(), time: new Date().toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' }) }]);
    if (!customText) setInputText('');
    setIsTyping(true);
    try {
      const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, session_context: sessionContext }) });
      const data = await res.json();
      setSessionContext(data.session_context || {});
      setMessages(prev => [...prev, { role: 'assistant', text: data.response, intent: data.intent, time: new Date().toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' }) }]);
      if (data.session_context?.crop && data.session_context?.district) fetchPriceCard(data.session_context.crop, data.session_context.district);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', text: 'अस्थायी समस्या हुई। कृपया दोबारा पूछें।', time: 'अभी' }]);
    } finally { setIsTyping(false); }
  };

  const handleVoiceToggle = () => status === 'connected' || status === 'connecting' ? disconnect() : connect('agri-room-1');

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><Wheat size={18} /></div><div><strong>Agri<span>Watch</span></strong><small>कृषि वॉयस इंटेलिजेंस</small></div></div>
        <div className="topbar-meta"><div className="live-indicator"><span /> सिस्टम सक्रिय</div><div className="weather"><CloudSun size={16} /> 28° <span>भोपाल</span></div><button className="icon-button" aria-label="सूचनाएं"><Bell size={17} /></button><button className="avatar" aria-label="प्रोफाइल">AK</button></div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <div className="sidebar-label">कंट्रोल सेंटर</div>
          {[['overview', BarChart3, 'ओवरव्यू'], ['voice', Radio, 'वॉयस सहायक'], ['chat', MessageSquare, 'टेक्स्ट चैट']].map(([id, Icon, label]) => <button key={id} onClick={() => setActiveTab(id)} className={`nav-item ${activeTab === id ? 'active' : ''}`}><Icon size={17} />{label}{id === 'voice' && status === 'connected' && <i />}</button>)}
          <div className="sidebar-spacer" />
          <div className="tip-card"><Sparkles size={16} /><strong>आज का सुझाव</strong><p>बेहतर भाव के लिए फसल को 2–3 दिन रोकने पर विचार करें।</p><button onClick={() => { setActiveTab('chat'); handleSendMessage('आज मेरी फसल के लिए क्या सुझाव है?'); }}>पूछें <ArrowUpRight size={13} /></button></div>
          <div className="sidebar-foot"><ShieldCheck size={14} /> सुरक्षित और निजी</div>
        </aside>

        <main className="main-content">
          <div className="page-heading"><div><p className="eyebrow">गुरुवार, 06 नवंबर 2026</p><h1>सुप्रभात, अरुण <span>।</span></h1><p className="subheading">आपके खेत और मंडी की आज की स्थिति एक नज़र में।</p></div><button onClick={handleVoiceToggle} className={`primary-button ${status === 'connected' ? 'danger' : ''}`}>{status === 'connected' ? <PhoneOff size={16} /> : <PhoneCall size={16} />}{status === 'connected' ? 'कॉल समाप्त करें' : 'लाइव सहायक से बात करें'}</button></div>

          <section className="stats-grid"><Stat icon={CircleDollarSign} label="आज का औसत भाव" value="₹ 2,450" note="गेहूं · प्रति क्विंटल" trend="+4.8%" /><Stat icon={TrendingUp} label="MSP से अंतर" value="+₹ 350" note="मौजूदा बाजार लाभ" trend="अच्छा" positive /><Stat icon={Leaf} label="आपकी फसल" value="गेहूं" note="कटाई: 18 दिन बाकी" /><Stat icon={CheckCircle2} label="डेटा विश्वसनीयता" value="98.4%" note="Agmarknet से सत्यापित" positive /></section>

          <div className="content-grid">
            <section className="panel assistant-panel">
              <div className="panel-header"><div><p className="eyebrow">AGRI INTELLIGENCE</p><h2>{activeTab === 'voice' ? 'वॉयस सहायक' : activeTab === 'chat' ? 'मंडी चैट' : 'आज का सहायक'}</h2></div><span className="status-badge"><span /> ऑनलाइन</span></div>
              {activeTab === 'overview' && <div className="overview-hero"><div className="orb-wrap"><AIOrbCSS state={orbState} volume={volume} size={168} onClick={handleVoiceToggle} /></div><div className="hero-copy"><h3>मंडी का हाल पूछें</h3><p>अपनी भाषा में बोलें या लिखें। मैं आपके लिए सबसे अच्छा भाव और बेचने का सही समय खोजूंगा।</p><div className="query-row">{quickQueries.map(query => <button key={query} onClick={() => { setActiveTab('chat'); handleSendMessage(query); }}>{query}<ArrowUpRight size={13} /></button>)}</div></div></div>}
              {activeTab === 'voice' && <div className="voice-view"><AIOrbCSS state={orbState} volume={volume} size={190} onClick={handleVoiceToggle} /><p className="voice-status"><span className={status === 'connected' ? 'pulse' : ''} />{status === 'connected' ? (isAgentSpeaking ? 'जवाब दे रहा हूँ' : isUserSpeaking ? 'सुन रहा हूँ...' : 'माइक सक्रिय है · अपनी बात कहें') : status === 'connecting' ? 'जुड़ रहे हैं...' : 'ऑर्ब पर टैप करके शुरू करें'}</p></div>}
              {activeTab === 'chat' && <Chat messages={messages} inputText={inputText} setInputText={setInputText} isTyping={isTyping} handleSendMessage={handleSendMessage} chatEndRef={chatEndRef} lastResult={lastResult} />}
              {voiceError && <div className="error-banner"><AlertCircle size={16} /><span>{voiceError}</span><button onClick={() => disconnect()} aria-label="बंद करें"><X size={14} /></button></div>}
            </section>
            <section className="panel market-panel"><div className="panel-header"><div><p className="eyebrow">NEARBY MARKETS</p><h2>नज़दीकी मंडियां</h2></div><button className="text-button">सब देखें <ArrowUpRight size={14} /></button></div><MarketRow name="सीहोर APMC" crop="गेहूं" price="₹ 2,450" change="+4.8%" /><MarketRow name="भोपाल मंडी" crop="गेहूं" price="₹ 2,410" change="+3.2%" /><MarketRow name="विदिशा मंडी" crop="चना" price="₹ 5,860" change="+1.7%" /><div className="market-footer"><ShieldCheck size={14} /> भाव आज सुबह 08:40 बजे अपडेट हुए</div></section>
          </div>
        </main>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, note, trend, positive }) { return <div className="stat-card"><div className="stat-icon"><Icon size={17} /></div><p>{label}</p><strong>{value}</strong><small>{note}</small>{trend && <em className={positive ? 'positive' : ''}>{trend}</em>}</div>; }
function MarketRow({ name, crop, price, change }) { return <div className="market-row"><div className="market-symbol"><Wheat size={15} /></div><div><strong>{name}</strong><small>{crop} · आज का भाव</small></div><div className="market-price"><strong>{price}</strong><small>{change}</small></div></div>; }
function Chat({ messages, inputText, setInputText, isTyping, handleSendMessage, chatEndRef, lastResult }) { return <div className="chat-wrap"><div className="messages">{messages.map((msg, i) => <div key={i} className={`message ${msg.role}`}><div>{msg.text}</div><small>{msg.time}</small></div>)}{isTyping && <div className="message assistant typing">मंडी भाव खोज रहे हैं...</div>}<div ref={chatEndRef} /></div>{lastResult && <div className="result-strip"><div><strong>{lastResult.crop} · {lastResult.district}</strong><small>{lastResult.market}</small></div><b>₹{Number(lastResult.modal_price).toLocaleString('en-IN')}<small>/क्विंटल</small></b></div>}<form className="chat-input" onSubmit={e => { e.preventDefault(); handleSendMessage(); }}><input value={inputText} onChange={e => setInputText(e.target.value)} placeholder="फसल और मंडी लिखें..." /><button disabled={!inputText.trim() || isTyping} aria-label="भेजें"><Send size={16} /></button></form></div>; }
