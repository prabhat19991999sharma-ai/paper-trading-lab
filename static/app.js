// Modern Trading Dashboard JavaScript
let currentMode = 'PAPER';
let pendingAction = null;
let ws = null;
let lastFeedStatus = null;
const lastQuoteTimes = {};

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);

function init() {
  setupEventListeners();
  connectWebSocket();
  loadInitialData();
  startDataRefresh();
}

function setupEventListeners() {
  // Trading mode toggle
  const paperBtn = document.getElementById('paperMode');
  const liveBtn = document.getElementById('liveMode');

  if (paperBtn) {
    paperBtn.addEventListener('click', () => {
      console.log('Paper mode clicked');
      setTradingMode('PAPER');
    });
  }

  if (liveBtn) {
    liveBtn.addEventListener('click', () => {
      console.log('Live mode clicked');
      setTradingMode('LIVE');
    });
  }

  // Feed control
  const feedToggleBtn = document.getElementById('feedToggleBtn');
  if (feedToggleBtn) {
    feedToggleBtn.addEventListener('click', toggleFeed);
  }

  // Kill switch
  const killBtn = document.getElementById('killSwitchBtn');
  if (killBtn) {
    killBtn.addEventListener('click', showKillSwitchModal);
  }
}

// Trading Mode Management
function setTradingMode(mode) {
  console.log(`Setting trading mode to: ${mode}, Current: ${currentMode}`);
  if (mode === currentMode) return;

  if (mode === 'LIVE') {
    console.log('Showing confirmation modal...');
    // Show confirmation modal for LIVE mode
    showModal(
      `Switch to LIVE trading mode?`,
      'confirm-live'
    );
    pendingAction = () => confirmTradingMode(mode);
  } else {
    // Switch to PAPER without confirmation
    confirmTradingMode(mode);
  }
}

async function confirmTradingMode(mode) {
  try {
    const res = await fetch('/api/trading/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, confirm: true })
    });

    const data = await res.json();

    if (data.success) {
      currentMode = (data.mode || mode).toUpperCase();
      updateModeUI(currentMode);
      loadLiveStatus();
      showStatus(`Switched to ${mode} mode`, mode === 'LIVE' ? 'warning' : 'success');
    } else {
      showStatus(data.message || 'Failed to switch mode', 'danger');
    }
  } catch (error) {
    console.error('Error switching mode:', error);
    showStatus('Error switching mode', 'danger');
  }

  closeModal();
}

function updateModeUI(mode) {
  const indicator = document.getElementById('modeIndicator');
  const paperBtn = document.getElementById('paperMode');
  const liveBtn = document.getElementById('liveMode');

  if (mode === 'LIVE') {
    indicator.classList.add('live');
    paperBtn.classList.remove('active');
    liveBtn.classList.add('active');
  } else {
    indicator.classList.remove('live');
    paperBtn.classList.add('active');
    liveBtn.classList.remove('active');
  }
}

function updateLiveStatusUI(data) {
  const el = document.getElementById('liveStatus');
  if (!el || !data) return;

  const mode = (data.trading_mode || 'PAPER').toUpperCase();
  const brokerConnected = Boolean(data.broker_connected);
  const engineMode = data.mode || 'idle';
  const engineState = data.running ? 'running' : 'idle';

  el.textContent = `Mode: ${mode} • Broker: ${brokerConnected ? 'Connected' : 'Not connected'} • Engine: ${engineMode} (${engineState})`;

  el.classList.remove('ok', 'warn', 'danger');
  if (mode === 'LIVE' && !brokerConnected) {
    el.classList.add('danger');
  } else if (mode === 'LIVE') {
    el.classList.add('ok');
  } else {
    el.classList.add('warn');
  }
}

function updateFeedStatusUI(data) {
  const el = document.getElementById('feedStatus');
  if (!el) return;

  if (!data || data.enabled === false) {
    el.textContent = 'Feed: disabled';
    el.classList.remove('ok', 'warn', 'danger');
    el.classList.add('warn');
    updateFeedToggleUI(data);
    return;
  }

  if (data.running === false) {
    el.textContent = 'Feed: stopped';
    el.classList.remove('ok', 'warn', 'danger');
    el.classList.add('warn');
    updateFeedToggleUI(data);
    return;
  }

  const connected = Boolean(data.connected);
  const lastTick = data.last_tick_time
    ? `Last: ${data.last_tick_symbol || '-'} @ ${data.last_tick_time.split(' ')[1]}`
    : 'Last: -';
  const errorText = data.last_error ? ` • ${data.last_error.slice(0, 80)}` : '';
  const invalidCount = Array.isArray(data.invalid_symbols) ? data.invalid_symbols.length : 0;
  const invalidText = invalidCount ? ` • Missing tokens: ${invalidCount}` : '';

  el.textContent = connected
    ? `Feed: connected • ${lastTick}${invalidText}`
    : `Feed: disconnected${errorText}`;

  el.classList.remove('ok', 'warn', 'danger');
  if (connected && !invalidCount) {
    el.classList.add('ok');
  } else if (connected && invalidCount) {
    el.classList.add('warn');
  } else {
    el.classList.add('danger');
  }

  updateFeedToggleUI(data);
}

