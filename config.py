"""Stock Newsletter Configuration"""

# Google Drive 포트폴리오 설정
GOOGLE_DRIVE_FILE_ID = "15GSpPWQ4ePvRUb9yuG5GmK3T6z6oo97m"
GOOGLE_CREDENTIALS_PATH = "../stock-portfolio/credentials.json"  # 서비스 계정 키

# 제외할 티커 (현금, 상폐, 뮤추얼펀드 등)
EXCLUDE_TICKERS = {"CASH", "NBEVQ", "BGSAX", "LBSAX"}

# 폴백용 티커 (Google Drive 접속 실패 시 사용)
FALLBACK_TICKERS = [
    "AMZN", "TSLA", "NFLX", "UNH", "INTC",
    "QCOM", "RDDT", "SOFI", "JOBY", "RBRK",
    "BMNR", "OPEN", "TMDX", "ROOT",
]

NEWSLETTER_SUBJECT = "Daily Stock Newsletter"
