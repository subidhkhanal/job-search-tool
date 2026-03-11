"""
Send job scrape results as a formatted HTML email via Gmail SMTP.
Also saves the same HTML to Supabase so the frontend can display it.

Credentials (env vars):
  - GMAIL_ADDRESS: your Gmail address
  - GMAIL_APP_PASSWORD: 16-char app password from Google
"""

import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown


def _build_html(md_content: str) -> str:
    """Convert markdown to styled HTML for email."""
    body_html = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "nl2br"],
    )

    html = f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 800px; margin: 0 auto; padding: 20px;
    background: #ffffff; color: #1a1a1a;
  }}
  table {{
    border-collapse: collapse; width: 100%; margin: 12px 0;
    font-size: 13px;
  }}
  th {{
    background: #f1f5f9; color: #1e293b; padding: 8px 10px;
    text-align: left; border: 1px solid #e2e8f0;
    font-weight: 600;
  }}
  td {{
    padding: 6px 10px; border: 1px solid #e2e8f0;
    background: #ffffff;
  }}
  tr:nth-child(even) td {{ background: #f8fafc; }}
  a {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""
    return html


def _detect_paid_status(text):
    """Detect if internship is paid or unpaid from description."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["unpaid", "no stipend", "voluntary", "volunteer"]):
        return "Unpaid"
    if any(kw in text_lower for kw in [
        "paid", "stipend", "salary", "compensation", "ctc",
        "per month", "/month", "lpa", "inr", "usd", "$",
    ]):
        return "Paid"
    return "-"


def _detect_duration(text):
    """Extract internship duration from description."""
    text_lower = text.lower()
    # Match patterns like "3 months", "6-month", "2 month duration"
    match = re.search(r'(\d+)\s*[-–]?\s*months?', text_lower)
    if match:
        return f"{match.group(1)} months"
    match = re.search(r'(\d+)\s*[-–]?\s*weeks?', text_lower)
    if match:
        return f"{match.group(1)} weeks"
    match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*months?', text_lower)
    if match:
        return f"{match.group(1)}-{match.group(2)} months"
    return "-"


def _job_row(j: dict) -> str:
    """Build a single markdown table row matching the website card fields."""
    title   = j.get("title", "Untitled").replace("|", "/").strip()[:50]
    company = j.get("company", "-").replace("|", "/").strip()[:25]
    location = j.get("location", "-").replace("|", "/").strip()[:20]
    score   = j.get("score", 0)
    verdict = (j.get("verdict") or "-").replace("|", "/").strip()[:15]
    ats     = j.get("ats_score") or "-"
    mode    = (j.get("work_mode") or "-").replace("|", "/").strip()[:10]
    source  = j.get("source", "-").replace("|", "/").strip()[:15]
    url     = j.get("url", "")
    link    = f"[Apply]({url})" if url else "-"
    reason  = (j.get("llm_reason") or "").replace("|", "/").strip()[:80]
    reason_cell = f"_{reason}_" if reason else "-"
    return f"| {title} | {company} | {location} | {mode} | {verdict} | {score} | {ats} | {source} | {reason_cell} | {link} |"


_TABLE_HEADER = "| Title | Company | Location | Mode | Verdict | Score | ATS | Source | Reason | Link |"
_TABLE_SEP    = "|-------|---------|----------|------|---------|-------|-----|--------|--------|------|"


def build_email_content(jobs, sources_status, sources_errors=None):
    """Build markdown table for the email — identical to the website job cards."""
    lines = []

    if not jobs:
        lines.append("No new internships found.")
        return "\n".join(lines)

    # Only show jobs that passed the filter (same as the website)
    filtered_jobs = [j for j in jobs if j.get("filtered", True)]

    if not filtered_jobs:
        lines.append("No new internships found.")
        return "\n".join(lines)

    lines.append(f"### New Jobs ({len(filtered_jobs)})")
    lines.append("")
    lines.append(_TABLE_HEADER)
    lines.append(_TABLE_SEP)
    for j in filtered_jobs:
        lines.append(_job_row(j))

    return "\n".join(lines)


def get_alert_number():
    """Get the next alert number from existing email logs."""
    try:
        from tracker import get_email_logs
        logs = get_email_logs(limit=1)
        if logs:
            # Extract number from last subject like "Job Alert #5"
            last_subject = logs[0].get("subject", "")
            match = re.search(r'#(\d+)', last_subject)
            if match:
                return int(match.group(1)) + 1
        return 1
    except Exception:
        return 1


def send_email(md_content: str, alert_number: int = 1) -> bool:
    """
    Send the markdown content as an HTML email via Gmail SMTP.
    Returns True on success, False on failure.
    """
    gmail_addr = os.environ.get("GMAIL_ADDRESS", "")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not gmail_addr or not gmail_pass:
        print("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — skipping email.")
        return False

    subject = f"Job Alert #{alert_number}"

    html_content = _build_html(md_content)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_addr
    msg["To"] = gmail_addr

    msg.attach(MIMEText(md_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_addr, gmail_pass)
            server.sendmail(gmail_addr, gmail_addr, msg.as_string())
        print(f"Email sent to {gmail_addr}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
