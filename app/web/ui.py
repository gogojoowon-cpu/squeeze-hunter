"""
Short Squeeze Hunter v3 - Web UI
단일 HTML 페이지 (Chart.js + WebSocket + 모든 탭)
"""

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🚀 Short Squeeze Hunter v3</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg: #0a0a14;
  --card-bg: #14142a;
  --card-bg-2: #1a1a35;
  --border: #2a2a4a;
  --text: #e0e0ff;
  --text-dim: #8888aa;
  --accent: #6c7dff;
  --up: #26d97f;
  --down: #ff5577;
  --warn: #ffb84d;
  --critical: #ff3333;
  --imminent: #ff00aa;
  --high: #ff8800;
  --medium: #ffcc00;
  --low: #66cc66;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.5;
}

header {
  background: linear-gradient(135deg, #14142a 0%, #1a1a35 100%);
  padding: 14px 24px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
}

header h1 {
  font-size: 1.3em;
  background: linear-gradient(90deg, #6c7dff, #ff5577);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.status-bar {
  display: flex;
  gap: 16px;
  align-items: center;
  font-size: 0.85em;
  color: var(--text-dim);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
  display: inline-block;
  margin-right: 5px;
}
.dot.on { background: var(--up); box-shadow: 0 0 8px var(--up); }

.tabs {
  display: flex;
  gap: 4px;
  padding: 10px 24px 0;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}

.tab {
  background: transparent;
  color: var(--text-dim);
  border: none;
  padding: 10px 18px;
  cursor: pointer;
  font-size: 0.92em;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.tab:hover { color: var(--text); }
.tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

main {
  padding: 20px 24px;
  max-width: 1600px;
  margin: 0 auto;
}

.tab-content { display: none; }
.tab-content.active { display: block; }

h2 {
  font-size: 1.2em;
  margin-bottom: 14px;
  color: var(--text);
}
h3 {
  font-size: 1em;
  margin: 14px 0 8px;
  color: var(--accent);
}

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
  align-items: center;
}

.filter-bar select,
.filter-bar input,
.filter-bar button {
  background: var(--card-bg);
  color: var(--text);
  border: 1px solid var(--border);
  padding: 7px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9em;
}
.filter-bar button:hover {
  background: var(--card-bg-2);
  border-color: var(--accent);
}
.filter-bar input[type="text"] { cursor: text; min-width: 120px; }

/* === 메인 테이블 === */
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--card-bg);
  border-radius: 8px;
  overflow: hidden;
  font-size: 0.88em;
}

th {
  background: var(--card-bg-2);
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  color: var(--text-dim);
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
}
th:hover { color: var(--accent); }
th.sort-asc::after { content: ' ▲'; color: var(--accent); }
th.sort-desc::after { content: ' ▼'; color: var(--accent); }

td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
}

tbody tr {
  cursor: pointer;
  transition: background 0.15s;
}
tbody tr:hover { background: var(--card-bg-2); }

.sym { font-weight: 700; color: var(--accent); }
.up { color: var(--up); }
.down { color: var(--down); }
.muted { color: var(--text-dim); }

/* === 점수 바 === */
.score-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 110px;
}
.score-bar {
  flex: 1;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
  min-width: 50px;
}
.score-bar > div {
  height: 100%;
  transition: width 0.3s;
}
.score-val { font-weight: 700; min-width: 38px; text-align: right; }

