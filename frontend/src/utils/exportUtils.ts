import api from '../services/api';
import {
  computeAverageMatchScore,
  computeDepartmentDistribution,
  computePositionDistribution,
  computeSkillsDistribution,
  extractAppUtcDateIso,
} from './hrAnalytics';

export interface DashboardExportPayload {
  applications: any[];
  appStats?: Record<string, any>;
  activeJobsCount?: number;
  totalCandidates?: number;
  totalResumes?: number;
  trendsData?: any;
}

const serializeCsvCell = (rawValue: unknown): string => {
  const raw = rawValue === null || rawValue === undefined ? '' : String(rawValue);
  const safe =
    /^[=+\-@\t\r]/.test(raw) && !/^-?\d+(\.\d+)?%?$/.test(raw)
      ? `'${raw}`
      : raw;
  const escaped = safe.replace(/"/g, '""');
  return `"${escaped}"`;
};

const buildCsvRow = (cells: unknown[]): string => cells.map(serializeCsvCell).join(',');

const sanitizeBaseFileName = (fileName: string, extension: string): string => {
  const extPattern = new RegExp(`\\.${extension}$`, 'i');
  return `${fileName.replace(extPattern, '')}.${extension}`;
};

export const downloadBlobFile = (blob: Blob, fileName: string, extension: string): void => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', sanitizeBaseFileName(fileName, extension));
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

const formatDateTag = (): string => new Date().toISOString().split('T')[0];

const normalizeSkillsText = (skills: unknown): string => {
  if (Array.isArray(skills)) {
    return skills.map((s) => String(s).trim()).filter(Boolean).join(', ') || 'None listed';
  }
  if (typeof skills === 'string' && skills.trim()) {
    return skills.trim();
  }
  return 'None listed';
};

/**
 * Utility to export an array of objects to a CSV file.
 * @param {Array<Record<string, any>>} data - The array of objects to export.
 * @param {string} fileName - The name of the file (without extension).
 */
export const exportToCSV = (data: Record<string, any>[], fileName: string): void => {
  if (!data || !data.length) {
    alert('No data available to export.');
    return;
  }

  const headers = Object.keys(data[0]);
  const csvRows = [
    buildCsvRow(headers),
    ...data.map((row) => buildCsvRow(headers.map((header) => row[header]))),
  ];

  const csvString = `\ufeff${csvRows.join('\r\n')}`;
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
  downloadBlobFile(blob, fileName, 'csv');
};

/**
 * Build and download a complete HR Dashboard CSV report containing analytics
 * summaries, position/department/skills breakdowns, and full applicant rows
 * matching what is rendered on screen.
 */
export const exportDashboardAnalyticsToCSV = (
  payload: DashboardExportPayload,
  fileName = `Mariwasa_HR_Recruitment_Report_${formatDateTag()}`
): { rowCount: number } => {
  const applications = Array.isArray(payload.applications) ? payload.applications : [];
  const stats = payload.appStats || {};
  const trends = payload.trendsData || {};

  const averageScore = computeAverageMatchScore(applications, trends?.average_score);
  const positionDist = computePositionDistribution(applications, trends?.position_distribution);
  const departmentDist = computeDepartmentDistribution(applications, trends?.department_distribution);
  const skillsDist = computeSkillsDistribution(applications, trends?.skills_distribution);

  const totalApplications = Math.max(
    applications.length,
    Number(stats?.total || 0)
  );
  const totalCandidates = payload.totalCandidates ?? totalApplications;
  const totalResumes = payload.totalResumes ?? totalApplications;
  const activePositions = payload.activeJobsCount ?? positionDist.length;

  const lines: string[] = [
    buildCsvRow(['Mariwasa HR Recruitment Analytics & Applicant Report']),
    buildCsvRow(['Generated Date', new Date().toISOString()]),
    '',
    buildCsvRow(['ANALYTICS SUMMARY']),
    buildCsvRow(['Metric', 'Value']),
    buildCsvRow(['Total Applications', totalApplications]),
    buildCsvRow(['Total Candidates', totalCandidates]),
    buildCsvRow(['Total Resumes', totalResumes]),
    buildCsvRow(['Active Positions', activePositions]),
    buildCsvRow(['Average Match Score', `${averageScore}%`]),
    buildCsvRow(['Pending', Number(stats?.pending ?? 0)]),
    buildCsvRow(['Reviewed', Number(stats?.reviewed ?? 0)]),
    buildCsvRow(['Accepted', Number(stats?.accepted ?? 0)]),
    buildCsvRow(['Rejected', Number(stats?.rejected ?? 0)]),
    '',
    buildCsvRow(['APPLICANTS PER POSITION']),
    buildCsvRow(['Position', 'Applicant Count', 'Share', 'Average Match Score']),
    ...(positionDist.length > 0
      ? positionDist.map((item) =>
          buildCsvRow([
            item.label,
            item.value,
            item.percentage,
            `${Number(item.avg_score ?? 0)}%`,
          ])
        )
      : [buildCsvRow(['No position data', 0, '0%', '0%'])]),
    '',
    buildCsvRow(['DEPARTMENT BREAKDOWN']),
    buildCsvRow(['Department', 'Applicant Count', 'Share']),
    ...(departmentDist.length > 0
      ? departmentDist.map((item) => buildCsvRow([item.label, item.value, item.percentage]))
      : [buildCsvRow(['No department data', 0, '0%'])]),
    '',
    buildCsvRow(['SKILLS DISTRIBUTION']),
    buildCsvRow(['Skill', 'Applicant Count', 'Share']),
    ...(skillsDist.length > 0
      ? skillsDist.map((item) => buildCsvRow([item.label, item.value, item.percentage]))
      : [buildCsvRow(['No skills recorded', 0, '0%'])]),
    '',
    buildCsvRow(['APPLICANT DATA']),
    buildCsvRow([
      'ID',
      'Candidate Name',
      'Email',
      'Preferred Role',
      'Department',
      'Status',
      'Match Score',
      'Skills Score',
      'Experience Score',
      'Education Score',
      'Experience (Years)',
      'Skills',
      'Application Date',
      'Location',
    ]),
    ...applications.map((app: any) =>
      buildCsvRow([
        app.id ?? 'N/A',
        app.name || 'Candidate',
        app.email || 'N/A',
        app.preferredJob || app.job?.job_title || 'General Application',
        app.jobDepartment || app.job?.department || 'General',
        app.status || 'Pending',
        `${Number(app.matchScore ?? app.match_score ?? 0)}%`,
        `${Number(app.skillsScore ?? app.skills_score ?? 0)}%`,
        `${Number(app.experienceScore ?? app.experience_score ?? 0)}%`,
        `${Number(app.educationScore ?? app.education_score ?? 0)}%`,
        app.experienceYears ?? app.experience_years ?? 0,
        normalizeSkillsText(app.skills),
        extractAppUtcDateIso(app.date || app.applied_at) || 'N/A',
        app.location || 'N/A',
      ])
    ),
  ];

  const csvString = `\ufeff${lines.join('\r\n')}`;
  const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
  downloadBlobFile(blob, fileName, 'csv');
  return { rowCount: applications.length };
};

const escapePdfAscii = (input: string): string =>
  input
    .replace(/[^\x20-\x7e]/g, ' ')
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)');

