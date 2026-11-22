import React from 'react';
import { FeatureDefinition } from '../../types/feature';
import { AskPage } from './AskPage';

export const askFeature: FeatureDefinition = {
  id: 'ask',
  name: 'Ask WeatherGPT',
  routes: [
    {
      id: 'ask',
      path: '/',
      labelKey: 'ask',
      defaultLabel: 'Ask',
      navPosition: 'bottom',
      order: 10,
      icon: ({ className = 'w-5 h-5', active }) =>
        React.createElement(
          'svg',
          {
            className: `${className} ${active ? 'text-blue-600' : 'text-slate-500'}`,
            fill: 'none',
            stroke: 'currentColor',
            viewBox: '0 0 24 24',
            'aria-hidden': 'true',
          },
          React.createElement('path', {
            strokeLinecap: 'round',
            strokeLinejoin: 'round',
            strokeWidth: '2',
            d: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
          })
        ),
      component: AskPage,
    },
  ],
  translations: {
    en: {
      ask_title: 'Ask WeatherGPT',
      placeholder: 'Type your question',
    },
    hi: {
      ask_title: 'WeatherGPT से पूछें',
      placeholder: 'अपना सवाल लिखें',
    },
  },
};

export default askFeature;
