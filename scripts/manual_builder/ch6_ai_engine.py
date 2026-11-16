def get_ch6_html():
    return """
    <div class="page-break"></div>
    <div class="chapter-header">Chapter 6 &bull; AI Intelligence Engine</div>
    <h1>AI Intelligence Engine & Scoring Specifications</h1>
    
    <h2>6.1 Deterministic Document Parsing Pipeline</h2>
    <p>A core architectural design tenet of ARAS is the deliberate separation between <strong>deterministic document parsing</strong> and <strong>qualitative generative analysis</strong>. By executing the primary resume ingestion deterministically, the system achieves sub-800ms parsing speeds, zero recurring LLM token expenses, and absolute mathematical consistency across all evaluations.</p>
    
    <div class="step-workflow avoid-break">
        <div class="step-item">
            <div class="step-badge">1</div>
            <div class="step-content">
                <div class="step-title">Document Preprocessing (PyMuPDF & python-docx)</div>
                <p>The parser accepts PDF, DOCX, and TXT files. PyMuPDF extracts raw text, structural bounding boxes, and typography weights, identifying section headings (e.g. <em>Education</em>, <em>Work Experience</em>, <em>Skills</em>, <em>Certifications</em>) based on font sizing, capitalization, and vertical spacing cues.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">2</div>
            <div class="step-content">
                <div class="step-title">Named Entity Recognition (NER) & Contact Extraction</div>
                <p>Regular expression heuristics and spaCy statistical models extract candidate contact particulars: candidate full name, phone number (normalized to Philippine E.164 format: <code>+639XXXXXXXXX</code>), email address, and residential municipality.</p>
            </div>
        </div>
        <div class="step-item">
            <div class="step-badge">3</div>
            <div class="step-content">
                <div class="step-title">Contextual Experience & Education Timeline Segmentation</div>
                <p>Date parser algorithms extract start and end dates (e.g. <em>"June 2021 &ndash; Present"</em>), calculating total months of cumulative professional experience while discounting overlapping date ranges.</p>
            </div>
        </div>
    </div>
    
    <h2>6.2 spaCy PhraseMatcher & Technical Taxonomy</h2>
    <p>To eliminate keyword misses caused by variations in vocabulary, ARAS incorporates an enterprise taxonomy containing over <strong>2,000+ domain terms</strong> specifically tuned for ceramic tile manufacturing, chemical engineering, industrial automation, and corporate management:</p>
    
    <div class="grid-2 avoid-break">
        <div class="feature-card">
            <div class="feature-card-header" style="color: #2563eb;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/></svg>
                Exact & Lemmatized Matching
            </div>
            <p style="font-size: 8.5pt; color: #475569;">spaCy tokenizes and lemmatizes the document text. The PhraseMatcher indexes multi-token terminology (e.g. <em>"Root Cause Analysis"</em>, <em>"Preventive Maintenance"</em>, <em>"Kiln Operation"</em>) with exact token boundary verification, preventing false-positive substring matches.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-card-header" style="color: #059669;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 12h8"/><path d="M12 8v8"/></svg>
                Fuzzy Sequence Matching (Threshold 0.75)
            </div>
            <p style="font-size: 8.5pt; color: #475569;">When candidates write typos or typographical variations (e.g. <em>"Lean 6-Sigma"</em> vs. <em>"Six Sigma"</em>), the difflib <code>SequenceMatcher</code> evaluates similarity against the taxonomy. If similarity exceeds <code>fuzzy_match_threshold</code> (0.75), credit is awarded.</p>
        </div>
    </div>
    
    <h2>6.3 Multi-Factor Match Scoring Formulation</h2>
    <p>Candidate alignment against a job requisition is computed through a standardized, multi-dimensional scoring model. The overall score represents the weighted summation of individual competency sub-scores:</p>
    
    <div class="formula-box avoid-break">
        <div class="formula-title">ARAS Algorithmic Match Formula</div>
        <div class="formula-math">
            Match Score = (w<sub>skills</sub> &times; S<sub>skills</sub>) + (w<sub>exp</sub> &times; S<sub>exp</sub>) + (w<sub>edu</sub> &times; S<sub>edu</sub>) + (w<sub>cert</sub> &times; S<sub>cert</sub>) + (w<sub>loc</sub> &times; S<sub>loc</sub>)
        </div>
        <div class="formula-desc">
            Where default weights are: <strong>w<sub>skills</sub> = 0.45 &ndash; 0.50</strong>, <strong>w<sub>exp</sub> = 0.25 &ndash; 0.30</strong>, <strong>w<sub>edu</sub> = 0.15 &ndash; 0.20</strong>, <strong>w<sub>cert</sub> = 0.10</strong>, and <strong>w<sub>loc</sub> = 0.05</strong>. The sum of all weights equals 1.00 (100%).
        </div>
    </div>
    
    <h3>1. Skills Alignment Sub-Score (S<sub>skills</sub>)</h3>
    <p>Measures direct overlap between the candidate's verified skills and the mandatory competencies specified in the job posting:</p>
    <pre><code>S_skills = min(100.0, (len(matched_required_skills) / len(total_required_skills)) * 100.0 + bonus_preferred)</code></pre>
    
    <h3>2. Experience Relevance Sub-Score (S<sub>exp</sub>)</h3>
    <p>Evaluates cumulative verifiable professional experience relative to the minimum years demanded by the requisition:</p>
    <pre><code>if candidate_years >= required_years:
    S_exp = 100.0
else:
    S_exp = (candidate_years / required_years) * 100.0</code></pre>
    
    <h3>3. Education Hierarchy Sub-Score (S<sub>edu</sub>)</h3>
    <p>Academic credentials are mapped to a standardized degree hierarchy scale from 1 (Senior High) to 6 (Doctorate / PhD):</p>
    
    <table class="data-table avoid-break">
        <thead>
            <tr>
                <th style="width: 15%; text-align: center;">Hierarchy Level</th>
                <th style="width: 35%;">Academic Qualification Classification</th>
                <th style="width: 25%; text-align: center;">Base Score Assigned</th>
                <th>Relevance to Mariwasa Positions</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="text-align: center;"><strong>Level 6</strong></td>
                <td>Doctorate / Ph.D. / Post-Graduate</td>
                <td style="text-align: center;"><span class="badge badge-purple">100 Pts</span></td>
                <td>Advanced research, materials science, executive roles.</td>
            </tr>
            <tr>
                <td style="text-align: center;"><strong>Level 5</strong></td>
                <td>Master's Degree (MBA, M.S. Engineering)</td>
                <td style="text-align: center;"><span class="badge badge-purple">95 Pts</span></td>
                <td>Senior plant management, specialized engineering.</td>
            </tr>
            <tr>
                <td style="text-align: center;"><strong>Level 4</strong></td>
                <td>Bachelor's Degree (B.S. Chem/Mech/IE, etc.)</td>
                <td style="text-align: center;"><span class="badge badge-blue">80 Pts</span></td>
                <td>Standard requirement for production engineers, QA supervisors.</td>
            </tr>
            <tr>
                <td style="text-align: center;"><strong>Level 3</strong></td>
                <td>Associate's Degree / 3-Year Technical Course</td>
                <td style="text-align: center;"><span class="badge badge-slate">60 Pts</span></td>
                <td>Laboratory technicians, junior line supervisors.</td>
            </tr>
            <tr>
                <td style="text-align: center;"><strong>Level 2</strong></td>
                <td>Diploma / Vocational Course / TESDA NCII</td>
                <td style="text-align: center;"><span class="badge badge-amber">40 Pts</span></td>
                <td>Standard requirement for maintenance technicians, operators.</td>
            </tr>
            <tr>
                <td style="text-align: center;"><strong>Level 1</strong></td>
                <td>Senior High School (SHS) Graduate</td>
                <td style="text-align: center;"><span class="badge badge-slate">20 Pts</span></td>
                <td>Entry-level plant packaging, warehousing personnel.</td>
            </tr>
        </tbody>
    </table>
    
    <h2>6.4 Gemini LLM Integration & Hybrid Fallback Architecture</h2>
    <p>For shortlisted candidates, ARAS invokes Google Gemini 1.5/2.0 Flash to synthesize a qualitative narrative summary and identify subtle contextual nuances. To ensure enterprise-grade resilience against third-party API rate limits, the system operates a <strong>Hybrid Fallback Architecture</strong>:</p>
    <ul>
        <li><strong>Rotational API Key Pool:</strong> The system maintains multiple Gemini API keys in <code>GEMINI_API_KEYS</code>, cycling through them in a round-robin rotation to avoid per-minute quota ceilings.</li>
        <li><strong>Deterministic Fallback:</strong> If all external API keys fail or internet access is severed, the backend automatically falls back to 100% deterministic rule-based scoring without throwing exceptions or delaying user workflows.</li>
    </ul>
    
    <h2>6.5 Twilio + Gemini Real-Time Voice Streaming Architecture</h2>
    <p>The AI Voice Caller establishes a bi-directional audio bridge between Twilio's telephony infrastructure and Gemini's Real-Time speech models via WebSockets (<code>/ai-caller/media-stream</code>). Audio is sampled at 8kHz mu-law telephony standards, converted to PCM, and processed in real time to interpret candidate verbal commitments in Tagalog and English with sub-400ms latency.</p>
    """
