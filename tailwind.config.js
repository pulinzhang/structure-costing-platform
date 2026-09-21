/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./static/**/*.html", "./static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        app: {
          deep: 'rgb(var(--bg-deep) / <alpha-value>)',
          main: 'rgb(var(--bg-main) / <alpha-value>)',
          surface: 'rgb(var(--bg-surface) / <alpha-value>)',
          elevated: 'rgb(var(--bg-elevated) / <alpha-value>)',
          hud: 'rgb(var(--bg-hud) / <alpha-value>)',
          rowhover: 'rgb(var(--bg-row-hover) / <alpha-value>)',
        },
        ink: {
          DEFAULT: 'rgb(var(--text-main) / <alpha-value>)',
          muted: 'rgb(var(--text-muted) / <alpha-value>)',
          dim: 'rgb(var(--text-disabled) / <alpha-value>)',
          faint: 'rgb(var(--text-faint) / <alpha-value>)',
        },
        line: {
          DEFAULT: 'rgb(var(--border-color) / <alpha-value>)',
          subtle: 'rgb(var(--border-subtle) / <alpha-value>)',
          hud: 'rgb(var(--border-hud) / <alpha-value>)',
        },
        brand: {
          DEFAULT: 'rgb(var(--brabus-red) / <alpha-value>)',
          hover: 'rgb(var(--brabus-red-hover) / <alpha-value>)',
          active: 'rgb(var(--border-active) / <alpha-value>)',
          hud: 'rgb(var(--hud-red) / <alpha-value>)',
        },
        ok: 'rgb(var(--success-color) / <alpha-value>)',
        warn: 'rgb(var(--warning-color) / <alpha-value>)',
        danger: 'rgb(var(--danger-color) / <alpha-value>)',
        overlay: 'rgb(var(--overlay) / <alpha-value>)',
      },
    },
  },
  plugins: [],
};