/* === 등급 배지 === */
.grade {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75em;
  font-weight: 700;
  text-transform: uppercase;
}
.grade.IMMINENT { background: var(--imminent); color: white; }
.grade.HIGH { background: var(--high); color: white; }
.grade.MEDIUM { background: var(--medium); color: #333; }
.grade.LOW { background: var(--low); color: white; }
.grade.WATCH { background: var(--border); color: var(--text-dim); }

/* === 매집 티어 === */
.tier {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.72em;
  font-weight: 700;
}
.tier.STRONG { background: #ff3366; color: white; }
.tier.ACTIVE { background: #ff8800; color: white; }
.tier.EMERGING { background: #ffcc00; color: #222; }
.tier.WEAK { background: #444; color: #999; }

/* === 페이지네이션 === */
.pager {
  display: flex;
  gap: 6px;
  justify-content: center;
  margin: 16px 0;
}
.pager button {
  background: var(--card-bg);
  color: var(--text);
  border: 1px solid var(--border);
  padding: 6px 12px;
  border-radius: 5px;
  cursor: pointer;
}
.pager button.active {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}
.pager button:disabled { opacity: 0.4; cursor: not-allowed; }

/* === 카드 / 알림 / 이벤트 === */
.card-list { display: flex; flex-direction: column; gap: 6px; }

.anom-card, .event-card, .alert-card {
  background: var(--card-bg);
  padding: 11px 16px;
  border-radius: 7px;
  cursor: pointer;
  transition: transform 0.12s, background 0.2s;
}
.anom-card:hover, .event-card:hover, .alert-card:hover {
  transform: translateX(4px);
  background: var(--card-bg-2);
}

.anom-head { display: flex; gap: 10px; align-items: center; margin-bottom: 6px; }
.anom-head .badge { padding: 2px 8px; border-radius: 4px; color: white; font-size: 0.72em; font-weight: 700; }
.anom-head .type { color: var(--text-dim); font-size: 0.88em; }
.anom-body { display: flex; gap: 14px; align-items: center; font-size: 0.88em; color: var(--text-dim); flex-wrap: wrap; }

.event-card {
  display: grid;
  grid-template-columns: 70px 1fr 80px 100px 80px 80px;
  gap: 10px;
  align-items: center;
  font-size: 0.9em;
}
.event-card .days { color: var(--warn); font-weight: 700; }
.event-card .extra { color: var(--up); }

.event-section { margin-bottom: 22px; }

.alert-card {
  display: grid;
  grid-template-columns: 60px 100px 1fr 90px;
  gap: 10px;
  align-items: center;
  border-left: 3px solid var(--border);
}
.alert-card.critical { border-left-color: var(--critical); }
.alert-card.high { border-left-color: var(--high); }
.alert-card.info { border-left-color: var(--accent); }
.alert-card .time { color: var(--text-dim); font-size: 0.8em; }

.warning-banner {
  background: linear-gradient(90deg, #ff550022, transparent);
  border-left: 3px solid var(--high);
  padding: 8px 12px;
  margin: 8px 0;
  color: #ffaa66;
  font-size: 0.9em;
  border-radius: 4px;
}
.warn-item { padding: 2px 0; }

/* === 테마 그룹 === */
.theme-group {
  background: var(--card-bg);
  padding: 14px;
  margin-bottom: 14px;
  border-radius: 8px;
}
.theme-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.theme-name { font-size: 1.05em; font-weight: 700; color: var(--accent); }
.theme-stats { color: var(--text-dim); font-size: 0.85em; }

/* === 상세 모달 === */
.modal-bg {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.7);
  display: none;
  justify-content: center;
  align-items: flex-start;
  z-index: 1000;
  overflow-y: auto;
  padding: 30px 0;
}
.modal-bg.open { display: flex; }

.modal {
  background: var(--card-bg);
  width: 90%;
  max-width: 1000px;
  border-radius: 10px;
  padding: 20px 24px;
  position: relative;
}
.modal-close {
  position: absolute;
  top: 14px;
  right: 18px;
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 1.4em;
  cursor: pointer;
}
.modal-close:hover { color: var(--down); }

.detail-section {
  background: var(--card-bg-2);
  padding: 14px;
  margin: 10px 0;
  border-radius: 7px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
  margin-top: 10px;
}
.metric-grid > div {
  background: var(--bg);
  padding: 8px 10px;
  border-radius: 6px;
}
.metric-grid label {
  display: block;
  color: var(--text-dim);
  font-size: 0.76em;
  margin-bottom: 3px;
}
.metric-grid b { color: var(--text); font-size: 1em; }

.chart-wrap { height: 240px; margin-top: 10px; }

.breakdown-list { list-style: none; }
.breakdown-list li {
  display: grid;
  grid-template-columns: 1fr 60px 80px;
  gap: 8px;
  padding: 5px 0;
  border-bottom: 1px solid var(--border);
  font-size: 0.88em;
}
.breakdown-list .label { color: var(--text-dim); }
.breakdown-list .val { text-align: right; }
.breakdown-list .max { text-align: right; color: var(--text-dim); font-size: 0.85em; }

/* === 매집 상세 === */
.acc-signals {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 6px;
}
.acc-tag {
  background: var(--bg);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.78em;
  color: var(--up);
}

.empty {
  color: var(--text-dim);
  padding: 30px;
  text-align: center;
}

.flash-up { animation: flashUp 0.6s; }
.flash-down { animation: flashDown 0.6s; }
@keyframes flashUp { 0% { background: #26d97f44; } 100% { background: transparent; } }
@keyframes flashDown { 0% { background: #ff557744; } 100% { background: transparent; } }

@media (max-width: 768px) {
  header { padding: 10px 14px; flex-direction: column; gap: 8px; }
  main { padding: 14px; }
  table { font-size: 0.78em; }
  th, td { padding: 7px 6px; }
  .event-card { grid-template-columns: 1fr 1fr; gap: 6px; }
  .modal { width: 96%; padding: 16px; }
}
</style>
</head>
<body>

<header>
  <h1>🚀 Short Squeeze Hunter v3</h1>
  <div class="status-bar">
    <span><span id="wsDot" class="dot"></span><span id="wsText">○ 연결중</span></span>
    <span id="loadStatus">로딩...</span>
    <span id="marketStatus" class="muted">시장 확인중</span>
  </div>
</header>

<nav class="tabs">
  <button class="tab active" data-tab="dashboard">📊 대시보드</button>
  <button class="tab" data-tab="themes">🏷️ 테마</button>
  <button class="tab" data-tab="accumulation">📈 매집신호</button>
  <button class="tab" data-tab="anomalies">⚠️ 이상거래</button>
  <button class="tab" data-tab="events">📅 이벤트</button>
  <button class="tab" data-tab="alerts">🔔 알림</button>
  <button class="tab" data-tab="status">⚙️ 상태</button>
</nav>

<main>
  <!-- ===== 대시보드 ===== -->
  <div id="tab-dashboard" class="tab-content active">
    <div class="filter-bar">
      <input type="text" id="searchSym" placeholder="🔍 심볼 검색" oninput="renderMain()">
      <select id="filterGrade" onchange="renderMain()">
        <option value="">전체 등급</option>
        <option value="IMMINENT">IMMINENT</option>
        <option value="HIGH">HIGH</option>
        <option value="MEDIUM">MEDIUM</option>
        <option value="LOW">LOW</option>
        <option value="WATCH">WATCH</option>
      </select>
      <select id="filterMinScore" onchange="renderMain()">
        <option value="0">점수 전체</option>
        <option value="40">40+</option>
        <option value="60">60+</option>
        <option value="75">75+</option>
        <option value="90">90+</option>
      </select>
      <select id="pageSize" onchange="renderMain()">
        <option value="50">50개</option>
        <option value="100" selected>100개</option>
        <option value="200">200개</option>
      </select>
      <span class="muted" id="resultCount"></span>
    </div>
    <table id="mainTable">
      <thead>
        <tr>
          <th data-sort="symbol">심볼</th>
          <th data-sort="price">가격</th>
          <th data-sort="change_pct">변동%</th>
          <th data-sort="volume">거래량</th>
          <th data-sort="si_pct">SI%</th>
          <th data-sort="ctb">CTB%</th>
          <th data-sort="float_shares">유동주식</th>
          <th data-sort="rsi14">RSI</th>
          <th data-sort="acc_score">매집</th>
          <th data-sort="sqs_score" class="sort-desc">SQS 점수</th>
          <th>등급</th>
        </tr>
      </thead>
      <tbody id="mainTbody"></tbody>
    </table>
    <div class="pager" id="mainPager"></div>
  </div>

  <!-- ===== 테마 ===== -->
  <div id="tab-themes" class="tab-content">
    <div id="themeList"></div>
  </div>

  <!-- ===== 매집신호 ===== -->
  <div id="tab-accumulation" class="tab-content">
    <div class="filter-bar">
      <select id="accMinScore" onchange="loadAccumulation()">
        <option value="40">매집점수 40+</option>
        <option value="60" selected>60+</option>
        <option value="75">75+ (STRONG)</option>
      </select>
      <button onclick="loadAccumulation()">새로고침</button>
      <span class="muted" id="accStats"></span>
    </div>
    <table>
      <thead>
        <tr>
          <th>심볼</th>
          <th>가격</th>
          <th>티어</th>
          <th>매집점수</th>
          <th>OBV</th>
          <th>CMF</th>
          <th>폭증일</th>
          <th>매집/분산</th>
          <th>시그널</th>
        </tr>
      </thead>
      <tbody id="accTbody"></tbody>
    </table>
  </div>

  <!-- ===== 이상거래 ===== -->
  <div id="tab-anomalies" class="tab-content">
    <div class="filter-bar">
      <select id="anomSeverity" onchange="loadAnomalies()">
        <option value="">전체 등급</option>
        <option value="critical">🔴 Critical</option>
        <option value="high">🟠 High</option>
        <option value="info">🔵 Info</option>
      </select>
      <button onclick="loadAnomalies()">새로고침</button>
      <span class="muted" id="anomStats"></span>
    </div>
    <div id="anomList" class="card-list"></div>
  </div>

  <!-- ===== 이벤트 ===== -->
  <div id="tab-events" class="tab-content">
    <div class="filter-bar">
      <select id="eventDays" onchange="loadEvents()">
        <option value="3">3일 이내</option>
        <option value="7" selected>7일 이내</option>
        <option value="14">14일 이내</option>
        <option value="30">30일 이내</option>
      </select>
      <button onclick="loadEvents()">새로고침</button>
    </div>
    <div class="event-section">
      <h3>📊 어닝 발표</h3>
      <div id="eventEarnings" class="card-list"></div>
    </div>
    <div class="event-section">
      <h3>💰 배당락</h3>
      <div id="eventDividends" class="card-list"></div>
    </div>
    <div class="event-section">
      <h3>✂️ 주식 분할</h3>
      <div id="eventSplits" class="card-list"></div>
    </div>
  </div>

  <!-- ===== 알림 ===== -->
  <div id="tab-alerts" class="tab-content">
    <div class="filter-bar">
      <select id="alertLevel" onchange="loadAlerts()">
        <option value="">전체</option>
        <option value="critical">🔴 Critical</option>
        <option value="high">🟠 High</option>
        <option value="info">🔵 Info</option>
      </select>
      <button onclick="loadAlerts()">새로고침</button>
    </div>
    <div id="alertList" class="card-list"></div>
  </div>

  <!-- ===== 상태 ===== -->
  <div id="tab-status" class="tab-content">
    <h3>시스템 상태</h3>
    <div id="sysStatus" class="metric-grid"></div>
    <h3>데이터 커버리지</h3>
    <table>
      <thead><tr><th>필드</th><th>커버리지</th></tr></thead>
      <tbody id="covTbody"></tbody>
    </table>
    <h3>점수 분포</h3>
    <div class="chart-wrap"><canvas id="scoreDistChart"></canvas></div>
    <button onclick="loadStatus()" style="margin-top:14px;background:var(--accent);color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer">새로고침</button>
  </div>
</main>

<!-- ===== 상세 모달 ===== -->
<div id="detailModal" class="modal-bg" onclick="if(event.target===this)closeDetail()">
  <div class="modal">
    <button class="modal-close" onclick="closeDetail()">✕</button>
    <div id="detailBody"></div>
  </div>
</div>
"""
HTML_PAGE += r"""
<script>
// ============================================================
// 전역 상태
// ============================================================
const STATE = {
  all: [],                // 전체 종목 [{symbol, ...}]
  byMap: {},              // symbol -> row
  page: 1,
  sortKey: 'sqs_score',
  sortDesc: true,
  ws: null,
  wsRetry: 0,
  ready: false,
  detailSym: null,
  charts: {},             // 차트 인스턴스 캐시
};

// ============================================================
// 유틸리티
// ============================================================
function fmtNum(n, digits = 2) {
  if (n === null || n === undefined || isNaN(n)) return '-';
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(digits) + 'B';
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(digits) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(digits) + 'K';
  return Number(n).toFixed(digits);
}

function fmtPct(n, digits = 2) {
  if (n === null || n === undefined || isNaN(n)) return '-';
  const s = Number(n).toFixed(digits);
  return (n > 0 ? '+' : '') + s + '%';
}

function fmtPrice(n) {
  if (!n || n <= 0) return '-';
  if (n < 1) return '$' + n.toFixed(4);
  if (n < 10) return '$' + n.toFixed(3);
  return '$' + n.toFixed(2);
}

function fmtTime(ts) {
  if (!ts) return '-';
  const d = new Date(ts * 1000);
  const now = new Date();
  const diff = (now - d) / 1000;
  if (diff < 60) return Math.floor(diff) + '초 전';
  if (diff < 3600) return Math.floor(diff / 60) + '분 전';
  if (diff < 86400) return Math.floor(diff / 3600) + '시간 전';
  return d.toLocaleDateString('ko-KR') + ' ' + d.toLocaleTimeString('ko-KR', {hour:'2-digit',minute:'2-digit'});
}

function scoreColor(s) {
  if (s >= 90) return '#ff00aa';
  if (s >= 75) return '#ff8800';
  if (s >= 60) return '#ffcc00';
  if (s >= 40) return '#66cc66';
  return '#666';
}

function escapeHtml(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// ============================================================
// 초기 스냅샷 로딩
// ============================================================
async function preloadSnapshot() {
  try {
    const r = await fetch('/api/snapshot?limit=2000').then(r => r.json());
    STATE.all = r.items || [];
    STATE.byMap = {};
    for (const it of STATE.all) STATE.byMap[it.symbol] = it;
    STATE.ready = r.ready;
    document.getElementById('loadStatus').textContent =
      r.ready
        ? `✅ ${r.loaded}/${r.total}개 로딩 완료`
        : `⏳ ${r.loaded}/${r.total}개 로딩중...`;
    renderMain();
  } catch (e) {
    console.error('snapshot 실패', e);
    document.getElementById('loadStatus').textContent = '❌ 로딩 실패';
  }
}

// 로딩 상태 폴링 (준비 안됐을 때만)
async function chkLoad() {
  if (STATE.ready) return;
  try {
    const r = await fetch('/api/market').then(r => r.json());
    STATE.ready = r.ready;
    document.getElementById('loadStatus').textContent = r.ready
      ? `✅ ${r.loaded}개 로딩 완료`
      : `⏳ ${r.loaded}개 로딩중...`;
    if (r.ready) preloadSnapshot();
  } catch (e) {}
}

// 시장 상태 표시
async function loadMarket() {
  try {
    const r = await fetch('/api/market').then(r => r.json());
    const el = document.getElementById('marketStatus');
    el.textContent = r.is_open ? '🟢 시장 OPEN' : '🔴 시장 CLOSED';
    el.style.color = r.is_open ? 'var(--up)' : 'var(--down)';
  } catch (e) {}
}

// ============================================================
// WebSocket 실시간 연결
// ============================================================
function conn() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${proto}://${location.host}/ws/scores`;
  try {
    STATE.ws = new WebSocket(url);
  } catch (e) {
    console.error('ws 생성 실패', e);
    setTimeout(conn, 3000);
    return;
  }

  STATE.ws.onopen = () => {
    STATE.wsRetry = 0;
    document.getElementById('wsDot').classList.add('on');
    document.getElementById('wsText').textContent = '● 실시간';
  };

  STATE.ws.onmessage = ev => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'snapshot' || msg.type === 'update') {
        live(msg.items || []);
      }
      // ping/pong 은 무시
    } catch (e) {}
  };

  STATE.ws.onclose = () => {
    document.getElementById('wsDot').classList.remove('on');
    document.getElementById('wsText').textContent = '○ 재연결중';
    STATE.wsRetry++;
    const delay = Math.min(15000, 2000 * STATE.wsRetry);
    setTimeout(conn, delay);
  };

  STATE.ws.onerror = () => {
    try { STATE.ws.close(); } catch (e) {}
  };
}

function live(items) {
  if (!items || !items.length) return;
  let changed = false;
  for (const it of items) {
    const prev = STATE.byMap[it.symbol];
    if (prev) {
      // 점수 변화 추적 (시각화용)
      const oldScore = prev.sqs_score || 0;
      const newScore = it.sqs_score || 0;
      if (Math.abs(newScore - oldScore) >= 0.5) {
        it._flash = newScore > oldScore ? 'up' : 'down';
      }
      Object.assign(prev, it);
    } else {
      STATE.byMap[it.symbol] = it;
      STATE.all.push(it);
    }
    changed = true;
  }
  if (changed) renderMain();
}

// ============================================================
// 메인 테이블 렌더링
// ============================================================
function renderMain() {
  const search = (document.getElementById('searchSym').value || '').trim().toUpperCase();
  const grade = document.getElementById('filterGrade').value;
  const minScore = parseFloat(document.getElementById('filterMinScore').value) || 0;
  const pageSize = parseInt(document.getElementById('pageSize').value) || 100;

  // 필터링
  let filtered = STATE.all.filter(it => {
    if (search && !it.symbol.includes(search)) return false;
    if (grade && it.grade !== grade) return false;
    if ((it.sqs_score || 0) < minScore) return false;
    if ((it.price || 0) <= 0) return false;
    return true;
  });

  // 정렬
  const k = STATE.sortKey;
  const dir = STATE.sortDesc ? -1 : 1;
  filtered.sort((a, b) => {
    const va = a[k] ?? 0;
    const vb = b[k] ?? 0;
    if (typeof va === 'string') return dir * va.localeCompare(vb);
    return dir * ((va - vb) || 0);
  });

  // 결과 카운트
  document.getElementById('resultCount').textContent = `${filtered.length}개 결과`;

  // 페이지네이션
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  if (STATE.page > totalPages) STATE.page = totalPages;
  const start = (STATE.page - 1) * pageSize;
  const pageItems = filtered.slice(start, start + pageSize);

  // 행 렌더링
  const tbody = document.getElementById('mainTbody');
  tbody.innerHTML = pageItems.map(it => {
    const score = it.sqs_score || 0;
    const flashClass = it._flash ? `flash-${it._flash}` : '';
    if (it._flash) delete it._flash;
    return `
      <tr class="${flashClass}" onclick="showDetail('${it.symbol}')">
        <td><span class="sym">${escapeHtml(it.symbol)}</span></td>
        <td>${fmtPrice(it.price)}</td>
        <td class="${(it.change_pct||0)>=0?'up':'down'}">${fmtPct(it.change_pct)}</td>
        <td>${fmtNum(it.volume, 0)}</td>
        <td>${(it.si_pct||0).toFixed(1)}%</td>
        <td>${(it.ctb||0).toFixed(1)}%</td>
        <td>${fmtNum(it.float_shares, 1)}</td>
        <td>${(it.rsi14||50).toFixed(0)}</td>
        <td>${(it.acc_score||0).toFixed(0)}</td>
        <td>
          <div class="score-cell">
            <div class="score-bar"><div style="width:${score}%;background:${scoreColor(score)}"></div></div>
            <span class="score-val" style="color:${scoreColor(score)}">${score.toFixed(1)}</span>
          </div>
        </td>
        <td>${it.grade ? `<span class="grade ${it.grade}">${it.grade}</span>` : '-'}</td>
      </tr>`;
  }).join('') || '<tr><td colspan="11" class="empty">결과 없음</td></tr>';

  // 페이저
  renderPager(totalPages);
}

function renderPager(totalPages) {
  const pager = document.getElementById('mainPager');
  if (totalPages <= 1) { pager.innerHTML = ''; return; }

  const cur = STATE.page;
  let html = '';
  html += `<button ${cur===1?'disabled':''} onclick="goPage(${cur-1})">‹</button>`;

  const start = Math.max(1, cur - 3);
  const end = Math.min(totalPages, cur + 3);
  if (start > 1) {
    html += `<button onclick="goPage(1)">1</button>`;
    if (start > 2) html += `<span class="muted">…</span>`;
  }
  for (let i = start; i <= end; i++) {
    html += `<button class="${i===cur?'active':''}" onclick="goPage(${i})">${i}</button>`;
  }
  if (end < totalPages) {
    if (end < totalPages - 1) html += `<span class="muted">…</span>`;
    html += `<button onclick="goPage(${totalPages})">${totalPages}</button>`;
  }
  html += `<button ${cur===totalPages?'disabled':''} onclick="goPage(${cur+1})">›</button>`;
  pager.innerHTML = html;
}

function goPage(p) {
  STATE.page = p;
  renderMain();
  window.scrollTo({top: 0, behavior: 'smooth'});
}

// 컬럼 정렬 이벤트
function bindSort() {
  document.querySelectorAll('#mainTable th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const k = th.dataset.sort;
      if (STATE.sortKey === k) {
        STATE.sortDesc = !STATE.sortDesc;
      } else {
        STATE.sortKey = k;
        STATE.sortDesc = true;
      }
      // 헤더 표시 갱신
      document.querySelectorAll('#mainTable th').forEach(t => {
        t.classList.remove('sort-asc', 'sort-desc');
      });
      th.classList.add(STATE.sortDesc ? 'sort-desc' : 'sort-asc');
      STATE.page = 1;
      renderMain();
    });
  });
}

// ============================================================
// 탭 전환
// ============================================================
function showTab(name) {
  document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

  const content = document.getElementById('tab-' + name);
  const btn = document.querySelector(`.tab[data-tab="${name}"]`);
  if (content) content.classList.add('active');
  if (btn) btn.classList.add('active');

  // 각 탭 진입 시 로딩
  if (name === 'themes') loadThemes();
  else if (name === 'accumulation') loadAccumulation();
  else if (name === 'anomalies') loadAnomalies();
  else if (name === 'events') loadEvents();
  else if (name === 'alerts') loadAlerts();
  else if (name === 'status') loadStatus();
}

function bindTabs() {
  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => showTab(btn.dataset.tab));
  });
}
</script>
"""
HTML_PAGE += r"""
<script>
// ============================================================
// 테마 탭
// ============================================================
async function loadThemes() {
  try {
    const r = await fetch('/api/themes').then(r => r.json());
    const el = document.getElementById('themeList');
    if (!r.themes || r.themes.length === 0) {
      el.innerHTML = '<div class="empty">테마 데이터 없음</div>';
      return;
    }
    el.innerHTML = r.themes.map(t => {
      const topRows = (t.top || []).map(it => {
        const s = it.sqs_score || 0;
        return `
          <tr onclick="showDetail('${it.symbol}')">
            <td><span class="sym">${escapeHtml(it.symbol)}</span></td>
            <td>${fmtPrice(it.price)}</td>
            <td class="${(it.change_pct||0)>=0?'up':'down'}">${fmtPct(it.change_pct)}</td>
            <td>
              <div class="score-cell">
                <div class="score-bar"><div style="width:${s}%;background:${scoreColor(s)}"></div></div>
                <span class="score-val" style="color:${scoreColor(s)}">${s.toFixed(1)}</span>
              </div>
            </td>
            <td>${it.grade ? `<span class="grade ${it.grade}">${it.grade}</span>` : '-'}</td>
          </tr>`;
      }).join('');
      return `
        <div class="theme-group">
          <div class="theme-head">
            <span class="theme-name">${escapeHtml(t.theme)}</span>
            <span class="theme-stats">${t.count}개 · 평균 ${t.avg_score.toFixed(1)}점</span>
          </div>
          <table>
            <thead><tr><th>심볼</th><th>가격</th><th>변동%</th><th>점수</th><th>등급</th></tr></thead>
            <tbody>${topRows}</tbody>
          </table>
        </div>`;
    }).join('');
  } catch (e) {
    document.getElementById('themeList').innerHTML = '<div class="empty">로딩 실패</div>';
  }
}

