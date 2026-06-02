import React, { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

const KAOMOJI = [
  '(｡•́︿•̀｡)', '(◔_versed)', '(¬‿¬)', '( •_•)>⌐■-■', '(⌐■_■)',
  '(´･_･`)', '◉_◉', '(°ロ°)', '( ˘⌣˘)♡', 'ヽ(>∀<☆)☆',
  '٩(๑❛ᴗ❛๑)۶', '(⊙_⊙)', '(¬_¬)', '( ͡° ͜ʖ ͡°)', 'ಠ_ಠ',
];

interface StatusBarProps {
  state: string;
  model: string;
  tokens: number;
  cost: number;
  uptime: number;
  thinkMode: boolean;
  diveMode: boolean;
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

export const StatusBar: React.FC<StatusBarProps> = ({
  state, model, tokens, cost, uptime, thinkMode, diveMode,
}) => {
  const [kaomojiIdx, setKaomojiIdx] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setKaomojiIdx(prev => (prev + 1) % KAOMOJI.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  const stateColor = state === 'READY' || state === 'IDLE'
    ? theme.accent.green
    : state === 'THINKING' || state === 'PROCESSING'
    ? theme.accent.amber
    : theme.txt.secondary;

  const stateLabel = state === 'THINKING' ? 'thinking…'
    : state === 'PROCESSING' ? 'running…'
    : state === 'SPEAKING' ? 'speaking…'
    : 'ready';

  const isBusy = state === 'THINKING' || state === 'PROCESSING';

  return (
    <Box
      flexDirection="row"
      paddingX={1}
      borderTop={true}
      borderColor={theme.border.normal}
    >
      <Text color={stateColor} bold>{'● '}{stateLabel}</Text>
      {isBusy && (
        <Text color={theme.accent.amber}>{' '}{KAOMOJI[kaomojiIdx]}</Text>
      )}
      <Text color={theme.border.normal}>{' │ '}</Text>
      <Text color={theme.accent.blue}>{model}</Text>
      <Text color={theme.border.normal}>{' │ '}</Text>
      <Text color={theme.txt.secondary}>{formatTokens(tokens)} tok</Text>
      <Text color={theme.border.normal}>{' │ '}</Text>
      <Text color={theme.txt.secondary}>{formatUptime(uptime)}</Text>
      {cost > 0 && (
        <>
          <Text color={theme.border.normal}>{' │ '}</Text>
          <Text color={theme.accent.green}>{'$'}{cost.toFixed(4)}</Text>
        </>
      )}
      {thinkMode && (
        <>
          <Text color={theme.border.normal}>{' │ '}</Text>
          <Text color={theme.accent.purple}>{'think'}</Text>
        </>
      )}
      {diveMode && (
        <>
          <Text color={theme.border.normal}>{' │ '}</Text>
          <Text color={theme.accent.cyan}>{'dive'}</Text>
        </>
      )}
    </Box>
  );
};
