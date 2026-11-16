def get_ch4_html():
    return """
    <div class="page-break"></div>
    <div class="chapter-header">Chapter 4 &bull; HR Screening Portal</div>
    <h1>HR Screening & Recruitment Portal Operations</h1>
    
    <h2>4.1 Recruitment Dashboard & Pipeline Analytics</h2>
    <p>The HR Screening Portal (<code>/hr/dashboard</code>) serves as the daily operational cockpit for recruiters and hiring managers at Mariwasa Siam Ceramics Inc. The dashboard synthesizes high-level recruitment metrics into real-time KPI tiles and visual pipeline funnels:</p>
    
    <div class="grid-4 avoid-break">
        <div class="feature-card">
            <div style="font-size: 8pt; text-transform: uppercase; color: #64748b; font-weight: 700;">Total Applicants</div>
            <div style="font-size: 20pt; font-weight: 900; color: #0f172a; margin: 1mm 0;">1,428</div>
            <div style="font-size: 7.5pt; color: #059669; font-weight: 600;">&uarr; 12% vs last month</div>
        </div>
        <div class="feature-card">
            <div style="font-size: 8pt; text-transform: uppercase; color: #64748b; font-weight: 700;">Pending Review</div>
            <div style="font-size: 20pt; font-weight: 900; color: #d97706; margin: 1mm 0;">184</div>
            <div style="font-size: 7.5pt; color: #d97706; font-weight: 600;">Requires HR action</div>
        </div>
        <div class="feature-card">
            <div style="font-size: 8pt; text-transform: uppercase; color: #64748b; font-weight: 700;">Shortlisted Slate</div>
            <div style="font-size: 20pt; font-weight: 900; color: #059669; margin: 1mm 0;">92</div>
            <div style="font-size: 7.5pt; color: #059669; font-weight: 600;">Score &ge; 75% threshold</div>
        </div>
        <div class="feature-card">
            <div style="font-size: 8pt; text-transform: uppercase; color: #64748b; font-weight: 700;">Interviews Booked</div>
            <div style="font-size: 20pt; font-weight: 900; color: #7c3aed; margin: 1mm 0;">36</div>
            <div style="font-size: 7.5pt; color: #7c3aed; font-weight: 600;">Synced with Google Cal</div>
        </div>
    </div>
    
    <p>Recruiters can monitor application inflow across manufacturing plant departments (Manufacturing, Quality Assurance, Maintenance, Supply Chain, and Administration) to identify pipeline bottlenecks before they disrupt production schedules.</p>
    
    <h2>4.2 Candidate Screening & Ranking Matrix</h2>
    <p>Navigating to <code>/hr/screening</code> opens the candidate evaluation grid. Unlike conventional applicant tracking systems that present unstructured chronologies, ARAS automatically ranks all applicants using the algorithmic <strong>Multi-Factor Match Score</strong> (0% to 100%).</p>
    
    <div class="grid-2 avoid-break">
        <div class="feature-card">
            <div class="feature-card-header" style="color: #1d4ed8;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                Search, Filters & Controls
            </div>
            <ul style="margin: 0; padding-left: 4.5mm; font-size: 8.5pt;">
                <li><strong>Requisition Dropdown:</strong> Filter candidates applied to specific job postings (e.g. <em>Maintenance Technician</em>).</li>
                <li><strong>Minimum Score Slider:</strong> Set cutoffs (e.g., show only applicants with &ge; 70% match score).</li>
                <li><strong>Status Tabs:</strong> View <em>All</em>, <em>Submitted</em>, <em>Under Review</em>, <em>Shortlisted</em>, or <em>Interview Scheduled</em>.</li>
                <li><strong>View Modes:</strong> Toggle between detailed <em>Card View</em> and high-density <em>Table View</em>.</li>
            </ul>
        </div>
        
        <div class="feature-card">
            <div class="feature-card-header" style="color: #7c3aed;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><polyline points="17 11 19 13 23 9"/></svg>
                Bulk Action Toolbar
            </div>
            <p style="font-size: 8.5pt; color: #475569; margin-bottom: 2mm;">Recruiters can select multiple candidates via checkboxes to execute batch actions in 1 click:</p>
            <ul style="margin: 0; padding-left: 4.5mm; font-size: 8.5pt;">
                <li><strong>Bulk Shortlist:</strong> Transition top candidates into the shortlisted queue.</li>
                <li><strong>Bulk Review:</strong> Mark new submissions as Under Review.</li>
                <li><strong>Bulk Export:</strong> Export selected candidate records to CSV or Excel.</li>
            </ul>
        </div>
    </div>
    
    <h2>4.3 Deep Candidate Inspection (Candidate Details Modal)</h2>
    <p>Clicking on any candidate card opens the comprehensive <strong>Candidate Details Modal</strong>. This interface provides unprecedented diagnostic clarity into the algorithmic scoring breakdown:</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 25%;">Evaluation Element</th>
                <th style="width: 50%;">Information Displayed in Inspection Modal</th>
                <th style="width: 25%;">Recruiter Action</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>AI Match Breakdown</strong></td>
                <td>Displays the three weighted component scores: Skills Alignment (50%), Experience Relevance (30%), and Education Level (20%).</td>
                <td>Verify scoring balance against job complexity.</td>
            </tr>
            <tr>
                <td><strong>Matched Skills</strong></td>
                <td>Highlighted in <span class="badge badge-green">GREEN BADGES</span> (e.g., <em>AutoCAD</em>, <em>Lean Six Sigma</em>, <em>Preventive Maintenance</em>).</td>
                <td>Confirms required competencies are possessed.</td>
            </tr>
            <tr>
                <td><strong>Missing Critical Skills</strong></td>
                <td>Highlighted in <span class="badge badge-red">RED BADGES</span>. Pinpoints qualifications requested by the job description that the candidate lacks.</td>
                <td>Determines if on-the-job plant training can bridge gaps.</td>
            </tr>
            <tr>
                <td><strong>Experience Timeline</strong></td>
                <td>Chronological employment tenure with employer names, dates, and responsibilities.</td>
                <td>Cross-check manufacturing tenure.</td>
            </tr>
            <tr>
                <td><strong>In-App Resume Viewer</strong></td>
                <td>Integrated document previewer rendering the original PDF/DOCX file directly in the browser.</td>
                <td>Review original document layout and formatting.</td>
            </tr>
            <tr>
                <td><strong>Recruiter Evaluation</strong></td>
                <td>Private internal text box for HR notes and 1-5 star candidate rating.</td>
                <td>Record remarks visible only to HR staff.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>4.4 Side-by-Side Candidate Comparison Tool</h2>
    <p>When selecting finalists from a competitive applicant pool, recruiters utilize the <strong>Compare Candidates Tool</strong> (<code>/hr/comparecandidates</code>). This feature allows recruiters to lock 2 to 4 candidates in a comparative matrix:</p>
    
    <div class="step-workflow avoid-break">
        <div class="step-item">
            <div class="step-badge">1</div>
            <div class="step-content">
                <div class="step-title">Select Applicants for Benchmarking</div>
                <p>From the Screening Portal, select checkboxes beside 2 to 4 candidates and click <em>Compare Candidates</em>.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">2</div>
            <div class="step-content">
                <div class="step-title">Review Side-by-Side Competency Matrix</div>
                <p>The screen renders a horizontal column for each applicant, contrasting overall AI match scores, years of relevant industry experience, highest degree earned, matched skill counts, and expected salaries.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">3</div>
            <div class="step-content">
                <div class="step-title">AI Comparative Fit Summary</div>
                <p>The system synthesizes a comparative narrative highlighting candidate relative strengths (e.g., <em>Candidate A possesses superior technical certifications, whereas Candidate B brings 3 additional years of plant supervisory experience</em>).</p>
            </div>
        </div>
    </div>
    
    <h2>4.5 Interview Scheduling & Google Calendar Integration</h2>
    <p>ARAS provides full-featured calendar scheduling (<code>/hr/scheduling</code>) with two-way Google Calendar synchronization:</p>
    <ul>
        <li><strong>Schedule Interview Modal:</strong> Set interview date, time window, duration (30, 45, 60 minutes), and interview mode (<em>In-Person Plant Office</em>, <em>Google Meet Video Call</em>, or <em>Phone Interview</em>).</li>
        <li><strong>Interviewer Assignment:</strong> Assign specific HR officers or plant department heads.</li>
        <li><strong>Google Calendar Sync:</strong> Synchronizes scheduled events with the recruiter's official Google Calendar via OAuth 2.0. Generates a Google Meet link automatically for video sessions.</li>
        <li><strong>Candidate Invitation:</strong> Dispatches an automated email and calendar invite (<code>.ics</code>) to the candidate.</li>
        <li><strong>RSVP Tracking:</strong> Tracks whether the candidate has <em>Confirmed</em>, <em>Declined</em>, or requested a <em>Reschedule</em>.</li>
    </ul>
    
    <h2>4.6 Automated AI Voice Interview Caller (Twilio + Gemini Real-Time)</h2>
    <p>To eliminate candidate interview no-shows and accelerate phone screening, ARAS integrates an <strong>Automated AI Voice Caller</strong> powered by Twilio Voice and Google Gemini Real-Time Audio (<code>/ai-caller/</code>):</p>
    
    <div class="grid-2 avoid-break">
        <div class="feature-card">
            <div class="feature-card-header" style="color: #0284c7;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                Core AI Voice Capabilities
            </div>
            <ul style="margin: 0; padding-left: 4.5mm; font-size: 8.5pt;">
                <li><strong>Automated Outbound Calling:</strong> Trigger calls with 1 click from the interview modal (<code>/ai-caller/interview/{id}/call</code>).</li>
                <li><strong>Bilingual Conversational AI:</strong> Converses fluidly in <em>Tagalog / Filipino</em> or <em>English</em>.</li>
                <li><strong>Verbal Response Interpretation:</strong> Natural language understanding interprets spoken responses (e.g. <em>"Opo, makakarating po ako sa interview sa Lunes"</em>) or touch-tone DTMF.</li>
                <li><strong>Automated Attendance Update:</strong> Automatically marks the interview status as <em>CONFIRMED</em> upon affirmative voice response.</li>
            </ul>
        </div>
        
        <div class="feature-card">
            <div class="feature-card-header" style="color: #d97706;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                Resilience & Fallback Protocol
            </div>
            <ul style="margin: 0; padding-left: 4.5mm; font-size: 8.5pt;">
                <li><strong>Smart Retry Policy:</strong> If the call is unanswered, Celery schedules retries after 2 hours and 24 hours.</li>
                <li><strong>Backup SMS Notification:</strong> Dispatches an SMS confirmation reminder if voice call attempts fail.</li>
                <li><strong>Hardware ADB Dialing:</strong> Supports connecting a local Android smartphone via USB ADB for direct SIM dialing.</li>
                <li><strong>Call Audio & Transcripts:</strong> Recruiter can review call duration, status, and transcripts in the interview record.</li>
            </ul>
        </div>
    </div>
    
    <h2>4.7 Physical Hard-Copy Resume Storage Vault</h2>
    <p>At the Mariwasa plant in Santo Tomas, Batangas, many local factory and maintenance workers submit physical, printed paper resumes at the guardhouse or reception desk. The <strong>Physical Hard-Copy Resume Storage Vault</strong> (<code>/hr/physical-resumes</code>) ensures walk-in submissions receive the same digital intelligence as online applications:</p>
    
    <div class="step-workflow avoid-break">
        <div class="step-item">
            <div class="step-badge">1</div>
            <div class="step-content">
                <div class="step-title">Scan & Ingest Hard-Copy Resume</div>
                <p>HR staff scan the paper resume using an office scanner or mobile camera and upload the file (PDF/JPG) at <code>/hr/physical-resumes</code>.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">2</div>
            <div class="step-content">
                <div class="step-title">Assign Physical Filing Location Reference</div>
                <p>The recruiter logs the exact physical storage location tag (e.g. <code>Cabinet B - Drawer 2 - Folder 2026-Eng</code>). This tag is permanently bound to the digital record, allowing any HR officer to physically retrieve the original document in seconds.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">3</div>
            <div class="step-content">
                <div class="step-title">OCR Parsing & Requisition Linking</div>
                <p>The system runs deterministic parsing on the scanned document, links the applicant to the target job requisition, and calculates the AI Match Score alongside digital applicants.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">4</div>
            <div class="step-content">
                <div class="step-title">Vault Search & Retrieval</div>
                <p>Filter physical resumes by status (<code>RECEIVED</code>, <code>UNDER_REVIEW</code>, <code>SHORTLISTED</code>), job requisition, or physical location tag. Recruiters can click <em>Copy Location</em> to copy filing references directly to clipboard.</p>
            </div>
        </div>
    </div>
    """