// ============================================================
// 매집신호 탭
// ============================================================
async function loadAccumulation() {
  try {
    const min = document.getElementById('accMinScore').value;
    const r = await fetch(`/api/accumulation?min_score=${min}&limit=200`).then(r => r.json());
    const items = r.items || [];

    // 티어별 통계
    const tiers = {STRONG: 0, ACTIVE: 0, EMERGING: 0, WEAK: 0};
    items.forEach(it => { tiers[it.tier] = (tiers[it.tier] || 0) + 1; });
    document.getElementById('accStats').textContent =
      `총 ${items.length}개 · STRONG ${tiers.STRONG} · ACTIVE ${tiers.ACTIVE} · EMERGING ${tiers.EMERGING}`;

    const tbody = document.getElementById('accTbody');
    tbody.innerHTML = items.map(it => {
      const signals = (it.acc_signals || []).slice(0, 3).map(s =>
        `<span class="acc-tag">${escapeHtml(s)}</span>`
      ).join(' ');
      const obvPct = ((it.obv_slope || 0) * 100).toFixed(1);
      return `
        <tr onclick="showDetail('${it.symbol}')">
          <td><span class="sym">${escapeHtml(it.symbol)}</span></td>
          <td>${fmtPrice(it.price)}</td>
          <td><span class="tier ${it.tier}">${it.tier}</span></td>
          <td><b style="color:${scoreColor(it.acc_score)}">${(it.acc_score||0).toFixed(0)}</b></td>
          <td class="${(it.obv_slope||0)>=0?'up':'down'}">${obvPct}%</td>
          <td class="${(it.cmf||0)>=0?'up':'down'}">${(it.cmf||0).toFixed(2)}</td>
          <td>${it.vol_spike_days || 0}일</td>
          <td>${it.acc_candles || 0} / ${it.dist_candles || 0}</td>
          <td>${signals || '-'}</td>
        </tr>`;
    }).join('') || '<tr><td colspan="9" class="empty">매집 신호 없음</td></tr>';
  } catch (e) {
    console.error(e);
  }
}

