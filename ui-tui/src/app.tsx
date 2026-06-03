// ui-tui/src/app.tsx
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
import { HelpOverlay } from './components/helpOverlay';
import { QueuedMessages } from './components/queuedMessages';

type Overlay = 'none' | 'palette' | 'switcher' | 'help';

export const App: React.FC = () => {
  const gw = useGateway();
  const [overlay, setOverlay] = useState<Overlay>('none');

  const toggleOverlay = (name: Overlay) => {
    setOverlay(prev => prev === name ? 'none' : name);
  };

  useInput((input, key) => {
    if (key.ctrl && input === 'k') {
      toggleOverlay('palette');
    } else if (key.ctrl && input === 'x') {
      toggleOverlay('switcher');
    } else if (key.ctrl && input === 'l') {
      gw.transcript.clear();
    } else if (input === '?') {
      toggleOverlay('help');
    } else if (key.escape) {
      if (overlay !== 'none') setOverlay('none');
      else gw.interrupt();
    }
  });

  const handleInput = useCallback((value: string) => {
    if (overlay !== 'none') return;
    if (value.startsWith('/')) gw.executeSlash(value);
    else gw.sendMessage(value);
  }, [gw, overlay]);

  const handleSlashFromPalette = useCallback((command: string) => {
    setOverlay('none');
    gw.executeSlash(command);
  }, [gw]);

  return (
    <Box flexDirection="column" height="100%">
      <Banner version="3.1" model={gw.model} />
      <DiscoveryPanel
        topic={gw.discovery.topic}
        progress={gw.discovery.progress}
        phase={gw.discovery.phase}
        papers={gw.discovery.papers}
        entities={gw.discovery.entities}
        edges={gw.discovery.edges}
        isActive={gw.discovery.isActive}
      />
      <Box flexDirection="column" flexShrink={1}>
        <Transcript entries={gw.transcript.entries} />
        <Streaming
          content={gw.transcript.streamingContent}
          isActive={gw.state === 'THINKING' || gw.state === 'PROCESSING'}
        />
        <ToolTrail tools={gw.tools} />
      </Box>
      <QueuedMessages messages={gw.queuedMessages} />
      <StatusBar
        state={gw.state}
        model={gw.model}
        tokens={gw.tokens}
        cost={gw.cost}
        uptime={gw.uptime}
        thinkMode={gw.thinkMode}
        diveMode={gw.diveMode}
        elapsed={gw.elapsed}
      />
      <InputArea
        onSubmit={handleInput}
        isBusy={gw.state !== 'READY' && gw.state !== 'IDLE'}
        disabled={overlay !== 'none'}
      />
      <CommandPalette visible={overlay === 'palette'} onSelect={handleSlashFromPalette} onClose={() => setOverlay('none')} />
      <SessionSwitcher
        sessions={gw.sessions}
        visible={overlay === 'switcher'}
        onSelect={(id) => { setOverlay('none'); }}
        onNew={() => setOverlay('none')}
        onClose={() => setOverlay('none')}
      />
      <HelpOverlay visible={overlay === 'help'} onClose={() => setOverlay('none')} />
    </Box>
  );
};
