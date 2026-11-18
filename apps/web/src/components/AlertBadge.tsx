import React from 'react';
import { AlertLevel, TOKENS } from '../tokens/tokens';
import { useTranslation } from '../i18n/LanguageContext';

export interface AlertBadgeProps {
  level: AlertLevel;
  customWord?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const AlertBadge: React.FC<AlertBadgeProps> = ({
  level,
  customWord,
  size = 'md',
  className = '',
}) => {
  const { language } = useTranslation();
  const token =
    level === 'green'
      ? TOKENS.colors.alertGreen
      : level === 'yellow'
      ? TOKENS.colors.alertYellow
      : level === 'orange'
      ? TOKENS.colors.alertOrange
      : TOKENS.colors.alertRed;

  const word = customWord || (language === 'hi' ? token.labelHi : token.label);

  const icons: Record<AlertLevel, React.ReactNode> = {
    green: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
      </svg>
    ),
    yellow: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
      </svg>
    ),
    orange: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    red: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
      </svg>
    ),
  };

  const sizeClasses = {
    sm: 'text-xs px-2.5 py-1 gap-1.5',
    md: 'text-sm px-3.5 py-1.5 gap-2 font-semibold',
    lg: 'text-base px-4 py-2 gap-2.5 font-bold',
  };

  return (
    <span
      role="status"
      style={{
        backgroundColor: token.bg,
        color: token.text,
      }}
      className={`inline-flex items-center rounded-lg shadow-sm tracking-wide ${sizeClasses[size]} ${className}`}
    >
      <span className="flex-shrink-0" aria-hidden="true">
        {icons[level]}
      </span>
      <span>{word}</span>
    </span>
  );
};
