import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from src.celery_app import celery_app
from src.config import settings


def load_email_template(template_name: str, context: dict) -> str:
    """Load and render email template with context variables."""
    template_path = Path(__file__).parent / "email_templates" / template_name
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Simple template variable replacement
            for key, value in context.items():
                content = content.replace(f"{{{{ {key} }}}}", str(value))
            return content
    except FileNotFoundError:
        # Fallback if template not found
        return f"Template {template_name} not found. Context: {context}"


def send_email_smtp(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str = None,
) -> bool:
    """Send email using SMTP."""
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.email_sender
        msg["To"] = to_email

        # Add text and HTML parts
        if text_content:
            text_part = MIMEText(text_content, "plain")
            msg.attach(text_part)

        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)

        # Send email
        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port) as server:
            server.starttls()
            server.login(settings.email_sender, settings.email_app_password)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Error sending email to {to_email}: {str(e)}")
        return False


@celery_app.task(name="send_invitation_email")
def send_invitation_email(
    user_email: str,
    user_name: str,
    company_name: str,
    role: str,
    activation_token: str,
    expiry_date: str,
    activation_url: str = None,
):
    """Send invitation email to new user."""
    # Build activation URL if not provided
    if not activation_url:
        # Assuming frontend URL - adjust as needed
        activation_url = f"https://your-frontend.com/activate/{activation_token}"

    # Load template
    html_content = load_email_template(
        "invitation.html",
        {
            "company_name": company_name,
            "role": role,
            "activation_url": activation_url,
            "expiry_date": expiry_date,
        },
    )

    # Create text version
    text_content = f"""You've been invited!

You have been invited to join {company_name} as {role}.

Click the link below to activate your account:
{activation_url}

This invitation will expire on {expiry_date}.
"""

    # Send email
    subject = f"Invitation to join {company_name}"
    send_email_smtp(
        to_email=user_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )


@celery_app.task(name="send_welcome_email")
def send_welcome_email(user_email: str, user_name: str):
    """Send welcome email to new user."""
    # Load template
    html_content = load_email_template(
        "welcome.html",
        {
            "user_name": user_name,
        },
    )

    # Create text version
    text_content = f"""Welcome!

Thank you for joining us, {user_name}!
"""

    # Send email
    subject = "Welcome to Office World"
    send_email_smtp(
        to_email=user_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )


@celery_app.task(name="send_password_reset_email")
def send_password_reset_email(user_email: str, reset_token: str, reset_url: str = None):
    """Send password reset email."""
    # Build reset URL if not provided
    if not reset_url:
        # Assuming frontend URL - adjust as needed
        reset_url = f"https://your-frontend.com/reset-password/{reset_token}"

    # Load template
    html_content = load_email_template(
        "reset_password.html",
        {
            "reset_url": reset_url,
        },
    )

    # Create text version
    text_content = f"""Password Reset

Click the link below to reset your password:
{reset_url}

If you did not request this, please ignore this email.
"""

    # Send email
    subject = "Password Reset Request"
    send_email_smtp(
        to_email=user_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )
