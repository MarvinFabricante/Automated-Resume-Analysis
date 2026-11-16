import os
import sys
import base64
import subprocess
import fitz

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.manual_builder.styles import get_css

def load_b64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

logo_b64 = load_b64("frontend/public/assets/logo.png")
logo_img = f'<img src="data:image/png;base64,{logo_b64}" alt="Mariwasa Logo" style="height: 48px; object-fit: contain;">' if logo_b64 else '<span style="font-size: 20pt; font-weight: 900; color: #1e40af;">MARIWASA</span>'

short_manual_css = get_css() + """
/* Additional styles for Short User Manual */
.manual-header {
    border-bottom: 2.5px solid #1e40af;
    padding-bottom: 4mm;
    margin-bottom: 5mm;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.manual-title-block h1 {
    margin: 0;
    padding: 0;
    border: none;
    font-size: 17pt;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.2;
}
.manual-title-block .subtitle {
    font-size: 9pt;
    color: #475569;
    font-weight: 500;
    margin-top: 1mm;
}
.portal-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 3.5mm 4mm;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.portal-card.admin { border-top: 4px solid #7c3aed; }
.portal-card.hr { border-top: 4px solid #2563eb; }
.portal-card.candidate { border-top: 4px solid #059669; }

.cred-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 2mm 2.5mm;
    margin: 1.5mm 0;
    font-size: 8pt;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.step-number {
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #1e40af;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 8.5pt;
}
.workflow-box {
    display: flex;
    gap: 3mm;
    margin-bottom: 2.5mm;
    align-items: flex-start;
}
.workflow-content {
    flex: 1;
}
.workflow-content h4 {
    margin: 0 0 0.8mm 0;
    font-size: 9pt;
    font-weight: 700;
    color: #0f172a;
}
.workflow-content p {
    margin: 0;
    font-size: 8pt;
    color: #334155;
    line-height: 1.45;
}
"""

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Automated Resume Analysis System — Quick Start User Manual</title>
    <style>
        {short_manual_css}
    </style>
