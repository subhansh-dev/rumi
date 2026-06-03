// ui-tui/src/components/discoveryPanel.tsx
import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface DiscoveryPanelProps {
  topic: string;
  progress: number;
  phase: string;
  papers: number;
  entities: number;
  edges: number;
  isActive: boolean;
}

const PIPELINE_STEPS = [
  'Literature',
  'Knowledge Graph',
  'Gap Detection',
  'Anomaly Detection',
  'Hidden Variables',
  'Mechanisms',
  'Predictions',
  'Verification',
];

export const DiscoveryPanel: React.FC<DiscoveryPanelProps> = ({
  topic, progress, phase, papers, entities, edges, isActive,
}) => {
  if (!isActive && progress === 0) return null;

  const completedSteps = Math.floor((progress / 100) * PIPELINE_STEPS.length);
  const currentStep = PIPELINE_STEPS.findIndex(s => s.toLowerCase().includes(phase.toLowerCase()));

  return (
    <Box flexDirection="column" paddingX={1} paddingBottom={1}>
      <Text color={theme.accent.blue} bold>{'[DISCOVERY]'}</Text>
      {topic && <Text color={theme.txt.primary}>{'  '}{topic}</Text>}
      <Box flexDirection="column">
        {PIPELINE_STEPS.map((step, i) => {
          let icon = 'o';
          let color: string = theme.txt.muted;
          if (i < completedSteps || (currentStep >= 0 && i < currentStep)) {
            icon = '+';
            color = theme.accent.green;
          } else if (i === currentStep || (currentStep < 0 && i === completedSteps)) {
            icon = '>';
            color = theme.accent.cyan;
          }
          return (
            <Text key={i} color={color}>
              {'  '}{icon}{' '}{step}
            </Text>
          );
        })}
      </Box>
      <Text color={theme.txt.muted}>{'  '}{papers} papers | {entities} entities | {edges} edges</Text>
    </Box>
  );
};
