"""Short Squeeze Hunter v3 — 통합 단일 페이지 UI"""

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>🔥 Short Squeeze Hunter v3</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0a0e1a;
    --bg2: #131826;
    --bg3: #1a2138;
    --border: #2a3454;
    --text: #e4e8f0;
    --text-dim: #8a93a8;
    --accent: #4a9eff;
    --green: #00d68f;
    --red: #ff5470;
    --orange: #ff9f43;
    --yellow: #feca57;
    --purple: #a55eea;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
  html, body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", sans-serif;
    font-size: 14px;
    line-height: 1.5;
    overflow-x: hidden;
  }
  a { color: var(--accent); text-decoration: none; }

  /* ============ 헤더 ============ */
  header {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .logo { font-size: 18px; font-weight: 700; }
  .logo .v { color: var(--accent); font-size: 12px; margin-left: 4px; }
  .status-bar {
    display: flex;
    gap: 12px;
    align-items: center;
    font-size: 12px;
    color: var(--text-dim);
  }
  .status-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--text-dim);
  }
  .status-dot.on { background: var(--green); box-shadow: 0 0 6px var(--green); }
  .status-dot.off { background: var(--red); }
  #marketStatus { font-weight: 600; }

  /* ============ 탭 ============ */
  .tabs {
    display: flex;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 0 20px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }
  .tabs::-webkit-scrollbar { display: none; }
  .tab {
    padding: 12px 18px;
    cursor: pointer;
    color: var(--text-dim);
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    font-size: 14px;
    transition: all 0.15s;
  }
  .tab:hover { color: var(--text); }
  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
    font-weight: 600;
  }

  /* ============ 메인 ============ */
  main { padding: 20px; }
  .panel {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
  }
  .panel h2 {
    font-size: 15px;
    margin-bottom: 12px;
    color: var(--text);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .panel h2 .count {
    font-size: 12px;
    color: var(--text-dim);
    font-weight: 400;
  }

  /* ============ 필터 ============ */
  .filter-bar {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
    align-items: center;
  }
  .filter-bar input,
  .filter-bar select {
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 13px;
  }
  .filter-bar input { width: 120px; }
  .filter-bar button {
    background: var(--accent);
    color: white;
    border: none;
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
    font-weight: 600;
  }
  .filter-bar button:hover { opacity: 0.85; }
  .filter-bar .info {
    margin-left: auto;
    color: var(--text-dim);
    font-size: 12px;
  }

  /* ============ 테이블 (PC) ============ */
  .table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }
  thead { background: var(--bg3); position: sticky; top: 0; }
  th {
    padding: 10px 8px;
    text-align: left;
    color: var(--text-dim);
    font-weight: 600;
    cursor: pointer;
    user-select: none;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  th:hover { color: var(--text); }
  th .arrow { color: var(--accent); margin-left: 2px; }
  td {
    padding: 8px;
    border-bottom: 1px solid rgba(42, 52, 84, 0.5);
    white-space: nowrap;
  }
  tbody tr { cursor: pointer; transition: background 0.1s; }
  tbody tr:hover { background: var(--bg3); }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  td.sym { font-weight: 700; }
  .pos { color: var(--green); }
  .neg { color: var(--red); }

  /* 등급 배지 */
  .grade {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
  }
  .g-IMMINENT { background: var(--red); color: white; }
  .g-HIGH { background: var(--orange); color: white; }
  .g-WATCH { background: var(--yellow); color: #333; }
  .g-NORMAL { background: var(--bg3); color: var(--text-dim); }

  /* 점수 색상 */
  .s-high { color: var(--red); font-weight: 700; }
  .s-mid { color: var(--orange); font-weight: 600; }
  .s-low { color: var(--text-dim); }

  /* ============ 모바일 카드 ============ */
  .mobile-card-list { display: none; }
  .mobile-card {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
    cursor: pointer;
  }
  .mobile-card:active { background: var(--bg2); }
  .mobile-card-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .mobile-card-sym {
    font-size: 18px;
    font-weight: 700;
  }
  .mobile-card-name {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 2px;
  }
  .mobile-card-score {
    font-size: 24px;
    font-weight: 800;
  }
  .mobile-card-mid {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 8px;
  }
  .mobile-card-price {
    font-size: 16px;
    font-weight: 600;
  }
  .mobile-card-change {
    font-size: 14px;
    font-weight: 600;
  }
  .mobile-card-bottom {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    font-size: 11px;
  }
  .mc-stat {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .mc-stat-label {
    color: var(--text-dim);
    font-size: 10px;
  }
  .mc-stat-value {
    font-weight: 600;
    font-size: 12px;
  }

  /* ============ 페이지네이션 ============ */
  .pagination {
    display: flex;
    justify-content: center;
    gap: 6px;
    margin-top: 16px;
    flex-wrap: wrap;
  }
  .pagination button {
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    min-width: 32px;
  }
  .pagination button.active {
    background: var(--accent);
    border-color: var(--accent);
    font-weight: 700;
  }
  .pagination button:disabled { opacity: 0.4; cursor: not-allowed; }

  /* ============ 테마/누적/이상거래/이벤트/알림 카드 ============ */
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }
  .theme-card, .anom-card, .event-card, .alert-card, .acc-card {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
  }
  .theme-card h3 {
    font-size: 14px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
  }
  .theme-card h3 .cnt { color: var(--text-dim); font-size: 11px; }
  .theme-list { font-size: 12px; }
  .theme-list .row {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
  }
  .theme-list .row:hover { color: var(--accent); cursor: pointer; }

  /* 이상거래 / 알림 레벨 */
  .badge {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
    margin-right: 4px;
  }
  .lv-critical { background: var(--red); color: white; }
  .lv-high { background: var(--orange); color: white; }
  .lv-info { background: var(--accent); color: white; }

  .anom-card .anom-head,
  .event-card .event-head,
  .alert-card .alert-head {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
    font-weight: 600;
  }
  .anom-card .anom-msg,
  .event-card .event-msg,
  .alert-card .alert-msg {
    font-size: 12px;
    color: var(--text-dim);
  }
  .anom-card .anom-time,
  .alert-card .alert-time {
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 6px;
  }

  /* 누적 신호 */
  .acc-card {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .acc-tags { display: flex; gap: 4px; flex-wrap: wrap; }
  .acc-tag {
    background: var(--bg2);
    border: 1px solid var(--border);
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10px;
  }
  .tier-stats {
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }
  .tier-stat {
    background: var(--bg3);
    border: 1px solid var(--border);
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
  }
  .tier-stat .v { font-size: 18px; font-weight: 700; }

  /* ============ 시스템 상태 ============ */
  .status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }
  .status-box {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
  }
  .status-box .label { color: var(--text-dim); font-size: 11px; }
  .status-box .value { font-size: 20px; font-weight: 700; margin-top: 4px; }
  .coverage-table {
    width: 100%;
    font-size: 12px;
  }
  .coverage-bar {
    background: var(--bg);
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    width: 100%;
  }
  .coverage-bar-fill {
    background: var(--green);
    height: 100%;
    transition: width 0.3s;
  }
  .coverage-bar-fill.low { background: var(--red); }
  .coverage-bar-fill.mid { background: var(--orange); }

  /* ============ 상세 모달 ============ */
  .modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.75);
    z-index: 1000;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }
  .modal-overlay.show { display: block; }
  .modal {
    background: var(--bg2);
    margin: 40px auto;
    max-width: 900px;
    border-radius: 8px;
    border: 1px solid var(--border);
    padding: 20px;
    position: relative;
  }
  .modal-close {
    position: absolute;
    top: 12px;
    right: 16px;
    font-size: 24px;
    cursor: pointer;
    color: var(--text-dim);
    background: none;
    border: none;
    width: 32px;
    height: 32px;
  }
  .modal-close:hover { color: var(--text); }
  .modal h2 { font-size: 22px; margin-bottom: 4px; }
  .modal .subtitle { color: var(--text-dim); margin-bottom: 16px; }
  .modal-section {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 12px;
  }
  .modal-section h3 {
    font-size: 13px;
    margin-bottom: 8px;
    color: var(--text-dim);
    text-transform: uppercase;
  }
  .metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 8px;
  }
  .metric-item {
    background: var(--bg2);
    padding: 6px 8px;
    border-radius: 4px;
    font-size: 11px;
  }
  .metric-item .lbl { color: var(--text-dim); font-size: 10px; }
  .metric-item .val { font-size: 13px; font-weight: 600; margin-top: 2px; }
  .warning-banner {
    background: rgba(255, 84, 112, 0.15);
    border: 1px solid var(--red);
    color: var(--red);
    padding: 8px 12px;
    border-radius: 4px;
    margin-bottom: 12px;
    font-size: 12px;
    font-weight: 600;
  }

  /* ============ 로딩 ============ */
  .loading {
    text-align: center;
    padding: 40px;
    color: var(--text-dim);
  }
  .progress-bar {
    background: var(--bg3);
    height: 6px;
    border-radius: 3px;
    overflow: hidden;
    max-width: 400px;
    margin: 16px auto;
  }
  .progress-bar-fill {
    background: var(--accent);
    height: 100%;
    transition: width 0.3s;
  }

  /* ============ 모바일 반응형 ============ */
  @media (max-width: 768px) {
    header { padding: 10px 12px; flex-wrap: wrap; gap: 8px; }
    .logo { font-size: 16px; }
    .status-bar { font-size: 10px; gap: 6px; flex-wrap: wrap; }
    .tabs { padding: 0 12px; }
    .tab { padding: 10px 12px; font-size: 13px; }
    main { padding: 12px; }
    .panel { padding: 12px; }

    /* PC 테이블 숨기고 모바일 카드 보이기 */
    .table-wrap { display: none; }
    .mobile-card-list { display: block; }

    .filter-bar { gap: 6px; }
    .filter-bar input,
    .filter-bar select { width: 100%; font-size: 14px; }
    .filter-bar input.short { width: calc(50% - 3px); }
    .filter-bar .info { width: 100%; margin-left: 0; }

    .card-grid {
      grid-template-columns: 1fr;
      gap: 8px;
    }
    .modal { margin: 0; border-radius: 0; min-height: 100vh; }
    .modal h2 { font-size: 18px; }
    .metric-grid {
      grid-template-columns: repeat(2, 1fr);
    }
    .status-grid {
      grid-template-columns: repeat(2, 1fr);
    }
    .tier-stats { gap: 6px; }
    .tier-stat { font-size: 11px; padding: 6px 10px; }
    .tier-stat .v { font-size: 16px; }
  }

  @media (max-width: 480px) {
    .mobile-card-bottom {
      grid-template-columns: repeat(3, 1fr);
    }
  }
