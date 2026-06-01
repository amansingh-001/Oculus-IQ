/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#0EA5E9',
        danger: '#EF4444',
        warning: '#F59E0B',
        success: '#10B981',
        bg: '#0F172A',
        card: '#1E293B',
      },
    },
  },
  plugins: [],
};
