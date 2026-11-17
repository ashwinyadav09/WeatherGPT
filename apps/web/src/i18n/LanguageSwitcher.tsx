import React from 'react';
import { useTranslation, LANGUAGES, SupportedLanguage } from './LanguageContext';

interface LanguageSwitcherProps {
  className?: string;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({ className = '' }) => {
  const { language, setLanguage } = useTranslation();

  return (
    <div
      role="radiogroup"
      aria-label="Language selection"
      className={`inline-flex items-center rounded-lg bg-slate-200 dark:bg-slate-800 p-1 ${className}`}
    >
      {(Object.keys(LANGUAGES) as SupportedLanguage[]).map((code) => {
        const info = LANGUAGES[code];
        const isActive = language === code;
        return (
          <button
            key={code}
            type="button"
            role="radio"
            aria-checked={isActive}
            lang={code}
            onClick={() => setLanguage(code)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all min-h-[36px] ${
              isActive
                ? 'bg-white dark:bg-slate-700 text-blue-700 dark:text-blue-300 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            {info.nativeName}
          </button>
        );
      })}
    </div>
  );
};
