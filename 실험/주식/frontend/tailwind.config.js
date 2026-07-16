/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0a1727",
        paper: "#f3f0e8",
        coral: "#ff6b4a",
        mint: "#52d6aa"
      }
    }
  },
  plugins: []
};

