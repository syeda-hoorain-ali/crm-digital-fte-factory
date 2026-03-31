"""Email notification service for customer communications."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending email notifications to customers."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
        use_tls: bool = True
    ):
        """Initialize notification service.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_username: SMTP authentication username
            smtp_password: SMTP authentication password
            from_email: Sender email address
            use_tls: Whether to use TLS encryption
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.use_tls = use_tls

    async def send_support_confirmation(
        self,
        to_email: str,
        customer_name: str,
        ticket_id: str,
        subject: str,
        estimated_response_time: str = "within 5 minutes"
    ) -> bool:
        """Send support request confirmation email.

        Args:
            to_email: Customer email address
            customer_name: Customer name
            ticket_id: Support ticket ID
            subject: Original support request subject
            estimated_response_time: Estimated response time

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = f"Support Request Received - Ticket #{ticket_id}"
            message["From"] = self.from_email
            message["To"] = to_email

            # Create email body
            text_body = self._create_text_body(
                customer_name, ticket_id, subject, estimated_response_time
            )
            html_body = self._create_html_body(
                customer_name, ticket_id, subject, estimated_response_time
            )

            # Attach both plain text and HTML versions
            text_part = MIMEText(text_body, "plain")
            html_part = MIMEText(html_body, "html")
            message.attach(text_part)
            message.attach(html_part)

            # Send email
            await self._send_email(to_email, message)

            logger.info(
                f"Support confirmation email sent successfully",
                extra={
                    "to_email": to_email,
                    "ticket_id": ticket_id
                }
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to send support confirmation email: {e}",
                extra={
                    "to_email": to_email,
                    "ticket_id": ticket_id
                },
                exc_info=True
            )
            return False

    def _create_text_body(
        self,
        customer_name: str,
        ticket_id: str,
        subject: str,
        estimated_response_time: str
    ) -> str:
        """Create plain text email body.

        Args:
            customer_name: Customer name
            ticket_id: Support ticket ID
            subject: Original support request subject
            estimated_response_time: Estimated response time

        Returns:
            Plain text email body
        """
        return f"""Hello {customer_name},

Thank you for contacting our support team. We have received your request and created a support ticket for you.

Ticket Details:
- Ticket ID: {ticket_id}
- Subject: {subject}
- Estimated Response Time: {estimated_response_time}

Our team will review your request and respond as soon as possible. You can check the status of your ticket at any time using your ticket ID.

If you have any urgent concerns, please don't hesitate to reach out to us directly.

Best regards,
CloudStream Support Team
"""

    def _create_html_body(
        self,
        customer_name: str,
        ticket_id: str,
        subject: str,
        estimated_response_time: str
    ) -> str:
        """Create HTML email body.

        Args:
            customer_name: Customer name
            ticket_id: Support ticket ID
            subject: Original support request subject
            estimated_response_time: Estimated response time

        Returns:
            HTML email body
        """
        return f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
        .ticket-info {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #4CAF50; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Support Request Received</h1>
        </div>
        <div class="content">
            <p>Hello {customer_name},</p>
            <p>Thank you for contacting our support team. We have received your request and created a support ticket for you.</p>

            <div class="ticket-info">
                <h3>Ticket Details</h3>
                <p><strong>Ticket ID:</strong> {ticket_id}</p>
                <p><strong>Subject:</strong> {subject}</p>
                <p><strong>Estimated Response Time:</strong> {estimated_response_time}</p>
            </div>

            <p>Our team will review your request and respond as soon as possible. You can check the status of your ticket at any time using your ticket ID.</p>
            <p>If you have any urgent concerns, please don't hesitate to reach out to us directly.</p>

            <p>Best regards,<br>CloudStream Support Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
"""

    async def _send_email(self, to_email: str, message: MIMEMultipart) -> None:
        """Send email via SMTP.

        Args:
            to_email: Recipient email address
            message: Email message to send

        Raises:
            Exception: If email sending fails
        """
        try:
            # Create SMTP connection
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)

            # Login and send
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(message)
            server.quit()

        except Exception as e:
            logger.error(f"SMTP error: {e}", exc_info=True)
            raise
