import React, { ButtonHTMLAttributes } from 'react';

export interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: React.ReactNode;
  active?: boolean;
}

export const Chip: React.FC<ChipProps> = ({
  icon,
  active = false,
  children,
  className = '',
  ...props
}) => {
  return (
    <button
      type="button"
      className={`inline-flex items-center gap-2 px-3.5 py-2 text-xs md:text-sm font-medium rounded-full transition-all min-h-touch focus-visible:outline focus-visible:outline-3 focus-visible:outline-focus-ring focus-visible:outline-offset-2 ${
        active
          ? 'bg-blue-600 text-white shadow-sm'
          : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500 shadow-sm'
      } ${className}`}
      {...props}
    >
      {icon && <span className="flex-shrink-0" aria-hidden="true">{icon}</span>}
      <span>{children}</span>
    </button>
  );
};