// ============================================================
// 이상거래 탭
// ============================================================
async function loadAnomalies() {
  try {
    const sev = document.getElementById('anomSeverity').value;
    const url = '/api/anomalies?limit=100' + (sev ? '&severity=' + sev : '');
    const r = await fetch(url).then(r => r.json());
    const el = document.getElementById('anomList');
    document.getElementById('anomStats').textContent = `총 ${r.count || 0}건`;

    if (!r.items || r.items.length === 0) {
      el.innerHTML = '<div class="empty">탐지된 이상거래 없음</div>';
      return;
    }

    const typeKr = {
      volume_spike: '거래량 급증',
      price_spike: '가격 급변',
      unusual_options: '이상 옵션 활동',
      gamma_squeeze_imminent: '감마 스퀴즈 임박',
      dark_pool_heavy: '다크풀 집중',
    };

    el.innerHTML = r.items.map(a => {
      const sevColor = {critical:'#ff3333', high:'#ff8800', info:'#3399ff'}[a.severity] || '#999';
      const tk = typeKr[a.anomaly_type] || a.anomaly_type;
      let detail = '';
      if (a.data) {
        if (a.data.z !== undefined) detail += `Z=${a.data.z} `;
        if (a.data.direction) detail += `(${a.data.direction === 'up' ? '⬆' : '⬇'}) `;
        if (a.data.gamma !== undefined) detail += `γ=${a.data.gamma} `;
        if (a.data.cp_ratio !== undefined) detail += `C/P=${a.data.cp_ratio} `;
        if (a.data.ratio !== undefined) detail += `${(a.data.ratio*100).toFixed(0)}% `;
        if (a.data.score !== undefined) detail += `score=${a.data.score} `;
      }
      return `
        <div class="anom-card" onclick="showDetail('${a.symbol}')" style="border-left:4px solid ${sevColor}">
          <div class="anom-head">
            <span class="sym">${escapeHtml(a.symbol)}</span>
            <span class="badge" style="background:${sevColor}">${(a.severity||'').toUpperCase()}</span>
            <span class="type">${tk}</span>
            <span class="muted" style="margin-left:auto">${fmtTime(a.detected_at)}</span>
          </div>
          <div class="anom-body">
            <span>${fmtPrice(a.price)}</span>
            <span class="${(a.change_pct||0)>=0?'up':'down'}">${fmtPct(a.change_pct)}</span>
            <span>거래량 ${fmtNum(a.volume, 0)}</span>
            <span>SQS ${(a.sqs_score||0).toFixed(1)}</span>
            ${a.grade ? `<span class="grade ${a.grade}">${a.grade}</span>` : ''}
            <span class="muted">${detail}</span>
          </div>
        </div>`;
    }).join('');
  } catch (e) {
    console.error(e);
  }
}

