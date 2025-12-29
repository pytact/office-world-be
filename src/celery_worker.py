import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from uuid import UUID
from datetime import datetime
from src.celery_app import celery_app
from src.config import settings
from src.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

# Import ALL models to ensure foreign key relationships are resolved in Base.metadata
# This is CRITICAL for SQLAlchemy to resolve foreign keys at runtime in Celery workers
# If any model is missing, foreign key resolution will fail with NoReferencedTableError
from src.users.models import User
from src.companies.models import Company
from src.employees.models import Employee
from src.permissions.models import Role, UserRoleAssignment
from src.leaves.models import LeaveRequest
from src.tasks.models import Task
from src.projects.models import Project
from src.salaries.models import BankInfo, SalaryDetails, SalaryPayment, SalaryHistory
from src.notifications.models import Notification

# Force metadata initialization by accessing model tables
# This ensures all imported models are registered with Base.metadata
# Accessing __table__ forces SQLAlchemy to register the table in metadata
_ = User.__table__
_ = Company.__table__
_ = Employee.__table__
_ = Role.__table__
_ = UserRoleAssignment.__table__
_ = LeaveRequest.__table__
_ = Task.__table__
_ = Project.__table__
_ = BankInfo.__table__
_ = SalaryDetails.__table__
_ = SalaryPayment.__table__
_ = SalaryHistory.__table__
_ = Notification.__table__

from src.notifications.constants import (
    CHANNEL_EMAIL,
    CHANNEL_IN_APP,
    STATUS_SENT,
    STATUS_FAILED,
    NOTIFICATION_TYPE_LEAVE_REQUEST,
    NOTIFICATION_TYPE_LEAVE_APPROVAL,
    NOTIFICATION_TYPE_LEAVE_REJECTION,
    NOTIFICATION_TYPE_LEAVE_MANAGER_APPROVAL,
    NOTIFICATION_TYPE_TASK_CREATED,
    NOTIFICATION_TYPE_TASK_UPDATED,
    NOTIFICATION_TYPE_TASK_ASSIGNMENT,
    NOTIFICATION_TYPE_TASK_UNASSIGNMENT,
    NOTIFICATION_TYPE_TASK_PERMISSION_CHANGE,
    NOTIFICATION_TYPE_TASK_STATUS_CHANGE,
    NOTIFICATION_TYPE_TASK_DELETED,
    RELATED_TABLE_LEAVES,
    RELATED_TABLE_TASKS,
)


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


