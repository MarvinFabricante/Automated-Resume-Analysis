import { Job } from '../types';

export const STATIC_JOBS: (Partial<Job> & { id: number; title: string; department: string; skills_requirements: string; location: string; job_type: string; salary_range: string; is_active: boolean })[] = [
  {
    id: 1,
    title: "Production Supervisor",
    department: "Manufacturing",
    skills_requirements: "Experience in ceramic manufacturing, leadership skills, and knowledge of ISO standards. Minimum 3 years experience.",
    location: "Bulacan",
    job_type: "Full-time",
    salary_range: "₱30,000 - ₱45,000",
    is_active: true
  },
  {
    id: 2,
    title: "Quality Control Analyst",
    department: "Quality Assurance",
    skills_requirements: "Strong attention to detail, laboratory experience, and knowledge of material testing. Chemical Engineering background preferred.",
    location: "Bulacan",
    job_type: "Full-time",
    salary_range: "₱25,000 - ₱35,000",
    is_active: true
  },
  {
    id: 3,
    title: "HR Generalist",
    department: "Human Resources",
    skills_requirements: "Recruitment, payroll processing, and employee relations. Excellent communication skills required.",
    location: "Makati",
    job_type: "Full-time",
    salary_range: "₱28,000 - ₱40,000",
    is_active: true
  },
  {
    id: 4,
    title: "Maintenance Technician",
    department: "Engineering",
    skills_requirements: "Troubleshooting industrial machinery, electrical systems, and preventive maintenance. TESDA certification is a plus.",
    location: "Bulacan",
    job_type: "Full-time",
    salary_range: "₱20,000 - ₱28,000",
    is_active: false
  }
];
