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
        <Box marginBottom={1}>
          <Text color={theme.accent.blue} bold>{'> '}</Text>
          <Text color={theme.txt.primary}>{entry.content}</Text>
        </Box>
      );

    case 'assistant':
      return (
        <Box flexDirection="column" marginBottom={1} paddingLeft={1}>
          <Text color={theme.accent.blue}>
            {'╭─ RUMI ' + '─'.repeat(Math.max(0, 50)) + '╮'}
          </Text>
          <Text color={theme.txt.primary} wrap="wrap">
            {'│ '}{entry.content}
          </Text>
          <Text color={theme.accent.blue}>
            {'╰' + '─'.repeat(52) + '╯'}
          </Text>
        </Box>
      );

    case 'system':
      return (
        <Box>
          <Text color={theme.txt.muted} italic>{'  '}{entry.content}</Text>
        </Box>
      );

    case 'error':
      return (
        <Box>
          <Text color={theme.accent.red}>{'  ✗ '}{entry.content}</Text>
        </Box>
      );

    default:
      return null;
  }
};
