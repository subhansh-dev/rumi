// ui-tui/src/components/toolTrail.tsx
import React, { useState } from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

export interface ToolCall {
  id: string;
  name: string;
  query: string;
  status: 'running' | 'done' | 'error';
  elapsed?: number;
  result?: string;
  isLast: boolean;
}

interface ToolTrailProps {
  tools: ToolCall[];
}

export const ToolTrail: React.FC<ToolTrailProps> = ({ tools }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (tools.length === 0) return null;

  return (
    <Box flexDirection="column" paddingLeft={1}>
      <Text color={theme.accent.blue} bold>{'[TOOLS]'}</Text>
      {tools.map(tool => (
        <ToolLine
          key={tool.id}
          tool={tool}
          isExpanded={expandedId === tool.id}
          onToggle={() => setExpandedId(prev => prev === tool.id ? null : tool.id)}
        />
      ))}
    </Box>
  );
};

interface ToolLineProps {
  tool: ToolCall;
  isExpanded: boolean;
  onToggle: () => void;
}

const ToolLine: React.FC<ToolLineProps> = ({ tool, isExpanded, onToggle }) => {
  const prefix = tool.isLast ? '`-' : '|-';
  const icon = tool.status === 'done' ? '+' : tool.status === 'error' ? '!' : '...';
  const iconColor = tool.status === 'done'
    ? theme.accent.green
    : tool.status === 'error'
    ? theme.accent.red
    : theme.accent.amber;

  const elapsedStr = tool.elapsed != null ? ` (${tool.elapsed.toFixed(1)}s)` : '';

  return (
    <Box flexDirection="column">
      <Box>
        <Text color={theme.txt.muted}>{prefix} </Text>
        <Text color={iconColor} bold>{icon} </Text>
        <Text color={theme.txt.primary} bold>
          {tool.name}
        </Text>
        {tool.query && (
          <Text color={theme.txt.secondary}> {tool.query.slice(0, 50)}</Text>
        )}
        <Text color={theme.txt.muted}>{elapsedStr}</Text>
      </Box>
      {isExpanded && tool.result && (
        <Box paddingLeft={4}>
          <Text color={theme.txt.secondary} wrap="wrap">
            {tool.result.slice(0, 500)}
          </Text>
        </Box>
      )}
    </Box>
  );
};
