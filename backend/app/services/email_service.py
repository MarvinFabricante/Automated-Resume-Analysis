import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    @staticmethod
    async def send_reset_password_email(email: str, token: str):
        # In a real production app, you'd use a real SMTP server.
        # For now, we'll simulate the email sending by printing to console
        # and providing the reset link.
        
        base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:5173").rstrip("/")
        reset_link = f"{base_url}/reset-password?token={token}"
        
        subject = "Password Reset Request - Mariwasa Portal"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; rounded: 10px;">
                    <h2 style="color: #D60041;">Mariwasa Portal</h2>
                    <p>Hello,</p>
                    <p>We received a request to reset your password. Click the button below to choose a new one:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" style="background-color: #D60041; color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; font-weight: bold;">Reset Password</a>
                    </div>
                    <p>If you didn't request this, you can safely ignore this email.</p>
                    <p>This link will expire in 1 hour.</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #999;">Mariwasa Siam Ceramics Inc. - Resume Analysis System</p>
                </div>
            </body>
        </html>
        """
        
        print(f"\n--- ATTEMPTING TO SEND EMAIL TO {email} ---")
        print(f"Subject: {subject}")
        print(f"Reset Link: {reset_link}")
        
        try:
            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", 587))
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")

            if not smtp_user or not smtp_password or "your-email" in smtp_user:
                print("WARNING: SMTP credentials not fully configured in .env. Falling back to console log only.")
                return True

            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))

            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            print("EMAIL SENT SUCCESSFULLY VIA SMTP")
        except Exception as e:
            print(f"Error sending email via SMTP: {e}")
            print("Note: If using Gmail, make sure to use an 'App Password'.")
        
        print("------------------------------\n")
        return True
