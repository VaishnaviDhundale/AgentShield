/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        cyber: {
          dark: '#0a0d14',
          panel: '#111726',
          border: '#1e293b',
          accent: '#06b6d4',
          allow: '#10b981',
          block: '#ef4444',
          ask: '#f59e0b',
          muted: '#64748b'
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace', 'ui-monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif']
      }
    },
  },
  plugins: [],
}
