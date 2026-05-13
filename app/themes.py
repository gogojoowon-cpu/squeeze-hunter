"""SIC 코드 기반 테마 자동 분류"""

THEMES = {
    "🔥 밈주식":             {"desc": "Reddit/SNS 주도 공매도 스퀴즈", "event": "2021.1 GameStop 한타", "color": "#ff2255"},
    "₿ 암호화폐·블록체인":    {"desc": "BTC/ETH 연동 채굴·거래소",     "event": "2021 불장 / 2022 FTX 붕괴",  "color": "#f7931a"},
    "⚡ EV·전기차":          {"desc": "전기차·자율주행·충전",         "event": "2020~21 EV 버블",          "color": "#00d4aa"},
    "🦠 코로나·바이오 특수":  {"desc": "팬데믹 수혜·백신",            "event": "2020~22 코로나19",          "color": "#00ff9d"},
    "🪖 방산·전쟁·지정학":    {"desc": "전쟁·분쟁·방위산업",          "event": "2022 러-우 전쟁",          "color": "#ff8800"},
    "🤖 AI·반도체":          {"desc": "AI·GPU·파운드리",            "event": "2023 ChatGPT / 엔비디아 1조",  "color": "#a855f7"},
    "💊 바이오·헬스케어":     {"desc": "임상·FDA·유전자치료",         "event": "mRNA 혁명 / GLP-1 비만치료",   "color": "#ec4899"},
    "💳 핀테크·결제":        {"desc": "디지털결제·네오뱅크",          "event": "2021 SPAC 붐",             "color": "#3b82f6"},
    "🌐 메타버스·게임":       {"desc": "게임·VR·메타버스",            "event": "2021 META 리브랜딩",         "color": "#8b5cf6"},
    "☀️ 신재생·수소·원자력":  {"desc": "태양광·풍력·수소·원자력",      "event": "IRA 법안 / 에너지전환",       "color": "#eab308"},
    "🛢️ 에너지·원자재":      {"desc": "유가·천연가스·금속",           "event": "2022 에너지 쇼크",           "color": "#78716c"},
    "📱 소셜·스트리밍·이커머스":{"desc": "SNS·이커머스·OTT",          "event": "팬데믹 비대면",             "color": "#06b6d4"},
    "⚕️ 의료기기·디지털헬스":  {"desc": "의료기기·원격진료",           "event": "코로나 진단키트 / CGM",      "color": "#10b981"},
    "💥 페니스탁·급등후보":    {"desc": "저가 소형주 — 폭발적 급등",    "event": "플로트 小 + 공매도 高",       "color": "#ff4444"},
    "🏦 S&P500 핵심":        {"desc": "미국 대표 500대 기업",         "event": "공매도 적지만 전제조건 모니터링",  "color": "#64748b"},
}

# SIC 코드 → 테마 매핑
_SIC_MAP = [
    (range(3674, 3675), "🤖 AI·반도체"),
    (range(7372, 7375), "🤖 AI·반도체"),
    (range(3672, 3673), "🤖 AI·반도체"),
    (range(2836, 2837), "💊 바이오·헬스케어"),
    (range(8000, 8100), "💊 바이오·헬스케어"),
    (range(2830, 2836), "💊 바이오·헬스케어"),
    (range(3841, 3852), "⚕️ 의료기기·디지털헬스"),
    (range(1311, 1390), "🛢️ 에너지·원자재"),
    (range(1400, 1500), "🛢️ 에너지·원자재"),
    (range(4911, 4940), "☀️ 신재생·수소·원자력"),
    (range(6000, 6300), "💳 핀테크·결제"),
    (range(6300, 6400), "💳 핀테크·결제"),
    (range(4800, 4900), "📱 소셜·스트리밍·이커머스"),
    (range(7810, 7820), "🌐 메타버스·게임"),
    (range(7990, 7998), "🌐 메타버스·게임"),
    (range(3760, 3770), "🪖 방산·전쟁·지정학"),
    (range(3812, 3813), "🪖 방산·전쟁·지정학"),
    (range(3711, 3717), "⚡ EV·전기차"),
    (range(3559, 3560), "⚡ EV·전기차"),
]


def classify_theme(sic: int, name: str, price: float) -> str:
    """이름 키워드 → SIC → 가격 순으로 분류"""
    nm = (name or "").upper()
    if any(k in nm for k in ["BITCOIN", "CRYPTO", "BLOCKCHAIN", "MINING", "MINER"]):
        return "₿ 암호화폐·블록체인"
    if any(k in nm for k in ["ELECTRIC VEH", "CHARGING", "EV ", "AUTONOMOUS"]):
        return "⚡ EV·전기차"
    if any(k in nm for k in ["THERAPEUTICS", "BIOSCIENCE", "BIOTECH", "GENOMIC", "ONCOLOGY"]):
        return "💊 바이오·헬스케어"
    if any(k in nm for k in ["DEFENSE", "AEROSPACE", "DRONE", "MILITARY"]):
        return "🪖 방산·전쟁·지정학"
    if any(k in nm for k in ["SOLAR", "WIND", "HYDROGEN", "NUCLEAR", "RENEWABLE"]):
        return "☀️ 신재생·수소·원자력"
    if any(k in nm for k in ["ARTIFICIAL INTEL", "SEMICONDUCTOR", "QUANTUM"]):
        return "🤖 AI·반도체"

    if sic:
        for rng, theme in _SIC_MAP:
            if sic in rng:
                return theme

    if 0 < price <= 5:
        return "💥 페니스탁·급등후보"
    return "🏦 S&P500 핵심"