// ============================================================
// 이벤트 탭
// ============================================================
async function loadEvents() {
  try {
    const days = document.getElementById('eventDays').value;
    const r = await fetch(`/api/events?days=${days}`).then(r => r.json());

    const render = (items, type) => {
      if (!items || items.length === 0) return '<div class="empty">없음</div>';
      return items.map(e => {
        const dateStr = (e.date || e.ex_date || '').slice(0, 10);
        let extra = '';
        if (type === 'dividend') extra = `$${(e.amount||0).toFixed(3)}`;
        else if (type === 'split') extra = e.ratio || '';
        return `
          <div class="event-card" onclick="showDetail('${e.symbol}')">
            <span class="sym">${escapeHtml(e.symbol)}</span>
            <span class="muted">${escapeHtml(e.name || '')}</span>
            <span class="days">D-${e.days}</span>
            <span class="muted">${dateStr}</span>
            <span class="extra">${extra}</span>
            <span>SQS ${(e.sqs_score||0).toFixed(0)}</span>
          </div>`;
      }).join('');
    };

    document.getElementById('eventEarnings').innerHTML = render(r.earnings, 'earnings');
    document.getElementById('eventDividends').innerHTML = render(r.dividends, 'dividend');
    document.getElementById('eventSplits').innerHTML = render(r.splits, 'split');
  } catch (e) {
    console.error(e);
  }
}

