import React, { useState } from 'react';
import { Box, Text } from 'ink';
import { theme } from '../theme';

interface BannerSection {
  title: string;
  content: string[];
  defaultOpen?: boolean;
}

interface BannerProps {
  version: string;
  model: string;
  domains: number;
  modules: number;
  sections?: BannerSection[];
}

export const Banner: React.FC<BannerProps> = ({
  version, model, domains, modules, sections = [],
}) => {
  const [openSections, setOpenSections] = useState<Set<number>>(() => {
    const open = new Set<number>();
    sections.forEach((s, i) => { if (s.defaultOpen) open.add(i); });
    return open;
  });

  const toggle = (idx: number) => {
    setOpenSections(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <Box flexDirection="column" paddingX={1} paddingBottom={1}>
      <Box>
        <Text color={theme.accent.blue} bold>{'RUMI'}</Text>
        <Text color={theme.txt.muted}>{` v${version} · `}</Text>
        <Text color={theme.txt.secondary}>{model}</Text>
        <Text color={theme.txt.muted}>{` · ${domains} domains · ${modules} modules`}</Text>
      </Box>
      {sections.map((section, idx) => {
        const isOpen = openSections.has(idx);
        const chevron = isOpen ? '▾' : '▸';
        return (
          <Box key={idx} paddingLeft={1}>
            <Text color={theme.txt.muted}>
              {chevron}{' '}{section.title}
            </Text>
            {isOpen && section.content.map((line, li) => (
              <Box key={li} paddingLeft={3}>
                <Text color={theme.txt.secondary}>
                  {line}
                </Text>
              </Box>
            ))}
          </Box>
        );
      })}
    </Box>
  );
};
