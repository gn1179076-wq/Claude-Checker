import imaplib
import email
from email.header import decode_header
import requests
import os

# --- 設定區域 ---
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
IMAP_SERVER = "imap.gmail.com"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_webhook(message, is_alert=False):
    """發送 Discord 嵌入式訊息"""
    # 紅色 (0xFF0000) 代表危險，綠色 (0x00FF00) 代表正常
    color = 0xFF0000 if is_alert else 0x00FF00
    title = "🚨 嚴重警告：帳單異常" if is_alert else "✅ 帳單檢查正常"
    
    payload = {
        "embeds": [{
            "title": title,
            "description": message,
            "color": color
        }]
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("✅ 訊息已成功發送至 Discord")
    except requests.exceptions.RequestException as e:
        print(f"❌ 發送 Discord 失敗: {e}")

def check_anthropic_emails():
    if not all([EMAIL_USER, EMAIL_PASS, DISCORD_WEBHOOK_URL]):
        print("錯誤：環境變數未設定完全")
        return

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        status, messages = mail.search(None, '(FROM "anthropic.com")')
        email_ids = messages[0].split()

        if not email_ids:
            print("目前沒有來自 Anthropic 的郵件。")
            mail.logout()
            return

        latest_email_id = email_ids[-1]
        _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        
        subject = decode_header(msg.get("Subject"))[0][0]
        if isinstance(subject, bytes): subject = subject.decode()

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
        else:
            body = msg.get_payload(decode=True).decode()

        # 邏輯判斷
        if "Gift Max" in subject or "Gift Max" in body:
            msg_text = f"偵測到不明的 Gift Max 交易！\n標題：{subject}"
            send_discord_webhook(msg_text, is_alert=True)
        else:
            msg_text = f"檢查完畢，最新 Anthropic 郵件為：{subject} (無 Gift Max 異常)"
            send_discord_webhook(msg_text, is_alert=False)
                    
        mail.logout()
    except Exception as e:
        print(f"程式發生錯誤: {e}")

if __name__ == "__main__":
    check_anthropic_emails()
