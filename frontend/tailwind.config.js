/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: '#0f172a',
          indigo: '#4f46e5',
          teal: '#14b8a6',
          amber: '#f59e0b',
          red: '#ef4444',
          slate: '#f8fafc',
        },
      },
    },
  },
  plugins: [],
}

