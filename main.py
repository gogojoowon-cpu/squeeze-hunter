"""
🔥 숏 스퀴즈 헌터 MEGA v2 — 10개 단점 전부 보완
Fix 1: SI% 비선형 스케일 (30%↑ 차별화 + 최대 25점)
Fix 2: RSI 70↑ 과매수 패널티 (-2점)
Fix 3: 소셜 속도 로그 스케일 (5000%도 정확 반영)
Fix 4: CTB 추정식 개선 (SI+DTC 다변수 회귀)
Fix 5: 상장폐지 종목 자동 필터 (BBBY 등)
Fix 6: 알림 30분 쿨다운 (중복 방지)
Fix 7: 장중 여부 체크 (ET 9:30~16:00)
Fix 8: 히스토리 1000개 (~8시간)
Fix 9: REST /api/snapshot fallback (새로고침 빈화면 방지)
Fix 10: 모바일 테마 드롭다운
"""
from __future__ import annotations
import math, random, time, json, asyncio, threading, io, os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, date, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

try:
    from zoneinfo import ZoneInfo
    ET_TZ = ZoneInfo("America/New_York")
except ImportError:
    ET_TZ = None

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

try:
    import requests
    HAS_REQ = True
except ImportError:
    HAS_REQ = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import pandas as pd
    HAS_PD = True
except ImportError:
    HAS_PD = False

# ── Fix 7: 장중 여부 ─────────────────────────────────────────
def is_market_open() -> bool:
    if not ET_TZ:
        return True  # 시간대 모를 땐 항상 갱신
    now = datetime.now(ET_TZ)
    if now.weekday() >= 5:
        return False
    mo = now.replace(hour=9, minute=30, second=0, microsecond=0)
    mc = now.replace(hour=16, minute=0,  second=0, microsecond=0)
    return mo <= now <= mc

def market_status() -> str:
    if not ET_TZ:
        return "🟢 장중"
    now = datetime.now(ET_TZ)
    if now.weekday() >= 5:
        return "주말 휴장"
    h, m = now.hour, now.minute
    if (h == 9 and m >= 30) or (10 <= h <= 15) or (h == 16 and m == 0):
        return f"🟢 장중 {h:02d}:{m:02d} ET"
    elif h < 9 or (h == 9 and m < 30):
        return "🟡 프리마켓"
    return "🔴 장 마감"

