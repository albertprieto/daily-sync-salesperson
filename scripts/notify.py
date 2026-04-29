"""Email notifier via Gmail SMTP.

Variables de entornno:
  GMAIL_USER      apm@industrialshields.com
  GMAIL_APP_PASS  App Password Gmail (16 chars, sin espacios)
  NOTIFY_TO       destinatario (default = GMAIL_USER)
"""
import os
import smtplib
import ssl
from email.message import EmailMessage


def send(subject: str, body_html: str, body_text: str = ""):
    user = os.environ["GMAIL_USER"]
    pwd = os.environ["GMAIL_APP_PASS"]
    to = os.environ.get("NOTIFY_TO", user)

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text or "Ver versión HTML del mensaje.")
    msg.add_alternative(body_html, subtype="html")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(user, pwd)
        s.send_message(msg)
    print(f"[notify] sent to {to}: {subject}")


if __name__ == "__main__":
    import sys
    subject = sys.argv[1] if len(sys.argv) > 1 else "Test daily-sync"
    body = sys.argv[2] if len(sys.argv) > 2 else "<p>Test email</p>"
    send(subject, body)
