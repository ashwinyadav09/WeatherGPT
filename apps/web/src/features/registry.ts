import { FeatureDefinition, FeatureRoute } from '../types/feature';

interface FeatureModule {
  default?: FeatureDefinition;
  feature?: FeatureDefinition;
}

/**
 * Dynamically discovers and loads all features across apps/web/src/features/*
 * using Vite's import.meta.glob. Adding a new feature folder with a feature.ts
 * file registers its routes and translation namespace automatically without
 * touching any shared files.
 */
export const loadRegisteredFeatures = (): FeatureDefinition[] => {
  const modules = import.meta.glob<FeatureModule>('./*/feature.ts', { eager: true });
  const features: FeatureDefinition[] = [];

  for (const path in modules) {
    const mod = modules[path];
    const def = mod.default || mod.feature;
    if (def && def.id) {
      features.push(def);
    }
  }

  return features;
};

export const getNavRoutes = (features: FeatureDefinition[]): FeatureRoute[] => {
  const routes: FeatureRoute[] = [];
  for (const feat of features) {
    for (const r of feat.routes) {
      if (r.navPosition !== 'hidden') {
        routes.push(r);
      }
    }
  }
  return routes.sort((a, b) => a.order - b.order);
};
