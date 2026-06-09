let ws = null;
let chart = null;
let candleSeries = null;
let ma5Series = null;
let ma20Series = null;
let botRunning = false;

// ── 차트 초기화 ──────────────────────────────────────────────────────────
function initChart() {
  chart = LightweightCharts.createChart(document.getElementById('chart'), {
    layout: { background: { color: '#181B28' }, textColor: '#9DA5C4' },
    grid: { vertLines: { color: '#2A2D45' }, horzLines: { color: '#2A2D45' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: '#2A2D45' },
    timeScale: { borderColor: '#2A2D45', timeVisible: true },
  });

  candleSeries = chart.addCandlestickSeries({
    upColor: '#E05555', downColor: '#38B2E8',
    borderUpColor: '#E05555', borderDownColor: '#38B2E8',
    wickUpColor: '#E05555', wickDownColor: '#38B2E8',
  });

  ma5Series = chart.addLineSeries({ color: '#7B8FF0', lineWidth: 1 });
  ma20Series = chart.addLineSeries({ color: '#E8A838', lineWidth: 1 });
}

async function loadChart(ticker) {
  try {
    const res = await fetch(`https://api.upbit.com/v1/candles/minutes/60?market=${ticker}&count=80`);
    const data = await res.json();
    if (!Array.isArray(data)) return;

    const candles = data.reverse().map(d => ({
      time: Math.floor(new Date(d.candle_date_time_utc).getTime() / 1000),
      open: d.opening_price,
      high: d.high_price,
      low: d.low_price,
      close: d.trade_price,
    }));
    candleSeries.setData(candles);

    const closes = candles.map(c => c.close);
    ma5Series.setData(calcMA(candles, closes, 5));
    ma20Series.setData(calcMA(candles, closes, 20));
  } catch (e) {
    console.error('차트 로드 실패', e);
  }
}

function calcMA(candles, closes, period) {
  const result = [];
  for (let i = period - 1; i < closes.length; i++) {
    const sum = closes.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
    result.push({ time: candles[i].time, value: sum / period });
  }
  return result;
}

// ── WebSocket ────────────────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = e => updateUI(JSON.parse(e.data));
  ws.onclose = () => setTimeout(connectWS, 3000);
}

// ── UI 업데이트 ──────────────────────────────────────────────────────────
function fmt(n) {
  if (n == null || isNaN(n)) return '-';
  return Number(n).toLocaleString('ko-KR');
}

function updateUI(s) {
  botRunning = s.running;

  // 상태 표시
  const dot = document.getElementById('statusDot');
  const txt = document.getElementById('statusTxt');
  if (s.running) {
    dot.className = 'status-dot on';
    txt.textContent = '자동매매 실행 중';
  } else if (s.connected) {
    dot.className = 'status-dot connected';
    txt.textContent = 'API 연결됨';
  } else {
    dot.className = 'status-dot';
    txt.textContent = '연결 안됨';
  }

  const startBtn = document.getElementById('startBtn');
  if (s.running) {
    startBtn.textContent = '■ 중지';
    startBtn.className = 'btn-start stop';
  } else {
    startBtn.textContent = '▶ 시작';
    startBtn.className = 'btn-start';
  }
  startBtn.disabled = !s.connected;

  document.getElementById('sPrice').textContent = fmt(s.current_price);
  document.getElementById('sKrw').textContent = fmt(s.balance_krw) + '원';
  document.getElementById('sCoin').textContent = s.balance_coin ? s.balance_coin.toFixed(6) : '-';

  const profitCard = document.getElementById('sProfitCard');
  const profitEl = document.getElementById('sProfit');
  if (s.profit_pct != null) {
    const sign = s.profit_pct >= 0 ? '+' : '';
    profitEl.textContent = `${sign}${s.profit_pct}%`;
    profitCard.className = 'stat ' + (s.profit_pct >= 0 ? 'profit-up' : 'profit-down');
  } else {
    profitEl.textContent = '-';
    profitCard.className = 'stat';
  }

  const rsi = s.indicators?.rsi;
  const rsiEl = document.getElementById('sRsi');
  rsiEl.textContent = rsi != null ? rsi : '-';
  rsiEl.style.color = rsi >= 70 ? 'var(--error)' : rsi <= 30 ? '#38B2E8' : 'var(--text)';

  const sigEl = document.getElementById('sSignal');
  const sigMap = { buy: '🟢 매수', sell: '🔴 매도', hold: '⏸ 관망' };
  sigEl.textContent = sigMap[s.last_signal] || '-';

  // 오류
  const errEl = document.getElementById('botErr');
  if (s.error) {
    errEl.textContent = '⚠ ' + s.error;
    errEl.hidden = false;
  } else {
    errEl.hidden = true;
  }

  // 거래 내역
  const tbody = document.getElementById('tradeTbody');
  const empty = document.getElementById('tradeEmpty');
  const trades = (s.trades || []).slice().reverse();
  if (trades.length === 0) {
    tbody.innerHTML = '';
    empty.hidden = false;
  } else {
    empty.hidden = true;
    tbody.innerHTML = trades.map(t => `
      <tr>
        <td>${t.time}</td>
        <td><span class="badge ${t.type}">${t.type === 'buy' ? '매수' : '매도'}</span></td>
        <td>${fmt(t.price)}원</td>
        <td>${fmt(Math.round(t.amount))}원</td>
      </tr>`).join('');
  }
}

// ── API 호출 ─────────────────────────────────────────────────────────────
async function toggleBot() {
  const ticker = document.getElementById('tickerSel').value;

  if (botRunning) {
    await fetch('/api/stop', { method: 'POST' });
  } else {
    const body = {
      ticker,
      use_golden_cross: document.getElementById('chkGolden').checked,
      use_rsi_buy: document.getElementById('chkRsiBuy').checked,
      use_rsi_sell: document.getElementById('chkRsiSell').checked,
      rsi_buy_threshold: parseFloat(document.getElementById('rsiBuy').value),
      rsi_sell_threshold: parseFloat(document.getElementById('rsiSell').value),
    };
    const res = await fetch('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const d = await res.json();
      alert(d.detail || '시작 실패');
      return;
    }
    loadChart(ticker);
  }
}

// ── 초기화 ───────────────────────────────────────────────────────────────
initChart();
loadChart('KRW-BTC');
connectWS();

document.getElementById('tickerSel').addEventListener('change', function () {
  loadChart(this.value);
});
