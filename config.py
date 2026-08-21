"""Stock Newsletter Configuration"""

# Webull 보유종목 조회 (auto-trader의 공식 OpenAPI 재사용) — 티커 1순위 소스
AUTO_TRADER_DIR = "/Users/hyunsikyun/auto-trader"
AUTO_TRADER_PYTHON = "/Users/hyunsikyun/auto-trader/.venv/bin/python3"

# Google Sheets 공개 URL (Overview 시트 - Total Portfolio 섹션) — Webull 실패 시 폴백
SHEET_ID  = "15GSpPWQ4ePvRUb9yuG5GmK3T6z6oo97m"
SHEET_GID = "1170127351"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

# 제외할 티커 (현금, 상폐, 헤더 등)
EXCLUDE_TICKERS = {"CASH", "NBEVQ", "BGSAX", "LBSAX", "TICKER", "TOTAL"}

# 폴백용 티커 (Webull과 Google Sheets 모두 실패 시 사용)
FALLBACK_TICKERS = [
    "AMZN", "TSLA", "NFLX", "UNH", "INTC",
    "QCOM", "RDDT", "SOFI", "JOBY", "RBRK",
    "BMNR", "OPEN", "TMDX", "ROOT",
]

NEWSLETTER_SUBJECT = "Daily Stock Newsletter"
