import React from 'react';

export type NavPosition = 'bottom' | 'top' | 'both' | 'more' | 'hidden';

export interface FeatureRoute {
  id: string;
  path: string;
  labelKey: string;
  defaultLabel: string;
  navPosition?: NavPosition;
  order: number;
  icon?: (props: { className?: string; active?: boolean }) => React.ReactElement;
  component: React.ComponentType;
}

export interface FeatureTranslations {
  en: Record<string, string>;
  hi: Record<string, string>;
  [lang: string]: Record<string, string>;
}

export interface FeatureDefinition {
  id: string;
  name: string;
  routes: FeatureRoute[];
  translations?: FeatureTranslations;
}
