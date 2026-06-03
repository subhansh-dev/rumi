import WebSocket from 'ws';

export type WsStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';
export type WsMessageHandler = (data: string) => void;
export type WsStatusHandler = (status: WsStatus) => void;

export class WsConnection {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 10000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private messageHandlers: WsMessageHandler[] = [];
  private statusHandlers: WsStatusHandler[] = [];
  private _status: WsStatus = 'disconnected';

  constructor(url = 'ws://127.0.0.1:18789') {
    this.url = url;
  }

  get status(): WsStatus {
    return this._status;
  }

  connect() {
    this.setStatus('connecting');
    this.ws = new WebSocket(this.url);

    this.ws.on('open', () => {
      this.setStatus('connected');
      this.reconnectDelay = 1000;
    });

    this.ws.on('message', (data: WebSocket.Data) => {
      const line = data.toString();
      for (const handler of this.messageHandlers) {
        handler(line);
      }
    });

    this.ws.on('close', () => {
      this.setStatus('disconnected');
      this.scheduleReconnect();
    });

    this.ws.on('error', () => {
      this.ws?.close();
    });
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.setStatus('reconnecting');
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
  }

  private setStatus(status: WsStatus) {
    this._status = status;
    for (const handler of this.statusHandlers) {
      handler(status);
    }
  }

  onMessage(handler: WsMessageHandler) {
    this.messageHandlers.push(handler);
  }

  onStatus(handler: WsStatusHandler) {
    this.statusHandlers.push(handler);
  }

  send(data: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    }
  }

  close() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }
}
