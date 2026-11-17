import React from 'react';
import { useTranslation } from '../i18n/LanguageContext';
import { LanguageSwitcher } from '../i18n/LanguageSwitcher';
import { Chip } from '../components/Chip';

interface HeaderProps {
  currentPlace?: string;
  onPlaceClick?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentPlace = 'Pune',
  onPlaceClick,
}) => {
  const { t } = useTranslation();

  return (
    <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 sticky top-0 z-30">
      <div className="max-w-column mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-lg shadow-sm">
            W
          </div>
          <div>
            <span className="font-bold text-lg text-slate-900 dark:text-slate-100 tracking-tight block leading-none">
              {t('app_name')}
            </span>
            <span className="text-[10px] text-slate-400 font-medium">India Public Pilot</span>
          </div>
        </div>

        {/* Place and Language Switcher */}
        <div className="flex items-center gap-2">
          {currentPlace && (
            <Chip
              onClick={onPlaceClick}
              className="text-xs py-1 px-2.5 h-9"
              icon={
                <svg className="w-3.5 h-3.5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              }
            >
              {currentPlace}
            </Chip>
          )}
          <LanguageSwitcher />
        </div>
      </div>
    </header>
  );
};
