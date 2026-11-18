import React from 'react';
import { FeatureDefinition } from '../../types/feature';
import { AdvisoriesPage } from './AdvisoriesPage';

export const advisoriesFeature: FeatureDefinition = {
  id: 'advisories',
  name: 'Official Advisories',
  routes: [
    {
      id: 'advisories',
      path: '/advisories',
      labelKey: 'advisories',
      defaultLabel: 'Advisories',
      navPosition: 'more',
      order: 35,
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
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      ),
      component: AdvisoriesPage,
    },
  ],
  translations: {
    en: {
      advisories: 'Advisories',
      advisories_title: 'Official Advisories (Agromet & Marine)',
    },
    hi: {
      advisories: 'कृषि व समुद्री सलाह',
      advisories_title: 'आधिकारिक सलाह (कृषि व समुद्री बुलेटिन)',
    },
  },
};

export default advisoriesFeature;
