def get_ch2_html():
    return """
    <div class="page-break"></div>
    <div class="chapter-header">Chapter 2 &bull; Access & Security</div>
    <h1>System Access, Authentication & Role-Based Permissions</h1>
    
    <h2>2.1 Access Endpoints & Network Environments</h2>
    <p>The Automated Resume Analysis System can be accessed across corporate local area networks (LAN) or securely over public HTTPS via automated Cloudflare tunnels. All HTTP traffic is enforced over TLS 1.3 encryption.</p>

    <div class="callout callout-info avoid-break" style="margin-top: 12px; margin-bottom: 16px;">
        <div class="callout-title" style="font-size: 10.5pt; font-weight: 700; color: #1d4ed8; margin-bottom: 6px;">
            🌐 Live Cloudflare Tunnel Deployment & Access Credentials Reference
        </div>
        <p style="margin-bottom: 8px;"><strong>Public Live Application URL:</strong> <a href="https://explanation-citizens-cooperative-evidence.trycloudflare.com/" target="_blank" style="color: #2563eb; font-weight: 600; text-decoration: underline;">https://explanation-citizens-cooperative-evidence.trycloudflare.com/</a></p>
        <table class="data-table" style="margin-top: 6px; margin-bottom: 4px; font-size: 8.5pt;">
            <thead>
                <tr>
                    <th style="width: 22%;">Role</th>
                    <th style="width: 38%;">Authentication Method & Email</th>
                    <th style="width: 20%;">Password / Auth</th>
                    <th style="width: 20%;">Default Landing Route</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><span class="badge badge-purple">ADMINISTRATOR</span></td>
                    <td><strong>Direct Portal Login</strong><br><code>jp@gmail.com</code></td>
                    <td><code>password</code></td>
                    <td><code>/admin/dashboard</code></td>
                </tr>
                <tr>
                    <td><span class="badge badge-blue">HR OFFICER</span></td>
                    <td><strong>Google OAuth Sign-In</strong><br><code>hr.mariwasa@gmail.com</code></td>
                    <td><code>Password123.</code></td>
                    <td><code>/hr/dashboard</code></td>
                </tr>
                <tr>
                    <td><span class="badge badge-green">CANDIDATE</span></td>
                    <td><strong>Google One-Click Registration</strong><br><em>(or standard email signup)</em></td>
                    <td><em>Google Account Auth</em></td>
                    <td><code>/candidate/dashboard</code></td>
                </tr>
            </tbody>
        </table>
    </div>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 25%;">Portal / Target Endpoint</th>
                <th style="width: 30%;">Local Docker Environment</th>
                <th style="width: 45%;">Production / Cloudflare Tunnel Route</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Public Landing & Careers</strong></td>
                <td><code>http://localhost:3000/</code></td>
                <td><code>https://explanation-citizens-cooperative-evidence.trycloudflare.com/</code></td>
            </tr>
            <tr>
                <td><strong>Candidate Dashboard</strong></td>
                <td><code>http://localhost:3000/candidate/dashboard</code></td>
                <td><code>https://explanation-citizens-cooperative-evidence.trycloudflare.com/candidate/dashboard</code></td>
            </tr>
            <tr>
                <td><strong>HR Screening Portal</strong></td>
                <td><code>http://localhost:3000/hr/dashboard</code></td>
                <td><code>https://explanation-citizens-cooperative-evidence.trycloudflare.com/hr/dashboard</code></td>
            </tr>
            <tr>
                <td><strong>Admin Control Center</strong></td>
                <td><code>http://localhost:3000/admin/dashboard</code></td>
                <td><code>https://explanation-citizens-cooperative-evidence.trycloudflare.com/admin/dashboard</code></td>
            </tr>
            <tr>
                <td><strong>FastAPI Interactive Docs</strong></td>
                <td><code>http://localhost:8000/docs</code></td>
                <td><code>https://explanation-citizens-cooperative-evidence.trycloudflare.com/docs</code></td>
            </tr>
        </tbody>
    </table>
    
    <h2>2.2 Role-Based Access Control (RBAC) Matrix</h2>
    <p>Access to resources, actions, and data views is strictly regulated based on authenticated user roles. The system enforces zero-trust boundaries at both the frontend Next.js routing layer (via middleware and client route guards) and backend FastAPI dependency guards (<code>Depends(get_current_user)</code> and role assertions).</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 32%;">System Capability / Function</th>
                <th style="width: 17%; text-align: center;">Public / Guest</th>
                <th style="width: 17%; text-align: center;">Candidate</th>
                <th style="width: 17%; text-align: center;">HR Officer</th>
                <th style="width: 17%; text-align: center;">Administrator</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Browse Job Openings & Job Specs</td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
            </tr>
            <tr>
                <td>Smart Match Resume Upload & Analysis</td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
                <td style="text-align: center;"><span class="badge badge-slate">N/A</span></td>
                <td style="text-align: center;"><span class="badge badge-slate">N/A</span></td>
            </tr>
            <tr>
                <td>Submit Application & Preview-Verify</td>
                <td style="text-align: center;"><span class="badge badge-amber">WITH ACCT</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
            </tr>
            <tr>
                <td>Track Application Lifecycle Stages</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-green">OWN ONLY</span></td>
                <td style="text-align: center;"><span class="badge badge-green">ALL</span></td>
                <td style="text-align: center;"><span class="badge badge-green">ALL</span></td>
            </tr>
            <tr>
                <td>Candidate-HR Live Messaging</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-green">OWN THREAD</span></td>
                <td style="text-align: center;"><span class="badge badge-green">ALL THREADS</span></td>
                <td style="text-align: center;"><span class="badge badge-green">ALL THREADS</span></td>
            </tr>
            <tr>
                <td>View Candidate Scores & Missing Skills</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-amber">SCORE ONLY</span></td>
                <td style="text-align: center;"><span class="badge badge-green">FULL RADAR</span></td>
                <td style="text-align: center;"><span class="badge badge-green">FULL RADAR</span></td>
            </tr>
            <tr>
                <td>Side-by-Side Candidate Comparison</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
            </tr>
            <tr>
                <td>Schedule Interviews & Google Sync</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-slate">RSVP ONLY</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
            </tr>
            <tr>
                <td>Dispatch Automated AI Voice Calls</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-slate">RECEIVE</span></td>
                <td style="text-align: center;"><span class="badge badge-green">TRIGGER</span></td>
                <td style="text-align: center;"><span class="badge badge-green">TRIGGER</span></td>
            </tr>
            <tr>
                <td>Physical Hard-Copy Resume Filing</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
            </tr>
            <tr>
                <td>Create, Edit, Archive Job Requisitions</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
                <td style="text-align: center;"><span class="badge badge-green">FULL CRUD</span></td>
            </tr>
            <tr>
                <td>User Account Provisioning & Roles</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
            </tr>
            <tr>
                <td>Configure AI Weights & Thresholds</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
            </tr>
            <tr>
                <td>View Security Audit Trail & Event Logs</td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-red">NO</span></td>
                <td style="text-align: center;"><span class="badge badge-green">YES</span></td>
            </tr>
        </tbody>
    </table>
    
    <h2>2.3 Registration & Authentication Procedures</h2>
    
    <div class="step-workflow avoid-break">
        <div class="step-item">
            <div class="step-badge">1</div>
            <div class="step-content">
                <div class="step-title">Candidate Registration (Google SSO & Standard)</div>
                <p>New applicants navigate to <code>/register</code>. Candidates can register instantly with a single click using <strong>"Continue with Google"</strong>, automatically linking their verified Google email address. Alternatively, candidates can manually submit their Full Name, Email Address, Contact Number, and create a secure password. Upon successful registration, the account is provisioned with the <code>CANDIDATE</code> role.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">2</div>
            <div class="step-content">
                <div class="step-title">HR & Admin Staff Account Provisioning</div>
                <p>HR Recruiters and System Administrators cannot self-register as staff. Privileged accounts are pre-provisioned via the <strong>Admin Control Center</strong> (<code>/admin/users</code>) or initialized via database seeds (e.g. Admin: <code>jp@gmail.com</code>, HR Google account: <code>hr.mariwasa@gmail.com</code>). Authorized HR staff log in seamlessly using <strong>Google SSO</strong>, while Administrators authenticate using direct secure credentials.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">3</div>
            <div class="step-content">
                <div class="step-title">Sign-In, OAuth Verification & JWT Token Issuance</div>
                <p>Users sign in at <code>/login</code> via Google SSO or standard email/password. For email logins, backend hashes are verified using <code>bcrypt</code>; for Google logins, the backend validates the Google OAuth2 callback. Upon successful authentication, the server generates a signed JSON Web Token (JWT) encapsulating user ID, email, and role. The token is stored in client state and dispatched in the <code>Authorization: Bearer &lt;token&gt;</code> header on all subsequent API requests.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">4</div>
            <div class="step-content">
                <div class="step-title">Role-Based Automatic Redirection</div>
                <p>Upon successful authentication, the system automatically redirects users to their appropriate home dashboard based on role claims:</p>
                <ul>
                    <li><code>CANDIDATE</code> &rarr; Directed to <code>/candidate/dashboard</code></li>
                    <li><code>HR</code> &rarr; Directed to <code>/hr/dashboard</code></li>
                    <li><code>ADMIN</code> &rarr; Directed to <code>/admin/dashboard</code></li>
                </ul>
            </div>
        </div>
    </div>
    
    <h2>2.4 Password Recovery & Self-Service Reset</h2>
    <p>If a candidate or staff member forgets their password, the self-service recovery protocol ensures account access can be restored safely:</p>
    <ol>
        <li>Navigate to <code>/forgot-password</code>.</li>
        <li>Enter the registered email address and submit the request.</li>
        <li>The backend generates a cryptographically secure, time-limited token stored in the <code>password_resets</code> database table (valid for 60 minutes).</li>
        <li>The user receives a secure link pointing to <code>/reset-password?token=&lt;token&gt;</code>.</li>
        <li>The user supplies a new compliant password, which is hashed with fresh salt and immediately replaces the obsolete credential.</li>
    </ol>
    """
