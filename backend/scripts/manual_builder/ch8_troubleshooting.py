def get_ch8_html():
    return """
    <div class="page-break"></div>
    <div class="chapter-header">Chapter 8 &bull; Troubleshooting & Reference</div>
    <h1>Troubleshooting, FAQs & System Appendices</h1>
    
    <h2>8.1 Diagnostics & Operational Recovery Procedures</h2>
    <p>This section documents structured recovery procedures for the most common technical anomalies encountered during production operation:</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 28%;">Diagnostic Symptom</th>
                <th style="width: 32%;">Probable Root Cause</th>
                <th>Standard Resolution Procedure</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Resume upload stuck on "Parsing..."</strong></td>
                <td>Celery worker is offline or Redis broker connection timed out.</td>
                <td>Run <code>./start.sh --status</code> to verify worker health. If stalled, execute <code>docker-compose restart celery_worker redis</code>. Check logs via <code>./start.sh --logs celery_worker</code>.</td>
            </tr>
            <tr>
                <td><strong>Frontend reports CORS / Network Error</strong></td>
                <td>Cloudflare tunnel regenerated a new URL that is not yet reflected in backend CORS origins.</td>
                <td>Execute <code>./start.sh -r</code> to cleanly restart all containers and automatically synchronize new tunnel URLs into backend CORS middleware.</td>
            </tr>
            <tr>
                <td><strong>Resume upload returns HTTP 403 Forbidden</strong></td>
                <td>Invalid or expired <code>SUPABASE_SERVICE_ROLE_KEY</code> in <code>.env</code>.</td>
                <td>Verify Supabase credentials in <code>.env</code>. Confirm that storage buckets <code>resumes</code>, <code>profile_images</code>, and <code>resume_images</code> exist and have appropriate access policies.</td>
            </tr>
            <tr>
                <td><strong>LLM Summary displays "Score calculated via deterministic rules"</strong></td>
                <td>Gemini API keys exceeded daily quota or encountered internet latency.</td>
                <td>This is normal system resilience behavior. The deterministic scoring engine operates unaffected. To restore LLM summaries, add fresh keys to <code>GEMINI_API_KEYS</code> in <code>.env</code> or via Admin Settings.</td>
            </tr>
            <tr>
                <td><strong>Automated Voice Call fails to connect</strong></td>
                <td>Candidate phone number is not in E.164 format, or Twilio account balance is depleted.</td>
                <td>Verify candidate phone number begins with <code>+639...</code>. In development environments, utilize the <strong>Simulate Voice Call</strong> feature on the interview details modal to test flow without Twilio telephony charges.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>8.2 Frequently Asked Questions (FAQ)</h2>
    
    <div class="grid-2 avoid-break">
        <div class="feature-card">
            <div class="feature-card-header" style="color: #2563eb;">Candidate FAQs</div>
            <p><strong>Q: What file formats are supported for resume upload?</strong><br>
            A: The system natively supports PDF (<code>.pdf</code>), Microsoft Word (<code>.docx</code>), and plain text (<code>.txt</code>) files up to 10MB in size.</p>
            <p><strong>Q: Can I fix an error if the AI misread my degree?</strong><br>
            A: Yes! The <em>Preview & Verify</em> screen specifically allows you to edit, add, or delete any extracted degree, skill, or job experience before you submit.</p>
            <p><strong>Q: What does my Match Score mean?</strong><br>
            A: It indicates how closely your verified qualifications match the specific job's technical competencies, experience level, and educational criteria.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-card-header" style="color: #047857;">HR Recruiter FAQs</div>
            <p><strong>Q: How are applicants ranked on the screening portal?</strong><br>
            A: Applicants are automatically sorted by their overall AI Match Score (highest to lowest), factoring in skills (50%), experience (30%), and education (20%).</p>
            <p><strong>Q: How do I file walk-in printed resumes?</strong><br>
            A: Scan the paper resume, upload it at <code>/hr/physical-resumes</code>, and enter the physical filing reference (e.g. <em>Cabinet B, Drawer 1</em>). The AI will parse the scan automatically.</p>
            <p><strong>Q: Does the AI Voice Caller replace HR interviews?</strong><br>
            A: No. The AI Caller conducts automated notification and preliminary attendance confirmation calls to reduce interview no-show rates.</p>
        </div>
    </div>
    
    <h2>8.3 Application Status Lifecycle State Machine</h2>
    <p>All job applications transition through well-defined lifecycle states governed by strict validation rules:</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 25%;">Status Identifier</th>
                <th style="width: 20%; text-align: center;">Portal Display Badge</th>
                <th>State Semantics & Allowed Next Transitions</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><code>SUBMITTED</code></td>
                <td style="text-align: center;"><span class="badge badge-slate">SUBMITTED</span></td>
                <td>Initial submission stage. Candidate data parsed. Can transition to <code>UNDER_REVIEW</code> or <code>REJECTED</code>.</td>
            </tr>
            <tr>
                <td><code>UNDER_REVIEW</code></td>
                <td style="text-align: center;"><span class="badge badge-blue">UNDER REVIEW</span></td>
                <td>Recruiter is inspecting profile. Can transition to <code>SHORTLISTED</code> or <code>REJECTED</code>.</td>
            </tr>
            <tr>
                <td><code>SHORTLISTED</code></td>
                <td style="text-align: center;"><span class="badge badge-green">SHORTLISTED</span></td>
                <td>Applicant qualified for interview round. Can transition to <code>INTERVIEW_SCHEDULED</code> or <code>REJECTED</code>.</td>
            </tr>
            <tr>
                <td><code>INTERVIEW_SCHEDULED</code></td>
                <td style="text-align: center;"><span class="badge badge-purple">INTERVIEW BOOKED</span></td>
                <td>Official interview time booked. Can transition to <code>ACCEPTED</code> or <code>REJECTED</code>.</td>
            </tr>
            <tr>
                <td><code>ACCEPTED</code></td>
                <td style="text-align: center;"><span class="badge badge-green">ACCEPTED</span></td>
                <td>Terminal state. Candidate received formal job offer and onboarding package.</td>
            </tr>
            <tr>
                <td><code>REJECTED</code></td>
                <td style="text-align: center;"><span class="badge badge-red">REJECTED</span></td>
                <td>Terminal state. Candidate qualifications did not meet criteria for this requisition.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>8.4 System Specifications & Supported Browsers</h2>
    <p>ARAS is engineered for cross-platform compatibility across modern desktop and mobile browsers:</p>
    <ul>
        <li><strong>Google Chrome / Chromium:</strong> Version 100+ (Full desktop & mobile support recommended).</li>
        <li><strong>Mozilla Firefox:</strong> Version 110+ (Full support).</li>
        <li><strong>Apple Safari:</strong> Version 16+ (macOS & iOS Safari supported).</li>
        <li><strong>Microsoft Edge:</strong> Version 100+ (Chromium-based full support).</li>
    </ul>
    
    <h2>8.5 Support & Corporate Directory</h2>
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 30%;">Department / Role</th>
                <th style="width: 35%;">Contact Channel</th>
                <th>Operational Responsibility</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Mariwasa HR Operations</strong></td>
                <td><code>hr.recruitment@mariwasa.com</code></td>
                <td>Candidate inquiries, interview scheduling, and hiring workflows.</td>
            </tr>
            <tr>
                <td><strong>IT Operations Helpdesk</strong></td>
                <td><code>it.support@mariwasa.com</code></td>
                <td>User account provisioning, password lockouts, and system access.</td>
            </tr>
            <tr>
                <td><strong>ARAS Systems Engineering</strong></td>
                <td><code>aras-dev@mariwasa.com</code></td>
                <td>Server deployment, container maintenance, and scoring algorithm calibration.</td>
            </tr>
        </tbody>
    </table>
    
    <div class="callout callout-info avoid-break" style="margin-top: 6mm;">
        <div class="callout-title">Official Document Authentication</div>
        This document represents the authorized enterprise operational specification for the <strong>Automated Resume Analysis System</strong> at <strong>Mariwasa Siam Ceramics Inc.</strong> Version 2.4.0. Effective November 2026.
    </div>
    """
