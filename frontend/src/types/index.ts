export type Role = 'ADMIN' | 'HR' | 'CANDIDATE' | 'Guest' | string;

export interface User {
  id?: number | string;
  email: string;
  role: Role;
  name?: string;
  fullname?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  location?: string;
  bio?: string;
  profile_image_url?: string | null;
  created_at?: string;
  is_active?: boolean;
  is_archived?: boolean;
  is_online?: boolean;
  last_active?: string;
}

export interface Job {
  id: number | string;
  job_id?: string;
  title: string;
  job_title?: string;
  department: string;
  location: string;
  salary_range: string;
  job_type?: string;
  employment_type?: string;
  skills_requirements?: string | string[];
  experience_required?: string;
  experience_requirements?: string;
  education_required?: string;
  education_requirements?: string;
  certifications_requirements?: string;
  responsibilities?: string;
  qualifications?: string;
  description?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  applicant_count?: number;
}

export interface Application {
  id: number | string;
  name: string;
  candidate_name?: string;
  email: string;
  candidate_email?: string;
  phone: string;
  location: string;
  status: string;
  preferredJob: string;
  company: string;
  skills: string[];
  matched_skills?: string[];
  missing_skills?: string[];
  profileImage?: string | null;
  profile_image_url?: string | null;
  resumeUrl?: string | null;
  resume_url?: string | null;
  date: string;
  created_at?: string;
  jobLocation?: string;
  jobDepartment?: string;
  degree?: string;
  college?: string;
  relevance?: string;
  matchScore: number;
  match_score?: number;
  skillsScore: number;
  skills_score?: number;
  experienceScore: number;
  experience_score?: number;
  educationScore: number;
  education_score?: number;
  certificationsScore: number;
  certifications_score?: number;
  skills_reason?: string;
  experience_reason?: string;
  education_reason?: string;
  relevant_experience?: string | null;
  experience_gaps?: string | null;
  required_degree?: string | null;
  candidate_degree?: string | null;
  recommendations?: string[];
  ai_summary?: string;
  strengths?: string[];
  weaknesses?: string[];
  ai_powered?: boolean;
  job?: Job;
  job_id?: number | string;
}

export interface CandidateApplicationView {
  id: number | string;
  role: string;
  company: string;
  appliedDate: string;
  status: string;
  statusColor: string;
  step: number;
  totalSteps: number;
  originalData: any;
}

export interface Interview {
  id: number | string;
  title?: string;
  application_id?: number | string;
  candidate_name?: string;
  candidate_email?: string;
  job_title?: string;
  interviewer_id?: number | string;
  interviewer_name?: string;
  interviewer_email?: string;
  scheduled_date?: string;
  start_time?: string;
  end_time?: string;
  stage?: string;
  round?: string;
  status?: string;
  meeting_link?: string;
  location?: string;
  notes?: string;
  created_at?: string;
}

export interface NotificationItem {
  id: number | string;
  title?: string;
  message?: string;
  desc?: string;
  type?: string;
  read?: boolean;
  is_read?: boolean;
  created_at?: string | Date;
  createdAt?: string | Date;
  time?: string;
  relativeTime?: string;
  timeStr?: string;
  dateStr?: string;
  displayDateTime?: string;
  fullDateTime?: string;
  tag?: string | null;
  tagColor?: string | null;
  bgColor?: string;
  textColor?: string;
  icon?: string;
  sender_role?: string;
  link?: string;
  data?: any;
}

export interface ChatMessage {
  id?: number | string;
  sender_id?: number | string;
  sender_email?: string;
  sender_name?: string;
  receiver_id?: number | string;
  receiver_email?: string;
  content: string;
  created_at?: string;
  timestamp?: string;
  is_read?: boolean;
}

export interface ChatContact {
  id: number | string;
  name: string;
  email: string;
  role?: string;
  unread_count?: number;
  last_message?: string;
  last_message_time?: string;
  profile_image_url?: string | null;
  is_archived?: boolean;
}
