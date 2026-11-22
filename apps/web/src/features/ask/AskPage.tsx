import React, { useEffect, useRef, useState } from 'react';
import { MicButton } from '../../components/MicButton';
import { BrowserAudioRecorder } from '../../utils/audioRecorder';
import { AnswerCard, AnswerCardData, EvidencePacket } from './AnswerCard';

export const AskPage: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [selectedPlace, setSelectedPlace] = useState<string>(() => {
    try {
      const active = localStorage.getItem('weathergpt_active_place_id');
      if (active) {
        return active.replace('saved_', '').toLowerCase();
      }
    } catch {
      // fallback
    }
    return 'pune';
  });
  const [language, setLanguage] = useState<'en' | 'hi'>('en');
  const [answers, setAnswers] = useState<AnswerCardData[]>([]);
  const [loading, setLoading] = useState(false);

  // Voice recording state
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState(0);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [voiceError, setVoiceError] = useState<string | null>(null);

  const recorderRef = useRef<BrowserAudioRecorder | null>(null);
  const timerRef = useRef<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions = [
    'Will it rain tomorrow in Pune?',
    'Is it going to rain tomorrow in Mumbai?',
    'कल पुणे में बारिश होगी क्या?',
  ];

  // Check voice provider health on mount
  useEffect(() => {
    fetch('/v1/voice/health')
      .then((r) => r.json())
      .then((data) => {
        if (data && (data.status === 'ok' || data.configured === true)) {
          setVoiceAvailable(true);
        } else {
          setVoiceAvailable(false);
        }
      })
      .catch(() => setVoiceAvailable(false));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recorderRef.current) {
        recorderRef.current.cancel();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const handleAsk = async (queryText: string) => {
    const q = queryText.trim();
    if (!q || loading) return;

    setLoading(true);
    setVoiceError(null);
    setLiveTranscript('');
    const cardId = `ans_${Date.now()}`;
    const newCard: AnswerCardData = {
      id: cardId,
      question: q,
      text: '',
      timestamp: new Date().toLocaleTimeString(),
      evidencePackets: [],
    };

    setAnswers((prev) => [newCard, ...prev]);

    try {
      const response = await fetch('/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: 'web_session',
          text: q,
          place_id: selectedPlace ? selectedPlace.toLowerCase() : undefined,
          language: language,
          stream: true,
        }),
      });

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedText = '';
      const gatheredPackets: EvidencePacket[] = [];
      let headline = '';
      let keyValues: Record<string, string> | undefined;
      let sourceLine = '';
      let caveat = '';
      let actions: string[] | undefined;
      let needsConfirmation = false;
      let guidanceCards: any[] | undefined;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = '';
        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event: ')) {
            currentEvent = trimmed.replace('event: ', '').trim();
          } else if (trimmed.startsWith('data: ') && currentEvent) {
            try {
              const data = JSON.parse(trimmed.replace('data: ', '').trim());
              if (currentEvent === 'token') {
                accumulatedText += data.text;
              } else if (currentEvent === 'evidence') {
                gatheredPackets.push(data);
              } else if (currentEvent === 'card') {
                headline = data.headline;
                keyValues = data.key_values;
                sourceLine = data.source_line;
                caveat = data.caveat;
                actions = data.actions;
                needsConfirmation = !!data.needs_confirmation;
                guidanceCards = data.guidance_cards;
              }

              // Update the active card in state
              setAnswers((prev) =>
                prev.map((c) =>
                  c.id === cardId
                    ? {
                        ...c,
                        text: accumulatedText,
                        headline: headline || c.headline,
                        keyValues: keyValues || c.keyValues,
                        sourceLine: sourceLine || c.sourceLine,
                        caveat: caveat || c.caveat,
                        actions: actions || c.actions,
                        needsConfirmation: needsConfirmation ?? c.needsConfirmation,
                        guidanceCards: guidanceCards || c.guidanceCards,
                        evidencePackets: gatheredPackets,
                      }
                    : c
                )
              );
            } catch {
              // Ignore partial chunk parse error
            }
          }
        }
      }
    } catch {
      setAnswers((prev) =>
        prev.map((c) =>
          c.id === cardId
            ? {
                ...c,
                text: 'Sorry, there was a problem connecting to official weather feeds. Please check your connection and retry.',
              }
            : c
        )
      );
    } finally {
      setLoading(false);
      setQuestion('');
    }
  };

  const startRecording = async () => {
    if (isListening || isProcessingVoice) return;
    setVoiceError(null);
    setLiveTranscript(language === 'hi' ? 'सुन रहे हैं... बोलिए' : 'Listening... speak now');
    setRecordingSeconds(0);

    try {
      const recorder = new BrowserAudioRecorder({
        onVolumeChange: (vol) => setVolumeLevel(vol),
        onError: (err) => {
          setVoiceError(err.message);
          stopRecording();
        },
      });
      recorderRef.current = recorder;
      await recorder.start();
      setIsListening(true);

      timerRef.current = window.setInterval(() => {
        setRecordingSeconds((s) => s + 1);
      }, 1000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not access microphone.';
      setVoiceError(`Microphone error: ${msg}. Please type your question.`);
      setIsListening(false);
      setLiveTranscript('');
      inputRef.current?.focus();
    }
  };

  const stopRecording = async () => {
    if (!isListening || !recorderRef.current) return;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    setIsListening(false);
    setIsProcessingVoice(true);
    setLiveTranscript(language === 'hi' ? 'पहचान रहे हैं...' : 'Transcribing voice...');

    try {
      const audioWavBlob = await recorderRef.current.stop();
      recorderRef.current = null;

      // Send audio to /v1/voice/transcribe
      const formData = new FormData();
      formData.append('audio', audioWavBlob, 'recording.wav');
      formData.append('language', language);

      const resp = await fetch('/v1/voice/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (!resp.ok) {
        throw new Error(`Speech service returned ${resp.status}`);
      }

      const resJson = await resp.json();
      const transcribedText = resJson.text?.trim() || '';

      if (transcribedText) {
        setLiveTranscript(`"${transcribedText}"`);
        handleAsk(transcribedText);
      } else {
        setLiveTranscript('');
        setVoiceError(language === 'hi' ? 'आवाज़ सुनाई नहीं दी, कृपया दोबारा बोलें या लिखकर पूछें।' : 'No speech detected. Please speak again or type.');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Transcription failed';
      setVoiceError(`${msg}. Falling back to typing.`);
      setLiveTranscript('');
      inputRef.current?.focus();
    } finally {
      setIsProcessingVoice(false);
      setVolumeLevel(0);
    }
  };

  const toggleRecording = () => {
    if (isListening) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="max-w-column mx-auto px-4 py-4 pb-28">
      {/* Top Header bar with Location Chip and Language Switch */}
      <header className="flex items-center justify-between gap-2 pb-3 mb-4 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-full text-xs font-semibold text-slate-700 shadow-sm">
            <svg className="w-3.5 h-3.5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
            </svg>
            <label htmlFor="place-select" className="sr-only">Select location</label>
            <select
              id="place-select"
              value={selectedPlace}
              onChange={(e) => {
                setSelectedPlace(e.target.value);
                localStorage.setItem('weathergpt_active_place_id', e.target.value);
              }}
              className="bg-transparent border-none text-xs font-semibold text-slate-700 focus:outline-none cursor-pointer capitalize"
            >
              <option value="pune">Pune</option>
              <option value="mumbai">Mumbai</option>
              <option value="delhi">Delhi</option>
              <option value="bengaluru">Bengaluru</option>
              <option value="chennai">Chennai</option>
              <option value="kolkata">Kolkata</option>
              <option value="hyderabad">Hyderabad</option>
              <option value="ahmedabad">Ahmedabad</option>
              <option value="jaipur">Jaipur</option>
              <option value="lucknow">Lucknow</option>
            </select>
          </div>
        </div>

        {/* Language switcher */}
        <div className="flex rounded-lg border border-slate-200 bg-white p-0.5 text-xs font-medium">
          <button
            type="button"
            onClick={() => setLanguage('en')}
            className={`px-2.5 py-1 rounded-md transition ${language === 'en' ? 'bg-blue-600 text-white font-semibold' : 'text-slate-600 hover:text-slate-900'}`}
          >
            EN
          </button>
          <button
            type="button"
            onClick={() => setLanguage('hi')}
            className={`px-2.5 py-1 rounded-md transition ${language === 'hi' ? 'bg-blue-600 text-white font-semibold' : 'text-slate-600 hover:text-slate-900'}`}
          >
            हिन्दी
          </button>
        </div>
      </header>

      {/* Suggestion Chips */}
      <div className="flex gap-2 overflow-x-auto pb-2 mb-4 scrollbar-none" aria-label="Suggested questions">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => handleAsk(s)}
            className="whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition flex-shrink-0"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Voice Error Notice */}
      {voiceError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-800 rounded-xl text-xs flex items-center justify-between">
          <span>{voiceError}</span>
          <button
            type="button"
            onClick={() => setVoiceError(null)}
            className="font-bold text-red-700 hover:text-red-900 ml-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* Live Voice Transcript Banner */}
      {liveTranscript && (
        <div
          className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-xl text-sm font-medium text-blue-900 flex items-center gap-2 shadow-sm animate-fade-in"
          aria-live="polite"
        >
          <span className="w-2.5 h-2.5 rounded-full bg-blue-600 animate-ping" />
          <span>{liveTranscript}</span>
        </div>
      )}

      {/* Answer Cards Thread */}
      <main className="space-y-4">
        {answers.length === 0 && (
          <div className="text-center py-12 px-4 text-slate-500">
            <div className="w-12 h-12 mx-auto mb-3 text-slate-400">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-base font-medium">Ask any question about weather across India</p>
            <p className="text-xs text-slate-400 mt-1">
              {voiceAvailable
                ? (language === 'hi' ? 'उदा. "कल पुणे में बारिश होगी क्या?" या माइक दबाएं' : 'E.g., "Will it rain tomorrow in Pune?" or tap the microphone')
                : (language === 'hi' ? 'उदा. "कल पुणे में बारिश होगी क्या?"' : 'E.g., "Will it rain tomorrow in Pune?"')}
            </p>
          </div>
        )}

        {answers.map((card) => (
          <AnswerCard
            key={card.id}
            data={card}
            language={language}
            onActionClick={(actionText) => handleAsk(actionText)}
          />
        ))}
      </main>

      {/* Fixed Bottom Input Area */}
      <div className="fixed bottom-14 left-0 right-0 p-3 bg-gradient-to-t from-slate-50 via-slate-50/90 to-transparent">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk(question);
          }}
          className="max-w-column mx-auto flex items-center gap-2 bg-white rounded-2xl shadow-lg border border-slate-200 p-1.5"
        >
          <input
            ref={inputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={
              voiceAvailable
                ? (language === 'hi' ? 'अपना प्रश्न पूछें या माइक दबाएं...' : 'Type or hold mic to speak...')
                : (language === 'hi' ? 'अपना प्रश्न पूछें...' : 'Type your question...')
            }
            disabled={loading || isListening || isProcessingVoice}
            className="flex-1 px-3 py-2 text-base rounded-xl outline-none text-slate-900 placeholder:text-slate-400 bg-transparent min-h-[48px]"
          />

          {/* Voice Input Push-to-Talk MicButton (only rendered when live voice provider configured) */}
          {voiceAvailable && (
            <MicButton
              isListening={isListening}
              isProcessing={isProcessingVoice}
              volumeLevel={volumeLevel}
              recordingSeconds={recordingSeconds}
              onClick={toggleRecording}
              onPointerDown={(e) => {
                // Push to talk on pointer hold
                if (e.pointerType === 'touch' || e.pointerType === 'mouse') {
                  startRecording();
                }
              }}
              onPointerUp={() => {
                if (isListening) {
                  stopRecording();
                }
              }}
            />
          )}

          {/* Send Button */}
          <button
            type="submit"
            disabled={!question.trim() || loading || isListening || isProcessingVoice}
            className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed hover:bg-blue-700 transition flex-shrink-0"
            aria-label="Send question"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
};
