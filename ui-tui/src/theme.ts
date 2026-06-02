// ui-tui/src/theme.ts
// Hermes Agent color palette — warm dark theme

export const theme = {
  bg: {
    deep: '#0d1117',
    secondary: '#161b22',
    panel: '#1c2128',
    element: '#21262d',
    hover: '#30363d',
    input: '#0d1117',
  },
  txt: {
    bright: '#f0f6fc',
    primary: '#c9d1d9',
    secondary: '#8b949e',
    muted: '#484f58',
    dim: '#30363d',
  },
  accent: {
    cyan: '#39d353',
    blue: '#58a6ff',
    green: '#39d353',
    amber: '#d29922',
    red: '#f85149',
    purple: '#bc8cff',
    teal: '#39d353',
    pink: '#f778ba',
  },
  border: {
    subtle: '#21262d',
    normal: '#30363d',
    active: '#58a6ff',
  },
} as const;

export type Theme = typeof theme;
