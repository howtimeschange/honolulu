/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary': '#6366f1',
        'primary-dark': '#4f46e5',
        'surface': '#1e1e2e',
        'surface-light': '#313244',
        'surface-lighter': '#45475a',
        'text': '#cdd6f4',
        'text-muted': '#a6adc8',
        'border': '#45475a',
        'success': '#a6e3a1',
        'warning': '#f9e2af',
        'error': '#f38ba8',
      },
    },
  },
  plugins: [],
}
