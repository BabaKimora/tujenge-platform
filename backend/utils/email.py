"""
Email Service for Tujenge Platform
Handles email sending for authentication and notifications
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import logging
try:
    from jinja2 import Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("⚠️ jinja2 not available - email templates will use basic formatting")
import os
from backend.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for sending transactional emails"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_tls = settings.SMTP_TLS
        self.smtp_ssl = settings.SMTP_SSL
        
        # Setup Jinja2 for email templates
        if JINJA2_AVAILABLE:
            template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'email')
            os.makedirs(template_dir, exist_ok=True)
            self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        else:
            self.jinja_env = None
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> bool:
        """Send an email"""
        try:
            if not self.smtp_host or not self.smtp_username:
                logger.warning("Email service not configured, skipping email send")
                return False
            
            from_email = from_email or self.smtp_username
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = from_email
            message["To"] = to_email
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            context = ssl.create_default_context()
            
            if self.smtp_ssl:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.sendmail(from_email, to_email, message.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.smtp_tls:
                        server.starttls(context=context)
                    server.login(self.smtp_username, self.smtp_password)
                    server.sendmail(from_email, to_email, message.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def send_password_reset_email(
        self,
        email: str,
        first_name: str,
        reset_token: str
    ) -> bool:
        """Send password reset email"""
        try:
            # Create reset URL (you'll need to configure your frontend URL)
            reset_url = f"https://your-frontend-domain.com/reset-password?token={reset_token}"
            
            subject = "Tujenge Platform - Password Reset Request"
            
            # HTML content
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #2563eb; color: white; padding: 20px; text-align: center;">
                    <h1>Tujenge Platform</h1>
                    <p>Tanzania Fintech Solution</p>
                </div>
                
                <div style="padding: 30px;">
                    <h2>Password Reset Request</h2>
                    <p>Hujambo {first_name},</p>
                    
                    <p>We received a request to reset your password for your Tujenge Platform account.</p>
                    
                    <p>Click the button below to reset your password:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" 
                           style="background-color: #2563eb; color: white; padding: 12px 24px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #666;">{reset_url}</p>
                    
                    <p><strong>Important:</strong> This link will expire in 1 hour for security reasons.</p>
                    
                    <p>If you didn't request this password reset, please ignore this email or contact our support team.</p>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                    
                    <p style="color: #666; font-size: 14px;">
                        Tujenge Platform - Tanzania Enterprise Fintech Solution<br>
                        Email: support@tujengeplatform.co.tz<br>
                        This is an automated message, please do not reply directly to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Text content
            text_content = f"""
            Tujenge Platform - Password Reset Request
            
            Hujambo {first_name},
            
            We received a request to reset your password for your Tujenge Platform account.
            
            Please visit the following link to reset your password:
            {reset_url}
            
            Important: This link will expire in 1 hour for security reasons.
            
            If you didn't request this password reset, please ignore this email or contact our support team.
            
            ---
            Tujenge Platform - Tanzania Enterprise Fintech Solution
            Email: support@tujengeplatform.co.tz
            """
            
            return await self.send_email(email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False
    
    async def send_welcome_email(
        self,
        email: str,
        first_name: str,
        tenant_name: str
    ) -> bool:
        """Send welcome email to new user"""
        try:
            subject = f"Welcome to Tujenge Platform - {tenant_name}"
            
            # HTML content
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #2563eb; color: white; padding: 20px; text-align: center;">
                    <h1>🏦 Tujenge Platform</h1>
                    <p>Tanzania Enterprise Fintech Solution</p>
                </div>
                
                <div style="padding: 30px;">
                    <h2>Welcome to {tenant_name}!</h2>
                    <p>Karibu {first_name},</p>
                    
                    <p>Your account has been successfully created on the Tujenge Platform. 
                       You now have access to our comprehensive fintech solution designed 
                       specifically for Tanzania's financial services sector.</p>
                    
                    <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3>🎯 What you can do with Tujenge Platform:</h3>
                        <ul style="margin: 0; padding-left: 20px;">
                            <li>💰 Manage loans and applications</li>
                            <li>👥 Handle customer relationships</li>
                            <li>📱 Process mobile money transactions (M-Pesa, Airtel)</li>
                            <li>🏛️ Integrate with government APIs (NIDA, TIN)</li>
                            <li>📊 Generate analytics and reports</li>
                            <li>📄 Manage documents and compliance</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="https://your-frontend-domain.com/login" 
                           style="background-color: #2563eb; color: white; padding: 12px 24px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Get Started
                        </a>
                    </div>
                    
                    <p>If you have any questions or need assistance, our support team is here to help:</p>
                    <p>📧 Email: support@tujengeplatform.co.tz<br>
                       📞 Phone: +255 XXX XXX XXX</p>
                    
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                    
                    <p style="color: #666; font-size: 14px;">
                        Asante for choosing Tujenge Platform!<br>
                        This is an automated message, please do not reply directly to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Text content
            text_content = f"""
            Welcome to Tujenge Platform - {tenant_name}!
            
            Karibu {first_name},
            
            Your account has been successfully created on the Tujenge Platform.
            
            What you can do:
            - Manage loans and applications
            - Handle customer relationships
            - Process mobile money transactions (M-Pesa, Airtel)
            - Integrate with government APIs (NIDA, TIN)
            - Generate analytics and reports
            - Manage documents and compliance
            
            Get started: https://your-frontend-domain.com/login
            
            Support: support@tujengeplatform.co.tz
            
            Asante for choosing Tujenge Platform!
            """
            
            return await self.send_email(email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
            return False

# Initialize email service
email_service = EmailService()

# Function aliases for compatibility with auth router
async def send_password_reset_email(email: str, first_name: str, reset_token: str) -> bool:
    """Send password reset email - function alias"""
    return await email_service.send_password_reset_email(email, first_name, reset_token)

async def send_welcome_email(email: str, first_name: str, tenant_name: str) -> bool:
    """Send welcome email - function alias"""
    return await email_service.send_welcome_email(email, first_name, tenant_name) 