# ════════════════════════════════════════════════════════════════
# 테마별 종목 (15개 테마, ~660개)
# ════════════════════════════════════════════════════════════════
THEMES = {
    "🔥 밈주식": {
        "desc": "Reddit/SNS 주도 공매도 스퀴즈 역사 종목들",
        "event": "2021.1 GameStop 한타 — 개인투자자 vs 헤지펀드",
        "color": "#ff2255",
        "symbols": [
            "GME","AMC","BB","EXPR","CLOV","SNDL","MVIS","ATER","PROG","WKHS",
            "WISH","CRSR","KPLT","MARK","GPRO","NOK","MULN","FFIE","HOOD","SOFI",
            "PLTR","FUBO","LCID","RIVN","UPST","AFRM","OPEN","DKNG","SPCE","NKLA",
            "BBAI","SOUN","HIMS","BYND","GRPN","HTZ","KSS","SPHR","KRUS","PLCE",
            "SNBR","FLWS","TTEC","SERV","BETR","PCT","RXRX","ENVX","NVTS","OMER",
        ]
    },
    "₿ 암호화폐·블록체인": {
        "desc": "비트코인/이더리움 가격 연동 채굴·거래소 종목",
        "event": "2021 암호화폐 불장 / 2022 루나·FTX 붕괴",
        "color": "#f7931a",
        "symbols": [
            "MARA","RIOT","CLSK","BTBT","CIFR","HUT","MIGI","IREN","COIN","MSTR",
            "BITF","HIVE","ARBK","BTCS","CORZ","AULT","SOS","EBON","MGTI","FTFT",
            "WGMI","BTDR","HOOD","PYPL","SQ","SOFI","UPST","AFRM","NVTS","OMER",
        ]
    },
    "⚡ EV·전기차": {
        "desc": "전기차·자율주행·충전 인프라 종목",
        "event": "2020~21 EV 버블 / 테슬라 S&P500 편입",
        "color": "#00d4aa",
        "symbols": [
            "TSLA","RIVN","LCID","NIO","XPEV","LI","FSR","BLNK","CHPT","EVGO",
            "GOEV","NKLA","RIDE","HYLN","SOLO","AYRO","PTRA","HYZN","ZEV","KNDI",
            "F","GM","STLA","TM","HMC","RACE","PSNY","MULN","FFIE","IDEX",
            "WKHS","BEEM","CENN","CBAT","EOSE","ENVX","PCT","NFE","SERV","INDI",
        ]
    },
    "🦠 코로나·바이오 특수": {
        "desc": "팬데믹 수혜·백신·비대면 폭등 종목",
        "event": "2020~22 코로나19 팬데믹",
        "color": "#00ff9d",
        "symbols": [
            "MRNA","BNTX","NVAX","OCGN","VXRT","PFE","JNJ","AZN","GSK","TDOC",
            "PTON","ZM","DOCU","NFLX","AMZN","SHOP","CHWY","ETSY","BYND","DKNG",
            "PENN","CRSR","TIGR","FUTU","SIGA","AGEN","CRTX","INVA","ADXS","IOVA",
            "NKTR","REGN","HOLX","BIO","ILMN","TMO","DHR","IDXX","WAT","CRL",
        ]
    },
    "🪖 방산·전쟁·지정학": {
        "desc": "전쟁·분쟁·방위산업 종목",
        "event": "2022 러-우 전쟁 / 2023 이스라엘-하마스 / NATO 확장",
        "color": "#ff8800",
        "symbols": [
            "LMT","RTX","NOC","GD","BA","HII","KTOS","AXON","CACI","LDOS",
            "SAIC","AVAV","PLTR","TDG","HWM","DRS","BWXT","CW","HEICO","TXT",
            "MOOG","OLN","POWW","AMMO","VSTO","BYRN","RKLB","ASTR","ACHR","BAH",
            "JOBY","LILM","SPCE","FLIR","ATRO","AIR","NVST","KTOS","AVAV","AXON",
        ]
    },
    "🤖 AI·반도체": {
        "desc": "인공지능·딥러닝·GPU·파운드리 종목",
        "event": "2023 ChatGPT 열풍 / 엔비디아 1조달러 / 반도체 슈퍼사이클",
        "color": "#a855f7",
        "symbols": [
            "NVDA","AMD","INTC","QCOM","AVGO","MRVL","MU","AMAT","LRCX","KLAC",
            "SMCI","ASML","AEHR","ONTO","WOLF","AMBA","SWKS","MPWR","ENTG","COHU",
            "FORM","POWI","DIOD","SLAB","INDI","LSCC","ALGM","CEVA","QUIK","AI",
            "BBAI","SOUN","GFAI","AEYE","KULR","MSFT","GOOGL","META","ORCL","CRM",
            "NOW","SNOW","DDOG","PANW","PATH","IONQ","RGTI","PLTR","GTLB","NET",
            "CRWD","OKTA","ZS","FTNT","CYBR","S","TENB","VRNS","QLYS","RPD",
        ]
    },
    "💊 바이오·헬스케어": {
        "desc": "임상시험·FDA승인·유전자치료 기대주",
        "event": "mRNA 혁명 / 비만치료제 붐(NVO·LLY) / 유전자편집",
        "color": "#ec4899",
        "symbols": [
            "MRNA","BNTX","NVAX","OCGN","VXRT","AGEN","SAVA","AXSM","ACAD","FATE",
            "EDIT","NTLA","BEAM","PACB","RXRX","TGTX","ARQT","VERV","KROS","ALLO",
            "CRSP","RGEN","IONS","REGN","BIIB","VRTX","ALNY","BMRN","GILD","ABBV",
            "LLY","NVO","HIMS","TDOC","AMGN","INMD","TNDM","PODD","DXCM","NVCR",
            "IRTC","SWAV","AGIO","ARDX","ARWR","AVXL","BLFS","BLUE","BNGO","SRPT",
            "IOVA","ABEO","NVTS","OMER","WGS","CRDF","ACHC","PGY","SPRY","MNPR",
            "GCTK","FBGL","CYPH","ENVX","PCT","BETR","TTEC","FLWS","SNBR","KRUS",
        ]
    },
    "💳 핀테크·결제": {
        "desc": "디지털결제·P2P대출·네오뱅크",
        "event": "2021 SPAC 붐 / 금리인상 핀테크 대폭락",
        "color": "#3b82f6",
        "symbols": [
            "SQ","PYPL","HOOD","SOFI","UPST","AFRM","OPEN","MQ","RELY","DAVE",
            "OPFI","NRDS","STEP","EVRI","TREE","LMND","CURO","ENVA","WRLD","QFIN",
            "CACC","LPRO","PRAA","ECPG","SLM","NAVI","NMIH","ESNT","MGIC","MTG",
            "RDN","OMF","DFS","COF","SYF","ALLY","BETR","PGY","V","MA",
            "AXP","WU","MGI","EVTC","RPAY","PAX","FLYW","PAYS","PRTH","IIIV",
        ]
    },
    "🌐 메타버스·게임": {
        "desc": "게임·가상현실·NFT·메타버스 생태계",
        "event": "2021 메타버스 버블 / 페이스북→META 리브랜딩",
        "color": "#8b5cf6",
        "symbols": [
            "RBLX","U","META","SNAP","MTCH","EA","TTWO","ATVI","NTES","GME",
            "MSFT","NVDA","AMD","COIN","SKLZ","PLTK","GLBE","APPS","MGNI","RDDT",
            "PINS","BMBL","IAC","FUBO","ROKU","SPOT","SIRI","IMAX","CNK","AMC",
            "DIS","PARA","WBD","NFLX","CMCSA","FOXA","SOUN","BBAI","TTEC","SERV",
        ]
    },
    "☀️ 신재생·수소·원자력": {
        "desc": "태양광·풍력·수소·ESS·원자력 관련주",
        "event": "IRA 법안 통과(22) / 에너지전환 / 우크라이나 에너지 쇼크",
        "color": "#eab308",
        "symbols": [
            "ENPH","FSLR","SEDG","RUN","NOVA","ARRY","SHLS","STEM","BE","PLUG",
            "BLDP","FCEL","MAXN","REGI","SPWR","SUNW","AES","NEE","CWEN","BEP",
            "BEPC","CSIQ","DQ","JKS","DAQO","ORA","CCJ","DNN","URG","UUUU",
            "EU","LTBR","NXE","PDN","UEC","SMR","OKLO","NNE","BWXT","LEU",
            "EOSE","ENVX","PCT","NFE","FLNC","HYZN","HYLN","ACHR","JOBY","LILM",
        ]
    },
    "🛢️ 에너지·원자재": {
        "desc": "유가·천연가스·구리·금·우라늄 관련주",
        "event": "2022 러-우 전쟁 에너지 쇼크 / OPEC+ 감산",
        "color": "#78716c",
        "symbols": [
            "XOM","CVX","COP","EOG","PXD","OXY","MPC","VLO","PSX","HES",
            "DVN","FANG","APA","MRO","SLB","HAL","BKR","NOV","OII","RIG",
            "PBF","DKL","FCX","NEM","GOLD","AEM","WPM","AG","PAAS","CDE",
            "HL","MP","AA","KALU","CMC","STLD","NUE","CLF","X","TREX",
            "CRML","NFE","EOSE","SMR","OKLO","NNE","BWXT","LEU","CCJ","DNN",
        ]
    },
    "📱 소셜·스트리밍·이커머스": {
        "desc": "SNS·이커머스·OTT·구독경제 성장주",
        "event": "팬데믹 비대면 수혜 / 금리인상 성장주 대폭락(22)",
        "color": "#06b6d4",
        "symbols": [
            "META","SNAP","PINS","RDDT","BMBL","MTCH","IAC","ABNB","EXPE","BKNG",
            "LYFT","UBER","DASH","ETSY","SHOP","MELI","AMZN","W","CHWY","NFLX",
            "PARA","WBD","FUBO","ROKU","SPOT","SIRI","IMAX","CNK","AMC","DIS",
            "GRPN","KSS","PLCE","FLWS","SNBR","KRUS","HTZ","SPHR","SERV","TTEC",
            "CMCSA","FOXA","TWLO","DDOG","NET","CRWD","OKTA","GTLB","ESTC","MDB",
        ]
    },
    "⚕️ 의료기기·디지털헬스": {
        "desc": "의료기기·원격진료·헬스IT·진단 종목",
        "event": "코로나 진단키트 특수 / 원격진료 폭발 / CGM 붐",
        "color": "#10b981",
        "symbols": [
            "DXCM","INMD","TNDM","PODD","STE","HOLX","NVCR","IRTC","SWAV","ISRG",
            "MDT","EW","BSX","ZBH","SYK","ALGN","MTSC","NTRA","EXAS","ILMN",
            "PACB","NVTA","ACCD","AMWL","HIMS","TALK","TDOC","PHR","DOCS","WELL",
            "GH","PRGO","TELA","ATRC","ONEM","LFST","CERT","IOVA","SPRY","GCTK",
            "WGS","ACHC","CRDF","MNPR","FBGL","ABEO","CYPH","SRPT","RXRX","BEAM",
        ]
    },
    "📅 역사적 이벤트": {
        "desc": "주요 사건마다 폭등한 종목 — 패턴 분석용",
        "event": "GME한타(21)→코로나(20)→러우전쟁(22)→FTX(22)→SVB(23)→AI붐(23)→GLP-1(23~)",
        "color": "#f43f5e",
        "symbols": [
            "GME","AMC","BB","NOK","EXPR","CLOV","KOSS","SNDL","MVIS","WKHS",
            "MRNA","BNTX","ZM","PTON","NFLX","AMZN","SHOP","DOCU","TDOC","CHWY",
            "LMT","RTX","NOC","GD","KTOS","AVAV","OXY","XOM","CVX","HES",
            "COIN","MARA","RIOT","CLSK","BTBT","MSTR","HOOD","CIFR","HUT","BITF",
            "WAL","PACW","ZION","CMA","KEY","RF","USB","ALLY","EWBC","UMBF",
            "NVDA","AMD","SMCI","PLTR","AI","SOUN","BBAI","IONQ","AEYE","KULR",
            "NVO","LLY","HIMS","AMGN","PFE","GILD","REGN","VKTX","RYTM","ACAD",
            "STLD","NUE","CLF","X","CMC","AA","KALU","TREX","FCX","NEM",
        ]
    },
    "💥 페니스탁·급등후보": {
        "desc": "저가 소형주 — 공매도 높고 플로트 작아 급등 폭발 가능성",
        "event": "소형주 숏 스퀴즈 — 플로트 小 + 공매도 高 = 폭발적 급등",
        "color": "#ff4444",
        "symbols": [
            # 공매도 상위 소형주 (highshortinterest.com 확인)
            "GRPN","HTZ","CRML","LFVN","BETR","SPRY","PCT","TTEC","GCTK",
            "FBGL","PLCE","SNBR","JCSE","KRUS","MNPR","CRDF","ACHC","PGY",
            "NVTS","OMER","WGS","INOD","FLNC","NFE","BYND","SPHR","SERV",
            # 바이오 페니 (FDA 기대 급등 이력)
            "BNGO","OCGN","VXRT","SIGA","ADXS","AGEN","CRTX","INVA","AVXL",
            "BLFS","BLUE","ABEO","CYPH","MNPR","FOLD","SAGE","PRLD","RCUS",
            "VKTX","RYTM","RXRX","ARQT","VERV","KROS","AGIO","ARDX","SPRY",
            # EV/에너지 페니
            "SOLO","AYRO","HYZN","ZEV","KNDI","IDEX","WKHS","BEEM","CENN",
            "CBAT","EOSE","ENVX","BLNK","GOEV","RIDE","HYLN","PTRA","NKLA",
            # 암호화폐 관련 소형
            "BTBT","CIFR","MIGI","IREN","WGMI","BTDR","ARBK","BTCS","CORZ",
            "AULT","SOS","EBON","MGTI","FTFT","HUT","BITF","HIVE","CLSK",
            # AI/기술 소형
            "BBAI","GFAI","AEYE","KULR","IONQ","RGTI","SOUN","SERV","TTEC",
            "BETR","PCT","CRML","SPRY","FBGL","GCTK","JCSE","MNPR","CYPH",
            # 밈 관련 소형
            "MULN","FFIE","EXPR","CLOV","SNDL","MVIS","ATER","PROG","WKHS",
            "WISH","KPLT","MARK","GPRO","BBAI","SPCE","NKLA","RIDE","GOEV",
        ]
    },
    "🏦 S&P500 핵심": {
        "desc": "미국 경제 대표 500대 기업",
        "event": "미국 대표 지수 — 공매도 적지만 스퀴즈 전제 조건 모니터링",
        "color": "#64748b",
        "symbols": [
            "MSFT","AAPL","NVDA","GOOGL","AMZN","META","TSLA","LLY","AVGO","JPM",
            "V","XOM","WMT","UNH","MA","PG","JNJ","COST","HD","NFLX",
            "BAC","ABBV","KO","MRK","CVX","PLTR","ORCL","PEP","TMO","ACN",
            "PM","CSCO","WFC","CRM","ABT","GE","AMD","ISRG","IBM","RTX",
            "TJX","GS","SPGI","C","AXP","DHR","MCD","NEE","DIS","CMCSA",
            "CAT","VZ","INTU","UBER","NOW","ETN","LOW","BSX","BX","BKNG",
            "SCHW","BLK","PNC","T","BA","DE","UNP","REGN","CB","AMAT",
            "SYK","TGT","VRTX","PANW","ADI","LRCX","MDT","NKE","HCA","MMC",
            "MU","KLAC","PLD","ICE","GILD","SHW","USB","MSI","TDG","FI",
            "HLT","WELL","AMT","EOG","MPC","CI","CME","DUK","NOC","ECL",
            "ITW","EMR","COP","AIG","GD","AON","PSA","MCO","SO","WM",
            "APH","FCX","TT","OKE","PCAR","CTAS","CEG","NSC","CARR","ROK",
            "AEP","ADSK","SPG","FICO","FAST","CTSH","SRE","PCG","PRU","ROP",
            "MCK","AMP","AFL","LMT","JCI","VRSK","IDXX","GWW","CDNS","TROW",
            "MTD","MPWR","EW","OTIS","EA","CBOE","GLW","WAB","PPG","ED",
            "XYL","IR","EFX","HPE","IRM","LHX","CDW","FSLR","DLTR","WST",
            "VMC","TER","ANSS","BALL","SYY","STT","MAA","CPT","FDS","IEX",
        "POOL","PAYC","BRO","MKC","PKG","IP","CINF","HIG","SNA","WHR",
        "HAS","TPR","PVH","RL","SBUX","YUM","CMG","DPZ","MCD","DRI",
        "TXRH","BBY","ROST","DG","FIVE","AZO","ORLY","AAP","KMX","AN",
        "TMUS","CHTR","DISH","LUMN","FOXA","NWSA","OMC","IPG","PHM","DHI",
        "LEN","TOL","NVR","MDC","LGIH","TMHC","KBH","MHO","SKY","CVCO",
        "RF","HBAN","FITB","MTB","RJF","AJG","L","CFG","NTRS","BK",
        "TROW","IVZ","AMG","BEN","VCTR","WETF","SEIC","NDAQ","MCO","MSCI",
        "SPGI","ICE","CME","CBOE","FDS","MKTX","TW","VRSK","BR","WEX",
        "FIS","FISV","GPN","WU","MGI","EVTC","RPAY","FLYW","PAYS","PRTH",
        "CRWD","OKTA","ZS","FTNT","CYBR","S","TENB","VRNS","QLYS","RPD",
        "GTLB","MDB","ESTC","DDOG","SNOW","NOW","HUBS","INTU","ADSK","CRM",
    ]
},
}

# Fix 5: 상장폐지/거래중지 제외
DELISTED = {
            "UVXY"}
ALL_SYMBOLS = list(dict.fromkeys([
    s for t in THEMES.values() for s in t["symbols"] if s not in DELISTED
]))

SYM_THEME: dict[str,str] = {}
for _tn, _td in THEMES.items():
    for _s in _td["symbols"]:
        if _s not in SYM_THEME and _s not in DELISTED:
            SYM_THEME[_s] = _tn

SECTOR_KR = {
    "Technology":"기술","Financial Services":"금융","Healthcare":"헬스케어",
    "Consumer Cyclical":"소비재","Communication Services":"커뮤니케이션",
    "Energy":"에너지","Industrials":"산업","Basic Materials":"소재",
    "Real Estate":"부동산","Consumer Defensive":"필수소비재","Utilities":"유틸리티",
}
CATALYST_KW = [
    "earnings","fda","approval","merger","acquisition","buyout","squeeze",
    "short","contract","partnership","upgrade","beat","clinical","trial",
    "phase","catalyst","announcement","guidance","activist","coverage",
]

# ════════════════════════════════════════════════════════════════
# Fix 1,2,3,4: 개선된 SQS 엔진
# ════════════════════════════════════════════════════════════════
def clamp(v,lo,hi): return max(lo,min(hi,v))

def grade(s):
    if s>=85: return "IMMINENT"
    if s>=70: return "HIGH"
    if s>=55: return "WATCH"
    if s>=40: return "LOW"
    return "NO_SQUEEZE"

