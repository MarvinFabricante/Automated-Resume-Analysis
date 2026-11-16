def get_ch5_html():
    return """
    <div class="page-break"></div>
    <div class="chapter-header">Chapter 5 &bull; Admin Control Center</div>
    <h1>System Administration & Governance Guide</h1>
    
    <h2>5.1 Admin Dashboard & Infrastructure Telemetry</h2>
    <p>The Admin Control Center (<code>/admin/dashboard</code>) gives system administrators and IT leads total visibility over operational infrastructure, active user traffic, and background task queues:</p>
    
    <div class="grid-3 avoid-break">
        <div class="feature-card">
            <div class="feature-card-header" style="color: #2563eb;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                PostgreSQL 16 Connection Pool
            </div>
            <p style="font-size: 8.5pt; color: #475569;">Monitors active and idle database connections managed by <code>asyncpg</code>. Default pool size: 10 connections with overflow ceiling of 5 and automatic pre-ping health checks.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-card-header" style="color: #d97706;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
                Redis 7 Message Broker
            </div>
            <p style="font-size: 8.5pt; color: #475569;">Tracks Celery task backlog, Celery worker ping responses, and Redis key memory utilization for the dynamic matching configuration cache.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-card-header" style="color: #059669;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                Cloudflare Quick Tunnel
            </div>
            <p style="font-size: 8.5pt; color: #475569;">Displays live public HTTPS tunnel ingress URL and verifies that backend CORS middleware dynamically authorizes requests from frontend tunnel endpoints.</p>
        </div>
    </div>
    
    <h2>5.2 User Account Management & Role Provisioning</h2>
    <p>Administrators manage all user credentials, role assignments, and security states at <code>/admin/users</code>:</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 25%;">Administrative Action</th>
                <th style="width: 45%;">Procedural Description</th>
                <th style="width: 30%;">Security Safeguards</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Create Staff Account</strong></td>
                <td>Click <em>+ Add User</em>. Enter staff name, email, initial temporary password, and assign role (<code>HR</code> or <code>ADMIN</code>).</td>
                <td>Requires admin re-authentication; initial login prompts mandatory password update.</td>
            </tr>
            <tr>
                <td><strong>Role Elevation / Demotion</strong></td>
                <td>Change role dropdown between <code>CANDIDATE</code>, <code>HR</code>, and <code>ADMIN</code>.</td>
                <td>Revokes active JWT sessions immediately; logged in audit trail.</td>
            </tr>
            <tr>
                <td><strong>Account Suspension</strong></td>
                <td>Toggle <em>Active / Suspended</em> toggle switch.</td>
                <td>Suspended users are blocked at API middleware with HTTP 403 Forbidden.</td>
            </tr>
            <tr>
                <td><strong>Force Password Reset</strong></td>
                <td>Trigger administrative reset. Dispatches reset link to staff email.</td>
                <td>Invalidates all existing refresh tokens.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>5.3 Job Requisition Management</h2>
    <p>The recruitment team relies on administrators to configure job openings at <code>/admin/jobmanagement</code>. Each job description directly influences the deterministic AI matching engine:</p>
    
    <div class="step-workflow avoid-break">
        <div class="step-item">
            <div class="step-badge">1</div>
            <div class="step-content">
                <div class="step-title">General Job Requisition Details</div>
                <p>Define Job Title (e.g. <em>Production Engineer</em>), Department (e.g. <em>Manufacturing</em>), Employment Type (Full-Time, Contract), Plant Location, and Salary Range.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">2</div>
            <div class="step-content">
                <div class="step-title">Technical Competency Taxonomies</div>
                <p>Input comma-separated technical proficiencies (e.g., <em>AutoCAD, Lean Manufacturing, ISO 9001, Quality Control</em>). These terms are parsed by the spaCy PhraseMatcher during resume ingestion.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">3</div>
            <div class="step-content">
                <div class="step-title">Minimum Educational & Experience Requirements</div>
                <p>Specify the required degree level (e.g., <em>Bachelor's degree in Engineering</em>) and minimum years of industry experience (e.g., <em>2-3 years in ceramics or manufacturing</em>). These parameters establish the baseline for the Education Hierarchy and Experience Relevance algorithms.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">4</div>
            <div class="step-content">
                <div class="step-title">Requisition Status Control</div>
                <p>Toggle job states: <em>Active</em> (visible to public and eligible for Smart Match), <em>Draft</em> (internal review), or <em>Archived</em> (closed position).</p>
            </div>
        </div>
    </div>
    
    <h2>5.4 Dynamic System Configuration & Algorithm Calibration</h2>
    <p>A critical enterprise feature of ARAS is the <strong>Dynamic System Settings</strong> dashboard (<code>/admin/system-config</code>). Administrators can adjust algorithmic parameters in real time without restarting backend servers or modifying source code. Settings are cached in Redis for sub-millisecond retrieval:</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 28%;">Configuration Parameter</th>
                <th style="width: 15%; text-align: center;">Default Value</th>
                <th style="width: 15%; text-align: center;">Adjustable Range</th>
                <th>Algorithmic Impact & Functional Description</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><code>skills_weight</code></td>
                <td style="text-align: center;"><strong>0.45 &ndash; 0.50</strong></td>
                <td style="text-align: center;">0.0 &ndash; 1.0</td>
                <td>Relative weight of direct technical and soft skill overlap in candidate overall match score.</td>
            </tr>
            <tr>
                <td><code>experience_weight</code></td>
                <td style="text-align: center;"><strong>0.25 &ndash; 0.30</strong></td>
                <td style="text-align: center;">0.0 &ndash; 1.0</td>
                <td>Relative weight of total career tenure and semantic job title relevance.</td>
            </tr>
            <tr>
                <td><code>education_weight</code></td>
                <td style="text-align: center;"><strong>0.15 &ndash; 0.20</strong></td>
                <td style="text-align: center;">0.0 &ndash; 1.0</td>
                <td>Relative weight based on degree hierarchy (Doctorate > Master's > Bachelor's > Associate's).</td>
            </tr>
            <tr>
                <td><code>fuzzy_match_threshold</code></td>
                <td style="text-align: center;"><strong>0.75</strong></td>
                <td style="text-align: center;">0.50 &ndash; 0.95</td>
                <td>Minimum string sequence similarity ratio required to consider non-exact skill terms a match.</td>
            </tr>
            <tr>
                <td><code>minimum_match_score</code></td>
                <td style="text-align: center;"><strong>30.0%</strong></td>
                <td style="text-align: center;">0.0 &ndash; 80.0%</td>
                <td>Cutoff threshold below which candidates are excluded from Smart Match job recommendations.</td>
            </tr>
            <tr>
                <td><code>gemini_api_keys</code></td>
                <td style="text-align: center;"><strong>Pool</strong></td>
                <td style="text-align: center;">List of Keys</td>
                <td>Comma-separated pool of Gemini API keys rotated in round-robin fashion for qualitative LLM candidate summaries.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>5.5 Security Audit Logging & Compliance Trails</h2>
    <p>To adhere to corporate governance standards, ARAS records an immutable audit log for every sensitive event in the <code>audit_logs</code> database table:</p>
    <ul>
        <li><strong>Tracked Security Events:</strong> User authentication attempts (success and failure), password resets, role modifications, resume downloads, manual score overrides, and job posting deletions.</li>
        <li><strong>Metadata Recorded:</strong> User ID, Actor Email, Timestamp (UTC), IP Address, User-Agent, and detailed JSON payload describing pre-action and post-action states.</li>
        <li><strong>Audit Search & Export:</strong> Administrators can query audit records by date range, user ID, or event category and export compliance reports for security audits.</li>
    </ul>
    """
