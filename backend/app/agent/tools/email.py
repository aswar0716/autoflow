"""
Email sending tool powered by SendGrid.

SendGrid is an industry-standard transactional email API. Using it here
teaches the pattern of wrapping external APIs as LangChain tools so the
agent can trigger real-world side effects autonomously.
"""

import os
import json
from langchain_core.tools import tool
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


@tool
def send_email(payload: str) -> str:
    """
    Send an email via SendGrid.

    Input must be a JSON string with keys:
      - to: recipient email address
      - subject: email subject line
      - body: plain-text email body

    Example input:
      {"to": "client@example.com", "subject": "Follow-up", "body": "Hi ..."}

    Returns a success or error message.
    """
    try:
        data = json.loads(payload)
        to_email = data["to"]
        subject = data["subject"]
        body = data["body"]
    except (json.JSONDecodeError, KeyError) as e:
        return f"Error: invalid input. Expected JSON with 'to', 'subject', 'body'. Got: {e}"

    from_email = os.getenv("SENDGRID_FROM_EMAIL")
    api_key = os.getenv("SENDGRID_API_KEY")

    if not api_key or not from_email:
        return "Error: SENDGRID_API_KEY or SENDGRID_FROM_EMAIL not configured."

    try:
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=body,
        )
        client = SendGridAPIClient(api_key)
        response = client.send(message)
        return f"Email sent successfully. Status: {response.status_code}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"
