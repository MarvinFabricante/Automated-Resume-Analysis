def get_ch7_html():
    return """
    <div class="page-break"></div>
    <div class="chapter-header">Chapter 7 &bull; Operations & Deployment</div>
    <h1>Deployment, CLI Operations & Environment Setup</h1>
    
    <h2>7.1 Container Architecture & Service Topology</h2>
    <p>ARAS is packaged into isolated, production-ready Docker containers orchestrated via <code>docker-compose.yml</code>. The container topology isolates compute, storage, and worker queues to maximize reliability and horizontal scalability:</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 20%;">Container Service</th>
                <th style="width: 22%;">Base Image</th>
                <th style="width: 18%; text-align: center;">Internal Port</th>
                <th>Role & Operational Function</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>frontend</strong></td>
                <td>Node 20 / Next.js 15</td>
                <td style="text-align: center;"><code>3000</code></td>
                <td>Next.js App Router frontend server rendering UI and serving static assets.</td>
            </tr>
            <tr>
                <td><strong>backend</strong></td>
                <td>Python 3.12 (Slim)</td>
                <td style="text-align: center;"><code>8000</code></td>
                <td>FastAPI application handling HTTP API requests, JWT auth, and WebSocket streams.</td>
            </tr>
            <tr>
                <td><strong>celery_worker</strong></td>
                <td>Python 3.12 (Slim)</td>
                <td style="text-align: center;"><code>N/A</code></td>
                <td>Asynchronous Celery worker executing heavy spaCy parsing and background match scoring.</td>
            </tr>
            <tr>
                <td><strong>redis</strong></td>
                <td>Redis 7.2 (Alpine)</td>
                <td style="text-align: center;"><code>6379</code></td>
                <td>In-memory broker for Celery queues and low-latency cache for matching weights.</td>
            </tr>
            <tr>
                <td><strong>db</strong></td>
                <td>PostgreSQL 16 (Alpine)</td>
                <td style="text-align: center;"><code>5432</code></td>
                <td>Relational database persisting user accounts, job postings, applications, and logs.</td>
            </tr>
            <tr>
                <td><strong>cloudflared</strong></td>
                <td>Cloudflare Quick Tunnel</td>
                <td style="text-align: center;"><code>N/A</code></td>
                <td>Establishes encrypted public HTTPS ingress tunnels with automatic CORS configuration.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>7.2 The Unified Management CLI (<code>./start.sh</code>)</h2>
    <p>ARAS provides an all-in-one automation script (<code>./start.sh</code>) located at the root of the repository. This script handles Docker container orchestration, Cloudflare tunnel generation, environment synchronization, and health verifications.</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 32%;">CLI Command Syntax</th>
                <th>Functional Description & Use Case</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><code>./start.sh</code></td>
                <td>Standard start. Builds images, launches all containers, spins up a live Cloudflare tunnel, and synchronizes CORS settings.</td>
            </tr>
            <tr>
                <td><code>./start.sh -q</code> or <code>--quick</code></td>
                <td>Fast start. Launches containers without checking or rebuilding Docker image layers. Ideal for daily development.</td>
            </tr>
            <tr>
                <td><code>./start.sh -b</code> or <code>--rebuild</code></td>
                <td>Force clean rebuild. Rebuilds all containers with <code>--no-cache</code> before launching services.</td>
            </tr>
            <tr>
                <td><code>./start.sh -r</code> or <code>--restart</code></td>
                <td>Restart stack. Gracefully cycles all containers and regenerates fresh Cloudflare tunnel URLs.</td>
            </tr>
            <tr>
                <td><code>./start.sh -s</code> or <code>--stop</code></td>
                <td>Graceful shutdown. Stops all running application containers and terminates active background tunnels.</td>
            </tr>
            <tr>
                <td><code>./start.sh --status</code></td>
                <td>Health check. Inspects container runtime statuses and verifies live Cloudflare tunnel health.</td>
            </tr>
            <tr>
                <td><code>./start.sh --logs [service]</code></td>
                <td>Log streamer. Streams live aggregated logs or targets a specific service (e.g. <code>./start.sh --logs backend</code>).</td>
            </tr>
            <tr>
                <td><code>./start.sh --seed</code></td>
                <td>Database seeder. Populates default Mariwasa job openings and default HR staff accounts.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>7.3 Environment Configuration (<code>.env</code>) Parameter Glossary</h2>
    <p>The central configuration file (<code>.env</code>) governs system security, database connections, and third-party integrations. All sensitive secrets must be configured prior to production deployment:</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 28%;">Environment Variable</th>
                <th style="width: 37%;">Example / Configuration Format</th>
                <th>Operational Description</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><code>DATABASE_URL</code></td>
                <td><code>postgresql+asyncpg://user:pass@db:5432/ar_db</code></td>
                <td>Asynchronous PostgreSQL connection URI utilized by SQLAlchemy and <code>asyncpg</code>.</td>
            </tr>
            <tr>
                <td><code>REDIS_URL</code></td>
                <td><code>redis://redis:6379/0</code></td>
                <td>Redis broker connection string for Celery background tasks and system cache.</td>
            </tr>
            <tr>
                <td><code>SECRET_KEY</code></td>
                <td><code>32+ character cryptographic secret string</code></td>
                <td>Cryptographic secret used for signing and verifying JWT authentication tokens.</td>
            </tr>
            <tr>
                <td><code>FRONTEND_URL</code></td>
                <td><code>http://localhost:3000,https://*.trycloudflare.com</code></td>
                <td>Comma-separated list of authorized origins permitted through FastAPI CORS middleware.</td>
            </tr>
            <tr>
                <td><code>GEMINI_API_KEYS</code></td>
                <td><code>key_1,key_2,key_3</code></td>
                <td>Comma-separated pool of Google Gemini API keys rotated in round-robin fashion.</td>
            </tr>
            <tr>
                <td><code>GOOGLE_CLIENT_ID</code></td>
                <td><code>&lt;oauth-client-id&gt;.apps.googleusercontent.com</code></td>
                <td>Google OAuth 2.0 client ID for Google Calendar two-way interview synchronization.</td>
            </tr>
            <tr>
                <td><code>GOOGLE_CLIENT_SECRET</code></td>
                <td><code>&lt;oauth-client-secret&gt;</code></td>
                <td>Google OAuth 2.0 client secret for calendar token exchange.</td>
            </tr>
            <tr>
                <td><code>SUPABASE_URL</code></td>
                <td><code>https://&lt;project&gt;.supabase.co</code></td>
                <td>Supabase Storage API URL for persisting resumes, scans, and avatars.</td>
            </tr>
            <tr>
                <td><code>SUPABASE_SERVICE_ROLE_KEY</code></td>
                <td><code>eyJhbGciOi... (Service Role JWT)</code></td>
                <td>Privileged Supabase service role key for automated bucket uploads.</td>
            </tr>
            <tr>
                <td><code>TWILIO_ACCOUNT_SID</code></td>
                <td><code>ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</code></td>
                <td>Twilio account SID for automated voice telephone dispatch.</td>
            </tr>
            <tr>
                <td><code>TWILIO_AUTH_TOKEN</code></td>
                <td><code>&lt;twilio-auth-token&gt;</code></td>
                <td>Twilio authentication token for API authorization.</td>
            </tr>
            <tr>
                <td><code>TWILIO_PHONE_NUMBER</code></td>
                <td><code>+1XXXXXXXXXX</code></td>
                <td>Registered Twilio phone number used as caller ID for outbound interview calls.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>7.4 Database Reset & Migration Protocol</h2>
    <p>When deploying to a clean staging environment or wiping test data, administrators execute <code>backend/reset-db.sh</code>:</p>
    <ol>
        <li>Drops and recreates the PostgreSQL <code>public</code> schema, purging all obsolete tables.</li>
        <li>Wipes temporary storage in <code>uploads/resumes/</code> and <code>uploads/resume_images/</code>.</li>
        <li>Executes <code>init-db.py</code> to initialize all SQLAlchemy ORM tables with foreign key constraints.</li>
        <li>Executes <code>./start.sh --seed</code> to insert Mariwasa job requisitions (Production Engineer, QA Supervisor, Maintenance Tech) and default HR credentials.</li>
    </ol>
    """
