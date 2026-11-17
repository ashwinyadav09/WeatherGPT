import React from 'react';
import { FeatureDefinition } from '../../types/feature';
import { SmartCityPage } from './SmartCityPage';

export const smartCityFeature: FeatureDefinition = {
  id: 'smartcity',
  name: 'Smart City Webhooks',
  routes: [
    {
      id: 'smartcity',
      path: '/smart-city',
      labelKey: 'smart_city',
      defaultLabel: 'Smart City',
      navPosition: 'more',
      order: 45,
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
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
          />
        </svg>
      ),
      component: SmartCityPage,
    },
  ],
  translations: {
    en: {
      smart_city: 'Smart City',
      smart_city_title: 'Smart City Webhooks',
    },
    hi: {
      smart_city: 'स्मार्ट सिटी',
      smart_city_title: 'स्मार्ट सिटी वेबहुक',
    },
  },
};

export default smartCityFeature;
