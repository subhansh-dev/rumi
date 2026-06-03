// ui-tui/src/components/helpOverlay.tsx
import React from 'react';
import { Box, Text, useInput } from 'ink';
import { theme } from '../theme';

interface HelpOverlayProps {
  visible: boolean;
  onClose: () => void;
}

export const HelpOverlay: React.FC<HelpOverlayProps> = ({ visible, onClose }) => {
  useInput((input, key) => {
    if (!visible) return;
    if (key.escape || input === '?') onClose();
  });

  if (!visible) return null;

  return (
    <Box flexDirection="column" padding={1} width="80%">
      <Text color={theme.accent.cyan} bold>{'[KEYBOARD SHORTCUTS]'}</Text>
      <Text color={theme.txt.muted}>{'='.repeat(44)}</Text>
      <Text color={theme.txt.primary}>{'  Enter        Send message'}</Text>
      <Text color={theme.txt.primary}>{'  Escape       Interrupt / close overlay'}</Text>
      <Text color={theme.txt.primary}>{'  Ctrl+K       Command palette'}</Text>
      <Text color={theme.txt.primary}>{'  Ctrl+X       Session switcher'}</Text>
      <Text color={theme.txt.primary}>{'  Ctrl+L       Clear screen'}</Text>
      <Text color={theme.txt.primary}>{'  ?            Show this help'}</Text>
      <Text color={theme.txt.primary}>{'  Up/Down      Navigate history'}</Text>
      <Text color={theme.txt.primary}>{'  Tab          Accept autocomplete'}</Text>
      <Text color={theme.txt.muted}>{'='.repeat(44)}</Text>
      <Text color={theme.accent.cyan} bold>{'  Slash Commands'}</Text>
      <Text color={theme.txt.primary}>{'  /discover <topic>   Full discovery pipeline'}</Text>
      <Text color={theme.txt.primary}>{'  /search <query>     Search papers'}</Text>
      <Text color={theme.txt.primary}>{'  /think              Toggle think mode'}</Text>
      <Text color={theme.txt.primary}>{'  /dive               Toggle deep dive'}</Text>
      <Text color={theme.txt.primary}>{'  /status             System status'}</Text>
      <Text color={theme.txt.primary}>{'  /clear              Clear screen'}</Text>
      <Text color={theme.txt.primary}>{'  /help               Show help'}</Text>
      <Text color={theme.txt.muted}>{'='.repeat(44)}</Text>
      <Text color={theme.txt.muted}>{' Press ? or Esc to close'}</Text>
    </Box>
  );
};