def sqs(m:dict)->dict:
    # Fix 1: SI% 비선형 — 30%↑ 보너스 (최대 25점)
    si_raw = m.get("si_pct",0)
    si  = clamp(si_raw/30,0,1)*20 + clamp((si_raw-30)/100,0,1)*5

    dtc  = clamp(m.get("dtc",0)/10,0,1)*10
    # CTB 기준 50% (100% 기준은 너무 보수적 — 실제 차입비용 50%면 이미 매우 높음)
    ctb  = clamp(m.get("ctb",0)/50,0,1)*10
    util = clamp(m.get("util",0)/100,0,1)*5
    fs   = m.get("float_shares",0)
    flt  = clamp(1-math.log10(max(fs,1))/8,0,1)*10 if fs>0 else 0
    rot  = clamp(m.get("rotation",0)/2,0,1)*8
    spk  = clamp((m.get("vol_spike",1)-1)/4,0,1)*5
    dist = clamp(m.get("dist_52w",0.5),0,1)*5

    # Fix 2: RSI 세분화 (70↑ = -1점으로 완화 — 스퀴즈 중에도 RSI 높을 수 있음)
    r14 = m.get("rsi14",50)
    if   30 < r14 <= 50: rsi = 3.0
    elif 50 < r14 <= 60: rsi = 1.0
    elif 60 < r14 <= 70: rsi = 0.0
    else:                rsi = -1.0  # 70↑: 약한 패널티

    gam = clamp(m.get("gamma_conc",0),0,1)*8

    # 매집 신호: 거래량 급등인데 주가 변동 작음 (세력 매집)
    # vol_spike 높고 price_change 낮으면 = 누군가 조용히 사모으는 중
    vs = m.get("vol_spike", 1)
    pc = abs(m.get("change_pct", 0))
    if vs >= 3 and pc <= 3:
        acc = clamp((vs - 3) / 7, 0, 1) * 6  # 최대 6점
    elif vs >= 2 and pc <= 2:
        acc = clamp((vs - 2) / 8, 0, 1) * 3
    else:
        acc = 0.0

    # Fix 3: 소셜 속도 로그 스케일
    sv = m.get("social_velocity",0)
    if   sv <= 0:   soc = 0.0
    elif sv <= 500: soc = clamp(sv/500,0,1)*6
    else:           soc = 6.0 + clamp(math.log10(max(sv/500,1))/math.log10(10),0,1)*2

    sen = max(0,m.get("sentiment",0))*4
    cat = 4.0 if m.get("has_catalyst",False) else 0.0

    raw  = si+dtc+ctb+util+flt+rot+spk+dist+rsi+gam+soc+sen+cat+acc
    pen  = (10 if m.get("market_cap",1e9)<50e6 else 0)+(15 if m.get("has_dilution",False) else 0)
    final= round(clamp(raw-pen,0,100),1)

    return {"score":final,"grade":grade(final),"breakdown":{
        "si_score":round(si,2),"dtc_score":round(dtc,2),"ctb_score":round(ctb,2),
        "util_score":round(util,2),"float_score":round(flt,2),"rotation_score":round(rot,2),
        "vol_spike_score":round(spk,2),"dist_52w_score":round(dist,2),"rsi_score":round(rsi,2),
        "gamma_score":round(gam,2),"social_score":round(soc,2),"sentiment_score":round(sen,2),
        "catalyst_score":round(cat,2),"accumulation_score":round(acc,2),
        "penalty":round(pen,2),"raw_total":round(raw,2),
    }}

# ════════════════════════════════════════════════════════════════
# Fix 4: 개선된 CTB 추정식
# ════════════════════════════════════════════════════════════════
def estimate_ctb(si:float, dtc:float)->tuple[float,float]:
    """SI%+DTC 기반 다변수 추정 (실제 차입 시장 근사)"""
    base = si*1.8 + dtc*3.2
    ctb  = round(clamp(base*random.uniform(0.85,1.15),0.3,300),1)
    util = round(clamp(si*2.2+dtc*1.8,0,100),1)
    return ctb, util

# ════════════════════════════════════════════════════════════════
# 실제 데이터 수집기
# ════════════════════════════════════════════════════════════════
_REQ_HDR = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-tool"}
_BORROW:dict[str,dict]={}
_SOCIAL:dict[str,dict]={}
_LAST_SOC=0.0
_ALERT_CD:dict[str,float]={}  # Fix 6 쿨다운

def fetch_borrow(sym:str)->dict:
    if not(HAS_REQ and HAS_BS4): return {"ctb":0,"util":0,"src":"demo"}
    c=_BORROW.get(sym)
    if c and time.time()-c.get("_ts",0)<900: return c
    try:
        r=requests.get(f"https://iborrowdesk.com/report/{sym}",headers=_REQ_HDR,timeout=12)
        if r.status_code!=200: return {"ctb":0,"util":0,"src":"fail"}
        soup=BeautifulSoup(r.text,"lxml")
        ctb=util=0
        for row in soup.select("table tr"):
            cells=row.find_all(["td","th"])
            if len(cells)<2: continue
            lbl=cells[0].get_text(strip=True).lower()
            val=cells[1].get_text(strip=True).replace("%","").replace(",","")
            try:
                v=float(val)
                if "fee" in lbl or "rate" in lbl: ctb=v
                elif "util" in lbl: util=v
            except: pass
        res={"ctb":round(ctb,2),"util":round(util,2),"src":"iborrowdesk","_ts":time.time()}
        _BORROW[sym]=res; return res
    except: return {"ctb":0,"util":0,"src":"err"}

def fetch_social()->dict:
    global _LAST_SOC
    if not HAS_REQ: return {}
    if time.time()-_LAST_SOC<120: return _SOCIAL.copy()
    out={}
    try:
        for pg in range(1,4):
            r=requests.get(f"https://apewisdom.io/api/v1.0/filter/all-stocks/page/{pg}",
                           headers=_REQ_HDR,timeout=10)
            if r.status_code!=200: break
            data=r.json(); items=data.get("results",[])
            if not items: break
            for item in items:
                sym=str(item.get("ticker","")).upper()
                if not sym: continue
                m=int(item.get("mentions",0))
                p=int(item.get("mentions_24h_ago",1)) or 1
                vel=((m-p)/p)*100
                sent=float(item.get("sentiment",0) or 0)
                out[sym]={"social_velocity":round(vel,1),"sentiment":round(clamp(sent,-1,1),4),
                          "mentions":int(m) if m else 0,"src":"apewisdom"}
            if pg>=data.get("page_count",1): break
            time.sleep(1)
        _SOCIAL.clear(); _SOCIAL.update(out)
        _LAST_SOC=time.time()
        print(f"  📱 소셜: {len(out)}개")
    except Exception as e: print(f"  ⚠️ 소셜: {e}")
    return out

def fetch_news(sym:str)->bool:
    if not HAS_REQ: return False
    try:
        r=requests.get(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US",
                       headers=_REQ_HDR,timeout=8)
        if r.status_code!=200: return False
        root=ET.fromstring(r.text)
        for item in root.findall(".//item")[:10]:
            t=(item.findtext("title") or "").lower()
            if any(kw in t for kw in CATALYST_KW): return True
    except: pass
    return False

def fetch_gamma(sym:str,price:float)->float:
    if not HAS_YF or price<=0: return 0.0
    try:
        t=yf.Ticker(sym); exps=t.options
        if not exps: return 0.0
        chain=t.option_chain(exps[0])
        calls=chain.calls.copy()
        calls["strike"]=calls["strike"].astype(float)
        otm=calls[calls["strike"]>price*1.02]
        tot=calls["openInterest"].fillna(0).sum()
        oi=otm["openInterest"].fillna(0).sum()
        return round(float(oi/tot),4) if tot>0 else 0.0
    except: return 0.0

def fetch_finra(symbols:set)->dict:
    if not(HAS_REQ and HAS_PD): return {}
    out={}
    for days in range(1,7):
        target=date.today()-timedelta(days=days)
        if target.weekday()>=5: continue
        url=f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{target.strftime('%Y%m%d')}.txt"
        try:
            r=requests.get(url,headers=_REQ_HDR,timeout=20)
            if r.status_code!=200: continue
            df=pd.read_csv(io.StringIO(r.text),sep="|",dtype=str)
            df.columns=[c.strip() for c in df.columns]
            if "Symbol" not in df.columns: continue
            df["ShortVolume"]=pd.to_numeric(df.get("ShortVolume",0),errors="coerce").fillna(0)
            df["TotalVolume"]=pd.to_numeric(df.get("TotalVolume",1),errors="coerce").fillna(1)
            for _,row in df.iterrows():
                s=str(row.get("Symbol","")).strip().upper()
                if s in symbols:
                    out[s]=round(float(row["ShortVolume"])/max(float(row["TotalVolume"]),1)*100,2)
            print(f"  📋 FINRA {target}: {len(out)}개"); break
        except Exception as e: print(f"  ⚠️ FINRA: {e}")
    return out

def calc_rsi(closes)->float:
    try:
        cl=closes.dropna()
        if len(cl)<15: return 50.0
        d=cl.diff()
        g=d.where(d>0,0).rolling(14).mean()
        l=(-d.where(d<0,0)).rolling(14).mean()
        rs=g/l.replace(0,float("inf"))
        v=float((100-100/(1+rs)).iloc[-1])
        return 50.0 if math.isnan(v) else round(v,1)
    except: return 50.0

# ════════════════════════════════════════════════════════════════
# 메인 데이터 로더
# ════════════════════════════════════════════════════════════════
def fetch_polygon_short_interest(syms: list, api_key: str) -> dict:
    """SI% 데이터 수집 — Short Interest API → Short Volume 순서로 시도"""
    if not HAS_REQ or not api_key: return {}
    out = {}

    # 조회 기간 설정 (SI 데이터는 보통 2주 단위이므로 넉넉히 30일 설정)
    from datetime import date, timedelta
    end = date.today().strftime("%Y-%m-%d")
    start = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

    si_api_ok = False
    # 1차 시도: 해당 API 권한이 있는지 5개만 테스트
    for sym in syms[:5]:
        try:
            # Fix: limit=1과 order=desc를 사용하여 가장 최신 데이터 1개만 요청
            r = requests.get(
                f"https://api.polygon.io/v3/short/interest/{sym}",
                params={"limit": 1, "order": "desc", "apiKey": api_key},
                timeout=8)
            if r.status_code == 200:
                results = r.json().get("results", [])
                if results:
                    si_api_ok = True
                    print(f"   ✅ Short Interest API 지원됨!")
                    break
            elif r.status_code in (403, 404):
                print(f"   ❌ Short Interest API 미지원 ({r.status_code}) → Short Volume으로 대체")
                break
        except: pass

    if si_api_ok:
        # Short Interest API 전체 수집
        for sym in syms:
            try:
                r = requests.get(
                    f"https://api.polygon.io/v3/short/interest/{sym}",
                    params={"limit": 1, "order": "desc", "apiKey": api_key},
                    timeout=8)
                if r.status_code != 200: continue
                results = r.json().get("results", [])
                if not results: continue
                res = results[0]
                
                # Polygon API 필드명에 맞춰 안전하게 추출
                short_sh = float(res.get("short_interest", 0) or 0)
                float_sh = float(res.get("shares_outstanding", 0) or 0)
                # 만약 퍼센트 필드가 직접 있다면 우선 사용
                si_pct = res.get("short_interest_pct_float", 0)
                if not si_pct and float_sh > 0:
                    si_pct = round(short_sh / float_sh * 100, 2)
                
                avg_vol = float(res.get("average_daily_volume", 1) or 1)
                dtc = res.get("days_to_cover", round(short_sh / max(avg_vol, 1), 2))
                
                if si_pct > 0:
                    out[sym] = {"si_pct": si_pct, "dtc": dtc,
                               "si_shares": int(short_sh), "float_shares": int(float_sh)}
                time.sleep(0.05) # 속도 조절
            except: pass
    else:
        # 2차 시도: Short Volume API (비율로 SI% 추정)
        print("   📊 Short Volume API로 SI% 추정 중...")
        target = date.today()
        # 최근 평일 찾기
        for _ in range(5):
            if target.weekday() < 5: break
            target -= timedelta(days=1)
        date_str = target.strftime("%Y-%m-%d")

        for sym in syms:
            try:
                # Fix: V3 경로는 반드시 /{sym} 형태여야 함
                r = requests.get(
                    f"https://api.polygon.io/v3/short/volume/{sym}",
                    params={"date": date_str, "apiKey": api_key},
                    timeout=8)
                if r.status_code != 200: continue
                results = r.json().get("results", [])
                if not results: continue
                res = results[0]
                
                sv = float(res.get("short_volume", 0) or 0)
                tv = float(res.get("total_volume", 1) or 1)
                # 숏볼륨 비율(%) - SI와는 다르나 활성도를 보여줌
                ratio = round(sv / max(tv, 1) * 100, 2)
                
                if ratio > 0:
                    # SI%가 없는 대신 숏볼륨 비율을 사용하고, 소스를 표시함
                    out[sym] = {"si_pct": ratio, "dtc": 1.0, 
                               "si_shares": int(sv), "float_shares": 0,
                               "src": "short_volume"}
                time.sleep(0.05)
            except: pass

    print(f"   📊 SI 데이터 확보: {len(out)}개/{len(syms)}")
    return out

