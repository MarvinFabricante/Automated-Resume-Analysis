import os
import smtplib
import asyncio
from datetime import datetime
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()


def _send_smtp_sync(to_email: str, subject: str, html_body: str) -> bool:
    """Synchronously send an email using SMTP credentials from environment variables."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    print(f"\n--- ATTEMPTING TO SEND EMAIL TO {to_email} ---")
    print(f"Subject: {subject}")

    if not smtp_user or not smtp_password or "your-email" in smtp_user:
        print("WARNING: SMTP credentials not fully configured in .env. Falling back to console log only.")
        print(f"Body Preview:\n{html_body[:300]}...")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = f"Mariwasa HR Team <{smtp_user}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"EMAIL SENT SUCCESSFULLY VIA SMTP to {to_email}")
        print("------------------------------\n")
        return True
    except Exception as e:
        print(f"Error sending email via SMTP to {to_email}: {e}")
        print("------------------------------\n")
        return False


class EmailService:
    @staticmethod
    async def send_reset_password_email(email: str, token: str):
        reset_link = f"http://localhost:5173/reset-password?token={token}"
        subject = "Password Reset Request - Mariwasa Portal"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f8fafc;">
                <div style="max-width: 600px; margin: 0 auto; padding: 30px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                    <h2 style="color: #D60041; margin-top: 0;">Mariwasa Portal</h2>
                    <p>Hello,</p>
                    <p>We received a request to reset your password. Click the button below to choose a new one:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" style="background-color: #D60041; color: white; padding: 12px 28px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block;">Reset Password</a>
                    </div>
                    <p>If you didn't request this, you can safely ignore this email.</p>
                    <p>This link will expire in 1 hour.</p>
                    <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 25px 0;">
                    <p style="font-size: 12px; color: #94a3b8; margin-bottom: 0;">Mariwasa Siam Ceramics Inc. - Resume Analysis & Scheduling System</p>
                </div>
            </body>
        </html>
        """
        return await asyncio.to_thread(_send_smtp_sync, email, subject, body)

    @staticmethod
    async def send_interview_invitation_email(
        to_email: str,
        candidate_name: str,
        job_title: str,
        interview_title: str,
        start_time: datetime,
        end_time: datetime,
        interviewer_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Send a detailed interview invitation email to the candidate's Gmail account."""
        formatted_date = start_time.strftime("%A, %B %d, %Y")
        start_str = start_time.strftime("%I:%M %p")
        end_str = end_time.strftime("%I:%M %p")
        interviewer_display = interviewer_name if interviewer_name else "Mariwasa HR Panel"

        subject = f"Interview Scheduled: {interview_title} - {job_title} | Mariwasa Siam Ceramics"

        notes_section = ""
        if notes and notes.strip():
            notes_section = f"""
            <div style="margin-top: 20px; padding: 16px; background-color: #f8fafc; border-left: 4px solid #D60041; border-radius: 4px;">
                <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: bold; text-transform: uppercase; color: #475569; letter-spacing: 0.05em;">Interview Agenda / Notes</p>
                <p style="margin: 0; font-size: 14px; color: #1e293b; white-space: pre-wrap;">{notes}</p>
            </div>
            """

        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; margin: 0; padding: 24px; background-color: #f1f5f9;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);">
                <!-- Header Banner -->
                <div style="background: linear-gradient(135deg, #D60041 0%, #900029 100%); padding: 32px 32px 28px 32px; color: #ffffff; text-align: left;">
                    <span style="display: inline-block; padding: 4px 12px; background-color: rgba(255, 255, 255, 0.2); border-radius: 12px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px;">
                        Interview Invitation
                    </span>
                    <h1 style="margin: 0; font-size: 24px; font-weight: 800; color: #ffffff; line-height: 1.2;">
                        Mariwasa Siam Ceramics, Inc.
                    </h1>
                    <p style="margin: 6px 0 0 0; font-size: 14px; color: #fecdd3; font-weight: 500;">
                        Human Resources & Talent Acquisition
                    </p>
                </div>

                <!-- Main Content -->
                <div style="padding: 32px;">
                    <p style="font-size: 16px; margin: 0 0 16px 0;">Dear <strong>{candidate_name}</strong>,</p>
                    
                    <p style="font-size: 15px; color: #334155; margin: 0 0 24px 0; line-height: 1.6;">
                        We are pleased to inform you that an interview has been scheduled for your application for the position of <strong>{job_title}</strong> at Mariwasa Siam Ceramics, Inc.
                    </p>

                    <!-- Interview Details Card -->
                    <div style="background-color: #fff1f2; border: 1px solid #ffe4e6; border-radius: 16px; padding: 24px; margin-bottom: 24px;">
                        <h3 style="margin: 0 0 18px 0; font-size: 16px; font-weight: 700; color: #9f1239; border-bottom: 1px solid #fecdd3; padding-bottom: 10px;">
                            Schedule Information
                        </h3>
                        
                        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; font-weight: 600; width: 140px;">Stage / Round:</td>
                                <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{interview_title}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Position:</td>
                                <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{job_title}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Date:</td>
                                <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{formatted_date}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Time:</td>
                                <td style="padding: 6px 0; color: #D60041; font-weight: 800;">{start_str} – {end_str}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Assigned Panelist:</td>
                                <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{interviewer_display}</td>
                            </tr>
                        </table>

                        {notes_section}
                    </div>

                    <!-- Preparation and Instructions -->
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; margin-bottom: 24px;">
                        <h4 style="margin: 0 0 8px 0; font-size: 13px; font-weight: 700; color: #1e293b; text-transform: uppercase; letter-spacing: 0.05em;">
                            Important Reminder
                        </h4>
                        <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #475569; line-height: 1.6;">
                            <li>Please confirm your availability and make sure you are ready 10 minutes prior to the scheduled start time.</li>
                            <li>Have an updated copy of your resume and any relevant portfolio or project work on hand.</li>
                            <li>If you need to reschedule due to unforeseen circumstances, please contact our HR team in advance.</li>
                        </ul>
                    </div>

                    <p style="font-size: 14px; color: #475569; margin: 0 0 4px 0;">
                        We look forward to meeting you and discussing your candidacy.
                    </p>
                    <p style="font-size: 14px; color: #0f172a; font-weight: 700; margin: 0;">
                        Best regards,<br>
                        Mariwasa Siam Ceramics Human Resources Team
                    </p>
                </div>

                <!-- Footer -->
                <div style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px 32px; text-align: center; font-size: 11px; color: #94a3b8;">
                    <p style="margin: 0 0 4px 0; font-weight: 600;">Mariwasa Siam Ceramics, Inc.</p>
                    <p style="margin: 0;">Automated Resume Analysis & Recruitment Portal • This is an automated notification.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return await asyncio.to_thread(_send_smtp_sync, to_email, subject, body)

    @staticmethod
    async def send_interview_rescheduled_email(
        to_email: str,
        candidate_name: str,
        job_title: str,
        interview_title: str,
        start_time: datetime,
        end_time: datetime,
        interviewer_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Send an interview rescheduled email to the candidate's Gmail account."""
        formatted_date = start_time.strftime("%A, %B %d, %Y")
        start_str = start_time.strftime("%I:%M %p")
        end_str = end_time.strftime("%I:%M %p")
        interviewer_display = interviewer_name if interviewer_name else "Mariwasa HR Panel"

        subject = f"Rescheduled: {interview_title} - {job_title} | Mariwasa Siam Ceramics"

        notes_section = ""
        if notes and notes.strip():
            notes_section = f"""
            <div style="margin-top: 20px; padding: 16px; background-color: #f8fafc; border-left: 4px solid #f59e0b; border-radius: 4px;">
                <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: bold; text-transform: uppercase; color: #475569; letter-spacing: 0.05em;">Updated Notes / Agenda</p>
                <p style="margin: 0; font-size: 14px; color: #1e293b; white-space: pre-wrap;">{notes}</p>
            </div>
            """

        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; margin: 0; padding: 24px; background-color: #f1f5f9;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);">
                <!-- Header Banner -->
                <div style="background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%); padding: 32px 32px 28px 32px; color: #ffffff; text-align: left;">
                    <span style="display: inline-block; padding: 4px 12px; background-color: rgba(255, 255, 255, 0.2); border-radius: 12px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px;">
                        Schedule Update
                    </span>
                    <h1 style="margin: 0; font-size: 24px; font-weight: 800; color: #ffffff; line-height: 1.2;">
                        Interview Rescheduled
                    </h1>
                    <p style="margin: 6px 0 0 0; font-size: 14px; color: #fef3c7; font-weight: 500;">
                        Mariwasa Siam Ceramics, Inc.
                    </p>
                </div>

                <!-- Main Content -->
                <div style="padding: 32px;">
                    <p style="font-size: 16px; margin: 0 0 16px 0;">Dear <strong>{candidate_name}</strong>,</p>
                    
                    <p style="font-size: 15px; color: #334155; margin: 0 0 24px 0; line-height: 1.6;">
                        Please be advised that your interview schedule for the position of <strong>{job_title}</strong> has been updated. Below are your new interview details:
                    </p>

                    <!-- Interview Details Card -->
                    <div style="background-color: #fffbeb; border: 1px solid #fef3c7; border-radius: 16px; padding: 24px; margin-bottom: 24px;">
                        <h3 style="margin: 0 0 18px 0; font-size: 16px; font-weight: 700; color: #92400e; border-bottom: 1px solid #fde68a; padding-bottom: 10px;">
                            New Schedule Information
                        </h3>
                        
                        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; font-weight: 600; width: 140px;">Stage / Round:</td>
                                <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{interview_title}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Position:</td>
                                <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{job_title}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; font-weight: 600;">New Date:</td>
                                <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{formatted_date}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; font-weight: 600;">New Time:</td>
                                <td style="padding: 6px 0; color: #b45309; font-weight: 800;">{start_str} – {end_str}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; font-weight: 600;">Assigned Panelist:</td>
                                <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{interviewer_display}</td>
                            </tr>
                        </table>

                        {notes_section}
                    </div>

                    <p style="font-size: 14px; color: #475569; margin: 0 0 4px 0;">
                        If you have any questions or need further clarification, please contact our HR recruitment team.
                    </p>
                    <p style="font-size: 14px; color: #0f172a; font-weight: 700; margin: 0;">
                        Best regards,<br>
                        Mariwasa Siam Ceramics Human Resources Team
                    </p>
                </div>

                <!-- Footer -->
                <div style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px 32px; text-align: center; font-size: 11px; color: #94a3b8;">
                    <p style="margin: 0 0 4px 0; font-weight: 600;">Mariwasa Siam Ceramics, Inc.</p>
                    <p style="margin: 0;">Automated Resume Analysis & Recruitment Portal • This is an automated notification.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return await asyncio.to_thread(_send_smtp_sync, to_email, subject, body)
