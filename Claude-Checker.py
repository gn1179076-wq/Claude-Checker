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
        
        subject_raw = msg.get("Subject")
        subject = decode_header(subject_raw)[0][0]
        if isinstance(subject, bytes): subject = subject.decode()

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        # --- 修改重點在這裡 ---
        is_alert = flase
        if "Gift Max" in subject or "Gift Max" in body:
            # 只有異常時才發送 Discord
            msg_text = f"偵測到不明的 Gift Max 交易！\n標題：{subject}"
            send_discord_webhook(msg_text, is_alert=True)
        else:
            # 正常情況：僅印 Log，什麼都不做
            print(f"✅ 檢查完畢，最新 Anthropic 郵件為：{subject} (無 Gift Max 異常)")
        
        mail.logout()
    except Exception as e:
        print(f"程式發生錯誤: {e}")
        send_discord_webhook(f"監控程式執行失敗: {str(e)}", is_alert=True)
