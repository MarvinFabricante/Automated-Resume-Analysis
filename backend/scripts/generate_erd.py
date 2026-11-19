import subprocess
import os
import shutil

# 1. Fetch Columns
cmd_cols = '''docker exec resume_analysis_db psql -U postgres -d automated_resume_db -t -A -F'|' -c "
SELECT c.table_name, c.column_name, c.data_type, c.is_nullable
FROM information_schema.columns c
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position;
"'''
raw_cols = subprocess.check_output(cmd_cols, shell=True, text=True)

# 2. Fetch PKs
cmd_pks = '''docker exec resume_analysis_db psql -U postgres -d automated_resume_db -t -A -F'|' -c "
SELECT tc.table_name, kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
WHERE tc.table_schema = 'public' AND tc.constraint_type = 'PRIMARY KEY';
"'''
raw_pks = subprocess.check_output(cmd_pks, shell=True, text=True)

# 3. Fetch FKs
cmd_fks = '''docker exec resume_analysis_db psql -U postgres -d automated_resume_db -t -A -F'|' -c "
SELECT 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
WHERE tc.table_schema = 'public' AND tc.constraint_type = 'FOREIGN KEY';
"'''
raw_fks = subprocess.check_output(cmd_fks, shell=True, text=True)

pks_set = set()
for l in raw_pks.strip().split('\n'):
    if l:
        pks_set.add(tuple(l.split('|')))

fks_dict = {}
for l in raw_fks.strip().split('\n'):
    if l:
        t, c, ft, fc = l.split('|')
        fks_dict[(t, c)] = (ft, fc)

# Logical FKs from SQLAlchemy models
logical_fks = [
    ('messages', 'application_id', 'job_applications', 'id'),
    ('form_templates', 'created_by', 'users', 'id'),
    ('system_configs', 'updated_by', 'users', 'id'),
    ('password_resets', 'email', 'users', 'email'),
    ('hr_candidate_notes', 'author_email', 'users', 'email'),
    ('notifications', 'target_email', 'users', 'email'),
    ('applicant_profile_access_logs', 'accessed_by', 'users', 'email')
]
for t, c, ft, fc in logical_fks:
    if (t, c) not in fks_dict:
        fks_dict[(t, c)] = (ft, fc)

schema = {}
for line in raw_cols.strip().split('\n'):
    if not line: continue
    t, c, dt, n = line.split('|')
    is_pk = (t, c) in pks_set
    fk_target = fks_dict.get((t, c))
    schema.setdefault(t, []).append({
        'name': c,
        'type': dt,
        'nullable': n == 'YES',
        'is_pk': is_pk,
        'fk_to': fk_target
    })

# Domains definition
clusters = {
    'cluster_identity': {
        'label': 'Identity, Authentication & Role Profiles',
        'bgcolor': '#F8FAFC',
        'header_bg': '#0F172A',
        'header_text': '#FFFFFF',
        'border': '#CBD5E1',
        'tables': ['users', 'candidates', 'hr_staffs', 'admins', 'password_resets', 'audit_logs']
    },
    'cluster_jobs': {
        'label': 'Job Descriptions & Recruitment Setup',
        'bgcolor': '#F5F3FF',
        'header_bg': '#4338CA',
        'header_text': '#FFFFFF',
        'border': '#DDD6FE',
        'tables': ['job_descriptions', 'form_templates', 'shortlist_rosters', 'shortlist_roster_items']
    },
    'cluster_applications': {
        'label': 'Job Applications, ATS Analysis & Resumes',
        'bgcolor': '#F0FDF4',
        'header_bg': '#065F46',
        'header_text': '#FFFFFF',
        'border': '#A7F3D0',
        'tables': ['job_applications', 'resumes', 'physical_resumes', 'application_status_history', 'hr_candidate_notes', 'applicant_profile_access_logs']
    },
    'cluster_interviews': {
        'label': 'Interview Scheduling & AI Voice Calls',
        'bgcolor': '#FFF1F2',
        'header_bg': '#9F1239',
        'header_text': '#FFFFFF',
        'border': '#FECDD3',
        'tables': ['interviews', 'interview_logs', 'voice_call_records', 'interview_panelists']
    },
    'cluster_comms': {
        'label': 'Messaging, Alerts & System Configuration',
        'bgcolor': '#EFF6FF',
        'header_bg': '#1E40AF',
        'header_text': '#FFFFFF',
        'border': '#BFDBFE',
        'tables': ['messages', 'archived_conversations', 'notifications', 'system_configs']
    }
}

