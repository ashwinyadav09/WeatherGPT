/**
 * Design tokens from docs/ui-spec.md
 * Never colour alone: pair colour with an icon and a word.
 */
export const TOKENS = {
  colors: {
    // Alert tokens (strictly reserved for official alerts)
    alertGreen: {
      bg: '#1B7F3B',
      text: '#FFFFFF',
      border: '#166530',
      label: 'Green: No warning',
      labelHi: 'हरा: कोई चेतावनी नहीं',
    },
    alertYellow: {
      bg: '#F2C200',
      text: '#1A1A1A',
      border: '#D4A800',
      label: 'Yellow: Watch (Stay aware)',
      labelHi: 'पीला: निगरानी (सतर्क रहें)',
    },
    alertOrange: {
      bg: '#E8710A',
      text: '#1A1A1A',
      border: '#C45D05',
      label: 'Orange: Alert (Be prepared)',
      labelHi: 'नारंगी: अलर्ट (तैयार रहें)',
    },
    alertRed: {
      bg: '#C62828',
      text: '#FFFFFF',
      border: '#A51D1D',
      label: 'Red: Warning (Take action)',
      labelHi: 'लाल: चेतावनी (कदम उठाएं)',
    },
    // Model guidance token (neutral with dashed border)
    guidance: {
      border: '#475569',
      bgLight: '#F1F5F9',
      bgDark: '#1E293B',
      label: 'Model guidance',
      labelHi: 'मॉडल का अनुमान',
    },
    // Accessible focus ring (3px outline with 2px offset)
    focus: '#1F5FBF',
  },
  typography: {
    fontFamily: "'Noto Sans', 'Noto Sans Devanagari', system-ui, -apple-system, sans-serif",
    fontSizeBase: '18px',
    lineHeight: '1.5',
  },
  layout: {
    maxColumnWidth: '720px',
    minTouchTarget: '48px',
    radius: '12px',
    spacing: [4, 8, 12, 16, 24, 32],
  },
} as const;

export type AlertLevel = 'green' | 'yellow' | 'orange' | 'red';
