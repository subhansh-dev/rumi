// ui-tui/src/components/completionList.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface CompletionItem {
  label: string;
  description: string;
}

interface CompletionListProps {
  items: CompletionItem[];
  selectedIndex: number;
  visible: boolean;
}

export const SLASH_COMMANDS: CompletionItem[] = [
  { label: '/discover', description: 'Full discovery pipeline' },
  { label: '/search', description: 'Search papers' },
  { label: '/hypothesize', description: 'Generate hypotheses' },
  { label: '/experiment', description: 'Design experiment' },
  { label: '/review', description: 'Peer review' },
  { label: '/graph', description: 'Knowledge graph stats' },
  { label: '/dashboard', description: 'Discovery dashboard' },
  { label: '/domains', description: 'List 17 domains' },
  { label: '/status', description: 'System status' },
  { label: '/stats', description: 'Session stats' },
  { label: '/timeline', description: 'Session timeline' },
  { label: '/think', description: 'Toggle think mode' },
  { label: '/dive', description: 'Toggle deep dive' },
  { label: '/personality', description: 'Switch personality' },
  { label: '/clear', description: 'Clear screen' },
  { label: '/help', description: 'Show help' },
  { label: '/exit', description: 'Shut down' },
];

export const CompletionList: React.FC<CompletionListProps> = ({
  items, selectedIndex, visible,
}) => {
  if (!visible || items.length === 0) return null;
  return (
    <Box flexDirection="column" paddingLeft={1}>
      {items.map((item, idx) => (
        <Box key={item.label}>
          <Text color={idx === selectedIndex ? theme.accent.cyan : theme.txt.primary} bold={idx === selectedIndex}>
            {idx === selectedIndex ? '> ' : '  '}
            {item.label}
          </Text>
          <Text color={theme.txt.muted}>{'  '}{item.description}</Text>
        </Box>
      ))}
    </Box>
  );
};
