import React, { useState } from 'react';

export interface AlertData {
  id: string;
  sender: string;
  sent: string;
  hazard: string;
  severity: 'Extreme' | 'Severe' | 'Moderate' | 'Minor' | 'Unknown';
  urgency: string;
  certainty: string;
  onset: string;
  expires: string;
  areas: Array<{ areaDesc: string; polygon?: string }>;
  text_by_language: Record<string, string>;
  source_url: string;
  authority_tier: number;
  level: 'green' | 'yellow' | 'orange' | 'red';
}

interface AlertCardProps {
  alert: AlertData;
  lang?: 'en' | 'hi';
}

const LEVEL_STYLES: Record<string, { bg: string; text: string; labelEn: string; labelHi: string; icon: string }> = {
  red: {
    bg: 'bg-alert-red',
    text: 'text-white',
    labelEn: 'Warning: Take Action',
    labelHi: 'चेतावनी: कार्रवाई करें',
    icon: '🚨',
  },
  orange: {
    bg: 'bg-alert-orange',
    text: 'text-slate-900',
    labelEn: 'Alert: Be Prepared',
    labelHi: 'अलर्ट: तैयार रहें',
    icon: '⚠️',
  },
  yellow: {
    bg: 'bg-alert-yellow',
    text: 'text-slate-900',
    labelEn: 'Watch: Stay Aware',
    labelHi: 'निगरानी: सतर्क रहें',
    icon: '⚡',
  },
  green: {
    bg: 'bg-alert-green',
    text: 'text-white',
    labelEn: 'No Warning',
    labelHi: 'कोई चेतावनी नहीं',
    icon: '✅',
  },
};

export const AlertCard: React.FC<AlertCardProps> = ({ alert, lang = 'en' }) => {
  const [showAdvice, setShowAdvice] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  const style = LEVEL_STYLES[alert.level] || LEVEL_STYLES.yellow;
  const areaName = alert.areas.map((a) => a.areaDesc).filter(Boolean).join(', ') || 'Your Area';
  const alertText = alert.text_by_language[lang] || alert.text_by_language.en || `${alert.hazard} alert for ${areaName}`;

  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' IST';
    } catch {
      return ts;
    }
  };

  const handleListen = () => {
    if ('speechSynthesis' in window) {
      if (speaking) {
        window.speechSynthesis.cancel();
        setSpeaking(false);
        return;
      }
      const utterance = new SpeechSynthesisUtterance(alertText);
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      setSpeaking(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden mb-4 transition-all hover:shadow-md">
      {/* Top Banner with Level Token, Icon, and Word */}
      <div className={`px-4 py-2.5 flex items-center justify-between ${style.bg} ${style.text}`}>
        <div className="flex items-center space-x-2 font-bold text-sm tracking-wide">
          <span aria-hidden="true" className="text-base">{style.icon}</span>
          <span>{lang === 'hi' ? style.labelHi : style.labelEn}</span>
        </div>
        <span className="text-xs uppercase tracking-wider font-semibold opacity-90">
          Official Alert
        </span>
      </div>

      <div className="p-4 space-y-3">
        {/* Hazard Headline and Place */}
        <div>
          <h3 className="text-lg font-bold text-slate-900 leading-snug">
            {alert.hazard} in {areaName}
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Issued by {alert.sender} via SACHET • {formatTime(alert.sent)} (Valid until {formatTime(alert.expires)})
          </p>
        </div>

        {/* Official Message Body */}
        <p className="text-sm text-slate-800 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
          {alertText}
        </p>

        {/* Action Buttons: Listen & Advice Toggle */}
        <div className="flex items-center justify-between pt-1 text-xs">
          <button
            type="button"
            onClick={handleListen}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium transition-colors"
          >
            <span>{speaking ? '⏹️ Stop' : '🔊 Listen'}</span>
          </button>

          <button
            type="button"
            onClick={() => setShowAdvice(!showAdvice)}
            className="text-blue-600 hover:text-blue-800 font-semibold focus:outline-none focus:underline"
          >
            {showAdvice ? 'Hide advice ▲' : 'What officials advise ▼'}
          </button>
        </div>

        {/* Expandable Advice Section */}
        {showAdvice && (
          <div className="border-t border-slate-100 pt-3 text-xs text-slate-600 bg-blue-50/50 p-3 rounded-lg">
            <h4 className="font-semibold text-slate-800 mb-1">
              {lang === 'hi' ? 'अधिकारियों की सलाह:' : 'What officials advise:'}
            </h4>
            <p className="leading-relaxed">
              {lang === 'hi'
                ? 'स्थानीय प्रशासन के निर्देशों का पालन करें। सुरक्षित आश्रय में रहें और बिजली के उपकरणों से दूर रहें।'
                : 'Follow instructions from your local disaster management authority. Stay indoors during thunderstorms, keep away from electrical poles and ungrounded structures.'}
            </p>
            <p className="mt-2 text-slate-400">
              Source:{' '}
              <a
                href={alert.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-slate-600"
              >
                Official NDMA CAP Broadcast
              </a>
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