def create_notification_records(
    user_id: UUID,
    company_id: UUID,
    notification_type: str,
    title: str,
    message: str,
    related_record_id: UUID = None,
    related_table: str = None,
    data: dict = None,
    create_email: bool = True,
    create_in_app: bool = True,
) -> None:
    """Create notification records (email and/or in-app) from Celery tasks.
    
    Uses synchronous database operations to avoid event loop conflicts in Celery workers.
    Celery tasks are synchronous by nature, so we use sync SQLAlchemy instead of async.
    
    Can create:
    1. Email channel notification (status='sent' or 'failed')
    2. In-app channel notification (status='sent', is_read=False)
    
    Args:
        create_email: If True, create email notification record
        create_in_app: If True, create in-app notification record (always created regardless of email success)
    """
    try:
        # Convert async database URL to sync (replace postgresql+asyncpg with postgresql+psycopg2)
        sync_database_url = settings.database_url.replace(
            "postgresql+asyncpg://", 
            "postgresql+psycopg2://"
        ).replace(
            "postgresql://",
            "postgresql+psycopg2://"
        )
        
        # Create a synchronous engine (no event loop issues)
        # Use NullPool to avoid keeping connections between tasks
        sync_engine = create_engine(
            sync_database_url,
            poolclass=NullPool,
            echo=False,
        )
        
        # Create session maker
        SyncSessionLocal = sessionmaker(
            bind=sync_engine,
            class_=Session,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        # Create session and add notifications
        with SyncSessionLocal() as session:
            try:
                # Create email notification record (if requested)
                if create_email:
                    email_notification = Notification(
                        user_id=user_id,
                        company_id=company_id,
                        type=notification_type,
                        title=title,
                        message=message,
                        channel=CHANNEL_EMAIL,
                        status=STATUS_SENT,
                        related_record_id=related_record_id,
                        related_table=related_table,
                        data=data,
                    )
                    session.add(email_notification)
                    print(f"[NOTIFICATION] Created email notification for user {user_id}, type {notification_type}")
                
                # Create in-app notification record (always created for in-app visibility)
                if create_in_app:
                    in_app_notification = Notification(
                        user_id=user_id,
                        company_id=company_id,
                        type=notification_type,
                        title=title,
                        message=message,
                        channel=CHANNEL_IN_APP,
                        status=STATUS_SENT,
                        is_read=False,
                        related_record_id=related_record_id,
                        related_table=related_table,
                        data=data,
                    )
                    session.add(in_app_notification)
                    print(f"[NOTIFICATION] Created in-app notification for user {user_id}, type {notification_type}")
                
                # Commit the transaction
                session.commit()
                print(f"[NOTIFICATION] ✅ Successfully committed notification records")
                
            except Exception as e:
                session.rollback()
                print(f"[NOTIFICATION ERROR] Database error, rolled back: {str(e)}")
                raise
        
        # Dispose of the engine to clean up connections
        sync_engine.dispose()
            
    except Exception as e:
        print(f"[NOTIFICATION ERROR] Failed to create notification records: {str(e)}")
        import traceback
        traceback.print_exc()
        # Don't raise - we don't want notification creation failure to break the task


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


# Leave Management Notification Tasks (F9_api_spec.md Section 5.1)

@celery_app.task(name="send_leave_created_notification")
def send_leave_created_notification(
    manager_email: str,
    manager_name: str,
    manager_user_id: str,
    applicant_name: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    company_id: str,
    company_name: str,
    leave_id: str,
):
    """Send notification when leave request is created (to manager approver).
    
    Creates in-app notification immediately, then attempts to send email.
    Creates email notification record only if email sending succeeds.
    """
    try:
        print(f"[CELERY TASK] ===== send_leave_created_notification STARTED =====")
        print(f"[CELERY TASK] Manager Email: {manager_email}")
        print(f"[CELERY TASK] Manager User ID: {manager_user_id}")
        print(f"[CELERY TASK] Company ID: {company_id}")
        print(f"[CELERY TASK] Leave ID: {leave_id}")

        # Load template (reuse invitation template structure or create leave-specific)
        html_content = f"""
        <html>
        <body>
        <h2>New Leave Request Submitted</h2>
        <p>Hello {manager_name},</p>
        <p>A new leave request has been submitted for your approval:</p>
        <ul>
        <li><strong>Applicant:</strong> {applicant_name}</li>
        <li><strong>Leave Type:</strong> {leave_type}</li>
        <li><strong>Duration:</strong> {start_date} to {end_date}</li>
        <li><strong>Company:</strong> {company_name}</li>
        </ul>
        <p>Please review and approve/reject the leave request in the system.</p>
        <p>Best regards,<br>The {company_name} Team</p>
        </body>
        </html>
        """

        # Create text version
        text_content = f"""New Leave Request Submitted

Hello {manager_name},

A new leave request has been submitted for your approval:

Applicant: {applicant_name}
Leave Type: {leave_type}
Duration: {start_date} to {end_date}
Company: {company_name}

Please review and approve/reject the leave request in the system.

Best regards,
The {company_name} Team
"""

        # Prepare notification data
        title = f"New Leave Request from {applicant_name}"
        message = f"A new leave request has been submitted for your approval:\n\nApplicant: {applicant_name}\nLeave Type: {leave_type}\nDuration: {start_date} to {end_date}"
        
        # Always create in-app notification (regardless of email success)
        # This ensures users see notifications in the app even if email fails
        try:
            create_notification_records(
                user_id=UUID(manager_user_id),
                company_id=UUID(company_id),
                notification_type=NOTIFICATION_TYPE_LEAVE_REQUEST,
                title=title,
                message=message,
                related_record_id=UUID(leave_id),
                related_table=RELATED_TABLE_LEAVES,
                data={
                    "applicant_name": applicant_name,
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                create_email=False,  # Email notification created separately based on email result
                create_in_app=True,   # Always create in-app notification
            )
        except Exception as e:
            print(f"[CELERY TASK WARNING] Failed to create in-app notification: {str(e)}")
            # Continue with email sending even if notification creation fails
        
        # Send email
        subject = f"New Leave Request from {applicant_name}"
        email_result = send_email_smtp(
            to_email=manager_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

        if email_result:
            print(f"[CELERY TASK] ✅ EMAIL SENT: {manager_email}")
            print(f"[CELERY TASK] Leave created notification email sent to: {manager_email} (User ID: {manager_user_id})")
            
            # Create email notification record after successful email
            try:
                create_notification_records(
                    user_id=UUID(manager_user_id),
                    company_id=UUID(company_id),
                    notification_type=NOTIFICATION_TYPE_LEAVE_REQUEST,
                    title=title,
                    message=message,
                    related_record_id=UUID(leave_id),
                    related_table=RELATED_TABLE_LEAVES,
                    data={
                        "applicant_name": applicant_name,
                        "leave_type": leave_type,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                    create_email=True,   # Create email notification
                    create_in_app=False, # In-app already created above
                )
                print(f"[CELERY TASK] ✅ NOTIFICATION RECORD CREATED for manager: {manager_user_id}")
            except Exception as e:
                print(f"[CELERY TASK WARNING] Failed to create email notification record: {str(e)}")
        else:
            print(f"[CELERY TASK] ❌ EMAIL FAILED TO MANAGER: {manager_email}")
            print(f"[CELERY TASK] Failed to send leave created notification email to {manager_email}")
            # Note: In-app notification was already created above, so user will still see it

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_leave_created_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_leave_approved_notification")
def send_leave_approved_notification(
    recipient_email: str,
    recipient_name: str,
    recipient_user_id: str,
    applicant_name: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    approved_by: str,
    company_id: str,
    company_name: str,
    approval_stage: str,
    leave_id: str,
    notification_type: str = None,
):
    """Send notification when leave request is approved.
    
    After successful email sending, creates both email and in-app notification records.
    notification_type should be either 'leave_approval' or 'leave_manager_approval'.
    """
    try:
        print(f"[CELERY TASK] send_leave_approved_notification to {recipient_email}")

        html_content = f"""
        <html>
        <body>
        <h2>Leave Request Approved</h2>
        <p>Hello {recipient_name},</p>
        <p>A leave request has been approved:</p>
        <ul>
        <li><strong>Applicant:</strong> {applicant_name}</li>
        <li><strong>Leave Type:</strong> {leave_type}</li>
        <li><strong>Duration:</strong> {start_date} to {end_date}</li>
        <li><strong>Approved By:</strong> {approved_by}</li>
        <li><strong>Approval Stage:</strong> {approval_stage}</li>
        <li><strong>Company:</strong> {company_name}</li>
        </ul>
        <p>The leave request is now active.</p>
        <p>Best regards,<br>The {company_name} Team</p>
        </body>
        </html>
        """

        text_content = f"""Leave Request Approved

Hello {recipient_name},

A leave request has been approved:

Applicant: {applicant_name}
Leave Type: {leave_type}
Duration: {start_date} to {end_date}
Approved By: {approved_by}
Approval Stage: {approval_stage}
Company: {company_name}

The leave request is now active.

Best regards,
The {company_name} Team
"""

        subject = f"Leave Request Approved for {applicant_name}"
        email_result = send_email_smtp(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

        if email_result:
            print(f"[CELERY TASK] Leave approved notification sent to {recipient_email}")
            
            # Determine notification type
            notif_type = notification_type if notification_type else NOTIFICATION_TYPE_LEAVE_APPROVAL
            
            # Create notification records after successful email
            title = f"Leave Request Approved for {applicant_name}"
            message = f"A leave request has been approved:\n\nApplicant: {applicant_name}\nLeave Type: {leave_type}\nDuration: {start_date} to {end_date}\nApproved By: {approved_by}\nApproval Stage: {approval_stage}"
            
            create_notification_records(
                user_id=UUID(recipient_user_id),
                company_id=UUID(company_id),
                notification_type=notif_type,
                title=title,
                message=message,
                related_record_id=UUID(leave_id),
                related_table=RELATED_TABLE_LEAVES,
                data={
                    "applicant_name": applicant_name,
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "approved_by": approved_by,
                    "approval_stage": approval_stage,
                },
            )
        else:
            print(f"[CELERY TASK] Failed to send leave approved notification to {recipient_email}")

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_leave_approved_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_leave_rejected_notification")
def send_leave_rejected_notification(
    applicant_email: str,
    applicant_name: str,
    applicant_user_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    rejected_by: str,
    rejection_reason: str,
    company_id: str,
    company_name: str,
    rejection_stage: str,
    leave_id: str,
):
    """Send notification when leave request is rejected.
    
    After successful email sending, creates both email and in-app notification records.
    """
    try:
        print(f"[CELERY TASK] send_leave_rejected_notification to {applicant_email}")

        html_content = f"""
        <html>
        <body>
        <h2>Leave Request Rejected</h2>
        <p>Hello {applicant_name},</p>
        <p>Your leave request has been rejected:</p>
        <ul>
        <li><strong>Leave Type:</strong> {leave_type}</li>
        <li><strong>Requested Duration:</strong> {start_date} to {end_date}</li>
        <li><strong>Rejected By:</strong> {rejected_by}</li>
        <li><strong>Rejection Stage:</strong> {rejection_stage}</li>
        <li><strong>Reason:</strong> {rejection_reason}</li>
        <li><strong>Company:</strong> {company_name}</li>
        </ul>
        <p>You can submit a new leave request or contact your manager for more information.</p>
        <p>Best regards,<br>The {company_name} Team</p>
        </body>
        </html>
        """

        text_content = f"""Leave Request Rejected

Hello {applicant_name},

Your leave request has been rejected:

Leave Type: {leave_type}
Requested Duration: {start_date} to {end_date}
Rejected By: {rejected_by}
Rejection Stage: {rejection_stage}
Reason: {rejection_reason}
Company: {company_name}

You can submit a new leave request or contact your manager for more information.

Best regards,
The {company_name} Team
"""

        subject = "Leave Request Rejected"
        email_result = send_email_smtp(
            to_email=applicant_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

        if email_result:
            print(f"[CELERY TASK] Leave rejected notification sent to {applicant_email}")
            
            # Create notification records after successful email
            title = "Leave Request Rejected"
            message = f"Your leave request has been rejected:\n\nLeave Type: {leave_type}\nRequested Duration: {start_date} to {end_date}\nRejected By: {rejected_by}\nRejection Stage: {rejection_stage}\nReason: {rejection_reason}"
            
            create_notification_records(
                user_id=UUID(applicant_user_id),
                company_id=UUID(company_id),
                notification_type=NOTIFICATION_TYPE_LEAVE_REJECTION,
                title=title,
                message=message,
                related_record_id=UUID(leave_id),
                related_table=RELATED_TABLE_LEAVES,
                data={
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "rejected_by": rejected_by,
                    "rejection_stage": rejection_stage,
                    "rejection_reason": rejection_reason,
                },
            )
        else:
            print(f"[CELERY TASK] Failed to send leave rejected notification to {applicant_email}")

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_leave_rejected_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_leave_cancelled_notification")
def send_leave_cancelled_notification(
    recipient_email: str,
    recipient_name: str,
    recipient_user_id: str,
    applicant_name: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    company_id: str,
    company_name: str,
    leave_id: str,
):
    """Send notification when leave request is cancelled (to manager and HR approvers).
    
    After successful email sending, creates both email and in-app notification records.
    """
    try:
        print(f"[CELERY TASK] send_leave_cancelled_notification to {recipient_email}")

        html_content = f"""
        <html>
        <body>
        <h2>Leave Request Cancelled</h2>
        <p>Hello {recipient_name},</p>
        <p>A leave request has been cancelled:</p>
        <ul>
        <li><strong>Applicant:</strong> {applicant_name}</li>
        <li><strong>Leave Type:</strong> {leave_type}</li>
        <li><strong>Requested Duration:</strong> {start_date} to {end_date}</li>
        <li><strong>Company:</strong> {company_name}</li>
        </ul>
        <p>The leave request has been cancelled by the applicant.</p>
        <p>Best regards,<br>The {company_name} Team</p>
        </body>
        </html>
        """

        text_content = f"""Leave Request Cancelled

Hello {recipient_name},

A leave request has been cancelled:

Applicant: {applicant_name}
Leave Type: {leave_type}
Requested Duration: {start_date} to {end_date}
Company: {company_name}

The leave request has been cancelled by the applicant.

Best regards,
The {company_name} Team
"""

        subject = f"Leave Request Cancelled - {applicant_name}"
        email_result = send_email_smtp(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

        if email_result:
            print(f"[CELERY TASK] Leave cancelled notification sent to {recipient_email}")
            
            # Create notification records after successful email
            title = f"Leave Request Cancelled - {applicant_name}"
            message = f"A leave request has been cancelled:\n\nApplicant: {applicant_name}\nLeave Type: {leave_type}\nRequested Duration: {start_date} to {end_date}"
            
            create_notification_records(
                user_id=UUID(recipient_user_id),
                company_id=UUID(company_id),
                notification_type=NOTIFICATION_TYPE_LEAVE_REQUEST,  # Using leave_request type for cancellation
                title=title,
                message=message,
                related_record_id=UUID(leave_id),
                related_table=RELATED_TABLE_LEAVES,
                data={
                    "applicant_name": applicant_name,
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "action": "cancelled",
                },
            )
        else:
            print(f"[CELERY TASK] Failed to send leave cancelled notification to {recipient_email}")

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_leave_cancelled_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


# ============================================================================
# Task Management Notification Tasks (F8_api_spec.md)
# ============================================================================

@celery_app.task(name="send_task_created_notification")
def send_task_created_notification(
    recipient_email: str,
    recipient_name: str,
    recipient_user_id: str,
    task_id: str,
    task_name: str,
    task_description: str,
    owner_name: str,
    project_name: str,
    company_id: str,
    company_name: str,
    is_owner: bool = False,
):
    """Send notification when task is created.
    
    Sends to:
    - Owner: Confirmation notification
    - Assignees: Assignment notification
    """
    try:
        print(f"[CELERY TASK] ===== send_task_created_notification STARTED =====")
        print(f"[CELERY TASK] Recipient Email: {recipient_email}")
        print(f"[CELERY TASK] Task ID: {task_id}")
        print(f"[CELERY TASK] Is Owner: {is_owner}")

        if is_owner:
            # Notification to owner (confirmation)
            html_content = f"""
            <html>
            <body>
            <h2>✅ Task Created Successfully</h2>
            <p>Hello {recipient_name},</p>
            <p>Your task has been created successfully:</p>
            <ul>
            <li><strong>Task:</strong> {task_name}</li>
            <li><strong>Description:</strong> {task_description or 'No description provided'}</li>
            <li><strong>Project:</strong> {project_name or 'No project linked'}</li>
            <li><strong>Company:</strong> {company_name}</li>
            </ul>
            <p>You can now manage this task and assign it to team members.</p>
            <p>Best regards,<br>The {company_name} Team</p>
            </body>
            </html>
            """
            title = f"Task Created: {task_name}"
            message = f"Your task '{task_name}' has been created successfully."
        else:
            # Notification to assignee
            html_content = f"""
            <html>
            <body>
            <h2>📋 New Task Assigned to You</h2>
            <p>Hello {recipient_name},</p>
            <p>You have been assigned to a new task:</p>
            <ul>
            <li><strong>Task:</strong> {task_name}</li>
            <li><strong>Description:</strong> {task_description or 'No description provided'}</li>
            <li><strong>Owner:</strong> {owner_name}</li>
            <li><strong>Project:</strong> {project_name or 'No project linked'}</li>
            <li><strong>Company:</strong> {company_name}</li>
            </ul>
            <p>Please review the task details and start working on it.</p>
            <p>Best regards,<br>The {company_name} Team</p>
            </body>
            </html>
            """
            title = f"New Task Assigned: {task_name}"
            message = f"You have been assigned to task '{task_name}' by {owner_name}."

        # Create in-app notification
        try:
            create_notification_records(
                user_id=UUID(recipient_user_id),
                company_id=UUID(company_id),
                notification_type=NOTIFICATION_TYPE_TASK_CREATED,
                title=title,
                message=message,
                related_record_id=UUID(task_id),
                related_table=RELATED_TABLE_TASKS,
                data={
                    "task_name": task_name,
                    "owner_name": owner_name,
                    "project_name": project_name,
                },
                create_email=False,
                create_in_app=True,
            )
        except Exception as e:
            print(f"[CELERY TASK WARNING] Failed to create in-app notification: {str(e)}")

        # Send email
        subject = title
        email_result = send_email_smtp(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=html_content,  # Simplified for now
        )

        if email_result:
            print(f"[CELERY TASK] ✅ EMAIL SENT: {recipient_email}")
            try:
                create_notification_records(
                    user_id=UUID(recipient_user_id),
                    company_id=UUID(company_id),
                    notification_type=NOTIFICATION_TYPE_TASK_CREATED,
                    title=title,
                    message=message,
                    related_record_id=UUID(task_id),
                    related_table=RELATED_TABLE_TASKS,
                    data={
                        "task_name": task_name,
                        "owner_name": owner_name,
                        "project_name": project_name,
                    },
                    create_email=True,
                    create_in_app=False,
                )
            except Exception as e:
                print(f"[CELERY TASK WARNING] Failed to create email notification record: {str(e)}")
        else:
            print(f"[CELERY TASK] ❌ EMAIL FAILED: {recipient_email}")

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_task_created_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_task_updated_notification")
def send_task_updated_notification(
    recipient_email: str,
    recipient_name: str,
    recipient_user_id: str,
    task_id: str,
    task_name: str,
    updated_by_name: str,
    updated_fields: str,
    company_id: str,
    company_name: str,
):
    """Send notification when task details are updated."""
    try:
        print(f"[CELERY TASK] ===== send_task_updated_notification STARTED =====")
        print(f"[CELERY TASK] Recipient Email: {recipient_email}")
        print(f"[CELERY TASK] Task ID: {task_id}")

        html_content = f"""
        <html>
        <body>
        <h2>📝 Task Updated</h2>
        <p>Hello {recipient_name},</p>
        <p>A task you're involved with has been updated:</p>
        <ul>
        <li><strong>Task:</strong> {task_name}</li>
        <li><strong>Updated Fields:</strong> {updated_fields}</li>
        <li><strong>Updated By:</strong> {updated_by_name}</li>
        <li><strong>Company:</strong> {company_name}</li>
        </ul>
        <p>Please review the updated task details.</p>
        <p>Best regards,<br>The {company_name} Team</p>
        </body>
        </html>
        """

        title = f"Task Updated: {task_name}"
        message = f"Task '{task_name}' was updated by {updated_by_name}. Updated: {updated_fields}"

        # Create in-app notification
        try:
            create_notification_records(
                user_id=UUID(recipient_user_id),
                company_id=UUID(company_id),
                notification_type=NOTIFICATION_TYPE_TASK_UPDATED,
                title=title,
                message=message,
                related_record_id=UUID(task_id),
                related_table=RELATED_TABLE_TASKS,
                data={
                    "task_name": task_name,
                    "updated_by_name": updated_by_name,
                    "updated_fields": updated_fields,
                },
                create_email=False,
                create_in_app=True,
            )
        except Exception as e:
            print(f"[CELERY TASK WARNING] Failed to create in-app notification: {str(e)}")

        # Send email
        subject = title
        email_result = send_email_smtp(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=html_content,
        )

        if email_result:
            print(f"[CELERY TASK] ✅ EMAIL SENT: {recipient_email}")
            try:
                create_notification_records(
                    user_id=UUID(recipient_user_id),
                    company_id=UUID(company_id),
                    notification_type=NOTIFICATION_TYPE_TASK_UPDATED,
                    title=title,
                    message=message,
                    related_record_id=UUID(task_id),
                    related_table=RELATED_TABLE_TASKS,
                    data={
                        "task_name": task_name,
                        "updated_by_name": updated_by_name,
                        "updated_fields": updated_fields,
                    },
                    create_email=True,
                    create_in_app=False,
                )
            except Exception as e:
                print(f"[CELERY TASK WARNING] Failed to create email notification record: {str(e)}")
        else:
            print(f"[CELERY TASK] ❌ EMAIL FAILED: {recipient_email}")

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_task_updated_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_task_status_changed_notification")
def send_task_status_changed_notification(
    recipient_email: str,
    recipient_name: str,
    recipient_user_id: str,
    task_id: str,
    task_name: str,
    old_status: str,
    new_status: str,
    changed_by_name: str,
    company_id: str,
    company_name: str,
):
    """Send notification when task status changes."""
    try:
        print(f"[CELERY TASK] ===== send_task_status_changed_notification STARTED =====")
        print(f"[CELERY TASK] Recipient Email: {recipient_email}")
        print(f"[CELERY TASK] Task ID: {task_id}")
        print(f"[CELERY TASK] Status: {old_status} → {new_status}")

        # Customize message based on status
        status_emoji = {
            "TODO": "📋",
            "IN_PROGRESS": "🚀",
            "HALT": "⏸️",
            "REVIEW": "👀",
            "DONE": "✅",
            "CANCELLED": "❌"
        }

        emoji = status_emoji.get(new_status, "📋")

        html_content = f"""
        <html>
        <body>
        <h2>{emoji} Task Status Changed</h2>
        <p>Hello {recipient_name},</p>
        <p>The status of a task has been updated:</p>
        <ul>
        <li><strong>Task:</strong> {task_name}</li>
        <li><strong>Status Change:</strong> {old_status} → {new_status}</li>
        <li><strong>Changed By:</strong> {changed_by_name}</li>
        <li><strong>Company:</strong> {company_name}</li>
        </ul>
        <p>Please review the task and take appropriate action if needed.</p>
        <p>Best regards,<br>The {company_name} Team</p>
        </body>
        </html>
        """

        title = f"Task Status Changed: {task_name}"
        message = f"Task '{task_name}' status changed from {old_status} to {new_status} by {changed_by_name}."

        # Create in-app notification
        try:
            create_notification_records(
                user_id=UUID(recipient_user_id),
                company_id=UUID(company_id),
                notification_type=NOTIFICATION_TYPE_TASK_STATUS_CHANGE,
                title=title,
                message=message,
                related_record_id=UUID(task_id),
                related_table=RELATED_TABLE_TASKS,
                data={
                    "task_name": task_name,
                    "old_status": old_status,
                    "new_status": new_status,
                    "changed_by_name": changed_by_name,
                },
                create_email=False,
                create_in_app=True,
            )
        except Exception as e:
            print(f"[CELERY TASK WARNING] Failed to create in-app notification: {str(e)}")

        # Send email
        subject = title
        email_result = send_email_smtp(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=html_content,
        )

        if email_result:
            print(f"[CELERY TASK] ✅ EMAIL SENT: {recipient_email}")
            try:
                create_notification_records(
                    user_id=UUID(recipient_user_id),
                    company_id=UUID(company_id),
                    notification_type=NOTIFICATION_TYPE_TASK_STATUS_CHANGE,
                    title=title,
                    message=message,
                    related_record_id=UUID(task_id),
                    related_table=RELATED_TABLE_TASKS,
                    data={
                        "task_name": task_name,
                        "old_status": old_status,
                        "new_status": new_status,
                        "changed_by_name": changed_by_name,
                    },
                    create_email=True,
                    create_in_app=False,
                )
            except Exception as e:
                print(f"[CELERY TASK WARNING] Failed to create email notification record: {str(e)}")
        else:
            print(f"[CELERY TASK] ❌ EMAIL FAILED: {recipient_email}")

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_task_status_changed_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_task_assigned_notification")
def send_task_assigned_notification(
    recipient_email: str,
    recipient_name: str,
    recipient_user_id: str,
    task_id: str,
    task_name: str,
    task_description: str,
    permission: str,
    assigned_by_name: str,
    project_name: str,
    company_id: str,
    company_name: str,
):
    """Send notification when user is assigned to a task."""
    try:
        print(f"[CELERY TASK] ===== send_task_assigned_notification STARTED =====")
        print(f"[CELERY TASK] Recipient Email: {recipient_email}")
        print(f"[CELERY TASK] Task ID: {task_id}")
        print(f"[CELERY TASK] Permission: {permission}")

        html_content = f"""
        <html>
        <body>
        <h2>📋 You've Been Assigned to a Task</h2>
        <p>Hello {recipient_name},</p>
        <p>You have been assigned to a task:</p>
        <ul>
        <li><strong>Task:</strong> {task_name}</li>
        <li><strong>Description:</strong> {task_description or 'No description provided'}</li>
        <li><strong>Permission:</strong> {permission}</li>
        <li><strong>Assigned By:</strong> {assigned_by_name}</li>
        <li><strong>Project:</strong> {project_name or 'No project linked'}</li>
        <li><strong>Company:</strong> {company_name}</li>
        </ul>
        <p>Please review the task details and start working on it.</p>
        <p>Best regards,<br>The {company_name} Team</p>
        </body>
        </html>
        """

        title = f"Task Assigned: {task_name}"
        message = f"You have been assigned to task '{task_name}' with {permission} permission by {assigned_by_name}."

        # Create in-app notification
        try:
            create_notification_records(
                user_id=UUID(recipient_user_id),
                company_id=UUID(company_id),
                notification_type=NOTIFICATION_TYPE_TASK_ASSIGNMENT,
                title=title,
                message=message,
                related_record_id=UUID(task_id),
                related_table=RELATED_TABLE_TASKS,
                data={
                    "task_name": task_name,
                    "permission": permission,
                    "assigned_by_name": assigned_by_name,
                    "project_name": project_name,
                },
                create_email=False,
                create_in_app=True,
            )
        except Exception as e:
            print(f"[CELERY TASK WARNING] Failed to create in-app notification: {str(e)}")

        # Send email
        subject = title
        email_result = send_email_smtp(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=html_content,
        )

        if email_result:
            print(f"[CELERY TASK] ✅ EMAIL SENT: {recipient_email}")
            try:
                create_notification_records(
                    user_id=UUID(recipient_user_id),
                    company_id=UUID(company_id),
                    notification_type=NOTIFICATION_TYPE_TASK_ASSIGNMENT,
                    title=title,
                    message=message,
                    related_record_id=UUID(task_id),
                    related_table=RELATED_TABLE_TASKS,
                    data={
                        "task_name": task_name,
                        "permission": permission,
                        "assigned_by_name": assigned_by_name,
                        "project_name": project_name,
                    },
                    create_email=True,
                    create_in_app=False,
                )
            except Exception as e:
                print(f"[CELERY TASK WARNING] Failed to create email notification record: {str(e)}")
        else:
            print(f"[CELERY TASK] ❌ EMAIL FAILED: {recipient_email}")

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_task_assigned_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_task_unassigned_notification")
def send_task_unassigned_notification(
    recipient_email: str,
    recipient_name: str,
    recipient_user_id: str,
    task_id: str,
    task_name: str,
    removed_by_name: str,
    company_id: str,
    company_name: str,
):
    """Send notification when user is removed from a task."""
    try:
        print(f"[CELERY TASK] ===== send_task_unassigned_notification STARTED =====")
        print(f"[CELERY TASK] Recipient Email: {recipient_email}")
        print(f"[CELERY TASK] Task ID: {task_id}")

        html_content = f"""
        <html>
        <body>
        <h2>🔔 Task Assignment Removed</h2>
        <p>Hello {recipient_name},</p>
        <p>You have been removed from a task:</p>
        <ul>
        <li><strong>Task:</strong> {task_name}</li>
        <li><strong>Removed By:</strong> {removed_by_name}</li>
        <li><strong>Company:</strong> {company_name}</li>
        </ul>
        <p>You no longer have access to this task.</p>
        <p>Best regards,<br>The {company_name} Team</p>
        </body>
        </html>
        """

        title = f"Task Unassigned: {task_name}"
        message = f"You have been removed from task '{task_name}' by {removed_by_name}."

        # Create in-app notification
        try:
            create_notification_records(
                user_id=UUID(recipient_user_id),
                company_id=UUID(company_id),
                notification_type=NOTIFICATION_TYPE_TASK_UNASSIGNMENT,
                title=title,
                message=message,
                related_record_id=UUID(task_id),
                related_table=RELATED_TABLE_TASKS,
                data={
                    "task_name": task_name,
                    "removed_by_name": removed_by_name,
                },
                create_email=False,
                create_in_app=True,
            )
        except Exception as e:
            print(f"[CELERY TASK WARNING] Failed to create in-app notification: {str(e)}")

        # Send email
        subject = title
        email_result = send_email_smtp(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=html_content,
        )

        if email_result:
            print(f"[CELERY TASK] ✅ EMAIL SENT: {recipient_email}")
            try:
                create_notification_records(
                    user_id=UUID(recipient_user_id),
                    company_id=UUID(company_id),
                    notification_type=NOTIFICATION_TYPE_TASK_UNASSIGNMENT,
                    title=title,
                    message=message,
                    related_record_id=UUID(task_id),
                    related_table=RELATED_TABLE_TASKS,
                    data={
                        "task_name": task_name,
                        "removed_by_name": removed_by_name,
                    },
                    create_email=True,
                    create_in_app=False,
                )
            except Exception as e:
                print(f"[CELERY TASK WARNING] Failed to create email notification record: {str(e)}")
        else:
            print(f"[CELERY TASK] ❌ EMAIL FAILED: {recipient_email}")

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_task_unassigned_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_task_permission_changed_notification")
def send_task_permission_changed_notification(
    recipient_email: str,
    recipient_name: str,
    recipient_user_id: str,
    task_id: str,
    task_name: str,
    old_permission: str,
    new_permission: str,
    changed_by_name: str,
    company_id: str,
    company_name: str,
):
    """Send notification when task permission is changed."""
    try:
        print(f"[CELERY TASK] ===== send_task_permission_changed_notification STARTED =====")
        print(f"[CELERY TASK] Recipient Email: {recipient_email}")
        print(f"[CELERY TASK] Task ID: {task_id}")
        print(f"[CELERY TASK] Permission: {old_permission} → {new_permission}")

        html_content = f"""
        <html>
        <body>
        <h2>🔐 Task Permission Updated</h2>
        <p>Hello {recipient_name},</p>
        <p>Your permission for a task has been updated:</p>
        <ul>
        <li><strong>Task:</strong> {task_name}</li>
        <li><strong>Permission Change:</strong> {old_permission} → {new_permission}</li>
        <li><strong>Changed By:</strong> {changed_by_name}</li>
        <li><strong>Company:</strong> {company_name}</li>
        </ul>
        <p>Please review the task with your updated permissions.</p>
        <p>Best regards,<br>The {company_name} Team</p>
        </body>
        </html>
        """

        title = f"Task Permission Updated: {task_name}"
        message = f"Your permission for task '{task_name}' changed from {old_permission} to {new_permission} by {changed_by_name}."

        # Create in-app notification
        try:
            create_notification_records(
                user_id=UUID(recipient_user_id),
                company_id=UUID(company_id),
                notification_type=NOTIFICATION_TYPE_TASK_PERMISSION_CHANGE,
                title=title,
                message=message,
                related_record_id=UUID(task_id),
                related_table=RELATED_TABLE_TASKS,
                data={
                    "task_name": task_name,
                    "old_permission": old_permission,
                    "new_permission": new_permission,
                    "changed_by_name": changed_by_name,
                },
                create_email=False,
                create_in_app=True,
            )
        except Exception as e:
            print(f"[CELERY TASK WARNING] Failed to create in-app notification: {str(e)}")

        # Send email
        subject = title
        email_result = send_email_smtp(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=html_content,
        )

        if email_result:
            print(f"[CELERY TASK] ✅ EMAIL SENT: {recipient_email}")
            try:
                create_notification_records(
                    user_id=UUID(recipient_user_id),
                    company_id=UUID(company_id),
                    notification_type=NOTIFICATION_TYPE_TASK_PERMISSION_CHANGE,
                    title=title,
                    message=message,
                    related_record_id=UUID(task_id),
                    related_table=RELATED_TABLE_TASKS,
                    data={
                        "task_name": task_name,
                        "old_permission": old_permission,
                        "new_permission": new_permission,
                        "changed_by_name": changed_by_name,
                    },
                    create_email=True,
                    create_in_app=False,
                )
            except Exception as e:
                print(f"[CELERY TASK WARNING] Failed to create email notification record: {str(e)}")
        else:
            print(f"[CELERY TASK] ❌ EMAIL FAILED: {recipient_email}")

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_task_permission_changed_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@celery_app.task(name="send_task_deleted_notification")
def send_task_deleted_notification(
    recipient_email: str,
    recipient_name: str,
    recipient_user_id: str,
    task_id: str,
    task_name: str,
    deleted_by_name: str,
    company_id: str,
    company_name: str,
):
    """Send notification when task is deleted."""
    try:
        print(f"[CELERY TASK] ===== send_task_deleted_notification STARTED =====")
        print(f"[CELERY TASK] Recipient Email: {recipient_email}")
        print(f"[CELERY TASK] Task ID: {task_id}")

        html_content = f"""
        <html>
        <body>
        <h2>🗑️ Task Deleted</h2>
        <p>Hello {recipient_name},</p>
        <p>A task you were involved with has been deleted:</p>
        <ul>
        <li><strong>Task:</strong> {task_name}</li>
        <li><strong>Deleted By:</strong> {deleted_by_name}</li>
        <li><strong>Company:</strong> {company_name}</li>
        </ul>
        <p>This task is no longer available.</p>
        <p>Best regards,<br>The {company_name} Team</p>
        </body>
        </html>
        """

        title = f"Task Deleted: {task_name}"
        message = f"Task '{task_name}' was deleted by {deleted_by_name}."

        # Create in-app notification
        try:
            create_notification_records(
                user_id=UUID(recipient_user_id),
                company_id=UUID(company_id),
                notification_type=NOTIFICATION_TYPE_TASK_DELETED,
                title=title,
                message=message,
                related_record_id=UUID(task_id),
                related_table=RELATED_TABLE_TASKS,
                data={
                    "task_name": task_name,
                    "deleted_by_name": deleted_by_name,
                },
                create_email=False,
                create_in_app=True,
            )
        except Exception as e:
            print(f"[CELERY TASK WARNING] Failed to create in-app notification: {str(e)}")

        # Send email
        subject = title
        email_result = send_email_smtp(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=html_content,
        )

        if email_result:
            print(f"[CELERY TASK] ✅ EMAIL SENT: {recipient_email}")
            try:
                create_notification_records(
                    user_id=UUID(recipient_user_id),
                    company_id=UUID(company_id),
                    notification_type=NOTIFICATION_TYPE_TASK_DELETED,
                    title=title,
                    message=message,
                    related_record_id=UUID(task_id),
                    related_table=RELATED_TABLE_TASKS,
                    data={
                        "task_name": task_name,
                        "deleted_by_name": deleted_by_name,
                    },
                    create_email=True,
                    create_in_app=False,
                )
            except Exception as e:
                print(f"[CELERY TASK WARNING] Failed to create email notification record: {str(e)}")
        else:
            print(f"[CELERY TASK] ❌ EMAIL FAILED: {recipient_email}")

        return email_result
    except Exception as e:
        print(f"[CELERY TASK ERROR] Error in send_task_deleted_notification: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
