// frontend/src/components/features/CitizenChat.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Send, ShieldAlert, Languages, AlertTriangle, ArrowRight, User, Bot, HelpCircle, FileText, CheckCircle2 } from 'lucide-react';
import { api } from '../../services/api';

export const CitizenChat = () => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([
    {
      role: 'assistant',
      text: 'Hello! I am ShieldAI\'s Citizen Fraud Shield. If you think someone is trying to scam you, tell me what happened in any language (English, Hindi, Telugu, Hinglish, etc.). I will evaluate it instantly.',
      isSystem: true
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState('en');
  const [reportingMsgIndex, setReportingMsgIndex] = useState(null);
  const [reportForm, setReportForm] = useState({ phone: '', location: '', email: '' });
  const [reportResult, setReportResult] = useState(null);
  const [isSubmittingReport, setIsSubmittingReport] = useState(false);
  const [sessionId] = useState(() => {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return `sess-${crypto.randomUUID()}`;
    }
    return `sess-${Math.random().toString(36).substring(2, 9)}-${Math.random().toString(36).substring(2, 9)}`;
  });
  const chatEndRef = useRef(null);

  const demoScams = [
    {
      title: 'CBI Video Call Scam (Hinglish)',
      text: 'Mujhe CBI officer Rajesh Kumar ka call aaya Skype pe. Bol rahe hain ki mera Aadhaar drug trafficking case me linked hai. Unhone video call lock kar diya hai aur keh rahe hain 2 lakh transfer karo verification ke liye warna arrest ho jayega. Main bohot dara hu, kya karu?'
    },
    {
      title: 'TRAI Sim Block Threat (English)',
      text: 'Got a call from TRAI saying my SIM will be deactivated in 2 hours because a mobile number registered on my name is sending illegal spam messages. They connected me to Mumbai police who asked for bank details to verify. Is this real?'
    },
    {
      title: 'Investment Group (English)',
      text: 'Added to a WhatsApp group for stock tips. They asked me to download an app called "BullTrade" and transfer Rs 50,000. I can see 3x returns in app but they won\'t let me withdraw unless I pay 20% commission.'
    }
  ];

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, loading]);

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!message.trim() || loading) return;

    // Simple sanitization against basic XSS vectors
    const sanitize = (str) => str.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const userText = sanitize(message.trim());
    
    setMessage('');
    setChatHistory((prev) => [...prev, { role: 'user', text: userText }]);
    setLoading(true);

    try {
      const data = await api.sendChatMessage(userText, sessionId, language);
      
      const newResponse = {
        role: 'assistant',
        text: data.response,
        risk: data.risk_assessment,
        report_link: data.report_link,
        original_user_text: userText
      };
      
      setChatHistory((prev) => [...prev, newResponse]);
    } catch (err) {
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'Sorry, I encountered an issue connecting to the safety server. If you are in immediate danger or an active scam, please hang up and call the Cyber Helpline at 1930 immediately.',
          isError: true
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleDemoClick = (text) => {
    setMessage(text);
  };

  const handleReportSubmit = async (e, description, msgIndex) => {
    e.preventDefault();
    setIsSubmittingReport(true);
    try {
      const result = await api.submitReport(
        description,
        reportForm.phone,
        reportForm.location,
        reportForm.email
      );
      setReportResult({ ...result, msgIndex });
      setReportingMsgIndex(null);
    } catch (error) {
      console.error("Failed to submit report:", error);
      alert("Failed to submit report. Please try again.");
    } finally {
      setIsSubmittingReport(false);
    }
  };

  return (
    <div className="glass-panel animate-slide-in" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: '550px', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-glass)', background: 'rgba(255,255,255,0.02)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: 'var(--accent-cyan-glow)', border: '1px solid var(--accent-cyan)', padding: '8px', borderRadius: '10px' }}>
            <ShieldAlert size={20} color="#06b6d4" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', color: 'var(--text-primary)' }}>Citizen Fraud Shield</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--accent-green)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--accent-green)', display: 'inline-block' }}></span>
              AI Agent Active
            </span>
          </div>
        </div>
        
        {/* Language select */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-tertiary)', padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
          <Languages size={14} color="var(--text-secondary)" />
          <select 
            value={language} 
            onChange={(e) => setLanguage(e.target.value)}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-primary)', outline: 'none', cursor: 'pointer', fontFamily: 'var(--font-body)', fontSize: '0.85rem' }}
          >
            <option value="en" style={{ backgroundColor: 'var(--bg-secondary)' }}>English</option>
            <option value="hi" style={{ backgroundColor: 'var(--bg-secondary)' }}>Hinglish / Hindi</option>
            <option value="te" style={{ backgroundColor: 'var(--bg-secondary)' }}>Telugu</option>
            <option value="ta" style={{ backgroundColor: 'var(--bg-secondary)' }}>Tamil</option>
          </select>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {chatHistory.map((msg, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
              <div style={{ 
                width: '32px', 
                height: '32px', 
                borderRadius: '50%', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                background: msg.role === 'user' ? 'var(--accent-purple-glow)' : 'var(--accent-cyan-glow)',
                border: `1px solid ${msg.role === 'user' ? 'var(--accent-purple)' : 'var(--accent-cyan)'}`
              }}>
                {msg.role === 'user' ? <User size={14} color="#8b5cf6" /> : <Bot size={14} color="#06b6d4" />}
              </div>

              <div style={{ 
                padding: '12px 16px', 
                borderRadius: msg.role === 'user' ? '16px 4px 16px 16px' : '4px 16px 16px 16px', 
                background: msg.role === 'user' ? 'var(--accent-purple-glow)' : 'var(--bg-tertiary)',
                border: '1px solid',
                borderColor: msg.role === 'user' ? 'rgba(139,92,246,0.2)' : 'var(--border-glass)',
                color: 'var(--text-primary)',
                fontSize: '0.95rem',
                lineHeight: '1.5',
                whiteSpace: 'pre-wrap'
              }}>
                {msg.text}
                
                {/* Risk assessment alert container */}
                {msg.risk && msg.risk.detected_risk && (
                  <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-red)', fontWeight: 'bold', fontSize: '0.85rem', marginBottom: '4px' }}>
                      <AlertTriangle size={16} />
                      WARNING: CONFIRMED {msg.risk.fraud_type?.replace('_', ' ').toUpperCase()} SCAM
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                      Severity: <strong>{msg.risk.risk_level}</strong> (Confidence: {Math.round(msg.risk.confidence * 100)}%)
                    </p>
                    
                    {msg.report_link && !reportResult?.msgIndex && reportingMsgIndex !== i && (
                      <button 
                        onClick={() => setReportingMsgIndex(i)}
                        style={{
                          background: 'var(--accent-red)',
                          color: '#fff',
                          border: 'none',
                          padding: '6px 12px',
                          borderRadius: '6px',
                          fontSize: '0.8rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontWeight: 'bold'
                        }}
                      >
                        <FileText size={14} /> Report Incident to Cyber Cell
                      </button>
                    )}

                    {reportingMsgIndex === i && (
                      <form onSubmit={(e) => handleReportSubmit(e, msg.original_user_text || "Scam reported", i)} style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px', background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                        <h4 style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-primary)' }}>File Official Report</h4>
                        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '0 0 8px 0' }}>Provide optional details to help authorities track this scammer.</p>
                        <input type="text" placeholder="Scammer's Phone (Optional)" value={reportForm.phone} onChange={e => setReportForm({...reportForm, phone: e.target.value})} style={{ padding: '8px', borderRadius: '4px', border: '1px solid var(--border-glass)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '0.8rem' }} />
                        <input type="text" placeholder="Your City/Location (Optional)" value={reportForm.location} onChange={e => setReportForm({...reportForm, location: e.target.value})} style={{ padding: '8px', borderRadius: '4px', border: '1px solid var(--border-glass)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '0.8rem' }} />
                        <input type="email" placeholder="Your Email (Optional)" value={reportForm.email} onChange={e => setReportForm({...reportForm, email: e.target.value})} style={{ padding: '8px', borderRadius: '4px', border: '1px solid var(--border-glass)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '0.8rem' }} />
                        <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                          <button type="submit" disabled={isSubmittingReport} style={{ flex: 1, background: 'var(--accent-red)', color: '#fff', border: 'none', padding: '8px', borderRadius: '4px', fontSize: '0.8rem', cursor: isSubmittingReport ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}>
                            {isSubmittingReport ? 'Submitting...' : 'Submit Report'}
                          </button>
                          <button type="button" onClick={() => setReportingMsgIndex(null)} style={{ padding: '8px 12px', background: 'transparent', border: '1px solid var(--border-glass)', color: 'var(--text-secondary)', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>Cancel</button>
                        </div>
                      </form>
                    )}

                    {reportResult?.msgIndex === i && (
                      <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(34, 197, 94, 0.1)', border: '1px solid rgba(34, 197, 94, 0.3)', borderRadius: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-green)', fontWeight: 'bold', fontSize: '0.85rem', marginBottom: '8px' }}>
                          <CheckCircle2 size={16} /> Report Submitted Successfully
                        </div>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-primary)', margin: '0 0 4px 0' }}>Reference: <strong>{reportResult.reference_number}</strong></p>
                        <ul style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0, paddingLeft: '16px' }}>
                          {reportResult.next_steps.slice(0, 3).map((step, idx) => <li key={idx}>{step}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', gap: '8px', alignSelf: 'flex-start' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--accent-cyan-glow)', border: '1px solid var(--accent-cyan)' }}>
              <Bot size={14} color="#06b6d4" />
            </div>
            <div style={{ padding: '12px 20px', borderRadius: '4px 16px 16px 16px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-glass)' }}>
              <div style={{ display: 'flex', gap: '4px', padding: '4px' }}>
                <span className="dot" style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%', animation: 'pulse-glow 1s infinite alternate' }}></span>
                <span className="dot" style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%', animation: 'pulse-glow 1s infinite alternate', animationDelay: '0.2s' }}></span>
                <span className="dot" style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%', animation: 'pulse-glow 1s infinite alternate', animationDelay: '0.4s' }}></span>
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Demo shortcuts */}
      <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border-glass)', background: 'rgba(0,0,0,0.1)' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
          <HelpCircle size={12} color="var(--accent-cyan)" />
          Quick Demo Scripts (Click to load):
        </span>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {demoScams.map((demo, idx) => (
            <button
              key={idx}
              onClick={() => handleDemoClick(demo.text)}
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border-glass)',
                padding: '6px 12px',
                borderRadius: '8px',
                color: 'var(--text-primary)',
                fontSize: '0.8rem',
                cursor: 'pointer',
                transition: 'var(--transition-smooth)'
              }}
              onMouseOver={(e) => { e.currentTarget.style.borderColor = 'var(--accent-cyan)'; e.currentTarget.style.background = 'var(--accent-cyan-glow)'; }}
              onMouseOut={(e) => { e.currentTarget.style.borderColor = 'var(--border-glass)'; e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
            >
              {demo.title}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <form onSubmit={handleSend} style={{ display: 'flex', padding: '16px 20px', borderTop: '1px solid var(--border-glass)', gap: '12px', background: 'var(--bg-secondary)' }}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Describe your situation here (e.g. 'I got a call saying I will be arrested...')"
          style={{
            flex: 1,
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-glass)',
            padding: '12px 16px',
            borderRadius: '12px',
            color: 'var(--text-primary)',
            outline: 'none',
            fontSize: '0.95rem',
            fontFamily: 'var(--font-body)',
            transition: 'var(--transition-smooth)'
          }}
          disabled={loading}
          onFocus={(e) => e.target.style.borderColor = 'var(--accent-cyan)'}
          onBlur={(e) => e.target.style.borderColor = 'var(--border-glass)'}
        />
        <button
          type="submit"
          disabled={loading || !message.trim()}
          style={{
            background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))',
            border: 'none',
            padding: '0 18px',
            borderRadius: '12px',
            color: '#fff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'var(--transition-smooth)',
            opacity: message.trim() ? 1 : 0.6
          }}
        >
          <Send size={18} />
        </button>
      </form>
    </div>
  );
};
export default CitizenChat;
