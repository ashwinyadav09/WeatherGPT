import React, { useState, useEffect } from 'react';
import { useTranslation, LANGUAGES, SupportedLanguage } from '../../i18n/LanguageContext';

const ONBOARDED_KEY = 'weathergpt_first_run_completed';

export const FirstRunLanguagePicker: React.FC = () => {
  const { setLanguage } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const completed = localStorage.getItem(ONBOARDED_KEY);
    if (!completed) {
      setIsOpen(true);
    }
  }, []);

  if (!isOpen) return null;

  const speakLanguageName = (text: string, langCode: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = langCode === 'hi' ? 'hi-IN' : 'en-IN';
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleSelectLanguage = (lang: SupportedLanguage) => {
    setLanguage(lang);
    localStorage.setItem(ONBOARDED_KEY, 'true');
    setIsOpen(false);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="language-picker-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
    >
      <div className="bg-white dark:bg-slate-900 rounded-spec max-w-sm w-full p-6 text-center shadow-2xl border border-slate-200 dark:border-slate-800 space-y-5 animate-in fade-in zoom-in-95 duration-150">
        <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white font-black text-2xl flex items-center justify-center mx-auto shadow-md">
          W
        </div>

        <div>
          <h2 id="language-picker-title" className="text-xl font-bold text-slate-900 dark:text-slate-100">
            Choose your language
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            अपनी भाषा चुनें / Select your language
          </p>
        </div>

        <div className="space-y-3">
          {(Object.keys(LANGUAGES) as SupportedLanguage[]).map((code) => {
            const info = LANGUAGES[code];
            return (
              <button
                key={code}
                type="button"
                onClick={() => handleSelectLanguage(code)}
                onMouseEnter={() => speakLanguageName(info.nativeName, code)}
                onFocus={() => speakLanguageName(info.nativeName, code)}
                className="w-full py-3.5 px-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-slate-700 flex items-center justify-between text-left transition-all min-h-touch focus-visible:outline focus-visible:outline-3 focus-visible:outline-focus-ring"
              >
                <div>
                  <span className="text-base font-bold text-slate-900 dark:text-slate-100 block">
                    {info.nativeName}
                  </span>
                  <span className="text-xs text-slate-500">
                    {info.name}
                  </span>
                </div>
                <span className="text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-1 rounded font-medium">
                  Select
                </span>
              </button>
            );
          })}
        </div>

        <p className="text-[11px] text-slate-400">
          You can change your language anytime from Settings.
        </p>
      </div>
    </div>
  );
};
