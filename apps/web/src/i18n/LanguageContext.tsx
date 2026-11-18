import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import enBase from './locales/en.json';
import hiBase from './locales/hi.json';

export type SupportedLanguage = 'en' | 'hi';

export interface LanguageInfo {
  code: SupportedLanguage;
  name: string;
  nativeName: string;
  fontFamily: string;
}

export const LANGUAGES: Record<SupportedLanguage, LanguageInfo> = {
  en: {
    code: 'en',
    name: 'English',
    nativeName: 'English',
    fontFamily: "'Noto Sans', system-ui, sans-serif",
  },
  hi: {
    code: 'hi',
    name: 'Hindi',
    nativeName: 'हिन्दी',
    fontFamily: "'Noto Sans Devanagari', 'Noto Sans', system-ui, sans-serif",
  },
};

interface LanguageContextType {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  registerTranslations: (featureId: string, translations: { en: Record<string, string>; hi: Record<string, string> }) => void;
}

const baseDictionaries: Record<SupportedLanguage, Record<string, string>> = {
  en: { ...enBase },
  hi: { ...hiBase },
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<SupportedLanguage>(() => {
    const saved = localStorage.getItem('weathergpt_lang') as SupportedLanguage;
    return saved && saved in LANGUAGES ? saved : 'en';
  });

  const [dictionaries, setDictionaries] = useState<Record<SupportedLanguage, Record<string, string>>>(baseDictionaries);

  const setLanguage = (lang: SupportedLanguage) => {
    setLanguageState(lang);
    localStorage.setItem('weathergpt_lang', lang);
    document.documentElement.lang = lang;
  };

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const registerTranslations = (
    featureId: string,
    translations: { en: Record<string, string>; hi: Record<string, string> }
  ) => {
    setDictionaries((prev) => {
      const nextEn = { ...prev.en };
      const nextHi = { ...prev.hi };

      for (const [k, v] of Object.entries(translations.en)) {
        nextEn[`${featureId}.${k}`] = v;
        if (!nextEn[k]) nextEn[k] = v; // Allow unqualified fallback
      }
      for (const [k, v] of Object.entries(translations.hi)) {
        nextHi[`${featureId}.${k}`] = v;
        if (!nextHi[k]) nextHi[k] = v;
      }
      return { en: nextEn, hi: nextHi };
    });
  };

  const t = (key: string, params?: Record<string, string | number>): string => {
    const dict = dictionaries[language] || dictionaries.en;
    let template = dict[key] || dictionaries.en[key] || key;

    if (params) {
      for (const [paramKey, paramVal] of Object.entries(params)) {
        template = template.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), String(paramVal));
      }
    }
    return template;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, registerTranslations }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useTranslation = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useTranslation must be used within a LanguageProvider');
  }
  return context;
};
