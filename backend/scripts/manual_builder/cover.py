def get_cover_html(logo_b64=""):
    logo_img = f'<img src="data:image/png;base64,{logo_b64}" alt="Logo">' if logo_b64 else '<span style="font-size:24pt; font-weight:900; color:#1e40af;">MARIWASA</span>'
    
    return f"""
    <div class="cover-container">
        <div class="cover-header">
            <div class="cover-logo">
                {logo_img}
            </div>
            <div class="cover-org-title">
                <div class="cover-org-name">MARIWASA SIAM CERAMICS INC.</div>
                <div class="cover-org-sub">Talent Acquisition & Technology Operations</div>
            </div>
        </div>
        
        <div class="cover-body">
            <div class="cover-tag">Enterprise Standard Operating Procedure & End-User Manual</div>
            <div class="cover-title">Automated Resume Analysis System</div>
            <div class="cover-subtitle">An Enterprise-Grade AI Ecosystem for High-Volume Talent Screening, Natural Language Resume Parsing & Intelligent Match Scoring</div>
            <div class="cover-divider"></div>
            
            <div class="cover-meta-grid">
                <div class="cover-meta-item">
                    <div class="cover-meta-label">Document Reference</div>
                    <div class="cover-meta-value">SOP-HR-ARAS-2026-v2.4</div>
                </div>
                <div class="cover-meta-item">
                    <div class="cover-meta-label">Software Version</div>
                    <div class="cover-meta-value">Release 2.4.0 (Enterprise Production)</div>
                </div>
                <div class="cover-meta-item">
                    <div class="cover-meta-label">Target Audience</div>
                    <div class="cover-meta-value">Candidates, HR Staff, Recruiters, Administrators</div>
                </div>
                <div class="cover-meta-item">
                    <div class="cover-meta-label">Effective Date</div>
                    <div class="cover-meta-value">November 2026</div>
                </div>
                <div class="cover-meta-item">
                    <div class="cover-meta-label">Client Facility</div>
                    <div class="cover-meta-value">Mariwasa Plant, Sto. Tomas, Batangas</div>
                </div>
                <div class="cover-meta-item">
                    <div class="cover-meta-label">Security Classification</div>
                    <div class="cover-meta-value">RESTRICTED / INTERNAL BUSINESS USE</div>
                </div>
            </div>
        </div>
        
        <div class="cover-footer">
            <div>&copy; 2026 Mariwasa Siam Ceramics Inc. — STI CS Thesis Academic Project</div>
            <div>Powered by Next.js 15, FastAPI, Celery, spaCy NLP & Gemini AI</div>
        </div>
    </div>
    
    <div class="page-break"></div>
    
    <!-- DOCUMENT CONTROL & REVISION HISTORY -->
    <div class="chapter-header">System Governance & Document Control</div>
    <h1>Document Information & Approval History</h1>
    
    <p>This document serves as the official operational manual and system administration specification for the <strong>Automated Resume Analysis System (ARAS)</strong> deployed at <strong>Mariwasa Siam Ceramics Inc.</strong> It outlines end-to-end workflows for Candidates, HR Screening Personnel, and System Administrators, detailing functional interfaces, algorithmic scoring formulas, voice interview integrations, and operational recovery protocols.</p>
    
    <div class="callout callout-info avoid-break">
        <div class="callout-title">Document Scope & Distribution Notice</div>
        The policies, procedures, and technical configurations contained herein apply to all human resource operations, factory plant hiring cycles, and administrative governance for Mariwasa Siam Ceramics Inc. Reproduction or distribution outside authorized organizational channels requires written permission from the Chief Information Officer and the Head of Human Resources.
    </div>
    
    <h2>Document Control Summary</h2>
    <table class="data-table avoid-break">
        <tr>
            <th style="width: 28%;">Attribute</th>
            <th>Specification Details</th>
        </tr>
        <tr>
            <td><strong>Document Title</strong></td>
            <td>Automated Resume Analysis System — Enterprise User Manual & Operations Guide</td>
        </tr>
        <tr>
            <td><strong>Document Identifier</strong></td>
            <td><code>MSCI-HR-ARAS-DOC-2026-V2.4</code></td>
        </tr>
        <tr>
            <td><strong>Custodian Department</strong></td>
            <td>Human Resources Management Department & IT Operations Group</td>
        </tr>
        <tr>
            <td><strong>Primary Target Roles</strong></td>
            <td>Job Candidates, HR Screening Officers, Talent Acquisition Leads, System Administrators</td>
        </tr>
        <tr>
            <td><strong>Core Engine Technologies</strong></td>
            <td>FastAPI 0.111, Next.js 15, Celery 5.4, Redis 7, PostgreSQL 16, spaCy 3.7, Google Gemini 1.5/2.0 Flash</td>
        </tr>
    </table>
    
    <h2>Revision & Change Management Log</h2>
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 12%;">Version</th>
                <th style="width: 16%;">Release Date</th>
                <th style="width: 22%;">Primary Author</th>
                <th>Summary of Structural Changes & Feature Enhancements</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="badge badge-slate">v1.0.0</span></td>
                <td>May 2026</td>
                <td>Project Engineering</td>
                <td>Initial prototype release. Deterministic regex-based resume parsing, basic PostgreSQL relational schemas, and manual candidate listing.</td>
            </tr>
            <tr>
                <td><span class="badge badge-slate">v1.5.0</span></td>
                <td>July 2026</td>
                <td>NLP Core Team</td>
                <td>Integration of spaCy PhraseMatcher with 2,000+ domain taxonomy. Introduced weighted matching scoring (Skills, Experience, Education).</td>
            </tr>
            <tr>
                <td><span class="badge badge-slate">v2.0.0</span></td>
                <td>October 2026</td>
                <td>Fullstack Team</td>
                <td>Architectural migration to Next.js 15 App Router and FastAPI Asynchronous Celery workers. Added Cloudflare Tunnel orchestration and Redis caching.</td>
            </tr>
            <tr>
                <td><span class="badge badge-slate">v2.2.0</span></td>
                <td>Late Oct 2026</td>
                <td>Voice & ATS Team</td>
                <td>Added Twilio + Gemini Real-Time Voice Interview Caller (Bilingual Filipino/English) and Physical Hard-Copy Resume Storage Vault with Cabinet/Drawer tracking.</td>
            </tr>
            <tr>
                <td><span class="badge badge-blue">v2.4.0</span></td>
                <td>November 2026</td>
                <td>Release Engineering</td>
                <td>Enterprise Production Edition. Dynamic runtime scoring weights, Google Calendar OAuth sync, multi-candidate comparison, and self-service Preview & Verify flow.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>Formal Approvals & Sign-Off</h2>
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 25%;">Stakeholder Role</th>
                <th style="width: 28%;">Name & Title</th>
                <th style="width: 22%;">Status</th>
                <th>Verification Date</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Lead System Architect</strong></td>
                <td>STI CS Thesis Engineering Lead</td>
                <td><span class="badge badge-green">APPROVED</span></td>
                <td>November 10, 2026</td>
            </tr>
            <tr>
                <td><strong>HR Operations Lead</strong></td>
                <td>HR Screening Lead, Mariwasa</td>
                <td><span class="badge badge-green">APPROVED</span></td>
                <td>November 11, 2026</td>
            </tr>
            <tr>
                <td><strong>Talent Acquisition Head</strong></td>
                <td>Director of HR & Admin, Mariwasa</td>
                <td><span class="badge badge-green">APPROVED</span></td>
                <td>November 12, 2026</td>
            </tr>
            <tr>
                <td><strong>Chief Technology Officer</strong></td>
                <td>Academic & Industrial Supervisor</td>
                <td><span class="badge badge-green">APPROVED</span></td>
                <td>November 13, 2026</td>
            </tr>
        </tbody>
    </table>
    
    <div class="page-break"></div>
    
    <!-- TABLE OF CONTENTS -->
    <div class="chapter-header">Reference Guide</div>
    <h1>Table of Contents</h1>
    
    <table class="data-table" style="font-size: 9pt;">
        <thead>
            <tr>
                <th style="width: 15%;">Section</th>
                <th style="width: 70%;">Chapter Title & Key Submodules</th>
                <th style="width: 15%; text-align: right;">Page Ref</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Chapter 1</strong></td>
                <td><strong>Executive Summary & System Architecture</strong><br>
                <span style="color:#64748b; font-size:8pt;">Organizational Context &bull; Core Problems Solved &bull; The Three-Portal Ecosystem &bull; Technical Topology & Data Flow</span></td>
                <td style="text-align: right; font-weight:700;">Page 4</td>
            </tr>
            <tr>
                <td><strong>Chapter 2</strong></td>
                <td><strong>System Access, Authentication & Role-Based Permissions</strong><br>
                <span style="color:#64748b; font-size:8pt;">Access URLs &bull; RBAC Security Matrix &bull; Candidate Registration &bull; JWT Authentication &bull; Password Reset</span></td>
                <td style="text-align: right; font-weight:700;">Page 7</td>
            </tr>
            <tr>
                <td><strong>Chapter 3</strong></td>
                <td><strong>Candidate Portal User Guide</strong><br>
                <span style="color:#64748b; font-size:8pt;">Candidate Dashboard &bull; Job Browsing &bull; Smart Match Direct Upload &bull; Human-in-the-Loop Preview & Verify &bull; Application Tracking &bull; Messaging</span></td>
                <td style="text-align: right; font-weight:700;">Page 9</td>
            </tr>
            <tr>
                <td><strong>Chapter 4</strong></td>
                <td><strong>HR Screening & Recruitment Portal Operations</strong><br>
                <span style="color:#64748b; font-size:8pt;">HR Dashboard & Funnels &bull; Candidate Screening Matrix &bull; Deep Profile Inspection &bull; Side-by-Side Comparison &bull; Interview Scheduling &bull; AI Voice Caller &bull; Physical Resumes Vault</span></td>
                <td style="text-align: right; font-weight:700;">Page 11</td>
            </tr>
            <tr>
                <td><strong>Chapter 5</strong></td>
                <td><strong>System Administrator Control Center Guide</strong><br>
                <span style="color:#64748b; font-size:8pt;">System Telemetry & Monitoring &bull; User & Role Management &bull; Job Requisition CRUD &bull; Dynamic Configuration & AI Weights &bull; Security Audit Logging</span></td>
                <td style="text-align: right; font-weight:700;">Page 14</td>
            </tr>
            <tr>
                <td><strong>Chapter 6</strong></td>
                <td><strong>AI Engine & Algorithmic Scoring Specifications</strong><br>
                <span style="color:#64748b; font-size:8pt;">Deterministic Ingestion Engine &bull; spaCy PhraseMatcher &bull; Multi-Factor Scoring Formula &bull; Degree Hierarchy Logic &bull; Twilio Voice Stream</span></td>
                <td style="text-align: right; font-weight:700;">Page 16</td>
            </tr>
            <tr>
                <td><strong>Chapter 7</strong></td>
                <td><strong>Deployment, CLI Operations & Environment Setup</strong><br>
                <span style="color:#64748b; font-size:8pt;">Container Topology &bull; <code>./start.sh</code> Orchestrator Reference &bull; Environment Variable Glossary &bull; Database Seeding</span></td>
                <td style="text-align: right; font-weight:700;">Page 18</td>
            </tr>
            <tr>
                <td><strong>Chapter 8</strong></td>
                <td><strong>Troubleshooting, FAQs & System Appendices</strong><br>
                <span style="color:#64748b; font-size:8pt;">Diagnostics Scenarios &bull; Candidate/HR/Admin FAQs &bull; Status Machine Dictionary &bull; Escalation Contacts</span></td>
                <td style="text-align: right; font-weight:700;">Page 20</td>
            </tr>
        </tbody>
    </table>
    
    <div class="callout callout-tip avoid-break" style="margin-top: 6mm;">
        <div class="callout-title">Quick Reading Recommendation</div>
        <ul>
            <li><strong>Candidates / Applicants:</strong> Focus directly on <strong>Chapter 2 (Access)</strong> and <strong>Chapter 3 (Candidate Guide)</strong> for step-by-step instructions on resume submission and application tracking.</li>
            <li><strong>HR Recruiters & Hiring Managers:</strong> Proceed directly to <strong>Chapter 4 (HR Portal)</strong> for instructions on candidate ranking, side-by-side comparison, interview booking, and hard-copy archiving.</li>
            <li><strong>System Administrators & DevOps:</strong> Review <strong>Chapter 5 (Admin Control)</strong>, <strong>Chapter 6 (AI Engine)</strong>, and <strong>Chapter 7 (Deployment)</strong>.</li>
        </ul>
    </div>
    """
