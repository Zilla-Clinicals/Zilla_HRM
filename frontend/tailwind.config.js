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
        // Zilla Clinicals brand — deep forest green (see zillaclinicals.com).
        // Anchors 50/100/400/600/700/800 are exact colors lifted from the site
        // + logo; the rest are derived tints for a smooth scale.
        brand: {
          50: "#f3f9f6",
          100: "#e9f4ee",
          200: "#c8e0d5",
          300: "#9dc7b5",
          400: "#77a692",
          500: "#3f8a63",
          600: "#06512c",
          700: "#0c4820",
          800: "#0d2611",
          900: "#08210c",
        },
        // Zilla accent — peach/apricot (the "Contact Us" CTA + section eyebrows).
        accent: {
          300: "#ffd9bf",
          400: "#fcb07e",
          500: "#f9955a",
          600: "#f45a2a",
        },
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #0c4820 0%, #06512c 55%, #3f8a63 100%)",
        "brand-gradient-soft": "linear-gradient(135deg, #f3f9f6 0%, #e9f4ee 100%)",
        "app-bg":
          "radial-gradient(1200px 600px at 100% -10%, #f3f9f6 0%, transparent 55%), radial-gradient(900px 500px at -10% 10%, #e9f4ee 0%, transparent 50%)",
        "sidebar-gradient": "linear-gradient(180deg, #0d2611 0%, #0c4820 100%)",
        shimmer:
          "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.6) 50%, rgba(255,255,255,0) 100%)",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16,24,40,.04), 0 4px 16px rgba(16,24,40,.06)",
        card: "0 1px 3px rgba(16,24,40,.05), 0 12px 32px -14px rgba(16,24,40,.14)",
        "card-hover": "0 2px 6px rgba(16,24,40,.06), 0 20px 40px -16px rgba(6,81,44,.28)",
        glow: "0 10px 24px -6px rgba(6,81,44,.5)",
        "glow-sm": "0 6px 16px -6px rgba(6,81,44,.5)",
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
