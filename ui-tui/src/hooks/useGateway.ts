import { useEffect, useState, useCallback, useRef } from 'react';
import { GatewayClient } from '../gateway/client';
import { useTranscript } from './useTranscript';
import { ToolCall } from '../components/toolTrail';

export function useGateway() {
  const clientRef = useRef<GatewayClient | null>(null);
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState('READY');
  const [model] = useState('Gemini 2.5');
  const [tokens, setTokens] = useState(0);
  const [cost, setCost] = useState(0);
  const [uptime, setUptime] = useState(0);
  const [thinkMode, setThinkMode] = useState(false);
  const [diveMode, setDiveMode] = useState(false);
  const [tools, setTools] = useState<ToolCall[]>([]);
  const [discovery, setDiscovery] = useState({
    topic: '', progress: 0, phase: '', isActive: false,
    papers: 0, entities: 0, edges: 0,
  });
  const [elapsed, setElapsed] = useState(0);
  const [queuedMessages, setQueuedMessages] = useState<string[]>([]);
  const [sessions, setSessions] = useState<Array<{id: string; title: string; model: string; messages: number}>>([]);
  const transcript = useTranscript();
  const elapsedIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const client = new GatewayClient();
    clientRef.current = client;

    client.onEvent((method, params) => {
      switch (method) {
        case 'gateway.ready':
          setConnected(true);
          client.send('session.create', {});
          break;
        case 'assistant.message':
          transcript.addAssistantMessage(params.content as string);
          break;
        case 'assistant.stream':
          transcript.appendStream(params.delta as string);
          break;
        case 'assistant.done':
          transcript.addAssistantMessage(transcript.streamingContent);
          if (params.tokens) setTokens(t => t + (params.tokens as number));
          if (params.cost) setCost(c => c + (params.cost as number));
          break;
        case 'user.message':
          transcript.addUserMessage(params.content as string);
          break;
        case 'system.message':
          transcript.addSystemMessage(params.content as string);
          break;
        case 'tool.start':
          setTools(prev => [...prev, {
            id: `tool-${Date.now()}`,
            name: params.name as string,
            query: params.query as string,
            status: 'running',
            isLast: true,
          }]);
          break;
        case 'tool.complete':
          setTools(prev => prev.map(t =>
            t.status === 'running' && t.name === params.name
              ? { ...t, status: 'done' as const, elapsed: params.elapsed as number, result: params.result as string }
              : { ...t, isLast: false }
          ));
          break;
        case 'discovery.phase':
          setDiscovery(prev => ({
            ...prev,
            phase: params.phase as string,
            progress: params.progress as number,
            topic: params.topic as string,
            isActive: true,
          }));
          break;
        case 'discovery.done':
          setDiscovery(prev => ({
            ...prev,
            isActive: false,
            papers: params.papers as number,
            entities: params.entities as number,
            edges: params.edges as number,
          }));
          break;
        case 'metrics.update':
          setTokens(params.tokens as number);
          setCost(params.cost as number);
          break;
        case 'state.update':
          setState(params.state as string);
          break;
        case 'thinking.start':
          setState('THINKING');
          setElapsed(0);
          if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
          elapsedIntervalRef.current = setInterval(() => setElapsed(prev => prev + 1), 1000);
          break;
        case 'thinking.done':
          setState('IDLE');
          if (elapsedIntervalRef.current) {
            clearInterval(elapsedIntervalRef.current);
            elapsedIntervalRef.current = null;
          }
          break;
        case 'session.list':
          setSessions(params.sessions as Array<{id: string; title: string; model: string; messages: number}>);
          break;
        case 'error':
          transcript.addErrorMessage(params.message as string);
          break;
      }
    });

    const interval = setInterval(() => setUptime(prev => prev + 1), 1000);
    return () => {
      if (elapsedIntervalRef.current) clearInterval(elapsedIntervalRef.current);
      clearInterval(interval);
      client.destroy();
    };
  }, []);

  const sendMessage = useCallback((content: string) => {
    transcript.addUserMessage(content);
    clientRef.current?.send('chat.send', { content });
  }, []);

  const interrupt = useCallback(() => {
    clientRef.current?.send('chat.interrupt', {});
  }, []);

  const executeSlash = useCallback((command: string) => {
    const parts = command.slice(1).split(' ');
    const cmd = parts[0];
    const args = parts.slice(1).join(' ');
    clientRef.current?.send('slash.execute', { command: cmd, args });
  }, []);

  return {
    connected, state, model, tokens, cost, uptime,
    thinkMode, diveMode, tools, discovery,
    elapsed, queuedMessages, sessions,
    transcript, sendMessage, interrupt, executeSlash,
  };
}
