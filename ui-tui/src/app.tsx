import React, { useState, useCallback } from 'react';
import { Box, useInput } from 'ink';
import { theme } from './theme';
import { useGateway } from './hooks/useGateway';
import { Banner } from './components/banner';
import { Transcript } from './components/transcript';
import { Streaming } from './components/streaming';
import { ToolTrail } from './components/toolTrail';
import { StatusBar } from './components/statusBar';
import { InputArea } from './components/inputArea';
import { CommandPalette } from './components/commandPalette';
import { SessionSwitcher } from './components/sessionSwitcher';
import { DiscoveryPanel } from './components/discoveryPanel';

export const App: React.FC = () => {
  const gw = useGateway();
  const [showPalette, setShowPalette] = useState(false);
  const [showSwitcher, setShowSwitcher] = useState(false);

  useInput((input, key) => {
    if (key.ctrl && input === 'k') {
      setShowPalette(prev => !prev);
      setShowSwitcher(false);
    } else if (key.ctrl && input === 'x') {
      setShowSwitcher(prev => !prev);
      setShowPalette(false);
    } else if (key.ctrl && input === 'l') {
      gw.transcript.clear();
    } else if (key.escape) {
      if (showPalette) setShowPalette(false);
      else if (showSwitcher) setShowSwitcher(false);
      else gw.interrupt();
    }
  });

  const handleInput = useCallback((value: string) => {
    if (value.startsWith('/')) gw.executeSlash(value);
    else gw.sendMessage(value);
  }, [gw]);

  const handleSlashFromPalette = useCallback((command: string) => {
    setShowPalette(false);
    gw.executeSlash(command);
  }, [gw]);

  return (
    <Box flexDirection="column" height="100%">
      <Banner
        version="3.0"
        model={gw.model}
        domains={17}
        modules={48}
        sections={[
          { title: 'Tools', content: ['search, discover, hypothesize, experiment, review, graph'], defaultOpen: true },
          { title: 'Skills', content: ['discovery_engine, knowledge_graph, novelty_checker'], defaultOpen: false },
        ]}
      />
      <DiscoveryPanel
        topic={gw.discovery.topic}
        progress={gw.discovery.progress}
        phase={gw.discovery.phase}
        papers={gw.discovery.papers}
        entities={gw.discovery.entities}
        edges={gw.discovery.edges}
        isActive={gw.discovery.isActive}
      />
      <Box flexDirection="column" flexShrink={1} overflow="hidden">
        <Transcript entries={gw.transcript.entries} />
        <Streaming
          content={gw.transcript.streamingContent}
          isActive={gw.state === 'THINKING' || gw.state === 'PROCESSING'}
        />
        <ToolTrail tools={gw.tools} />
      </Box>
      <StatusBar
        state={gw.state}
        model={gw.model}
        tokens={gw.tokens}
        cost={gw.cost}
        uptime={gw.uptime}
        thinkMode={gw.thinkMode}
        diveMode={gw.diveMode}
      />
      <InputArea onSubmit={handleInput} isBusy={gw.state !== 'READY' && gw.state !== 'IDLE'} />
      <CommandPalette visible={showPalette} onSelect={handleSlashFromPalette} onClose={() => setShowPalette(false)} />
      <SessionSwitcher sessions={[]} visible={showSwitcher} onSelect={() => {}} onNew={() => setShowSwitcher(false)} onClose={() => setShowSwitcher(false)} />
    </Box>
  );
};