</style>
</head>
<body>

<header>
  <div>
    <span class="logo">🔥 Short Squeeze Hunter <span class="v">v3</span></span>
  </div>
  <div class="status-bar">
    <div class="status-item">
      <div id="wsDot" class="status-dot"></div>
      <span id="wsLabel">연결 중...</span>
    </div>
    <div class="status-item">
      <span id="marketStatus">시장 확인 중...</span>
    </div>
    <div class="status-item">
      <span id="loadStatus">로딩...</span>
    </div>
  </div>
</header>

<div class="tabs">
  <div class="tab active" data-tab="main">📊 대시보드</div>
  <div class="tab" data-tab="themes">🎯 테마</div>
  <div class="tab" data-tab="accumulation">💎 누적신호</div>
  <div class="tab" data-tab="anomalies">⚡ 이상거래</div>
  <div class="tab" data-tab="events">📅 이벤트</div>
  <div class="tab" data-tab="alerts">🔔 알림</div>
  <div class="tab" data-tab="status">⚙️ 상태</div>
</div>

<main>
  <!-- ===== 대시보드 ===== -->
  <section id="tab-main" class="tab-content">
    <div class="panel">
      <h2>실시간 스코어보드 <span class="count" id="mainCount">0개</span></h2>
      <div class="filter-bar">
        <input type="text" id="filterSym" placeholder="심볼 검색..." class="short">
        <select id="filterGrade">
          <option value="">모든 등급</option>
          <option value="IMMINENT">IMMINENT</option>
          <option value="HIGH">HIGH</option>
          <option value="WATCH">WATCH</option>
          <option value="NORMAL">NORMAL</option>
        </select>
        <input type="number" id="filterMinScore" placeholder="최소 점수" class="short">
        <button onclick="applyFilter()">필터</button>
        <span class="info" id="filterInfo"></span>
      </div>

      <!-- PC 테이블 -->
      <div class="table-wrap">
        <table id="mainTable">
          <thead>
            <tr>
              <th data-sort="symbol">심볼</th>
              <th data-sort="name">이름</th>
              <th data-sort="theme">테마</th>
              <th class="num" data-sort="price">가격</th>
              <th class="num" data-sort="change_pct">변동%</th>
              <th class="num" data-sort="volume">거래량</th>
              <th class="num" data-sort="sqs_score">SQS</th>
              <th data-sort="grade">등급</th>
              <th class="num" data-sort="si_pct">SI%</th>
              <th class="num" data-sort="ctb">CTB%</th>
              <th class="num" data-sort="rsi14">RSI</th>
            </tr>
          </thead>
          <tbody id="mainBody"></tbody>
        </table>
      </div>

      <!-- 모바일 카드 -->
      <div class="mobile-card-list" id="mainCardList"></div>

      <div class="pagination" id="pagination"></div>
    </div>
  </section>

  <!-- ===== 테마 ===== -->
  <section id="tab-themes" class="tab-content" style="display:none">
    <div class="panel">
      <h2>테마별 종목 <span class="count" id="themesCount"></span></h2>
      <div id="themesGrid" class="card-grid"><div class="loading">로딩 중...</div></div>
    </div>
  </section>

  <!-- ===== 누적신호 ===== -->
  <section id="tab-accumulation" class="tab-content" style="display:none">
    <div class="panel">
      <h2>스마트머니 누적 신호 <span class="count" id="accCount"></span></h2>
      <div id="tierStats" class="tier-stats"></div>
      <div id="accGrid" class="card-grid"><div class="loading">로딩 중...</div></div>
    </div>
  </section>

  <!-- ===== 이상거래 ===== -->
  <section id="tab-anomalies" class="tab-content" style="display:none">
    <div class="panel">
      <h2>이상거래 탐지 <span class="count" id="anomCount"></span></h2>
      <div class="filter-bar">
        <select id="anomSeverity">
          <option value="">전체</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="info">Info</option>
        </select>
        <button onclick="loadAnomalies()">새로고침</button>
      </div>
      <div id="anomGrid" class="card-grid"><div class="loading">로딩 중...</div></div>
    </div>
  </section>

  <!-- ===== 이벤트 ===== -->
  <section id="tab-events" class="tab-content" style="display:none">
    <div class="panel">
      <h2>예정 이벤트 <span class="count" id="eventsCount"></span></h2>
      <div class="filter-bar">
        <select id="eventDays">
          <option value="3">3일 이내</option>
          <option value="7" selected>7일 이내</option>
          <option value="14">14일 이내</option>
          <option value="30">30일 이내</option>
        </select>
        <button onclick="loadEvents()">새로고침</button>
      </div>
      <div id="eventsContainer"><div class="loading">로딩 중...</div></div>
    </div>
  </section>

  <!-- ===== 알림 ===== -->
  <section id="tab-alerts" class="tab-content" style="display:none">
    <div class="panel">
      <h2>최근 알림 <span class="count" id="alertsCount"></span></h2>
      <div class="filter-bar">
        <select id="alertLevel">
          <option value="">전체</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="info">Info</option>
        </select>
        <button onclick="loadAlerts()">새로고침</button>
      </div>
      <div id="alertsGrid" class="card-grid"><div class="loading">로딩 중...</div></div>
    </div>
  </section>

  <!-- ===== 시스템 상태 ===== -->
  <section id="tab-status" class="tab-content" style="display:none">
    <div class="panel">
      <h2>시스템 상태</h2>
      <div id="statusGrid" class="status-grid"><div class="loading">로딩 중...</div></div>
    </div>
    <div class="panel">
      <h2>데이터 커버리지</h2>
      <table class="coverage-table" id="coverageTable"></table>
    </div>
    <div class="panel">
      <h2>점수 분포</h2>
      <canvas id="scoreDistChart" height="100"></canvas>
    </div>
  </section>