// Kill Switch
function showKillSwitchModal() {
  document.getElementById('killSwitchModal').classList.add('show');
}

function closeKillSwitchModal() {
  document.getElementById('killSwitchModal').classList.remove('show');
}

async function confirmKillSwitch() {
  try {
    const res = await fetch('/api/trading/killswitch', {
      method: 'POST'
    });

    const data = await res.json();

    if (data.success) {
      document.getElementById('killSwitchBtn').classList.add('active');
      showStatus('🚨 KILL SWITCH ACTIVATED - All trading stopped', 'danger');
    }
  } catch (error) {
    console.error('Error activating kill switch:', error);
  }

  closeKillSwitchModal();
}

// Modal Management
function showModal(message, action) {
  document.getElementById('confirmMessage').textContent = message;
  document.getElementById('confirmModal').classList.add('show');
}

function closeModal() {
  document.getElementById('confirmModal').classList.remove('show');
  pendingAction = null;
}

function confirmAction() {
  if (pendingAction) {
    pendingAction();
    pendingAction = null;
  }
}

// Status Banner
function showStatus(message, type = 'info') {
  const banner = document.getElementById('statusBanner');
  const text = document.getElementById('statusText');

  text.textContent = message;
  banner.className = `status-banner ${type}`;

  // Auto-hide after 5 seconds
  setTimeout(() => {
    banner.className = 'status-banner';
    text.textContent = 'System Ready';
  }, 5000);
}

// Safety Limits
async function loadSafetyLimits() {
  try {
    const res = await fetch('/api/trading/limits');
    const data = await res.json();

    if (data) {
      updateSafetyUI(data);
    }
  } catch (error) {
    console.error('Error loading safety limits:', error);
  }
}

function updateSafetyUI(data) {
  // Trades
  const tradesUsed = data.trades_today || 0;
  const tradesTotal = data.limits?.max_trades_per_day || 5;
  const tradesRemaining = data.trades_remaining || tradesTotal;
  document.getElementById('tradesCount').textContent = `${tradesUsed}/${tradesTotal}`;
  document.getElementById('tradesProgress').style.width = `${(tradesUsed / tradesTotal) * 100}%`;
  if (tradesUsed / tradesTotal > 0.8) {
    document.getElementById('tradesProgress').classList.add('warning');
  }

  // Loss
  const lossUsed = data.loss_today || 0;
  const lossTotal = data.limits?.max_loss_per_day || 5000;
  document.getElementById('lossCount').textContent = `₹${lossUsed.toFixed(0)}/₹${lossTotal.toFixed(0)}`;
  document.getElementById('lossProgress').style.width = `${(lossUsed / lossTotal) * 100}%`;
  if (lossUsed / lossTotal > 0.8) {
    document.getElementById('lossProgress').classList.add('warning');
  }

  // Positions
  const positionsUsed = data.open_positions || 0;
  const positionsTotal = data.limits?.max_positions_open || 3;
  document.getElementById('positionsCount').textContent = `${positionsUsed}/${positionsTotal}`;
  document.getElementById('positionsProgress').style.width = `${(positionsUsed / positionsTotal) * 100}%`;

  // Status dot
  const statusDot = document.getElementById('safetyStatus');
  if (data.kill_switch_active) {
    statusDot.style.background = 'var(--color-danger)';
  } else if (!data.trading_allowed) {
    statusDot.style.background = 'var(--color-warning)';
  } else {
    statusDot.style.background = 'var(--color-success)';
  }
}

// Positions
async function refreshPositions() {
  try {
    const res = await fetch('/api/positions/live');
    const data = await res.json();

    if (data && data.positions) {
      renderPositions(data.positions);
    }
  } catch (error) {
    console.error('Error loading positions:', error);
  }
}

