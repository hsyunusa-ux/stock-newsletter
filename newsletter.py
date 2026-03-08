#!/usr/bin/env python3
"""Stock Newsletter Generator v2 - Premium Daily Report"""

import os
import yfinance as yf
import pandas as pd
import anthropic
from datetime import datetime, timedelta
from config import TICKERS, NEWSLETTER_SUBJECT

# .env 파일에서 환경변수 로드
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()


def calc_rsi(prices, period=14):
    """RSI 계산"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).iloc[-1]


def get_stock_data(ticker_symbol):
    """종목의 전체 데이터 수집: 가격, 밸류에이션, 재무, 기술적 지표"""
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info

        if not info or info.get("regularMarketPrice") is None:
            return None

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

        change_pct = None
        if current_price and previous_close and previous_close != 0:
            change_pct = ((current_price - previous_close) / previous_close) * 100

        # 기술적 지표: 50일/200일 이동평균, RSI
        ma50 = info.get("fiftyDayAverage")
        ma200 = info.get("twoHundredDayAverage")

        # RSI 계산 (최근 30일 데이터로)
        rsi = None
        try:
            hist = stock.history(period="1mo")
            if len(hist) >= 15:
                rsi = round(calc_rsi(hist["Close"]), 1)
        except Exception:
            pass

        # 재무 데이터
        revenue_growth = info.get("revenueGrowth")  # YoY
        earnings_growth = info.get("earningsGrowth")  # YoY
        eps_trailing = info.get("trailingEps")
        eps_forward = info.get("forwardEps")
        revenue = info.get("totalRevenue")

        # 배당
        dividend_yield = info.get("dividendYield")

        # 공매도
        short_ratio = info.get("shortRatio")
        short_pct_float = info.get("shortPercentOfFloat")

        # 섹터/산업
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")

        return {
            "ticker": ticker_symbol,
            "name": info.get("shortName") or info.get("longName") or ticker_symbol,
            "current_price": current_price,
            "previous_close": previous_close,
            "change_pct": change_pct,
            # Valuation
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            # Analyst
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "target_mean": info.get("targetMeanPrice"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
            "recommendation": info.get("recommendationKey"),
            # Range
            "fifty_two_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_low": info.get("fiftyTwoWeekLow"),
            "market_cap": info.get("marketCap"),
            # Technical
            "ma50": ma50,
            "ma200": ma200,
            "rsi": rsi,
            # Financials
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "eps_trailing": eps_trailing,
            "eps_forward": eps_forward,
            "revenue": revenue,
            # Dividend & Short
            "dividend_yield": dividend_yield,
            "short_ratio": short_ratio,
            "short_pct_float": short_pct_float,
            # Classification
            "sector": sector,
            "industry": industry,
        }
    except Exception as e:
        print(f"[ERROR] {ticker_symbol}: {e}")
        return None


def fetch_article_text(url, timeout=10):
    """뉴스 기사 URL에서 본문 텍스트 추출"""
    if not url:
        return ""
    try:
        from newspaper import Article
        article = Article(url)
        article.download()
        article.parse()
        text = article.text
        # 너무 긴 경우 앞부분만 (토큰 절약)
        if len(text) > 3000:
            text = text[:3000] + "..."
        return text
    except Exception as e:
        print(f"    [FETCH SKIP] {url[:60]}... ({e})")
        return ""


def analyze_news_with_ai(all_news_data):
    """Claude Sonnet으로 기사 전문을 읽고 종목별 한글 분석"""
    if not all_news_data:
        return {}

    # 기사 본문 수집
    print("    Fetching article full texts...")
    news_with_text = {}
    for ticker, articles in all_news_data.items():
        news_with_text[ticker] = []
        for a in articles[:3]:  # 종목당 최대 3개 기사
            print(f"    [{ticker}] {a['title'][:50]}...")
            body = fetch_article_text(a.get("link", ""))
            news_with_text[ticker].append({
                "title": a["title"],
                "publisher": a["publisher"],
                "body": body if body else "(본문 추출 실패 - 헤드라인만 참고)",
            })

    # 종목별 뉴스 텍스트 구성
    news_text = ""
    for ticker, articles in news_with_text.items():
        news_text += f"\n## {ticker}\n"
        for i, a in enumerate(articles, 1):
            news_text += f"\n### 기사 {i}: [{a['publisher']}] {a['title']}\n"
            news_text += f"{a['body']}\n"

    prompt = f"""당신은 전문 주식 애널리스트입니다. 아래는 오늘 수집된 종목별 최신 뉴스 기사 전문입니다.

