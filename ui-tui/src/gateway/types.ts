// ui-tui/src/gateway/types.ts

export interface JsonRpcRequest {
  jsonrpc: '2.0';
  id: number | string;
  method: string;
  params: Record<string, unknown>;
}

export interface JsonRpcResponse {
  jsonrpc: '2.0';
  id: number | string;
  result?: unknown;
  error?: { code: number; message: string };
}

export interface JsonRpcEvent {
  jsonrpc: '2.0';
  method: string;
  params: Record<string, unknown>;
}

export interface AssistantMessageEvent {
  content: string;
}

export interface ToolStartEvent {
  name: string;
  query: string;
}

export interface ToolCompleteEvent {
  name: string;
  result: string;
  elapsed?: number;
}

export interface DiscoveryPhaseEvent {
  phase: string;
  progress: number;
  topic: string;
}

export interface MetricsUpdateEvent {
  tokens: number;
  cost: number;
  latency: number;
}

export interface GraphUpdateEvent {
  nodes: number;
  edges: number;
  clusters: number;
  papers: number;
  entities: number;
  relationships: number;
}

export interface StateUpdateEvent {
  state: string;
}

export type GatewayEventType =
  | 'gateway.ready'
  | 'assistant.message'
  | 'assistant.stream'
  | 'assistant.done'
  | 'user.message'
  | 'system.message'
  | 'tool.start'
  | 'tool.complete'
  | 'tool.error'
  | 'discovery.phase'
  | 'discovery.done'
  | 'metrics.update'
  | 'graph.update'
  | 'state.update'
  | 'thinking.start'
  | 'thinking.done'
  | 'error';
