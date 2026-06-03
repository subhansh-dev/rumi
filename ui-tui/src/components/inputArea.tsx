// ui-tui/src/components/inputArea.tsx
import React, { useState } from 'react';
import { Box, Text } from 'ink';
import TextInput from 'ink-text-input';
import { theme } from '../theme';
import { CompletionList, SLASH_COMMANDS } from './completionList';

interface InputAreaProps {
  onSubmit: (value: string) => void;
  isBusy: boolean;
  disabled?: boolean;
}

export const InputArea: React.FC<InputAreaProps> = ({ onSubmit, isBusy, disabled = false }) => {
  const [value, setValue] = useState('');
  const [showCompletions, setShowCompletions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filtered = value.startsWith('/')
    ? SLASH_COMMANDS.filter(c => c.label.startsWith(value))
    : [];

  const handleSubmit = (val: string) => {
    if (disabled) return;
    const trimmed = val.trim();
    if (!trimmed) return;
    if (showCompletions && filtered.length > 0) {
      setValue(filtered[selectedIndex].label + ' ');
      setShowCompletions(false);
      return;
    }
    setValue('');
    setShowCompletions(false);
    onSubmit(trimmed);
  };

  const handleChange = (val: string) => {
    setValue(val);
    if (val.startsWith('/') && val.length > 0) {
      setShowCompletions(true);
      setSelectedIndex(0);
    } else {
      setShowCompletions(false);
    }
  };

  return (
    <Box flexDirection="column">
      <CompletionList items={filtered} selectedIndex={selectedIndex} visible={showCompletions} />
      <Box flexDirection="row" paddingX={1}>
        <Text color={theme.accent.cyan} bold>{'> '}</Text>
        <TextInput
          value={value}
          onChange={handleChange}
          onSubmit={handleSubmit}
          placeholder={isBusy ? 'queuing...' : 'ask RUMI anything...'}
        />
      </Box>
    </Box>
  );
};