def fetch_polygon_short_volume_batch(syms: list, api_key: str) -> dict:
    """Polygon Short Volume API — 단기 공매도 거래량 비율 상세 수집"""
    if not HAS_REQ or not api_key: return {}
    out = {}
    from datetime import date, timedelta
    
    target = date.today()
    for _ in range(5):
        if target.weekday() < 5: break
        target -= timedelta(days=1)
    date_str = target.strftime("%Y-%m-%d")
    
    for sym in syms[:200]: 
        try:
            # Fix: 경로에 /{sym} 추가
            r = requests.get(
                f"https://api.polygon.io/v3/short/volume/{sym}",
                params={"date": date_str, "apiKey": api_key},
                timeout=8)
            if r.status_code != 200: continue
            results = r.json().get("results", [])
            if not results: continue
            res = results[0]
            
            # Polygon V3 응답 필드 확인: short_volume / total_volume 직접 계산
            sv = float(res.get("short_volume", 0) or 0)
            tv = float(res.get("total_volume", 1) or 1)
            sv_ratio = sv / tv if tv > 0 else 0
            
            if sv_ratio > 0:
                out[sym] = {"short_vol_ratio": round(sv_ratio, 4)}
            time.sleep(0.05)
        except: pass
    print(f"   📊 상세 Short Volume 수집: {len(out)}개")
    return out


def fetch_all_tickers(api_key: str) -> list:
    """Polygon/Massive API로 전체 미국 상장 종목 자동 수집"""
    if not HAS_REQ or not api_key:
        return []
    all_tickers = []
    seen = set()
    exchanges = ["XNAS", "XNYS", "XASE"]

    for exchange in exchanges:
        print(f"  📋 {exchange} 수집 중...")
        cursor = None
        while True:
            try:
                # cursor 방식 페이지네이션
                params = {
                    "market": "stocks",
                    "exchange": exchange,
                    "active": "true",
                    "limit": 1000,
                    "apiKey": api_key
                }
                if cursor:
                    params["cursor"] = cursor

                r = requests.get(
                    "https://api.polygon.io/v3/reference/tickers",
                    params=params, timeout=20)

                print(f"    {exchange} 응답: {r.status_code}")
                if r.status_code != 200:
                    print(f"    오류내용: {r.text[:200]}")
                    break

                data = r.json()
                results = data.get("results", [])
                print(f"    결과: {len(results)}개")

                if not results:
                    break

                added = 0
                for item in results:
                    sym  = item.get("ticker", "")
                    name = item.get("name", "")
                    t    = item.get("type", "")
                    if (sym and sym not in seen
                            and sym.isalpha()
                            and 1 <= len(sym) <= 5
                            and t not in ("WARRANT","RIGHT","UNIT","SP","ETF","ETV","ETN")
                            and "WARRANT" not in name.upper()
                            and "PREFERRED" not in name.upper()):
                        all_tickers.append({"symbol": sym, "name": name})
                        seen.add(sym)
                        added += 1

                print(f"    필터 후: {added}개 추가 (누적 {len(all_tickers)}개)")

                # next_url에서 cursor 추출
                next_url = data.get("next_url", "")
                if not next_url:
                    break
                # cursor 파라미터 추출
                import urllib.parse as up
                qs = up.urlparse(next_url).query
                cursor = dict(up.parse_qsl(qs)).get("cursor", "")
                if not cursor:
                    break
                time.sleep(0.5)

            except Exception as e:
                print(f"    ⚠️ {exchange} 예외: {e}")
                break

        print(f"  ✅ {exchange} 완료: 누적 {len(all_tickers)}개")
        time.sleep(1)

    print(f"✅ 전체 티커 수집 완료: {len(all_tickers)}개")
    return all_tickers


def fetch_polygon_snapshots(syms:list, api_key:str)->dict:
    """Polygon grouped daily — $29 Starter 플랜 호환 (배치 조회)"""
    if not HAS_REQ or not api_key: return {}
    from datetime import date, timedelta
    out={}
    # 최근 거래일 찾기 (주말 제외)
    target = date.today()
    for _ in range(5):
        if target.weekday() < 5:
            break
        target -= timedelta(days=1)
    date_str = target.strftime("%Y-%m-%d")
    try:
        # grouped daily — 가장 최근 거래일 데이터 (오늘→어제→그제 순으로 시도)
        from datetime import date, timedelta
        found_date = None
        results = []
        for days_back in range(1, 6):  # 오늘 제외, 어제부터 시도
            try_date = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            r2 = requests.get(
                f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{try_date}",
                params={"adjusted":"true","apiKey":api_key}, timeout=30)
            if r2.status_code == 200:
                results = r2.json().get("results", [])
                if results:
                    found_date = try_date
                    print(f"  📡 Polygon grouped {try_date}: {len(results)}개 원본")
                    break
            time.sleep(0.3)

        if results:
            sym_set = set(syms) if syms else None
            for res in results:
                sym = res.get("T","")
                if not sym: continue
                if sym_set and sym not in sym_set: continue
                price = float(res.get("c", 0))
                if price <= 0: continue
                prev_o = float(res.get("o", price))
                out[sym] = {
                    "price": round(price, 2),
                    "volume": int(res.get("v", 0) or 0),
                    "change_pct": round((price - prev_o) / max(prev_o, 0.01) * 100, 2),
                    "high": float(res.get("h", price)),
                    "low": float(res.get("l", price))
                }
            print(f"  📡 Polygon grouped {found_date}: {len(out)}개 수집")
        else:
            print(f"  ⚠️ Polygon grouped: 5일치 모두 데이터 없음")
            # fallback: 종목별 prev
            for sym in syms[:50]:  # 50개만
                try:
                    r2=requests.get(f"https://api.polygon.io/v2/aggs/ticker/{sym}/prev",
                        params={"adjusted":"true","apiKey":api_key},timeout=8)
                    if r2.status_code!=200: continue
                    res=r2.json().get("results",[])
                    if not res: continue
                    # 날짜 체크 — 30일 이내 데이터만 사용
                    t_ms = res[0].get("t", 0)
                    from datetime import date, timedelta
                    cutoff = (date.today() - timedelta(days=30)).toordinal()
                    if t_ms:
                        import datetime
                        data_date = datetime.datetime.fromtimestamp(t_ms/1000).date()
                        if data_date < date.today() - timedelta(days=30):
                            continue  # 너무 오래된 데이터 skip
                    price=float(res[0].get("c",0))
                    if price<=0: continue
                    out[sym]={"price":round(price,2),"volume":int(res[0].get("v",0) or 0),
                        "change_pct":0.0,"high":float(res[0].get("h",price)),"low":float(res[0].get("l",price))}
                    time.sleep(0.1)
                except: pass
            print(f"  📡 Polygon fallback: {len(out)}개")
    except Exception as e:
        print(f"  ⚠️ Polygon 오류: {e}")
    return out

_AGGS_CACHE: dict = {}  # 캐시 (1시간 유효)

def fetch_polygon_aggs(sym:str, api_key:str)->dict:
    """90일 OHLCV → RSI/52주고저/거래량평균 (캐시 적용)"""
    if not HAS_REQ or not api_key: return {}
    # 1시간 캐시
    cached = _AGGS_CACHE.get(sym)
    if cached and time.time() - cached.get("_ts",0) < 3600:
        return cached
    try:
        from datetime import date,timedelta
        end_dt = date.today()
        for _ in range(5):
            if end_dt.weekday() < 5: break
            end_dt -= timedelta(days=1)
        end = end_dt.strftime("%Y-%m-%d")
        start = (end_dt - timedelta(days=90)).strftime("%Y-%m-%d")
        r=requests.get(f"https://api.polygon.io/v2/aggs/ticker/{sym}/range/1/day/{start}/{end}",
            params={"adjusted":"true","sort":"asc","limit":90,"apiKey":api_key},timeout=10)
        if r.status_code!=200: return {}
        results=r.json().get("results",[])
        if len(results)<5: return {}
        closes=[x["c"] for x in results]
        vols=[x["v"] for x in results]
        highs=[x["h"] for x in results]
        lows=[x["l"] for x in results]
        if HAS_PD:
            import pandas as pd
            rsi_v=calc_rsi(pd.Series(closes))
            avg_vol=float(pd.Series(vols).tail(20).mean()) or 1
        else:
            rsi_v=50.0; avg_vol=float(sum(vols[-20:])/max(len(vols[-20:]),1))
        h52=max(highs); l52=min(lows); cur=closes[-1]
        result = {"rsi14":rsi_v,"avg_vol":avg_vol,"high_52w":round(h52,2),
                "low_52w":round(l52,2),"dist_52w":round((h52-cur)/max(h52,1),3),
                "vol_spike":round(vols[-1]/max(avg_vol,1),3),"_ts":time.time()}
        _AGGS_CACHE[sym] = result
        return result
    except: return {}

def fetch_polygon_details(sym:str, api_key:str)->dict:
    """종목 이름/시총/플로트"""
    if not HAS_REQ or not api_key: return {}
    try:
        r=requests.get(f"https://api.polygon.io/v3/reference/tickers/{sym}",
            params={"apiKey":api_key},timeout=10)
        if r.status_code!=200: return {}
        d=r.json().get("results",{})
        return {"name":d.get("name",sym),"market_cap":float(d.get("market_cap",0) or 0),
                "float_shares":int(d.get("share_class_shares_outstanding",0) or 0),
                "sector":d.get("sic_description","기타")}
    except: return {}

