import React from 'react';
import { FeatureDefinition } from '../../types/feature';
import { MorePage } from './MorePage';

export const moreFeature: FeatureDefinition = {
  id: 'more',
  name: 'More',
  routes: [
    {
      id: 'more',
      path: '/more',
      labelKey: 'more',
      defaultLabel: 'More',
      navPosition: 'bottom',
      order: 40,
      icon: ({ className = 'w-5 h-5', active }) => (
        <svg
          className={`${className} ${active ? 'text-blue-600' : 'text-slate-500'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      ),
      component: MorePage,
    },
  ],
  translations: {
    en: {
      more_title: 'Settings & About',
    },
    hi: {
      more_title: 'सेटिंग और जानकारी',
    },
  },
};

export default moreFeature;
