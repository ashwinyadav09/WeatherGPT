import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import enBase from './locales/en.json';
import hiBase from './locales/hi.json';
import bnBase from './locales/bn.json';
import mrBase from './locales/mr.json';
import teBase from './locales/te.json';
import taBase from './locales/ta.json';
import orBase from './locales/or.json';

export type SupportedLanguage = 'en' | 'hi' | 'bn' | 'mr' | 'te' | 'ta' | 'or';

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
  bn: {
    code: 'bn',
    name: 'Bengali',
    nativeName: 'বাংলা',
    fontFamily: "'Noto Sans Bengali', 'Noto Sans', system-ui, sans-serif",
  },
  mr: {
    code: 'mr',
    name: 'Marathi',
    nativeName: 'मराठी',
    fontFamily: "'Noto Sans Devanagari', 'Noto Sans', system-ui, sans-serif",
  },
  te: {
    code: 'te',
    name: 'Telugu',
    nativeName: 'తెలుగు',
    fontFamily: "'Noto Sans Telugu', 'Noto Sans', system-ui, sans-serif",
  },
  ta: {
    code: 'ta',
    name: 'Tamil',
    nativeName: 'தமிழ்',
    fontFamily: "'Noto Sans Tamil', 'Noto Sans', system-ui, sans-serif",
  },
  or: {
    code: 'or',
    name: 'Odia',
    nativeName: 'ଓଡ଼ିଆ',
    fontFamily: "'Noto Sans Oriya', 'Noto Sans', system-ui, sans-serif",
  },
};

interface LanguageContextType {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  registerTranslations: (featureId: string, translations: Partial<Record<SupportedLanguage, Record<string, string>>>) => void;
}

const baseDictionaries: Record<SupportedLanguage, Record<string, string>> = {
  en: { ...enBase },
  hi: { ...hiBase },
  bn: { ...bnBase },
  mr: { ...mrBase },
  te: { ...teBase },
  ta: { ...taBase },
  or: { ...orBase },
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
    translations: Partial<Record<SupportedLanguage, Record<string, string>>>
  ) => {
    setDictionaries((prev) => {
      const next: Record<SupportedLanguage, Record<string, string>> = { ...prev };
      for (const langKey of Object.keys(LANGUAGES) as SupportedLanguage[]) {
        const langDict = { ...prev[langKey] };
        const incoming = translations[langKey];
        if (incoming) {
          for (const [k, v] of Object.entries(incoming)) {
            langDict[`${featureId}.${k}`] = v;
            if (!langDict[k]) langDict[k] = v;
          }
        }
        next[langKey] = langDict;
      }
      return next;
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
