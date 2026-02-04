const state = {
  selectedDate: null,
  liveRunning: false,
};

const fmtCurrency = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

const fmtNumber = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });
const fmtPercent = (value) => `${(value * 100).toFixed(1)}%`;

const el = (id) => document.getElementById(id);

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

async function loadStatus() {
  const data = await fetchJSON("/api/status");
  el("status-bars").textContent = data.bars;
  el("status-trades").textContent = data.trades;
  el("status-run").textContent = data.last_run ? new Date(data.last_run).toLocaleString() : "—";
}

async function loadDates() {
  const data = await fetchJSON("/api/dates");
  const select = el("date-select");
  select.innerHTML = "";
  data.dates.forEach((date, idx) => {
    const option = document.createElement("option");
    option.value = date;
    option.textContent = date;
    select.appendChild(option);
    if (idx === 0) {
      state.selectedDate = date;
    }
  });
  if (state.selectedDate) {
    select.value = state.selectedDate;
  }
}

async function loadWatchlist() {
  const data = await fetchJSON("/api/watchlist");
  const input = el("watchlist-input");
  // Update state.watchlistSymbols for rendering
  state.watchlistSymbols = data.symbols || [];
  if (data.symbols && data.symbols.length) {
    input.value = data.symbols.join(",");
  }
  renderMarketWatch();
}

async function loadMarketQuotes() {
  const quotes = await fetchJSON("/api/market/quotes");
  state.quotes = quotes || {};
  renderMarketWatch();
}

function renderMarketWatch() {
  const tbody = el("market-watch-rows");
  if (!state.watchlistSymbols) return;

  tbody.innerHTML = "";
  state.watchlistSymbols.forEach(sym => {
    const price = state.quotes ? state.quotes[sym] : undefined;

    const row = document.createElement("tr");

    const cellSym = document.createElement("td");
    cellSym.textContent = sym;

    const cellPrice = document.createElement("td");
    cellPrice.textContent = price ? fmtCurrency.format(price) : "—";
    cellPrice.id = `quote-${sym}`; // For easy update

    const cellChange = document.createElement("td");
    cellChange.textContent = "—"; // Could calc change if we had valid close

    row.appendChild(cellSym);
    row.appendChild(cellPrice);
    row.appendChild(cellChange);
    tbody.appendChild(row);
  });
}



function updateLiveBar(payload) {
  if (!payload || !payload.bar) return;
  const bar = payload.bar;
  el("live-bar").textContent = `Last bar: ${bar.symbol} ${bar.ts}`;
  if (payload.index && payload.total) {
    el("live-progress").textContent = `${payload.index}/${payload.total}`;
  }

  // Update Market Watch immediately
  if (state.quotes) state.quotes[bar.symbol] = bar.close;
  const cell = el(`quote-${bar.symbol}`);
  if (cell) {
    cell.textContent = fmtCurrency.format(bar.close);
    // Visual flash could be added here
    cell.style.color = "#36e7a8";
    setTimeout(() => cell.style.color = "", 500);
  }
}





function renderDailyReport(data) {
  const dateEl = el("report-date");
  const reportEl = el("daily-report");
  if (!data || !data.date) {
    dateEl.textContent = "—";
    reportEl.textContent = "Run the simulator or start a live replay to generate today’s report.";
    return;
  }
  dateEl.textContent = data.date;
  reportEl.textContent = `${data.trades} trades · ${data.wins} wins · ${data.losses} losses · Win rate ${fmtPercent(
    data.win_rate || 0
  )} · Realized PnL ${fmtCurrency.format(data.realized_pnl || 0)} · Avg R ${fmtNumber.format(data.avg_r || 0)}`;
}

async function loadSummary() {
  if (!state.selectedDate) return;
  const data = await fetchJSON(`/api/summary?date=${state.selectedDate}`);
  el("kpi-pnl").textContent = fmtCurrency.format(data.realized_pnl || 0);
  el("kpi-trades").textContent = data.trades || 0;
  el("kpi-win").textContent = fmtPercent(data.win_rate || 0);
  el("kpi-r").textContent = fmtNumber.format(data.avg_r || 0);
  renderDailyReport(data);
}

async function loadTrades() {
  if (!state.selectedDate) return;
  const data = await fetchJSON(`/api/trades?date=${state.selectedDate}`);
  const tbody = el("trade-rows");
  tbody.innerHTML = "";
  data.trades.forEach((trade) => {
    const row = document.createElement("tr");
    const cells = [
      trade.symbol,
      new Date(trade.entry_time).toLocaleTimeString(),
      trade.exit_time ? new Date(trade.exit_time).toLocaleTimeString() : "—",
      trade.qty,
      fmtNumber.format(trade.entry_price),
      trade.exit_price ? fmtNumber.format(trade.exit_price) : "—",
      fmtCurrency.format(trade.pnl || 0),
      fmtNumber.format(trade.r_multiple || 0),
    ];
    cells.forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value;
      row.appendChild(td);
    });
    tbody.appendChild(row);
  });
}

