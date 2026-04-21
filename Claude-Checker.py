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
    # 初始化 msg_text 為空字串
    msg_text = ""
    
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
        
        subject_raw = msg.get("Subject")
        subject = decode_header(subject_raw)[0][0]
        if isinstance(subject, bytes): 
            subject = subject.decode()

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break # 找到第一個純文字內容就跳出
        else:
            body = msg.get_payload(decode=True).decode()

        # 這裡一定會賦值給 msg_text
        if "Gift Max" in subject or "Gift Max" in body:
            msg_text = f"偵測到不明的 Gift Max 交易！\n標題：{subject}"
            is_alert = True
        else:
            # 正常情況：僅印在 Log，不發送 Discord
            msg_text = f"檢查完畢，最新 Anthropic 郵件為：{subject} (無 Gift Max 異常)"
            print(f"✅ {msg_text}")
        
        # 發送通知
        send_discord_webhook(msg_text, is_alert=is_alert)
                    
        mail.logout()
    except Exception as e:
        print(f"程式發生錯誤: {e}")
        # 如果是程式執行到一半崩潰，也可以發送錯誤警報到 Discord
        send_discord_webhook(f"監控程式執行失敗: {str(e)}", is_alert=True)

if __name__ == "__main__":
    check_anthropic_emails()
