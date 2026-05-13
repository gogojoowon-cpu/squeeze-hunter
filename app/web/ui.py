"""HTML UI 템플릿 - 숏 스퀴즈 헌터 v3"""

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔥 숏 스퀴즈 헌터 v3</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;900&family=Space+Mono:wght@400;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#04040c;--sf:#0c0c1a;--sf2:#111122;--bd:#181830;--ac:#00ff9d;--tx:#dde0f0;--mu:#3a3a58}
body{background:var(--bg);color:var(--tx);font-family:'Noto Sans KR',sans-serif;min-height:100vh}
header{background:rgba(12,12,26,.96);border-bottom:1px solid var(--bd);padding:10px 18px;position:sticky;top:0;z-index:200;backdrop-filter:blur(12px)}
.hdr{max-width:1600px;margin:0 auto;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.logo{font-family:'Space Mono',monospace;font-size:.9rem;font-weight:700;color:var(--ac)}
.logo b{color:#fff;font-style:normal}
.ver{font-size:.55rem;color:var(--mu);border:1px solid var(--bd);padding:1px 5px;border-radius:3px;font-family:'Space Mono',monospace}
nav{display:flex;gap:3px;flex-wrap:wrap}
nav button{background:none;border:1px solid transparent;color:var(--mu);cursor:pointer;font-size:.72rem;font-family:'Noto Sans KR',sans-serif;padding:4px 9px;border-radius:5px;transition:all .2s;font-weight:700}
nav button:hover,nav button.on{color:var(--ac);border-color:var(--ac);background:rgba(0,255,157,.06)}
.hdr-r{display:flex;align-items:center;gap:8px;margin-left:auto}
#mktBadge{font-size:.62rem;font-family:'Space Mono',monospace;padding:2px 7px;border-radius:10px;background:rgba(0,255,157,.08);border:1px solid rgba(0,255,157,.2);color:var(--ac);white-space:nowrap}
.live{display:flex;align-items:center;gap:4px;font-family:'Space Mono',monospace;font-size:.62rem}
.dot{width:7px;height:7px;border-radius:50%;background:var(--mu)}
.dot.on{background:var(--ac);animation:dp 2s infinite}
@keyframes dp{0%,100%{box-shadow:0 0 0 0 rgba(0,255,157,.5)}50%{box-shadow:0 0 0 5px rgba(0,255,157,0)}}
#banner{padding:6px 18px;text-align:center;font-size:.74rem;color:var(--ac);background:rgba(0,255,157,.05);border-bottom:1px solid rgba(0,255,157,.12);display:none}
.pg{display:none;max-width:1600px;margin:0 auto;padding:14px 16px}
.pg.on{display:block}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:12px}
.sc{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:11px 13px}
.sl{font-size:.6rem;color:var(--mu);margin-bottom:2px;font-weight:700;text-transform:uppercase}
.sv{font-family:'Space Mono',monospace;font-size:1.3rem;font-weight:700}
.theme-wrap{margin-bottom:10px}
.ttabs{display:flex;gap:5px;overflow-x:auto;padding-bottom:6px;scrollbar-width:thin}
.ttabs::-webkit-scrollbar{height:3px}
.ttabs::-webkit-scrollbar-thumb{background:var(--bd);border-radius:2px}
.ttab{background:var(--sf);border:1px solid var(--bd);color:var(--mu);padding:5px 11px;border-radius:18px;cursor:pointer;font-size:.72rem;font-weight:700;white-space:nowrap;transition:all .2s;font-family:'Noto Sans KR',sans-serif;flex-shrink:0}
.ttab:hover{border-color:var(--ac);color:var(--ac)}
.ttab.on{color:#000;font-weight:900}
.theme-select{display:none;width:100%;background:var(--sf);border:1px solid var(--bd);color:var(--tx);padding:8px 12px;border-radius:8px;font-size:.78rem;font-family:'Noto Sans KR',sans-serif;outline:none;margin-bottom:8px}
.theme-select:focus{border-color:var(--ac)}
@media(max-width:640px){
  .ttabs{display:none}
  .theme-select{display:block}
}
#themeInfo{background:var(--sf);border:1px solid var(--bd);border-radius:7px;padding:8px 12px;margin-bottom:9px;font-size:.78rem;display:none}
.lay{display:grid;grid-template-columns:1fr 230px;gap:12px;align-items:start}
@media(max-width:800px){.lay{grid-template-columns:1fr}}
.fltrs{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:9px;align-items:center}
.fb{background:var(--sf);border:1px solid var(--bd);color:var(--mu);padding:4px 11px;border-radius:16px;cursor:pointer;font-size:.72rem;font-weight:700;transition:all .2s;font-family:'Noto Sans KR',sans-serif}
.fb:hover{border-color:var(--ac);color:var(--ac)}
.fb.on{color:#000;background:var(--ac);border-color:var(--ac)}
.srch{margin-left:auto;background:var(--sf);border:1px solid var(--bd);color:var(--tx);padding:4px 11px;border-radius:16px;font-size:.72rem;outline:none;font-family:'Noto Sans KR',sans-serif;width:140px}
.srch:focus{border-color:var(--ac)}
.tw{background:var(--sf);border:1px solid var(--bd);border-radius:10px;overflow:hidden}
table{width:100%;border-collapse:collapse;font-size:.76rem}
th{padding:9px 10px;text-align:left;color:var(--mu);font-size:.6rem;font-weight:700;border-bottom:1px solid var(--bd);cursor:pointer;user-select:none;white-space:nowrap}
th:hover{color:var(--ac)}
td{padding:9px 10px;border-bottom:1px solid rgba(24,24,48,.7);vertical-align:middle;white-space:nowrap}
tr:last-child td{border:none}
tr{cursor:pointer;transition:background .1s}
tr:hover td{background:rgba(255,255,255,.018)}
tr.rI{animation:rp 2.5s ease-in-out infinite}
@keyframes rp{0%,100%{background:rgba(255,34,85,.04)}50%{background:rgba(255,34,85,.09)}}
.fu td{animation:fup .6s ease-out}
.fd td{animation:fdn .6s ease-out}
@keyframes fup{0%{background:rgba(0,255,157,.16)}100%{background:transparent}}
@keyframes fdn{0%{background:rgba(255,34,85,.16)}100%{background:transparent}}
.bdg{display:inline-flex;align-items:center;gap:2px;padding:2px 6px;border-radius:3px;font-size:.65rem;font-weight:700;white-space:nowrap}
.bI{background:rgba(255,34,85,.18);color:#ff2255;border:1px solid rgba(255,34,85,.4)}
.bH{background:rgba(255,136,0,.18);color:#ff8800;border:1px solid rgba(255,136,0,.4)}
.bW{background:rgba(255,208,0,.14);color:#ffd000;border:1px solid rgba(255,208,0,.35)}
.bL{background:rgba(102,102,187,.14);color:#8888dd;border:1px solid rgba(102,102,187,.3)}
.bN{background:rgba(34,34,68,.2);color:#3a3a58;border:1px solid rgba(34,34,68,.3)}
.dsrc{display:inline-block;padding:1px 4px;border-radius:2px;font-size:.56rem;font-weight:700}
.real{background:rgba(0,255,157,.15);color:var(--ac);border:1px solid rgba(0,255,157,.3)}
.est{background:rgba(255,208,0,.12);color:#ffd000;border:1px solid rgba(255,208,0,.3)}
.demo{background:rgba(58,58,88,.3);color:var(--mu);border:1px solid var(--bd)}
.ttag{display:inline-block;padding:1px 5px;border-radius:2px;font-size:.58rem;font-weight:700}
.sbw{display:flex;align-items:center;gap:6px}
.sn{font-family:'Space Mono',monospace;font-weight:700;font-size:.85rem;min-width:33px}
.sb{width:55px;height:3px;background:var(--bd);border-radius:2px;overflow:hidden;flex-shrink:0}
.sbf{height:100%;border-radius:2px;transition:width .4s}
.sym{font-family:'Space Mono',monospace;font-weight:700;color:var(--ac);font-size:.78rem}
.sdb{display:flex;flex-direction:column;gap:10px}
.card{background:var(--sf);border:1px solid var(--bd);border-radius:9px;padding:13px}
.ct{font-size:.6rem;color:var(--mu);text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px;font-weight:700}
.hb{display:flex;align-items:flex-end;gap:1px;height:60px}
.hbi{flex:1;border-radius:1px 1px 0 0;transition:height .4s;min-width:2px}
.hl{display:flex;justify-content:space-between;margin-top:3px}
.hl span{font-size:.54rem;color:var(--mu)}
.gr{display:flex;align-items:center;gap:6px;margin-bottom:5px}
.gr:last-child{margin:0}
.gd{font-size:.66rem;color:var(--mu)}
.dh{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px;align-items:flex-start}
.dsym{font-family:'Space Mono',monospace;font-size:2rem;font-weight:700;color:var(--ac)}
.dname{color:var(--mu);font-size:.8rem;margin-top:2px}
.dscore{font-family:'Space Mono',monospace;font-size:2.8rem;font-weight:700;line-height:1}
.mg{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:13px}
.mc{background:var(--sf);border:1px solid var(--bd);border-radius:7px;padding:10px}
.ml{font-size:.6rem;color:var(--mu);margin-bottom:2px;font-weight:600}
.mv{font-family:'Space Mono',monospace;font-size:1rem;font-weight:700}
.mbar{height:3px;background:var(--bd);border-radius:2px;margin-top:6px;overflow:hidden}
.mbf{height:100%;border-radius:2px}
.cw{position:relative;height:175px}
.ar{display:flex;align-items:center;gap:8px;padding:11px 14px;border-bottom:1px solid rgba(24,24,48,.6)}
.ar:last-child{border:none}
.am{flex:1;font-size:.76rem;color:var(--mu)}
.at{font-size:.62rem;color:var(--bd);white-space:nowrap}
.tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:11px;margin-top:12px}
.tcard{background:var(--sf);border:1px solid var(--bd);border-radius:9px;padding:13px;cursor:pointer;transition:all .18s}
.tcard:hover{border-color:var(--ac);transform:translateY(-1px)}
.fix-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;margin-top:12px}
.fix-card{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:12px}
.fix-num{font-family:'Space Mono',monospace;font-size:.65rem;color:var(--mu);margin-bottom:4px}
.fix-title{font-size:.82rem;font-weight:700;margin-bottom:3px}
.fix-desc{font-size:.72rem;color:var(--mu);line-height:1.5}
.mt2{width:100%;border-collapse:collapse;font-size:.76rem}
.mt2 th{padding:8px 12px;text-align:left;color:var(--mu);border-bottom:1px solid var(--bd);font-size:.6rem;text-transform:uppercase}
.mt2 td{padding:8px 12px;border-bottom:1px solid rgba(24,24,48,.5)}
.mt2 tr:hover td{background:rgba(255,255,255,.018)}
@media(max-width:560px){
  table thead{display:none}table,tbody,tr,td{display:block;width:100%}
  tr{padding:10px 12px;border-bottom:1px solid var(--bd)}
  td{padding:2px 0;border:none;font-size:.74rem}
  td::before{content:attr(data-label)" ";color:var(--mu);font-size:.6rem}
  .sb{display:none}.tgrid{grid-template-columns:1fr}.fix-grid{grid-template-columns:1fr}
}
.back{background:none;border:1px solid var(--bd);color:var(--ac);padding:5px 12px;border-radius:5px;cursor:pointer;font-family:'Noto Sans KR',sans-serif;font-size:.72rem;margin-bottom:15px;transition:all .2s}
.back:hover{background:var(--ac);color:#000}
.empty{text-align:center;padding:40px;color:var(--mu);font-size:.8rem}
.pgi{font-size:.65rem;color:var(--mu);margin-bottom:5px;display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.pgb{background:var(--sf);border:1px solid var(--bd);color:var(--ac);padding:2px 7px;border-radius:3px;cursor:pointer;font-size:.65rem;font-family:'Noto Sans KR',sans-serif}
footer{text-align:center;padding:16px;font-size:.63rem;color:#1a1a30;border-top:1px solid var(--bd);margin-top:22px}
.dp{color:#00ff9d;font-family:'Space Mono',monospace;font-size:.65rem}
.dn{color:#ff2255;font-family:'Space Mono',monospace;font-size:.65rem}
</style>
</head>
<body>
<header>
  <div class="hdr">
    <div class="logo">🔥 숏스퀴즈 <b>헌터</b> <span class="ver">v3</span></div>
    <nav>
      <button class="on" onclick="pg('dashboard')">📊 대시보드</button>
      <button onclick="pg('themes')">🗂️ 테마</button>
      <button onclick="pg('fixes')">🔧 개선사항</button>
      <button onclick="pg('accumulation')">🎯 매집신호</button>
      <button onclick="pg('alerts')">🔔 알림</button>
      <button onclick="pg('methodology')">📐 방법론</button>
    </nav>
    <div class="hdr-r">
      <div id="mktBadge">로딩중...</div>
      <div class="live">
        <span class="dot" id="dot"></span>
        <span id="ltxt" style="color:var(--mu)">연결중</span>
      </div>
    </div>
  </div>
</header>
<div id="banner"></div>

<div class="pg on" id="pg-dashboard">
  <div class="stats" id="statsG"></div>
  <div class="theme-wrap">
    <div class="ttabs" id="ttabs"></div>
    <select class="theme-select" id="themeSelect" onchange="setThemeFromSelect(this.value)">
      <option value="">전체 종목</option>
    </select>
  </div>
  <div id="themeInfo"></div>
  <div class="lay">
    <div>
      <div class="fltrs">
        <button class="fb on" onclick="gf('ALL',this)">전체</button>
        <button class="fb" onclick="gf('IMMINENT',this)">🔥 임박</button>
        <button class="fb" onclick="gf('HIGH',this)">⚡ 높음</button>
        <button class="fb" onclick="gf('WATCH',this)">👀 주시</button>
        <button class="fb" onclick="gf('LOW',this)">💤 낮음</button>
        <input class="srch" id="srch" placeholder="🔍 심볼 검색..." oninput="rt()">
      </div>
      <div class="pgi" id="pgi"></div>
      <div class="tw">
        <table>
          <thead><tr>
            <th onclick="sb('symbol')">심볼 ⇅</th>
            <th onclick="sb('score')">SQS ⇅</th>
            <th>등급</th>
            <th onclick="sb('price')">현재가 ⇅</th>
            <th>등락</th>
            <th onclick="sb('si_pct')">공매도% ⇅</th>
            <th onclick="sb('ctb')">CTB% ⇅</th>
            <th onclick="sb('util')">활용률 ⇅</th>
            <th onclick="sb('dtc')">청산일 ⇅</th>
            <th onclick="sb('rsi14')">RSI ⇅</th>
            <th onclick="sb('volume')">거래량 ⇅</th>
            <th>테마</th>
          </tr></thead>
          <tbody id="tbody"></tbody>
        </table>
        <div class="empty" id="emp" style="display:none">조건에 맞는 종목이 없습니다.</div>
      </div>
    </div>
    <div class="sdb">
      <div class="card">
        <div class="ct">점수 분포</div>
        <div class="hb" id="histB"></div>
        <div class="hl"><span>0</span><span>50</span><span>100</span></div>
      </div>
      <div class="card">
        <div class="ct">등급 기준</div>
        <div class="gr"><span class="bdg bI">🔥 임박</span><span class="gd">85↑ 스퀴즈 임박</span></div>
        <div class="gr"><span class="bdg bH">⚡ 높음</span><span class="gd">70~84 위험 높음</span></div>
        <div class="gr"><span class="bdg bW">👀 주시</span><span class="gd">55~69 모니터링</span></div>
        <div class="gr"><span class="bdg bL">💤 낮음</span><span class="gd">40~54 낮음</span></div>
        <div class="gr"><span class="bdg bN">❌ 없음</span><span class="gd">40↓ 신호없음</span></div>
      </div>
      <div class="card">
        <div class="ct">시스템</div>
        <div id="lastT" style="font-family:'Space Mono',monospace;font-size:.76rem;color:var(--ac)">—</div>
        <div id="statInfo" style="font-size:.63rem;color:var(--mu);margin-top:5px;line-height:1.7"></div>
      </div>
    </div>
  </div>
</div>

<div class="pg" id="pg-themes">
  <h2 style="font-size:.95rem;color:var(--mu);margin-bottom:4px">🗂️ 테마별 종목 분류</h2>
  <p style="font-size:.72rem;color:var(--mu);margin-bottom:2px">카드 클릭 → 해당 테마 종목만 필터링</p>
  <div class="tgrid" id="tgrid"></div>
</div>

<div class="pg" id="pg-fixes">
  <h2 style="font-size:.95rem;color:var(--ac);margin-bottom:6px">🔧 v3 개선사항</h2>
  <p style="font-size:.74rem;color:var(--mu);margin-bottom:12px">모듈화 + 동적 티커 수집 + Wyckoff 매집신호</p>
  <div class="fix-grid">
    <div class="fix-card"><div class="fix-num">v3-1</div><div class="fix-title" style="color:var(--ac)">모듈 분리</div><div class="fix-desc">단일 파일 → app/ 패키지 분리<br>config / providers / pipeline / api / web</div></div>
    <div class="fix-card"><div class="fix-num">v3-2</div><div class="fix-title" style="color:var(--ac)">동적 티커 수집</div><div class="fix-desc">하드코딩 660개 → Polygon API<br>NASDAQ+NYSE 6500+ 종목</div></div>
    <div class="fix-card"><div class="fix-num">v3-3</div><div class="fix-title" style="color:#ff4444">Wyckoff 매집신호</div><div class="fix-desc">OBV + CMF + Spring + 매집캔들<br>월스트리트 다중지표 검증</div></div>
    <div class="fix-card"><div class="fix-num">Fix 1</div><div class="fix-title" style="color:#ff2255">SI% 비선형 스케일</div><div class="fix-desc">30% 초과분 보너스 최대 5점<br>최대 25점 (GME 2021 정확 반영)</div></div>
    <div class="fix-card"><div class="fix-num">Fix 2</div><div class="fix-title" style="color:#ff8800">RSI 과매수 패널티</div><div class="fix-desc">RSI 70↑ = -2점 (이미 끝난 신호)<br>RSI 30~50 = +3점 (최적 구간)</div></div>
    <div class="fix-card"><div class="fix-num">Fix 3</div><div class="fix-title" style="color:#a855f7">소셜 속도 로그 스케일</div><div class="fix-desc">로그 스케일로 500~5000% 차별화</div></div>
    <div class="fix-card"><div class="fix-num">Fix 4</div><div class="fix-title" style="color:#3b82f6">CTB 추정식 개선</div><div class="fix-desc">SI×1.8 + DTC×3.2 (다변수)</div></div>
    <div class="fix-card"><div class="fix-num">Fix 5</div><div class="fix-title" style="color:#00ff9d">상장폐지 종목 제거</div><div class="fix-desc">BBBY, SIVB, FRC, SI 등 자동 제외</div></div>
    <div class="fix-card"><div class="fix-num">Fix 6</div><div class="fix-title" style="color:#eab308">알림 중복 방지</div><div class="fix-desc">종목당 30분 쿨다운</div></div>
    <div class="fix-card"><div class="fix-num">Fix 7</div><div class="fix-title" style="color:#06b6d4">장중 여부 체크</div><div class="fix-desc">ET 9:30~16:00 장중에만 갱신</div></div>
    <div class="fix-card"><div class="fix-num">Fix 8</div><div class="fix-title" style="color:#10b981">히스토리 8시간치</div><div class="fix-desc">1000개 = 약 8시간치</div></div>
    <div class="fix-card"><div class="fix-num">Fix 9</div><div class="fix-title" style="color:#f43f5e">새로고침 빈화면 방지</div><div class="fix-desc">/api/snapshot REST fallback</div></div>
    <div class="fix-card"><div class="fix-num">Fix 10</div><div class="fix-title" style="color:#8b5cf6">모바일 드롭다운</div><div class="fix-desc">640px 이하 자동 드롭다운</div></div>
  </div>
</div>

<div class="pg" id="pg-detail">
  <button class="back" onclick="pg('dashboard')">← 대시보드로</button>
  <div id="detC"></div>
</div>

<div class="pg" id="pg-accumulation">
  <h2 style="margin-bottom:6px;color:#ff4444;font-family:'Space Mono',monospace">🎯 매집 신호 (Wyckoff + OBV + CMF)</h2>
  <p style="font-size:.76rem;color:var(--mu);margin-bottom:12px;line-height:1.7">
    월스트리트 <b style="color:#ffd000">Wyckoff 매집 단계</b> + <b style="color:var(--ac)">OBV(누적거래량)</b> + <b style="color:#ff8800">CMF(자금흐름)</b> 다중 검증<br>
    <span style="color:#ff2255">🔥 STRONG (75↑)</span> · <span style="color:#ff8800">⚡ ACTIVE (60~74)</span> · <span style="color:#ffd000">👀 EMERGING (45~59)</span>
  </p>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:14px" id="accStats"></div>
  <div class="tw">
    <table>
      <thead><tr>
        <th>심볼</th>
        <th>매집점수</th>
        <th>매집 시그널</th>
        <th>OBV 추세</th>
        <th>CMF</th>
        <th>거래량 폭증일</th>
        <th>등락</th>
        <th>현재가</th>
        <th>테마</th>
      </tr></thead>
      <tbody id="accBody"></tbody>
    </table>
    <div class="empty" id="accEmp" style="display:none">매집 신호 종목 없음 (데이터 로딩 중...)</div>
  </div>
</div>

<div class="pg" id="pg-alerts">
  <h2 style="margin-bottom:13px;font-size:.9rem;color:var(--mu)">🔔 등급 변동 알림 <span style="font-size:.7rem;color:var(--mu)">(30분 쿨다운 적용)</span></h2>
  <div class="tw" id="aList"></div>
</div>

<div class="pg" id="pg-methodology">
  <h2 style="margin-bottom:7px;color:var(--ac);font-family:'Space Mono',monospace">SQS v3 방법론</h2>
  <p style="color:var(--mu);font-size:.78rem;margin-bottom:16px;line-height:1.7">
    SQS(Squeeze Score) v3는 Polygon API 기반 동적 데이터 + 10가지 개선 점수식으로<br>
    미국 전체 상장 종목 6500+개에 대해 30초마다 자동 갱신됩니다.
  </p>
  <div class="tw" style="margin-bottom:16px">
    <table class="mt2">
      <thead><tr><th>지표</th><th>가중치</th><th>산식</th><th>소스</th></tr></thead>
      <tbody>
        <tr><td>공매도 SI%</td><td style="color:var(--ac);font-family:'Space Mono',monospace">20+5</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">min(SI/30)×20 + bonus(SI>30)×5</td><td><span class="dsrc real">Polygon SI</span></td></tr>
        <tr><td>청산 소요일 DTC</td><td style="color:var(--ac);font-family:'Space Mono',monospace">10</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">min(DTC/10,1)×10</td><td><span class="dsrc real">Polygon SI</span></td></tr>
        <tr><td>차입 비용 CTB%</td><td style="color:var(--ac);font-family:'Space Mono',monospace">10</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">min(CTB/50,1)×10</td><td><span class="dsrc est">추정</span></td></tr>
        <tr><td>대여 활용률 Util%</td><td style="color:var(--ac);font-family:'Space Mono',monospace">5</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">min(Util/100,1)×5</td><td><span class="dsrc est">추정</span></td></tr>
        <tr><td>유통 주식수</td><td style="color:var(--ac);font-family:'Space Mono',monospace">10</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">clamp(1−log₁₀/8)×10</td><td><span class="dsrc real">Polygon Float</span></td></tr>
        <tr><td>플로트 회전율</td><td style="color:var(--ac);font-family:'Space Mono',monospace">8</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">min(Rot/2,1)×8</td><td><span class="dsrc real">Polygon</span></td></tr>
        <tr><td>거래량 급등</td><td style="color:var(--ac);font-family:'Space Mono',monospace">5</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">clamp((spike−1)/4)×5</td><td><span class="dsrc real">Polygon Aggs</span></td></tr>
        <tr><td>52주 고점 거리</td><td style="color:var(--ac);font-family:'Space Mono',monospace">5</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">dist×5</td><td><span class="dsrc real">Polygon Aggs</span></td></tr>
        <tr><td>RSI 다이버전스</td><td style="color:var(--ac);font-family:'Space Mono',monospace">3</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">30~50→+3 / 70↑→-2</td><td><span class="dsrc real">Polygon RSI</span></td></tr>
        <tr><td>MACD 모멘텀</td><td style="color:var(--ac);font-family:'Space Mono',monospace">5</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">골든크로스+5 / 데드크로스-3</td><td><span class="dsrc real">Polygon MACD</span></td></tr>
        <tr><td>매집 신호 (Wyckoff)</td><td style="color:#ff4444;font-family:'Space Mono',monospace">8</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">OBV+CMF+Spring+캔들 → 100점 × 0.08</td><td><span class="dsrc real">Polygon Aggs</span></td></tr>
        <tr><td>소셜 속도 24h</td><td style="color:var(--ac);font-family:'Space Mono',monospace">8</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">≤500 선형 / >500 로그</td><td><span class="dsrc real">Apewisdom</span></td></tr>
        <tr><td>투자자 심리</td><td style="color:var(--ac);font-family:'Space Mono',monospace">4</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">max(0,sent)×4</td><td><span class="dsrc real">Apewisdom</span></td></tr>
        <tr><td>카탈리스트 D−7</td><td style="color:var(--ac);font-family:'Space Mono',monospace">4</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">bool?4:0</td><td><span class="dsrc real">Polygon News</span></td></tr>
      </tbody>
    </table>
  </div>
  <h3 style="margin:20px 0 8px;color:#ff4444;font-family:'Space Mono',monospace;font-size:.9rem">🎯 매집 신호 세부 산식</h3>
  <div class="tw">
    <table class="mt2">
      <thead><tr><th>지표</th><th>가중치</th><th>산식</th><th>의미</th></tr></thead>
      <tbody>
        <tr><td>OBV 추세</td><td style="color:var(--ac)">25</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">20일 기울기 > 10% → +25</td><td>누적 매집 거래량</td></tr>
        <tr><td>CMF (20일)</td><td style="color:var(--ac)">20</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">+0.15↑ → +20 / -0.1↓ → -5</td><td>자금흐름 강도</td></tr>
        <tr><td>거래량 폭증일</td><td style="color:var(--ac)">15</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">10일 중 평균2배 일수 ≥5 → +15</td><td>지속적 매집</td></tr>
        <tr><td>가격 안정+거래량</td><td style="color:var(--ac)">15</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">ATR<3% + 거래량↑ → +15</td><td>횡보 중 매집</td></tr>
        <tr><td>Wyckoff Spring</td><td style="color:var(--ac)">15</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">신저가 후 즉시 회복+거래량폭증</td><td>매집 막바지</td></tr>
        <tr><td>매집 캔들 비율</td><td style="color:var(--ac)">10</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">종가 상단60%+거래량↑ → 70%↑</td><td>세력 매수 의지</td></tr>
      </tbody>
    </table>
  </div>
  <p style="font-size:.65rem;color:#1a1a30;text-align:center;margin-top:16px">⚠️ 교육 목적 전용 | 투자 자문 아님</p>
</div>

<footer>⚠️ 교육 목적 전용 | 투자 자문 아님 | Not investment advice | v3 Wyckoff Edition</footer>

<script>
let all={}, sortK='score', sortD=true, gfil='ALL', themeFil='', detChart=null, curPage=1;
const PAGE=50;
const GE={IMMINENT:'🔥',HIGH:'⚡',WATCH:'👀',LOW:'💤',NO_SQUEEZE:'❌'};
const GK={IMMINENT:'임박',HIGH:'높음',WATCH:'주시',LOW:'낮음',NO_SQUEEZE:'없음'};
const BC={IMMINENT:'bI',HIGH:'bH',WATCH:'bW',LOW:'bL',NO_SQUEEZE:'bN'};
let TD=[];

async function preloadSnapshot(){
  try{
    const data=await fetch('/api/snapshot').then(r=>r.json());
    if(data&&data.length>0){
      data.forEach(d=>all[d.symbol]={...(all[d.symbol]||{}),...d});
      rt();rs();rh();
      console.log(`REST 스냅샷 로드: ${data.length}개`);
    }
  }catch(e){console.warn('스냅샷 로드 실패',e)}
}

function conn(){
  const p=location.protocol==='https:'?'wss':'ws';
  const ws=new WebSocket(`${p}://${location.host}/ws/scores`);
  ws.onopen=()=>live(true);
  ws.onclose=()=>{live(false);setTimeout(conn,3000)};
  ws.onerror=()=>ws.close();
  ws.onmessage=e=>{
    const m=JSON.parse(e.data);
    if(m.type==='snapshot'){
      m.data.forEach(d=>all[d.symbol]={...(all[d.symbol]||{}),...d});
      rt();rs();rh();loadThemes();
    } else if(m.type==='score_update'&&m.symbol){
      const s=m.symbol,pv=all[s]?.score||0;
      all[s]={...(all[s]||{}),...m};
      if(Math.abs(m.score-pv)>0.1) flash(s,m.score>pv);
      rt();rs();rh();
      document.getElementById('lastT').textContent=new Date().toLocaleTimeString('ko-KR');
    }
  };
}

function live(on){
  document.getElementById('dot').className='dot'+(on?' on':'');
  const el=document.getElementById('ltxt');
  el.textContent=on?'● 실시간':'○ 연결중';
  el.style.color=on?'var(--ac)':'var(--mu)';
}

function chkLoad(){
  fetch('/api/status').then(r=>r.json()).then(s=>{
    const b=document.getElementById('banner');
    b.style.display=s.ready?'none':'';
    if(!s.ready) b.textContent=`📡 로딩 중... (${s.loaded||0}/${s.total||0}개)`;
    document.getElementById('mktBadge').textContent=s.market||'로딩중...';
    document.getElementById('statInfo').innerHTML=
      `로드: <b style="color:var(--ac)">${s.loaded}</b>개<br>`+
      `소셜실제: <b style="color:var(--ac)">${s.real_social||0}</b>개<br>`+
      `상폐제외: <b style="color:#ff8800">${s.delisted||0}</b>개<br>`+
      `보강완료: <b style="color:${s.enrich_done?'var(--ac)':'#ffd000'}">${s.enrich_done?'예':'진행중'}</b>`;
  }).catch(()=>{});
}

async function loadThemes(){
  if(TD.length) return;
  TD=await fetch('/api/themes').then(r=>r.json()).catch(()=>[]);
  const tc={};TD.forEach(t=>tc[t.id]=t.color);
  document.getElementById('ttabs').innerHTML=
    `<button class="ttab on" style="border-color:var(--ac);color:var(--ac);background:rgba(0,255,157,.1)" onclick="setT('',this)">전체</button>`+
    TD.map(t=>`<button class="ttab" onclick="setT('${t.id}',this)" data-color="${t.color}">${t.id} <span style="color:var(--mu)">${t.count}</span></button>`).join('');
  const sel=document.getElementById('themeSelect');
  TD.forEach(t=>{ const o=document.createElement('option'); o.value=t.id; o.textContent=`${t.id} (${t.count}개)`; sel.appendChild(o); });
  document.getElementById('tgrid').innerHTML=TD.map(t=>`
    <div class="tcard" onclick="goTheme('${t.id}')" style="border-color:${t.color}22">
      <div style="color:${t.color};font-size:.9rem;font-weight:700;margin-bottom:3px">${t.id}</div>
      <div style="font-size:.68rem;color:var(--mu);margin-bottom:5px;line-height:1.4">📌 ${t.event}</div>
      <div style="font-size:.68rem;color:var(--mu);margin-bottom:6px">${t.desc}</div>
      <span style="font-family:'Space Mono',monospace;font-size:.7rem;color:${t.color}">${t.count}개 종목</span>
    </div>`).join('');
}

function setT(id,btn){
  themeFil=id; curPage=1;
  document.querySelectorAll('.ttab').forEach(b=>{b.classList.remove('on');b.style.background='';b.style.color='';b.style.borderColor='';});
  if(btn){
    btn.classList.add('on');
    const c=btn.dataset.color||'var(--ac)';
    btn.style.background=c+'22'; btn.style.color=c; btn.style.borderColor=c;
  }
  const ti=document.getElementById('themeInfo');
  if(id){ const t=TD.find(x=>x.id===id); if(t){ ti.style.display=''; ti.innerHTML=`<b style="color:${t.color}">${t.id}</b> — <span style="color:var(--mu)">📌 ${t.event}</span>`; } }
  else ti.style.display='none';
  rt();
}

function setThemeFromSelect(val){
  themeFil=val; curPage=1;
  const ti=document.getElementById('themeInfo');
  if(val){ const t=TD.find(x=>x.id===val); if(t){ ti.style.display=''; ti.innerHTML=`<b style="color:${t.color}">${t.id}</b> — <span style="color:var(--mu)">📌 ${t.event}</span>`; } }
  else ti.style.display='none';
  rt();
}

function goTheme(id){
  pg('dashboard');
  setTimeout(()=>{ const btn=document.querySelector(`.ttab[onclick*="'${id}'"]`); setT(id,btn); document.getElementById('themeSelect').value=id; },80);
}

function pg(n,sym){
  document.querySelectorAll('.pg').forEach(p=>p.classList.remove('on'));
  document.getElementById('pg-'+n).classList.add('on');
  const nm={dashboard:0,themes:1,fixes:2,accumulation:3,alerts:4,methodology:5};
  document.querySelectorAll('nav button').forEach((b,i)=>b.classList.toggle('on',i===nm[n]));
  if(n==='detail'&&sym) rd(sym);
  if(n==='alerts') ra();
  if(n==='accumulation') racc();
}

function gf(g,btn){ gfil=g; curPage=1; document.querySelectorAll('.fb').forEach(b=>b.classList.remove('on')); btn.classList.add('on'); rt(); }
function sb(k){ sortK===k?sortD=!sortD:(sortK=k,sortD=true); curPage=1; rt(); }

const f=(n,d=2)=>n==null?'—':Number(n).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
const fv=n=>!n?'—':n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(0)+'K':String(n);
const mc2=n=>!n?'—':n>=1e12?(n/1e12).toFixed(1)+'조':n>=1e8?(n/1e8).toFixed(0)+'억':'$'+Math.round(n);
const sc=s=>s>=85?'#ff2255':s>=70?'#ff8800':s>=55?'#ffd000':s>=40?'#8888dd':'#2a2a44';
const bdg=g=>`<span class="bdg ${BC[g]}">${GE[g]} ${GK[g]||g}</span>`;
const srcB=s=>s==='polygon'||s==='apewisdom'?'<span class="dsrc real">실제</span>':s==='estimated'?'<span class="dsrc est">추정</span>':'<span class="dsrc demo">데모</span>';

let _fil=[];
function rt(){
  const srch=(document.getElementById('srch')?.value||'').toUpperCase();
  _fil=Object.values(all);
  if(gfil!=='ALL') _fil=_fil.filter(r=>r.grade===gfil);
  if(themeFil) _fil=_fil.filter(r=>r.theme===themeFil);
  if(srch) _fil=_fil.filter(r=>r.symbol?.includes(srch)||(r.name||'').toUpperCase().includes(srch));
  _fil.sort((a,b)=>{const av=a[sortK]??0,bv=b[sortK]??0;
    return typeof av==='string'?sortD?bv.localeCompare(av):av.localeCompare(bv):sortD?bv-av:av-bv;});
  rp2();
}
function rp2(){
  const tb=document.getElementById('tbody'),em=document.getElementById('emp'),pi=document.getElementById('pgi');
  if(!_fil.length){ tb.innerHTML=''; em.style.display=''; pi.innerHTML=''; return; }
  em.style.display='none';
  const total=_fil.length, pages=Math.ceil(total/PAGE);
  if(curPage>pages) curPage=Math.max(1,pages);
  const start=(curPage-1)*PAGE, slice=_fil.slice(start,start+PAGE);
  pi.innerHTML=`<span>총 <b style="color:var(--ac)">${total}</b>개</span>
    <span style="color:var(--bd)">|</span><span>${start+1}~${Math.min(start+PAGE,total)}</span>
    ${pages>1?`<button class="pgb" onclick="curPage=Math.max(1,curPage-1);rp2()">◀</button>
    <span>${curPage}/${pages}페이지</span>
    <button class="pgb" onclick="curPage=Math.min(${pages},curPage+1);rp2()">▶</button>`:''}`;
  const tcolor={};TD.forEach(t=>tcolor[t.id]=t.color);
  tb.innerHTML=slice.map(r=>{
    const s=r.score||0,g=r.grade||'NO_SQUEEZE',ch=r.change_pct||0;
    const chH=ch>=0?`<span class="dp">▲${f(ch,2)}%</span>`:`<span class="dn">▼${f(Math.abs(ch),2)}%</span>`;
    const tc=tcolor[r.theme||'']||'#3a3a58';
    return`<tr class="${g==='IMMINENT'?'rI':''}" id="row-${r.symbol}" onclick="pg('detail','${r.symbol}')">
      <td data-label="심볼">
        <span class="sym">${r.symbol}</span>${r.has_catalyst?'<span style="color:#ffd000;font-size:.7rem" title="카탈리스트">⚡</span>':''}
        <div style="font-size:.58rem;color:var(--mu)">${r.name||''}</div>
      </td>
      <td data-label="SQS"><div class="sbw">
        <span class="sn" style="color:${sc(s)}">${f(s,1)}</span>
        <div class="sb"><div class="sbf" style="width:${s}%;background:${sc(s)}"></div></div>
      </div></td>
      <td data-label="등급">${bdg(g)}</td>
      <td data-label="현재가"><span style="font-family:'Space Mono',monospace">$${f(r.price)}</span></td>
      <td data-label="등락">${chH}</td>
      <td data-label="공매도%"><span style="font-family:'Space Mono',monospace;color:${(r.si_pct||0)>25?'#ff2255':(r.si_pct||0)>15?'#ff8800':'inherit'}">${f(r.si_pct,1)}%</span></td>
      <td data-label="CTB%"><span style="font-family:'Space Mono',monospace;color:${(r.ctb||0)>50?'#ff2255':(r.ctb||0)>20?'#ff8800':'inherit'}">${f(r.ctb,1)}%</span></td>
      <td data-label="활용률"><span style="font-family:'Space Mono',monospace;color:${(r.util||0)>80?'#ff8800':'inherit'}">${f(r.util,1)}%</span></td>
      <td data-label="청산일"><span style="font-family:'Space Mono',monospace">${f(r.dtc,1)}</span></td>
      <td data-label="RSI"><span style="font-family:'Space Mono',monospace;color:${(r.rsi14||50)<40?'var(--ac)':(r.rsi14||50)>70?'#ff8800':'inherit'}">${f(r.rsi14,1)}</span></td>
      <td data-label="거래량"><span style="font-family:'Space Mono',monospace">${fv(r.volume)}</span></td>
      <td data-label="테마"><span class="ttag" style="background:${tc}20;color:${tc};border:1px solid ${tc}40">${(r.theme||'기타').split(' ').slice(0,2).join(' ')}</span></td>
    </tr>`;
  }).join('');
}

function rs(){
  const rows=Object.values(all);
  const c={IMMINENT:0,HIGH:0,WATCH:0,LOW:0,NO_SQUEEZE:0};
  rows.forEach(r=>c[r.grade||'NO_SQUEEZE']=(c[r.grade||'NO_SQUEEZE']||0)+1);
  document.getElementById('statsG').innerHTML=`
    <div class="sc"><div class="sl">🔥 임박</div><div class="sv" style="color:#ff2255">${c.IMMINENT}</div></div>
    <div class="sc"><div class="sl">⚡ 높음</div><div class="sv" style="color:#ff8800">${c.HIGH}</div></div>
    <div class="sc"><div class="sl">👀 주시</div><div class="sv" style="color:#ffd000">${c.WATCH}</div></div>
    <div class="sc"><div class="sl">📊 전체</div><div class="sv" style="color:var(--ac)">${rows.length}</div></div>`;
}
function rh(){
  const bk=new Array(21).fill(0);
  Object.values(all).forEach(r=>{const i=Math.min(Math.floor((r.score||0)/5),20);bk[i]++;});
  const mx=Math.max(...bk,1);
  const cl=['#111120','#111120','#111120','#111120','#111120','#111120','#111120','#111120',
            '#5555aa','#5555aa','#7777cc','#ffd000','#ffd000','#ffd000','#ff8800','#ff8800',
            '#ff8800','#ff2255','#ff2255','#ff2255','#ff2255'];
  document.getElementById('histB').innerHTML=bk.map((c,i)=>
    `<div class="hbi" title="${i*5}~${i*5+4}점: ${c}개" style="height:${Math.max(2,(c/mx)*56)}px;background:${cl[i]}"></div>`
  ).join('');
}
function flash(sym,up){
  const r=document.getElementById('row-'+sym);
  if(!r)return; r.classList.remove('fu','fd'); void r.offsetWidth;
  r.classList.add(up?'fu':'fd'); setTimeout(()=>r.classList.remove('fu','fd'),650);
}

async function rd(sym){
  const st=all[sym];
  if(!st){ document.getElementById('detC').innerHTML='<p style="color:var(--mu)">데이터 없음</p>'; return; }
  const g=st.grade||'NO_SQUEEZE', s=st.score||0;
  const [bd,hi]=await Promise.all([
    fetch('/api/scores/'+sym+'/breakdown').then(r=>r.json()).catch(()=>({})),
    fetch('/api/scores/'+sym+'/history').then(r=>r.json()).catch(()=>[]),
  ]);
  const bdd=bd.breakdown||{}, hist=hi.slice(-80);
  const tcolor=TD.find(t=>t.id===st.theme)?.color||'#3a3a58';
  const keys=[
    {k:'si_score',l:'공매도 비율',max:25},{k:'dtc_score',l:'청산 소요일',max:10},
    {k:'ctb_score',l:'차입 비용',max:10},{k:'util_score',l:'대여 활용률',max:5},
    {k:'float_score',l:'유통 주식수',max:10},{k:'rotation_score',l:'플로트 회전율',max:8},
    {k:'vol_spike_score',l:'거래량 급등',max:5},{k:'dist_52w_score',l:'52주 고점',max:5},
    {k:'rsi_score',l:'RSI 다이버전스',max:3},{k:'macd_score',l:'MACD 모멘텀',max:5},
    {k:'social_score',l:'소셜 속도',max:8},{k:'sentiment_score',l:'투자자 심리',max:4},
    {k:'catalyst_score',l:'카탈리스트',max:4},{k:'accumulation_score',l:'매집 신호',max:8},
  ];
  document.getElementById('detC').innerHTML=`
    <div class="dh">
      <div>
        <div class="dsym">${sym}${st.has_catalyst?' <span style="font-size:1.1rem" title="카탈리스트 감지">⚡</span>':''}</div>
        <div class="dname">${st.name||''} · ${st.sector||'기타'}</div>
        <div style="margin-top:7px;display:flex;gap:5px;flex-wrap:wrap">
          ${bdg(g)}
          <span class="ttag" style="background:${tcolor}20;color:${tcolor};border:1px solid ${tcolor}40;padding:2px 7px;font-size:.65rem;border-radius:3px">${st.theme||'기타'}</span>
          ${st.has_catalyst?'<span class="ttag" style="background:rgba(255,208,0,.15);color:#ffd000;border:1px solid rgba(255,208,0,.3);padding:2px 7px;font-size:.65rem;border-radius:3px">⚡ 카탈리스트</span>':''}
          ${(st.acc_score||0)>=60?`<span class="ttag" style="background:rgba(255,68,68,.15);color:#ff4444;border:1px solid rgba(255,68,68,.3);padding:2px 7px;font-size:.65rem;border-radius:3px">🎯 매집신호 ${st.acc_score}</span>`:''}
        </div>
      </div>
      <div style="margin-left:auto;text-align:right">
        <div class="dscore" style="color:${sc(s)}">${f(s,1)}</div>
        <div style="font-size:.65rem;color:var(--mu);margin-top:2px">/ 100점</div>
      </div>
    </div>
    <div class="mg">
      <div class="mc"><div class="ml">현재가</div><div class="mv">$${f(st.price)}</div><div style="font-size:.58rem;color:var(--mu);margin-top:2px">${st.change_pct>=0?'▲':'▼'}${f(Math.abs(st.change_pct),2)}%</div></div>
      <div class="mc"><div class="ml">공매도 SI% ${srcB('polygon')}</div><div class="mv" style="color:#ff2255">${f(st.si_pct,1)}%</div><div style="font-size:.58rem;color:var(--mu);margin-top:2px">${(st.si_shares||0).toLocaleString()}주</div></div>
      <div class="mc"><div class="ml">CTB % ${srcB(st.ctb_src||'demo')}</div><div class="mv" style="color:${(st.ctb||0)>50?'#ff2255':(st.ctb||0)>20?'#ff8800':'inherit'}">${f(st.ctb,1)}%</div></div>
      <div class="mc"><div class="ml">활용률 Util</div><div class="mv" style="color:${(st.util||0)>80?'#ff8800':'inherit'}">${f(st.util,1)}%</div></div>
      <div class="mc"><div class="ml">청산 소요일 DTC</div><div class="mv">${f(st.dtc,1)}일</div></div>
      <div class="mc"><div class="ml">RSI(14)</div><div class="mv" style="color:${(st.rsi14||50)<40?'var(--ac)':(st.rsi14||50)>70?'#ff8800':'inherit'}">${f(st.rsi14,1)}</div></div>
      <div class="mc"><div class="ml">거래량 배수</div><div class="mv">${f(st.vol_spike,2)}x</div></div>
      <div class="mc"><div class="ml">소셜 속도 ${srcB(st.soc_src||'demo')}</div><div class="mv">${f(st.social_velocity,0)}</div><div style="font-size:.58rem;color:var(--mu);margin-top:2px">${(st.mentions||0).toLocaleString()} 멘션</div></div>
      <div class="mc"><div class="ml">거래량</div><div class="mv">${fv(st.volume)}</div></div>
      <div class="mc"><div class="ml">시가총액</div><div class="mv" style="font-size:.82rem">${mc2(st.market_cap)}</div></div>
      <div class="mc"><div class="ml">52주 고점</div><div class="mv">$${f(st.high_52w)}</div></div>
      <div class="mc"><div class="ml">52주 저점</div><div class="mv">$${f(st.low_52w)}</div></div>
    </div>
    ${hist.length>1?`<div class="card" style="margin-bottom:12px"><div class="ct">SQS 점수 히스토리 (최대 8시간)</div><div class="cw"><canvas id="hc"></canvas></div></div>`:''}
    <div class="card" style="margin-bottom:12px">
      <div class="ct">세부 점수 분석</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:7px;margin-top:5px">
        ${keys.map(({k,l,max})=>{const v=Number(bdd[k]||0),p2=Math.min((v/max)*100,100);
          const c=p2>=75?'var(--ac)':p2>=40?'#ffd000':'var(--mu)';
          return`<div class="mc"><div class="ml">${l}</div>
            <div class="mv" style="color:${c}">${f(v,1)}<span style="font-size:.55rem;color:var(--mu)">/${max}</span></div>
            <div class="mbar"><div class="mbf" style="width:${p2}%;background:${c}"></div></div></div>`;
        }).join('')}
      </div>
      ${(bdd.penalty||0)>0?`<div style="margin-top:9px;padding:8px 11px;background:rgba(255,34,85,.08);border:1px solid rgba(255,34,85,.25);border-radius:5px;font-size:.74rem;color:#ff6677">⚠️ 페널티: -${f(bdd.penalty,0)}점${st.has_dilution?' (희석 발행)':''}${(st.market_cap||0)<50e6?' (소형주)':''}</div>`:''}
    </div>`;
  if(hist.length>1){
    if(detChart){ detChart.destroy(); detChart=null; }
    const ctx=document.getElementById('hc').getContext('2d');
    detChart=new Chart(ctx,{type:'line',
      data:{labels:hist.map(h=>new Date(h.ts).toLocaleTimeString('ko-KR')),
            datasets:[{label:'SQS',data:hist.map(h=>h.score),
              borderColor:'#00ff9d',backgroundColor:'rgba(0,255,157,.05)',
              tension:.3,pointRadius:0,borderWidth:2,fill:true}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},
        scales:{x:{ticks:{color:'#3a3a58',maxTicksLimit:5},grid:{color:'rgba(24,24,48,.5)'}},
                y:{min:0,max:100,ticks:{color:'#3a3a58'},grid:{color:'rgba(24,24,48,.5)'}}}}});
  }
}

async function racc(){
  const data = await fetch('/api/accumulation?limit=100&min_score=40').then(r=>r.json()).catch(()=>[]);
  const tb = document.getElementById('accBody');
  const em = document.getElementById('accEmp');
  const st = document.getElementById('accStats');
  if(!data.length){ tb.innerHTML=''; em.style.display=''; return; }
  em.style.display='none';
  const tcolor={};TD.forEach(t=>tcolor[t.id]=t.color);
  
  const strong = data.filter(d=>d.acc_tier==='STRONG').length;
  const active = data.filter(d=>d.acc_tier==='ACTIVE').length;
  const emerging = data.filter(d=>d.acc_tier==='EMERGING').length;
  const avg_score = (data.reduce((a,r)=>a+(r.acc_score||0),0)/data.length).toFixed(1);
  
  st.innerHTML=`
    <div class="sc"><div class="sl">🔥 강력매집</div><div class="sv" style="color:#ff2255">${strong}</div></div>
    <div class="sc"><div class="sl">⚡ 활발매집</div><div class="sv" style="color:#ff8800">${active}</div></div>
    <div class="sc"><div class="sl">👀 신호발생</div><div class="sv" style="color:#ffd000">${emerging}</div></div>
    <div class="sc"><div class="sl">평균 점수</div><div class="sv" style="color:var(--ac)">${avg_score}</div></div>
  `;
  
  const tierColor={STRONG:'#ff2255',ACTIVE:'#ff8800',EMERGING:'#ffd000',WEAK:'#8888dd'};
  const tierKR={STRONG:'🔥강력',ACTIVE:'⚡활발',EMERGING:'👀신호',WEAK:'💤약'};
  
  tb.innerHTML = data.map(r=>{
    const tc = tcolor[r.theme||'']||'#3a3a58';
    const tier_c = tierColor[r.acc_tier]||'#8888dd';
    const chH = (r.change_pct||0)>=0
      ? `<span class="dp">▲${f(r.change_pct,2)}%</span>`
      : `<span class="dn">▼${f(Math.abs(r.change_pct),2)}%</span>`;
    return`<tr onclick="pg('detail','${r.symbol}')" style="cursor:pointer">
      <td><span class="sym">${r.symbol}</span><div style="font-size:.58rem;color:var(--mu)">${r.name||''}</div></td>
      <td>
        <span style="font-family:'Space Mono',monospace;color:${tier_c};font-weight:700;font-size:1rem">${f(r.acc_score,0)}</span>
        <div style="font-size:.58rem;color:${tier_c};font-weight:700">${tierKR[r.acc_tier]||''}</div>
      </td>
      <td style="font-size:.66rem;color:var(--mu);max-width:240px;white-space:normal;line-height:1.4">${r.acc_summary||'—'}</td>
      <td><span style="font-family:'Space Mono',monospace;color:${(r.obv_slope||0)>0.1?'var(--ac)':(r.obv_slope||0)>0?'#ffd000':'var(--mu)'}">${((r.obv_slope||0)*100).toFixed(1)}%</span></td>
      <td><span style="font-family:'Space Mono',monospace;color:${(r.cmf||0)>0.15?'var(--ac)':(r.cmf||0)>0?'#ffd000':'#ff8800'}">${f(r.cmf,2)}</span></td>
      <td><span style="font-family:'Space Mono',monospace;color:#ffd000">${r.vol_spike_days||0}일</span></td>
      <td>${chH}</td>
      <td><span style="font-family:'Space Mono',monospace">$${f(r.price)}</span></td>
      <td><span class="ttag" style="background:${tc}20;color:${tc};border:1px solid ${tc}40">${(r.theme||'기타').split(' ').slice(0,2).join(' ')}</span></td>
    </tr>`;
  }).join('');
}

async function ra(){
  const data=await fetch('/api/alerts?limit=100').then(r=>r.json()).catch(()=>[]);
  const el=document.getElementById('aList');
  if(!data.length){ el.innerHTML='<div class="empty">아직 알림이 없습니다.<br>(30분 쿨다운 적용)</div>'; return; }
  const tcolor={};TD.forEach(t=>tcolor[t.id]=t.color);
  el.innerHTML=data.map(a=>{
    const tc=tcolor[a.theme||'']||'#3a3a58';
    return`<div class="ar">
      ${bdg(a.grade)}
      <span class="sym" style="min-width:46px;cursor:pointer" onclick="pg('detail','${a.symbol}')">${a.symbol}</span>
      <span class="ttag" style="background:${tc}20;color:${tc};border:1px solid ${tc}40;padding:1px 5px;font-size:.58rem;border-radius:2px">${(a.theme||'기타').split(' ').slice(0,2).join(' ')}</span>
      <span style="font-family:'Space Mono',monospace;font-size:.76rem;color:#ffd000">${f(a.score,1)}점</span>
      <span class="am">${a.message||''}</span>
      <span class="at">${new Date(a.created_at).toLocaleString('ko-KR')}</span>
    </div>`;
  }).join('');
}

document.getElementById('banner').style.display='';
document.getElementById('banner').textContent='📡 실제 주식 데이터 로딩 중... (5~10분 소요)';
preloadSnapshot();
conn();
setInterval(chkLoad,4000);
</script>
</body>
</html>"""