{news_text}

각 종목별로 기사를 읽고 다음 형식으로 분석해주세요.

**출력 형식 (반드시 준수):**
각 종목을 "### TICKER" 로 시작하고, 아래 3개 섹션을 작성:

[요약]
- 기사 핵심 내용을 bullet point(-)로 3~5개 정리
- 각 bullet은 한 줄로 간결하게

[영향]
호재/악재/중립 중 하나 + 한 줄 근거

[주목 포인트]
- 투자자가 주목해야 할 핵심 포인트를 bullet point(-)로 필요한 만큼 자유롭게 작성 (2~5개)

**규칙:**
- 반드시 한국어로 작성
- 불필요한 수식어 없이 팩트 중심
- [요약], [영향], [주목 포인트] 섹션 헤더를 반드시 포함"""

    try:
        client = anthropic.Anthropic()
        print("    Calling Claude Sonnet for analysis...")
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = resp.content[0].text

        # 파싱: ### TICKER 기준으로 분리
        analyses = {}
        current_ticker = None
        current_text = []
        for line in raw.split("\n"):
            if line.strip().startswith("### "):
                if current_ticker and current_text:
                    analyses[current_ticker] = "\n".join(current_text).strip()
                current_ticker = line.strip().replace("### ", "").strip()
                current_text = []
            elif current_ticker:
                current_text.append(line)
        if current_ticker and current_text:
            analyses[current_ticker] = "\n".join(current_text).strip()

        return analyses
    except Exception as e:
        print(f"[AI ERROR] {e}")
        return {}


def get_stock_news(ticker_symbol, max_items=5):
    """24시간 내 신규 뉴스 수집"""
    try:
        stock = yf.Ticker(ticker_symbol)
        news = stock.news
        if not news:
            return []

        cutoff = datetime.now() - timedelta(hours=24)
        results = []
        for item in news[:max_items]:
            content = item.get("content", {})
            pub_date_str = content.get("pubDate", "")
            # 24시간 필터
            try:
                pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                if pub_date.replace(tzinfo=None) < cutoff:
                    continue
            except Exception:
                pass  # 파싱 실패시 포함

            results.append({
                "title": content.get("title", "No title"),
                "publisher": content.get("provider", {}).get("displayName", "Unknown"),
                "link": content.get("canonicalUrl", {}).get("url", ""),
                "published": pub_date_str,
            })
        return results
    except Exception as e:
        print(f"[NEWS ERROR] {ticker_symbol}: {e}")
        return []


def get_market_summary():
    """시장 지수 요약 (S&P500, NASDAQ, DOW)"""
    indices = {"^GSPC": "S&P 500", "^IXIC": "NASDAQ", "^DJI": "DOW 30", "^VIX": "VIX"}
    results = []
    for symbol, name in indices.items():
        try:
            t = yf.Ticker(symbol)
            info = t.info
            price = info.get("regularMarketPrice") or info.get("previousClose")
            prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
            chg = ((price - prev) / prev * 100) if price and prev else None
            results.append({"name": name, "price": price, "change_pct": chg})
        except Exception:
            results.append({"name": name, "price": None, "change_pct": None})
    return results


# ── Formatting helpers ──

def fmt_num(n):
    if n is None: return "N/A"
    if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
    if abs(n) >= 1e9: return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6: return f"${n/1e6:.1f}M"
    return f"${n:,.0f}"

def fmt_price(p):
    if p is None: return "N/A"
    return f"${p:,.2f}"

def fmt_ratio(r):
    if r is None: return "N/A"
    return f"{r:.2f}"

def fmt_pct(p):
    if p is None: return "N/A"
    return f"{p*100:+.1f}%" if abs(p) < 10 else f"{p:+.1f}%"

def fmt_pct_raw(p):
    if p is None: return "N/A"
    return f"{p:+.2f}%"

def format_ai_analysis(raw_text):
    """AI 분석 텍스트를 구조화된 HTML 섹션으로 변환"""
    import re

    # 섹션 분리: [요약], [영향], [주목 포인트]
    sections = {"요약": "", "영향": "", "주목 포인트": ""}
    current = None
    lines_buf = []

    for line in raw_text.split("\n"):
        stripped = line.strip()
        # 섹션 헤더 매칭
        matched = False
        for key in sections:
            if re.match(rf"^\[{key}\]", stripped) or re.match(rf"^\*?\*?\[{key}\]\*?\*?", stripped):
                if current and lines_buf:
                    sections[current] = "\n".join(lines_buf).strip()
                current = key
                lines_buf = []
                matched = True
                break
        if not matched and current is not None:
            lines_buf.append(line)

    if current and lines_buf:
        sections[current] = "\n".join(lines_buf).strip()

    # 섹션이 파싱 안 된 경우 원문 그대로 표시
    if not any(sections.values()):
        fallback = raw_text.replace("\n", "<br>")
        return f"""
    <div style="margin-top: 10px; background: #f0f4ff; border-radius: 10px; padding: 16px; border-left: 4px solid #6366f1;">
      <div style="font-size: 12px; font-weight: 700; color: #6366f1; margin-bottom: 8px;">AI 뉴스 분석</div>
      <div style="font-size: 13px; color: #333; line-height: 1.7;">{fallback}</div>
    </div>"""

    def bullets_to_html(text):
        """bullet point 텍스트를 HTML 리스트로 변환"""
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                line = line[2:]
            elif line.startswith("* "):
                line = line[2:]
            if line:
                # **bold** 마크다운 처리
                line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
                items.append(line)
        if not items:
            return ""
        return '<ul style="margin: 4px 0; padding-left: 18px;">' + "".join(
            f'<li style="margin: 3px 0; font-size: 13px; line-height: 1.6; color: #333;">{item}</li>'
            for item in items
        ) + "</ul>"

    # 영향 파싱: 호재/악재/중립
    impact_text = sections["영향"].strip()
    impact_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', impact_text)
    impact_color = "#6366f1"
    impact_icon = ""
    if "호재" in impact_text:
        impact_color = "#16a34a"
        impact_icon = "▲"
    elif "악재" in impact_text:
        impact_color = "#dc2626"
        impact_icon = "▼"
    elif "중립" in impact_text:
        impact_color = "#d97706"
        impact_icon = "■"

    html = f"""
    <div style="margin-top: 10px; background: #f8f9ff; border-radius: 10px; padding: 16px; border-left: 4px solid #6366f1;">
      <div style="font-size: 12px; font-weight: 700; color: #6366f1; margin-bottom: 10px;">AI 뉴스 분석</div>"""

    # 요약 섹션
    if sections["요약"]:
        html += f"""
      <div style="margin-bottom: 10px;">
        <div style="font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">핵심 요약</div>
        {bullets_to_html(sections["요약"])}
      </div>"""

    # 영향 섹션
    if sections["영향"]:
        html += f"""
      <div style="margin-bottom: 10px; background: white; border-radius: 6px; padding: 8px 12px; display: inline-block;">
        <span style="font-size: 13px; color: {impact_color}; font-weight: 700;">{impact_icon} {impact_text.replace(chr(10), ' ')}</span>
      </div>"""

    # 주목 포인트 섹션
    if sections["주목 포인트"]:
        html += f"""
      <div>
        <div style="font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">투자자 주목 포인트</div>
        {bullets_to_html(sections["주목 포인트"])}
      </div>"""

    html += "\n    </div>"
    return html


def color_val(val, threshold=0):
    if val is None: return "#888"
    return "#22c55e" if val >= threshold else "#ef4444"


# ── HTML Generation ──

def generate_html(stocks_data, news_data, market_data, ai_analyses=None):
    today = datetime.now().strftime("%Y-%m-%d (%A)")

    # 포트폴리오 통계
    valid = [s for s in stocks_data if s and s["change_pct"] is not None]
    avg_change = sum(s["change_pct"] for s in valid) / len(valid) if valid else 0
    gainers = [s for s in valid if s["change_pct"] > 0]
    losers = [s for s in valid if s["change_pct"] < 0]
    best = max(valid, key=lambda x: x["change_pct"]) if valid else None
    worst = min(valid, key=lambda x: x["change_pct"]) if valid else None

    # 섹터 분류
    sectors = {}
    for s in stocks_data:
        if s:
            sec = s["sector"] or "Other"
            sectors.setdefault(sec, []).append(s["ticker"])

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 850px; margin: 0 auto; padding: 20px; background: #f0f2f5; color: #1a1a2e;">

<!-- Header -->
<div style="background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; padding: 30px; border-radius: 16px; margin-bottom: 20px;">
  <h1 style="margin: 0; font-size: 26px; letter-spacing: -0.5px;">Daily Stock Newsletter</h1>
  <p style="margin: 8px 0 0; opacity: 0.7; font-size: 14px;">{today} | {len(stocks_data)} stocks tracked</p>
</div>

<!-- Market Summary -->
<div style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">"""

    for m in market_data:
        c = color_val(m["change_pct"])
        chg = fmt_pct_raw(m["change_pct"]) if m["change_pct"] else "N/A"
        p = f"{m['price']:,.2f}" if m["price"] else "N/A"
        html += f"""
  <div style="flex: 1; min-width: 120px; background: white; border-radius: 12px; padding: 14px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); text-align: center;">
    <div style="font-size: 12px; color: #888; font-weight: 600;">{m['name']}</div>
    <div style="font-size: 18px; font-weight: 700; margin: 4px 0;">{p}</div>
    <div style="font-size: 14px; font-weight: 700; color: {c};">{chg}</div>
  </div>"""

    html += f"""
</div>

<!-- Portfolio Summary -->
<div style="background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
  <h2 style="margin: 0 0 12px; font-size: 18px;">Portfolio Summary</h2>
  <div style="display: flex; gap: 20px; flex-wrap: wrap; font-size: 14px;">
    <div><span style="color: #888;">Avg Change:</span> <b style="color: {color_val(avg_change)}">{avg_change:+.2f}%</b></div>
    <div><span style="color: #888;">Gainers:</span> <b style="color: #22c55e">{len(gainers)}</b></div>
    <div><span style="color: #888;">Losers:</span> <b style="color: #ef4444">{len(losers)}</b></div>
    <div><span style="color: #888;">Best:</span> <b style="color: #22c55e">{best['ticker'] if best else 'N/A'} ({best['change_pct']:+.2f}%)</b></div>
    <div><span style="color: #888;">Worst:</span> <b style="color: #ef4444">{worst['ticker'] if worst else 'N/A'} ({worst['change_pct']:+.2f}%)</b></div>
  </div>
  <div style="margin-top: 10px; font-size: 13px; color: #888;">
    Sectors: {' | '.join(f'<b>{sec}</b>: {", ".join(tickers)}' for sec, tickers in sectors.items())}
  </div>
</div>

<!-- Overview Table -->
<div style="background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px;">
<h2 style="margin: 0; padding: 16px 16px 0; font-size: 18px;">Price & Valuation</h2>
<div style="overflow-x: auto;">
<table style="width: 100%; border-collapse: collapse; font-size: 13px;">
<thead>
  <tr style="background: #1a1a2e; color: white;">
    <th style="padding: 10px 8px; text-align: left;">Ticker</th>
    <th style="padding: 10px 6px; text-align: right;">Price</th>
    <th style="padding: 10px 6px; text-align: right;">Chg%</th>
    <th style="padding: 10px 6px; text-align: right;">P/E</th>
    <th style="padding: 10px 6px; text-align: right;">Fwd P/E</th>
    <th style="padding: 10px 6px; text-align: right;">Target</th>
    <th style="padding: 10px 6px; text-align: right;">Upside</th>
    <th style="padding: 10px 6px; text-align: right;">MA50</th>
    <th style="padding: 10px 6px; text-align: right;">RSI</th>
    <th style="padding: 10px 6px; text-align: center;">Rating</th>
  </tr>
</thead>
<tbody>"""

    for s in stocks_data:
        if s is None:
            continue
        chg_c = color_val(s["change_pct"])
        chg_s = fmt_pct_raw(s["change_pct"]) if s["change_pct"] is not None else "N/A"

        upside_s = "N/A"
        if s["target_mean"] and s["current_price"]:
            upside = ((s["target_mean"] - s["current_price"]) / s["current_price"]) * 100
            upside_s = f'<span style="color:{color_val(upside)}">{upside:+.1f}%</span>'

        rec = (s["recommendation"] or "N/A").upper()
        rec_colors = {"BUY": "#22c55e", "STRONG_BUY": "#15803d", "HOLD": "#f59e0b", "SELL": "#ef4444", "STRONG_SELL": "#dc2626"}
        rec_c = rec_colors.get(rec, "#888")

        # MA50 vs price signal
        ma50_s = fmt_price(s["ma50"])
        ma50_signal = ""
        if s["ma50"] and s["current_price"]:
            ma50_signal = " ↑" if s["current_price"] > s["ma50"] else " ↓"

        # RSI color
        rsi_s = f'{s["rsi"]}' if s["rsi"] else "N/A"
        rsi_c = "#888"
        if s["rsi"]:
            if s["rsi"] >= 70: rsi_c = "#ef4444"   # 과매수
            elif s["rsi"] <= 30: rsi_c = "#22c55e"  # 과매도
            else: rsi_c = "#888"

        html += f"""
  <tr style="border-bottom: 1px solid #f0f0f0;">
    <td style="padding: 8px; font-weight: bold;">{s['ticker']}<br><span style="font-weight: normal; font-size: 10px; color: #999;">{s['name'][:18]}</span></td>
    <td style="padding: 8px 6px; text-align: right;">{fmt_price(s['current_price'])}</td>
    <td style="padding: 8px 6px; text-align: right; color: {chg_c}; font-weight: 700;">{chg_s}</td>
    <td style="padding: 8px 6px; text-align: right;">{fmt_ratio(s['pe_ratio'])}</td>
    <td style="padding: 8px 6px; text-align: right;">{fmt_ratio(s['forward_pe'])}</td>
    <td style="padding: 8px 6px; text-align: right;">{fmt_price(s['target_mean'])}</td>
    <td style="padding: 8px 6px; text-align: right;">{upside_s}</td>
    <td style="padding: 8px 6px; text-align: right; font-size: 11px;">{ma50_s}{ma50_signal}</td>
    <td style="padding: 8px 6px; text-align: right; color: {rsi_c}; font-weight: 600;">{rsi_s}</td>
    <td style="padding: 8px 6px; text-align: center;"><span style="background:{rec_c}; color:white; padding:2px 6px; border-radius:10px; font-size:10px;">{rec}</span></td>
  </tr>"""

    html += """
</tbody></table></div></div>

<!-- Individual Stock Cards -->
<h2 style="font-size: 18px; margin: 24px 0 12px;">Stock Details</h2>"""

    for s in stocks_data:
        if s is None:
            continue

        chg_c = color_val(s["change_pct"])
        chg_s = fmt_pct_raw(s["change_pct"]) if s["change_pct"] is not None else "N/A"

        # 52주 범위 내 위치 (프로그레스 바)
        pos_52w = ""
        if s["fifty_two_low"] and s["fifty_two_high"] and s["current_price"]:
            rng = s["fifty_two_high"] - s["fifty_two_low"]
            if rng > 0:
                pct = min(max((s["current_price"] - s["fifty_two_low"]) / rng * 100, 0), 100)
                pos_52w = f"""
    <div style="margin: 8px 0;">
      <div style="font-size: 11px; color: #888; margin-bottom: 4px;">52W Range: {fmt_price(s['fifty_two_low'])} — {fmt_price(s['fifty_two_high'])}</div>
      <div style="background: #e5e7eb; border-radius: 4px; height: 8px; position: relative;">
        <div style="background: linear-gradient(90deg, #22c55e, #f59e0b, #ef4444); border-radius: 4px; height: 8px; width: 100%;"></div>
        <div style="position: absolute; top: -2px; left: {pct:.0f}%; width: 12px; height: 12px; background: #1a1a2e; border-radius: 50%; border: 2px solid white; transform: translateX(-50%);"></div>
      </div>
    </div>"""

        # EPS & Revenue
        eps_section = ""
        eps_parts = []
        if s["eps_trailing"] is not None:
            eps_parts.append(f"EPS (TTM): <b>${s['eps_trailing']:.2f}</b>")
        if s["eps_forward"] is not None:
            eps_parts.append(f"EPS (Fwd): <b>${s['eps_forward']:.2f}</b>")
        if s["revenue"]:
            eps_parts.append(f"Revenue: <b>{fmt_num(s['revenue'])}</b>")
        if s["revenue_growth"] is not None:
            c = color_val(s["revenue_growth"])
            eps_parts.append(f'Rev Growth: <b style="color:{c}">{fmt_pct(s["revenue_growth"])}</b>')
        if s["earnings_growth"] is not None:
            c = color_val(s["earnings_growth"])
            eps_parts.append(f'EPS Growth: <b style="color:{c}">{fmt_pct(s["earnings_growth"])}</b>')
        if eps_parts:
            eps_section = '<div style="margin: 6px 0; font-size: 12px; color: #555;">' + " &nbsp;|&nbsp; ".join(eps_parts) + "</div>"

        # Dividend & Short
        extra_parts = []
        if s["dividend_yield"] is not None and s["dividend_yield"] > 0:
            extra_parts.append(f"Div Yield: <b>{s['dividend_yield']*100:.2f}%</b>")
        if s["short_ratio"] is not None:
            extra_parts.append(f"Short Ratio: <b>{s['short_ratio']:.1f}</b>")
        if s["short_pct_float"] is not None:
            extra_parts.append(f"Short % Float: <b>{s['short_pct_float']*100:.2f}%</b>")
        extra_section = ""
        if extra_parts:
            extra_section = '<div style="margin: 6px 0; font-size: 12px; color: #555;">' + " &nbsp;|&nbsp; ".join(extra_parts) + "</div>"

        # Technical signals
        tech_parts = []
        if s["ma50"]:
            signal = "Above" if s["current_price"] and s["current_price"] > s["ma50"] else "Below"
            tech_parts.append(f"MA50: {fmt_price(s['ma50'])} ({signal})")
        if s["ma200"]:
            signal = "Above" if s["current_price"] and s["current_price"] > s["ma200"] else "Below"
            tech_parts.append(f"MA200: {fmt_price(s['ma200'])} ({signal})")
        if s["rsi"]:
            rsi_label = "Overbought" if s["rsi"] >= 70 else ("Oversold" if s["rsi"] <= 30 else "Neutral")
            tech_parts.append(f"RSI: {s['rsi']} ({rsi_label})")
        tech_section = ""
        if tech_parts:
            tech_section = '<div style="margin: 6px 0; font-size: 12px; color: #555;">' + " &nbsp;|&nbsp; ".join(tech_parts) + "</div>"

        # AI 뉴스 분석
        ai_section = ""
        if ai_analyses and s["ticker"] in ai_analyses:
            raw_analysis = ai_analyses[s["ticker"]]
            ai_section = format_ai_analysis(raw_analysis)

        # News for this ticker
        news_section = ""
        ticker_news = news_data.get(s["ticker"], [])
        if ticker_news:
            news_section = '<div style="margin-top: 8px; border-top: 1px solid #f0f0f0; padding-top: 8px; font-size: 11px; color: #888;">뉴스 원문:</div>'
            for a in ticker_news[:3]:
                pub = a["published"][:10] if a["published"] else ""
                if a["link"]:
                    news_section += f'<p style="margin: 4px 0; font-size: 12px;"><a href="{a["link"]}" style="color: #2563eb; text-decoration: none;">{a["title"]}</a> <span style="color:#bbb;">- {a["publisher"]} {pub}</span></p>'
                else:
                    news_section += f'<p style="margin: 4px 0; font-size: 12px;">{a["title"]} <span style="color:#bbb;">- {a["publisher"]} {pub}</span></p>'

        # Analyst target bar
        target_section = ""
        if s["target_low"] and s["target_high"] and s["target_mean"] and s["current_price"]:
            target_section = f'<div style="font-size: 12px; color: #555; margin: 6px 0;">Target: {fmt_price(s["target_low"])} — <b>{fmt_price(s["target_mean"])}</b> — {fmt_price(s["target_high"])} ({s["num_analysts"] or "?"} analysts)</div>'

        html += f"""
<div style="background: white; border-radius: 12px; padding: 18px; margin-bottom: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); border-left: 4px solid {chg_c};">
  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
    <div>
      <span style="font-size: 17px; font-weight: 700;">{s['ticker']}</span>
      <span style="font-size: 13px; color: #888; margin-left: 8px;">{s['name']}</span>
      <span style="font-size: 11px; color: #aaa; margin-left: 6px;">{s['sector']}</span>
    </div>
    <div style="text-align: right;">
      <span style="font-size: 20px; font-weight: 700;">{fmt_price(s['current_price'])}</span>
      <span style="font-size: 15px; font-weight: 700; color: {chg_c}; margin-left: 8px;">{chg_s}</span>
    </div>
  </div>
  <div style="display: flex; gap: 16px; margin-top: 8px; font-size: 12px; color: #555; flex-wrap: wrap;">
    <span>P/E: <b>{fmt_ratio(s['pe_ratio'])}</b></span>
    <span>Fwd P/E: <b>{fmt_ratio(s['forward_pe'])}</b></span>
    <span>PEG: <b>{fmt_ratio(s['peg_ratio'])}</b></span>
    <span>Mkt Cap: <b>{fmt_num(s['market_cap'])}</b></span>
  </div>
  {pos_52w}
  {target_section}
  {eps_section}
  {extra_section}
  {tech_section}
  {ai_section}
  {news_section}
</div>"""

    # Footer
    html += """
<p style="text-align: center; color: #aaa; font-size: 11px; margin-top: 30px;">
  Generated by Stock Newsletter Bot | Data from Yahoo Finance<br>
  Disclaimer: This is for informational purposes only, not investment advice.
</p>
</body></html>"""

    return html


def main():
    print(f"[{datetime.now()}] Collecting data...")

    # 시장 지수
    print("  Fetching market indices...")
    market_data = get_market_summary()

    stocks_data = []
    news_data = {}

    for ticker in TICKERS:
        print(f"  Fetching {ticker}...")
        data = get_stock_data(ticker)
        if data:
            stocks_data.append(data)
        else:
            print(f"  [SKIP] {ticker} - no data")

        news = get_stock_news(ticker)
        if news:
            news_data[ticker] = news

    # AI 뉴스 분석
    ai_analyses = {}
    if news_data:
        print("  Analyzing news with Claude AI...")
        ai_analyses = analyze_news_with_ai(news_data)

    html = generate_html(stocks_data, news_data, market_data, ai_analyses)

    # 파일 저장
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    output_path = os.path.join(output_dir, f"newsletter_{datetime.now().strftime('%Y%m%d')}.html")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[SAVED] {output_path}")

    return html, NEWSLETTER_SUBJECT


if __name__ == "__main__":
    html, subject = main()
    print(f"\nNewsletter generated: {len(html)} bytes")
