/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter var",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      colors: {
        // Zilla Clinicals brand — official HR palette: deep teal-green #052925
        // (=800) and sage #75a793 (=400) are the exact brand anchors; the other
        // steps are derived so the scale stays smooth and legible. White text is
        // only legible on 600+ (600=5.0, 700=7.9, 800=15.5:1), so buttons/sidebar
        // use those; 400/500 are for fills/accents, not text backgrounds.
        brand: {
          50: "#f1f6f4",
          100: "#dce9e4",
          200: "#c1d7ce",
          300: "#a1c3b6",
          400: "#75a793",
          500: "#44967c",
          600: "#297c67",
          700: "#155c4e",
          800: "#052925",
          900: "#031715",
        },
        // Zilla accent — peach/apricot #fcb07e (official). Pair with DARK text
        // (black on peach = 11.6:1; white on peach = 1.8:1 fails), so peach is
        // used for highlights/eyebrows/badges, not white-text buttons.
        accent: {
          300: "#ffd9bf",
          400: "#fcb07e",
          500: "#f9955a",
          600: "#f45a2a",
        },
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #297c67 0%, #14544a 50%, #052925 100%)",
        "brand-gradient-soft": "linear-gradient(135deg, #f1f6f4 0%, #dce9e4 100%)",
        "app-bg":
          "radial-gradient(1200px 600px at 100% -10%, #f1f6f4 0%, transparent 55%), radial-gradient(900px 500px at -10% 10%, #dce9e4 0%, transparent 50%)",
        "sidebar-gradient": "linear-gradient(180deg, #0a4038 0%, #052925 100%)",
        shimmer:
          "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.6) 50%, rgba(255,255,255,0) 100%)",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16,24,40,.04), 0 4px 16px rgba(16,24,40,.06)",
        card: "0 1px 3px rgba(16,24,40,.05), 0 12px 32px -14px rgba(16,24,40,.14)",
        "card-hover": "0 2px 6px rgba(16,24,40,.06), 0 20px 40px -16px rgba(5,41,37,.30)",
        glow: "0 10px 24px -6px rgba(20,80,68,.5)",
        "glow-sm": "0 6px 16px -6px rgba(20,80,68,.5)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-in-up": {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        "slide-in-right": {
          from: { opacity: "0", transform: "translateX(16px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-14px)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-in": "fade-in .4s ease-out both",
        "fade-in-up": "fade-in-up .5s cubic-bezier(.16,1,.3,1) both",
        "scale-in": "scale-in .2s ease-out both",
        "slide-in-right": "slide-in-right .35s cubic-bezier(.16,1,.3,1) both",
        float: "float 8s ease-in-out infinite",
        shimmer: "shimmer 1.6s infinite",
      },
    },
  },
  plugins: [],
};
