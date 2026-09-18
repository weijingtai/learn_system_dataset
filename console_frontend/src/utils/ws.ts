import { usePipelineStore } from '../stores/pipeline';
import type { WebSocketEvent } from '../types';

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string = '';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 20;
  private reconnectInterval = 3000;
  private reconnectTimer: number | null = null;
  private pingTimer: number | null = null;
  private isExplicitClose = false;

  constructor() {
    const loc = window.location;
    const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    // 在开发模式下，Vite proxy 将 /ws 代理至后端
    this.url = `${proto}//${loc.host}/ws/events`;
  }

  public connect() {
    this.isExplicitClose = false;
    this.cleanup();

    const store = usePipelineStore();

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[WS] Connected to event bus:', this.url);
        this.reconnectAttempts = 0;
        store.setWsConnected(true);
        store.appendLog({
          id: `log_${Date.now()}_ws_conn`,
          timestamp: Date.now(),
          runId: store.currentRunId || 'system',
          level: 'success',
          message: 'WebSocket 实时事件总线已建立连接',
        });
        this.startHeartbeat();
      };

      this.ws.onmessage = (evt) => {
        try {
          const data: WebSocketEvent = JSON.parse(evt.data);
          this.handleEvent(data);
        } catch (err) {
          console.warn('[WS] Received non-JSON message:', evt.data);
        }
      };

      this.ws.onclose = (evt) => {
        console.warn('[WS] Closed with code:', evt.code, evt.reason);
        store.setWsConnected(false);
        this.stopHeartbeat();
        if (!this.isExplicitClose) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (err) => {
        console.error('[WS] Connection error:', err);
        store.setWsConnected(false);
      };
    } catch (e) {
      console.error('[WS] Exception during connect:', e);
      this.scheduleReconnect();
    }
  }

  private handleEvent(data: WebSocketEvent) {
    const store = usePipelineStore();
    console.log('[WS Event Received]', data);

    const eventType = data.eventType || (data as any).event_type;
    const runId = data.runId || (data as any).run_id;
    const logMessage = data.logMessage || (data as any).log_message || '';
    const stage = data.stage;
    const status = data.status;

    if (eventType === 'stage_change') {
      if (stage !== undefined && status !== undefined) {
        store.updateStageStatus(stage, status, logMessage);
      }
    } else if (eventType === 'log_append' || eventType === 'log_event') {
      store.appendLog({
        id: `log_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        timestamp: data.timestamp ? data.timestamp * 1000 : Date.now(),
        runId: runId || store.currentRunId,
        level: 'info',
        message: logMessage,
      });
    } else if (eventType === 'human_ready') {
      store.appendLog({
        id: `log_${Date.now()}_hr`,
        timestamp: Date.now(),
        runId: runId || store.currentRunId,
        level: 'warn',
        message: `人工介入待办就绪：${logMessage || '请进入审校工作台处理分歧项'}`,
      });
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('[WS] Max reconnect attempts reached');
      return;
    }

    if (this.reconnectTimer) return;

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1), 30000);
    console.log(`[WS] Reconnecting in ${Math.round(delay / 1000)}s (attempt ${this.reconnectAttempts})...`);

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.pingTimer = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      }
    }, 25000);
  }

  private stopHeartbeat() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private cleanup() {
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
      this.ws = null;
    }
  }

  public disconnect() {
    this.isExplicitClose = true;
    this.cleanup();
  }

  public send(msg: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } else {
      console.warn('[WS] Cannot send message, socket is not OPEN');
    }
  }
}

export const wsClient = new WebSocketClient();
