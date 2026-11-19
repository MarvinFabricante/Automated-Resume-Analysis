def get_ch3_html():
    return """
    <div class="page-break"></div>
    <div class="chapter-header">Chapter 3 &bull; Candidate Portal</div>
    <h1>Candidate Portal Operations Manual</h1>
    
    <h2>3.1 Candidate Portal Overview & Dashboard</h2>
    <p>The Candidate Portal provides job seekers with a streamlined, transparent experience. Upon logging into <code>/candidate/dashboard</code>, applicants are greeted with a personalized command center featuring four primary summary counters:</p>
    
    <div class="grid-4 avoid-break">
        <div class="feature-card" style="text-align: center;">
            <div style="font-size: 16pt; font-weight: 800; color: #2563eb;">Total Applied</div>
            <div style="font-size: 8pt; color: #64748b; margin-top: 1mm;">Active submissions</div>
        </div>
        <div class="feature-card" style="text-align: center;">
            <div style="font-size: 16pt; font-weight: 800; color: #d97706;">Under Review</div>
            <div style="font-size: 8pt; color: #64748b; margin-top: 1mm;">Screening by HR</div>
        </div>
        <div class="feature-card" style="text-align: center;">
            <div style="font-size: 16pt; font-weight: 800; color: #059669;">Shortlisted</div>
            <div style="font-size: 8pt; color: #64748b; margin-top: 1mm;">Qualified for next round</div>
        </div>
        <div class="feature-card" style="text-align: center;">
            <div style="font-size: 16pt; font-weight: 800; color: #7c3aed;">Interviews</div>
            <div style="font-size: 8pt; color: #64748b; margin-top: 1mm;">Scheduled sessions</div>
        </div>
    </div>
    
    <h2>3.2 Finding & Filtering Job Opportunities</h2>
    <p>Candidates can browse all open requisitions at <code>/candidate/findjobs</code> (or the public <code>/careerspage</code>). The interface provides real-time search and multi-facet filtering:</p>
    <ul>
        <li><strong>Search Bar:</strong> Type keywords matching job titles, required technical proficiencies (e.g. <em>AutoCAD</em>, <em>Lean Manufacturing</em>), or department names.</li>
        <li><strong>Department Filter:</strong> Filter across <em>Manufacturing</em>, <em>Quality Assurance</em>, <em>Engineering & Maintenance</em>, <em>Supply Chain & Logistics</em>, or <em>Human Resources</em>.</li>
        <li><strong>Employment Type:</strong> Select <em>Full-Time</em>, <em>Part-Time</em>, or <em>Contractual</em> roles.</li>
        <li><strong>Job Requisition Cards:</strong> Each card displays the job title, department badge, plant location (Santo Tomas, Batangas), salary range, and required experience level. Clicking <em>View Details</em> opens the full job description.</li>
    </ul>
    
    <h2>3.3 The "Smart Match" Direct Resume Upload Workflow</h2>
    <p>A signature innovation of ARAS is the <strong>Smart Match</strong> capability (<code>/candidate/smart-upload</code>). Job seekers are not required to manually inspect dozens of job postings. Instead, candidates can simply upload their resume once, and the engine automatically calculates their fit across <em>every single active vacancy</em> in the organization.</p>
    
    <div class="step-workflow avoid-break">
        <div class="step-item">
            <div class="step-badge">1</div>
            <div class="step-content">
                <div class="step-title">Drag-and-Drop Resume Ingestion</div>
                <p>Upload a resume in PDF, DOCX, or plain text format (maximum file size: 10MB). The file is uploaded asynchronously to Supabase Storage.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">2</div>
            <div class="step-content">
                <div class="step-title">Deterministic NLP Extraction</div>
                <p>The backend Celery worker and spaCy engine parse the document in under 800ms, extracting contact information, education history, work timeline, and identifying technical competencies from the curated taxonomy.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">3</div>
            <div class="step-content">
                <div class="step-title">Multi-Job Algorithmic Matching</div>
                <p>The parsed data is matched against all open job requisitions using the Multi-Factor scoring formula (Skills 50%, Experience 30%, Education 20%).</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">4</div>
            <div class="step-content">
                <div class="step-title">Ranked Recommendation List</div>
                <p>The candidate is redirected to <code>/candidate/smart-matches</code>, displaying a ranked list of best-fitting positions ordered by match score (e.g., <em>Production Engineer &mdash; 92% Match</em>). Matched skills are highlighted with green badges, and a 1-click <em>Apply Now</em> button facilitates instant application.</p>
            </div>
        </div>
    </div>
    
    <h2>3.4 Human-in-the-Loop "Preview & Verify" Interface</h2>
    <p>To guarantee 100% data fidelity and prevent algorithmic misinterpretation, ARAS mandates a <strong>Preview & Verify</strong> step prior to final job application submission (<code>/preview-and-verify/[jobId]</code>). Candidates review the raw information extracted by the AI and can edit, add, or delete any record.</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 25%;">Extracted Section</th>
                <th style="width: 45%;">Candidate Verification Actions Available</th>
                <th style="width: 30%;">Impact on Match Score</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Personal & Contact</strong></td>
                <td>Edit Full Name, Email, Contact Phone, and Residential Address.</td>
                <td>Used for communication and AI Voice phone calls.</td>
            </tr>
            <tr>
                <td><strong>Education History</strong></td>
                <td>Select Degree Level (Doctorate, Master's, Bachelor's, Associate, Vocational, Senior High), Institution Name, Graduation Year.</td>
                <td>Directly recalculates the 20% Education Hierarchy score.</td>
            </tr>
            <tr>
                <td><strong>Work Experience</strong></td>
                <td>Add/Edit employer name, job title, start/end dates, and job summary. Compute total tenure duration.</td>
                <td>Directly recalculates the 30% Experience Relevance score.</td>
            </tr>
            <tr>
                <td><strong>Technical & Soft Skills</strong></td>
                <td>Review parsed skill tags (green pills). Add missing proficiencies or delete irrelevant terms.</td>
                <td>Directly recalculates the 50% Skills Alignment score.</td>
            </tr>
            <tr>
                <td><strong>Certifications</strong></td>
                <td>Add licenses (e.g. PRC Licensed Engineer, TESDA NCII, Six Sigma).</td>
                <td>Awards certification alignment bonus points.</td>
            </tr>
        </tbody>
    </table>
    
    <div class="callout callout-tip avoid-break">
        <div class="callout-title">Candidate Tip for Maximum Match Scores</div>
        If you possess critical certifications (e.g., <em>PRC Mechanical Engineer</em> or <em>Lean Manufacturing</em>) that were abbreviated on your resume, ensure you verify them in the Preview & Verify screen before final submission. This guarantees the scoring engine credits full points.
    </div>
    
    <h2>3.5 Application Tracking Dashboard & Status Progression</h2>
    <p>Candidates track all submissions in real-time at <code>/candidate/applicationtracking</code>. Each application displays an interactive timeline detailing current status:</p>
    
    <div class="step-workflow avoid-break">
        <div class="step-item">
            <div class="step-badge" style="background:#64748b;">1</div>
            <div class="step-content">
                <div class="step-title">SUBMITTED <span class="badge badge-slate">Initial Stage</span></div>
                <p>The application and verified resume credentials have been received and stored in the database. Awaiting recruiter review.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge" style="background:#2563eb;">2</div>
            <div class="step-content">
                <div class="step-title">UNDER REVIEW <span class="badge badge-blue">In Progress</span></div>
                <p>An assigned HR recruiter has opened and reviewed the application details and verified qualifications.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge" style="background:#059669;">3</div>
            <div class="step-content">
                <div class="step-title">SHORTLISTED <span class="badge badge-green">Qualified</span></div>
                <p>The candidate exceeded the match score threshold and has been placed on the priority hiring slate.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge" style="background:#7c3aed;">4</div>
            <div class="step-content">
                <div class="step-title">INTERVIEW SCHEDULED <span class="badge badge-purple">Session Booked</span></div>
                <p>An official interview session has been scheduled. The candidate receives email and calendar invitations, plus an optional automated voice notification.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge" style="background:#0f172a;">5</div>
            <div class="step-content">
                <div class="step-title">ACCEPTED or REJECTED <span class="badge badge-slate">Terminal Decision</span></div>
                <p>Final recruitment outcome. Candidates receive official confirmation and onboarding instructions if accepted.</p>
            </div>
        </div>
    </div>
    
    <h2>3.6 Real-Time Candidate-HR Messaging</h2>
    <p>Candidates can communicate directly with the HR recruitment team at <code>/candidate/messages</code>. The real-time messaging interface is powered by WebSockets:</p>
    <ul>
        <li><strong>Inquiry Threads:</strong> Ask questions regarding plant shift schedules, benefits, or interview locations.</li>
        <li><strong>Document Requests:</strong> Receive requests from recruiters for supplementary credentials (e.g. TOR, NBI clearance, diploma).</li>
        <li><strong>Unread Notification Badges:</strong> Red counter badges indicate pending messages across candidate navigation bars.</li>
    </ul>
    """