// ============================================================
// 알림 탭
// ============================================================
async function loadAlerts() {
  try {
    const level = document.getElementById('alertLevel').value;
    const url = '/api/alerts?limit=200' + (level ? '&level=' + level : '');
    const r = await fetch(url).then(r => r.json());
    const el = document.getElementById('alertList');

    if (!r.items || r.items.length === 0) {
      el.innerHTML = '<div class="empty">알림 없음</div>';
      return;
    }

    el.innerHTML = r.items.map(a => `
      <div class="alert-card ${a.level || 'info'}" onclick="showDetail('${a.symbol}')">
        <span class="sym">${escapeHtml(a.symbol)}</span>
        <span class="muted">${escapeHtml(a.type || '')}</span>
        <span>${escapeHtml(a.msg || '')}</span>
        <span class="time">${fmtTime(a.t)}</span>
      </div>
    `).join('');
  } catch (e) {
    console.error(e);
  }
}

// ============================================================
// 시스템 상태 탭
// ============================================================
async function loadStatus() {
  try {
    const r = await fetch('/api/status').then(r => r.json());

    // 시스템 메트릭
    document.getElementById('sysStatus').innerHTML = `
      <div><label>준비 상태</label><b style="color:${r.ready?'var(--up)':'var(--warn)'}">${r.ready ? '✅ Ready' : '⏳ Loading'}</b></div>
      <div><label>전체 종목</label><b>${r.total_symbols.toLocaleString()}</b></div>
      <div><label>WebSocket</label><b style="color:${r.ws_connected?'var(--up)':'var(--down)'}">${r.ws_connected ? '🟢 Connected' : '🔴 Off'}</b></div>
      <div><label>재계산 대기</label><b>${r.dirty_pending}</b></div>
      <div><label>활성 이상거래</label><b>${r.anomalies_active}</b></div>
      <div><label>누적 알림</label><b>${r.alerts_total}</b></div>
    `;

    // 커버리지 테이블
    const cov = r.coverage || {};
    document.getElementById('covTbody').innerHTML = Object.entries(cov).map(([k, v]) => {
      const match = v.match(/\((\d+)%\)/);
      const pct = match ? parseInt(match[1]) : 0;
      const color = pct >= 60 ? 'var(--up)' : pct >= 30 ? 'var(--warn)' : 'var(--down)';
      return `<tr><td>${escapeHtml(k)}</td><td style="color:${color}">${escapeHtml(v)}</td></tr>`;
    }).join('');

    // 점수 분포 차트
    drawScoreDist(r.score_distribution || {});
  } catch (e) {
    console.error(e);
  }
}

