#!/usr/bin/env python3
"""Gmail SMTP로 뉴스레터 자동 발송"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from newsletter import main


def send_newsletter():
    # Gmail 앱 비밀번호 (환경변수 또는 .env에서 로드)
    gmail_user = os.environ.get("GMAIL_USER", "hsyunusa@gmail.com")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not gmail_app_password:
        print("[ERROR] GMAIL_APP_PASSWORD 환경변수를 설정해주세요.")
        print("  1. https://myaccount.google.com/apppasswords 에서 앱 비밀번호 생성")
        print("  2. export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'")
        return False

    # 뉴스레터 생성
    html_content, subject = main()
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"{subject} - {today}"

    # 이메일 구성
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = gmail_user

    msg.attach(MIMEText(html_content, "html"))

    # SMTP 발송
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_app_password)
            server.sendmail(gmail_user, gmail_user, msg.as_string())
        print(f"[SUCCESS] Newsletter sent to {gmail_user}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send: {e}")
        return False


if __name__ == "__main__":
    send_newsletter()
