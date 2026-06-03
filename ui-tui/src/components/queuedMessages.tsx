// ui-tui/src/components/queuedMessages.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface QueuedMessagesProps {
  messages: string[];
}

export const QueuedMessages: React.FC<QueuedMessagesProps> = ({ messages }) => {
  if (messages.length === 0) return null;

  return (
    <Box flexDirection="column" paddingX={1}>
      <Text color={theme.accent.amber} bold>
        {`[QUEUED] ${messages.length} message(s)`}
      </Text>
      {messages.slice(0, 5).map((msg, i) => (
        <Text key={i} color={theme.txt.primary}>
          {`  ${i + 1}. ${msg.slice(0, 50)}`}
        </Text>
      ))}
      {messages.length > 5 && (
        <Text color={theme.txt.muted}>
          {`  ... +${messages.length - 5} more`}
        </Text>
      )}
    </Box>
  );
};
