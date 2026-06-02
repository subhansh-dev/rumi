// ui-tui/src/gateway/client.ts
import * as readline from 'readline';
import { JsonRpcRequest, JsonRpcResponse, JsonRpcEvent } from './types';

type EventHandler = (method: string, params: Record<string, unknown>) => void;

let _nextId = 1;

export class GatewayClient {
  private pending = new Map<number | string, {
    resolve: (result: unknown) => void;
    reject: (error: Error) => void;
  }>();
  private handlers: EventHandler[] = [];
  private rl: readline.Interface;

  constructor() {
    this.rl = readline.createInterface({
      input: process.stdin,
      terminal: false,
    });

    this.rl.on('line', (line: string) => {
      this.handleLine(line.trim());
    });

    this.rl.on('close', () => {
      this.emit('gateway.close', {});
    });
  }

  private handleLine(line: string) {
    if (!line) return;

    let msg: JsonRpcResponse | JsonRpcEvent;
    try {
      msg = JSON.parse(line);
    } catch {
      return;
    }

    if ('id' in msg && msg.id !== undefined) {
      const resp = msg as JsonRpcResponse;
      const pending = this.pending.get(resp.id);
      if (pending) {
        this.pending.delete(resp.id);
        if (resp.error) {
          pending.reject(new Error(resp.error.message));
        } else {
          pending.resolve(resp.result);
        }
      }
    } else if ('method' in msg) {
      const evt = msg as JsonRpcEvent;
      this.emit(evt.method, evt.params);
    }
  }

  private emit(method: string, params: Record<string, unknown>) {
    for (const handler of this.handlers) {
      handler(method, params);
    }
  }

  onEvent(handler: EventHandler) {
    this.handlers.push(handler);
  }

  async send(method: string, params: Record<string, unknown> = {}): Promise<unknown> {
    const id = _nextId++;
    const request: JsonRpcRequest = {
      jsonrpc: '2.0',
      id,
      method,
      params,
    };

    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      process.stdout.write(JSON.stringify(request) + '\n');
    });
  }

  emitLocal(method: string, params: Record<string, unknown>) {
    this.emit(method, params);
  }

  destroy() {
    this.rl.close();
  }
}