</main>

<!-- 상세 모달 -->
<div id="detailModal" class="modal-overlay" onclick="if(event.target===this)closeDetail()">
  <div class="modal">
    <button class="modal-close" onclick="closeDetail()">×</button>
    <div id="detailBody"></div>
  </div>
</div>

"""

HTML_PAGE += r"""
<script>
// ============================================================
// 전역 상태
// ============================================================
let allRows = [];        // 전체 종목 (서버 스냅샷)
let filteredRows = [];   // 필터/정렬 후
let sortKey = "sqs_score";
let sortDir = "desc";
let currentPage = 1;
const PAGE_SIZE_PC = 50;
const PAGE_SIZE_MOBILE = 20;
let ws = null;
let wsReconnectTimer = null;
let detailCharts = { history: null, breakdown: null };

const isMobile = () => window.innerWidth <= 768;

// ============================================================
// 유틸
// ============================================================
function fmtNum(v, digits) {
  if (v === null || v === undefined || isNaN(v)) return "-";
  digits = digits ?? 2;
  return Number(v).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}
function fmtInt(v) {
  if (v === null || v === undefined || isNaN(v)) return "-";
  return Number(v).toLocaleString("en-US");
}
function fmtVol(v) {
  if (!v || isNaN(v)) return "-";
  if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (v >= 1e3) return (v / 1e3).toFixed(1) + "K";
  return String(v);
}
function fmtPct(v, digits) {
  if (v === null || v === undefined || isNaN(v)) return "-";
  digits = digits ?? 2;
  return Number(v).toFixed(digits) + "%";
}
function fmtMcap(v) {
  if (!v || isNaN(v)) return "-";
  if (v >= 1e12) return "$" + (v / 1e12).toFixed(2) + "T";
  if (v >= 1e9) return "$" + (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6) return "$" + (v / 1e6).toFixed(2) + "M";
  return "$" + fmtInt(v);
}
function fmtTime(ts) {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  return d.toLocaleString("ko-KR", { hour12: false });
}
function fmtDate(s) {
  if (!s) return "-";
  return s.substring(0, 10);
}
function scoreClass(s) {
  if (s >= 70) return "s-high";
  if (s >= 50) return "s-mid";
  return "s-low";
}
function pctClass(v) {
  if (v > 0) return "pos";
  if (v < 0) return "neg";
  return "";
}

// ============================================================
// 탭
// ============================================================
function bindTabs() {
  document.querySelectorAll(".tab").forEach(t => {
    t.addEventListener("click", () => showTab(t.dataset.tab));
  });
}
function showTab(name) {
  document.querySelectorAll(".tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  document.querySelectorAll(".tab-content").forEach(c => {
    c.style.display = c.id === "tab-" + name ? "" : "none";
  });
  // 탭별 자동 로딩
  if (name === "themes") loadThemes();
  else if (name === "accumulation") loadAccumulation();
  else if (name === "anomalies") loadAnomalies();
  else if (name === "events") loadEvents();
  else if (name === "alerts") loadAlerts();
  else if (name === "status") loadStatus();
}

// ============================================================
// 시장 상태
// ============================================================
async function loadMarket() {
  try {
    const r = await fetch("/api/market");
    const j = await r.json();
    const el = document.getElementById("marketStatus");
    if (!el) return;
    const session = j.session || "closed";
    const label = j.label || "마감";
    el.textContent = label;
    if (session === "regular") el.style.color = "var(--green)";
    else if (session === "pre") el.style.color = "var(--yellow)";
    else if (session === "after") el.style.color = "var(--orange)";
    else el.style.color = "var(--red)";
  } catch (e) {
    console.warn("market load fail", e);
  }
}

