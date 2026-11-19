def get_css():
    return """
    @page {
        size: A4;
        margin: 16mm 13mm 16mm 13mm;
    }
    
    *, *:before, *:after {
        box-sizing: border-box;
    }
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #1e293b;
        background-color: #ffffff;
        font-size: 9pt;
        line-height: 1.5;
        margin: 0;
        padding: 0;
    }
    
    /* Page Break Helpers */
    .page-break {
        page-break-before: always;
    }
    .avoid-break {
        page-break-inside: avoid;
    }
    
    /* Cover Page */
    .cover-container {
        height: 100vh;
        max-height: 255mm;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 8mm 4mm;
        page-break-after: always;
    }
    .cover-header {
        border-bottom: 3px solid #1e40af;
        padding-bottom: 6mm;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .cover-logo img {
        height: 55px;
        object-fit: contain;
    }
    .cover-org-title {
        text-align: right;
    }
    .cover-org-name {
        font-size: 14pt;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
    }
    .cover-org-sub {
        font-size: 8pt;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .cover-body {
        margin: auto 0;
        padding: 8mm 0;
    }
    .cover-tag {
        display: inline-block;
        background: #eff6ff;
        color: #1d4ed8;
        font-size: 8pt;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 9999px;
        border: 1px solid #bfdbfe;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 5mm;
    }
    .cover-title {
        font-size: 26pt;
        font-weight: 900;
        color: #0f172a;
        line-height: 1.15;
        letter-spacing: -0.03em;
        margin: 0 0 3.5mm 0;
    }
    .cover-subtitle {
        font-size: 12pt;
        font-weight: 500;
        color: #475569;
        line-height: 1.4;
        margin: 0 0 6mm 0;
    }
    .cover-divider {
        width: 55px;
        height: 3.5px;
        background: #2563eb;
        border-radius: 2px;
        margin-bottom: 6mm;
    }
    .cover-meta-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 3.5mm 6mm;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 4mm 5mm;
        max-width: 155mm;
    }
    .cover-meta-item {
        font-size: 8.5pt;
    }
    .cover-meta-label {
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 7pt;
        letter-spacing: 0.05em;
    }
    .cover-meta-value {
        color: #0f172a;
        font-weight: 700;
        font-size: 9pt;
    }
    .cover-footer {
        border-top: 1px solid #e2e8f0;
        padding-top: 4mm;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 7.5pt;
        color: #64748b;
    }
    
    /* Typography */
    h1 {
        font-size: 16pt;
        font-weight: 800;
        color: #0f172a;
        margin: 5mm 0 2.5mm 0;
        padding-bottom: 1.5mm;
        border-bottom: 1.5px solid #e2e8f0;
        letter-spacing: -0.02em;
    }
    .chapter-header {
        font-size: 8pt;
        font-weight: 700;
        color: #2563eb;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 1mm;
    }
    h2 {
        font-size: 11.5pt;
        font-weight: 700;
        color: #1e293b;
        margin: 4mm 0 2mm 0;
        letter-spacing: -0.01em;
    }
    h3 {
        font-size: 9.5pt;
        font-weight: 600;
        color: #334155;
        margin: 3mm 0 1.5mm 0;
    }
    p {
        margin: 0 0 2.5mm 0;
    }
    ul, ol {
        margin: 0 0 2.5mm 0;
        padding-left: 4.5mm;
    }
    li {
        margin-bottom: 1mm;
    }
    
    /* Callout Boxes */
    .callout {
        padding: 3mm 4mm;
        border-radius: 5px;
        margin: 2.5mm 0;
        font-size: 8.5pt;
        border-left: 3.5px solid #3b82f6;
        background-color: #eff6ff;
    }
    .callout-title {
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 5px;
        margin-bottom: 1mm;
        font-size: 8.5pt;
    }
    .callout-info {
        border-left-color: #2563eb;
        background-color: #eff6ff;
        color: #1e3a8a;
    }
    .callout-info .callout-title { color: #1d4ed8; }
    .callout-tip {
        border-left-color: #059669;
        background-color: #ecfdf5;
        color: #064e3b;
    }
    .callout-tip .callout-title { color: #047857; }
    .callout-warning {
        border-left-color: #d97706;
        background-color: #fffbeb;
        color: #78350f;
    }
    .callout-warning .callout-title { color: #b45309; }
    .callout-danger {
        border-left-color: #dc2626;
        background-color: #fef2f2;
        color: #7f1d1d;
    }
    .callout-danger .callout-title { color: #b91c1c; }
    
    /* Tables */
    table.data-table {
        width: 100%;
        border-collapse: collapse;
        margin: 2.5mm 0 3.5mm 0;
        font-size: 8pt;
    }
    table.data-table th {
        background-color: #0f172a;
        color: #ffffff;
        text-align: left;
        padding: 4.5px 8px;
        font-weight: 600;
        border: 1px solid #0f172a;
    }
    table.data-table td {
        padding: 4px 8px;
        border: 1px solid #e2e8f0;
        vertical-align: top;
    }
    table.data-table tr:nth-child(even) td {
        background-color: #f8fafc;
    }
    
    /* Cards & Grids */
    .grid-2 {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 2.5mm;
        margin: 2.5mm 0;
    }
    .grid-3 {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 2.5mm;
        margin: 2.5mm 0;
    }
    .grid-4 {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 2mm;
        margin: 2.5mm 0;
    }
    .feature-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 5px;
        padding: 2.5mm 3.5mm;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .feature-card-header {
        font-weight: 700;
        font-size: 9pt;
        color: #0f172a;
        margin-bottom: 1mm;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 1px 6px;
        border-radius: 3px;
        font-size: 7pt;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .badge-blue { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
    .badge-green { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
    .badge-amber { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
    .badge-red { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
    .badge-purple { background: #f3e8ff; color: #6b21a8; border: 1px solid #e9d5ff; }
    .badge-slate { background: #f1f5f9; color: #334155; border: 1px solid #e2e8f0; }
    
    /* Step Workflow */
    .step-workflow {
        margin: 2.5mm 0;
    }
    .step-item {
        display: flex;
        gap: 3mm;
        margin-bottom: 2mm;
    }
    .step-badge {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: #2563eb;
        color: #ffffff;
        font-weight: 700;
        font-size: 8pt;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        margin-top: 1px;
    }
    .step-content {
        flex: 1;
    }
    .step-title {
        font-weight: 700;
        color: #0f172a;
        font-size: 9pt;
        margin-bottom: 0.5mm;
    }
    
    /* Code and Pre */
    code {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 7.5pt;
        background-color: #f1f5f9;
        color: #0f172a;
        padding: 1px 4px;
        border-radius: 3px;
        border: 1px solid #e2e8f0;
    }
    pre {
        background-color: #0f172a;
        color: #f8fafc;
        padding: 3mm 4mm;
        border-radius: 5px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 7.5pt;
        line-height: 1.4;
        overflow-x: auto;
        margin: 2.5mm 0;
        border: 1px solid #1e293b;
    }
    pre code {
        background: none;
        color: inherit;
        padding: 0;
        border: none;
        font-size: inherit;
    }
    
    /* Formula Box */
    .formula-box {
        background: #f8fafc;
        border: 1.5px solid #cbd5e1;
        border-radius: 5px;
        padding: 3mm 4mm;
        margin: 2.5mm 0;
        text-align: center;
    }
    .formula-title {
        font-weight: 700;
        color: #475569;
        font-size: 7.5pt;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 1.5mm;
    }
    .formula-math {
        font-family: "Cambria Math", "Times New Roman", serif;
        font-size: 10.5pt;
        font-weight: 600;
        color: #0f172a;
    }
    .formula-desc {
        font-size: 7.5pt;
        color: #64748b;
        margin-top: 1.5mm;
        text-align: left;
    }
    
    /* Image container */
    .img-box {
        text-align: center;
        margin: 3mm 0;
    }
    .img-box img {
        max-width: 95%;
        height: auto;
        border-radius: 5px;
        border: 1px solid #cbd5e1;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .img-caption {
        font-size: 7.5pt;
        color: #64748b;
        margin-top: 1mm;
        font-style: italic;
    }
    """