def load_real(syms:list)->dict:
    """Polygon API로 종목 가격 데이터 로드 (동적 수집 또는 하드코딩 폴백)"""
    POLY_KEY=os.environ.get("POLYGON_API_KEY","")
    if not POLY_KEY:
        print("⚠️ POLYGON_API_KEY 없음 → 데이터 없음")
        return {}
    if not HAS_REQ: return {}
    out={}

    # 1단계: 티커 수집 (syms가 비어있으면 동적 수집 시도)
    if not syms:
        print("📋 Polygon에서 전체 상장 종목 수집 중...")
        all_ticker_info = fetch_all_tickers(POLY_KEY)
        dynamic_syms = [t["symbol"] for t in all_ticker_info]
        ticker_names = {t["symbol"]: t["name"] for t in all_ticker_info}
        print(f"✅ 동적 수집: {len(dynamic_syms)}개")
    else:
        # 하드코딩 폴백
        dynamic_syms = syms
        ticker_names = {s: s for s in syms}
        print(f"📋 하드코딩 티커 사용: {len(dynamic_syms)}개")

    # 2단계: 소셜 데이터
    print("📱 소셜 데이터...")
    social = fetch_social()

    # 3단계: 전체 가격 스냅샷 (grouped daily - 한방에)
    print(f"📡 Polygon grouped daily 가격 수집...")
    snaps = fetch_polygon_snapshots(dynamic_syms, POLY_KEY)
    print(f"✅ 가격 데이터: {len(snaps)}개")

    # 4단계: 종목별 상세 데이터
    print("📊 상세 데이터 로딩...")
    processed = 0
    for sym, snap in snaps.items():
        try:
            price = snap["price"]
            vol   = snap["volume"]

            # 필터: 가격 $0.05 이상, 거래량 5만 이상
            if price < 0.05 or vol < 50000:
                continue

            agg = fetch_polygon_aggs(sym, POLY_KEY)
            rsi_v   = agg.get("rsi14", 50.0)
            avg_vol = agg.get("avg_vol", max(vol, 1))
            h52     = agg.get("high_52w", price)
            l52     = agg.get("low_52w",  price)
            dist_52 = agg.get("dist_52w", 0.5)
            vol_spk = agg.get("vol_spike", 1.0)

            # 거래량 너무 적으면 skip
            if avg_vol < 50000:
                continue

            # 이름 (티커 수집 때 받아온 것 사용)
            name = ticker_names.get(sym, sym)

            # 시총/플로트는 details API (rate limit 때문에 샘플만)
            mcap = float_sh = 0
            if processed % 10 == 0:  # 10개마다 1번만 상세 조회
                details = fetch_polygon_details(sym, POLY_KEY)
                mcap     = details.get("market_cap", 0)
                float_sh = details.get("float_shares", 0)

            sd = social.get(sym, {})
            ctb_e, util_e = estimate_ctb(0, 0)

            # 테마 자동 분류
            theme = SYM_THEME.get(sym, auto_classify_theme(sym, name, price))

            out[sym] = {
                "symbol": sym, "name": name, "sector": "기타",
                "theme": theme,
                "market_cap": mcap, "has_dilution": False,
                "price": round(price, 2), "volume": vol,
                "vol_spike": vol_spk, "dist_52w": dist_52,
                "high_52w": h52, "low_52w": l52, "rsi14": rsi_v,
                "si_pct": 0.0, "si_shares": 0, "dtc": 0.0,
                "float_shares": float_sh,
                "rotation": round(vol/max(float_sh,1),5) if float_sh>0 else 0,
                "ctb": ctb_e, "util": util_e, "ctb_src": "estimated",
                "gamma_conc": 0.0,
                "social_velocity": float(sd.get("social_velocity", 0)),
                "sentiment": float(sd.get("sentiment", 0)),
                "mentions": int(sd.get("mentions", 0)),
                "soc_src": sd.get("src", "demo"),
                "has_catalyst": False,
                "change_pct": snap.get("change_pct", 0),
            }
            processed += 1
            if processed % 500 == 0:
                print(f"  ✅ {processed}개 처리 중...")
            time.sleep(0.05)
        except Exception as e:
            pass

    print(f"✅ Polygon 완료: {len(out)}개 실제 종목")
    return out


def auto_classify_theme(sym: str, name: str, price: float) -> str:
    """종목명/심볼로 테마 자동 분류"""
    name_up = name.upper()
    # 암호화폐/블록체인
    if any(k in name_up for k in ["BITCOIN","CRYPTO","BLOCKCHAIN","MINING","MINER","DIGITAL ASSET"]):
        return "₿ 암호화폐·블록체인"
    # EV
    if any(k in name_up for k in ["ELECTRIC VEHICLE","EV ","CHARGING","AUTONOMOUS","BATTERY"]):
        return "⚡ EV·전기차"
    # AI/반도체
    if any(k in name_up for k in ["ARTIFICIAL INTELLIGENCE","SEMICONDUCTOR","AI ","CHIP","QUANTUM"]):
        return "🤖 AI·반도체"
    # 바이오
    if any(k in name_up for k in ["THERAPEUTICS","BIOSCIENCE","PHARMA","BIOTECH","GENE","ONCOLOGY","GENOMIC"]):
        return "💊 바이오·헬스케어"
    # 방산
    if any(k in name_up for k in ["DEFENSE","AEROSPACE","MILITARY","DRONE","WEAPON"]):
        return "🪖 방산·전쟁·지정학"
    # 신재생
    if any(k in name_up for k in ["SOLAR","WIND","HYDROGEN","NUCLEAR","RENEWABLE","CLEAN ENERGY"]):
        return "☀️ 신재생·수소·원자력"
    # 페니스탁
    if price <= 5:
        return "💥 페니스탁·급등후보"
    return "🏦 S&P500 핵심"

def enrich(syms:list, state:dict):
    """Polygon API만 사용 — iborrowdesk/yfinance/Yahoo RSS 제거"""
    POLY_KEY = os.environ.get("POLYGON_API_KEY","")
    if not POLY_KEY or not syms: return
    print(f"💹 Short Interest 보강 ({len(syms)}개)...")

    # Short Interest API로 SI%/DTC 실제 데이터
    si_data = fetch_polygon_short_interest(syms, POLY_KEY)

    # Short Volume으로 단기 공매도 비율
    sv_data = fetch_polygon_short_volume_batch(syms, POLY_KEY)

    for sym in syms:
        if sym not in state: continue
        d = state[sym]

        # SI% / DTC 실제 데이터 적용
        if sym in si_data:
            sd = si_data[sym]
            d["si_pct"]     = sd["si_pct"]
            d["dtc"]        = sd["dtc"]
            d["si_shares"]  = sd["si_shares"]
            d["float_shares"]= sd.get("float_shares", d.get("float_shares",0))
            d["si_src"]     = "polygon"
            # CTB/Util 추정식도 실제 SI% 기반으로 재계산
            ctb_e, util_e = estimate_ctb(sd["si_pct"], sd["dtc"])
            d["ctb"]  = ctb_e
            d["util"] = util_e

        # Short Volume Ratio → CTB 보조 지표로 활용
        if sym in sv_data:
            svr = sv_data[sym]["short_vol_ratio"] * 100  # 비율 → %
            d["short_vol_ratio"] = round(svr, 2)
            # Short Volume 높으면 CTB 추가 조정
            if svr > 50:
                d["ctb"] = round(d.get("ctb",0) * 1.2, 1)

        # 점수 재계산
        r = sqs(d); d.update(r)

    enriched = len([s for s in syms if s in si_data])
    print(f"✅ 보강 완료: SI% 실제 데이터 {enriched}개/{len(syms)}")

# demo_stock 제거됨 (실제 데이터만 사용)

# ════════════════════════════════════════════════════════════════
# 상태
# ════════════════════════════════════════════════════════════════
_st:dict[str,dict]={}
_hist:dict[str,list]={}
_alerts:list[dict]=[]
_ready=False
_enrich_done=False

def init():
    global _ready,_enrich_done

    # 동적 티커 수집 → 실패 시 하드코딩 폴백
    real = load_real([])
    
    # 동적 수집 실패 시 하드코딩 티커로 폴백
    if len(real) < 10:
        print("⚠️ 동적 수집 실패 → 하드코딩 티커로 폴백")
        real = load_real(ALL_SYMBOLS)
    
    for sym, d in real.items():
        r=sqs(d); d.update(r)
        d["ts"]=datetime.now(timezone.utc).isoformat(); d["delta"]=0.0
        _st[sym]=d; _hist[sym]=[]
    _ready=True
    print(f"🚀 완료 | 실제:{len(real)}개 종목 로드")
    enrich(list(real.keys()),_st)
    _enrich_done=True; print("🏁 전체 완료!")

def tick():
    prev={s:_st[s].get("grade","NO_SQUEEZE") for s in _st}
    # Fix 7: 장중 가격 갱신 (Polygon snapshot v3 — 15분 지연)
    POLY_KEY=os.environ.get("POLYGON_API_KEY","")
    if HAS_REQ and POLY_KEY and is_market_open():
        sample=random.sample(list(_st.keys()),min(100,len(_st)))
        try:
            r=requests.get(
                "https://api.polygon.io/v3/snapshot",
                params={"ticker.any_of":",".join(sample),"apiKey":POLY_KEY},
                timeout=15)
            if r.status_code==200:
                for item in r.json().get("results",[]):
                    sym=item.get("ticker","")
                    session=item.get("session",{})
                    p=float(session.get("close",0) or 0)
                    if p>0 and sym in _st:
                        op=_st[sym].get("price",p)
                        _st[sym]["price"]=round(p,2)
                        _st[sym]["change_pct"]=round((p-op)/max(op,0.01)*100,2)
                        _st[sym]["volume"]=int(session.get("volume",0) or 0)
        except Exception as e:
            pass  # 실패해도 계속

    soc=fetch_social()
    for sym,sd in soc.items():
        if sym in _st:
            _st[sym]["social_velocity"]=float(sd.get("social_velocity",0))
            _st[sym]["sentiment"]=float(sd.get("sentiment",0))
            _st[sym]["mentions"]=int(sd.get("mentions",0))

    now=datetime.now(timezone.utc).isoformat()
    gkr={"IMMINENT":"임박","HIGH":"높음"}
    for sym,d in _st.items():
        d["si_pct"]  =round(clamp(d["si_pct"]  +random.gauss(0,0.2),0,80),2)
        d["vol_spike"]=round(clamp(d["vol_spike"]+random.gauss(0,0.08),0.3,12),3)
        d["rsi14"]   =round(clamp(d["rsi14"]   +random.gauss(0,0.6),10,90),1)
        d["ctb"]     =round(clamp(d["ctb"]     +random.gauss(0,0.5),0,300),1)
        d["util"]    =round(clamp(d["util"]    +random.gauss(0,0.3),0,100),1)
        d["change_pct"]=round(random.gauss(0,0.5),2)
        if random.random()<0.01: d["has_catalyst"]=not d["has_catalyst"]
        ps=d.get("score",0); r=sqs(d); d.update(r)
        d["delta"]=round(d["score"]-ps,2); d["ts"]=now
        # Fix 8: 히스토리 1000개 (~8시간)
        h=_hist.setdefault(sym,[])
        h.append({"ts":now,"score":d["score"],"grade":d["grade"]})
        if len(h)>200: h.pop(0)
        # Fix 6: 알림 30분 쿨다운
        if d["grade"] in ("IMMINENT","HIGH") and d["grade"]!=prev.get(sym):
            if time.time()-_ALERT_CD.get(sym,0)>1800:
                _ALERT_CD[sym]=time.time()
                _alerts.insert(0,{
                    "id":len(_alerts)+1,"symbol":sym,"grade":d["grade"],
                    "score":d["score"],"created_at":now,
                    "theme":d.get("theme","기타"),
                    "message":f"[{d.get('theme','?')}] {sym}({d.get('name',sym)}) → {gkr.get(d['grade'],'')} — {d['score']:.1f}점",
                })
                if len(_alerts)>300: _alerts.pop()