// ============================================================
// 로딩 상태 체크
// ============================================================
async function chkLoad() {
  try {
    const r = await fetch("/health");
    const j = await r.json();
    const el = document.getElementById("loadStatus");
    if (!el) return;
    if (j.status === "ok" && j.loaded > 0) {
      el.textContent = `📦 ${fmtInt(j.loaded)}개 로드`;
      el.style.color = "var(--green)";
    } else {
      el.textContent = "⏳ 로딩 중...";
      el.style.color = "var(--yellow)";
    }
  } catch (e) {}
}

// ============================================================
// 초기 스냅샷
// ============================================================
async function preloadSnapshot() {
  try {
    const r = await fetch("/api/snapshot?limit=2000");
    const j = await r.json();
    allRows = j.items || [];
    applyFilter();
  } catch (e) {
    console.error("snapshot load fail", e);
    document.getElementById("mainBody").innerHTML =
      '<tr><td colspan="11" style="text-align:center;padding:40px;color:var(--red)">데이터 로드 실패. 잠시 후 새로고침하세요.</td></tr>';
  }
}

// ============================================================
// 필터 + 정렬
// ============================================================
function applyFilter() {
  const sym = (document.getElementById("filterSym")?.value || "").toUpperCase().trim();
  const grade = document.getElementById("filterGrade")?.value || "";
  const minScore = parseFloat(document.getElementById("filterMinScore")?.value) || 0;

  filteredRows = allRows.filter(r => {
    if (sym && !(r.symbol || "").toUpperCase().includes(sym)) return false;
    if (grade && r.grade !== grade) return false;
    if (minScore > 0 && (r.sqs_score || 0) < minScore) return false;
    return true;
  });

  sortRows();
  currentPage = 1;
  renderMain();

  const info = document.getElementById("filterInfo");
  if (info) info.textContent = `${fmtInt(filteredRows.length)} / ${fmtInt(allRows.length)}`;
  document.getElementById("mainCount").textContent = `${fmtInt(filteredRows.length)}개`;
}

function bindSort() {
  document.querySelectorAll("#mainTable th[data-sort]").forEach(th => {
    th.addEventListener("click", () => {
      const k = th.dataset.sort;
      if (sortKey === k) sortDir = sortDir === "asc" ? "desc" : "asc";
      else { sortKey = k; sortDir = "desc"; }
      sortRows();
      renderMain();
    });
  });
}

function sortRows() {
  const k = sortKey, dir = sortDir === "asc" ? 1 : -1;
  filteredRows.sort((a, b) => {
    let va = a[k], vb = b[k];
    if (va === null || va === undefined) va = (typeof vb === "number") ? -Infinity : "";
    if (vb === null || vb === undefined) vb = (typeof va === "number") ? -Infinity : "";
    if (typeof va === "string") return va.localeCompare(vb) * dir;
    return (va - vb) * dir;
  });
  // 헤더 화살표 갱신
  document.querySelectorAll("#mainTable th").forEach(th => {
    const a = th.dataset.sort === sortKey ? (sortDir === "asc" ? " ▲" : " ▼") : "";
    th.innerHTML = th.textContent.replace(/[▲▼]/g, "").trim() + (a ? `<span class="arrow">${a}</span>` : "");
  });
}

// ============================================================
// 메인 렌더링 (PC 테이블 + 모바일 카드)
// ============================================================
function renderMain() {
  const pageSize = isMobile() ? PAGE_SIZE_MOBILE : PAGE_SIZE_PC;
  const start = (currentPage - 1) * pageSize;
  const end = start + pageSize;
  const pageRows = filteredRows.slice(start, end);

  renderTable(pageRows);
  renderCards(pageRows);
  renderPagination(pageSize);
}

function renderTable(rows) {
  const tb = document.getElementById("mainBody");
  if (!tb) return;
  if (!rows.length) {
    tb.innerHTML = '<tr><td colspan="11" style="text-align:center;padding:40px;color:var(--text-dim)">결과가 없습니다.</td></tr>';
    return;
  }
  tb.innerHTML = rows.map(r => `
    <tr onclick="showDetail('${r.symbol}')">
      <td class="sym">${r.symbol || "-"}</td>
      <td>${(r.name || "-").substring(0, 24)}</td>
      <td>${r.theme || "-"}</td>
      <td class="num">$${fmtNum(r.price)}</td>
      <td class="num ${pctClass(r.change_pct)}">${fmtPct(r.change_pct)}</td>
      <td class="num">${fmtVol(r.volume)}</td>
      <td class="num ${scoreClass(r.sqs_score || 0)}">${fmtNum(r.sqs_score, 1)}</td>
      <td><span class="grade g-${r.grade || 'NORMAL'}">${r.grade || "NORMAL"}</span></td>
      <td class="num">${fmtPct((r.si_pct || 0) * 100, 1)}</td>
      <td class="num">${fmtPct(r.ctb, 1)}</td>
      <td class="num">${fmtNum(r.rsi14, 1)}</td>
    </tr>
  `).join("");
}

function renderCards(rows) {
  const list = document.getElementById("mainCardList");
  if (!list) return;
  if (!rows.length) {
    list.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-dim)">결과가 없습니다.</div>';
    return;
  }
  list.innerHTML = rows.map(r => `
    <div class="mobile-card" onclick="showDetail('${r.symbol}')">
      <div class="mobile-card-top">
        <div>
          <div class="mobile-card-sym">${r.symbol || "-"}</div>
          <div class="mobile-card-name">${(r.name || "").substring(0, 28)}</div>
        </div>
        <div style="text-align:right">
          <div class="mobile-card-score ${scoreClass(r.sqs_score || 0)}">${fmtNum(r.sqs_score, 0)}</div>
          <span class="grade g-${r.grade || 'NORMAL'}">${r.grade || "NORMAL"}</span>
        </div>
      </div>
      <div class="mobile-card-mid">
        <div class="mobile-card-price">$${fmtNum(r.price)}</div>
        <div class="mobile-card-change ${pctClass(r.change_pct)}">${fmtPct(r.change_pct)}</div>
      </div>
      <div class="mobile-card-bottom">
        <div class="mc-stat">
          <span class="mc-stat-label">거래량</span>
          <span class="mc-stat-value">${fmtVol(r.volume)}</span>
        </div>
        <div class="mc-stat">
          <span class="mc-stat-label">SI%</span>
          <span class="mc-stat-value">${fmtPct((r.si_pct || 0) * 100, 1)}</span>
        </div>
        <div class="mc-stat">
          <span class="mc-stat-label">CTB%</span>
          <span class="mc-stat-value">${fmtPct(r.ctb, 1)}</span>
        </div>
        <div class="mc-stat">
          <span class="mc-stat-label">RSI</span>
          <span class="mc-stat-value">${fmtNum(r.rsi14, 0)}</span>
        </div>
      </div>
    </div>
  `).join("");
}

