/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./*.html",
    "./{coucou,mus,redaktion,zugang,js}/**/*.{html,php,js}",
  ],
  theme: {
    extend: {
      colors: {
        hvw: {
          ink: "#1a1a1a",
          charcoal: "#3d3d3d",
          mute: "#4a4a4a",
          paper: "#ffffff",
          fog: "#f3f3f3",
          line: "#1a1a1a",
          accent: "#c8102e",
          blue: "#47a1fb",
        },
      },
      fontFamily: {
        sans: ['"Outfit"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      maxWidth: {
        site: "1280px",
      },
      fontSize: {
        base: ["1.125rem", { lineHeight: "1.65" }],
      },
    },
  },
};