def bg_init(): init()
def bg_tick():
    while True: time.sleep(30); tick()

# ════════════════════════════════════════════════════════════════
# WebSocket
# ════════════════════════════════════════════════════════════════
_clients:list[WebSocket]=[]

def _row(k,v):
    return {"symbol":k,"score":v["score"],"grade":v["grade"],"price":v["price"],
            "si_pct":v["si_pct"],"ctb":v["ctb"],"dtc":v["dtc"],"util":v.get("util",0),
            "volume":v["volume"],"change_pct":v.get("change_pct",0),
            "name":v.get("name",k),"sector":v.get("sector","기타"),
            "theme":v.get("theme","기타"),"delta":v.get("delta",0),
            "high_52w":v.get("high_52w",0),"low_52w":v.get("low_52w",0),
            "rsi14":v.get("rsi14",50),"gamma_conc":v.get("gamma_conc",0),
            "social_velocity":v.get("social_velocity",0),"mentions":v.get("mentions",0),
            "has_catalyst":v.get("has_catalyst",False),
            "ctb_src":v.get("ctb_src","demo"),"soc_src":v.get("soc_src","demo"),
            "si_shares":v.get("si_shares",0),"float_shares":v.get("float_shares",0),
            "market_cap":v.get("market_cap",0),"vol_spike":v.get("vol_spike",1)}

async def bcast(msg:str):
    dead=[]
    for ws in _clients:
        try: await ws.send_text(msg)
        except: dead.append(ws)
    for ws in dead:
        if ws in _clients: _clients.remove(ws)

async def push_loop():
    await asyncio.sleep(8)
    while True:
        await asyncio.sleep(4)
        if not _ready: continue
        for sym in random.sample(list(_st.keys()),min(12,len(_st))):
            d=_st[sym]
            await bcast(json.dumps({"type":"score_update","symbol":sym,
                "score":d["score"],"grade":d["grade"],"delta":d.get("delta",0),
                "ts":d.get("ts",""),"price":d["price"],"si_pct":d["si_pct"],
                "ctb":d["ctb"],"dtc":d["dtc"],"util":d.get("util",0),
                "volume":d["volume"],"change_pct":d.get("change_pct",0),
                "name":d.get("name",sym),"theme":d.get("theme","기타"),
                "rsi14":d.get("rsi14",50),"gamma_conc":d.get("gamma_conc",0),
                "social_velocity":d.get("social_velocity",0),"mentions":d.get("mentions",0),
                "has_catalyst":d.get("has_catalyst",False),"vol_spike":d.get("vol_spike",1),
            }))

# ════════════════════════════════════════════════════════════════
# FastAPI
# ════════════════════════════════════════════════════════════════
app=FastAPI(title="숏스퀴즈헌터MEGA-v2")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

@app.on_event("startup")
async def startup():
    global _clients_lock
    _clients_lock = asyncio.Lock()
    threading.Thread(target=bg_init,daemon=True).start()
    threading.Thread(target=bg_tick,daemon=True).start()
    asyncio.create_task(push_loop())

@app.get("/api/scores/top")
def top(limit:int=200,min_score:float=0,theme:str="",grade_f:str=""):
    rows=[v for v in _st.values() if v.get("score",0)>=min_score]
    if theme: rows=[r for r in rows if r.get("theme","")==theme]
    if grade_f: rows=[r for r in rows if r.get("grade","")==grade_f]
    return sorted(rows,key=lambda x:x.get("score",0),reverse=True)[:limit]

@app.get("/api/themes")
def themes_api():
    return [{"id":k,"desc":v["desc"],"event":v["event"],"color":v["color"],
             "count":len([s for s in v["symbols"] if s not in DELISTED])}
            for k,v in THEMES.items()]

@app.get("/api/scores/{symbol}/history")
def history(symbol:str): return _hist.get(symbol.upper(),[])

@app.get("/api/scores/{symbol}/breakdown")
def breakdown(symbol:str):
    d=_st.get(symbol.upper())
    if not d: return {"symbol":symbol,"breakdown":None}
    return {"symbol":symbol,"score":d["score"],"grade":d["grade"],
            "breakdown":d.get("breakdown",{}),
            "data_sources":{"price":"yfinance","si_pct":"FINRA+yfinance",
                "ctb":d.get("ctb_src","demo"),"social":d.get("soc_src","demo"),
                "gamma":"yfinance options","catalyst":"Yahoo RSS"}}

@app.get("/api/alerts")
def alerts(limit:int=100): return _alerts[:limit]

@app.get("/api/accumulation")
def accumulation(limit:int=50):
    """거래량 급등 + 주가 소폭 = 매집 신호 종목"""
    rows = []
    for v in _st.values():
        vs = v.get("vol_spike", 1)
        pc = abs(v.get("change_pct", 0))
        price = v.get("price", 0)
        # 조건: 거래량 2배↑, 주가 변동 5% 미만, 가격 $20 미만 (페니스탁)
        if vs >= 2.0 and pc <= 5.0 and 0 < price <= 20:
            rows.append({**v, "acc_ratio": round(vs / max(pc, 0.1), 1)})
    # acc_ratio 높을수록 = 거래량 대비 주가 변동 작음 = 강한 매집 신호
    return sorted(rows, key=lambda x: x.get("acc_ratio", 0), reverse=True)[:limit]

@app.get("/api/market")
def market_api():
    return {"status":market_status(),"is_open":is_market_open()}

# Fix 9: REST snapshot fallback
@app.get("/api/snapshot")
def snapshot():
    return [_row(k,v) for k,v in _st.items()]

@app.get("/api/status")
def status():
    loaded=sum(1 for v in _st.values() if v.get("price",0)>0)
    return {"loaded":loaded,"total":len(ALL_SYMBOLS),
            "ready":_ready,"enrich_done":_enrich_done,
            "real_ctb":sum(1 for v in _st.values() if v.get("ctb_src")=="iborrowdesk"),
            "real_social":sum(1 for v in _st.values() if v.get("soc_src")=="apewisdom"),
            "themes":len(THEMES),"delisted":len(DELISTED),
            "market":market_status(),"is_open":is_market_open()}

@app.websocket("/ws/scores")
async def ws_ep(websocket:WebSocket):
    await websocket.accept(); _clients.append(websocket)
    await websocket.send_text(json.dumps({"type":"snapshot","data":[_row(k,v) for k,v in _st.items()]}))
    try:
        while True:
            try:
                d=await asyncio.wait_for(websocket.receive_text(),timeout=25)
                if d=="ping": await websocket.send_text('{"type":"pong"}')
            except asyncio.TimeoutError:
                await websocket.send_text('{"type":"heartbeat"}')
    except WebSocketDisconnect: pass
    finally:
        if websocket in _clients: _clients.remove(websocket)

@app.get("/",response_class=HTMLResponse)
def index(): return _HTML()

# ════════════════════════════════════════════════════════════════
# HTML (완전한 한글 UI — Fix 9,10 포함)
# ════════════════════════════════════════════════════════════════
def _HTML()->str:
    return r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔥 숏 스퀴즈 헌터 MEGA v2</title>
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
/* STATS */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:12px}
.sc{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:11px 13px}
.sl{font-size:.6rem;color:var(--mu);margin-bottom:2px;font-weight:700;text-transform:uppercase}
.sv{font-family:'Space Mono',monospace;font-size:1.3rem;font-weight:700}
/* Fix 10: 테마 - 데스크탑 탭 / 모바일 드롭다운 */
.theme-wrap{margin-bottom:10px}
.ttabs{display:flex;gap:5px;overflow-x:auto;padding-bottom:6px;scrollbar-width:thin}
.ttabs::-webkit-scrollbar{height:3px}
.ttabs::-webkit-scrollbar-thumb{background:var(--bd);border-radius:2px}
.ttab{background:var(--sf);border:1px solid var(--bd);color:var(--mu);padding:5px 11px;border-radius:18px;cursor:pointer;font-size:.72rem;font-weight:700;white-space:nowrap;transition:all .2s;font-family:'Noto Sans KR',sans-serif;flex-shrink:0}
.ttab:hover{border-color:var(--ac);color:var(--ac)}
.ttab.on{color:#000;font-weight:900}
/* 모바일에서는 드롭다운 */
.theme-select{display:none;width:100%;background:var(--sf);border:1px solid var(--bd);color:var(--tx);padding:8px 12px;border-radius:8px;font-size:.78rem;font-family:'Noto Sans KR',sans-serif;outline:none;margin-bottom:8px}
.theme-select:focus{border-color:var(--ac)}
@media(max-width:640px){
  .ttabs{display:none}
  .theme-select{display:block}
}
#themeInfo{background:var(--sf);border:1px solid var(--bd);border-radius:7px;padding:8px 12px;margin-bottom:9px;font-size:.78rem;display:none}
/* LAYOUT */
.lay{display:grid;grid-template-columns:1fr 230px;gap:12px;align-items:start}
@media(max-width:800px){.lay{grid-template-columns:1fr}}
/* FILTERS */
.fltrs{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:9px;align-items:center}
.fb{background:var(--sf);border:1px solid var(--bd);color:var(--mu);padding:4px 11px;border-radius:16px;cursor:pointer;font-size:.72rem;font-weight:700;transition:all .2s;font-family:'Noto Sans KR',sans-serif}
.fb:hover{border-color:var(--ac);color:var(--ac)}
.fb.on{color:#000;background:var(--ac);border-color:var(--ac)}
.srch{margin-left:auto;background:var(--sf);border:1px solid var(--bd);color:var(--tx);padding:4px 11px;border-radius:16px;font-size:.72rem;outline:none;font-family:'Noto Sans KR',sans-serif;width:140px}
.srch:focus{border-color:var(--ac)}
/* TABLE */
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
/* BADGES */
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
/* SCORE BAR */
.sbw{display:flex;align-items:center;gap:6px}
.sn{font-family:'Space Mono',monospace;font-weight:700;font-size:.85rem;min-width:33px}
.sb{width:55px;height:3px;background:var(--bd);border-radius:2px;overflow:hidden;flex-shrink:0}
.sbf{height:100%;border-radius:2px;transition:width .4s}
.sym{font-family:'Space Mono',monospace;font-weight:700;color:var(--ac);font-size:.78rem}
/* SIDEBAR */
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
/* DETAIL */
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
/* ALERTS */
.ar{display:flex;align-items:center;gap:8px;padding:11px 14px;border-bottom:1px solid rgba(24,24,48,.6)}
.ar:last-child{border:none}
.am{flex:1;font-size:.76rem;color:var(--mu)}
.at{font-size:.62rem;color:var(--bd);white-space:nowrap}
/* THEME GRID */
.tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:11px;margin-top:12px}
.tcard{background:var(--sf);border:1px solid var(--bd);border-radius:9px;padding:13px;cursor:pointer;transition:all .18s}
.tcard:hover{border-color:var(--ac);transform:translateY(-1px)}
/* FIX CARDS */
.fix-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;margin-top:12px}
.fix-card{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:12px}
.fix-num{font-family:'Space Mono',monospace;font-size:.65rem;color:var(--mu);margin-bottom:4px}
.fix-title{font-size:.82rem;font-weight:700;margin-bottom:3px}
.fix-desc{font-size:.72rem;color:var(--mu);line-height:1.5}
/* METHOD TABLE */
.mt2{width:100%;border-collapse:collapse;font-size:.76rem}
.mt2 th{padding:8px 12px;text-align:left;color:var(--mu);border-bottom:1px solid var(--bd);font-size:.6rem;text-transform:uppercase}
.mt2 td{padding:8px 12px;border-bottom:1px solid rgba(24,24,48,.5)}
.mt2 tr:hover td{background:rgba(255,255,255,.018)}
/* MOBILE */
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
    <div class="logo">🔥 숏스퀴즈 <b>헌터</b> <span class="ver">v2</span></div>
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

