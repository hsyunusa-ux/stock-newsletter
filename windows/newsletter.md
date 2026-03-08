매일 아침 투자 종목 뉴스레터를 생성하고 Gmail로 발송합니다.

아래 명령어를 실행해주세요.

```bash
cd %USERPROFILE%\stock-newsletter && python send_email.py
```

실행이 완료되면:

1. 생성된 HTML 파일을 `%USERPROFILE%\stock-newsletter\output\` 에서 확인
2. 브라우저로 열어서 미리보기

뉴스레터 포함 내용:
- Market Summary (S&P500, NASDAQ, DOW, VIX)
- Portfolio Summary (평균 등락, Best/Worst, 섹터 분류)
- Price & Valuation Table (가격, P/E, Fwd P/E, Target, RSI, MA50)
- 종목별 상세 카드 (재무, 기술지표, 배당/공매도)
- Claude Sonnet AI 뉴스 분석 (기사 전문 읽기 → 한글 핵심 요약 + 호재/악재 + 주목 포인트)
- 뉴스 원문 링크

종목: AMZN, TSLA, NFLX, UNH, INTC, QCOM, RDDT, SOFI, JOBY, RBRK, BMNR, OPEN, TMDX, ROOT

결과를 한국어로 알려주세요.
