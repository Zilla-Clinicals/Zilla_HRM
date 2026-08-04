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
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
        },
        accent: {
          400: "#c084fc",
          500: "#a855f7",
          600: "#9333ea",
        },
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)",
        "brand-gradient-soft": "linear-gradient(135deg, #eef2ff 0%, #faf5ff 100%)",
        "app-bg":
          "radial-gradient(1200px 600px at 100% -10%, #eef2ff 0%, transparent 55%), radial-gradient(900px 500px at -10% 10%, #faf5ff 0%, transparent 50%)",
        "sidebar-gradient": "linear-gradient(180deg, #4f46e5 0%, #6d28d9 100%)",
        shimmer:
          "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.6) 50%, rgba(255,255,255,0) 100%)",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16,24,40,.04), 0 4px 16px rgba(16,24,40,.06)",
        card: "0 1px 3px rgba(16,24,40,.05), 0 12px 32px -14px rgba(16,24,40,.14)",
        "card-hover": "0 2px 6px rgba(16,24,40,.06), 0 20px 40px -16px rgba(79,70,229,.28)",
        glow: "0 10px 24px -6px rgba(99,102,241,.5)",
        "glow-sm": "0 6px 16px -6px rgba(99,102,241,.5)",
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