function drawScoreDist(dist) {
  const ctx = document.getElementById('scoreDistChart');
  if (!ctx) return;
  if (STATE.charts.scoreDist) STATE.charts.scoreDist.destroy();

  const labels = ['0-20', '20-40', '40-60', '60-80', '80+'];
  const data = labels.map(l => dist[l] || 0);
  const colors = ['#666', '#66cc66', '#ffcc00', '#ff8800', '#ff00aa'];

  STATE.charts.scoreDist = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: '종목 수',
        data,
        backgroundColor: colors,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#888' }, grid: { color: '#2a2a4a' } },
        y: { ticks: { color: '#888' }, grid: { color: '#2a2a4a' } },
      }
    }
  });
}

// ============================================================
// 상세 모달
// ============================================================
async function showDetail(sym) {
  if (!sym) return;
  STATE.detailSym = sym;
  const modal = document.getElementById('detailModal');
  modal.classList.add('open');
  const body = document.getElementById('detailBody');
  body.innerHTML = `<div class="empty">⏳ ${sym} 로딩중...</div>`;

  try {
    // 병렬 로드
    const [bd, opt, fund, news, hist] = await Promise.all([
      fetch(`/api/scores/${sym}/breakdown`).then(r => r.json()),
      fetch(`/api/options/${sym}`).then(r => r.json()).catch(() => null),
      fetch(`/api/fundamentals/${sym}`).then(r => r.json()).catch(() => null),
      fetch(`/api/news/${sym}?limit=8`).then(r => r.json()).catch(() => null),
      fetch(`/api/scores/${sym}/history?limit=100`).then(r => r.json()).catch(() => null),
    ]);

    if (bd.error) {
      body.innerHTML = `<div class="empty">❌ ${sym} 데이터 없음</div>`;
      return;
    }

    body.innerHTML = renderDetail(sym, bd, opt, fund, news, hist);

    // 차트 그리기 (DOM 생성 후)
    setTimeout(() => {
      drawScoreHistory(hist);
      drawBreakdown(bd.breakdown);
    }, 50);
  } catch (e) {
    console.error(e);
    body.innerHTML = `<div class="empty">❌ 로딩 실패</div>`;
  }
}

function closeDetail() {
  document.getElementById('detailModal').classList.remove('open');
  STATE.detailSym = null;
  // 차트 정리
  ['scoreHist', 'breakdownChart'].forEach(k => {
    if (STATE.charts[k]) {
      STATE.charts[k].destroy();
      delete STATE.charts[k];
    }
  });
}

