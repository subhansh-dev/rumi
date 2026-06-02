// ui-tui/src/entry.tsx
import React from 'react';
import { render, Text, Box } from 'ink';
import { theme } from './theme';

const App: React.FC = () => {
  return (
    <Box flexDirection="column" padding={1}>
      <Text color={theme.accent.blue} bold>
        RUMI TUI v3.0
      </Text>
      <Text color={theme.txt.secondary}>
        Hermes Agent Style — Coming soon
      </Text>
    </Box>
  );
};

render(<App />);
