/**
 * department-db-types.ts — TypeScript Models for AIDA Department Database Entities.
 * 
 * Provides type contracts for:
 * 1. Faculty
 * 2. Students
 * 3. Subjects
 * 4. Timetable
 * 5. Notices
 * 6. Events
 * 7. Academic Documents
 * 8. Student Requests & Approval Workflow
 */

export interface Faculty {
    id: string;
    user_id?: string | null;
    name: string;
    designation: string;
    department: string;
    email: string;
    contact_info?: string | null;
    specialization?: string | null;
    subjects_handled?: string[];
    availability?: string | null;
    is_active: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface Student {
    id: string;
    user_id?: string | null;
    enrollment_no: string;
    full_name: string;
    email: string;
    department: string;
    semester: number;
    section: string;
    batch_year?: string;
    contact_number?: string | null;
    created_at?: string;
    updated_at?: string;
}

export interface Subject {
    id: string;
    name: string;
    department: string;
    semester: number;
    credits: number;
    description?: string | null;
    syllabus_url?: string | null;
    faculty_in_charge_id?: string | null;
    created_at?: string;
}

export interface TimetableEntry {
    id: string;
    day: string;
    time_slot: string;
    subject_id?: string | null;
    subject_name: string;
    faculty_id?: string | null;
    faculty_name?: string | null;
    room: string;
    student_group: string;
    department: string;
    created_at?: string;
}

export interface Notice {
    id: string;
    title: string;
    content: string;
    department: string;
    category: string;
    date: string;
    is_pinned?: boolean;
    created_by?: string | null;
    created_at?: string;
}

export interface DepartmentEvent {
    id: string;
    title: string;
    description: string;
    date_time: string;
    location: string;
    organizer: string;
    department: string;
    created_by?: string | null;
    created_at?: string;
    updated_at?: string;
}

export interface AcademicDocument {
    id: string;
    filename: string;
    file_path: string;
    category: string;
    department: string;
    year?: string | null;
    course?: string | null;
    file_size_bytes?: number | null;
    uploaded_by?: string | null;
    created_at?: string;
}

export type StudentRequestStatus =
    | "Pending"
    | "Under Review"
    | "In Review"
    | "Approved"
    | "Rejected"
    | "More Information Required";

export interface RequestHistoryItem {
    timestamp: string;
    action: string;
    actor_name?: string;
    actor_role?: string;
    from_status?: string;
    to_status?: string;
    comments?: string;
    assigned_to?: string;
}

export type StudentRequestType =
    | "Bonafide Certificate"
    | "Lab Compute Access"
    | "Leave of Absence"
    | "Project Guide Allocation"
    | "Course Exemption"
    | "Other";

export interface StudentRequest {
    id: string;
    student_id?: string | null;
    user_id: string;
    request_type: StudentRequestType | string;
    description: string;
    status: StudentRequestStatus;
    assigned_to?: string | null;
    comments?: string | null;
    history?: RequestHistoryItem[];
    created_at: string;
    updated_at: string;
    students?: {
        full_name: string;
        enrollment_no: string;
        section: string;
    };
    faculty?: {
        name: string;
        designation: string;
    };
}

export interface DepartmentOverviewStats {
    department_code: string;
    department_name: string;
    students_count: number;
    faculty_count: number;
    active_notices_count: number;
    total_events_count: number;
    upcoming_events_count: number;
    pending_requests_count: number;
    total_requests_count: number;
    subjects_count: number;
    documents_count: number;
    students_by_section: Record<string, number>;
    upcoming_events: DepartmentEvent[];
    recent_requests: StudentRequest[];
}

