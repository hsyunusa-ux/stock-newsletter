"""Stock Newsletter Configuration"""

# 투자 종목 티커 목록
TICKERS = [
    "AMZN", "TSLA", "NFLX", "UNH", "INTC",
    "QCOM", "RDDT", "SOFI", "JOBY", "RBRK",
    "BMNR", "OPEN", "TMDX", "ROOT",
]

# 뉴스레터 수신 이메일 (Gmail MCP로 발송)
# Gmail MCP는 인증된 계정에서 자기 자신에게 발송
NEWSLETTER_SUBJECT = "Daily Stock Newsletter"
