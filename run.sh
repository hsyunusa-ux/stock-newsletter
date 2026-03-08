#!/bin/bash
# Stock Newsletter - 매일 아침 자동 실행 스크립트
cd /Users/hyunsikyun/stock-newsletter

# 환경변수 로드
source /Users/hyunsikyun/stock-newsletter/.env 2>/dev/null

# Python 경로
PYTHON=/Library/Developer/CommandLineTools/usr/bin/python3

# 뉴스레터 생성 및 발송
$PYTHON send_email.py >> /Users/hyunsikyun/stock-newsletter/logs/newsletter.log 2>&1