async function loadEquity() {
  if (!state.selectedDate) return;
  const data = await fetchJSON(`/api/equity?date=${state.selectedDate}`);
  renderChart(data.points || []);
}

function renderChart(points) {
  const canvas = el("equity-chart");
  const ctx = canvas.getContext("2d");
  const { width } = canvas.getBoundingClientRect();
  const height = canvas.height;
  const scale = window.devicePixelRatio || 1;

  canvas.width = width * scale;
  canvas.height = height * scale;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(scale, scale);

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#0c0c1a";
  ctx.fillRect(0, 0, width, height);

  if (!points.length) {
    ctx.fillStyle = "#b4b2c9";
    ctx.font = "14px Space Grotesk";
    ctx.fillText("Run a simulation to see the equity curve.", 16, 32);
    return;
  }

  const values = points.map((p) => p.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = 20;
  const range = max - min || 1;
  const denominator = Math.max(points.length - 1, 1);

  const lineGradient = ctx.createLinearGradient(0, 0, width, 0);
  lineGradient.addColorStop(0, "#36e7a8");
  lineGradient.addColorStop(1, "#5ea0ff");

  ctx.beginPath();
  points.forEach((point, idx) => {
    const x = padding + (idx / denominator) * (width - padding * 2);
    const y = height - padding - ((point.equity - min) / range) * (height - padding * 2);
    if (idx === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.strokeStyle = lineGradient;
  ctx.lineWidth = 2.5;
  ctx.stroke();
}

async function runSimulation() {
  await fetchJSON("/api/simulate", { method: "POST" });
  await refreshAll();
}

async function uploadData() {
  const fileInput = el("file-input");
  if (!fileInput.files.length) return;
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  await fetchJSON("/api/data/upload", { method: "POST", body: formData });
  fileInput.value = "";
  await refreshAll();
}

async function resetData() {
  const ok = window.confirm("This will clear trades and reload the sample data. Continue?");
  if (!ok) return;
  await fetchJSON("/api/data/reset", { method: "POST" });
  await refreshAll();
}

async function saveWatchlist() {
  const raw = el("watchlist-input").value || "";
  const data = await fetchJSON("/api/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbols: raw }),
  });
  const note = el("watchlist-note");
  if (note && data.symbols) {
    note.textContent = `Saved ${data.symbols.length} symbols.`;
  }
  await loadWatchlist(); // Refresh table
}

async function startLive() {
  const speed = Number(el("speed-select").value || 60);
  await fetchJSON(`/api/live/start?speed=${speed}&reset=true`, { method: "POST" });
}

async function stopLive() {
  await fetchJSON("/api/live/stop", { method: "POST" });
}

async function refreshAll() {
  await loadStatus();
  await loadDates();
  await loadSummary();
  await loadTrades();
  await loadEquity();
  await loadWatchlist(); // Ensure watchlist is loaded
  await loadMarketQuotes();
}

function updateLiveStatus(payload) {
  const dot = el("live-indicator");
  const status = el("live-status");
  const progress = el("live-progress");
  state.liveRunning = payload.running;
  if (payload.running) {
    dot.classList.add("active");
    status.textContent = payload.mode === "stream" ? "Streaming" : "Running";
  } else {
    dot.classList.remove("active");
    status.textContent = "Stopped";
  }
  if (payload.total !== undefined && payload.total !== 0) {
    progress.textContent = `${payload.index || 0}/${payload.total}`;
  }

  // Update Broker Status
  const brokerEl = el("status-broker");
  if (payload.broker_name) {
    brokerEl.textContent = payload.broker_name === "paper" ? "Paper" : "Active";
    brokerEl.className = "status-badge " + (payload.broker_connected ? "connected" : "paper");
    if (payload.broker_name === "paper") brokerEl.className = "status-badge paper";
  }
}



function handleSocketMessage(message) {
  if (!message || !message.type) return;
  if (message.type === "status" || message.type === "done") {
    updateLiveStatus(message);
    return;
  }
  if (message.type === "bar") {
    updateLiveBar(message);
    return;
  }
  if (message.type === "trade") {
    if (message.summary) {
      renderDailyReport(message.summary);
    }
    refreshAll();
  }
}

function connectSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    handleSocketMessage(message);
  });
  socket.addEventListener("close", () => {
    setTimeout(connectSocket, 2000);
  });
}

function bindEvents() {
  el("btn-run").addEventListener("click", runSimulation);
  el("btn-refresh").addEventListener("click", refreshAll);
  el("btn-upload").addEventListener("click", uploadData);
  el("btn-reset").addEventListener("click", resetData);
  el("btn-live-start").addEventListener("click", startLive);
  el("btn-live-stop").addEventListener("click", stopLive);
  el("btn-watchlist-save").addEventListener("click", saveWatchlist);
  el("date-select").addEventListener("change", (event) => {
    state.selectedDate = event.target.value;
    loadSummary();
    loadTrades();
    loadEquity();
  });
}

bindEvents();
connectSocket();
refreshAll();
loadWatchlist();
