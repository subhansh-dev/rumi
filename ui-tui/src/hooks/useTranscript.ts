// ui-tui/src/hooks/useTranscript.ts
import { useState, useCallback } from 'react';

export interface TranscriptEntry {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'error';
  content: string;
  timestamp: number;
}

export function useTranscript() {
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [streamingContent, setStreamingContent] = useState('');

  const addUserMessage = useCallback((content: string) => {
    setEntries(prev => [...prev, {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: Date.now(),
    }]);
  }, []);

  const addAssistantMessage = useCallback((content: string) => {
    setStreamingContent('');
    setEntries(prev => [...prev, {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content,
      timestamp: Date.now(),
    }]);
  }, []);

  const appendStream = useCallback((delta: string) => {
    setStreamingContent(prev => prev + delta);
  }, []);

  const addSystemMessage = useCallback((content: string) => {
    setEntries(prev => [...prev, {
      id: `system-${Date.now()}`,
      role: 'system',
      content,
      timestamp: Date.now(),
    }]);
  }, []);

  const addErrorMessage = useCallback((content: string) => {
    setEntries(prev => [...prev, {
      id: `error-${Date.now()}`,
      role: 'error',
      content,
      timestamp: Date.now(),
    }]);
  }, []);

  const clear = useCallback(() => {
    setEntries([]);
    setStreamingContent('');
  }, []);

  return {
    entries,
    streamingContent,
    addUserMessage,
    addAssistantMessage,
    appendStream,
    addSystemMessage,
    addErrorMessage,
    clear,
  };
}
