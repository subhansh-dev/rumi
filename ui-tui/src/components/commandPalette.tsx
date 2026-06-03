// ui-tui/src/components/commandPalette.tsx
import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import { theme } from '../theme';

interface PaletteItem {
  key: string;
  label: string;
  command: string;
}

const PALETTE_ITEMS: PaletteItem[] = [
  { key: 'discover', label: 'Run Discovery Pipeline', command: '/discover ' },
  { key: 'search', label: 'Search Papers', command: '/search ' },
  { key: 'hypothesize', label: 'Generate Hypotheses', command: '/hypothesize ' },
  { key: 'experiment', label: 'Design Experiment', command: '/experiment' },
  { key: 'review', label: 'Peer Review', command: '/review' },
  { key: 'graph', label: 'Knowledge Graph', command: '/graph' },
  { key: 'domains', label: 'List Domains', command: '/domains' },
  { key: 'status', label: 'System Status', command: '/status' },
  { key: 'timeline', label: 'Session Timeline', command: '/timeline' },
  { key: 'clear', label: 'Clear Screen', command: '/clear' },
  { key: 'think', label: 'Toggle Think Mode', command: '/think' },
  { key: 'dive', label: 'Toggle Deep Dive', command: '/dive' },
  { key: 'dashboard', label: 'Discovery Dashboard', command: '/dashboard' },
  { key: 'personality', label: 'Switch Personality', command: '/personality' },
];

interface CommandPaletteProps {
  visible: boolean;
  onSelect: (command: string) => void;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  visible, onSelect, onClose,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  useInput((input, key) => {
    if (!visible) return;
    if (key.escape) onClose();
    else if (key.upArrow) setSelectedIndex(prev => (prev > 0 ? prev - 1 : PALETTE_ITEMS.length - 1));
    else if (key.downArrow) setSelectedIndex(prev => (prev < PALETTE_ITEMS.length - 1 ? prev + 1 : 0));
    else if (key.return) onSelect(PALETTE_ITEMS[selectedIndex].command);
  });

  if (!visible) return null;

  return (
    <Box flexDirection="column" padding={1} width="60%">
      <Text color={theme.accent.cyan} bold>{'[COMMANDS]'}</Text>
      <Text color={theme.txt.muted}>{'--'.repeat(25)}</Text>
      {PALETTE_ITEMS.map((item, idx) => (
        <Box key={item.key}>
          <Text color={idx === selectedIndex ? theme.accent.cyan : theme.txt.primary} bold={idx === selectedIndex}>
            {idx === selectedIndex ? ' > ' : '   '}
          </Text>
          <Text color={theme.txt.primary}>{item.label}</Text>
          <Text color={theme.txt.muted}>{'  '}{item.command}</Text>
        </Box>
      ))}
      <Text color={theme.txt.muted}>{'--'.repeat(25)}</Text>
      <Text color={theme.txt.muted}>{' Up/Down navigate . Enter select . Esc close'}</Text>
    </Box>
  );
};
