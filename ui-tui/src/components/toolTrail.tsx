import React from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

export interface ToolCall {
  id: string;
  name: string;
  query: string;
  status: 'running' | 'done' | 'error';
  elapsed?: number;
  isLast: boolean;
}

interface ToolTrailProps {
  tools: ToolCall[];
}

export const ToolTrail: React.FC<ToolTrailProps> = ({ tools }) => {
  if (tools.length === 0) return null;

  return (
    <Box flexDirection="column" paddingLeft={1}>
      {tools.map(tool => (
        <ToolLine key={tool.id} tool={tool} />
      ))}
    </Box>
  );
};

const ToolLine: React.FC<{ tool: ToolCall }> = ({ tool }) => {
  const prefix = tool.isLast ? '└─' : '├─';
  const icon = tool.status === 'done' ? '✓' : tool.status === 'error' ? '✗' : '○';
  const iconColor = tool.status === 'done'
    ? theme.accent.green
    : tool.status === 'error'
    ? theme.accent.red
    : theme.accent.amber;

  const elapsedStr = tool.elapsed != null ? ` (${tool.elapsed.toFixed(1)}s)` : '';

  return (
    <Box>
      <Text color={theme.txt.muted}>{prefix} </Text>
      <Text color={iconColor} bold>{icon} </Text>
      <Text color={theme.accent.blue} bold>{tool.name}</Text>
      {tool.query && (
        <Text color={theme.txt.secondary}> {tool.query.slice(0, 40)}</Text>
      )}
      <Text color={theme.txt.muted}>{elapsedStr}</Text>
    </Box>
  );
};