function renderPagination(pageSize) {
  const total = filteredRows.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const el = document.getElementById("pagination");
  if (!el) return;

  if (totalPages <= 1) { el.innerHTML = ""; return; }

  let html = "";
  html += `<button onclick="goPage(1)" ${currentPage===1?"disabled":""}>«</button>`;
  html += `<button onclick="goPage(${currentPage-1})" ${currentPage===1?"disabled":""}>‹</button>`;

  // 페이지 번호 (현재 ±2)
  const start = Math.max(1, currentPage - 2);
  const end = Math.min(totalPages, currentPage + 2);
  for (let i = start; i <= end; i++) {
    html += `<button class="${i===currentPage?'active':''}" onclick="goPage(${i})">${i}</button>`;
  }
  html += `<button onclick="goPage(${currentPage+1})" ${currentPage===totalPages?"disabled":""}>›</button>`;
  html += `<button onclick="goPage(${totalPages})" ${currentPage===totalPages?"disabled":""}>»</button>`;

  el.innerHTML = html;
}

function goPage(p) {
  const pageSize = isMobile() ? PAGE_SIZE_MOBILE : PAGE_SIZE_PC;
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  currentPage = Math.max(1, Math.min(p, totalPages));
  renderMain();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ============================================================
// 입력 이벤트 (디바운스 검색)
// ============================================================
let filterTimer = null;
function bindFilterInputs() {
  ["filterSym", "filterMinScore"].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", () => {
      clearTimeout(filterTimer);
      filterTimer = setTimeout(applyFilter, 300);
    });
  });
  const gr = document.getElementById("filterGrade");
  if (gr) gr.addEventListener("change", applyFilter);
}

// ============================================================
// WebSocket 실시간
// ============================================================
function conn() {
  if (ws && ws.readyState === WebSocket.OPEN) return;
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${proto}//${location.host}/ws/scores`;
  try {
    ws = new WebSocket(url);
  } catch (e) {
    setWsStatus(false);
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    setWsStatus(true);
    // 30초마다 ping
    if (ws._pingTimer) clearInterval(ws._pingTimer);
    ws._pingTimer = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 30000);
  };

  ws.onmessage = (evt) => {
    let msg;
    try { msg = JSON.parse(evt.data); } catch { return; }
    if (msg.type === "snapshot" && Array.isArray(msg.items)) {
      mergeUpdates(msg.items);
    } else if (msg.type === "update" && Array.isArray(msg.items)) {
      mergeUpdates(msg.items);
    } else if (msg.type === "heartbeat") {
      // 무시
    }
  };

  ws.onclose = () => {
    setWsStatus(false);
    if (ws && ws._pingTimer) clearInterval(ws._pingTimer);
    scheduleReconnect();
  };
  ws.onerror = () => {
    setWsStatus(false);
  };
}

function scheduleReconnect() {
  if (wsReconnectTimer) return;
  wsReconnectTimer = setTimeout(() => {
    wsReconnectTimer = null;
    conn();
  }, 5000);
}

function setWsStatus(on) {
  const dot = document.getElementById("wsDot");
  const lbl = document.getElementById("wsLabel");
  if (!dot || !lbl) return;
  dot.classList.toggle("on", on);
  dot.classList.toggle("off", !on);
  lbl.textContent = on ? "실시간 연결" : "재연결 중...";
}

function mergeUpdates(items) {
  const byId = {};
  items.forEach(it => { byId[it.symbol] = it; });
  for (let i = 0; i < allRows.length; i++) {
    const u = byId[allRows[i].symbol];
    if (u) Object.assign(allRows[i], u);
  }
  // 현재 화면에 보이는 페이지만 다시 렌더
  // 정렬 키가 동적 값이면 재정렬 후 렌더 (스크롤 유지 위해 페이지는 유지)
  sortRows();
  renderMain();
}

// 윈도우 리사이즈: PC↔모바일 전환 시 페이지 재계산
let resizeTimer = null;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    currentPage = 1;
    renderMain();
  }, 200);
});
</script>
"""

HTML_PAGE += r"""
<script>
// ============================================================
// 테마 탭
// ============================================================
async function loadThemes() {
  const grid = document.getElementById("themesGrid");
  grid.innerHTML = '<div class="loading">로딩 중...</div>';
  try {
    const r = await fetch("/api/themes");
    const j = await r.json();
    const themes = j.themes || [];
    document.getElementById("themesCount").textContent = `${themes.length}개 테마`;

    if (!themes.length) {
      grid.innerHTML = '<div class="loading">테마 데이터가 없습니다.</div>';
      return;
    }

    grid.innerHTML = themes.map(t => `
      <div class="theme-card">
        <h3>
          <span>${t.theme}</span>
          <span class="cnt">${t.count}개 · 평균 ${fmtNum(t.avg_score, 1)}</span>
        </h3>
        <div class="theme-list">
          ${(t.top || []).map(s => `
            <div class="row" onclick="showDetail('${s.symbol}')">
              <span><strong>${s.symbol}</strong> ${(s.name || "").substring(0, 18)}</span>
              <span class="${scoreClass(s.sqs_score || 0)}">${fmtNum(s.sqs_score, 1)}</span>
            </div>
          `).join("")}
        </div>
      </div>
    `).join("");
  } catch (e) {
    grid.innerHTML = '<div class="loading" style="color:var(--red)">로드 실패</div>';
  }
}

