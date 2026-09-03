// Minimal frontend behavior: draw a grid and provide WebSocket placeholder
const canvas = document.getElementById('mapCanvas');
const ctx = canvas.getContext('2d');
const logEl = document.getElementById('log');
const inputEl = document.getElementById('input');
const connectBtn = document.getElementById('connectBtn');

function log(...args) {
  const line = document.createElement('div');
  line.textContent = args.map(a => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' ');
  logEl.appendChild(line);
  logEl.scrollTop = logEl.scrollHeight;
}

function drawGrid() {
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = '#222';
  const size = 40;
  for (let x = 0; x <= w; x += size) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 0; y <= h; y += size) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
  // sample token
  ctx.fillStyle = '#ffb86b';
  ctx.beginPath();
  ctx.arc(100, 100, 12, 0, Math.PI * 2);
  ctx.fill();
}

drawGrid();

let ws = null;

function connect() {
  if (ws) {
    ws.close();
    ws = null;
    connectBtn.textContent = 'Connect';
    log('WebSocket disconnected');
    return;
  }
  const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.hostname + ':8000/ws';
  log('Connecting to', wsUrl);
  ws = new WebSocket(wsUrl);
  ws.onopen = () => {
    log('WS open');
    connectBtn.textContent = 'Disconnect';
  };
  ws.onmessage = (ev) => {
    log('WS message:', ev.data);
  };
  ws.onclose = () => {
    log('WS closed');
    connectBtn.textContent = 'Connect';
    ws = null;
  };
  ws.onerror = (e) => {
    log('WS error', e);
  };
}

connectBtn.addEventListener('click', connect);

inputEl.addEventListener('keydown', (ev) => {
  if (ev.key === 'Enter') {
    const v = inputEl.value.trim();
    if (!v) return;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(v);
      log('Sent:', v);
    } else {
      log('No WebSocket connection - not sent');
    }
    inputEl.value = '';
  }
});
