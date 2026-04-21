import imaplib
import email
from email.header import decode_header
import requests
import os

# --- 環境變數讀取 ---
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
IMAP_SERVER = "imap.gmail.com"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_notification(message, is_critical=True, is_system_error=False):
    """
    發送 Discord 通知
    is_critical: 是否為緊急通知 (True=紅色, False=綠色)
    is_system_error: 是否為程式崩潰導致的錯誤
    """
    # 顏色定義：紅色 (0xFF0000) 用於警告，綠色 (0x00FF00) 用於系統運作
    color = 0xFF0000 if is_critical else 0x00FF00
    
    # 標題定義
    if is_system_error:
        title = "❌ 系統錯誤：監控程式故障"
    elif is_critical:
        title = "🚨 緊急警報：發現可疑帳單"
    else:
        title = "✅ 系統檢查完成"

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
        print(f"✅ Discord 通知已發送: {title}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 無法發送 Discord 通知: {e}")

def check_anthropic_emails():
    # 檢查變數是否齊全
    if not all([EMAIL_USER, EMAIL_PASS, DISCORD_WEBHOOK_URL]):
        print("❌ 錯誤：環境變數未設定完整")
        return

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # 搜尋郵件
        status, messages = mail.search(None, '(FROM "anthropic.com")')
        email_ids = messages[0].split()

        if not email_ids:
            print("ℹ️ 目前沒有來自 Anthropic 的郵件。")
            mail.logout()
            return

        # 解析最後一封信
        latest_email_id = email_ids[-1]
        _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        
        subject = decode_header(msg.get("Subject", ""))[0][0]
        if isinstance(subject, bytes): subject = subject.decode()

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        # --- 核心判定邏輯 ---
        if "Gift Max" in subject or "Gift Max" in body:
            msg_text = f"警告：在郵件中偵測到關鍵字 'Gift Max'。\n標題：{subject}"
            send_discord_notification(msg_text, is_critical=True, is_system_error=False)
        else:
            print(f"✅ 檢查完成，最新郵件無異常: {subject}")
        
        mail.logout()

    except Exception as e:
        error_msg = f"監控程式在執行時發生錯誤: {str(e)}"
        print(f"❌ {error_msg}")
        send_discord_notification(error_msg, is_critical=True, is_system_error=True)

if __name__ == "__main__":
    check_anthropic_emails()