const buildMinimalPdfBlob = (payload: DashboardExportPayload): Blob => {
  const applications = Array.isArray(payload.applications) ? payload.applications : [];
  const stats = payload.appStats || {};
  const trends = payload.trendsData || {};
  const averageScore = computeAverageMatchScore(applications, trends?.average_score);
  const positionDist = computePositionDistribution(applications, trends?.position_distribution);
  const skillsDist = computeSkillsDistribution(applications, trends?.skills_distribution);

  const lines: string[] = [
    'Mariwasa HR Recruitment & Analytics Report',
    `Generated: ${formatDateTag()}`,
    `Total Applications: ${applications.length} | Avg Match Score: ${averageScore}% | Active Positions: ${payload.activeJobsCount ?? positionDist.length}`,
    `Statuses - Pending: ${stats?.pending ?? 0}, Reviewed: ${stats?.reviewed ?? 0}, Accepted: ${stats?.accepted ?? 0}, Rejected: ${stats?.rejected ?? 0}`,
    '--- Applicants Per Position ---',
    ...positionDist.slice(0, 10).map(
      (item) => `${item.label}: ${item.value} (${item.percentage}, avg ${Number(item.avg_score ?? 0)}%)`
    ),
    '--- Top Skills Distribution ---',
    ...skillsDist.slice(0, 12).map((item) => `${item.label}: ${item.value} (${item.percentage})`),
    '--- Applicant Records ---',
    ...applications.slice(0, 22).map((app: any) => {
      const dateStr = extractAppUtcDateIso(app.date || app.applied_at) || 'N/A';
      return `#${app.id ?? '-'} ${app.name || 'Candidate'} | ${app.preferredJob || 'General'} | ${app.status || 'Pending'} | ${app.matchScore ?? 0}% | ${dateStr}`;
    }),
  ];

  const textOps = lines.map((line, index) => {
    const y = 780 - index * 14;
    if (y < 40) return '';
    return `BT /F1 ${index === 0 ? 13 : 9} Tf 40 ${y} Td (${escapePdfAscii(line.slice(0, 105))}) Tj ET`;
  }).filter(Boolean).join('\n');

  const encoder = new TextEncoder();
  const objects = [
    '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
    '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
    '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n',
    '4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n',
    `5 0 obj\n<< /Length ${encoder.encode(textOps).length} >>\nstream\n${textOps}\nendstream\nendobj\n`,
  ];

  let pdf = '%PDF-1.4\n';
  const offsets: number[] = [];
  for (const obj of objects) {
    offsets.push(encoder.encode(pdf).length);
    pdf += obj;
  }
  const xrefStart = encoder.encode(pdf).length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets) {
    pdf += `${String(offset).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF\n`;

  return new Blob([encoder.encode(pdf)], { type: 'application/pdf' });
};

/**
 * Download the multi-page HR Dashboard PDF report from `/hr/export/pdf`,
 * falling back cleanly to a valid client-generated PDF if the backend is unavailable.
 */
export const exportDashboardPDFWithFallback = async (
  payload: DashboardExportPayload,
  fileName = `Mariwasa_HR_Recruitment_Report_${formatDateTag()}`
): Promise<{ source: 'backend' | 'fallback'; rowCount: number }> => {
  const rowCount = Array.isArray(payload.applications) ? payload.applications.length : 0;
  try {
    const response = await api.get('/hr/export/pdf', { responseType: 'blob' });
    const blob = response.data instanceof Blob
      ? response.data
      : new Blob([response.data], { type: 'application/pdf' });

    if (blob.size > 0 && !(blob.type && blob.type.includes('application/json'))) {
      const headerSignature = await blob.slice(0, 5).text();
      if (headerSignature.startsWith('%PDF-')) {
        downloadBlobFile(blob, fileName, 'pdf');
        return { source: 'backend', rowCount };
      }
    }
  } catch {
    // Fallback below ensures the PDF file still downloads when offline
  }

  const fallbackBlob = buildMinimalPdfBlob(payload);
  downloadBlobFile(fallbackBlob, fileName, 'pdf');
  return { source: 'fallback', rowCount };
};