// ============================================================
// 누적신호 탭
// ============================================================
async function loadAccumulation() {
  const grid = document.getElementById("accGrid");
  grid.innerHTML = '<div class="loading">로딩 중...</div>';
  try {
    const r = await fetch("/api/accumulation?limit=200&min_score=40");
    const j = await r.json();
    const items = j.items || [];

    // tier 통계
    const tiers = { STRONG: 0, ACTIVE: 0, WEAK: 0, EMERGING: 0 };
    items.forEach(it => { if (tiers[it.tier] !== undefined) tiers[it.tier]++; });

    document.getElementById("tierStats").innerHTML = `
      <div class="tier-stat"><div>STRONG</div><div class="v" style="color:var(--red)">${tiers.STRONG}</div></div>
      <div class="tier-stat"><div>ACTIVE</div><div class="v" style="color:var(--orange)">${tiers.ACTIVE}</div></div>
      <div class="tier-stat"><div>EMERGING</div><div class="v" style="color:var(--yellow)">${tiers.EMERGING}</div></div>
      <div class="tier-stat"><div>WEAK</div><div class="v" style="color:var(--text-dim)">${tiers.WEAK}</div></div>
    `;
    document.getElementById("accCount").textContent = `${items.length}개`;

    if (!items.length) {
      grid.innerHTML = '<div class="loading">누적 신호 종목 없음</div>';
      return;
    }

    grid.innerHTML = items.map(it => `
      <div class="acc-card" onclick="showDetail('${it.symbol}')" style="cursor:pointer">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div>
            <strong style="font-size:15px">${it.symbol}</strong>
            <span style="color:var(--text-dim);font-size:11px;margin-left:6px">${(it.name||"").substring(0,18)}</span>
          </div>
          <span class="grade g-${it.grade || 'NORMAL'}">${it.tier}</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:12px">
          <span>누적점수: <strong class="${scoreClass(it.acc_score)}">${fmtNum(it.acc_score, 1)}</strong></span>
          <span>SQS: <strong class="${scoreClass(it.sqs_score)}">${fmtNum(it.sqs_score, 1)}</strong></span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-dim)">
          <span>$${fmtNum(it.price)}</span>
          <span class="${pctClass(it.change_pct)}">${fmtPct(it.change_pct)}</span>
          <span>${fmtVol(it.volume)}</span>
        </div>
        ${it.signals && it.signals.length ? `
          <div class="acc-tags">
            ${it.signals.slice(0, 4).map(s => `<span class="acc-tag">${s}</span>`).join("")}
          </div>
        ` : ""}
      </div>
    `).join("");
  } catch (e) {
    grid.innerHTML = '<div class="loading" style="color:var(--red)">로드 실패</div>';
  }
}

// ============================================================
// 이상거래 탭
// ============================================================
async function loadAnomalies() {
  const grid = document.getElementById("anomGrid");
  grid.innerHTML = '<div class="loading">로딩 중...</div>';
  try {
    const sev = document.getElementById("anomSeverity").value;
    const q = sev ? `?severity=${sev}&limit=100` : "?limit=100";
    const r = await fetch("/api/anomalies" + q);
    const j = await r.json();
    const items = j.items || [];
    document.getElementById("anomCount").textContent = `${items.length}개`;

    if (!items.length) {
      grid.innerHTML = '<div class="loading">감지된 이상거래 없음</div>';
      return;
    }

    grid.innerHTML = items.map(it => `
      <div class="anom-card" onclick="showDetail('${it.symbol}')" style="cursor:pointer">
        <div class="anom-head">
          <span>
            <span class="badge lv-${it.level || 'info'}">${(it.level||'info').toUpperCase()}</span>
            <strong>${it.symbol}</strong>
          </span>
          <span class="${scoreClass(it.sqs_score || 0)}">${fmtNum(it.sqs_score, 1)}</span>
        </div>
        <div class="anom-msg">${it.msg || it.type || "-"}</div>
        <div class="anom-time">${fmtTime(it.t)}</div>
      </div>
    `).join("");
  } catch (e) {
    grid.innerHTML = '<div class="loading" style="color:var(--red)">로드 실패</div>';
  }
}

// ============================================================
// 이벤트 탭
// ============================================================
async function loadEvents() {
  const container = document.getElementById("eventsContainer");
  container.innerHTML = '<div class="loading">로딩 중...</div>';
  try {
    const days = document.getElementById("eventDays").value || 7;
    const r = await fetch(`/api/events?days=${days}`);
    const j = await r.json();
    const earnings = j.earnings || [];
    const dividends = j.dividends || [];
    const splits = j.splits || [];

    const total = earnings.length + dividends.length + splits.length;
    document.getElementById("eventsCount").textContent = `${total}건`;

    if (!total) {
      container.innerHTML = `<div class="loading">${days}일 이내 예정 이벤트 없음</div>`;
      return;
    }

    container.innerHTML = `
      ${earnings.length ? `
        <h3 style="font-size:14px;margin:12px 0 8px">📊 실적 발표 (${earnings.length})</h3>
        <div class="card-grid">
          ${earnings.map(e => `
            <div class="event-card" onclick="showDetail('${e.symbol}')" style="cursor:pointer">
              <div class="event-head">
                <strong>${e.symbol}</strong>
                <span style="color:var(--orange)">D-${e.days_to}</span>
              </div>
              <div class="event-msg">${fmtDate(e.date)} · ${e.timing || ""}</div>
            </div>
          `).join("")}
        </div>` : ""}
      ${dividends.length ? `
        <h3 style="font-size:14px;margin:16px 0 8px">💰 배당 (${dividends.length})</h3>
        <div class="card-grid">
          ${dividends.map(e => `
            <div class="event-card" onclick="showDetail('${e.symbol}')" style="cursor:pointer">
              <div class="event-head">
                <strong>${e.symbol}</strong>
                <span style="color:var(--green)">D-${e.days_to}</span>
              </div>
              <div class="event-msg">배당락: ${fmtDate(e.ex_date)} · $${fmtNum(e.cash_amount, 4)}</div>
            </div>
          `).join("")}
        </div>` : ""}
      ${splits.length ? `
        <h3 style="font-size:14px;margin:16px 0 8px">🔀 액면분할 (${splits.length})</h3>
        <div class="card-grid">
          ${splits.map(e => `
            <div class="event-card" onclick="showDetail('${e.symbol}')" style="cursor:pointer">
              <div class="event-head">
                <strong>${e.symbol}</strong>
                <span style="color:var(--purple)">D-${e.days_to}</span>
              </div>
              <div class="event-msg">${fmtDate(e.execution_date)} · ${e.split_from}:${e.split_to}</div>
            </div>
          `).join("")}
        </div>` : ""}
    `;
  } catch (e) {
    container.innerHTML = '<div class="loading" style="color:var(--red)">로드 실패</div>';
  }
}

// ============================================================
// 알림 탭
// ============================================================
async function loadAlerts() {
  const grid = document.getElementById("alertsGrid");
  grid.innerHTML = '<div class="loading">로딩 중...</div>';
  try {
    const lv = document.getElementById("alertLevel").value;
    const q = lv ? `?level=${lv}&limit=200` : "?limit=200";
    const r = await fetch("/api/alerts" + q);
    const j = await r.json();
    const items = j.items || [];
    document.getElementById("alertsCount").textContent = `${items.length}개`;

    if (!items.length) {
      grid.innerHTML = '<div class="loading">알림 없음</div>';
      return;
    }

    grid.innerHTML = items.map(it => `
      <div class="alert-card" onclick="showDetail('${it.symbol}')" style="cursor:pointer">
        <div class="alert-head">
          <span>
            <span class="badge lv-${it.level || 'info'}">${(it.level||'info').toUpperCase()}</span>
            <strong>${it.symbol}</strong>
          </span>
          <span style="font-size:10px;color:var(--text-dim)">${it.type || ""}</span>
        </div>
        <div class="alert-msg">${it.msg || "-"}</div>
        <div class="alert-time">${fmtTime(it.t)}</div>
      </div>
    `).join("");
  } catch (e) {
    grid.innerHTML = '<div class="loading" style="color:var(--red)">로드 실패</div>';
  }
}