function renderPositions(positions) {
  const container = document.getElementById('positionsList');

  if (!positions || positions.length === 0) {
    container.innerHTML = '<div class="empty-state">No open positions</div>';
    document.getElementById('totalPnl').textContent = '₹0.00';
    return;
  }

  let totalPnl = 0;
  const html = positions.map(pos => {
    const pnl = pos.pnl || 0;
    totalPnl += pnl;
    const pnlClass = pnl >= 0 ? 'positive' : 'negative';
    const pnlSign = pnl >= 0 ? '+' : '';

    return `
            <div class="position-item">
                <div>
                    <div class="position-symbol">${pos.symbol}</div>
                    <div class="position-qty">${pos.quantity} shares @ ₹${pos.avg_price}</div>
                </div>
                <div class="pnl-value ${pnlClass}">
                    ${pnlSign}₹${Math.abs(pnl).toFixed(2)}
                </div>
            </div>
        `;
  }).join('');

  container.innerHTML = html;

  const totalPnlEl = document.getElementById('totalPnl');
  totalPnlEl.textContent = `${totalPnl >= 0 ? '+' : ''}₹${totalPnl.toFixed(2)}`;
  totalPnlEl.className = `pnl-value ${totalPnl >= 0 ? 'positive' : 'negative'}`;
}

// Orders
async function refreshOrders() {
  try {
    const res = await fetch('/api/orders/live');
    const data = await res.json();

    if (data && data.orders) {
      renderOrders(data.orders);
    }
  } catch (error) {
    console.error('Error loading orders:', error);
  }
}

function renderOrders(orders) {
  const tbody = document.getElementById('ordersBody');

  if (!orders || orders.length === 0) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No orders yet</td></tr>';
    return;
  }

  const html = orders.slice(0, 10).map(order => {
    const statusClass = order.status.toLowerCase();
    const time = new Date(order.timestamp).toLocaleTimeString();

    return `
            <tr>
                <td>${time}</td>
                <td><strong>${order.symbol}</strong></td>
                <td class="${order.side === 'BUY' ? 'text-success' : 'text-danger'}">${order.side}</td>
                <td>${order.quantity}</td>
                <td>₹${order.price.toFixed(2)}</td>
                <td><span class="order-status ${statusClass}">${order.status}</span></td>
            </tr>
        `;
  }).join('');

  tbody.innerHTML = html;
}

// Stats
async function loadStats() {
  try {
    const res = await fetch('/api/summary');
    const data = await res.json();

    if (data) {
      document.getElementById('winRate').textContent = `${(data.win_rate * 100).toFixed(0)}%`;
      document.getElementById('totalTrades').textContent = data.trades || 0;

      const pnl = data.realized_pnl || 0;
      const pnlEl = document.getElementById('realizedPnl');
      pnlEl.textContent = `${pnl >= 0 ? '+' : ''}₹${Math.abs(pnl).toLocaleString()}`;
      pnlEl.className = `stat-value pnl-value ${pnl >= 0 ? 'positive' : 'negative'}`;
    }
  } catch (error) {
    console.error('Error loading stats:', error);
  }
}

// Watchlist
async function loadWatchlist() {
  try {
    const res = await fetch('/api/watchlist');
    const data = await res.json();

    if (data && data.symbols) {
      renderWatchlist(data.symbols);
    }
  } catch (error) {
    console.error('Error loading watchlist:', error);
  }
}

