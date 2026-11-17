import React, { useState } from 'react';

export interface EvidencePacket {
  id: string;
  source: string;
  authority_tier: number;
  provenance: string;
  issued_at: string;
  valid_from: string;
  valid_to: string;
  place: {
    id: string;
    name: string;
    lat: number;
    lon: number;
  };
  values: Array<{
    variable: string;
    value: number | string | null;
    unit: string;
  }>;
  attribution: string;
  fetched_at: string;
}

export interface AnswerCardData {
  id: string;
  question: string;
  text: string;
  headline?: string;
  keyValues?: Record<string, string>;
  sourceLine?: string;
  caveat?: string;
  evidencePackets?: EvidencePacket[];
  timestamp: string;
}

interface AnswerCardProps {
  data: AnswerCardData;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({ data }) => {
  const [showEvidence, setShowEvidence] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  const handleListen = () => {
    if ('speechSynthesis' in window) {
      if (speaking) {
        window.speechSynthesis.cancel();
        setSpeaking(false);
        return;
      }
      const utterance = new SpeechSynthesisUtterance(data.text);
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      setSpeaking(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'WeatherGPT Update',
          text: data.text,
          url: window.location.href,
        });
      } catch {
        // User cancelled or share failed
      }
    } else {
      await navigator.clipboard.writeText(data.text);
      alert('Answer copied to clipboard!');
    }
  };

  return (
    <article
      className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 mb-4 max-w-column mx-auto"
      aria-live="polite"
    >
      {/* Question header */}
      <div className="text-sm font-medium text-slate-500 mb-2">
        {data.question}
      </div>

      {/* Headline & Key Number */}
      <div className="flex items-center justify-between gap-4 mb-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            {data.headline || 'Forecast Summary'}
          </h2>
          {data.keyValues && (
            <div className="flex gap-4 mt-2">
              {Object.entries(data.keyValues).map(([k, v]) => (
                <div key={k} className="bg-blue-50 px-3 py-1.5 rounded-lg border border-blue-100">
                  <span className="text-xs text-slate-500 block uppercase font-medium">{k}</span>
                  <span className="text-lg font-bold text-blue-900">{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        {/* Weather Icon (Cloud/Sun SVG) */}
        <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 flex-shrink-0" aria-hidden="true">
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
          </svg>
        </div>
      </div>

      {/* Answer narrative text */}
      <p className="text-base text-slate-800 leading-relaxed mb-3">
        {data.text}
      </p>

      {/* Source Line & Caveat */}
      <div className="border-t border-slate-100 pt-3 text-xs text-slate-500 space-y-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-600">Model guidance:</span>
          <span>{data.sourceLine || 'Data: Open-Meteo (CC BY 4.0)'}</span>
        </div>
        <div className="text-amber-700 bg-amber-50 px-2 py-1 rounded inline-block">
          {data.caveat || 'Official IMD forecast is not connected yet'}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap items-center gap-2 mt-4 pt-2 border-t border-slate-100">
        <button
          onClick={handleListen}
          type="button"
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg text-slate-700 bg-slate-100 hover:bg-slate-200 min-h-[44px]"
          aria-label={speaking ? 'Stop listening' : 'Listen to answer'}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M12 18.75a6.75 6.75 0 01-6.75-6.75A6.75 6.75 0 0112 5.25v13.5z" />
          </svg>
          {speaking ? 'Stop' : 'Listen'}
        </button>

        <button
          onClick={handleShare}
          type="button"
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg text-slate-700 bg-slate-100 hover:bg-slate-200 min-h-[44px]"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
          Share
        </button>

        <button
          onClick={() => setShowEvidence(!showEvidence)}
          type="button"
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg text-blue-700 bg-blue-50 hover:bg-blue-100 min-h-[44px] ml-auto"
        >
          Why this answer?
        </button>
      </div>

      {/* Expandable Evidence Packet Viewer */}
      {showEvidence && (
        <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-2">
          <h4 className="font-semibold text-slate-700">Underlying Evidence Packets</h4>
          {data.evidencePackets && data.evidencePackets.length > 0 ? (
            data.evidencePackets.map((ep) => (
              <div key={ep.id} className="bg-white p-2.5 rounded border border-slate-200">
                <div className="flex justify-between font-medium text-slate-800">
                  <span>Source: {ep.source} (Tier {ep.authority_tier})</span>
                  <span>Provenance: {ep.provenance}</span>
                </div>
                <div className="text-slate-600 mt-1">
                  Place: {ep.place.name} ({ep.place.lat.toFixed(2)}, {ep.place.lon.toFixed(2)})
                </div>
                <div className="text-slate-600 mt-1">
                  Values: {ep.values.map((v) => `${v.variable}: ${v.value} ${v.unit}`).join(', ')}
                </div>
                <div className="text-slate-400 mt-1 text-[11px]">
                  Attribution: {ep.attribution}
                </div>
              </div>
            ))
          ) : (
            <p className="text-slate-500 italic">No raw evidence packets attached.</p>
          )}
        </div>
      )}
    </article>
  );
};
