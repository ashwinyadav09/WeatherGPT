import React from 'react';
import { FeatureDefinition } from '../../types/feature';
import { AviationPage } from './AviationPage';

export const aviationFeature: FeatureDefinition = {
  id: 'aviation',
  name: 'Aviation Weather',
  routes: [
    {
      id: 'aviation',
      path: '/aviation',
      labelKey: 'aviation',
      defaultLabel: 'Aviation',
      navPosition: 'more',
      order: 40,
      icon: ({ className = 'w-5 h-5', active }) => (
        <svg
          className={`${className} ${active ? 'text-blue-600' : 'text-slate-500'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
          />
        </svg>
      ),
      component: AviationPage,
    },
  ],
  translations: {
    en: {
      aviation: 'Aviation',
      aviation_title: 'Aviation Weather (METAR / TAF)',
    },
    hi: {
      aviation: 'विमानन मौसम',
      aviation_title: 'विमानन मौसम (METAR / TAF)',
    },
  },
};

export default aviationFeature;
