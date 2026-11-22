import React from 'react';
import { useTranslation } from '../i18n/LanguageContext';

export interface SourceLineProps {
  sourceName?: string;
  issuedAt?: string;
  validUntil?: string;
  attribution?: string;
  className?: string;
}

export const SourceLine: React.FC<SourceLineProps> = ({
  sourceName = 'Open-Meteo (model data)',
  issuedAt,
  validUntil,
  attribution,
  className = '',
}) => {
  const { t } = useTranslation();

  return (
    <div className={`text-xs text-slate-500 dark:text-slate-400 space-y-1 ${className}`}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-medium text-slate-700 dark:text-slate-300">
          {t('source')}: {sourceName}
        </span>
        {issuedAt && (
          <>
            <span aria-hidden="true">•</span>
            <span>
              {t('issued')}: {issuedAt}
            </span>
          </>
        )}
        {validUntil && (
          <>
            <span aria-hidden="true">•</span>
            <span>
              {t('valid_until')}: {validUntil}
            </span>
          </>
        )}
      </div>

      {attribution && (
        <div className="text-[10px] text-slate-400 dark:text-slate-500">
          {attribution}
        </div>
      )}
    </div>
  );
};