type_map = {
    'integer': 'INT',
    'character varying': 'VARCHAR',
    'timestamp without time zone': 'DATETIME',
    'timestamp with time zone': 'TIMESTAMPTZ',
    'double precision': 'FLOAT',
    'boolean': 'BOOLEAN',
    'text': 'TEXT',
    'json': 'JSON'
}

def format_type(t_str):
    return type_map.get(t_str, t_str.upper())

def build_dot(is_overview=False):
    title = "Automated Resume Analysis System - Full Entity-Relationship Diagram (ERD)" if not is_overview else "Automated Resume Analysis System - Core Entity-Relationship Diagram (Overview)"
    subtitle = "Complete Database Schema (24 Tables, PostgreSQL 16, SQLAlchemy Async)" if not is_overview else "Core Entities, Primary Keys, Foreign Keys & Relationships"

    dot = [
        'digraph ERD {',
        '  graph [rankdir=TB, splines=spline, nodesep=0.7, ranksep=1.1, bgcolor="#FFFFFF",',
        f'         fontname="Helvetica-Bold", fontsize=18, label="{title}\\n{subtitle}\\n", labelloc=t, labeljust=l];',
        '  node [shape=plain, fontname="Helvetica", fontsize=10];',
        '  edge [fontname="Helvetica", fontsize=8, color="#64748B", penwidth=1.6, arrowhead=vee, arrowsize=0.85];\n'
    ]

    for c_id, c_data in clusters.items():
        dot.append(f'  subgraph {c_id} {{')
        dot.append(f'    label="{c_data["label"]}";')
        dot.append(f'    style="rounded,filled";')
        dot.append(f'    color="{c_data["border"]}";')
        dot.append(f'    fillcolor="{c_data["bgcolor"]}";')
        dot.append(f'    fontsize=13;')
        dot.append(f'    fontname="Helvetica-Bold";')
        dot.append(f'    margin=14;\n')

        for tbl in c_data['tables']:
            if tbl not in schema:
                continue
            cols = schema[tbl]
            h_bg = c_data['header_bg']
            h_tx = c_data['header_text']

            def col_priority(c):
                if c['is_pk'] and c['fk_to']: return (0, c['name'])
                if c['is_pk']: return (1, c['name'])
                if c['fk_to']: return (2, c['name'])
                return (3, c['name'])

            sorted_cols = sorted(cols, key=col_priority)

            # In overview mode, limit non-key columns to 6
            if is_overview and len(sorted_cols) > 10:
                pk_fk_cols = [c for c in sorted_cols if c['is_pk'] or c['fk_to']]
                other_cols = [c for c in sorted_cols if not c['is_pk'] and not c['fk_to']]
                displayed_cols = pk_fk_cols + other_cols[:6]
                remaining_count = len(sorted_cols) - len(displayed_cols)
            else:
                displayed_cols = sorted_cols
                remaining_count = 0

            html = [f'<<table border="1" cellborder="0" cellspacing="0" cellpadding="4" style="rounded" bgcolor="#FFFFFF" color="{c_data["border"]}">' ]
            html.append(f'<tr><td colspan="3" bgcolor="{h_bg}" align="center"><font color="{h_tx}"><b>{tbl.upper()}</b></font></td></tr>')

            for col in displayed_cols:
                c_name = col['name']
                c_type = format_type(col['type'])
                tag = ""
                tag_color = "#64748B"
                if col['is_pk'] and col['fk_to']:
                    tag = "PK, FK"
                    tag_color = "#DC2626"
                elif col['is_pk']:
                    tag = "PK"
                    tag_color = "#D97706"
                elif col['fk_to']:
                    tag = "FK"
                    tag_color = "#2563EB"

                req_mark = '' if col['nullable'] else '*'
                tag_html = f'<font color="{tag_color}"><b>{tag}</b></font>' if tag else ''

                html.append(f'<tr>'
                            f'<td align="left" port="{c_name}"><font color="#0F172A"><b>{c_name}</b>{req_mark}</font></td>'
                            f'<td align="left"><font color="#64748B">{c_type}</font></td>'
                            f'<td align="right">{tag_html}</td>'
                            f'</tr>')

            if remaining_count > 0:
                html.append(f'<tr><td colspan="3" align="center" bgcolor="#F1F5F9"><font color="#64748B"><i>... and {remaining_count} more columns</i></font></td></tr>')

            html.append('</table>>')
            dot.append(f'    {tbl} [label={"".join(html)}];')

        dot.append('  }\n')

    # Edge styling with distinct colors per primary entity
    edge_colors = {
        'users': '#2563EB',
        'job_descriptions': '#7C3AED',
        'job_applications': '#059669',
        'interviews': '#DC2626',
        'shortlist_rosters': '#D97706',
        'candidates': '#0284C7'
    }

    for (t, c), (ft, fc) in fks_dict.items():
        if t in schema and ft in schema:
            e_color = edge_colors.get(ft, '#64748B')
            label = f"{t}.{c} -> {ft}.{fc}"
            dot.append(f'  {t}:{c} -> {ft}:{fc} [color="{e_color}", tooltip="{label}"];')

    dot.append('}')
    return '\n'.join(dot)

