import imaplib
import email
from email.header import decode_header
import requests
import os

# --- 使用環境變數設定 ---
# 在 GitHub Actions 或本地環境設定這些環境變數即可
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
IMAP_SERVER = "imap.gmail.com"  # Gmail 固定為此
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_webhook(message):
    """發送訊息到 Discord"""
    payload = {"content": f"🚨 **Claude 帳單監控提醒** 🚨\n{message}"}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("✅ 訊息已成功發送至 Discord")
    except requests.exceptions.RequestException as e:
        print(f"❌ 發送 Discord 失敗: {e}")

def check_anthropic_emails():
    if not all([EMAIL_USER, EMAIL_PASS, DISCORD_WEBHOOK_URL]):
        print("錯誤：缺少環境變數 (EMAIL_USER, EMAIL_PASS 或 DISCORD_WEBHOOK_URL)")
        return

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # 搜尋所有來自 anthropic.com 的郵件
        status, messages = mail.search(None, '(FROM "anthropic.com")')
        email_ids = messages[0].split()

        if not email_ids:
            print("目前沒有來自 Anthropic 的郵件。")
            return

        # 檢查最後一封郵件 (為了避免一直發同樣的通知，實務上通常會檢查是否為已讀或日期)
        latest_email_id = email_ids[-1]
        _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        
        subject = decode_header(msg.get("Subject"))[0][0]
        if isinstance(subject, bytes): 
            subject = subject.decode()

        # 讀取郵件內容
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
        else:
            body = msg.get_payload(decode=True).decode()

        # 邏輯判斷：如果標題或內容有 Gift Max，才發送警報
        if "Gift Max" in subject or "Gift Max" in body:
            print(f"🚨 偵測到可疑交易：{subject}")
            send_discord_webhook(f"偵測到可疑交易！\n標題：{subject}")
        else:
            print(f"檢查完畢，最新一封 Anthropic 郵件為：{subject} (無 Gift Max 異常)")
                    
        mail.logout()
    except Exception as e:
        print(f"錯誤：{e}")

if __name__ == "__main__":
    check_anthropic_emails()