// ============================================================
// 시스템 상태 탭
// ============================================================
let scoreDistChart = null;
async function loadStatus() {
  const grid = document.getElementById("statusGrid");
  grid.innerHTML = '<div class="loading">로딩 중...</div>';
  try {
    const r = await fetch("/api/status");
    const j = await r.json();

    grid.innerHTML = `
      <div class="status-box"><div class="label">로드 종목</div><div class="value">${fmtInt(j.loaded || 0)}</div></div>
      <div class="status-box"><div class="label">WS 연결</div><div class="value" style="color:${j.ws_connected?'var(--green)':'var(--red)'}">${j.ws_connected?"ON":"OFF"}</div></div>
      <div class="status-box"><div class="label">WS 클라이언트</div><div class="value">${fmtInt(j.ws_clients || 0)}</div></div>
      <div class="status-box"><div class="label">대기 업데이트</div><div class="value">${fmtInt(j.dirty || 0)}</div></div>
      <div class="status-box"><div class="label">이상거래</div><div class="value">${fmtInt(j.anomalies || 0)}</div></div>
      <div class="status-box"><div class="label">활성 알림</div><div class="value">${fmtInt(j.alerts || 0)}</div></div>
    `;

    // 데이터 커버리지
    const cov = j.coverage || {};
    const total = j.loaded || 1;
    const covTable = document.getElementById("coverageTable");
    const rows = Object.keys(cov).map(k => {
      const n = cov[k] || 0;
      const pct = (n / total * 100).toFixed(1);
      const cls = pct < 30 ? "low" : (pct < 60 ? "mid" : "");
      return `
        <tr>
          <td style="padding:6px 8px;width:30%">${k}</td>
          <td style="padding:6px 8px;width:15%">${fmtInt(n)}</td>
          <td style="padding:6px 8px;width:10%">${pct}%</td>
          <td style="padding:6px 8px"><div class="coverage-bar"><div class="coverage-bar-fill ${cls}" style="width:${pct}%"></div></div></td>
        </tr>`;
    }).join("");
    covTable.innerHTML = `<thead><tr><th>필드</th><th>채워진 종목</th><th>%</th><th>비율</th></tr></thead><tbody>${rows}</tbody>`;

    // 점수 분포 차트
    drawScoreDist(j.score_distribution || {});
  } catch (e) {
    grid.innerHTML = '<div class="loading" style="color:var(--red)">로드 실패</div>';
  }
}

function drawScoreDist(dist) {
  const ctx = document.getElementById("scoreDistChart");
  if (!ctx) return;
  if (scoreDistChart) { scoreDistChart.destroy(); scoreDistChart = null; }
  const labels = Object.keys(dist);
  const data = Object.values(dist);
  scoreDistChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "종목 수",
        data,
        backgroundColor: ["#8a93a8", "#feca57", "#ff9f43", "#ff5470", "#a55eea"]
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { color: "#8a93a8" }, grid: { color: "rgba(138,147,168,0.15)" } },
        x: { ticks: { color: "#8a93a8" }, grid: { display: false } }
      }
    }
  });
}

// ============================================================
// 상세 모달
// ============================================================
async function showDetail(sym) {
  const modal = document.getElementById("detailModal");
  const body = document.getElementById("detailBody");
  body.innerHTML = `<div class="loading">불러오는 중... <strong>${sym}</strong></div>`;
  modal.classList.add("show");
  document.body.style.overflow = "hidden";

  try {
    const [bdR, optR, fundR, newsR, histR] = await Promise.all([
      fetch(`/api/scores/${sym}/breakdown`).then(r => r.json()).catch(() => ({})),
      fetch(`/api/options/${sym}`).then(r => r.json()).catch(() => ({})),
      fetch(`/api/fundamentals/${sym}`).then(r => r.json()).catch(() => ({})),
      fetch(`/api/news/${sym}?limit=10`).then(r => r.json()).catch(() => ({})),
      fetch(`/api/scores/${sym}/history?limit=100`).then(r => r.json()).catch(() => ({}))
    ]);
    renderDetail(sym, bdR, optR, fundR, newsR, histR);
  } catch (e) {
    body.innerHTML = `<div class="loading" style="color:var(--red)">상세 로드 실패: ${e.message}</div>`;
  }
}

function closeDetail() {
  const modal = document.getElementById("detailModal");
  modal.classList.remove("show");
  document.body.style.overflow = "";
  if (detailCharts.history) { detailCharts.history.destroy(); detailCharts.history = null; }
  if (detailCharts.breakdown) { detailCharts.breakdown.destroy(); detailCharts.breakdown = null; }
}

