"""
email_service.py — Send automated return decision emails via SMTP (MailHog in dev).

Emails are sent asynchronously using asyncio.to_thread to avoid blocking the worker.
All emails are viewable at http://localhost:8025 (MailHog Web UI).
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


# ── HTML Email Templates ─────────────────────────────────────────────────────

def _base_template(title: str, accent_color: str, icon: str, body_html: str) -> str:
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0f0f1a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f1a;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#1a1a2e;border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,0.06);">
        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,{accent_color},#1a1a2e);padding:32px 40px;text-align:center;">
          <div style="font-size:40px;margin-bottom:8px;">{icon}</div>
          <h1 style="color:#fff;margin:0;font-size:24px;font-weight:700;">{title}</h1>
        </td></tr>
        <!-- Body -->
        <tr><td style="padding:32px 40px;color:#e0e0e0;font-size:15px;line-height:1.7;">
          {body_html}
        </td></tr>
        <!-- Footer -->
        <tr><td style="padding:20px 40px 28px;text-align:center;border-top:1px solid rgba(255,255,255,0.06);">
          <p style="color:#666;font-size:12px;margin:0;">
            ReturnGuard AI &mdash; Automated Return Processing<br>
            This is an automated message. Do not reply.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _approved_email(product_name: str, amount: float, explanation: str, return_id: str) -> str:
    body = f"""\
    <p>Great news! Your return request has been <strong style="color:#22c55e;">approved</strong>.</p>
    <table width="100%" cellpadding="12" cellspacing="0" style="background:rgba(34,197,94,0.08);border-radius:12px;border:1px solid rgba(34,197,94,0.2);margin:16px 0;">
      <tr><td style="color:#999;font-size:13px;">Product</td><td style="color:#fff;text-align:right;">{product_name}</td></tr>
      <tr><td style="color:#999;font-size:13px;">Refund Amount</td><td style="color:#22c55e;text-align:right;font-weight:700;">${amount:.2f}</td></tr>
      <tr><td style="color:#999;font-size:13px;">Return ID</td><td style="color:#888;text-align:right;font-family:monospace;font-size:13px;">{return_id[:8]}</td></tr>
    </table>
    <p style="color:#ccc;">{explanation}</p>
    <p style="color:#888;font-size:13px;">Your refund will be processed within <strong>5-7 business days</strong>.</p>"""
    return _base_template("Return Approved ✓", "#22c55e", "✅", body)


def _denied_email(product_name: str, amount: float, explanation: str, return_id: str) -> str:
    body = f"""\
    <p>We've reviewed your return request and unfortunately it has been <strong style="color:#ef4444;">denied</strong>.</p>
    <table width="100%" cellpadding="12" cellspacing="0" style="background:rgba(239,68,68,0.08);border-radius:12px;border:1px solid rgba(239,68,68,0.2);margin:16px 0;">
      <tr><td style="color:#999;font-size:13px;">Product</td><td style="color:#fff;text-align:right;">{product_name}</td></tr>
      <tr><td style="color:#999;font-size:13px;">Amount</td><td style="color:#ef4444;text-align:right;font-weight:700;">${amount:.2f}</td></tr>
      <tr><td style="color:#999;font-size:13px;">Return ID</td><td style="color:#888;text-align:right;font-family:monospace;font-size:13px;">{return_id[:8]}</td></tr>
    </table>
    <p style="color:#ccc;">{explanation}</p>
    <p style="color:#888;font-size:13px;">If you believe this decision was made in error, please contact our support team.</p>"""
    return _base_template("Return Denied", "#ef4444", "❌", body)


def _escalated_email(product_name: str, amount: float, explanation: str, return_id: str) -> str:
    body = f"""\
    <p>Your return request requires additional review and has been <strong style="color:#f59e0b;">escalated</strong> to our team.</p>
    <table width="100%" cellpadding="12" cellspacing="0" style="background:rgba(245,158,11,0.08);border-radius:12px;border:1px solid rgba(245,158,11,0.2);margin:16px 0;">
      <tr><td style="color:#999;font-size:13px;">Product</td><td style="color:#fff;text-align:right;">{product_name}</td></tr>
      <tr><td style="color:#999;font-size:13px;">Amount</td><td style="color:#f59e0b;text-align:right;font-weight:700;">${amount:.2f}</td></tr>
      <tr><td style="color:#999;font-size:13px;">Return ID</td><td style="color:#888;text-align:right;font-family:monospace;font-size:13px;">{return_id[:8]}</td></tr>
    </table>
    <p style="color:#ccc;">{explanation}</p>
    <p style="color:#888;font-size:13px;">A team member will review your case within <strong>24 hours</strong>.</p>"""
    return _base_template("Under Review", "#f59e0b", "🔍", body)


# ── Public API ───────────────────────────────────────────────────────────────

EMAIL_BUILDERS = {
    "approved": _approved_email,
    "denied": _denied_email,
    "escalated": _escalated_email,
}

SUBJECT_MAP = {
    "approved": "✅ Your return has been approved — ReturnGuard",
    "denied": "Return request update — ReturnGuard",
    "escalated": "🔍 Your return is under review — ReturnGuard",
}


def send_decision_email(
    to_email: str,
    decision: str,
    product_name: str,
    amount: float,
    explanation: str,
    return_id: str,
):
    """Send an HTML email for the given decision type (approved/denied/escalated)."""
    builder = EMAIL_BUILDERS.get(decision)
    if not builder:
        print(f"⚠️  Unknown decision type for email: {decision}")
        return

    html_content = builder(product_name, amount, explanation, return_id)
    subject = SUBJECT_MAP[decision]

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.sendmail(settings.email_from, to_email, msg.as_string())
        print(f"📧 Email sent to {to_email} — {decision.upper()}")
    except Exception as e:
        print(f"⚠️  Failed to send email: {e}")
