// ui-tui/src/components/contextBar.tsx
import React from 'react';
import { Text } from 'ink';
import { theme } from '../theme';

interface ContextBarProps {
  used: number;
  max: number;
}

function contextColor(pct: number): string {
  if (pct < 50) return theme.accent.green;
  if (pct < 75) return theme.accent.blue;
  if (pct < 90) return theme.accent.amber;
  return theme.accent.red;
}

export const ContextBar: React.FC<ContextBarProps> = ({ used, max }) => {
  const pct = Math.round((used / max) * 100);
  const barWidth = 10;
  const filled = Math.round((pct / 100) * barWidth);
  const empty = barWidth - filled;
  const bar = '#'.repeat(filled) + '-'.repeat(empty);
  const color = contextColor(pct);

  return (
    <Text color={color}>
      {`[${bar}] ${pct}%`}
    </Text>
  );
};
