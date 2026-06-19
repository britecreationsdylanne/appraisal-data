/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#272D3F",
        slate: "#7DA3AF",
        teal: "#008182",
        mint: "#31D7CA",
        steel: "#466F88",
        mist: "#A9C1CB",
        cloud: "#E1E7EF",
        frost: "#F4F7FC",
        orange: "#FC883A",
        coral: "#D73D4F",
        blush: "#FCE6E8",
      },
      fontFamily: {
        sans: ["Gilroy", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
