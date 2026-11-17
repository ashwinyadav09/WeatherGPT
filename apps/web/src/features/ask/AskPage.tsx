import React, { useState } from 'react';
import { AnswerCard, AnswerCardData, EvidencePacket } from './AnswerCard';

export const AskPage: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [selectedPlace] = useState('Pune');
  const [language, setLanguage] = useState<'en' | 'hi'>('en');
  const [answers, setAnswers] = useState<AnswerCardData[]>([]);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);

  const suggestions = [
    'Will it rain tomorrow in Pune?',
    'Is it going to rain tomorrow in Mumbai?',
    'कल पुणे में बारिश होगी क्या?',
  ];

  const handleAsk = async (queryText: string) => {
    const q = queryText.trim();
    if (!q || loading) return;

    setLoading(true);
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
                        evidencePackets: gatheredPackets,
                      }
                    : c
                )
              );
            } catch {
              // Ignore parse error on partial chunks
            }
          }
        }
      }
    } catch (err) {
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

  const toggleMic = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Speech recognition is not supported in this browser. Please type your query.');
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
    recognition.interimResults = false;

    if (!recording) {
      recognition.start();
      setRecording(true);
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setRecording(false);
        handleAsk(transcript);
      };
      recognition.onerror = () => setRecording(false);
      recognition.onend = () => setRecording(false);
    } else {
      setRecording(false);
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
            <span>Place: {selectedPlace}</span>
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
            <p className="text-xs text-slate-400 mt-1">E.g., "Will it rain tomorrow in Pune?"</p>
          </div>
        )}

        {answers.map((card) => (
          <AnswerCard key={card.id} data={card} />
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
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={language === 'hi' ? 'अपना प्रश्न पूछें...' : 'Type your question...'}
            disabled={loading}
            className="flex-1 px-3 py-2 text-base rounded-xl outline-none text-slate-900 placeholder:text-slate-400 bg-transparent min-h-[48px]"
          />

          {/* Voice Input Microphone Button */}
          <button
            type="button"
            onClick={toggleMic}
            className={`w-12 h-12 rounded-xl flex items-center justify-center transition flex-shrink-0 ${
              recording
                ? 'bg-red-600 text-white animate-pulse'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
            aria-label={recording ? 'Stop recording voice' : 'Speak question'}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </button>

          {/* Send Button */}
          <button
            type="submit"
            disabled={!question.trim() || loading}
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