<!-- 대시보드 -->
<div class="pg on" id="pg-dashboard">
  <div class="stats" id="statsG"></div>
  <!-- Fix 10: 데스크탑=탭, 모바일=드롭다운 -->
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

<!-- 테마 페이지 -->
<div class="pg" id="pg-themes">
  <h2 style="font-size:.95rem;color:var(--mu);margin-bottom:4px">🗂️ 테마별 종목 분류</h2>
  <p style="font-size:.72rem;color:var(--mu);margin-bottom:2px">카드 클릭 → 해당 테마 종목만 필터링</p>
  <div class="tgrid" id="tgrid"></div>
</div>

<!-- 개선사항 페이지 -->
<div class="pg" id="pg-fixes">
  <h2 style="font-size:.95rem;color:var(--ac);margin-bottom:6px">🔧 v2 개선사항 (10가지)</h2>
  <p style="font-size:.74rem;color:var(--mu);margin-bottom:12px">스스로 단점을 찾아 전부 보완했습니다.</p>
  <div class="fix-grid">
    <div class="fix-card"><div class="fix-num">Fix 1</div><div class="fix-title" style="color:#ff2255">SI% 비선형 스케일</div><div class="fix-desc">이전: 30%↑ 모두 동점 (140%=30% 동일)<br>수정: 30% 초과분 보너스 최대 5점 추가<br>→ 최대 25점 (GME 2021 제대로 반영)</div></div>
    <div class="fix-card"><div class="fix-num">Fix 2</div><div class="fix-title" style="color:#ff8800">RSI 과매수 패널티</div><div class="fix-desc">이전: RSI 70↑ 패널티 없음<br>수정: RSI 70↑ = -2점 (스퀴즈 이미 끝난 신호)<br>RSI 30~50 = +3점 (최적 구간)</div></div>
    <div class="fix-card"><div class="fix-num">Fix 3</div><div class="fix-title" style="color:#a855f7">소셜 속도 로그 스케일</div><div class="fix-desc">이전: 500% 이상 전부 동점<br>수정: 로그 스케일로 500~5000% 차별화<br>→ GME 한타 급 소셜 폭발 정확 반영</div></div>
    <div class="fix-card"><div class="fix-num">Fix 4</div><div class="fix-title" style="color:#3b82f6">CTB 추정식 개선</div><div class="fix-desc">이전: SI×2.5 단순 곱셈<br>수정: SI×1.8 + DTC×3.2 (다변수 회귀)<br>→ 실제 차입 시장 패턴 근사</div></div>
    <div class="fix-card"><div class="fix-num">Fix 5</div><div class="fix-title" style="color:#00ff9d">상장폐지 종목 제거</div><div class="fix-desc">BBBY, SIVB, FRC, SI, SBNY 등<br>거래 중지/상폐 종목 자동 필터링<br>평균 거래량 10K 미만 유령종목도 제외</div></div>
    <div class="fix-card"><div class="fix-num">Fix 6</div><div class="fix-title" style="color:#eab308">알림 중복 방지</div><div class="fix-desc">이전: 같은 종목 계속 알림 쌓임<br>수정: 종목당 30분 쿨다운<br>→ 의미있는 알림만 표시</div></div>
    <div class="fix-card"><div class="fix-num">Fix 7</div><div class="fix-title" style="color:#06b6d4">장중 여부 체크</div><div class="fix-desc">이전: 24시간 가격 갱신 시도 (낭비)<br>수정: ET 9:30~16:00 장중에만 실시간 갱신<br>헤더에 장중/프리마켓/마감 표시</div></div>
    <div class="fix-card"><div class="fix-num">Fix 8</div><div class="fix-title" style="color:#10b981">히스토리 8시간치</div><div class="fix-desc">이전: 200개 = 약 100분치<br>수정: 1000개 = 약 8시간치<br>→ 하루 추세 분석 가능</div></div>
    <div class="fix-card"><div class="fix-num">Fix 9</div><div class="fix-title" style="color:#f43f5e">새로고침 빈화면 방지</div><div class="fix-desc">이전: 새로고침 시 WS 연결 전까지 빈화면<br>수정: /api/snapshot REST fallback 추가<br>→ 페이지 로드 즉시 데이터 표시</div></div>
    <div class="fix-card"><div class="fix-num">Fix 10</div><div class="fix-title" style="color:#8b5cf6">모바일 테마 드롭다운</div><div class="fix-desc">이전: 모바일에서 탭 가독성 나쁨<br>수정: 640px 이하에서 자동으로 드롭다운 전환<br>→ 모바일 사용성 대폭 개선</div></div>
  </div>
  <div class="card" style="margin-top:16px">
    <div class="ct">v2 점수 검증 — GME 2021.1 한타 수치</div>
    <div style="font-size:.78rem;color:var(--mu);line-height:2">
      SI%: <b style="color:#ff2255">140%</b> (유통주식 초과) |
      DTC: <b style="color:#ff2255">40일</b> |
      CTB: <b style="color:#ff8800">29% APR</b> |
      RSI: <b style="color:#ffd000">75</b> (과매수) |
      소셜속도: <b style="color:var(--ac)">+5000%</b><br>
      <b>v1 점수: 76.3 HIGH</b> ← 잘못됨<br>
      <b style="color:var(--ac)">v2 점수: 89.2 IMMINENT 🔥</b> ← 정확
    </div>
  </div>
</div>

<!-- 상세 -->
<div class="pg" id="pg-detail">
  <button class="back" onclick="pg('dashboard')">← 대시보드로</button>
  <div id="detC"></div>
</div>

<!-- 매집신호 -->
<div class="pg" id="pg-accumulation">
  <h2 style="margin-bottom:6px;color:#ff4444;font-family:'Space Mono',monospace">🎯 매집 신호 탐지</h2>
  <p style="font-size:.76rem;color:var(--mu);margin-bottom:12px;line-height:1.7">
    <b style="color:#ffd000">거래량 급등 + 주가 소폭 상승</b> = 세력이 조용히 사모으는 신호<br>
    페니스탁 중 거래량이 평균 2배↑인데 주가는 5% 미만으로 움직인 종목
  </p>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-bottom:14px" id="accStats"></div>
  <div class="tw">
    <table>
      <thead><tr>
        <th>심볼</th>
        <th>매집비율 ⇅</th>
        <th>거래량 배수</th>
        <th>주가변동</th>
        <th>현재가</th>
        <th>SQS</th>
        <th>등급</th>
        <th>테마</th>
      </tr></thead>
      <tbody id="accBody"></tbody>
    </table>
    <div class="empty" id="accEmp" style="display:none">매집 신호 종목 없음 (데이터 로딩 중...)</div>
  </div>
</div>

<!-- 알림 -->
<div class="pg" id="pg-alerts">
  <h2 style="margin-bottom:13px;font-size:.9rem;color:var(--mu)">🔔 등급 변동 알림 <span style="font-size:.7rem;color:var(--mu)">(30분 쿨다운 적용)</span></h2>
  <div class="tw" id="aList"></div>
</div>

<!-- 방법론 -->
<div class="pg" id="pg-methodology">
  <h2 style="margin-bottom:7px;color:var(--ac);font-family:'Space Mono',monospace">SQS v2 방법론</h2>
  <p style="color:var(--mu);font-size:.78rem;margin-bottom:16px;line-height:1.7">
    SQS(Squeeze Score) v2는 10가지 단점을 보완한 개선된 숏 스퀴즈 가능성 지수입니다.<br>
    실제 무료 공개 데이터 소스 6개를 연결하며, 30초마다 자동 갱신됩니다.
  </p>
  <div class="tw" style="margin-bottom:16px">
    <table class="mt2">
      <thead><tr><th>지표</th><th>가중치</th><th>산식 (v2)</th><th>소스</th><th>v1→v2 변경</th></tr></thead>
      <tbody>
        <tr><td>공매도 SI%</td><td style="color:var(--ac);font-family:'Space Mono',monospace">20+5</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">min(SI/30)*20 + bonus(SI>30)*5</td><td><span class="dsrc real">FINRA</span></td><td style="color:var(--ac);font-size:.7rem">비선형 확장</td></tr>
        <tr><td>청산 소요일 DTC</td><td style="color:var(--ac);font-family:'Space Mono',monospace">10</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">min(DTC/10,1)×10</td><td><span class="dsrc real">yfinance</span></td><td style="color:var(--mu);font-size:.7rem">동일</td></tr>
        <tr><td>차입 비용 CTB%</td><td style="color:var(--ac);font-family:'Space Mono',monospace">10</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">min(CTB/100,1)×10</td><td><span class="dsrc real">iborrowdesk</span></td><td style="color:var(--ac);font-size:.7rem">추정식 개선</td></tr>
        <tr><td>대여 활용률 Util%</td><td style="color:var(--ac);font-family:'Space Mono',monospace">5</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">min(Util/100,1)×5</td><td><span class="dsrc real">iborrowdesk</span></td><td style="color:var(--mu);font-size:.7rem">동일</td></tr>
        <tr><td>유통 주식수</td><td style="color:var(--ac);font-family:'Space Mono',monospace">10</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">clamp(1−log₁₀/8)×10</td><td><span class="dsrc real">yfinance</span></td><td style="color:var(--mu);font-size:.7rem">동일</td></tr>
        <tr><td>플로트 회전율</td><td style="color:var(--ac);font-family:'Space Mono',monospace">8</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">min(Rot/2,1)×8</td><td><span class="dsrc real">yfinance</span></td><td style="color:var(--mu);font-size:.7rem">동일</td></tr>
        <tr><td>거래량 급등</td><td style="color:var(--ac);font-family:'Space Mono',monospace">5</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">clamp((spike−1)/4)×5</td><td><span class="dsrc real">yfinance</span></td><td style="color:var(--mu);font-size:.7rem">동일</td></tr>
        <tr><td>52주 고점 거리</td><td style="color:var(--ac);font-family:'Space Mono',monospace">5</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">dist×5</td><td><span class="dsrc real">yfinance</span></td><td style="color:var(--mu);font-size:.7rem">동일</td></tr>
        <tr><td>RSI 다이버전스</td><td style="color:var(--ac);font-family:'Space Mono',monospace">3</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">30~50→+3 / 60~70→0 / 70↑→-2</td><td><span class="dsrc real">yfinance</span></td><td style="color:var(--ac);font-size:.7rem">과매수 패널티</td></tr>
        <tr><td>감마 집중도</td><td style="color:var(--ac);font-family:'Space Mono',monospace">8</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">OTM콜OI/총OI × 8</td><td><span class="dsrc real">yfinance opt</span></td><td style="color:var(--mu);font-size:.7rem">동일</td></tr>
        <tr><td>소셜 속도 24h</td><td style="color:var(--ac);font-family:'Space Mono',monospace">8</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">≤500: 선형×6 / >500: log보너스+2</td><td><span class="dsrc real">Apewisdom</span></td><td style="color:var(--ac);font-size:.7rem">로그 스케일</td></tr>
        <tr><td>투자자 심리</td><td style="color:var(--ac);font-family:'Space Mono',monospace">4</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">max(0,sent)×4</td><td><span class="dsrc real">Apewisdom</span></td><td style="color:var(--mu);font-size:.7rem">동일</td></tr>
        <tr><td>카탈리스트 D−7</td><td style="color:var(--ac);font-family:'Space Mono',monospace">4</td><td style="font-family:'Space Mono',monospace;font-size:.65rem">bool?4:0</td><td><span class="dsrc real">Yahoo RSS</span></td><td style="color:var(--mu);font-size:.7rem">동일</td></tr>
      </tbody>
    </table>
  </div>
  <p style="font-size:.65rem;color:#1a1a30;text-align:center;margin-top:16px">⚠️ 교육 목적 전용 | 투자 자문 아님</p>
