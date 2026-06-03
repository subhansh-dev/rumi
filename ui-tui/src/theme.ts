// ui-tui/src/theme.ts
// RUMI — Premium AI Research Operating System

export const theme = {
  bg: {
    deep: '#000000',
    panel: '#0a0a0a',
    card: '#111111',
  },
  txt: {
    bright: '#EAEAEA',
    primary: '#EAEAEA',
    secondary: '#7A7A7A',
    muted: '#555555',
  },
  accent: {
    blue: '#00BFFF',
    cyan: '#00E5FF',
    green: '#00E676',
    amber: '#FFD740',
    red: '#FF5252',
    purple: '#B388FF',
  },
  border: {
    subtle: '#333333',
    normal: '#555555',
    active: '#00BFFF',
  },
} as const;

export type Theme = typeof theme;
