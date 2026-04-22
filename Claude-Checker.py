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

# 【大膽想法：搜尋模式配置】
# 可選模式: "ANTHROPIC" (標準), "GIFT_MAX_ONLY" (關鍵字優先), "ALL" (測試用)
SEARCH_MODE = "ALL" 

# 緊急聯絡資訊
BANK_CONTACTS = {
    "銀行名稱": "國泰世華銀行",
    "掛失/盜刷專線": "02-2383-1000",
    "國內免付費專線": "0800-818-818",
    "Anthropic 客服": "https://support.anthropic.com/"
}

def send_discord_notification(message, is_critical=True, is_system_error=False, contact_info=None):
    color = 0xFF0000 if is_critical else 0x00FF00
    
    if is_system_error:
        title = "❌ 系統錯誤：監控程式故障"
    elif is_critical:
        title = "🚨 緊急警報：發現可疑帳單"
    else:
        title = "✅ 系統檢查完成"

    description = message
    if contact_info:
        description += "\n\n**🆘 緊急處置建議：**"
        for key, value in contact_info.items():
            description += f"\n- **{key}**: {value}"

    payload = {
        "embeds": [{
            "title": title,
            "description": description,
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
    if not all([EMAIL_USER, EMAIL_PASS, DISCORD_WEBHOOK_URL]):
        print("❌ 錯誤：環境變數未設定完整")
        return

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # 【根據模式決定搜尋條件】
        if SEARCH_MODE == "ANTHROPIC":
            status, messages = mail.search(None, '(FROM "anthropic.com")')
        elif SEARCH_MODE == "GIFT_MAX_ONLY":
            status, messages = mail.search(None, 'SUBJECT "Gift Max"')
        else:
            status, messages = mail.search(None, 'ALL')

        email_ids = messages[0].split()

        if not email_ids:
            print(f"ℹ️ 模式 [{SEARCH_MODE}] 下目前沒有匹配的郵件。")
            mail.logout()
            return

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

        # 核心判定邏輯
        if "Gift Max" in subject or "Gift Max" in body:
            msg_text = f"警告：偵測到 'Gift Max' 關鍵字。\n標題：{subject}"
            send_discord_notification(msg_text, is_critical=True, is_system_error=False, contact_info=BANK_CONTACTS)
        else:
            print(f"✅ 檢查完成，最新郵件無異常: {subject}")
        
        mail.logout()

    except Exception as e:
        error_msg = f"監控程式在執行時發生錯誤: {str(e)}"
        print(f"❌ {error_msg}")
        send_discord_notification(error_msg, is_critical=True, is_system_error=True)

if __name__ == "__main__":
    check_anthropic_emails()
