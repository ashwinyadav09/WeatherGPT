import React, { useEffect, useRef, useState } from 'react';
import { ShareModal } from '../share/ShareModal';

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

export interface GuidanceCard {
  id: string;
  hazard: string;
  title: string;
  items: string[];
  source_title: string;
  source_url: string;
  retrieved_on?: string;
  reviewed?: boolean;
}

export interface AnswerCardData {
  id: string;
  question: string;
  text: string;
  headline?: string;
  keyValues?: Record<string, string>;
  sourceLine?: string;
  caveat?: string;
  actions?: string[];
  needsConfirmation?: boolean;
  guidanceCards?: GuidanceCard[];
  evidencePackets?: EvidencePacket[];
  timestamp: string;
}

interface AnswerCardProps {
  data: AnswerCardData;
  language?: 'en' | 'hi';
  onActionClick?: (actionText: string) => void;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({
  data,
  language = 'en',
  onActionClick,
}) => {
  const [showEvidence, setShowEvidence] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<0.8 | 1.0>(1.0);
  const [isShareOpen, setIsShareOpen] = useState(false);
  const [audioLoading, setAudioLoading] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handleListen = async () => {
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      return;
    }

    if (audioRef.current) {
      audioRef.current.playbackRate = playbackSpeed;
      audioRef.current.play();
      setIsPlaying(true);
      return;
    }

    setAudioLoading(true);

    try {
      // Fetch high-quality natural spoken speech from backend Speech Gateway
      const resp = await fetch('/v1/voice/speak', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: data.text,
          language: language,
          voice: 'female',
        }),
      });

      if (!resp.ok) {
        throw new Error('Speech synthesis endpoint failed');
      }

      const blob = await resp.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audio.playbackRate = playbackSpeed;

      audio.onended = () => {
        setIsPlaying(false);
      };

      audio.onerror = () => {
        setIsPlaying(false);
        fallbackSpeechSynthesis();
      };

      audioRef.current = audio;
      await audio.play();
      setIsPlaying(true);
    } catch {
      fallbackSpeechSynthesis();
    } finally {
      setAudioLoading(false);
    }
  };

  const fallbackSpeechSynthesis = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(data.text);
      utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
      utterance.rate = playbackSpeed;
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => setIsPlaying(false);
      setIsPlaying(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleReplay = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.playbackRate = playbackSpeed;
      audioRef.current.play();
      setIsPlaying(true);
    } else {
      handleListen();
    }
  };

  const toggleSpeed = () => {
    const newSpeed = playbackSpeed === 1.0 ? 0.8 : 1.0;
    setPlaybackSpeed(newSpeed);
    if (audioRef.current) {
      audioRef.current.playbackRate = newSpeed;
    }
  };

  const handleShare = () => {
    setIsShareOpen(true);
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
        {/* Weather Icon */}
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

      {/* Official Guidance Cards (Drawn from NDMA/IMD library with neutral dashed border per docs/ui-spec.md) */}
      {data.guidanceCards && data.guidanceCards.length > 0 && (
        <div className="my-3 space-y-3">
          {data.guidanceCards.map((gc) => (
            <div
              key={gc.id}
              className="border-2 border-dashed border-slate-300 bg-slate-50 rounded-xl p-4 text-xs space-y-2 text-slate-800"
            >
              <div className="flex items-center justify-between gap-2 border-b border-slate-200 pb-2">
                <span className="font-bold text-sm text-slate-900">{gc.title}</span>
                <span className="px-2 py-0.5 rounded bg-slate-200 text-slate-700 text-[10px] uppercase font-semibold">
                  Official Guidance
                </span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-slate-700">
                {gc.items.map((item, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {item}
                  </li>
                ))}
              </ul>
              <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-500 flex items-center justify-between">
                <span>Source: {gc.source_title}</span>
                {gc.source_url && (
                  <a
                    href={gc.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    View Official Document
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Place Confirmation & Action Buttons if clarification needed */}
      {data.actions && data.actions.length > 0 && (
        <div className="my-3 p-3 bg-amber-50 rounded-xl border border-amber-200">
          <p className="text-xs font-semibold text-amber-900 mb-2">
            {data.needsConfirmation
              ? (language === 'hi' ? 'पुष्टि करें (हाँ या नहीं कहें):' : 'Confirm place (say Yes or No):')
              : (language === 'hi' ? 'विकल्प चुनें:' : 'Select an option:')}
          </p>
          <div className="flex flex-wrap gap-2">
            {data.actions.map((act) => (
              <button
                key={act}
                type="button"
                onClick={() => onActionClick && onActionClick(act)}
                className="px-4 py-2 rounded-lg text-sm font-semibold bg-white border border-amber-300 text-amber-900 shadow-sm hover:bg-amber-100 min-h-[44px]"
              >
                {act}
              </button>
            ))}
          </div>
        </div>
      )}

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
        {/* Listen / Pause button */}
        <button
          onClick={handleListen}
          type="button"
          disabled={audioLoading}
          className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg min-h-[44px] transition ${
            isPlaying ? 'bg-blue-600 text-white' : 'text-slate-700 bg-slate-100 hover:bg-slate-200'
          }`}
          aria-label={isPlaying ? 'Pause audio' : 'Listen to spoken answer'}
        >
          {audioLoading ? (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M12 18.75a6.75 6.75 0 01-6.75-6.75A6.75 6.75 0 0112 5.25v13.5z" />
            </svg>
          )}
          {isPlaying ? (language === 'hi' ? 'रोकें' : 'Pause') : (language === 'hi' ? 'सुनें' : 'Listen')}
        </button>

        {/* Replay button */}
        <button
          onClick={handleReplay}
          type="button"
          className="inline-flex items-center gap-1 px-2.5 py-2 text-sm font-medium rounded-lg text-slate-700 bg-slate-100 hover:bg-slate-200 min-h-[44px]"
          aria-label="Replay speech"
          title="Replay from beginning"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>{language === 'hi' ? 'दोबारा' : 'Replay'}</span>
        </button>

        {/* Slow-down speed toggle (1.0x vs 0.8x) */}
        <button
          onClick={toggleSpeed}
          type="button"
          className={`inline-flex items-center px-2.5 py-2 text-xs font-semibold rounded-lg min-h-[44px] transition ${
            playbackSpeed === 0.8 ? 'bg-amber-100 text-amber-900 border border-amber-300' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          }`}
          aria-label={`Playback speed: ${playbackSpeed}x. Tap to switch.`}
          title="Toggle slow-down speed"
        >
          {playbackSpeed === 0.8 ? '0.8x (Slow)' : '1.0x'}
        </button>

        {/* Share button */}
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

        {/* Why this answer evidence expansion */}
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

      {/* Share Modal Dialog with Link & Image Card */}
      <ShareModal
        isOpen={isShareOpen}
        onClose={() => setIsShareOpen(false)}
        data={{
          headline: data.headline || 'Weather Forecast',
          keyNumber: data.keyValues ? Object.values(data.keyValues).join(' • ') : '',
          placeName: data.evidencePackets?.[0]?.place?.name || 'Local Area',
          sourceLine: data.sourceLine || 'Open-Meteo (model data)',
          issuedAt: data.timestamp,
          caveat: data.caveat,
        }}
      />
    </article>
  );
};
