// Modern Trading Dashboard JavaScript
let currentMode = 'PAPER';
let pendingAction = null;
let ws = null;

// Initialize on page load
document.addEventListener('DOM ContentLoaded', init);

function init() {
  setupEventListeners();
  connectWebSocket();
  loadInitialData();
  startDataRefresh();
}

function setupEventListeners() {
  // Trading mode toggle
  document.getElementById('paperMode').addEventListener('click', () => setTradingMode('PAPER'));
  document.getElementById('liveMode').addEventListener('click', () => setTradingMode('LIVE'));

  // Kill switch
  document.getElementById('killSwitchBtn').addEventListener('click', showKillSwitchModal);
}

// Trading Mode Management
function setTradingMode(mode) {
  if (mode === currentMode) return;

  if (mode === 'LIVE') {
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
      currentMode = mode;
      updateModeUI(mode);
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
    // Update watchlist price
    const priceEl = document.getElementById(`price-${data.symbol}`);
    if (priceEl) {
      priceEl.textContent = `₹${data.price.toFixed(2)}`;
    }
  } else if (data.type === 'trade') {
    refreshOrders();
    refreshPositions();
    loadSafetyLimits();
    loadStats();
    loadFunds();
  } else if (data.type === 'status') {
    updateModeUI(data.trading_mode || 'PAPER');
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
}

function startDataRefresh() {
  // Refresh every 5 seconds
  setInterval(() => {
    loadSafetyLimits();
    refreshPositions();
    loadStats();
    loadFunds();
  }, 5000);

  // Refresh orders every 10 seconds
  setInterval(refreshOrders, 10000);
}

function toggleWatchlistEdit() {
  // TODO: Implement watchlist editing
  showStatus('Watchlist editing coming soon!', 'info');
}