function renderDetail(sym, bd, opt, fund, news, hist) {
  const m = bd.metrics || {};
  const score = bd.score || 0;

  // 헤더
  let html = `
    <h2 style="display:flex;gap:12px;align-items:center">
      <span class="sym" style="font-size:1.3em">${escapeHtml(sym)}</span>
      <span class="muted">${escapeHtml(bd.name || '')}</span>
      <span style="margin-left:auto;color:${scoreColor(score)};font-size:1.3em">${score.toFixed(1)}</span>
      ${bd.grade ? `<span class="grade ${bd.grade}">${bd.grade}</span>` : ''}
    </h2>
    <div class="muted" style="margin-top:4px">${fmtPrice(bd.price)}</div>
  `;

  // 점수 히스토리 차트
  html += `
    <div class="detail-section">
      <h3>📈 점수 히스토리</h3>
      <div class="chart-wrap"><canvas id="scoreHistCanvas"></canvas></div>
    </div>
  `;

  // 점수 구성 (breakdown)
  if (bd.breakdown) {
    const items = Object.entries(bd.breakdown).map(([k, v]) => {
      const val = (typeof v === 'object' ? v.val : v) || 0;
      const max = (typeof v === 'object' ? v.max : 0) || 0;
      return `<li><span class="label">${escapeHtml(k)}</span><span class="val">${Number(val).toFixed(2)}</span><span class="max">/${max}</span></li>`;
    }).join('');
    html += `
      <div class="detail-section">
        <h3>📊 점수 구성</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
          <ul class="breakdown-list">${items}</ul>
          <div class="chart-wrap"><canvas id="breakdownCanvas"></canvas></div>
        </div>
      </div>
    `;
  }

  // 핵심 지표
  html += `
    <div class="detail-section">
      <h3>🔑 핵심 지표</h3>
      <div class="metric-grid">
        <div><label>SI%</label><b>${(m.si_pct||0).toFixed(2)}%</b></div>
        <div><label>CTB%</label><b>${(m.ctb||0).toFixed(2)}%</b></div>
        <div><label>DTC</label><b>${(m.dtc||0).toFixed(2)}</b></div>
        <div><label>Utilization</label><b>${(m.util||0).toFixed(1)}%</b></div>
        <div><label>유동주식</label><b>${fmtNum(m.float_shares, 1)}</b></div>
        <div><label>Rotation</label><b>${(m.rotation||0).toFixed(2)}x</b></div>
        <div><label>거래량 스파이크</label><b>${(m.vol_spike||0).toFixed(2)}x</b></div>
        <div><label>52주 거리</label><b>${((m.dist_52w||0)*100).toFixed(1)}%</b></div>
        <div><label>RSI</label><b>${(m.rsi14||50).toFixed(0)}</b></div>
        <div><label>소셜 속도</label><b>${(m.social_velocity||0).toFixed(0)}%</b></div>
        <div><label>촉매</label><b>${m.has_catalyst ? '✅' : '-'}</b></div>
        <div><label>MACD</label><b>${(m.macd_histogram||0).toFixed(3)}</b></div>
        <div><label>매집점수</label><b>${(m.acc_score||0).toFixed(0)}</b></div>
      </div>
    </div>
  `;

  // 옵션 체인
  if (opt && !opt.error) {
    const warn = opt.warning ? `<div class="warning-banner">⚠️ ${opt.warning}</div>` : '';
    html += `
      <div class="detail-section">
        <h3>🎯 옵션 체인</h3>
        ${warn}
        <div class="metric-grid">
          <div><label>감마 집중도</label><b>${((opt.gamma_concentration||0)*100).toFixed(1)}%</b></div>
          <div><label>C/P 비율</label><b>${(opt.call_put_ratio||0).toFixed(2)}</b></div>
          <div><label>이상 옵션 점수</label><b>${(opt.unusual_options_score||0).toFixed(0)}</b></div>
          <div><label>Max Pain</label><b>${fmtPrice(opt.max_pain)}</b></div>
          <div><label>콜 OI</label><b>${fmtNum(opt.total_call_oi, 0)}</b></div>
          <div><label>풋 OI</label><b>${fmtNum(opt.total_put_oi, 0)}</b></div>
          <div><label>콜 거래량</label><b>${fmtNum(opt.total_call_volume, 0)}</b></div>
          <div><label>풋 거래량</label><b>${fmtNum(opt.total_put_volume, 0)}</b></div>
          <div><label>IV 평균</label><b>${((opt.iv_avg||0)*100).toFixed(1)}%</b></div>
        </div>
      </div>
    `;
  }

  // 펀더멘털
  if (fund && !fund.error) {
    const warns = (fund.warnings || []).map(w => `<div class="warn-item">⚠️ ${escapeHtml(w)}</div>`).join('');
    html += `
      <div class="detail-section">
        <h3>💼 펀더멘털</h3>
        ${warns ? `<div class="warning-banner">${warns}</div>` : ''}
        <div class="metric-grid">
          <div><label>시가총액</label><b>${fmtNum(fund.market_cap, 2)}</b></div>
          <div><label>부채/자본</label><b>${(fund.debt_to_equity||0).toFixed(2)}</b></div>
          <div><label>현금소진</label><b>${(fund.cash_runway_months||0).toFixed(0)}개월</b></div>
          <div><label>매출 YoY</label><b>${(fund.revenue_growth_yoy||0).toFixed(1)}%</b></div>
          <div><label>매출</label><b>${fmtNum(fund.total_revenue, 1)}</b></div>
          <div><label>순이익</label><b>${fmtNum(fund.net_income, 1)}</b></div>
          <div><label>현금</label><b>${fmtNum(fund.cash_and_equivalents, 1)}</b></div>
          <div><label>부채</label><b>${fmtNum(fund.total_debt, 1)}</b></div>
        </div>
      </div>
    `;
  }

  // 뉴스
  if (news && news.news && news.news.length > 0) {
    const newsHtml = news.news.map(n => `
      <div style="padding:8px 0;border-bottom:1px solid var(--border)">
        <a href="${escapeHtml(n.url || '#')}" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:none">
          ${escapeHtml(n.title || '')}
        </a>
        <div class="muted" style="font-size:0.82em;margin-top:3px">
          ${escapeHtml(n.publisher || '')} · ${n.published_utc ? new Date(n.published_utc).toLocaleString('ko-KR') : ''}
        </div>
      </div>
    `).join('');
    html += `
      <div class="detail-section">
        <h3>📰 최근 뉴스 ${news.has_catalyst ? '<span class="grade HIGH" style="margin-left:8px">촉매 감지</span>' : ''}</h3>
        ${newsHtml}
      </div>
    `;
  }

  return html;
}

function drawScoreHistory(hist) {
  if (!hist || !hist.items) return;
  const ctx = document.getElementById('scoreHistCanvas');
  if (!ctx) return;
  if (STATE.charts.scoreHist) STATE.charts.scoreHist.destroy();

  const items = hist.items || [];
  const labels = items.map(it => {
    const d = new Date(it.t * 1000);
    return d.toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit'});
  });
  const data = items.map(it => it.s);

  STATE.charts.scoreHist = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'SQS 점수',
        data,
        borderColor: '#6c7dff',
        backgroundColor: 'rgba(108,125,255,0.15)',
        fill: true,
        tension: 0.3,
        pointRadius: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#888', maxTicksLimit: 10 }, grid: { color: '#2a2a4a' } },
        y: { ticks: { color: '#888' }, grid: { color: '#2a2a4a' }, suggestedMin: 0, suggestedMax: 100 },
      }
    }
  });
}

function drawBreakdown(bd) {
  if (!bd) return;
  const ctx = document.getElementById('breakdownCanvas');
  if (!ctx) return;
  if (STATE.charts.breakdownChart) STATE.charts.breakdownChart.destroy();

  const entries = Object.entries(bd);
  const labels = entries.map(([k]) => k);
  const values = entries.map(([, v]) => (typeof v === 'object' ? v.val : v) || 0);
  const maxes = entries.map(([, v]) => (typeof v === 'object' ? v.max : 0) || 0);

  STATE.charts.breakdownChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: '획득',
          data: values,
          backgroundColor: '#6c7dff',
        },
        {
          label: '최대',
          data: maxes,
          backgroundColor: 'rgba(255,255,255,0.08)',
        }
      ]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#888' } } },
      scales: {
        x: { stacked: false, ticks: { color: '#888' }, grid: { color: '#2a2a4a' } },
        y: { stacked: false, ticks: { color: '#888', font: { size: 10 } }, grid: { color: '#2a2a4a' } },
      }
    }
  });
}

// ESC 키로 모달 닫기
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeDetail();
});

// ============================================================
// 초기화
// ============================================================
async function init() {
  bindTabs();
  bindSort();
  await preloadSnapshot();
  await loadMarket();
  conn();

  // 주기적 갱신
  setInterval(chkLoad, 5000);          // 로딩 상태 (준비 안됐을 때만)
  setInterval(loadMarket, 60000);      // 시장 상태 1분
}

init();
</script>
</body>
</html>
"""