function renderDetail(sym, bd, opt, fund, news, hist) {
  const body = document.getElementById("detailBody");
  const m = bd.metrics || {};
  const score = bd.sqs_score ?? m.sqs_score ?? 0;
  const grade = bd.grade || m.grade || "NORMAL";

  let warnings = "";
  if (opt && opt.warning) warnings += `<div class="warning-banner">⚠️ ${opt.warning}</div>`;
  if (fund && fund.warnings && fund.warnings.length) {
    fund.warnings.forEach(w => warnings += `<div class="warning-banner">⚠️ ${w}</div>`);
  }

  body.innerHTML = `
    <h2>${sym} <span class="grade g-${grade}" style="font-size:13px;vertical-align:middle">${grade}</span></h2>
    <div class="subtitle">${m.name || ""} · ${m.theme || ""}</div>
    ${warnings}

    <div class="modal-section">
      <h3>핵심 지표</h3>
      <div class="metric-grid">
        <div class="metric-item"><div class="lbl">SQS 점수</div><div class="val ${scoreClass(score)}">${fmtNum(score, 1)}</div></div>
        <div class="metric-item"><div class="lbl">가격</div><div class="val">$${fmtNum(m.price)}</div></div>
        <div class="metric-item"><div class="lbl">변동률</div><div class="val ${pctClass(m.change_pct)}">${fmtPct(m.change_pct)}</div></div>
        <div class="metric-item"><div class="lbl">거래량</div><div class="val">${fmtVol(m.volume)}</div></div>
        <div class="metric-item"><div class="lbl">시가총액</div><div class="val">${fmtMcap(m.market_cap)}</div></div>
        <div class="metric-item"><div class="lbl">SI %</div><div class="val">${fmtPct((m.si_pct || 0) * 100, 2)}</div></div>
        <div class="metric-item"><div class="lbl">CTB %</div><div class="val">${fmtPct(m.ctb, 2)}</div></div>
        <div class="metric-item"><div class="lbl">RSI(14)</div><div class="val">${fmtNum(m.rsi14, 1)}</div></div>
        <div class="metric-item"><div class="lbl">MACD Hist</div><div class="val">${fmtNum(m.macd_histogram, 3)}</div></div>
        <div class="metric-item"><div class="lbl">누적점수</div><div class="val ${scoreClass(m.acc_score || 0)}">${fmtNum(m.acc_score, 1)}</div></div>
        <div class="metric-item"><div class="lbl">다크풀 비율</div><div class="val">${fmtPct((m.dark_pool_ratio || 0) * 100, 1)}</div></div>
        <div class="metric-item"><div class="lbl">유동주식</div><div class="val">${fmtVol(m.float_shares)}</div></div>
      </div>
    </div>

    ${hist && hist.history && hist.history.length ? `
      <div class="modal-section">
        <h3>점수 히스토리</h3>
        <canvas id="histChart" height="80"></canvas>
      </div>
    ` : ""}

    ${bd && bd.breakdown ? `
      <div class="modal-section">
        <h3>점수 구성</h3>
        <canvas id="bdChart" height="80"></canvas>
      </div>
    ` : ""}

    ${opt && opt.contract_count ? `
      <div class="modal-section">
        <h3>옵션 체인</h3>
        <div class="metric-grid">
          <div class="metric-item"><div class="lbl">감마 집중도</div><div class="val">${fmtPct((opt.gamma_concentration || 0) * 100, 1)}</div></div>
          <div class="metric-item"><div class="lbl">C/P 비율</div><div class="val">${fmtNum(opt.call_put_ratio, 2)}</div></div>
          <div class="metric-item"><div class="lbl">특이옵션</div><div class="val">${fmtNum(opt.unusual_options_score, 1)}</div></div>
          <div class="metric-item"><div class="lbl">맥스페인</div><div class="val">$${fmtNum(opt.max_pain)}</div></div>
          <div class="metric-item"><div class="lbl">콜 OI</div><div class="val">${fmtVol(opt.total_call_oi)}</div></div>
          <div class="metric-item"><div class="lbl">풋 OI</div><div class="val">${fmtVol(opt.total_put_oi)}</div></div>
          <div class="metric-item"><div class="lbl">콜 거래량</div><div class="val">${fmtVol(opt.total_call_volume)}</div></div>
          <div class="metric-item"><div class="lbl">풋 거래량</div><div class="val">${fmtVol(opt.total_put_volume)}</div></div>
          <div class="metric-item"><div class="lbl">평균 IV</div><div class="val">${fmtPct((opt.avg_iv || 0) * 100, 1)}</div></div>
          <div class="metric-item"><div class="lbl">컨트랙트</div><div class="val">${fmtInt(opt.contract_count)}</div></div>
        </div>
      </div>
    ` : ""}

    ${fund && (fund.debt_to_equity !== undefined || fund.cash_runway_months !== undefined) ? `
      <div class="modal-section">
        <h3>펀더멘털</h3>
        <div class="metric-grid">
          <div class="metric-item"><div class="lbl">부채/자본</div><div class="val">${fmtNum(fund.debt_to_equity, 2)}</div></div>
          <div class="metric-item"><div class="lbl">현금 런웨이</div><div class="val">${fmtNum(fund.cash_runway_months, 1)}개월</div></div>
          <div class="metric-item"><div class="lbl">매출 성장 YoY</div><div class="val ${pctClass(fund.revenue_growth_yoy)}">${fmtPct(fund.revenue_growth_yoy)}</div></div>
          <div class="metric-item"><div class="lbl">시가총액</div><div class="val">${fmtMcap(fund.market_cap)}</div></div>
        </div>
      </div>
    ` : ""}

    ${news && news.items && news.items.length ? `
      <div class="modal-section">
        <h3>뉴스 (${news.items.length})</h3>
        <div style="display:flex;flex-direction:column;gap:6px">
          ${news.items.slice(0, 10).map(n => `
            <a href="${n.url || '#'}" target="_blank" rel="noopener" style="font-size:12px;padding:6px;background:var(--bg2);border-radius:4px;display:block">
              <div style="font-weight:600">${(n.title || "").substring(0, 100)}</div>
              <div style="color:var(--text-dim);font-size:10px;margin-top:2px">
                ${n.publisher || ""} · ${fmtDate(n.published_utc || n.t)}
                ${n.catalyst ? '<span style="color:var(--orange);margin-left:6px">⚡촉매</span>' : ""}
              </div>
            </a>
          `).join("")}
        </div>
      </div>
    ` : ""}
  `;

  // 차트 렌더
  if (hist && hist.history && hist.history.length) {
    setTimeout(() => drawScoreHistory(hist.history), 50);
  }
  if (bd && bd.breakdown) {
    setTimeout(() => drawBreakdown(bd.breakdown), 50);
  }
}

function drawScoreHistory(hist) {
  const ctx = document.getElementById("histChart");
  if (!ctx) return;
  if (detailCharts.history) detailCharts.history.destroy();
  const labels = hist.map(h => {
    const d = new Date((h.t || 0) * 1000);
    return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
  });
  const data = hist.map(h => h.score);
  detailCharts.history = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "SQS",
        data,
        borderColor: "#4a9eff",
        backgroundColor: "rgba(74,158,255,0.15)",
        fill: true,
        tension: 0.3,
        pointRadius: 0
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { color: "#8a93a8" }, grid: { color: "rgba(138,147,168,0.15)" } },
        x: { ticks: { color: "#8a93a8", maxRotation: 0, autoSkipPadding: 20 }, grid: { display: false } }
      }
    }
  });
}

function drawBreakdown(bd) {
  const ctx = document.getElementById("bdChart");
  if (!ctx) return;
  if (detailCharts.breakdown) detailCharts.breakdown.destroy();
  const labels = Object.keys(bd);
  const data = Object.values(bd).map(v => Number(v) || 0);
  detailCharts.breakdown = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "점수",
        data,
        backgroundColor: "#4a9eff"
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8a93a8" }, grid: { color: "rgba(138,147,168,0.15)" } },
        y: { ticks: { color: "#8a93a8" }, grid: { display: false } }
      }
    }
  });
}

// ============================================================
// 초기화
// ============================================================
async function init() {
  bindTabs();
  bindSort();
  bindFilterInputs();
  await preloadSnapshot();
  await loadMarket();
  conn();
  setInterval(chkLoad, 5000);
  setInterval(loadMarket, 60000);
  // 5분마다 스냅샷 재요청 (WS 미연결 시 폴백)
  setInterval(async () => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      await preloadSnapshot();
    }
  }, 300000);
}

// ESC 키로 모달 닫기
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeDetail();
});

window.addEventListener("DOMContentLoaded", init);
</script>

</body>
</html>
"""
