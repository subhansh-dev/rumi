// ui-tui/src/components/streaming.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface StreamingProps {
  content: string;
  isActive: boolean;
}

export const Streaming: React.FC<StreamingProps> = ({ content, isActive }) => {
  if (!isActive && !content) return null;

  return (
    <Box flexDirection="column" marginBottom={1} paddingLeft={1}>
      <Text color={theme.accent.blue}>
        {'╭─ RUMI ' + '─'.repeat(50) + '╮'}
      </Text>
      <Text color={theme.txt.primary} wrap="wrap">
        {'│ '}{content}
        {isActive && <Text color={theme.accent.green}>{'▍'}</Text>}
      </Text>
      {!isActive && content && (
        <Text color={theme.accent.blue}>
          {'╰' + '─'.repeat(52) + '╯'}
        </Text>
      )}
    </Box>
  );
};
