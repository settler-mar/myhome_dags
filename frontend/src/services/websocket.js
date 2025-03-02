const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const host = window.location.host;
const wsUrl = `${protocol}//${host}/ws`;

export class WebSocketService {
  constructor(url) {
    this.url = url;
    this.socket = null;
    this.listeners = new Map();
    this.retryCount = 0;
    this.MAX_RETRIES = 5;
    this.connect();
    this.state = 'disconnected';
  }

  connect() {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      this.state = 'connecting';
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        this.state = 'connected';
        console.info("ws: connected");
        this.retryCount = 0; // Сбросить счётчик при успешном подключении
      };

      this.socket.onmessage = (event) => {
        console.log("ws: message:", event.data);
        const data = JSON.parse(event.data);
        const eventKey = `${data.type}:${data.action}`;
        const payload = data.data;
        if (this.listeners.has(eventKey)) {
          this.listeners.get(eventKey).forEach((callback) => callback(payload));
        }
      };

      this.socket.onclose = () => {
        this.state = 'disconnected';
        if (this.retryCount < this.MAX_RETRIES) {
          console.warn("ws: disconnected, retrying...");
          this.retryCount++;
          setTimeout(() => this.connect(), 3000 * this.retryCount); // Экспоненциальная задержка
        } else {
          this.state = 'disconnected';
          console.error("ws: disconnected, max retries exceeded");
        }
      };

      this.socket.onerror = (error) => {
        this.state = 'error';
        console.error("ws: error:", error);
        this.socket.close();
      };
    }
  }

  onMessage(group, type, callback) {
    const eventKey = `${group}:${type}`;
    if (!this.listeners.has(eventKey)) {
      this.listeners.set(eventKey, []);
    }
    this.listeners.get(eventKey).push(callback);
  }

  offMessage(group, type, callback) {
    const eventKey = `${group}:${type}`;
    if (this.listeners.has(eventKey)) {
      const callbacks = this.listeners.get(eventKey).filter((cb) => cb !== callback);
      if (callbacks.length > 0) {
        this.listeners.set(eventKey, callbacks);
      } else {
        this.listeners.delete(eventKey);
      }
    }
  }
}

const webSocketService = new WebSocketService(wsUrl);

export {webSocketService};