async function loadFunds() {
  try {
    console.log('Fetching funds...');
    const res = await fetch('/api/funds');
    const data = await res.json();
    console.log('Funds data:', data);

    if (data && data.available_balance !== undefined) {
      const balance = data.available_balance;
      console.log('Updating balance to:', balance);
      document.getElementById('navFunds').textContent = `₹${balance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
  } catch (error) {
    console.error('Error loading funds:', error);
  }
}

function renderWatchlist(symbols) {
  const container = document.getElementById('watchlistGrid');

  const html = symbols.map(symbol => `
        <div class="watchlist-item">
            <div class="watchlist-symbol">${symbol}</div>
            <div class="watchlist-price" id="price-${symbol}">-</div>
            <div class="watchlist-time" id="time-${symbol}">Last: -</div>
        </div>
    `).join('');

  container.innerHTML = html;
}

// WebSocket Connection
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('WebSocket connected');
    showStatus('Connected', 'success');
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleWebSocketMessage(data);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    showStatus('Connection error', 'danger');
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
    showStatus('Disconnected - Reconnecting...', 'warning');
    setTimeout(connectWebSocket, 3000);
  };
}

function handleWebSocketMessage(data) {
  if (data.type === 'quote') {
    updateQuoteUI(data.symbol, data.price, data.ts);
  } else if (data.type === 'trade') {
    refreshOrders();
    refreshPositions();
    loadSafetyLimits();
    loadStats();
    loadFunds();
  } else if (data.type === 'status') {
    updateModeUI(data.trading_mode || 'PAPER');
    updateLiveStatusUI(data);
  }
}

// Data Refresh
function loadInitialData() {
  loadSafetyLimits();
  refreshPositions();
  refreshOrders();
  loadStats();
  loadWatchlist();
  loadFunds();
  loadLiveStatus();
  loadFeedStatus();
  loadMarketQuotes();
}

function startDataRefresh() {
  // Refresh every 5 seconds
  setInterval(() => {
    loadSafetyLimits();
    refreshPositions();
    loadStats();
    loadFunds();
    loadLiveStatus();
    loadFeedStatus();
  }, 5000);

  // Refresh orders every 10 seconds
  setInterval(refreshOrders, 10000);

  // Refresh last quotes every 15 seconds (fallback if websocket drops)
  setInterval(loadMarketQuotes, 15000);
}

// Live status / broker connectivity
async function loadLiveStatus() {
  try {
    const res = await fetch('/api/live/status');
    const data = await res.json();
    if (data) {
      if (data.trading_mode) {
        currentMode = data.trading_mode.toUpperCase();
        updateModeUI(currentMode);
      }
      updateLiveStatusUI(data);
    }
  } catch (error) {
    console.error('Error loading live status:', error);
  }
}

// Market feed status
async function loadFeedStatus() {
  try {
    const res = await fetch('/api/debug/feed');
    const data = await res.json();
    lastFeedStatus = data;
    updateFeedStatusUI(data);
  } catch (error) {
    console.error('Error loading feed status:', error);
  }
}

function updateQuoteUI(symbol, price, ts) {
  if (!symbol) return;
  const key = String(symbol).toUpperCase();
  const priceEl = document.getElementById(`price-${key}`);
  if (priceEl && typeof price === 'number') {
    priceEl.textContent = `₹${price.toFixed(2)}`;
  }

  let timeText = '';
  if (ts) {
    const parts = String(ts).split(' ');
    timeText = parts.length > 1 ? parts[1] : String(ts);
  } else {
    timeText = new Date().toLocaleTimeString();
  }
  lastQuoteTimes[key] = timeText;

  const timeEl = document.getElementById(`time-${key}`);
  if (timeEl) {
    timeEl.textContent = `Last: ${timeText}`;
  }
}

async function loadMarketQuotes() {
  try {
    const res = await fetch('/api/market/quotes');
    const data = await res.json();
    const quotes = data && data.quotes ? data.quotes : data;
    if (!quotes || typeof quotes !== 'object') return;
    Object.entries(quotes).forEach(([symbol, price]) => {
      if (typeof price === 'number') {
        updateQuoteUI(symbol, price, lastQuoteTimes[String(symbol).toUpperCase()]);
      }
    });
  } catch (error) {
    console.error('Error loading market quotes:', error);
  }
}

function updateFeedToggleUI(data) {
  const btn = document.getElementById('feedToggleBtn');
  if (!btn) return;

  if (!data || data.enabled === false) {
    btn.textContent = 'Feed Disabled';
    btn.disabled = true;
    return;
  }

  btn.disabled = false;
  if (data.running === false) {
    btn.textContent = 'Start Feed';
  } else {
    btn.textContent = 'Stop Feed';
  }
}

async function toggleFeed() {
  const data = lastFeedStatus;
  if (!data || data.enabled === false) {
    showStatus('Feed is disabled via config', 'warning');
    return;
  }

  try {
    const endpoint = data.running === false ? '/api/feed/start' : '/api/feed/stop';
    const res = await fetch(endpoint, { method: 'POST' });
    const result = await res.json();
    if (result.success) {
      showStatus(result.message || 'Feed updated', 'success');
      if (result.status) {
        lastFeedStatus = { ...data, ...result.status, enabled: true };
        updateFeedStatusUI(lastFeedStatus);
      } else {
        loadFeedStatus();
      }
    } else {
      showStatus(result.message || 'Failed to update feed', 'danger');
    }
  } catch (error) {
    console.error('Error toggling feed:', error);
    showStatus('Error toggling feed', 'danger');
  }
}

function toggleWatchlistEdit() {
  // TODO: Implement watchlist editing
  showStatus('Watchlist editing coming soon!', 'info');
}
