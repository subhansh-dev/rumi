// ui-tui/src/components/transcript.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';
import { TranscriptEntry } from '../hooks/useTranscript';

interface TranscriptProps {
  entries: TranscriptEntry[];
  maxHeight?: number;
}

export const Transcript: React.FC<TranscriptProps> = ({ entries, maxHeight = 50 }) => {
  const visible = entries.slice(-maxHeight);

  return (
    <Box flexDirection="column" flexShrink={1}>
      {visible.map(entry => (
        <TranscriptLine key={entry.id} entry={entry} />
      ))}
    </Box>
  );
};

const TranscriptLine: React.FC<{ entry: TranscriptEntry }> = ({ entry }) => {
  switch (entry.role) {
    case 'user':
      return (
        <Box flexDirection="column" marginBottom={1} paddingLeft={1}>
          <Text color={theme.accent.blue} bold>{'[USER]'}</Text>
          <Text color={theme.txt.primary} wrap="wrap">
            {entry.content}
          </Text>
        </Box>
      );

    case 'assistant':
      return (
        <Box flexDirection="column" marginBottom={1} paddingLeft={1}>
          <Text color={theme.accent.cyan} bold>{'[RUMI]'}</Text>
          <Text color={theme.txt.primary} wrap="wrap">
            {entry.content}
          </Text>
        </Box>
      );

    case 'system':
      return (
        <Box paddingLeft={1}>
          <Text color={theme.txt.muted}>{entry.content}</Text>
        </Box>
      );

    case 'error':
      return (
        <Box paddingLeft={1}>
          <Text color={theme.accent.red} bold>{'[ERROR]'}</Text>
          <Text color={theme.accent.red}>{' '}{entry.content}</Text>
        </Box>
      );

    default:
      return null;
  }
};
