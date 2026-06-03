// ui-tui/src/components/banner.tsx
import React, { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface BannerProps {
  version: string;
  model: string;
}

const LOGO = [
  ' ███████╗██╗   ██╗██████╗ ██╗███╗   ██╗██╗███╗   ██╗██████╗ ',
  ' ██╔════╝██║   ██║██╔══██╗██║████╗  ██║██║████╗  ██║██╔══██╗',
  ' ███████╗██║   ██║██████╔╝██║██╔██╗ ██║██║██╔██╗ ██║██║  ██║',
  ' ╚════██║██║   ██║██╔══██╗██║██║╚██╗██║██║██║╚██╗██║██║  ██║',
  ' ███████║╚██████╔╝██║  ██║██║██║ ╚████║██║██║ ╚████║██████╔╝',
  ' ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝╚═════╝ ',
];

export const Banner: React.FC<BannerProps> = ({ version, model }) => {
  const [showLogo, setShowLogo] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShowLogo(false), 2000);
    return () => clearTimeout(timer);
  }, []);

  if (showLogo) {
    return (
      <Box flexDirection="column" paddingX={1} paddingBottom={1}>
        {LOGO.map((line, i) => (
          <Text key={i} color={theme.accent.cyan} bold>{line}</Text>
        ))}
        <Text color={theme.txt.secondary}>{'Research Unified Machine Intelligence'}</Text>
        <Text color={theme.txt.muted}>{` v${version} | ${model}`}</Text>
      </Box>
    );
  }

  return (
    <Box paddingX={1} paddingBottom={1}>
      <Text color={theme.accent.cyan} bold>{'RUMI'}</Text>
      <Text color={theme.txt.muted}>{` | ${model}`}</Text>
    </Box>
  );
};
