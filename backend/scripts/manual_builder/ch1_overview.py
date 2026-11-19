def get_ch1_html(erd_b64=""):
    erd_html = ""
    if erd_b64:
        erd_html = f"""
        <div class="img-box avoid-break">
            <img src="data:image/png;base64,{erd_b64}" alt="Database Entity Relationship Diagram" style="max-height: 140mm; object-fit: contain;">
            <div class="img-caption">Figure 1.2: Relational Database Schema & Entity Relationships (PostgreSQL 16)</div>
        </div>
        """
    
    return f"""
    <div class="page-break"></div>
    <div class="chapter-header">Chapter 1 &bull; System Architecture</div>
    <h1>Executive Summary & System Architecture</h1>
    
    <h2>1.1 Enterprise Background & Operational Objectives</h2>
    <p><strong>Mariwasa Siam Ceramics Inc.</strong>, a premier pioneer in ceramic tile manufacturing operating under the SCG Group in Sto. Tomas, Batangas, processes thousands of job applications annually across plant manufacturing, quality assurance, engineering maintenance, supply chain, and administrative departments. Prior to the introduction of the <strong>Automated Resume Analysis System (ARAS)</strong>, the human resources team experienced severe screening bottlenecks, subjective qualification discrepancies, high candidate interview no-show rates, and difficulties tracking hard-copy resumes submitted directly at plant security gates.</p>
    
    <div class="grid-2 avoid-break">
        <div class="feature-card">
            <div class="feature-card-header" style="color: #b91c1c;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                Previous Operational Bottlenecks
            </div>
            <ul style="margin: 0; padding-left: 4.5mm; font-size: 8.5pt;">
                <li><strong>Screening Latency:</strong> Manual review of 1,000+ resumes required 3-4 weeks per hiring cycle.</li>
                <li><strong>Subjective Evaluations:</strong> Inconsistent scoring across different recruiters and departments.</li>
                <li><strong>Hard-Copy Filing Chaos:</strong> Physical walk-in resumes misplaced in physical storage drawers.</li>
                <li><strong>Candidate Interview Drop-Off:</strong> Low confirmation rates via standard email notifications.</li>
            </ul>
        </div>
        
        <div class="feature-card">
            <div class="feature-card-header" style="color: #047857;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                ARAS System Transformations
            </div>
            <ul style="margin: 0; padding-left: 4.5mm; font-size: 8.5pt;">
                <li><strong>Sub-Second Parsing:</strong> Deterministic ingestion and entity extraction in under 800ms.</li>
                <li><strong>Mathematical Multi-Factor Match:</strong> Algorithmic scoring (Skills 50%, Experience 30%, Education 20%).</li>
                <li><strong>Physical Storage Vault:</strong> Scanned uploads linked to exact physical drawers (e.g. Cabinet B, Shelf 3).</li>
                <li><strong>AI Voice Caller:</strong> Automated bilingual voice confirmation (Tagalog/English) reducing no-shows.</li>
            </ul>
        </div>
    </div>
    
    <h2>1.2 The Three Portal Ecosystem</h2>
    <p>The system is architected around three dedicated, role-specific web applications sharing a unified, secure backend:</p>
    
    <div class="grid-3 avoid-break">
        <div class="feature-card">
            <div class="feature-card-header" style="color: #1d4ed8;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                1. Candidate Portal
            </div>
            <p style="font-size: 8.5pt; color: #475569;">Empowers applicants to search Mariwasa careers, leverage <strong>Smart Match</strong> (upload without selecting a job to get instant job recommendations), verify AI-extracted credentials via the <strong>Preview & Verify</strong> interface, track application stages in real-time, and message HR directly.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-card-header" style="color: #047857;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                2. HR Screening Portal
            </div>
            <p style="font-size: 8.5pt; color: #475569;">Provides recruitment officers with high-fidelity candidate rankings, match score inspection (matched vs. missing competencies), side-by-side comparison, Google Calendar interview booking, AI Voice Caller triggers, and physical hard-copy filing management.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-card-header" style="color: #7c3aed;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
                3. Admin Control Center
            </div>
            <p style="font-size: 8.5pt; color: #475569;">Gives IT and HR administrators centralized oversight over accounts and role permissions, dynamic runtime tuning of scoring weights and threshold cutoffs, rate limits, audit logging of all sensitive events, and full job requisition CRUD control.</p>
        </div>
    </div>
    
    <h2>1.3 High-Level Technical Architecture</h2>
    <p>ARAS employs an asynchronous, event-driven micro-service architecture optimized for high concurrency, low latency, and deterministic reliability:</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 22%;">System Layer</th>
                <th style="width: 33%;">Core Technology Stack</th>
                <th>Architectural Responsibilities</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Presentation Layer</strong></td>
                <td>Next.js 15 (App Router), TypeScript, Tailwind CSS v4, Redux Toolkit</td>
                <td>Delivers responsive, server-side rendered and interactive client interfaces for candidates, recruiters, and admins with sub-100ms client route transitions.</td>
            </tr>
            <tr>
                <td><strong>API Gateway & Services</strong></td>
                <td>FastAPI (Python 3.12), Pydantic v2, SQLAlchemy 2.0 (Async)</td>
                <td>Exposes non-blocking asynchronous REST endpoints, manages JWT bearer security, orchestrates business rules, and bridges WebSocket streams.</td>
            </tr>
            <tr>
                <td><strong>Task Worker Engine</strong></td>
                <td>Celery 5.4, Redis 7 (Alpine), spaCy 3.7 PhraseMatcher</td>
                <td>Executes asynchronous heavy NLP parsing, background candidate match recalculations, and scheduled voice call retries without blocking HTTP threads.</td>
            </tr>
            <tr>
                <td><strong>Data Persistence</strong></td>
                <td>PostgreSQL 16 (Alpine) with <code>asyncpg</code> connection pool</td>
                <td>Stores normalized entity models for users, candidate profiles, job descriptions, applications, interview logs, and immutable audit trails.</td>
            </tr>
            <tr>
                <td><strong>Object Storage</strong></td>
                <td>Supabase Storage (S3-compatible)</td>
                <td>Secure cloud storage for candidate resume PDFs, profile avatars, and scanned hard-copy walk-in physical resumes.</td>
            </tr>
            <tr>
                <td><strong>AI Voice & Gateway</strong></td>
                <td>Twilio Voice API, Google Gemini 1.5/2.0 Flash, Cloudflare Tunnel</td>
                <td>Bridges real-time bi-directional audio streams for automated candidate phone screening and provides secure external HTTPS ingress with automatic CORS.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>1.4 Relational Database Architecture (ERD)</h2>
    <p>The persistence layer is modeled in PostgreSQL 16 utilizing strict foreign-key referential integrity, automated cascade policies, and asynchronous connection pooling via <code>asyncpg</code>. The schema is organized into distinct logical sub-domains: User Authentication & RBAC, Candidate Data & Work History, Job Postings & Requisition Criteria, Applications & Scoring Results, Interview Scheduling & Call Logs, and Physical Resume Vault Records.</p>
    
    {erd_html}
    """
