"""
Send TONIGHT.md as a formatted HTML email via Gmail SMTP.
Credentials come from environment variables:
  - GMAIL_ADDRESS: your Gmail address (also used as recipient)
  - GMAIL_APP_PASSWORD: 16-char app password from Google
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import markdown


def send_battle_plan_email():
    """Read TONIGHT.md, convert to HTML, and send via Gmail SMTP."""

    # Check if TONIGHT.md exists
    if not os.path.exists("TONIGHT.md"):
        print("TONIGHT.md not found — skipping email.")
        return

    # Check credentials
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        print("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — skipping email.")
        return

    # Read markdown content
    with open("TONIGHT.md", "r", encoding="utf-8") as f:
        md_content = f.read()

    # Convert markdown to HTML
    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "nl2br"],
    )

    # Wrap in a clean email template
    html_email = f"""\
<html>
<head>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: 0 auto; padding: 20px; }}
    h1 {{ color: #1a1a2e; border-bottom: 2px solid #e94560; padding-bottom: 10px; }}
    h2 {{ color: #16213e; margin-top: 30px; }}
    h3 {{ color: #0f3460; }}
    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
    th {{ background-color: #16213e; color: white; }}
    tr:nth-child(even) {{ background-color: #f9f9f9; }}
    a {{ color: #e94560; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    ul {{ padding-left: 20px; }}
    li {{ margin-bottom: 8px; }}
    hr {{ border: none; border-top: 1px solid #eee; margin: 30px 0; }}
    strong {{ color: #1a1a2e; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    # Build email
    today = datetime.now().strftime("%B %d, %Y")
    subject = f"\U0001f3af Tonight's Battle Plan — {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = gmail_address

    # Attach both plain text and HTML versions
    msg.attach(MIMEText(md_content, "plain"))
    msg.attach(MIMEText(html_email, "html"))

    # Send via Gmail SMTP
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, gmail_address, msg.as_string())

    print(f"Email sent to {gmail_address}")


if __name__ == "__main__":
    send_battle_plan_email()
