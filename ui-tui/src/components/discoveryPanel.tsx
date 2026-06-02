import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface DiscoveryPanelProps {
  topic: string;
  progress: number;
  phase: string;
  papers: number;
  entities: number;
  edges: number;
  isActive: boolean;
}

function makeProgressBar(pct: number, width: number = 10): string {
  const filled = Math.round((pct / 100) * width);
  const empty = width - filled;
  return '[' + '█'.repeat(filled) + '░'.repeat(empty) + '] ' + pct + '%';
}

function progressColor(pct: number): string {
  if (pct < 50) return theme.accent.green;
  if (pct < 80) return theme.accent.amber;
  return theme.accent.blue;
}

export const DiscoveryPanel: React.FC<DiscoveryPanelProps> = ({
  topic, progress, phase, papers, entities, edges, isActive,
}) => {
  if (!isActive && progress === 0) return null;
  return (
    <Box flexDirection="column" paddingX={1} paddingBottom={1}>
      <Text color={theme.accent.purple} bold>{'Discovery: '}{topic.slice(0, 60)}</Text>
      <Box>
        <Text color={progressColor(progress)}>{'  '}{makeProgressBar(progress)}</Text>
        <Text color={theme.txt.secondary}>{'  '}{papers} papers</Text>
        <Text color={theme.txt.secondary}>{'  '}{entities} entities</Text>
        <Text color={theme.txt.secondary}>{'  '}{edges} edges</Text>
      </Box>
      {phase && <Text color={theme.txt.muted}>{'  '}{phase}</Text>}
    </Box>
  );
};
