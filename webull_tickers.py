#!/usr/bin/env python3
"""Webull 전 계좌 보유종목 조회 — auto-trader venv로 실행 (읽기 전용, 주문 없음)

실행: /Users/hyunsikyun/auto-trader/.venv/bin/python3 webull_tickers.py
출력: stdout 마지막 줄에 TICKERS_JSON=[...] (진행 메시지는 stderr)
"""
import sys
import json
import time

AUTO_TRADER_DIR = "/Users/hyunsikyun/auto-trader"
sys.path.insert(0, AUTO_TRADER_DIR)

# 제외할 계좌: 5JB24027은 auto-trader 자동 스윙 매매 전용이라 뉴스 분석 불필요
EXCLUDE_ACCOUNTS = {"5JB24027"}

from src.broker import _trade_client  # 공식 Webull OpenAPI 클라이언트 재사용


def main():
    client = _trade_client()
    # API에 연결된 전체 계좌 목록 (현재 4개)
    subs = client.account.get_app_subscriptions().json()

    symbols = set()
    for sub in subs:
        if sub["account_number"] in EXCLUDE_ACCOUNTS:
            print(f"  [{sub['account_number']}] 자동매매 계좌 — 제외", file=sys.stderr)
            continue
        acct_id = sub["account_id"]
        for attempt in range(3):
            try:
                time.sleep(3)  # 연속 호출 시 429(Too Many Requests) 방지
                body = client.account.get_account_position(acct_id, page_size=100).json()
                items = body if isinstance(body, list) else (
                    body.get("holdings") or body.get("positions") or []
                )
                acct_syms = {it["symbol"] for it in items if it.get("symbol")}
                symbols |= acct_syms
                print(f"  [{sub['account_number']}] {len(acct_syms)}개 보유", file=sys.stderr)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  ⚠️ {sub['account_number']} 조회 실패: {str(e)[:100]}", file=sys.stderr)
                else:
                    time.sleep(5)  # 재시도 전 대기

    print("TICKERS_JSON=" + json.dumps(sorted(symbols)))


if __name__ == "__main__":
    main()