</head>
<body>

    <!-- PAGE 1: SYSTEM OVERVIEW & ACCESS DIRECTORY -->
    <div class="manual-header">
        <div class="manual-title-block">
            <div class="chapter-header" style="margin-bottom: 1mm;">Mariwasa Siam Ceramics Inc. &bull; Enterprise User Manual</div>
            <h1>Automated Resume Analysis System</h1>
            <div class="subtitle">Quick Start Reference Guide & System Operations Manual</div>
        </div>
        <div>
            {logo_img}
        </div>
    </div>

    <!-- PRIMARY ACCESS BANNER -->
    <div class="callout callout-info avoid-break" style="margin-top: 0; margin-bottom: 4mm; padding: 3.5mm 4.5mm;">
        <div class="callout-title" style="font-size: 11pt; font-weight: 800; color: #1d4ed8; margin-bottom: 2mm;">
            🌐 Live Cloudflare Tunnel Production Access
        </div>
        <p style="font-size: 9pt; margin-bottom: 1.5mm;">
            The enterprise system is deployed and publicly accessible via secure Cloudflare Tunnel with TLS 1.3 encryption:
        </p>
        <div style="background: #ffffff; border: 1.5px solid #3b82f6; border-radius: 5px; padding: 2.5mm 3.5mm; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 10pt; font-family: monospace; font-weight: 700; color: #1e3a8a;">
                https://explanation-citizens-cooperative-evidence.trycloudflare.com/
            </span>
            <span class="badge badge-green" style="font-size: 8pt; padding: 2px 8px;">LIVE & SECURE</span>
        </div>
    </div>

    <h2>1. Quick Authentication & Role Credentials Directory</h2>
    <p style="font-size: 8.5pt; margin-bottom: 3mm;">
        The system enforces strict Role-Based Access Control (RBAC). Three pre-configured user roles provide dedicated workflows for applicants, recruiters, and administrators. Use the verified credentials below to log into the respective environment:
    </p>

    <!-- 3 COLUMNS OF CREDENTIALS -->
    <div class="grid-3 avoid-break" style="gap: 3mm; margin-bottom: 4mm;">
        <!-- ADMIN -->
        <div class="portal-card admin">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2mm;">
                <span style="font-weight: 800; font-size: 9.5pt; color: #6b21a8;">ADMINISTRATOR</span>
                <span class="badge badge-purple">Full Control</span>
            </div>
            <p style="font-size: 7.8pt; color: #64748b; margin-bottom: 1.5mm;">System governance, AI weights configuration, user account provisioning, and audit trail monitoring.</p>
            <div style="font-size: 7.5pt; font-weight: 600; color: #475569; text-transform: uppercase;">Login Method: Direct Sign-In</div>
            <div class="cred-box">
                <div><strong>Email:</strong> jp@gmail.com</div>
                <div><strong>Password:</strong> password</div>
                <div><strong>Target:</strong> <code>/admin/dashboard</code></div>
            </div>
            <div style="font-size: 7.5pt; color: #6b21a8; font-weight: 600; margin-top: 1mm;">
                &rarr; Navigate to <code>/login</code> and enter credentials directly.
            </div>
        </div>

        <!-- HR -->
        <div class="portal-card hr">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2mm;">
                <span style="font-weight: 800; font-size: 9.5pt; color: #1e40af;">HR OFFICER</span>
                <span class="badge badge-blue">Recruiter</span>
            </div>
            <p style="font-size: 7.8pt; color: #64748b; margin-bottom: 1.5mm;">Job posting, AI resume screening, radar skill gap analysis, interview scheduling & voice screening.</p>
            <div style="font-size: 7.5pt; font-weight: 600; color: #475569; text-transform: uppercase;">Login Method: Google OAuth SSO</div>
            <div class="cred-box">
                <div><strong>Google Email:</strong> hr.mariwasa@gmail.com</div>
                <div><strong>Google Pass:</strong> Password123.</div>
                <div><strong>Target:</strong> <code>/hr/dashboard</code></div>
            </div>
            <div style="font-size: 7.5pt; color: #1e40af; font-weight: 600; margin-top: 1mm;">
                &rarr; At <code>/login</code>, click <strong>"Continue with Google"</strong>.
            </div>
        </div>

        <!-- CANDIDATE -->
        <div class="portal-card candidate">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2mm;">
                <span style="font-weight: 800; font-size: 9.5pt; color: #065f46;">CANDIDATE</span>
                <span class="badge badge-green">Applicant</span>
            </div>
            <p style="font-size: 7.8pt; color: #64748b; margin-bottom: 1.5mm;">Explore careers, upload resume for Smart Match, preview-verify parsed data, track application lifecycle.</p>
            <div style="font-size: 7.5pt; font-weight: 600; color: #475569; text-transform: uppercase;">Registration: Google SSO / Email</div>
            <div class="cred-box">
                <div><strong>Registration:</strong> Google Account (1-Click)</div>
                <div><strong>Alternate:</strong> Sign up via <code>/register</code></div>
                <div><strong>Target:</strong> <code>/candidate/dashboard</code></div>
            </div>
            <div style="font-size: 7.5pt; color: #065f46; font-weight: 600; margin-top: 1mm;">
                &rarr; Click <strong>"Continue with Google"</strong> on <code>/register</code>.
            </div>
        </div>
    </div>

    <h2>2. System Overview & Architecture Highlights</h2>
    <p style="font-size: 8.5pt;">
        The Mariwasa Automated Resume Analysis System integrates state-of-the-art Natural Language Processing (spaCy NLP) and Google Gemini AI to revolutionize talent acquisition. The end-to-end recruitment pipeline automates resume ingestion, semantic entity extraction, scoring against job requirements, interview scheduling with Google Calendar sync, and telephone voice screening.
    </p>

    <table class="data-table avoid-break" style="margin-top: 2mm; margin-bottom: 3mm;">
        <thead>
            <tr>
                <th style="width: 25%;">Core Component</th>
                <th style="width: 35%;">Technology Stack</th>
                <th style="width: 40%;">Key Enterprise Functionality</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Frontend Client</strong></td>
                <td>Next.js 15, React 19, Tailwind CSS, Redux Toolkit</td>
                <td>Responsive portal for Candidates, HR Recruiters, and System Administrators.</td>
            </tr>
            <tr>
                <td><strong>Backend REST API</strong></td>
                <td>FastAPI (Python 3.12), Pydantic v2, JWT Auth</td>
                <td>High-throughput asynchronous API handling auth, parsing, and scoring.</td>
            </tr>
            <tr>
                <td><strong>AI & NLP Engine</strong></td>
                <td>spaCy <code>en_core_web_md</code>, Google Gemini 2.5 Flash</td>
                <td>Extracts technical skills, education, experience; computes radar match score.</td>
            </tr>
            <tr>
                <td><strong>Async Worker & Queue</strong></td>
                <td>Celery 5.4 with Redis In-Memory Broker</td>
                <td>Processes background AI parsing, batch scoring, email dispatches, and voice calls.</td>
            </tr>
            <tr>
                <td><strong>Database Storage</strong></td>
                <td>PostgreSQL 16 & SQLAlchemy 2.0 ORM</td>
                <td>ACID-compliant storage for users, jobs, applications, and security audit logs.</td>
            </tr>
        </tbody>
    </table>

    <!-- PAGE BREAK FOR CHAPTER 3: CANDIDATE GUIDE -->
    <div class="page-break"></div>

    <div class="manual-header">
        <div class="manual-title-block">
            <div class="chapter-header">Candidate User Guide &bull; Chapter 3</div>
            <h1>Candidate Portal & Application Walkthrough</h1>
            <div class="subtitle">Step-by-Step Guide for Job Applicants from Registration to Interview Confirmation</div>
        </div>
        <div>{logo_img}</div>
    </div>

    <div class="callout callout-tip avoid-break" style="margin-bottom: 3.5mm;">
        <div class="callout-title">💡 Pro Tip for Applicants</div>
        Upload your resume in clean <strong>PDF</strong> or <strong>DOCX</strong> format (maximum file size: 10MB). Standard typography and structured headers (Skills, Work Experience, Education) ensure maximum extraction accuracy and optimal AI match scoring.
    </div>

    <div class="step-workflow">
        <div class="workflow-box avoid-break">
            <div class="step-number">1</div>
            <div class="workflow-content">
                <h4>Account Creation & Sign-In (Google Account or Email)</h4>
                <p>
                    Navigate to <code>https://explanation-citizens-cooperative-evidence.trycloudflare.com/register</code>. Click <strong>"Continue with Google"</strong> to register instantly with your verified Google account. Alternatively, fill in your Full Name, Email Address, Phone Number, and Password. If already registered, log in at <code>/login</code>.
                </p>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">2</div>
            <div class="workflow-content">
                <h4>Explore Job Openings & Position Details</h4>
                <p>
                    Browse open requisitions under <strong>Find Jobs</strong> (<code>/candidate/findjobs</code>). Filter by department (Manufacturing, Quality Control, IT, Logistics), job level, and location. Click on any job card to view full specifications, required technical competencies, education thresholds, and core responsibilities.
                </p>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">3</div>
            <div class="workflow-content">
                <h4>Smart Match Resume Upload & Real-Time AI Parsing</h4>
                <p>
                    Click <strong>"Apply Now"</strong> or navigate to <strong>Smart Upload</strong> (<code>/candidate/smart-upload</code>). Drag and drop your resume file. The background AI parser extracts:
                </p>
                <ul style="margin: 1mm 0 1mm 4mm; font-size: 7.8pt;">
                    <li><strong>Contact Details:</strong> Full Name, Email, Phone Number, Residential Location.</li>
                    <li><strong>Skills Inventory:</strong> Technical competencies, certifications, software tools, soft skills.</li>
                    <li><strong>Work Experience:</strong> Job titles, employers, employment duration, quantified achievements.</li>
                    <li><strong>Education:</strong> Highest degree earned, academic institution, major, graduation year.</li>
                </ul>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">4</div>
            <div class="workflow-content">
                <h4>Preview & Verification Screen (Human-in-the-Loop Review)</h4>
                <p>
                    Review the auto-extracted data on the <strong>Preview & Verify</strong> screen (<code>/preview-and-verify</code>). You have full control to edit, correct typos, add missing skills, or update dates before finalizing your submission. This guarantees data precision before AI scoring.
                </p>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">5</div>
            <div class="workflow-content">
                <h4>Application Submission & AI Match Score Feedback</h4>
                <p>
                    Click <strong>"Submit Application"</strong>. The AI engine instantly calculates your overall match score against the job description based on Skills (40%), Experience (30%), Education (20%), and Semantic Alignment (10%). You receive immediate confirmation and a reference tracking code.
                </p>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">6</div>
            <div class="workflow-content">
                <h4>Application Stage Tracking & Live HR Messaging</h4>
                <p>
                    Monitor your application live under <strong>Application Tracking</strong> (<code>/candidate/applicationtracking</code>). The status updates transparently through five stages:
                </p>
                <div style="display: flex; gap: 2mm; margin: 2mm 0; flex-wrap: wrap;">
                    <span class="badge badge-slate">1. Submitted</span> &rarr;
                    <span class="badge badge-blue">2. Under Review</span> &rarr;
                    <span class="badge badge-purple">3. Shortlisted</span> &rarr;
                    <span class="badge badge-amber">4. Interview Scheduled</span> &rarr;
                    <span class="badge badge-green">5. Offer / Hired</span>
                </div>
                <p>
                    Use the built-in <strong>Messages</strong> tab (<code>/candidate/messages</code>) to chat directly with Mariwasa HR recruiters and respond to interview RSVP requests.
                </p>
            </div>
        </div>
    </div>

    <!-- PAGE BREAK FOR CHAPTER 4: HR RECRUITER GUIDE -->
    <div class="page-break"></div>

    <div class="manual-header">
        <div class="manual-title-block">
            <div class="chapter-header">HR Recruiter Guide &bull; Chapter 4</div>
            <h1>HR Screening & Talent Acquisition Portal</h1>
            <div class="subtitle">Complete Workflow for Job Posting, AI Applicant Screening, Interviewing & Comparison</div>
        </div>
        <div>{logo_img}</div>
    </div>

    <div class="callout callout-info avoid-break" style="margin-bottom: 3.5mm;">
        <div class="callout-title">🔑 HR Login Access Reference</div>
        Navigate to <code>https://explanation-citizens-cooperative-evidence.trycloudflare.com/login</code> and click <strong>"Continue with Google"</strong>. Authenticate using the official HR account: <strong><code>hr.mariwasa@gmail.com</code></strong> (Password: <code>Password123.</code>).
    </div>

    <div class="step-workflow">
        <div class="workflow-box avoid-break">
            <div class="step-number">1</div>
            <div class="workflow-content">
                <h4>HR Executive Dashboard & Metrics</h4>
                <p>
                    Upon sign-in, you land on <code>/hr/dashboard</code>. Access high-level recruitment KPIs including Total Applicants, Active Job Openings, Candidates Screened, Average AI Match Score, and Upcoming Scheduled Interviews.
                </p>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">2</div>
            <div class="workflow-content">
                <h4>Job Requisition Management</h4>
                <p>
                    Create and publish job requisitions. Define job title, department, position overview, minimum experience years, required education, and weighted technical skill requirements. Openings immediately propagate to the public candidate portal.
                </p>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">3</div>
            <div class="workflow-content">
                <h4>AI Candidate Screening & Skill Radar Analysis</h4>
                <p>
                    In the <strong>Screening Portal</strong> (<code>/hr/screeningportal</code>), applicants are automatically ranked by their overall AI Match Score. Click on any applicant card to inspect:
                </p>
                <ul style="margin: 1mm 0 1mm 4mm; font-size: 7.8pt;">
                    <li><strong>Overall Match %:</strong> Weighted score synthesized across all qualification criteria.</li>
                    <li><strong>Skills Radar Chart:</strong> Visual breakdown comparing Candidate Skills vs. Job Requirements.</li>
                    <li><strong>Matching Skills vs. Missing Skills:</strong> Immediate visibility into skill gaps (highlighted in red badges).</li>
                    <li><strong>Parsed Resume View:</strong> Full structured resume alongside original PDF document viewer.</li>
                </ul>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">4</div>
            <div class="workflow-content">
                <h4>Side-by-Side Candidate Comparison Matrix</h4>
                <p>
                    Under <strong>Compare Candidates</strong> (<code>/hr/comparecandidates</code>), select 2 to 4 shortlisted candidates. The system generates a comprehensive comparative matrix aligning match scores, skill competencies, years of experience, and educational attainment side-by-side to eliminate hiring bias.
                </p>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">5</div>
            <div class="workflow-content">
                <h4>Interview Scheduling & Google Calendar Integration</h4>
                <p>
                    Navigate to <strong>Scheduling</strong> (<code>/hr/scheduling</code>). Select a shortlisted candidate, designate interview type (Technical Interview, HR Behavioral, or Panel Interview), assign interviewers, and pick date/time slots. The system automatically:
                </p>
                <ul style="margin: 1mm 0 1mm 4mm; font-size: 7.8pt;">
                    <li>Dispatches email notifications with calendar invites (.ics).</li>
                    <li>Syncs event details with Google Calendar and generates Google Meet video links.</li>
                    <li>Updates the candidate's tracking portal with RSVP action buttons.</li>
                </ul>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">6</div>
            <div class="workflow-content">
                <h4>Automated AI Phone Screening Calls</h4>
                <p>
                    For preliminary high-volume screening, trigger automated AI voice calls directly from the candidate profile. The AI agent conducts automated qualification questions and records responses for recruiter review.
                </p>
            </div>
        </div>

        <div class="workflow-box avoid-break">
            <div class="step-number">7</div>
            <div class="workflow-content">
                <h4>Physical Hard-Copy Resume Filing System</h4>
                <p>
                    Under <strong>Physical Resumes</strong> (<code>/hr/physical-resumes</code>), catalog physical hard-copy resumes submitted at the Mariwasa plant gate. Assign Cabinet, Drawer, and Folder IDs, generate barcode labels, and maintain compliance records.
                </p>
            </div>
        </div>
    </div>

    <!-- PAGE BREAK FOR CHAPTER 5: ADMIN GUIDE & TROUBLESHOOTING -->
    <div class="page-break"></div>

    <div class="manual-header">
        <div class="manual-title-block">
            <div class="chapter-header">Administration & Maintenance &bull; Chapter 5</div>
            <h1>Administrator Control & Operations Guide</h1>
            <div class="subtitle">System Governance, Scoring Configuration, Audit Logs & Operational Troubleshooting</div>
        </div>
        <div>{logo_img}</div>
    </div>

    <div class="callout callout-info avoid-break" style="margin-bottom: 3.5mm;">
        <div class="callout-title">🛡️ Administrator Access Reference</div>
        Navigate to <code>https://explanation-citizens-cooperative-evidence.trycloudflare.com/login</code> and sign in directly using email: <strong><code>jp@gmail.com</code></strong> (Password: <code>password</code>).
    </div>

    <h2>5.1 Administrative Core Functions</h2>
    <div class="grid-2 avoid-break" style="gap: 3mm; margin-bottom: 4mm;">
        <div class="feature-card">
            <div class="feature-card-header" style="color: #6b21a8;">
                <span>👥 User Management & RBAC</span>
            </div>
            <p style="font-size: 8pt; color: #475569; margin: 0;">
                Located at <code>/admin/users</code>. Administrators can view all registered accounts, change role assignments (Candidate, HR, Admin), activate or suspend accounts, reset user credentials, and monitor last-login timestamps.
            </p>
        </div>
        <div class="feature-card">
            <div class="feature-card-header" style="color: #1e40af;">
                <span>⚙️ AI Scoring Weights & Thresholds</span>
            </div>
            <p style="font-size: 8pt; color: #475569; margin: 0;">
                Located at <code>/admin/system-config</code>. Fine-tune algorithm weights for overall score calculation: Skills Match (Default: 40%), Experience (30%), Education (20%), Semantic Similarity (10%), and minimum passing threshold (Default: 60%).
            </p>
        </div>
        <div class="feature-card">
            <div class="feature-card-header" style="color: #059669;">
                <span>📋 Enterprise Job Management</span>
            </div>
            <p style="font-size: 8pt; color: #475569; margin: 0;">
                Located at <code>/admin/jobmanagement</code>. System-wide oversight over all active, closed, and draft job requisitions across all plant divisions with full audit control and deletion safeguards.
            </p>
        </div>
        <div class="feature-card">
            <div class="feature-card-header" style="color: #b45309;">
                <span>📜 Security Audit Trail & Event Logs</span>
            </div>
            <p style="font-size: 8pt; color: #475569; margin: 0;">
                Maintains an immutable record of authentication events, role changes, job creation/deletion, score overrides, and data exports. Ensures full compliance with Philippine Data Privacy Act (RA 10173).
            </p>
        </div>
    </div>

    <h2>5.2 Troubleshooting & Frequently Asked Questions (FAQs)</h2>

    <table class="data-table avoid-break" style="margin-top: 2mm; margin-bottom: 3mm;">
        <thead>
            <tr>
                <th style="width: 28%;">Issue Description</th>
                <th style="width: 32%;">Potential Cause</th>
                <th style="width: 40%;">Recommended Corrective Action</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Google Sign-In Popup Blocked or Fails to Load</strong></td>
                <td>Browser popup blocker active or third-party cookie restrictions.</td>
                <td>Allow popups for <code>*.trycloudflare.com</code>. Ensure you are signed into <code>hr.mariwasa@gmail.com</code> in your browser session before clicking "Continue with Google".</td>
            </tr>
            <tr>
                <td><strong>Resume Parsing Fails or Returns Blank Fields</strong></td>
                <td>File is password-protected, corrupt, or contains low-resolution raster images without text.</td>
                <td>Ensure the document is a native PDF or DOCX file (under 10MB) with selectable text. Scanned images must be clean and legible for OCR processing.</td>
            </tr>
            <tr>
                <td><strong>"502 Bad Gateway" on Cloudflare Tunnel URL</strong></td>
                <td>Backend FastAPI server, Docker containers, or Cloudflare daemon restarting.</td>
                <td>Wait 30-60 seconds for health check to pass. System administrators should verify Docker status via <code>docker compose ps</code>.</td>
            </tr>
            <tr>
                <td><strong>Cannot see Candidate Scores in HR Portal</strong></td>
                <td>Candidate application is in initial queue and Celery AI task is processing.</td>
                <td>AI parsing and scoring takes 3-10 seconds per resume. Refresh the page or check the Celery worker queue logs.</td>
            </tr>
            <tr>
                <td><strong>Forgot Password for Administrator Account</strong></td>
                <td>Admin password lost or misconfigured.</td>
                <td>Use <code>/forgot-password</code> recovery flow, or execute database reset seed via <code>./start.sh --seed</code> from backend terminal.</td>
            </tr>
        </tbody>
    </table>

    <div class="callout callout-tip avoid-break" style="margin-top: 3mm;">
        <div class="callout-title">📞 Technical Support & Inquiries</div>
        <div style="font-size: 8pt; color: #064e3b; display: flex; justify-content: space-between; flex-wrap: wrap;">
            <span><strong>System Maintenance:</strong> Mariwasa IT Operations & STI College Thesis Team</span>
            <span><strong>Facility Location:</strong> Mariwasa Plant, Sto. Tomas, Batangas</span>
            <span><strong>Support Channel:</strong> hr.mariwasa@gmail.com</span>
        </div>
    </div>

