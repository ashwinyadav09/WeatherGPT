import React, { HTMLAttributes } from 'react';

export type CardVariant = 'standard' | 'guidance' | 'elevated';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  headerBadge?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  variant = 'standard',
  headerBadge,
  children,
  className = '',
  ...props
}) => {
  const baseStyles = 'rounded-spec p-5 transition-shadow max-w-column w-full';

  const variantStyles: Record<CardVariant, string> = {
    standard:
      'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm text-slate-900 dark:text-slate-100',
    guidance:
      'border-2 border-dashed border-guidance-border bg-guidance-light dark:bg-guidance-dark text-slate-800 dark:text-slate-200',
    elevated:
      'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-md text-slate-900 dark:text-slate-100',
  };

  return (
    <article className={`${baseStyles} ${variantStyles[variant]} ${className}`} {...props}>
      {variant === 'guidance' && (
        <div className="flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-2.5">
          <span className="w-2 h-2 rounded-full bg-slate-500 inline-block" aria-hidden="true" />
          <span>Model guidance</span>
        </div>
      )}
      {headerBadge && <div className="mb-3">{headerBadge}</div>}
      {children}
    </article>
  );
};
