/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: {
          900: '#0a0a0a',
          800: '#121212',
          700: '#1a1a1a',
          600: '#242424',
          500: '#2e2e2e',
        },
        aura: {
          green: '#00ff9f',
          blue: '#00d1ff',
          red: '#ff4d4d',
        }
      },
    },
  },
  plugins: [],
}
