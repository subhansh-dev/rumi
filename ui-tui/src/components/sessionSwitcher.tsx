// ui-tui/src/components/sessionSwitcher.tsx
import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import { theme } from '../theme';

interface Session {
  id: string;
  title: string;
  model: string;
  messages: number;
}

interface SessionSwitcherProps {
  sessions: Session[];
  visible: boolean;
  onSelect: (sessionId: string) => void;
  onNew: () => void;
  onClose: () => void;
}

export const SessionSwitcher: React.FC<SessionSwitcherProps> = ({
  sessions, visible, onSelect, onNew, onClose,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  useInput((input, key) => {
    if (!visible) return;
    if (key.escape) onClose();
    else if (key.upArrow) setSelectedIndex(prev => (prev > 0 ? prev - 1 : sessions.length));
    else if (key.downArrow) setSelectedIndex(prev => (prev < sessions.length ? prev + 1 : 0));
    else if (key.return) {
      if (selectedIndex === sessions.length) onNew();
      else if (sessions[selectedIndex]) onSelect(sessions[selectedIndex].id);
    }
  });

  if (!visible) return null;

  return (
    <Box flexDirection="column" padding={1} width="70%">
      <Text color={theme.accent.cyan} bold>{'[SESSIONS]'}</Text>
      <Text color={theme.txt.muted}>{'--'.repeat(30)}</Text>
      {sessions.map((session, idx) => (
        <Box key={session.id}>
          <Text color={idx === selectedIndex ? theme.accent.cyan : theme.txt.primary} bold={idx === selectedIndex}>
            {idx === selectedIndex ? ' > ' : '   '}
          </Text>
          <Text color={theme.txt.primary}>{session.title || session.id}</Text>
          <Text color={theme.txt.muted}>{'  '}{session.model} . {session.messages} msgs</Text>
        </Box>
      ))}
      <Box>
        <Text color={selectedIndex === sessions.length ? theme.accent.cyan : theme.txt.primary} bold={selectedIndex === sessions.length}>
          {selectedIndex === sessions.length ? ' > ' : '   '}
        </Text>
        <Text color={theme.accent.green}>{'+ New Session'}</Text>
      </Box>
      <Text color={theme.txt.muted}>{'--'.repeat(30)}</Text>
      <Text color={theme.txt.muted}>{' Up/Down navigate . Enter select . Esc close'}</Text>
    </Box>
  );
};
