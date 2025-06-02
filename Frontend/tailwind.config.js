/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "brand-green": "#0B3D1F",
        "brand-teal": "#1BC5AE",
      },
    },
  },
  plugins: [],
};
