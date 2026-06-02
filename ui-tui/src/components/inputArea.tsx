import React, { useState, useCallback } from 'react';
import { Box, Text } from 'ink';
import TextInput from 'ink-text-input';
import { theme } from '../theme';
import { CompletionList, SLASH_COMMANDS } from './completionList';

interface InputAreaProps {
  onSubmit: (value: string) => void;
  isBusy: boolean;
}

export const InputArea: React.FC<InputAreaProps> = ({ onSubmit, isBusy }) => {
  const [value, setValue] = useState('');
  const [showCompletions, setShowCompletions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filtered = value.startsWith('/')
    ? SLASH_COMMANDS.filter(c => c.label.startsWith(value))
    : [];

  const handleSubmit = (val: string) => {
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
      <Box flexDirection="row">
        <Text color={theme.accent.blue} bold>{'> '}</Text>
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