# Generate both
os.makedirs('docs', exist_ok=True)

with open('docs/erd_complete.dot', 'w') as f:
    f.write(build_dot(is_overview=False))

with open('docs/erd_overview.dot', 'w') as f:
    f.write(build_dot(is_overview=True))

print("Compiling complete ERD (PNG & SVG)...")
subprocess.run(['dot', '-Tpng', '-Gdpi=150', 'docs/erd_complete.dot', '-o', 'docs/erd_complete.png'], check=True)
subprocess.run(['dot', '-Tsvg', 'docs/erd_complete.dot', '-o', 'docs/erd_complete.svg'], check=True)

print("Compiling overview ERD (PNG & SVG)...")
subprocess.run(['dot', '-Tpng', '-Gdpi=150', 'docs/erd_overview.dot', '-o', 'docs/erd_overview.png'], check=True)
subprocess.run(['dot', '-Tsvg', 'docs/erd_overview.dot', '-o', 'docs/erd_overview.svg'], check=True)

# Also create standardized files in root / docs
shutil.copy('docs/erd_complete.png', 'docs/erd.png')
shutil.copy('docs/erd_complete.svg', 'docs/erd.svg')

# Copy to conversation artifact directory
artifact_dir = '/home/marvin/.gemini/antigravity/brain/f4b6b84a-eb9f-4231-89c1-38da313c6121'
os.makedirs(artifact_dir, exist_ok=True)
shutil.copy('docs/erd_complete.png', os.path.join(artifact_dir, 'erd_complete.png'))
shutil.copy('docs/erd_complete.svg', os.path.join(artifact_dir, 'erd_complete.svg'))
shutil.copy('docs/erd_overview.png', os.path.join(artifact_dir, 'erd_overview.png'))
shutil.copy('docs/erd_overview.svg', os.path.join(artifact_dir, 'erd_overview.svg'))
shutil.copy('docs/erd.png', os.path.join(artifact_dir, 'erd.png'))

print("All ERD images generated and copied successfully!")
