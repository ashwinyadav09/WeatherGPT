import React from 'react';
import { useTranslation } from '../i18n/LanguageContext';
import { FeatureRoute } from '../types/feature';

interface NavigationProps {
  routes: FeatureRoute[];
  activeRouteId: string;
  onRouteChange: (id: string) => void;
}

export const Navigation: React.FC<NavigationProps> = ({
  routes,
  activeRouteId,
  onRouteChange,
}) => {
  const { t } = useTranslation();

  return (
    <>
      {/* Desktop Top Navigation (visible on md screens and up) */}
      <nav
        className="hidden md:block border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur sticky top-16 z-20"
        aria-label="Desktop Navigation"
      >
        <div className="max-w-column mx-auto px-4 flex items-center justify-start gap-1">
          {routes.map((route) => {
            const isActive = activeRouteId === route.id;
            const label = t(route.labelKey) || route.defaultLabel;

            return (
              <button
                key={route.id}
                type="button"
                onClick={() => onRouteChange(route.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold transition-colors border-b-2 min-h-touch ${
                  isActive
                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                {route.icon && route.icon({ className: 'w-4 h-4', active: isActive })}
                <span>{label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Mobile Persistent Bottom Bar (docs/ui-spec.md) */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 flex items-center justify-around z-30 shadow-lg"
        aria-label="Mobile Navigation"
      >
        {routes.map((route) => {
          const isActive = activeRouteId === route.id;
          const label = t(route.labelKey) || route.defaultLabel;

          return (
            <button
              key={route.id}
              type="button"
              onClick={() => onRouteChange(route.id)}
              className={`flex flex-col items-center justify-center flex-1 h-full min-h-touch transition-colors text-xs font-semibold ${
                isActive
                  ? 'text-blue-600 dark:text-blue-400'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              {route.icon && route.icon({ className: 'w-5 h-5 mb-0.5', active: isActive })}
              <span>{label}</span>
            </button>
          );
        })}
      </nav>
    </>
  );
};
