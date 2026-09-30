import { useAppStore } from '../store/appStore';

const RECONNECT_DELAY_MS = 3000;

let socket = null;
let reconnectTimer = null;
let currentToken = null;
let manualClose = false;

function buildUrl(token) {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws?token=${encodeURIComponent(token)}`;
}

function handleMessage(event) {
  let msg;
  try {
    msg = JSON.parse(event.data);
  } catch {
    return;
  }
  const store = useAppStore.getState();
  switch (msg.type) {
    case 'event_feed':
      store.appendFeedEvent(msg.data);
      break;
    case 'connection_status':
      store.setConnectionStatus(msg.data.profile, msg.data.status);
      break;
    case 'session_expired':
      store.clearSession();
      window.location.assign('/login');
      break;
    default:
      break;
  }
}

function scheduleReconnect() {
  if (manualClose || reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (currentToken) connectWebSocket(currentToken);
  }, RECONNECT_DELAY_MS);
}

export function connectWebSocket(token) {
  currentToken = token;
  manualClose = false;
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }
  socket = new WebSocket(buildUrl(token));
  socket.onmessage = handleMessage;
  socket.onclose = () => {
    socket = null;
    scheduleReconnect();
  };
  socket.onerror = () => {
    if (socket) socket.close();
  };
}

export function disconnectWebSocket() {
  manualClose = true;
  currentToken = null;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) {
    socket.close();
    socket = null;
  }
}
