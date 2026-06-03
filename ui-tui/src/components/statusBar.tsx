// ui-tui/src/components/statusBar.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';
import { ContextBar } from './contextBar';

interface StatusBarProps {
  state: string;
  model: string;
  tokens: number;
  cost: number;
  uptime: number;
  thinkMode: boolean;
  diveMode: boolean;
  elapsed?: number;
  maxContext?: number;
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m${s}s`;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  state, model, tokens, cost, uptime, thinkMode, diveMode,
  elapsed = 0, maxContext = 200000,
}) => {
  const stateColor = state === 'READY' || state === 'IDLE'
    ? theme.accent.green
    : state === 'THINKING' || state === 'PROCESSING'
    ? theme.accent.amber
    : theme.txt.primary;

  const stateLabel = state === 'THINKING' ? 'thinking'
    : state === 'PROCESSING' ? 'running'
    : state === 'SPEAKING' ? 'speaking'
    : 'ready';

  return (
    <Box flexDirection="row" paddingX={1}>
      <Text color={stateColor} bold>{stateLabel}</Text>
      <Text color={theme.txt.muted}>{' | '}</Text>
      <Text color={theme.txt.primary}>{model}</Text>
      <Text color={theme.txt.muted}>{' | '}</Text>
      <Text color={theme.txt.primary}>{formatTokens(tokens)} tok</Text>
      <Text color={theme.txt.muted}>{' | '}</Text>
      <ContextBar used={tokens} max={maxContext} />
      <Text color={theme.txt.muted}>{' | '}</Text>
      <Text color={theme.txt.primary}>{formatUptime(uptime)}</Text>
      {elapsed > 0 && (
        <>
          <Text color={theme.txt.muted}>{' | '}</Text>
          <Text color={theme.accent.amber}>{formatElapsed(elapsed)}</Text>
        </>
      )}
      {cost > 0 && (
        <>
          <Text color={theme.txt.muted}>{' | '}</Text>
          <Text color={theme.accent.green}>${cost.toFixed(4)}</Text>
        </>
      )}
      {thinkMode && (
        <>
          <Text color={theme.txt.muted}>{' | '}</Text>
          <Text color={theme.accent.purple}>{'think'}</Text>
        </>
      )}
      {diveMode && (
        <>
          <Text color={theme.txt.muted}>{' | '}</Text>
          <Text color={theme.accent.cyan}>{'dive'}</Text>
        </>
      )}
    </Box>
  );
};
