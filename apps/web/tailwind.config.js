/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'media',
  theme: {
    extend: {
      colors: {
        'alert-green': '#1B7F3B',
        'alert-yellow': '#F2C200',
        'alert-orange': '#E8710A',
        'alert-red': '#C62828',
        'focus-ring': '#1F5FBF',
        'guidance-border': '#475569',
        'guidance-light': '#F1F5F9',
        'guidance-dark': '#1E293B',
      },
      maxWidth: {
        'column': '720px',
      },
      minHeight: {
        'touch': '48px',
      },
      minWidth: {
        'touch': '48px',
      },
      borderRadius: {
        'spec': '12px',
      },
    },
  },
  plugins: [],
}
