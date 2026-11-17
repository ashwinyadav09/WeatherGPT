/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'alert-green': '#1B7F3B',
        'alert-yellow': '#F2C200',
        'alert-orange': '#E8710A',
        'alert-red': '#C62828',
        'focus-ring': '#1F5FBF',
      },
      maxWidth: {
        'column': '720px',
      },
    },
  },
  plugins: [],
}
