"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "../../lib/api-client";
import {
    Student,
    Faculty,
    Subject,
    Notice,
    DepartmentEvent,
    StudentRequest,
    StudentRequestStatus,
    DepartmentOverviewStats
} from "../../lib/department-db-types";

type AdminTab =
    | "overview"
    | "students"
    | "faculty"
    | "subjects"
    | "timetable"
    | "notices"
    | "events"
    | "docs"
    | "requests"
    | "logs";

interface LogEntry {
    id: string;
    created_at: string;
    user_id: string | null;
    query: string;
    intent: string;
    latency_ms: number;
}

interface DocumentItem {
    name: string;
    size: number;
    department: string;
    category: string;
    year: string;
    course: string;
}

type TimetableFile = {
    filename: string;
    group: string;
    rows: Record<string, string>[];
    headers: string[];
    row_count: number;
    size: number;
};

export default function AdminDashboard() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<AdminTab>("overview");
    const [isAdmin, setIsAdmin] = useState<boolean | null>(null);

    // ── 1. OVERVIEW & ANALYTICS STATE ───────────────────────────────────────────
    const [overview, setOverview] = useState<DepartmentOverviewStats | null>(null);
    const [isOverviewLoading, setIsOverviewLoading] = useState(false);

    // ── 2. STUDENTS MANAGEMENT STATE ────────────────────────────────────────────
    const [students, setStudents] = useState<Student[]>([]);
    const [isStudentsLoading, setIsStudentsLoading] = useState(false);
    const [studentSectionFilter, setStudentSectionFilter] = useState("all");
    const [showStudentModal, setShowStudentModal] = useState(false);
    const [editingStudent, setEditingStudent] = useState<Student | null>(null);
    const [studentFormData, setStudentFormData] = useState({
        enrollment_no: "",
        full_name: "",
        email: "",
        section: "AIML-A",
        semester: 6,
        batch_year: "2023-2027",
        contact_number: ""
    });

    // ── 3. FACULTY MANAGEMENT STATE ─────────────────────────────────────────────
    const [facultyList, setFacultyList] = useState<Faculty[]>([]);
    const [isFacultyLoading, setIsFacultyLoading] = useState(false);
    const [showFacultyModal, setShowFacultyModal] = useState(false);
    const [editingFaculty, setEditingFaculty] = useState<Faculty | null>(null);
    const [facultyFormData, setFacultyFormData] = useState({
        name: "",
        designation: "Assistant Professor",
        email: "",
        contact_info: "",
        specialization: "",
        subjects_handled: "AI401",
        availability: "Mon & Wed: 2:00 PM - 4:00 PM"
    });

    // ── 4. SUBJECTS CATALOG STATE ───────────────────────────────────────────────
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [isSubjectsLoading, setIsSubjectsLoading] = useState(false);
    const [showSubjectModal, setShowSubjectModal] = useState(false);
    const [editingSubject, setEditingSubject] = useState<Subject | null>(null);
    const [subjectFormData, setSubjectFormData] = useState({
        id: "",
        name: "",
        semester: 6,
        credits: 4,
        description: ""
    });

    // ── 5. TIMETABLES & DEADLINES STATE ─────────────────────────────────────────
    const [timetableFiles, setTimetableFiles] = useState<TimetableFile[]>([]);
    const [isTimetableLoading, setIsTimetableLoading] = useState(false);
    const [timeFile, setTimeFile] = useState<File | null>(null);
    const [timeGroup, setTimeGroup] = useState("");
    const [timeStatus, setTimeStatus] = useState("");
    const [isTimeUploading, setIsTimeUploading] = useState(false);
    const [expandedGroup, setExpandedGroup] = useState<string | null>(null);

    const [deadlineFile, setDeadlineFile] = useState<File | null>(null);
    const [deadlineStatus, setDeadlineStatus] = useState("");
    const [isDeadlineUploading, setIsDeadlineUploading] = useState(false);
    const [deadlineRows, setDeadlineRows] = useState<Record<string, string>[]>([]);
    const [deadlineHeaders, setDeadlineHeaders] = useState<string[]>([]);
    const [deadlineExists, setDeadlineExists] = useState(false);
    const [isDeadlineLoading, setIsDeadlineLoading] = useState(false);

    // ── 6. NOTICES STATE ────────────────────────────────────────────────────────
    const [notices, setNotices] = useState<Notice[]>([]);
    const [isNoticesLoading, setIsNoticesLoading] = useState(false);
    const [showNoticeModal, setShowNoticeModal] = useState(false);
    const [editingNotice, setEditingNotice] = useState<Notice | null>(null);
    const [noticeFormData, setNoticeFormData] = useState({
        title: "",
        content: "",
        category: "Academic",
        is_pinned: false
    });

    // ── 7. EVENTS STATE ─────────────────────────────────────────────────────────
    const [events, setEvents] = useState<DepartmentEvent[]>([]);
    const [isEventsLoading, setIsEventsLoading] = useState(false);
    const [showEventModal, setShowEventModal] = useState(false);
    const [editingEvent, setEditingEvent] = useState<DepartmentEvent | null>(null);
    const [eventFormData, setEventFormData] = useState({
        title: "",
        description: "",
        date_time: "",
        location: "",
        organizer: "AIML Department"
    });

    // ── 8. DOCUMENTS & RAG KNOWLEDGE BASE STATE ─────────────────────────────────
    const [documents, setDocuments] = useState<DocumentItem[]>([]);
    const [isDocsLoading, setIsDocsLoading] = useState(false);
    const [docFile, setDocFile] = useState<File | null>(null);
    const [docStatus, setDocStatus] = useState("");
    const [isDocUploading, setIsDocUploading] = useState(false);
    const [docCategory, setDocCategory] = useState("AIML Syllabus");
    const [docCourse, setDocCourse] = useState("AI401");
    const [docYear, setDocYear] = useState("2025-2026");
    const [indexStatus, setIndexStatus] = useState("");
    const [isIndexing, setIsIndexing] = useState(false);

    // ── 9. STUDENT REQUESTS & APPROVAL STATE ────────────────────────────────────
    const [adminRequests, setAdminRequests] = useState<StudentRequest[]>([]);
    const [isAdminRequestsLoading, setIsAdminRequestsLoading] = useState(false);
    const [adminRequestFilter, setAdminRequestFilter] = useState("all");
    const [adminReviewComments, setAdminReviewComments] = useState<Record<string, string>>({});
    const [adminActionLoading, setAdminActionLoading] = useState<string | null>(null);
    const [adminExpandedHistory, setAdminExpandedHistory] = useState<Record<string, boolean>>({});

    // ── 10. SYSTEM LOGS & TELEMETRY STATE ───────────────────────────────────────
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isLogsLoading, setIsLogsLoading] = useState(false);

    // ── STRICT AUTHENTICATION GUARD ─────────────────────────────────────────────
    useEffect(() => {
        const checkAdmin = async () => {
            const token = localStorage.getItem("token");
            if (!token) {
                router.push("/login");
                return;
            }
            try {
                const res = await apiFetch("/me");
                if (res.ok) {
                    const data = await res.json();
                    if (!data.is_admin) {
                        router.push(data.is_faculty ? "/faculty" : "/");
                    } else {
                        setIsAdmin(true);
                    }
                } else {
                    router.push("/login");
                }
            } catch (err) {
                console.error("Admin auth check failed:", err);
                router.push("/login");
            }
        };
        checkAdmin();
    }, [router]);

    // ── FETCH DATA ON TAB CHANGE ────────────────────────────────────────────────
    useEffect(() => {
        if (!isAdmin) return;
        if (activeTab === "overview") fetchOverview();
        if (activeTab === "students") fetchStudents();
        if (activeTab === "faculty") fetchFaculty();
        if (activeTab === "subjects") fetchSubjects();
        if (activeTab === "timetable") {
            fetchTimetable();
            fetchDeadlines();
        }
        if (activeTab === "notices") fetchNotices();
        if (activeTab === "events") fetchEvents();
        if (activeTab === "docs") fetchDocs();
        if (activeTab === "requests") fetchRequests();
        if (activeTab === "logs") fetchLogs();
    }, [activeTab, isAdmin]);

    // ── DATA FETCHING IMPLEMENTATIONS ───────────────────────────────────────────
    const fetchOverview = async () => {
        setIsOverviewLoading(true);
        try {
            const res = await apiFetch("/admin/overview");
            if (res.ok) {
                setOverview(await res.json());
            }
        } catch (err) {
            console.error("Failed to load overview:", err);
        } finally {
            setIsOverviewLoading(false);
        }
    };

    const fetchStudents = async () => {
        setIsStudentsLoading(true);
        try {
            const res = await apiFetch("/students");
            if (res.ok) {
                setStudents(await res.json());
            }
        } catch (err) {
            console.error("Failed to load students:", err);
        } finally {
            setIsStudentsLoading(false);
        }
    };

    const fetchFaculty = async () => {
        setIsFacultyLoading(true);
        try {
            const res = await apiFetch("/faculty");
            if (res.ok) {
                setFacultyList(await res.json());
            }
        } catch (err) {
            console.error("Failed to load faculty:", err);
        } finally {
            setIsFacultyLoading(false);
        }
    };

    const fetchSubjects = async () => {
        setIsSubjectsLoading(true);
        try {
            const res = await apiFetch("/subjects");
            if (res.ok) {
                setSubjects(await res.json());
            }
        } catch (err) {
            console.error("Failed to load subjects:", err);
        } finally {
            setIsSubjectsLoading(false);
        }
    };

    const fetchTimetable = async () => {
        setIsTimetableLoading(true);
        try {
            const res = await apiFetch("/admin/timetable");
            if (res.ok) {
                setTimetableFiles(await res.json());
            }
        } catch (err) {
            console.error("Failed to load timetables:", err);
        } finally {
            setIsTimetableLoading(false);
        }
    };

    const fetchDeadlines = async () => {
        setIsDeadlineLoading(true);
        try {
            const res = await apiFetch("/admin/deadlines");
            if (res.ok) {
                const data = await res.json();
                setDeadlineExists(data.exists);
                setDeadlineRows(data.rows ?? []);
                setDeadlineHeaders(data.headers ?? []);
            }
        } catch (err) {
            console.error("Failed to load deadlines:", err);
        } finally {
            setIsDeadlineLoading(false);
        }
    };

    const fetchNotices = async () => {
        setIsNoticesLoading(true);
        try {
            const res = await apiFetch("/db/notices");
            if (res.ok) {
                setNotices(await res.json());
            }
        } catch (err) {
            console.error("Failed to load notices:", err);
        } finally {
            setIsNoticesLoading(false);
        }
    };

    const fetchEvents = async () => {
        setIsEventsLoading(true);
        try {
            const res = await apiFetch("/events");
            if (res.ok) {
                setEvents(await res.json());
            }
        } catch (err) {
            console.error("Failed to load events:", err);
        } finally {
            setIsEventsLoading(false);
        }
    };

    const fetchDocs = async () => {
        setIsDocsLoading(true);
        try {
            const res = await apiFetch("/admin/docs");
            if (res.ok) {
                setDocuments(await res.json());
            }
        } catch (err) {
            console.error("Failed to load documents:", err);
        } finally {
            setIsDocsLoading(false);
        }
    };

    const fetchRequests = async () => {
        setIsAdminRequestsLoading(true);
        try {
            const res = await apiFetch("/requests");
            if (res.ok) {
                setAdminRequests(await res.json());
            }
        } catch (err) {
            console.error("Failed to load requests:", err);
        } finally {
            setIsAdminRequestsLoading(false);
        }
    };

    const fetchLogs = async () => {
        setIsLogsLoading(true);
        try {
            const res = await apiFetch("/admin/logs");
            if (res.ok) {
                setLogs(await res.json());
            }
        } catch (err) {
            console.error("Failed to load telemetry logs:", err);
        } finally {
            setIsLogsLoading(false);
        }
    };

    // ── CRUD HANDLERS ───────────────────────────────────────────────────────────

    // STUDENTS CRUD
    const handleSaveStudent = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingStudent) {
                const res = await apiFetch(`/students/${editingStudent.id}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(studentFormData)
                });
                if (res.ok) {
                    const updated = await res.json();
                    setStudents(prev => prev.map(s => s.id === editingStudent.id ? { ...s, ...updated } : s));
                    setShowStudentModal(false);
                } else {
                    alert("Failed to update student.");
                }
            } else {
                const res = await apiFetch("/students", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(studentFormData)
                });
                if (res.ok) {
                    const created = await res.json();
                    setStudents(prev => [created, ...prev]);
                    setShowStudentModal(false);
                } else {
                    alert("Failed to create student.");
                }
            }
        } catch (err) {
            console.error("Student save error:", err);
        }
    };

    const handleDeleteStudent = async (studentId: string, name: string) => {
        if (!confirm(`Are you sure you want to delete student "${name}"? This action cannot be undone.`)) return;
        try {
            const res = await apiFetch(`/students/${studentId}`, { method: "DELETE" });
            if (res.ok) {
                setStudents(prev => prev.filter(s => s.id !== studentId && s.enrollment_no !== studentId));
            } else {
                alert("Failed to delete student.");
            }
        } catch (err) {
            console.error("Student delete error:", err);
        }
    };

    // FACULTY CRUD
    const handleSaveFaculty = async (e: React.FormEvent) => {
        e.preventDefault();
        const payload = {
            ...facultyFormData,
            subjects_handled: facultyFormData.subjects_handled.split(",").map(s => s.trim()).filter(Boolean)
        };
        try {
            if (editingFaculty) {
                const res = await apiFetch(`/faculty/${editingFaculty.id}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    const updated = await res.json();
                    setFacultyList(prev => prev.map(f => f.id === editingFaculty.id ? { ...f, ...updated } : f));
                    setShowFacultyModal(false);
                } else {
                    alert("Failed to update faculty.");
                }
            } else {
                const res = await apiFetch("/faculty", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    const created = await res.json();
                    setFacultyList(prev => [...prev, created]);
                    setShowFacultyModal(false);
                } else {
                    alert("Failed to create faculty.");
                }
            }
        } catch (err) {
            console.error("Faculty save error:", err);
        }
    };

    const handleDeleteFaculty = async (facultyId: string, name: string) => {
        if (!confirm(`Are you sure you want to remove faculty member "${name}"? This will detach them from assigned subjects and office hours.`)) return;
        try {
            const res = await apiFetch(`/faculty/${facultyId}`, { method: "DELETE" });
            if (res.ok) {
                setFacultyList(prev => prev.filter(f => f.id !== facultyId));
            } else {
                alert("Failed to delete faculty.");
            }
        } catch (err) {
            console.error("Faculty delete error:", err);
        }
    };

    // SUBJECTS CRUD
    const handleSaveSubject = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingSubject) {
                const res = await apiFetch(`/subjects/${editingSubject.id}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(subjectFormData)
                });
                if (res.ok) {
                    const updated = await res.json();
                    setSubjects(prev => prev.map(s => s.id === editingSubject.id ? { ...s, ...updated } : s));
                    setShowSubjectModal(false);
                } else {
                    alert("Failed to update subject.");
                }
            } else {
                const res = await apiFetch("/subjects", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(subjectFormData)
                });
                if (res.ok) {
                    const created = await res.json();
                    setSubjects(prev => [...prev, created]);
                    setShowSubjectModal(false);
                } else {
                    alert("Failed to add subject.");
                }
            }
        } catch (err) {
            console.error("Subject save error:", err);
        }
    };

    const handleDeleteSubject = async (subjectId: string, name: string) => {
        if (!confirm(`Are you sure you want to remove course "${subjectId} – ${name}" from the active catalog?`)) return;
        try {
            const res = await apiFetch(`/subjects/${subjectId}`, { method: "DELETE" });
            if (res.ok) {
                setSubjects(prev => prev.filter(s => s.id !== subjectId));
            } else {
                alert("Failed to delete subject.");
            }
        } catch (err) {
            console.error("Subject delete error:", err);
        }
    };

    // NOTICES CRUD
    const handleSaveNotice = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingNotice) {
                const res = await apiFetch(`/db/notices/${editingNotice.id}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(noticeFormData)
                });
                if (res.ok) {
                    const updated = await res.json();
                    setNotices(prev => prev.map(n => n.id === editingNotice.id ? { ...n, ...updated } : n));
                    setShowNoticeModal(false);
                } else {
                    alert("Failed to update notice.");
                }
            } else {
                const res = await apiFetch("/db/notices", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(noticeFormData)
                });
                if (res.ok) {
                    const created = await res.json();
                    setNotices(prev => [created, ...prev]);
                    setShowNoticeModal(false);
                } else {
                    alert("Failed to publish notice.");
                }
            }
        } catch (err) {
            console.error("Notice save error:", err);
        }
    };

    const handleDeleteNotice = async (noticeId: string, title: string) => {
        if (!confirm(`Are you sure you want to remove circular "${title}"?`)) return;
        try {
            const res = await apiFetch(`/db/notices/${noticeId}`, { method: "DELETE" });
            if (res.ok) {
                setNotices(prev => prev.filter(n => n.id !== noticeId));
            } else {
                alert("Failed to delete notice.");
            }
        } catch (err) {
            console.error("Notice delete error:", err);
        }
    };

    // EVENTS CRUD
    const handleSaveEvent = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingEvent) {
                const res = await apiFetch(`/events/${editingEvent.id}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(eventFormData)
                });
                if (res.ok) {
                    const updated = await res.json();
                    setEvents(prev => prev.map(ev => ev.id === editingEvent.id ? { ...ev, ...updated } : ev));
                    setShowEventModal(false);
                } else {
                    alert("Failed to update event.");
                }
            } else {
                const res = await apiFetch("/events", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(eventFormData)
                });
                if (res.ok) {
                    const created = await res.json();
                    setEvents(prev => [created, ...prev]);
                    setShowEventModal(false);
                } else {
                    alert("Failed to schedule event.");
                }
            }
        } catch (err) {
            console.error("Event save error:", err);
        }
    };

    const handleDeleteEvent = async (eventId: string, title: string) => {
        if (!confirm(`Are you sure you want to cancel and delete department event "${title}"?`)) return;
        try {
            const res = await apiFetch(`/events/${eventId}`, { method: "DELETE" });
            if (res.ok) {
                setEvents(prev => prev.filter(ev => ev.id !== eventId));
            } else {
                alert("Failed to delete event.");
            }
        } catch (err) {
            console.error("Event delete error:", err);
        }
    };

    // DOCUMENTS & RAG
    const handleUploadDoc = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!docFile) return;
        setIsDocUploading(true);
        setDocStatus("Uploading & vectorizing document...");
        const formData = new FormData();
        formData.append("file", docFile);
        formData.append("department", "AIML");
        formData.append("category", docCategory);
        formData.append("course", docCourse);
        formData.append("year", docYear);

        try {
            const res = await apiFetch("/upload", { method: "POST", body: formData });
            if (res.ok) {
                setDocStatus(`Successfully uploaded ${docFile.name}!`);
                setDocFile(null);
                fetchDocs();
                setTimeout(() => setDocStatus(""), 4000);
            } else {
                setDocStatus("Document upload failed.");
            }
        } catch (err) {
            console.error("Doc upload error:", err);
            setDocStatus("Error uploading file.");
        } finally {
            setIsDocUploading(false);
        }
    };

    const handleDeleteDoc = async (filename: string) => {
        if (!confirm(`Are you sure you want to permanently delete document "${filename}" from the knowledge base? You will need to rebuild the search index afterwards.`)) return;
        try {
            const res = await apiFetch(`/admin/docs/${filename}`, { method: "DELETE" });
            if (res.ok) {
                setDocuments(prev => prev.filter(d => d.name !== filename));
            } else {
                alert("Failed to delete document.");
            }
        } catch (err) {
            console.error("Doc delete error:", err);
        }
    };

    const handleViewDoc = async (filename: string) => {
        try {
            const res = await apiFetch(`/admin/docs/${filename}/view`);
            if (res.ok) {
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                window.open(url, "_blank");
            } else {
                alert("Failed to preview document.");
            }
        } catch (err) {
            console.error("Preview error:", err);
        }
    };

    const handleRebuildIndex = async () => {
        if (!confirm("Rebuilding the FAISS vector index will re-chunk and re-embed all documents in data/docs. Proceed?")) return;
        setIsIndexing(true);
        setIndexStatus("Rebuilding vector embeddings index...");
        try {
            const res = await apiFetch("/rebuild-index", { method: "POST" });
            if (res.ok) {
                const data = await res.json();
                setIndexStatus(`Search index rebuilt successfully! (${data.chunks_count} chunks embedded)`);
                setTimeout(() => setIndexStatus(""), 6000);
            } else {
                setIndexStatus("Rebuild failed.");
            }
        } catch (err) {
            console.error("Index error:", err);
            setIndexStatus("Error rebuilding search index.");
        } finally {
            setIsIndexing(false);
        }
    };

    // TIMETABLES & DEADLINES
    const handleUploadTimetable = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!timeFile) return;
        setIsTimeUploading(true);
        setTimeStatus("Uploading timetable CSV...");
        const formData = new FormData();
        formData.append("file", timeFile);
        if (timeGroup.trim()) formData.append("group", timeGroup.trim().toUpperCase());

        try {
            const res = await apiFetch("/upload-timetable", { method: "POST", body: formData });
            if (res.ok) {
                setTimeStatus(`Successfully uploaded timetable ${timeFile.name}!`);
                setTimeFile(null);
                fetchTimetable();
                setTimeout(() => setTimeStatus(""), 4000);
            } else {
                setTimeStatus("Timetable upload failed.");
            }
        } catch (err) {
            console.error("Timetable upload error:", err);
            setTimeStatus("Error uploading timetable.");
        } finally {
            setIsTimeUploading(false);
        }
    };

    const handleUploadDeadlines = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!deadlineFile) return;

        setIsDeadlineUploading(true);
        setDeadlineStatus("Uploading deadlines CSV...");
        const formData = new FormData();
        formData.append("file", deadlineFile);

        try {
            const res = await apiFetch("/upload-deadlines", { method: "POST", body: formData });
            if (!res.ok) {
                const data = await res.json().catch(() => null);
                throw new Error(data?.detail || "Deadline upload failed.");
            }
            setDeadlineFile(null);
            await fetchDeadlines();
            setDeadlineStatus("Deadlines uploaded successfully.");
        } catch (err) {
            console.error("Deadline upload error:", err);
            setDeadlineStatus(err instanceof Error ? err.message : "Error uploading deadlines.");
        } finally {
            setIsDeadlineUploading(false);
        }
    };

    const handleDeleteDeadlines = async () => {
        if (!confirm("Delete the current department deadlines CSV?")) return;
        setDeadlineStatus("");
        try {
            const res = await apiFetch("/admin/deadlines", { method: "DELETE" });
            if (!res.ok) {
                const data = await res.json().catch(() => null);
                throw new Error(data?.detail || "Failed to delete deadlines.");
            }
            await fetchDeadlines();
            setDeadlineStatus("Deadlines deleted successfully.");
        } catch (err) {
            console.error("Deadline delete error:", err);
            setDeadlineStatus(err instanceof Error ? err.message : "Error deleting deadlines.");
        }
    };

    const handleDeleteTimetable = async (filename: string) => {
        if (!confirm(`Delete timetable payload "${filename}"?`)) return;
        try {
            const res = await apiFetch(`/admin/timetable/${filename}`, { method: "DELETE" });
            if (res.ok) {
                setTimetableFiles(prev => prev.filter(f => f.filename !== filename));
            } else {
                alert("Failed to delete timetable.");
            }
        } catch (err) {
            console.error("Timetable delete error:", err);
        }
    };

    // REQUESTS CRUD & STATUS UPDATE
    const handleAdminStatusUpdate = async (requestId: string, newStatus: StudentRequestStatus) => {
        const comments = adminReviewComments[requestId] || "";
        if (newStatus === "More Information Required" && !comments.trim()) {
            alert("Please provide remarks in the input box specifying what additional information is required from the student.");
            return;
        }

        setAdminActionLoading(requestId);
        try {
            const res = await apiFetch(`/requests/${requestId}/status`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: newStatus, comments: comments })
            });
            if (res.ok) {
                const updated = await res.json();
                setAdminRequests(prev => prev.map(r => r.id === requestId ? { ...r, ...updated } : r));
                setAdminReviewComments(prev => ({ ...prev, [requestId]: "" }));
            } else {
                alert("Failed to update request status.");
            }
        } catch (err) {
            console.error("Status update error:", err);
        } finally {
            setAdminActionLoading(null);
        }
    };

    const handleDeleteRequest = async (requestId: string, reqType: string) => {
        if (!confirm(`Are you sure you want to delete student request "${reqType}" (${requestId}) from the database?`)) return;
        try {
            const res = await apiFetch(`/requests/${requestId}`, { method: "DELETE" });
            if (res.ok) {
                setAdminRequests(prev => prev.filter(r => r.id !== requestId));
            } else {
                alert("Failed to delete request.");
            }
        } catch (err) {
            console.error("Request delete error:", err);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "Approved":
                return "bg-green-500/20 text-green-400 border border-green-500/40";
            case "Rejected":
                return "bg-red-500/20 text-red-400 border border-red-500/40";
            case "More Information Required":
                return "bg-amber-500/20 text-amber-400 border border-amber-500/40";
            case "Under Review":
            case "In Review":
                return "bg-sky-500/20 text-sky-400 border border-sky-500/40";
            default:
                return "bg-yellow-500/20 text-yellow-400 border border-yellow-500/40";
        }
    };

    if (isAdmin === null) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-background relative overflow-hidden">
                <div className="relative w-16 h-16">
                    <div className="absolute inset-0 border-4 border-primary/20 rounded-full" />
                    <div className="absolute inset-0 border-4 border-primary rounded-full border-t-transparent animate-spin" />
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col min-h-screen bg-background relative text-foreground">
            {/* Header */}
            <header className="flex items-center justify-between px-6 py-4 bg-[#0A0A12]/80 backdrop-blur-xl border-b border-white/10 shrink-0 relative z-10 shadow-lg">
                <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/20 text-primary border border-primary/30 shadow-[0_0_15px_rgba(0,229,255,0.2)]">
                        <span className="font-mono font-bold text-sm">AI</span>
                    </div>
                    <div>
                        <h1 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary leading-none">
                            AIDA Department Governance Portal
                        </h1>
                        <p className="text-xs text-muted-foreground mt-1 uppercase tracking-widest font-semibold">
                            Artificial Intelligence &amp; Machine Learning Administration
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <span className="text-xs px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/30 font-mono hidden md:inline">
                        Admin Privileges Active
                    </span>
                    <Link
                        href="/faculty"
                        className="text-xs px-3 py-1.5 rounded-lg bg-accent/10 text-accent hover:bg-accent/20 border border-accent/30 font-semibold transition-colors"
                    >
                        Faculty Portal
                    </Link>
                    <Link
                        href="/student"
                        className="text-xs px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-foreground border border-white/10 transition-colors"
                    >
                        Student Portal
                    </Link>
                    <Link
                        href="/"
                        className="text-xs px-3 py-1.5 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary border border-primary/40 font-bold transition-colors"
                    >
                        Core AI
                    </Link>
                </div>
            </header>

            {/* Main Content Area */}
            <main className="flex-1 p-4 md:p-8 max-w-7xl mx-auto w-full relative z-10 space-y-6">
                {/* Navigation Tabs Bar */}
                <div className="flex space-x-1.5 bg-black/60 border border-white/10 p-1.5 rounded-2xl w-full overflow-x-auto shadow-xl backdrop-blur-md">
                    {[
                        { id: "overview", label: "Overview & Analytics" },
                        { id: "students", label: "Students", count: students.length },
                        { id: "faculty", label: "Faculty", count: facultyList.length },
                        { id: "subjects", label: "Subjects", count: subjects.length },
                        { id: "timetable", label: "Timetables" },
                        { id: "notices", label: "Notices", count: notices.length },
                        { id: "events", label: "Events", count: events.length },
                        { id: "docs", label: "Knowledge Base (RAG)", count: documents.length },
                        { id: "requests", label: "Requests", count: adminRequests.length },
                        { id: "logs", label: "Telemetry Logs" }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as AdminTab)}
                            className={`px-3.5 py-2 text-xs font-bold rounded-xl transition-all whitespace-nowrap cursor-pointer flex items-center gap-1.5 ${activeTab === tab.id
                                ? "bg-primary/20 text-primary shadow-[0_0_12px_rgba(0,229,255,0.25)] border border-primary/40"
                                : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                }`}
                        >
                            <span>{tab.label}</span>
                            {tab.count !== undefined && (
                                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${activeTab === tab.id
                                    ? "bg-primary/30 text-primary"
                                    : "bg-white/10 text-muted-foreground"
                                    }`}>
                                    {tab.count}
                                </span>
                            )}
                        </button>
                    ))}
                </div>

                {/* =========================================================================
                    TAB: OVERVIEW & ANALYTICS
                   ========================================================================= */}
                {activeTab === "overview" && (
                    <div className="space-y-6">
                        {isOverviewLoading ? (
                            <div className="p-12 text-center text-sm text-muted-foreground">Loading department telemetry...</div>
                        ) : (
                            <>
                                {/* Top KPI Cards */}
                                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                                    <div className="glass-panel p-4 rounded-xl border border-white/10 space-y-1">
                                        <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Enrolled Students</span>
                                        <span className="block text-2xl font-bold text-primary font-mono">{overview?.students_count || students.length}</span>
                                        <span className="text-[10px] text-muted-foreground">AIML-A &amp; AIML-B Batches</span>
                                    </div>
                                    <div className="glass-panel p-4 rounded-xl border border-white/10 space-y-1">
                                        <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Faculty Staff</span>
                                        <span className="block text-2xl font-bold text-accent font-mono">{overview?.faculty_count || facultyList.length}</span>
                                        <span className="text-[10px] text-muted-foreground">Professors &amp; Instructors</span>
                                    </div>
                                    <div className="glass-panel p-4 rounded-xl border border-white/10 space-y-1">
                                        <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Pending Requests</span>
                                        <span className="block text-2xl font-bold text-amber-400 font-mono">{overview?.pending_requests_count || 0}</span>
                                        <span className="text-[10px] text-muted-foreground">Action Required</span>
                                    </div>
                                    <div className="glass-panel p-4 rounded-xl border border-white/10 space-y-1">
                                        <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Active Notices</span>
                                        <span className="block text-2xl font-bold text-cyan-400 font-mono">{overview?.active_notices_count || notices.length}</span>
                                        <span className="text-[10px] text-muted-foreground">Circulars Published</span>
                                    </div>
                                    <div className="glass-panel p-4 rounded-xl border border-white/10 space-y-1">
                                        <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Upcoming Events</span>
                                        <span className="block text-2xl font-bold text-purple-400 font-mono">{overview?.upcoming_events_count || events.length}</span>
                                        <span className="text-[10px] text-muted-foreground">Seminars &amp; Hackathons</span>
                                    </div>
                                    <div className="glass-panel p-4 rounded-xl border border-white/10 space-y-1">
                                        <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Knowledge Base</span>
                                        <span className="block text-2xl font-bold text-emerald-400 font-mono">{overview?.documents_count || documents.length}</span>
                                        <span className="text-[10px] text-muted-foreground">Indexed RAG Files</span>
                                    </div>
                                </div>

                                {/* Department Details & Sections Breakdown */}
                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                    <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
                                        <h3 className="text-base font-bold text-foreground">Section Distribution</h3>
                                        <p className="text-xs text-muted-foreground">Active AIML Semester 6 cohort enrollment across classroom cohorts.</p>
                                        <div className="space-y-3 text-xs">
                                            {overview?.students_by_section ? (
                                                Object.entries(overview.students_by_section).map(([sec, count]) => (
                                                    <div key={sec} className="flex items-center justify-between p-3 rounded-xl bg-black/40 border border-white/5">
                                                        <span className="font-bold text-primary font-mono">{sec}</span>
                                                        <span className="font-mono text-muted-foreground">{count} Students</span>
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="space-y-2">
                                                    <div className="flex items-center justify-between p-3 rounded-xl bg-black/40 border border-white/5">
                                                        <span className="font-bold text-primary font-mono">AIML-A</span>
                                                        <span className="font-mono text-muted-foreground">45 Students</span>
                                                    </div>
                                                    <div className="flex items-center justify-between p-3 rounded-xl bg-black/40 border border-white/5">
                                                        <span className="font-bold text-primary font-mono">AIML-B</span>
                                                        <span className="font-mono text-muted-foreground">45 Students</span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Upcoming Department Schedule */}
                                    <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4 lg:col-span-2">
                                        <div className="flex items-center justify-between">
                                            <h3 className="text-base font-bold text-foreground">Next Scheduled Department Events</h3>
                                            <button
                                                onClick={() => setActiveTab("events")}
                                                className="text-xs text-primary hover:underline font-semibold cursor-pointer"
                                            >
                                                Manage Events &rarr;
                                            </button>
                                        </div>
                                        <div className="space-y-3">
                                            {overview?.upcoming_events && overview.upcoming_events.length > 0 ? (
                                                overview.upcoming_events.map(ev => (
                                                    <div key={ev.id} className="p-3.5 rounded-xl bg-black/30 border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                                        <div className="space-y-0.5">
                                                            <span className="font-bold text-foreground text-sm">{ev.title}</span>
                                                            <div className="text-xs text-muted-foreground flex items-center gap-2">
                                                                <span className="text-accent">{ev.location}</span>
                                                                <span>•</span>
                                                                <span>{ev.organizer}</span>
                                                            </div>
                                                        </div>
                                                        <span className="text-xs font-mono text-purple-400 bg-purple-500/10 px-2.5 py-1 rounded-lg border border-purple-500/20 shrink-0">
                                                            {ev.date_time}
                                                        </span>
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="p-6 text-center text-xs text-muted-foreground">No upcoming events scheduled.</div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                )}

                {/* =========================================================================
                    TAB: STUDENTS MANAGEMENT
                   ========================================================================= */}
                {activeTab === "students" && (
                    <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-bold text-foreground">Enrolled Department Students</h2>
                                <p className="text-xs text-muted-foreground">
                                    Manage AIML student roster, cohort allocations, and academic records.
                                </p>
                            </div>
                            <div className="flex items-center gap-2 flex-wrap">
                                <select
                                    value={studentSectionFilter}
                                    onChange={e => setStudentSectionFilter(e.target.value)}
                                    className="px-3 py-1.5 bg-black/40 border border-white/10 rounded-xl text-xs text-foreground focus:outline-none focus:border-primary"
                                >
                                    <option value="all">All Sections</option>
                                    <option value="AIML-A">AIML-A</option>
                                    <option value="AIML-B">AIML-B</option>
                                </select>
                                <button
                                    onClick={() => {
                                        setEditingStudent(null);
                                        setStudentFormData({
                                            enrollment_no: "",
                                            full_name: "",
                                            email: "",
                                            section: "AIML-A",
                                            semester: 6,
                                            batch_year: "2023-2027",
                                            contact_number: ""
                                        });
                                        setShowStudentModal(true);
                                    }}
                                    className="px-4 py-1.5 rounded-xl text-xs font-bold bg-primary text-black hover:opacity-90 transition-opacity cursor-pointer"
                                >
                                    + Add Student
                                </button>
                            </div>
                        </div>

                        {/* Students Table */}
                        {isStudentsLoading ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">Loading student roster...</div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-xs border-collapse">
                                    <thead>
                                        <tr className="border-b border-white/10 text-muted-foreground font-semibold">
                                            <th className="py-3 px-3">Enrollment No</th>
                                            <th className="py-3 px-3">Full Name</th>
                                            <th className="py-3 px-3">Email</th>
                                            <th className="py-3 px-3">Section</th>
                                            <th className="py-3 px-3">Semester</th>
                                            <th className="py-3 px-3">Batch</th>
                                            <th className="py-3 px-3 text-right">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {students
                                            .filter(s => studentSectionFilter === "all" || s.section === studentSectionFilter)
                                            .map(s => (
                                                <tr key={s.id} className="hover:bg-white/[0.02] transition-colors">
                                                    <td className="py-3 px-3 font-mono font-bold text-primary">{s.enrollment_no}</td>
                                                    <td className="py-3 px-3 font-semibold text-foreground">{s.full_name}</td>
                                                    <td className="py-3 px-3 text-muted-foreground font-mono">{s.email}</td>
                                                    <td className="py-3 px-3">
                                                        <span className="px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 font-mono text-[11px]">
                                                            {s.section}
                                                        </span>
                                                    </td>
                                                    <td className="py-3 px-3">Sem {s.semester}</td>
                                                    <td className="py-3 px-3 text-muted-foreground">{s.batch_year}</td>
                                                    <td className="py-3 px-3 text-right space-x-2">
                                                        <button
                                                            onClick={() => {
                                                                setEditingStudent(s);
                                                                setStudentFormData({
                                                                    enrollment_no: s.enrollment_no,
                                                                    full_name: s.full_name,
                                                                    email: s.email,
                                                                    section: s.section,
                                                                    semester: s.semester,
                                                                    batch_year: s.batch_year || "2023-2027",
                                                                    contact_number: s.contact_number || ""
                                                                });
                                                                setShowStudentModal(true);
                                                            }}
                                                            className="text-xs text-primary hover:underline font-semibold cursor-pointer"
                                                        >
                                                            Edit
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteStudent(s.id, s.full_name)}
                                                            className="text-xs text-red-400 hover:underline font-semibold cursor-pointer"
                                                        >
                                                            Delete
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                {/* =========================================================================
                    TAB: FACULTY MANAGEMENT
                   ========================================================================= */}
                {activeTab === "faculty" && (
                    <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-bold text-foreground">Department Faculty Directory</h2>
                                <p className="text-xs text-muted-foreground">
                                    Manage teaching faculty, designations, course allocations, and consultation office hours.
                                </p>
                            </div>
                            <button
                                onClick={() => {
                                    setEditingFaculty(null);
                                    setFacultyFormData({
                                        name: "",
                                        designation: "Assistant Professor",
                                        email: "",
                                        contact_info: "",
                                        specialization: "",
                                        subjects_handled: "AI401",
                                        availability: "Mon & Wed: 2:00 PM - 4:00 PM"
                                    });
                                    setShowFacultyModal(true);
                                }}
                                className="px-4 py-1.5 rounded-xl text-xs font-bold bg-accent text-black hover:opacity-90 transition-opacity cursor-pointer self-start sm:self-auto"
                            >
                                + Add Faculty
                            </button>
                        </div>

                        {/* Faculty Grid */}
                        {isFacultyLoading ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">Loading faculty directory...</div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {facultyList.map(f => (
                                    <div key={f.id} className="p-4 rounded-xl bg-black/40 border border-white/10 space-y-3 flex flex-col justify-between hover:border-accent/40 transition-colors">
                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between gap-2">
                                                <h3 className="font-bold text-foreground text-sm">{f.name}</h3>
                                                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/30">
                                                    {f.designation}
                                                </span>
                                            </div>
                                            <p className="text-xs text-muted-foreground font-mono">{f.email}</p>
                                            <p className="text-xs text-foreground/80"><strong className="text-accent">Spec:</strong> {f.specialization}</p>
                                            <p className="text-xs text-muted-foreground"><strong className="text-foreground">Courses:</strong> {f.subjects_handled?.join(", ") || "None"}</p>
                                            <p className="text-xs text-muted-foreground"><strong className="text-foreground">Hours:</strong> {f.availability || "By appointment"}</p>
                                        </div>

                                        <div className="pt-3 border-t border-white/5 flex items-center justify-end gap-3 text-xs">
                                            <button
                                                onClick={() => {
                                                    setEditingFaculty(f);
                                                    setFacultyFormData({
                                                        name: f.name,
                                                        designation: f.designation,
                                                        email: f.email,
                                                        contact_info: f.contact_info || "",
                                                        specialization: f.specialization || "",
                                                        subjects_handled: f.subjects_handled?.join(", ") || "",
                                                        availability: f.availability || ""
                                                    });
                                                    setShowFacultyModal(true);
                                                }}
                                                className="text-accent hover:underline font-semibold cursor-pointer"
                                            >
                                                Edit
                                            </button>
                                            <button
                                                onClick={() => handleDeleteFaculty(f.id, f.name)}
                                                className="text-red-400 hover:underline font-semibold cursor-pointer"
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* =========================================================================
                    TAB: SUBJECTS CATALOG
                   ========================================================================= */}
                {activeTab === "subjects" && (
                    <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-bold text-foreground">Academic Subjects Catalog</h2>
                                <p className="text-xs text-muted-foreground">
                                    Curriculum course codes, credit schemes, and syllabus assignments.
                                </p>
                            </div>
                            <button
                                onClick={() => {
                                    setEditingSubject(null);
                                    setSubjectFormData({
                                        id: "",
                                        name: "",
                                        semester: 6,
                                        credits: 4,
                                        description: ""
                                    });
                                    setShowSubjectModal(true);
                                }}
                                className="px-4 py-1.5 rounded-xl text-xs font-bold bg-primary text-black hover:opacity-90 transition-opacity cursor-pointer self-start sm:self-auto"
                            >
                                + Add Subject
                            </button>
                        </div>

                        {/* Subjects Grid */}
                        {isSubjectsLoading ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">Loading curriculum catalog...</div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {subjects.map(s => (
                                    <div key={s.id} className="p-4 rounded-xl bg-black/40 border border-white/10 space-y-2 flex flex-col justify-between hover:border-primary/40 transition-colors">
                                        <div className="space-y-1">
                                            <div className="flex items-center justify-between">
                                                <span className="font-mono font-bold text-primary text-sm">{s.id}</span>
                                                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 text-muted-foreground">
                                                    {s.credits} Credits • Sem {s.semester}
                                                </span>
                                            </div>
                                            <h3 className="font-semibold text-foreground text-sm">{s.name}</h3>
                                            <p className="text-xs text-muted-foreground line-clamp-2">{s.description}</p>
                                        </div>

                                        <div className="pt-2 border-t border-white/5 flex items-center justify-end gap-3 text-xs">
                                            <button
                                                onClick={() => {
                                                    setEditingSubject(s);
                                                    setSubjectFormData({
                                                        id: s.id,
                                                        name: s.name,
                                                        semester: s.semester,
                                                        credits: s.credits,
                                                        description: s.description || ""
                                                    });
                                                    setShowSubjectModal(true);
                                                }}
                                                className="text-primary hover:underline font-semibold cursor-pointer"
                                            >
                                                Edit
                                            </button>
                                            <button
                                                onClick={() => handleDeleteSubject(s.id, s.name)}
                                                className="text-red-400 hover:underline font-semibold cursor-pointer"
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* =========================================================================
                    TAB: TIMETABLES & SCHEDULE SYNC
                   ========================================================================= */}
                {activeTab === "timetable" && (
                    <div className="space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Timetable Upload Form */}
                        <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4 h-fit">
                            <h2 className="text-base font-bold text-foreground">Upload Timetable CSV</h2>
                            <p className="text-xs text-muted-foreground">
                                Upload section timetables (<code>timetable_aiml_a.csv</code>).
                            </p>
                            {timeStatus && (
                                <div className="p-3 text-xs text-primary bg-primary/10 rounded-lg border border-primary/20">
                                    {timeStatus}
                                </div>
                            )}
                            <form onSubmit={handleUploadTimetable} className="space-y-4">
                                <div>
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Section / Group</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. AIML-A"
                                        value={timeGroup}
                                        onChange={e => setTimeGroup(e.target.value)}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-xs text-foreground focus:outline-none focus:border-primary"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-bold text-muted-foreground uppercase">CSV File</label>
                                    <input
                                        type="file"
                                        accept=".csv"
                                        required
                                        onChange={e => setTimeFile(e.target.files?.[0] || null)}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-xs text-foreground file:mr-3 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-primary/20 file:text-primary cursor-pointer"
                                    />
                                </div>
                                <button
                                    type="submit"
                                    disabled={isTimeUploading || !timeFile}
                                    className="w-full py-2.5 rounded-xl text-xs font-bold bg-secondary text-white hover:opacity-90 transition-opacity disabled:opacity-40 cursor-pointer"
                                >
                                    {isTimeUploading ? "Uploading..." : "Sync Timetable CSV"}
                                </button>
                            </form>
                        </div>

                        {/* Timetable Files List */}
                        <div className="lg:col-span-2 space-y-4">
                            <h2 className="text-base font-bold text-foreground">Active Section Timetables</h2>
                            {isTimetableLoading ? (
                                <div className="p-8 text-center text-sm text-muted-foreground">Loading timetables...</div>
                            ) : timetableFiles.length === 0 ? (
                                <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                    No timetable CSV payloads found. Upload a timetable using the form on the left.
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {timetableFiles.map(tf => (
                                        <div key={tf.filename} className="glass-panel p-4 rounded-xl border border-white/10 space-y-2">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-mono font-bold text-primary text-xs">{tf.filename}</span>
                                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                                                        {tf.group || "Shared"}
                                                    </span>
                                                    <span className="text-xs text-muted-foreground">({tf.row_count} slots)</span>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <button
                                                        onClick={() => setExpandedGroup(expandedGroup === tf.filename ? null : tf.filename)}
                                                        className="text-xs text-primary hover:underline font-semibold cursor-pointer"
                                                    >
                                                        {expandedGroup === tf.filename ? "Hide Rows" : "Preview"}
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeleteTimetable(tf.filename)}
                                                        className="text-xs text-red-400 hover:underline font-semibold cursor-pointer"
                                                    >
                                                        Delete
                                                    </button>
                                                </div>
                                            </div>

                                            {expandedGroup === tf.filename && (
                                                <div className="mt-3 overflow-x-auto max-h-60 border-t border-white/5 pt-2">
                                                    <table className="w-full text-[11px] text-left">
                                                        <thead>
                                                            <tr className="border-b border-white/10 text-muted-foreground">
                                                                {tf.headers.map(h => <th key={h} className="p-1.5">{h}</th>)}
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-white/5 font-mono">
                                                            {tf.rows.slice(0, 10).map((r, i) => (
                                                                <tr key={i}>
                                                                    {tf.headers.map(h => <td key={h} className="p-1.5">{r[h]}</td>)}
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                        <section className="lg:col-span-3 grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4 h-fit">
                                <h2 className="text-base font-bold text-foreground">Upload Assignment Deadlines</h2>
                                <p className="text-xs text-muted-foreground">
                                    Upload a CSV with course_id, course_name, title, type, due_date, and description columns.
                                </p>
                                {deadlineStatus && (
                                    <div role="status" className="p-3 text-xs text-primary bg-primary/10 rounded-lg border border-primary/20">
                                        {deadlineStatus}
                                    </div>
                                )}
                                <form onSubmit={handleUploadDeadlines} className="space-y-4">
                                    <input
                                        type="file"
                                        accept=".csv,text/csv"
                                        required
                                        onChange={e => setDeadlineFile(e.target.files?.[0] || null)}
                                        className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-xs text-foreground file:mr-3 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-primary/20 file:text-primary cursor-pointer"
                                    />
                                    <button
                                        type="submit"
                                        disabled={isDeadlineUploading || !deadlineFile}
                                        className="w-full py-2.5 rounded-xl text-xs font-bold bg-primary text-black hover:opacity-90 transition-opacity disabled:opacity-40 cursor-pointer"
                                    >
                                        {isDeadlineUploading ? "Uploading..." : "Upload Deadlines CSV"}
                                    </button>
                                </form>
                            </div>

                            <div className="lg:col-span-2 space-y-4">
                                <div className="flex items-center justify-between gap-3">
                                    <h2 className="text-base font-bold text-foreground">Current Deadlines</h2>
                                    {deadlineExists && (
                                        <button
                                            onClick={handleDeleteDeadlines}
                                            className="text-xs text-red-400 hover:underline font-semibold cursor-pointer"
                                        >
                                            Delete CSV
                                        </button>
                                    )}
                                </div>
                                {isDeadlineLoading ? (
                                    <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                        Loading deadlines...
                                    </div>
                                ) : !deadlineExists ? (
                                    <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                        No deadlines CSV has been uploaded.
                                    </div>
                                ) : deadlineRows.length === 0 ? (
                                    <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                        The deadlines CSV is empty or has no rows.
                                    </div>
                                ) : (
                                    <div className="glass-panel rounded-2xl border border-white/10 overflow-x-auto">
                                        <table className="w-full text-left text-xs">
                                            <thead className="bg-white/5 text-muted-foreground uppercase">
                                                <tr>
                                                    {deadlineHeaders.map(header => (
                                                        <th key={header} className="px-3 py-3 whitespace-nowrap">{header.replaceAll("_", " ")}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-white/5">
                                                {deadlineRows.map((row, index) => (
                                                    <tr key={`${row.course_id}-${row.title}-${index}`}>
                                                        {deadlineHeaders.map(header => (
                                                            <td key={header} className="px-3 py-3 text-foreground min-w-32">{row[header] || "—"}</td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </section>
                    </div>
                )}

                {/* =========================================================================
                    TAB: NOTICES & CIRCULARS
                   ========================================================================= */}
                {activeTab === "notices" && (
                    <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-bold text-foreground">Department Notices &amp; Circulars</h2>
                                <p className="text-xs text-muted-foreground">
                                    Broadcast official department announcements indexed by the AIDA Notices Agent.
                                </p>
                            </div>
                            <button
                                onClick={() => {
                                    setEditingNotice(null);
                                    setNoticeFormData({ title: "", content: "", category: "Academic", is_pinned: false });
                                    setShowNoticeModal(true);
                                }}
                                className="px-4 py-1.5 rounded-xl text-xs font-bold bg-primary text-black hover:opacity-90 transition-opacity cursor-pointer self-start sm:self-auto"
                            >
                                + Publish Notice
                            </button>
                        </div>

                        {/* Notices List */}
                        {isNoticesLoading ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">Loading notices...</div>
                        ) : (
                            <div className="space-y-3">
                                {notices.map(n => (
                                    <div key={n.id} className="p-4 rounded-xl bg-black/40 border border-white/10 space-y-2 hover:border-primary/40 transition-colors">
                                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 uppercase">
                                                    {n.category}
                                                </span>
                                                {n.is_pinned && (
                                                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40">
                                                        PINNED
                                                    </span>
                                                )}
                                                <span className="font-bold text-foreground text-sm">{n.title}</span>
                                            </div>
                                            <div className="flex items-center gap-3 text-xs">
                                                <span className="text-muted-foreground">{new Date(n.date).toLocaleDateString()}</span>
                                                <button
                                                    onClick={() => {
                                                        setEditingNotice(n);
                                                        setNoticeFormData({
                                                            title: n.title,
                                                            content: n.content,
                                                            category: n.category,
                                                            is_pinned: !!n.is_pinned
                                                        });
                                                        setShowNoticeModal(true);
                                                    }}
                                                    className="text-primary hover:underline font-semibold cursor-pointer"
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    onClick={() => handleDeleteNotice(n.id, n.title)}
                                                    className="text-red-400 hover:underline font-semibold cursor-pointer"
                                                >
                                                    Delete
                                                </button>
                                            </div>
                                        </div>
                                        <p className="text-xs text-foreground/80 whitespace-pre-wrap">{n.content}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* =========================================================================
                    TAB: EVENTS & WORKSHOPS
                   ========================================================================= */}
                {activeTab === "events" && (
                    <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-bold text-foreground">Department Events &amp; Workshops</h2>
                                <p className="text-xs text-muted-foreground">
                                    Manage upcoming symposiums, seminars, and technical hackathons.
                                </p>
                            </div>
                            <button
                                onClick={() => {
                                    setEditingEvent(null);
                                    setEventFormData({
                                        title: "",
                                        description: "",
                                        date_time: "",
                                        location: "",
                                        organizer: "AIML Department"
                                    });
                                    setShowEventModal(true);
                                }}
                                className="px-4 py-1.5 rounded-xl text-xs font-bold bg-accent text-black hover:opacity-90 transition-opacity cursor-pointer self-start sm:self-auto"
                            >
                                + Schedule Event
                            </button>
                        </div>

                        {/* Events Grid */}
                        {isEventsLoading ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">Loading events...</div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {events.map(ev => (
                                    <div key={ev.id} className="p-5 rounded-xl bg-black/40 border border-white/10 space-y-3 flex flex-col justify-between hover:border-accent/40 transition-colors">
                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between gap-2">
                                                <h3 className="font-bold text-foreground text-sm">{ev.title}</h3>
                                                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
                                                    {ev.date_time}
                                                </span>
                                            </div>
                                            <p className="text-xs text-foreground/80 line-clamp-3">{ev.description}</p>
                                            <div className="text-xs text-muted-foreground space-y-0.5 pt-1">
                                                <p><strong className="text-accent">Venue:</strong> {ev.location}</p>
                                                <p><strong className="text-foreground">Organizer:</strong> {ev.organizer}</p>
                                            </div>
                                        </div>

                                        <div className="pt-2 border-t border-white/5 flex items-center justify-end gap-3 text-xs">
                                            <button
                                                onClick={() => {
                                                    setEditingEvent(ev);
                                                    setEventFormData({
                                                        title: ev.title,
                                                        description: ev.description,
                                                        date_time: ev.date_time,
                                                        location: ev.location,
                                                        organizer: ev.organizer
                                                    });
                                                    setShowEventModal(true);
                                                }}
                                                className="text-accent hover:underline font-semibold cursor-pointer"
                                            >
                                                Edit
                                            </button>
                                            <button
                                                onClick={() => handleDeleteEvent(ev.id, ev.title)}
                                                className="text-red-400 hover:underline font-semibold cursor-pointer"
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* =========================================================================
                    TAB: DOCUMENTS & RAG KNOWLEDGE BASE
                   ========================================================================= */}
                {activeTab === "docs" && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Doc Upload Form & Index Rebuild */}
                        <div className="space-y-6">
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
                                <h2 className="text-base font-bold text-foreground">Ingest Knowledge Base Document</h2>
                                <p className="text-xs text-muted-foreground">
                                    Upload official syllabus, project rules, and lab manuals into the RAG vector engine.
                                </p>
                                {docStatus && (
                                    <div className="p-3 text-xs text-primary bg-primary/10 rounded-lg border border-primary/20">
                                        {docStatus}
                                    </div>
                                )}
                                <form onSubmit={handleUploadDoc} className="space-y-4">
                                    <div>
                                        <label className="text-xs font-bold text-muted-foreground uppercase">Course ID</label>
                                        <select
                                            value={docCourse}
                                            onChange={e => setDocCourse(e.target.value)}
                                            className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-xs text-foreground focus:outline-none focus:border-primary"
                                        >
                                            <option value="AI401">AI401 – Machine Learning Foundations</option>
                                            <option value="AI402">AI402 – Deep Learning &amp; Neural Networks</option>
                                            <option value="AI403">AI403 – Natural Language Processing</option>
                                            <option value="AI404">AI404 – Computer Vision</option>
                                            <option value="AI405">AI405 – Reinforcement Learning &amp; Robotics</option>
                                            <option value="AI406">AI406 – AI Ethics &amp; Governance</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs font-bold text-muted-foreground uppercase">Category</label>
                                        <select
                                            value={docCategory}
                                            onChange={e => setDocCategory(e.target.value)}
                                            className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-xs text-foreground focus:outline-none focus:border-primary"
                                        >
                                            <option value="AIML Syllabus">Curriculum &amp; Syllabus</option>
                                            <option value="Lab Manuals">Lab Manuals &amp; GPU Rules</option>
                                            <option value="Project Guidelines">Capstone Project Guidelines</option>
                                            <option value="Academic Regulations">Academic Regulations</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-xs font-bold text-muted-foreground uppercase">Select File (.pdf, .md, .txt)</label>
                                        <input
                                            type="file"
                                            accept=".pdf,.md,.txt,.docx"
                                            required
                                            onChange={e => setDocFile(e.target.files?.[0] || null)}
                                            className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-xs text-foreground file:mr-3 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-primary/20 file:text-primary cursor-pointer"
                                        />
                                    </div>
                                    <button
                                        type="submit"
                                        disabled={isDocUploading || !docFile}
                                        className="w-full py-2.5 rounded-xl text-xs font-bold bg-primary text-black hover:opacity-90 transition-opacity disabled:opacity-40 cursor-pointer"
                                    >
                                        {isDocUploading ? "Vectorizing..." : "Upload Document"}
                                    </button>
                                </form>
                            </div>

                            {/* Rebuild Search Index */}
                            <div className="glass-panel p-6 rounded-2xl border border-red-500/20 bg-red-500/[0.02] space-y-3">
                                <h3 className="text-sm font-bold text-red-400">Reconstruct Search Engine Index</h3>
                                <p className="text-xs text-muted-foreground">
                                    Re-chunks and re-embeds all files in <code>data/docs</code> using FAISS. Run this after bulk deletions.
                                </p>
                                {indexStatus && (
                                    <div className="p-2.5 text-xs text-red-300 bg-red-500/10 rounded-lg border border-red-500/30">
                                        {indexStatus}
                                    </div>
                                )}
                                <button
                                    onClick={handleRebuildIndex}
                                    disabled={isIndexing}
                                    className="w-full py-2.5 rounded-xl text-xs font-bold bg-red-600/80 hover:bg-red-500 text-white transition-colors disabled:opacity-40 cursor-pointer"
                                >
                                    {isIndexing ? "Rebuilding Index..." : "Rebuild Search Index"}
                                </button>
                            </div>
                        </div>

                        {/* Document Directory */}
                        <div className="lg:col-span-2 space-y-4">
                            <h2 className="text-base font-bold text-foreground">Vectorized Knowledge Base Directory</h2>
                            {isDocsLoading ? (
                                <div className="p-8 text-center text-sm text-muted-foreground">Loading knowledge base files...</div>
                            ) : documents.length === 0 ? (
                                <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                    No documents indexed yet.
                                </div>
                            ) : (
                                <div className="space-y-2.5">
                                    {documents.map((doc, idx) => (
                                        <div
                                            key={idx}
                                            className="glass-panel p-4 rounded-xl border border-white/10 flex items-center justify-between gap-3 hover:border-primary/40 transition-colors"
                                        >
                                            <div className="space-y-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="font-bold text-foreground text-sm truncate">{doc.name}</span>
                                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-muted-foreground border border-white/5">
                                                        {(doc.size / 1024).toFixed(1)} KB
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <span className="text-primary font-semibold">{doc.category}</span>
                                                    {doc.course && (
                                                        <>
                                                            <span>•</span>
                                                            <span className="font-mono text-accent">{doc.course}</span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-3 shrink-0">
                                                <button
                                                    onClick={() => handleViewDoc(doc.name)}
                                                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 hover:bg-white/10 text-foreground transition-colors border border-white/10 cursor-pointer"
                                                >
                                                    Preview
                                                </button>
                                                <button
                                                    onClick={() => handleDeleteDoc(doc.name)}
                                                    className="text-xs text-red-400 hover:underline font-semibold cursor-pointer"
                                                >
                                                    Delete
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* =========================================================================
                    TAB: STUDENT REQUESTS & HUMAN APPROVAL
                   ========================================================================= */}
                {activeTab === "requests" && (
                    <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-bold text-foreground">Student Requests &amp; Human Approvals Queue</h2>
                                <p className="text-xs text-muted-foreground">
                                    Review academic and administrative requests submitted by students. Human review required for approval or rejection.
                                </p>
                            </div>
                            <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="text-xs text-muted-foreground mr-1">Filter:</span>
                                {["all", "pending", "under review", "more information required", "approved", "rejected"].map(filter => (
                                    <button
                                        key={filter}
                                        onClick={() => setAdminRequestFilter(filter)}
                                        className={`px-3 py-1 rounded-full text-xs capitalize transition-colors cursor-pointer ${adminRequestFilter === filter
                                            ? "bg-amber-500/20 text-amber-400 border border-amber-500/40 font-bold"
                                            : "bg-white/5 text-muted-foreground hover:text-foreground border border-white/5"
                                            }`}
                                    >
                                        {filter === "more information required" ? "More Info Req." : filter}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {isAdminRequestsLoading ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">Loading requests...</div>
                        ) : adminRequests.length === 0 ? (
                            <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                No requests found.
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {adminRequests
                                    .filter(r => {
                                        if (adminRequestFilter === "all") return true;
                                        const st = r.status.toLowerCase();
                                        if (adminRequestFilter === "under review") return st === "under review" || st === "in review";
                                        return st === adminRequestFilter.toLowerCase();
                                    })
                                    .map(req => {
                                        const hasHistory = req.history && req.history.length > 0;
                                        const isHistoryOpen = !!adminExpandedHistory[req.id];

                                        return (
                                            <div
                                                key={req.id}
                                                className="glass-panel p-5 rounded-xl border border-white/10 space-y-3.5 hover:border-amber-500/30 transition-colors"
                                            >
                                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                                    <div className="flex items-center gap-2.5 flex-wrap">
                                                        <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${getStatusBadge(req.status)}`}>
                                                            {req.status}
                                                        </span>
                                                        <span className="font-bold text-foreground text-sm">{req.request_type}</span>
                                                        {req.students && (
                                                            <span className="text-xs text-muted-foreground font-mono">
                                                                ({req.students.full_name} • {req.students.enrollment_no} • {req.students.section})
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-3">
                                                        <span className="text-xs text-muted-foreground">
                                                            Submitted: {new Date(req.created_at).toLocaleDateString()}
                                                        </span>
                                                        <button
                                                            onClick={() => handleDeleteRequest(req.id, req.request_type)}
                                                            className="text-xs text-red-400 hover:underline font-semibold cursor-pointer"
                                                        >
                                                            Delete
                                                        </button>
                                                    </div>
                                                </div>

                                                <p className="text-sm text-foreground/90 bg-black/30 p-3 rounded-lg border border-white/5 whitespace-pre-wrap">
                                                    {req.description}
                                                </p>

                                                {req.comments && (
                                                    <div className="text-xs text-muted-foreground bg-amber-500/5 p-2.5 rounded-lg border border-amber-500/20">
                                                        <strong className="text-amber-400 font-semibold">Latest Remark: </strong>
                                                        {req.comments}
                                                    </div>
                                                )}

                                                {/* Human Approval Controls */}
                                                <div className="pt-2 space-y-2 border-t border-white/5">
                                                    <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center justify-between">
                                                        <input
                                                            type="text"
                                                            placeholder="Add administrator review remarks (required when requesting more info)..."
                                                            value={adminReviewComments[req.id] || ""}
                                                            onChange={e => setAdminReviewComments(prev => ({ ...prev, [req.id]: e.target.value }))}
                                                            className="flex-1 px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:border-amber-400"
                                                        />
                                                        <div className="flex gap-1.5 shrink-0 flex-wrap">
                                                            <button
                                                                onClick={() => handleAdminStatusUpdate(req.id, "Approved")}
                                                                disabled={adminActionLoading === req.id || req.status === "Approved"}
                                                                className="px-3 py-1.5 rounded-lg text-xs font-bold bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/40 transition-colors disabled:opacity-40 cursor-pointer"
                                                            >
                                                                Approve
                                                            </button>
                                                            <button
                                                                onClick={() => handleAdminStatusUpdate(req.id, "Rejected")}
                                                                disabled={adminActionLoading === req.id || req.status === "Rejected"}
                                                                className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/40 transition-colors disabled:opacity-40 cursor-pointer"
                                                            >
                                                                Reject
                                                            </button>
                                                            <button
                                                                onClick={() => handleAdminStatusUpdate(req.id, "More Information Required")}
                                                                disabled={adminActionLoading === req.id || req.status === "More Information Required"}
                                                                className="px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 border border-amber-500/40 transition-colors disabled:opacity-40 cursor-pointer"
                                                            >
                                                                Request Info
                                                            </button>
                                                            <button
                                                                onClick={() => handleAdminStatusUpdate(req.id, "Under Review")}
                                                                disabled={adminActionLoading === req.id || req.status === "Under Review"}
                                                                className="px-3 py-1.5 rounded-lg text-xs font-bold bg-sky-500/20 hover:bg-sky-500/30 text-sky-400 border border-sky-500/40 transition-colors disabled:opacity-40 cursor-pointer"
                                                            >
                                                                Under Review
                                                            </button>
                                                        </div>
                                                    </div>

                                                    {/* Audit Timeline / History */}
                                                    {hasHistory && (
                                                        <div className="pt-2 border-t border-white/5">
                                                            <button
                                                                onClick={() => setAdminExpandedHistory(prev => ({ ...prev, [req.id]: !prev[req.id] }))}
                                                                className="text-xs text-muted-foreground hover:text-amber-400 transition-colors flex items-center gap-1 cursor-pointer font-medium"
                                                            >
                                                                <span>{isHistoryOpen ? "Hide" : "View"} Audit History ({req.history?.length})</span>
                                                            </button>

                                                            {isHistoryOpen && (
                                                                <div className="mt-2.5 space-y-2 pl-3 border-l-2 border-amber-500/40">
                                                                    {req.history?.map((item, idx) => (
                                                                        <div key={idx} className="text-xs space-y-0.5">
                                                                            <div className="flex items-center gap-2">
                                                                                <span className="font-semibold text-foreground">{item.action}</span>
                                                                                <span className="text-muted-foreground">•</span>
                                                                                <span className="text-amber-400 font-mono text-[11px]">
                                                                                    {item.actor_name || "Staff"} ({item.actor_role || "User"})
                                                                                </span>
                                                                                <span className="text-muted-foreground text-[10px]">
                                                                                    {new Date(item.timestamp).toLocaleString()}
                                                                                </span>
                                                                            </div>
                                                                            {item.comments && (
                                                                                <p className="text-muted-foreground italic pl-2 text-[11px]">
                                                                                    &quot;{item.comments}&quot;
                                                                                </p>
                                                                            )}
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        );
                                    })}
                            </div>
                        )}
                    </div>
                )}

                {/* =========================================================================
                    TAB: TELEMETRY LOGS
                   ========================================================================= */}
                {activeTab === "logs" && (
                    <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <h2 className="text-lg font-bold text-foreground">AIDA Core AI Telemetry Logs</h2>
                                <p className="text-xs text-muted-foreground">
                                    Real-time LangGraph query routing, intent classification, and latency telemetry.
                                </p>
                            </div>
                            <button
                                onClick={fetchLogs}
                                className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-white/5 hover:bg-white/10 text-foreground border border-white/10 transition-colors cursor-pointer"
                            >
                                Refresh Logs
                            </button>
                        </div>

                        {isLogsLoading ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">Fetching telemetry logs...</div>
                        ) : logs.length === 0 ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">No telemetry logs recorded yet.</div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-xs border-collapse">
                                    <thead>
                                        <tr className="border-b border-white/10 text-muted-foreground font-semibold">
                                            <th className="py-3 px-3">Timestamp</th>
                                            <th className="py-3 px-3">User Query</th>
                                            <th className="py-3 px-3">Routed Intent</th>
                                            <th className="py-3 px-3 text-right">Latency</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {logs.slice(0, 50).map(log => (
                                            <tr key={log.id} className="hover:bg-white/[0.02]">
                                                <td className="py-3 px-3 text-muted-foreground font-mono">
                                                    {new Date(log.created_at).toLocaleTimeString()}
                                                </td>
                                                <td className="py-3 px-3 text-foreground font-medium">{log.query}</td>
                                                <td className="py-3 px-3">
                                                    <span className="px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 font-mono text-[11px]">
                                                        {log.intent}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-3 text-right font-mono text-muted-foreground">
                                                    {log.latency_ms} ms
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}
            </main>

            {/* =========================================================================
                MODALS FOR CREATE & EDIT
               ========================================================================= */}

            {/* STUDENT MODAL */}
            {showStudentModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
                    <div className="glass-panel p-6 rounded-2xl border border-white/20 w-full max-w-lg space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-base font-bold text-foreground">
                                {editingStudent ? `Edit Student: ${editingStudent.full_name}` : "Register New Student"}
                            </h3>
                            <button onClick={() => setShowStudentModal(false)} className="text-muted-foreground hover:text-foreground text-sm">✕</button>
                        </div>
                        <form onSubmit={handleSaveStudent} className="space-y-3 text-xs">
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Enrollment No</label>
                                    <input
                                        type="text"
                                        required
                                        disabled={!!editingStudent}
                                        value={studentFormData.enrollment_no}
                                        onChange={e => setStudentFormData({ ...studentFormData, enrollment_no: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary disabled:opacity-50"
                                    />
                                </div>
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Full Name</label>
                                    <input
                                        type="text"
                                        required
                                        value={studentFormData.full_name}
                                        onChange={e => setStudentFormData({ ...studentFormData, full_name: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Email</label>
                                    <input
                                        type="email"
                                        required
                                        value={studentFormData.email}
                                        onChange={e => setStudentFormData({ ...studentFormData, email: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                    />
                                </div>
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Section</label>
                                    <select
                                        value={studentFormData.section}
                                        onChange={e => setStudentFormData({ ...studentFormData, section: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                    >
                                        <option value="AIML-A">AIML-A</option>
                                        <option value="AIML-B">AIML-B</option>
                                    </select>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Semester</label>
                                    <input
                                        type="number"
                                        min={1}
                                        max={8}
                                        value={studentFormData.semester}
                                        onChange={e => setStudentFormData({ ...studentFormData, semester: parseInt(e.target.value) || 6 })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                    />
                                </div>
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Batch Year</label>
                                    <input
                                        type="text"
                                        value={studentFormData.batch_year}
                                        onChange={e => setStudentFormData({ ...studentFormData, batch_year: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="font-bold text-muted-foreground uppercase">Contact Number</label>
                                <input
                                    type="text"
                                    value={studentFormData.contact_number}
                                    onChange={e => setStudentFormData({ ...studentFormData, contact_number: e.target.value })}
                                    className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                />
                            </div>
                            <div className="flex justify-end gap-2 pt-3">
                                <button
                                    type="button"
                                    onClick={() => setShowStudentModal(false)}
                                    className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-muted-foreground transition-colors cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-5 py-2 rounded-xl font-bold bg-primary text-black hover:opacity-90 transition-opacity cursor-pointer"
                                >
                                    Save Student
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* FACULTY MODAL */}
            {showFacultyModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
                    <div className="glass-panel p-6 rounded-2xl border border-white/20 w-full max-w-lg space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-base font-bold text-foreground">
                                {editingFaculty ? `Edit Faculty: ${editingFaculty.name}` : "Add Department Faculty"}
                            </h3>
                            <button onClick={() => setShowFacultyModal(false)} className="text-muted-foreground hover:text-foreground text-sm">✕</button>
                        </div>
                        <form onSubmit={handleSaveFaculty} className="space-y-3 text-xs">
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Full Name</label>
                                    <input
                                        type="text"
                                        required
                                        value={facultyFormData.name}
                                        onChange={e => setFacultyFormData({ ...facultyFormData, name: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                    />
                                </div>
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Designation</label>
                                    <input
                                        type="text"
                                        required
                                        value={facultyFormData.designation}
                                        onChange={e => setFacultyFormData({ ...facultyFormData, designation: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Email</label>
                                    <input
                                        type="email"
                                        required
                                        value={facultyFormData.email}
                                        onChange={e => setFacultyFormData({ ...facultyFormData, email: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                    />
                                </div>
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Cabin / Contact</label>
                                    <input
                                        type="text"
                                        value={facultyFormData.contact_info}
                                        onChange={e => setFacultyFormData({ ...facultyFormData, contact_info: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="font-bold text-muted-foreground uppercase">Specialization</label>
                                <input
                                    type="text"
                                    value={facultyFormData.specialization}
                                    onChange={e => setFacultyFormData({ ...facultyFormData, specialization: e.target.value })}
                                    className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                />
                            </div>
                            <div>
                                <label className="font-bold text-muted-foreground uppercase">Subjects Handled (comma-separated)</label>
                                <input
                                    type="text"
                                    value={facultyFormData.subjects_handled}
                                    onChange={e => setFacultyFormData({ ...facultyFormData, subjects_handled: e.target.value })}
                                    className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                />
                            </div>
                            <div>
                                <label className="font-bold text-muted-foreground uppercase">Consultation Availability</label>
                                <input
                                    type="text"
                                    value={facultyFormData.availability}
                                    onChange={e => setFacultyFormData({ ...facultyFormData, availability: e.target.value })}
                                    className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                />
                            </div>
                            <div className="flex justify-end gap-2 pt-3">
                                <button
                                    type="button"
                                    onClick={() => setShowFacultyModal(false)}
                                    className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-muted-foreground transition-colors cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-5 py-2 rounded-xl font-bold bg-accent text-black hover:opacity-90 transition-opacity cursor-pointer"
                                >
                                    Save Faculty
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* SUBJECT MODAL */}
            {showSubjectModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
                    <div className="glass-panel p-6 rounded-2xl border border-white/20 w-full max-w-lg space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-base font-bold text-foreground">
                                {editingSubject ? `Edit Subject: ${editingSubject.id}` : "Add Academic Subject"}
                            </h3>
                            <button onClick={() => setShowSubjectModal(false)} className="text-muted-foreground hover:text-foreground text-sm">✕</button>
                        </div>
                        <form onSubmit={handleSaveSubject} className="space-y-3 text-xs">
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Subject Code</label>
                                    <input
                                        type="text"
                                        required
                                        disabled={!!editingSubject}
                                        value={subjectFormData.id}
                                        onChange={e => setSubjectFormData({ ...subjectFormData, id: e.target.value.toUpperCase() })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary disabled:opacity-50"
                                    />
                                </div>
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Subject Name</label>
                                    <input
                                        type="text"
                                        required
                                        value={subjectFormData.name}
                                        onChange={e => setSubjectFormData({ ...subjectFormData, name: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Semester</label>
                                    <input
                                        type="number"
                                        min={1}
                                        max={8}
                                        value={subjectFormData.semester}
                                        onChange={e => setSubjectFormData({ ...subjectFormData, semester: parseInt(e.target.value) || 6 })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                    />
                                </div>
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Credits</label>
                                    <input
                                        type="number"
                                        min={1}
                                        max={10}
                                        value={subjectFormData.credits}
                                        onChange={e => setSubjectFormData({ ...subjectFormData, credits: parseInt(e.target.value) || 4 })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="font-bold text-muted-foreground uppercase">Description</label>
                                <textarea
                                    rows={3}
                                    value={subjectFormData.description}
                                    onChange={e => setSubjectFormData({ ...subjectFormData, description: e.target.value })}
                                    className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                />
                            </div>
                            <div className="flex justify-end gap-2 pt-3">
                                <button
                                    type="button"
                                    onClick={() => setShowSubjectModal(false)}
                                    className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-muted-foreground transition-colors cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-5 py-2 rounded-xl font-bold bg-primary text-black hover:opacity-90 transition-opacity cursor-pointer"
                                >
                                    Save Subject
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* NOTICE MODAL */}
            {showNoticeModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
                    <div className="glass-panel p-6 rounded-2xl border border-white/20 w-full max-w-lg space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-base font-bold text-foreground">
                                {editingNotice ? "Edit Circular Notice" : "Publish Department Notice"}
                            </h3>
                            <button onClick={() => setShowNoticeModal(false)} className="text-muted-foreground hover:text-foreground text-sm">✕</button>
                        </div>
                        <form onSubmit={handleSaveNotice} className="space-y-3 text-xs">
                            <div>
                                <label className="font-bold text-muted-foreground uppercase">Title</label>
                                <input
                                    type="text"
                                    required
                                    value={noticeFormData.title}
                                    onChange={e => setNoticeFormData({ ...noticeFormData, title: e.target.value })}
                                    className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-3 items-center">
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Category</label>
                                    <select
                                        value={noticeFormData.category}
                                        onChange={e => setNoticeFormData({ ...noticeFormData, category: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                    >
                                        <option value="Academic">Academic</option>
                                        <option value="Exam">Exam</option>
                                        <option value="Lab">Lab</option>
                                        <option value="Event">Event</option>
                                    </select>
                                </div>
                                <div className="flex items-center gap-2 pt-4">
                                    <input
                                        type="checkbox"
                                        id="pinned-check"
                                        checked={noticeFormData.is_pinned}
                                        onChange={e => setNoticeFormData({ ...noticeFormData, is_pinned: e.target.checked })}
                                        className="rounded text-primary focus:ring-0"
                                    />
                                    <label htmlFor="pinned-check" className="font-bold text-foreground cursor-pointer">Pin to top of feed</label>
                                </div>
                            </div>
                            <div>
                                <label className="font-bold text-muted-foreground uppercase">Content</label>
                                <textarea
                                    rows={4}
                                    required
                                    value={noticeFormData.content}
                                    onChange={e => setNoticeFormData({ ...noticeFormData, content: e.target.value })}
                                    className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-primary"
                                />
                            </div>
                            <div className="flex justify-end gap-2 pt-3">
                                <button
                                    type="button"
                                    onClick={() => setShowNoticeModal(false)}
                                    className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-muted-foreground transition-colors cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-5 py-2 rounded-xl font-bold bg-primary text-black hover:opacity-90 transition-opacity cursor-pointer"
                                >
                                    Save Notice
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* EVENT MODAL */}
            {showEventModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
                    <div className="glass-panel p-6 rounded-2xl border border-white/20 w-full max-w-lg space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-base font-bold text-foreground">
                                {editingEvent ? "Edit Department Event" : "Schedule Department Event"}
                            </h3>
                            <button onClick={() => setShowEventModal(false)} className="text-muted-foreground hover:text-foreground text-sm">✕</button>
                        </div>
                        <form onSubmit={handleSaveEvent} className="space-y-3 text-xs">
                            <div>
                                <label className="font-bold text-muted-foreground uppercase">Event Title</label>
                                <input
                                    type="text"
                                    required
                                    value={eventFormData.title}
                                    onChange={e => setEventFormData({ ...eventFormData, title: e.target.value })}
                                    className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Date &amp; Time</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="e.g. 2026-11-20 10:00 AM"
                                        value={eventFormData.date_time}
                                        onChange={e => setEventFormData({ ...eventFormData, date_time: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                    />
                                </div>
                                <div>
                                    <label className="font-bold text-muted-foreground uppercase">Venue / Location</label>
                                    <input
                                        type="text"
                                        required
                                        value={eventFormData.location}
                                        onChange={e => setEventFormData({ ...eventFormData, location: e.target.value })}
                                        className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="font-bold text-muted-foreground uppercase">Organizer / Cell</label>
                                <input
                                    type="text"
                                    required
                                    value={eventFormData.organizer}
                                    onChange={e => setEventFormData({ ...eventFormData, organizer: e.target.value })}
                                    className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                />
                            </div>
                            <div>
                                <label className="font-bold text-muted-foreground uppercase">Description</label>
                                <textarea
                                    rows={3}
                                    required
                                    value={eventFormData.description}
                                    onChange={e => setEventFormData({ ...eventFormData, description: e.target.value })}
                                    className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-foreground focus:outline-none focus:border-accent"
                                />
                            </div>
                            <div className="flex justify-end gap-2 pt-3">
                                <button
                                    type="button"
                                    onClick={() => setShowEventModal(false)}
                                    className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-muted-foreground transition-colors cursor-pointer"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-5 py-2 rounded-xl font-bold bg-accent text-black hover:opacity-90 transition-opacity cursor-pointer"
                                >
                                    Save Event
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
