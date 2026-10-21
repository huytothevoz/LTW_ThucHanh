"""SMTP password recovery. Never silently pretend an email was delivered."""
import os
import smtplib
import ssl
from email.message import EmailMessage


def smtp_ready() -> bool:
    return bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM') and os.getenv('SMTP_USER') and os.getenv('SMTP_PASSWORD'))


def send_reset(email: str, name: str, url: str, locale: str='vi') -> None:
    if not smtp_ready(): raise RuntimeError('SMTP is not configured')
    msg=EmailMessage()
    msg['Subject']='CrawlInsight — Khôi phục mật khẩu / Password reset'
    msg['From']=os.environ['SMTP_FROM'];msg['To']=email
    msg.set_content(f'Xin chào {name},\n\nMở liên kết sau để đặt lại mật khẩu CrawlInsight (20 phút):\n{url}\n\nNếu không yêu cầu, bạn có thể bỏ qua email.\n\nHello, use the link above to reset your password. It expires in 20 minutes.\n')
    host=os.environ['SMTP_HOST']; port=int(os.getenv('SMTP_PORT','587'))
    if port==465:
        with smtplib.SMTP_SSL(host,port,context=ssl.create_default_context(),timeout=12) as smtp:
            smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);smtp.send_message(msg)
    else:
        with smtplib.SMTP(host,port,timeout=12) as smtp:
            smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
            smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);smtp.send_message(msg)
