const state = {
  quotes: {},
  watchlistSymbols: [],
  trades: [],
  equity: 100000.0, // Default start
};

const fmtCurrency = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

const fmtTime = (date) => new Date(date).toLocaleTimeString("en-IN", { hour: '2-digit', minute: '2-digit' });

const el = (id) => document.getElementById(id);

// --- API Helpers ---
async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

// --- Rendering ---

function updateHeader(equity, timestamp) {
  if (equity !== undefined) {
    el("display-funds").textContent = fmtCurrency.format(equity);
    state.equity = equity;
  }
  if (timestamp) {
    el("display-time").textContent = fmtTime(timestamp); // Use server time if available
  } else {
    // Fallback to local time if no server time provided
    el("display-time").textContent = new Date().toLocaleTimeString("en-IN", { hour: '2-digit', minute: '2-digit' });
  }
}

function renderStockList() {
  const container = el("stock-list");
  const filter = el("search-input").value.toUpperCase();

  container.innerHTML = "";

  state.watchlistSymbols.forEach(sym => {
    if (filter && !sym.includes(filter)) return;

    const price = state.quotes[sym];
    const item = document.createElement("div");
    item.className = "stock-item";
    item.dataset.symbol = sym;

    // Simulate change (randomized for demo/visual as we don't have prev close in quotes map usually)
    // In a real app, we'd calculate change %
    const priceDisplay = price ? fmtCurrency.format(price) : "—";

    item.innerHTML = `
      <span class="stock-symbol">${sym}</span>
      <span class="stock-price" id="quote-${sym}">${priceDisplay}</span>
    `;
    container.appendChild(item);
  });
}

function renderTradeFeed(trades) {
  const container = el("trade-feed");
  // Prepend new trades? Or re-render all. Simpler to re-render sorted by time DESC.
  // Assuming 'trades' is sorted or we sort it.
  container.innerHTML = "";

  // Sort trades by time desc
  const sorted = [...trades].sort((a, b) => new Date(b.entry_time) - new Date(a.entry_time));

  sorted.forEach(trade => {
    const item = document.createElement("div");
    item.className = `trade-item ${trade.side === 'LONG' ? 'buy' : 'sell'}`; // Assume Long=Buy for now

    const pnlClass = (trade.pnl > 0) ? "price-up" : (trade.pnl < 0 ? "price-down" : "");
    const pnlText = trade.pnl ? `${fmtCurrency.format(trade.pnl)}` : "OPEN";
    const status = trade.exit_time ? "CLOSED" : "OPEN";

    item.innerHTML = `
      <div class="trade-header">
        <span class="trade-symbol">${trade.symbol}</span>
        <span class="trade-time">${fmtTime(trade.entry_time)}</span>
      </div>
      <div class="trade-details">
        <div>${trade.side} @ ${trade.entry_price}</div>
        <div style="margin-top: 4px; font-weight: 500;" class="${pnlClass}">
           ${status}: ${pnlText}
        </div>
      </div>
    `;
    container.appendChild(item);
  });
}

// --- Logic ---

async function loadData() {
  try {
    const [watchlistData, quotesData, tradesData, statusData] = await Promise.all([
      fetchJSON("/api/watchlist"),
      fetchJSON("/api/market/quotes"),
      fetchJSON("/api/trades"), // Gets last 100 trades
      fetchJSON("/api/status") // To get summary or equity if needed
    ]);

    state.watchlistSymbols = watchlistData.symbols || [];
    state.quotes = quotesData || {};
    state.trades = tradesData.trades || [];

    renderStockList();
    renderTradeFeed(state.trades);

    // Initial fetch doesn't give equity easily without /api/summary for specifics or tracking it.
    // We'll trust the socket or separate call for live equity.
    // For now, let's load specific daily summary for today to get accurate PnL to add to base equity?
    // Simplified: Just update header time.
    updateHeader(state.equity);

  } catch (e) {
    console.error("Load failed:", e);
  }
}

// --- Socket ---

function handleSocketMessage(msg) {
  if (!msg || !msg.type) return;

  if (msg.type === "bar" && msg.bar) {
    // Update Quote
    state.quotes[msg.bar.symbol] = msg.bar.close;

    // Update DOM directly for performance
    const cell = el(`quote-${msg.bar.symbol}`);
    if (cell) {
      cell.textContent = fmtCurrency.format(msg.bar.close);
      // Flash effect?
      cell.style.color = msg.bar.close > (state.quotes[msg.bar.symbol] || 0) ? "var(--green)" : "var(--red)"; // Simple Logic
      setTimeout(() => cell.style.color = "", 500);
    }

    // Update Time
    if (msg.bar.ts) updateHeader(msg.equity, msg.bar.ts);
  }

  if (msg.type === "trade") {
    // Trade update (entry or exit)
    // We usually receive the single trade object
    // We need to upsert it into state.trades
    const newTrade = msg.trade;
    // Remove existing if any (by symbol + entry_time match? or ID if available)
    // App doesn't send unique Trade ID easily visible here, relying on simple filter
    state.trades = state.trades.filter(t => !(t.symbol === newTrade.symbol && t.entry_time === newTrade.entry_time));
    state.trades.unshift(newTrade);
    renderTradeFeed(state.trades);

    // Update Equity
    if (msg.equity) updateHeader(msg.equity);
  }

  if (msg.type === "done") {
    el("btn-live-start").textContent = "Start Live";
  }
}

function connectSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
  socket.addEventListener("message", (event) => handleSocketMessage(JSON.parse(event.data)));
  socket.addEventListener("close", () => setTimeout(connectSocket, 2000));
}

// --- Events ---

el("search-input").addEventListener("input", renderStockList);
el("btn-search").addEventListener("click", renderStockList);

el("btn-setup-notification").addEventListener("click", () => {
  alert("Notification setup feature coming soon!");
});

// Dev Controls
el("btn-live-start").addEventListener("click", async () => {
  const speed = el("speed-select").value;
  await fetchJSON(`/api/live/start?speed=${speed}&reset=true`, { method: "POST" });
  el("btn-live-start").textContent = "Running...";
});
el("btn-live-stop").addEventListener("click", async () => {
  await fetchJSON("/api/live/stop", { method: "POST" });
  el("btn-live-start").textContent = "Start Live";
});
el("btn-reset").addEventListener("click", async () => {
  if (confirm("Reset Data?")) {
    await fetchJSON("/api/data/reset", { method: "POST" });
    loadData();
  }
});


// Init
loadData();
connectSocket();
setInterval(() => {
  // Keep time updated if no socket flow
  if (!state.liveRunning) updateHeader(undefined, new Date());
}, 1000);
