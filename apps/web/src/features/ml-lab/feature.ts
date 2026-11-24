import React from 'react';
import { FeatureDefinition } from '../../types/feature';
import { MLLabPage } from './MLLabPage';

export const feature: FeatureDefinition = {
  id: 'mllab',
  name: 'ML Lab',
  routes: [
    {
      id: 'mllab',
      path: '/ml-lab',
      defaultLabel: 'ML Lab',
      labelKey: 'ml_lab',
      component: MLLabPage,
      navPosition: 'top',
      order: 40,
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
            d: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z',
          })
        ),
    },
  ],
  translations: {
    en: {
      ml_lab: 'ML Lab',
      models: 'Registered Models',
      eval_summary: 'Evaluation Summary',
      try_it: 'Try Live Inference',
      not_measured: 'NOT MEASURED',
    },
    hi: {
      ml_lab: 'एमएल लैब',
      models: 'पंजीकृत मॉडल्स',
      eval_summary: 'मूल्यांकन सारांश',
      try_it: 'लाइव मॉडल चलाएं',
      not_measured: 'मापा नहीं गया (NOT MEASURED)',
    },
  },
};

export default feature;
