// ui-tui/src/components/streaming.tsx
import React, { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface StreamingProps {
  content: string;
  isActive: boolean;
}

const THINKING_STEPS = [
  'Searching literature',
  'Extracting entities',
  'Building graph',
  'Detecting anomalies',
  'Generating hypotheses',
];

const SPINNER = ['|', '/', '-', '\\'];

export const Streaming: React.FC<StreamingProps> = ({ content, isActive }) => {
  const [stepIdx, setStepIdx] = useState(0);
  const [spinIdx, setSpinIdx] = useState(0);

  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(() => {
      setSpinIdx(prev => (prev + 1) % SPINNER.length);
    }, 150);
    return () => clearInterval(interval);
  }, [isActive]);

  useEffect(() => {
    if (!isActive) return;
    const interval = setInterval(() => {
      setStepIdx(prev => (prev + 1) % THINKING_STEPS.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [isActive]);

  if (!isActive && !content) return null;

  if (isActive && !content) {
    return (
      <Box flexDirection="column" paddingLeft={1}>
        <Text color={theme.accent.cyan} bold>{'[THINKING]'}</Text>
        <Text color={theme.txt.muted}>{'  '}{SPINNER[spinIdx]}{' Thinking...'}</Text>
        {THINKING_STEPS.slice(0, stepIdx + 1).map((step, i) => (
          <Text key={i} color={theme.txt.secondary}>
            {i === stepIdx ? `  ${SPINNER[spinIdx]} ${step}...` : `  + ${step}`}
          </Text>
        ))}
      </Box>
    );
  }

  return (
    <Box flexDirection="column" marginBottom={1} paddingLeft={1}>
      <Text color={theme.txt.primary} wrap="wrap">
        {content}
      </Text>
    </Box>
  );
};