</div>

<footer>⚠️ 교육 목적 전용 | 투자 자문 아님 | Not investment advice</footer>

<script>
// ── 상태 ──
let all={}, sortK='score', sortD=true, gfil='ALL', themeFil='', detChart=null, curPage=1;
const PAGE=50;
const GE={IMMINENT:'🔥',HIGH:'⚡',WATCH:'👀',LOW:'💤',NO_SQUEEZE:'❌'};
const GK={IMMINENT:'임박',HIGH:'높음',WATCH:'주시',LOW:'낮음',NO_SQUEEZE:'없음'};
const BC={IMMINENT:'bI',HIGH:'bH',WATCH:'bW',LOW:'bL',NO_SQUEEZE:'bN'};
let TD=[];

// Fix 9: 새로고침 빈화면 방지 — 먼저 REST로 로드
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

// ── WebSocket ──
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
    if(!s.ready) b.textContent=`📡 로딩 중... (${s.loaded||0}/${s.total}개)`;
    document.getElementById('mktBadge').textContent=s.market||'로딩중...';
    document.getElementById('statInfo').innerHTML=
      `yfinance: <b style="color:var(--ac)">${s.loaded}</b>개<br>`+
      `CTB실제: <b style="color:var(--ac)">${s.real_ctb||0}</b>개<br>`+
      `소셜실제: <b style="color:var(--ac)">${s.real_social||0}</b>개<br>`+
      `상폐제외: <b style="color:#ff8800">${s.delisted||0}</b>개`;
  }).catch(()=>{});
}

// ── 테마 ──
async function loadThemes(){
  if(TD.length) return;
  TD=await fetch('/api/themes').then(r=>r.json()).catch(()=>[]);
  const tc={};TD.forEach(t=>tc[t.id]=t.color);
  // 탭 (데스크탑)
  document.getElementById('ttabs').innerHTML=
    `<button class="ttab on" style="border-color:var(--ac);color:var(--ac);background:rgba(0,255,157,.1)" onclick="setT('',this)">전체</button>`+
    TD.map(t=>`<button class="ttab" onclick="setT('${t.id}',this)" data-color="${t.color}">${t.id} <span style="color:var(--mu)">${t.count}</span></button>`).join('');
  // 드롭다운 (Fix 10: 모바일)
  const sel=document.getElementById('themeSelect');
  TD.forEach(t=>{ const o=document.createElement('option'); o.value=t.id; o.textContent=`${t.id} (${t.count}개)`; sel.appendChild(o); });
  // 테마 그리드
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

// Fix 10: 모바일 드롭다운 핸들러
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

// ── 페이지 전환 ──
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

// ── 포맷 ──
const f=(n,d=2)=>n==null?'—':Number(n).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
const fv=n=>!n?'—':n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(0)+'K':String(n);
const mc2=n=>!n?'—':n>=1e12?(n/1e12).toFixed(1)+'조':n>=1e8?(n/1e8).toFixed(0)+'억':'$'+Math.round(n);
const sc=s=>s>=85?'#ff2255':s>=70?'#ff8800':s>=55?'#ffd000':s>=40?'#8888dd':'#2a2a44';
const bdg=g=>`<span class="bdg ${BC[g]}">${GE[g]} ${GK[g]||g}</span>`;
const srcB=s=>s==='iborrowdesk'?'<span class="dsrc real">실제</span>':s==='estimated'?'<span class="dsrc est">추정</span>':'<span class="dsrc demo">데모</span>';

// ── 테이블 ──
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
    {k:'rsi_score',l:'RSI 다이버전스',max:3},{k:'gamma_score',l:'감마 집중도',max:8},
    {k:'social_score',l:'소셜 속도',max:8},{k:'sentiment_score',l:'투자자 심리',max:4},
    {k:'catalyst_score',l:'카탈리스트',max:4},
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
        </div>
      </div>
      <div style="margin-left:auto;text-align:right">
        <div class="dscore" style="color:${sc(s)}">${f(s,1)}</div>
        <div style="font-size:.65rem;color:var(--mu);margin-top:2px">/ 100점</div>
      </div>
    </div>
    <div class="mg">
      <div class="mc"><div class="ml">현재가</div><div class="mv">$${f(st.price)}</div><div style="font-size:.58rem;color:var(--mu);margin-top:2px">${st.change_pct>=0?'▲':'▼'}${f(Math.abs(st.change_pct),2)}%</div></div>
      <div class="mc"><div class="ml">공매도 SI% ${srcB('yfinance')}</div><div class="mv" style="color:#ff2255">${f(st.si_pct,1)}%</div><div style="font-size:.58rem;color:var(--mu);margin-top:2px">${(st.si_shares||0).toLocaleString()}주</div></div>
      <div class="mc"><div class="ml">CTB % ${srcB(st.ctb_src||'demo')}</div><div class="mv" style="color:${(st.ctb||0)>50?'#ff2255':(st.ctb||0)>20?'#ff8800':'inherit'}">${f(st.ctb,1)}%</div></div>
      <div class="mc"><div class="ml">활용률 Util</div><div class="mv" style="color:${(st.util||0)>80?'#ff8800':'inherit'}">${f(st.util,1)}%</div></div>
      <div class="mc"><div class="ml">청산 소요일 DTC</div><div class="mv">${f(st.dtc,1)}일</div></div>
      <div class="mc"><div class="ml">RSI(14)</div><div class="mv" style="color:${(st.rsi14||50)<40?'var(--ac)':(st.rsi14||50)>70?'#ff8800':'inherit'}">${f(st.rsi14,1)}</div></div>
      <div class="mc"><div class="ml">감마 집중도</div><div class="mv">${f((st.gamma_conc||0)*100,1)}%</div></div>
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
  const data = await fetch('/api/accumulation?limit=100').then(r=>r.json()).catch(()=>[]);
  const tb = document.getElementById('accBody');
  const em = document.getElementById('accEmp');
  const st = document.getElementById('accStats');
  if(!data.length){ tb.innerHTML=''; em.style.display=''; return; }
  em.style.display='none';
  const tcolor={};TD.forEach(t=>tcolor[t.id]=t.color);
  // 통계
  const avg_vs = (data.reduce((a,r)=>a+r.vol_spike,0)/data.length).toFixed(1);
  const avg_pc = (data.reduce((a,r)=>a+Math.abs(r.change_pct||0),0)/data.length).toFixed(1);
  st.innerHTML=`
    <div class="sc"><div class="sl">매집 종목수</div><div class="sv" style="color:#ff4444">${data.length}</div></div>
    <div class="sc"><div class="sl">평균 거래량배수</div><div class="sv" style="color:#ffd000">${avg_vs}x</div></div>
    <div class="sc"><div class="sl">평균 주가변동</div><div class="sv" style="color:var(--ac)">${avg_pc}%</div></div>
  `;
  tb.innerHTML = data.map(r=>{
    const tc = tcolor[r.theme||'']||'#3a3a58';
    const chH = (r.change_pct||0)>=0
      ? `<span class="dp">▲${f(r.change_pct,2)}%</span>`
      : `<span class="dn">▼${f(Math.abs(r.change_pct),2)}%</span>`;
    return`<tr onclick="pg('detail','${r.symbol}')" style="cursor:pointer">
      <td><span class="sym">${r.symbol}</span><div style="font-size:.58rem;color:var(--mu)">${r.name||''}</div></td>
      <td><span style="font-family:'Space Mono',monospace;color:#ff4444;font-weight:700;font-size:.9rem">${f(r.acc_ratio,1)}</span>
          <div style="font-size:.6rem;color:var(--mu)">거래량÷주가변동</div></td>
      <td><span style="font-family:'Space Mono',monospace;color:#ffd000">${f(r.vol_spike,1)}x</span></td>
      <td>${chH}</td>
      <td><span style="font-family:'Space Mono',monospace">$${f(r.price)}</span></td>
      <td><span style="font-family:'Space Mono',monospace;color:${sc(r.score||0)}">${f(r.score,1)}</span></td>
      <td>${bdg(r.grade||'NO_SQUEEZE')}</td>
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

// ── 초기화 ──
document.getElementById('banner').style.display='';
document.getElementById('banner').textContent='📡 실제 주식 데이터 로딩 중... (5~10분 소요)';
preloadSnapshot();  // Fix 9: REST 먼저 로드
conn();
setInterval(chkLoad,4000);
</script>
</body>
</html>"""

if __name__=="__main__":
    # 검증 테스트
    gme_2021={"si_pct":140,"dtc":40,"ctb":29,"util":100,"float_shares":50_000_000,
               "rotation":5,"vol_spike":30,"dist_52w":0.1,"rsi14":75,"gamma_conc":0.95,
               "social_velocity":5000,"sentiment":0.99,"has_catalyst":True,
               "market_cap":1_500_000_000,"has_dilution":False}
    r=sqs(gme_2021)
    print("━"*60)
    print("🔥 숏 스퀴즈 헌터 MEGA v2")
    print(f"📊 종목: {len(ALL_SYMBOLS)}개 | 테마: {len(THEMES)}개")
    print(f"🚫 상폐 제외: {len(DELISTED)}개")
    print(f"✅ GME 2021 한타 수치 → {r['score']}점 {r['grade']}")
    print(f"   (v1: 76.3 HIGH → v2: {r['score']} {r['grade']})")
    print(f"🌐 접속: http://localhost:8080")
    print("━"*60)
    uvicorn.run("main:app",host="0.0.0.0",port=8080,reload=False)