</body>
</html>
"""

html_path = "/tmp/aras_short_manual.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Wrote short manual HTML ({len(html_content)} bytes) to {html_path}")

raw_pdf_path = "/tmp/aras_short_raw.pdf"
output_pdf_path = "/home/marvin/Documents/automated_resume_analysis/Short_User_Manual.pdf"
output_pdf_alt = "/home/marvin/Documents/automated_resume_analysis/Automated_Resume_Analysis_Short_User_Manual.pdf"

print("Compiling Short Manual HTML to PDF via headless Google Chrome...")
chrome_cmd = [
    "google-chrome",
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--no-pdf-header-footer",
    f"--print-to-pdf={raw_pdf_path}",
    html_path
]

res = subprocess.run(chrome_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print("Chrome compilation failed:", res.stderr)
    sys.exit(1)

print(f"Raw PDF compiled successfully: {os.path.getsize(raw_pdf_path)} bytes")

print("Stamping running headers, footers, divider lines and page numbers via PyMuPDF...")
doc = fitz.open(raw_pdf_path)
total_pages = len(doc)
print(f"Total short manual pages: {total_pages}")

hdr_color = (0.2, 0.25, 0.35)
rule_color = (0.82, 0.85, 0.90)
ftr_color = (0.35, 0.40, 0.50)

for idx in range(total_pages):
    page = doc[idx]
    rect = page.rect
    page_num = idx + 1
    
    # Running Header (Skip page 1 header line if top already has header)
    if idx > 0:
        hdr_left = "AUTOMATED RESUME ANALYSIS SYSTEM — QUICK START MANUAL"
        hdr_right = "MARIWASA SIAM CERAMICS INC."
        page.insert_text((42, 30), hdr_left, fontsize=7.5, color=hdr_color)
        page.insert_text((rect.width - 195, 30), hdr_right, fontsize=7.5, color=(0.15, 0.30, 0.70))
        page.draw_line((42, 35), (rect.width - 42, 35), color=rule_color, width=0.65)
    
    # Running Footer Rule Line
    page.draw_line((42, rect.height - 35), (rect.width - 42, rect.height - 35), color=rule_color, width=0.65)
    
    # Running Footer Text
    ftr_left = "Quick Start Reference Guide & System Operations Manual"
    ftr_center = "MARIWASA SIAM CERAMICS &bull; STI CS THESIS"
    ftr_right = f"Page {page_num} of {total_pages}"
    
    page.insert_text((42, rect.height - 23), ftr_left, fontsize=7.5, color=ftr_color)
    page.insert_text((rect.width / 2 - 75, rect.height - 23), "MARIWASA INTERNAL / RESTRICTED", fontsize=7, color=(0.55, 0.60, 0.70))
    page.insert_text((rect.width - 85, rect.height - 23), ftr_right, fontsize=7.5, color=hdr_color)

doc.save(output_pdf_path)
doc.save(output_pdf_alt)

print(f"SUCCESS! Short User Manual written to:\n  - {output_pdf_path}\n  - {output_pdf_alt}")
print(f"Final Short PDF Size: {os.path.getsize(output_pdf_path)} bytes across {total_pages} pages.")

