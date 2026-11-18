import React from 'react';
import { FeatureDefinition } from '../../types/feature';
import { PlacesPage } from './PlacesPage';

export const placesFeature: FeatureDefinition = {
  id: 'places',
  name: 'Places',
  routes: [
    {
      id: 'places',
      path: '/places',
      labelKey: 'places',
      defaultLabel: 'Places',
      navPosition: 'bottom',
      order: 30,
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
            d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      ),
      component: PlacesPage,
    },
  ],
  translations: {
    en: {
      places_title: 'Saved Places',
      search_placeholder: 'Search village, block, district...',
    },
    hi: {
      places_title: 'सहेजे गए स्थान',
      search_placeholder: 'गाँव, ब्लॉक, जिला खोजें...',
    },
  },
};

export default placesFeature;
