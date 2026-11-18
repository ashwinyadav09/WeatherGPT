import React, { useState, useEffect, useMemo } from 'react';
import { Header } from './Header';
import { Navigation } from './Navigation';
import { loadRegisteredFeatures, getNavRoutes } from '../features/registry';
import { useTranslation } from '../i18n/LanguageContext';
import { FirstRunLanguagePicker } from '../features/onboarding/FirstRunLanguagePicker';

export const AppLayout: React.FC = () => {
  const { registerTranslations } = useTranslation();
  const features = useMemo(() => loadRegisteredFeatures(), []);

  // Register feature translation namespaces dynamically
  useEffect(() => {
    for (const feat of features) {
      if (feat.translations) {
        registerTranslations(feat.id, feat.translations);
      }
    }
  }, [features, registerTranslations]);

  const navRoutes = useMemo(() => getNavRoutes(features), [features]);
  const [activeRouteId, setActiveRouteId] = useState<string>('ask');

  const activeRoute = useMemo(() => {
    for (const feat of features) {
      const match = feat.routes.find((r) => r.id === activeRouteId);
      if (match) return match;
    }
    return navRoutes[0];
  }, [features, navRoutes, activeRouteId]);

  const ActiveComponent = activeRoute ? activeRoute.component : () => null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col font-sans transition-colors pb-20 md:pb-8">
      {/* Accessible landmark header */}
      <Header
        currentPlace="Pune"
        onPlaceClick={() => setActiveRouteId('places')}
      />

      {/* Navigation bar (Desktop top / Mobile bottom) */}
      <Navigation
        routes={navRoutes}
        activeRouteId={activeRouteId}
        onRouteChange={setActiveRouteId}
      />

      {/* Main Landmark Area */}
      <main className="flex-1 w-full" id="main-content">
        <ActiveComponent />
      </main>

      {/* First-run voice-accessible language picker */}
      <FirstRunLanguagePicker />
    </div>
  );
};
