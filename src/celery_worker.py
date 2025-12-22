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
            # Template uses {{ variable }} format (2 braces with spaces)
            for key, value in context.items():
                # Replace {{ variable }} format (2 braces with spaces) - most common
                content = content.replace(f"{{{{ {key} }}}}", str(value))
                # Also handle without spaces: {{variable}}
                content = content.replace(f"{{{{{key}}}}}", str(value))
                # Handle with single braces: { variable }
                content = content.replace(f"{{ {key} }}", str(value))
                # Handle without spaces: {variable}
                content = content.replace(f"{{{key}}}", str(value))
            print(f"[EMAIL TEMPLATE] Loaded template: {template_name} with context keys: {list(context.keys())}")
            return content
    except FileNotFoundError:
        # Fallback if template not found
        error_msg = f"Template {template_name} not found at {template_path}. Context: {context}"
        print(f"[EMAIL TEMPLATE ERROR] {error_msg}")
        return f"<html><body><p>{error_msg}</p></body></html>"
    except Exception as e:
        error_msg = f"Error loading template {template_name}: {str(e)}"
        print(f"[EMAIL TEMPLATE ERROR] {error_msg}")
        return f"<html><body><p>{error_msg}</p></body></html>"


def send_email_smtp(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str = None,
) -> bool:
    """Send email using SMTP."""
    try:
        print(f"[EMAIL] Attempting to send email to {to_email}")
        print(f"[EMAIL] SMTP Host: {settings.email_smtp_host}, Port: {settings.email_smtp_port}")
        print(f"[EMAIL] From: {settings.email_sender}")
        
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
        print(f"[EMAIL] Connecting to SMTP server...")
        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port) as server:
            print(f"[EMAIL] Starting TLS...")
            server.starttls()
            print(f"[EMAIL] Logging in...")
            server.login(settings.email_sender, settings.email_app_password)
            print(f"[EMAIL] Sending message...")
            server.send_message(msg)
            print(f"[EMAIL] Email sent successfully to {to_email}")

        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL ERROR] Authentication failed: {str(e)}")
        print(f"[EMAIL ERROR] Check email_sender and email_app_password in config")
        return False
    except smtplib.SMTPException as e:
        print(f"[EMAIL ERROR] SMTP error: {str(e)}")
        return False
    except Exception as e:
        print(f"[EMAIL ERROR] Unexpected error sending email to {to_email}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


@celery_app.task(name="send_invitation_email", bind=True)
def send_invitation_email(
    self,
    user_email: str,
    user_name: str,
    company_name: str,
    role: str,
    activation_token: str,
    expiry_date: str,
    activation_url: str = None,
):
    """Send invitation email to new user."""
    try:
        print(f"[CELERY TASK] send_invitation_email called for {user_email}")
        print(f"[CELERY TASK] Parameters: company={company_name}, role={role}, token={activation_token}")
        
        # Build activation URL if not provided
        if not activation_url:
            # Use frontend_url from settings if available
            if hasattr(settings, 'frontend_url'):
                activation_url = f"{settings.frontend_url}/activate/{activation_token}"
            else:
                activation_url = f"http://localhost:3000/activate/{activation_token}"

        print(f"[CELERY TASK] Activation URL: {activation_url}")

        # Load template
        html_content = load_email_template(
            "invitation.html",
            {
                "user_email": user_email,
                "user_name": user_name,
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
        result = send_email_smtp(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
        
        if result:
            print(f"[CELERY TASK] Email sent successfully to {user_email}")
        else:
            print(f"[CELERY TASK] Failed to send email to {user_email}")
            
        return result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_invitation_email: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_welcome_email")
def send_welcome_email(user_email: str, user_name: str):
    """Send welcome email to new user."""
    try:
        print(f"[CELERY TASK] send_welcome_email called for {user_email}")
        
        # Load template
        html_content = load_email_template(
            "welcome.html",
            {
                "user_email": user_email,
                "user_name": user_name,
            },
        )

        # Create text version
        text_content = f"""Welcome to Office World!

Hello {user_name},

Thank you for joining us! Your account has been successfully activated.

We're excited to have you on board and look forward to working with you.

If you have any questions or need assistance, please don't hesitate to reach out to our support team.

Best regards,
The Office World Team
"""

        # Send email
        subject = "Welcome to Office World!"
        result = send_email_smtp(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
        
        if result:
            print(f"[CELERY TASK] Welcome email sent successfully to {user_email}")
        else:
            print(f"[CELERY TASK] Failed to send welcome email to {user_email}")
            
        return result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_welcome_email: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_password_reset_email")
def send_password_reset_email(user_email: str, reset_token: str, reset_url: str = None):
    """Send password reset email."""
    try:
        print(f"[CELERY TASK] send_password_reset_email called for {user_email}")
        
        # Build reset URL if not provided
        if not reset_url:
            # Use frontend_url from settings if available
            if hasattr(settings, 'frontend_url'):
                reset_url = f"{settings.frontend_url}/reset-password/{reset_token}"
            else:
                reset_url = f"http://localhost:3000/reset-password/{reset_token}"  # Fallback

        print(f"[CELERY TASK] Reset URL: {reset_url}")

        # Get user name from email (fallback)
        user_name = user_email.split("@")[0] if user_email else "User"

        # Load template
        html_content = load_email_template(
            "reset_password.html",
            {
                "user_email": user_email,
                "user_name": user_name,
                "reset_url": reset_url,
                "reset_token": reset_token,
            },
        )

        # Create text version
        text_content = f"""Password Reset Request

Hello {user_name},

You requested to reset your password for your account.

Click the link below to reset your password:
{reset_url}

This link will expire in 24 hours.

If you did not request this password reset, please ignore this email and your password will remain unchanged.
"""

        # Send email
        subject = "Password Reset Request"
        result = send_email_smtp(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
        
        if result:
            print(f"[CELERY TASK] Password reset email sent successfully to {user_email}")
        else:
            print(f"[CELERY TASK] Failed to send password reset email to {user_email}")
            
        return result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_password_reset_email: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
