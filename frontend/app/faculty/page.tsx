"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "../../lib/api-client";
import {
    StudentRequest,
    StudentRequestStatus,
    Faculty,
    DepartmentEvent,
    Notice
} from "../../lib/department-db-types";

type FacultyTab = "requests" | "notices" | "events" | "upload" | "profile";

interface DocumentItem {
    name: string;
    size: number;
    department: string;
    category: string;
    year: string;
    course: string;
}

interface DepartmentMetadata {
    department_code: string;
    department_name: string;
    department_acronym: string;
    institution_name: string;
    student_sections: string[];
    courses: { id: string; name: string; semester: number; credits: number }[];
    laboratories: { id: string; name: string; location: string; description: string }[];
    document_categories: string[];
}

export default function FacultyDashboard() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<FacultyTab>("requests");
    const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
    const [userEmail, setUserEmail] = useState("");
    const [userId, setUserId] = useState("");
    const [facultyProfile, setFacultyProfile] = useState<Faculty | null>(null);
    const [deptConfig, setDeptConfig] = useState<DepartmentMetadata | null>(null);

    // ── REQUESTS STATE ──────────────────────────────────────────────────────────
    const [requests, setRequests] = useState<StudentRequest[]>([]);
    const [isRequestsLoading, setIsRequestsLoading] = useState(false);
    const [requestScope, setRequestScope] = useState<"assigned" | "all">("all");
    const [statusFilter, setStatusFilter] = useState<string>("all");
    const [reviewComments, setReviewComments] = useState<Record<string, string>>({});
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const [expandedHistory, setExpandedHistory] = useState<Record<string, boolean>>({});

    // ── NOTICES STATE ───────────────────────────────────────────────────────────
    const [notices, setNotices] = useState<Notice[]>([]);
    const [isNoticesLoading, setIsNoticesLoading] = useState(false);
    const [noticeTitle, setNoticeTitle] = useState("");
    const [noticeContent, setNoticeContent] = useState("");
    const [noticeCategory, setNoticeCategory] = useState("Academic");
    const [isPostingNotice, setIsPostingNotice] = useState(false);
    const [noticeMsg, setNoticeMsg] = useState("");
    const [deletingNoticeId, setDeletingNoticeId] = useState<string | null>(null);

    // ── EVENTS STATE ────────────────────────────────────────────────────────────
    const [events, setEvents] = useState<DepartmentEvent[]>([]);
    const [isEventsLoading, setIsEventsLoading] = useState(false);
    const [showEventForm, setShowEventForm] = useState(false);
    const [eventTitle, setEventTitle] = useState("");
    const [eventDesc, setEventDesc] = useState("");
    const [eventDateTime, setEventDateTime] = useState("");
    const [eventLocation, setEventLocation] = useState("");
    const [eventOrganizer, setEventOrganizer] = useState("");
    const [isCreatingEvent, setIsCreatingEvent] = useState(false);
    const [eventMsg, setEventMsg] = useState("");

    // ── RAG DOCUMENTS STATE ─────────────────────────────────────────────────────
    const [documents, setDocuments] = useState<DocumentItem[]>([]);
    const [isDocsLoading, setIsDocsLoading] = useState(false);
    const [docFile, setDocFile] = useState<File | null>(null);
    const [docCategory, setDocCategory] = useState("Lab Manuals");
    const [docCourse, setDocCourse] = useState("AI401");
    const [isUploadingDoc, setIsUploadingDoc] = useState(false);
    const [uploadMsg, setUploadMsg] = useState("");

    // ── PROFILE & AVAILABILITY STATE ────────────────────────────────────────────
    const [availabilityText, setAvailabilityText] = useState("");
    const [isSavingAvailability, setIsSavingAvailability] = useState(false);
    const [availSuccess, setAvailSuccess] = useState("");

    // ── 1. STRICT SERVER-VERIFIED AUTHENTICATION GUARD ──────────────────────────
    useEffect(() => {
        const verifyFaculty = async () => {
            const token = localStorage.getItem("token");
            if (!token) {
                router.push("/login");
                return;
            }

            try {
                const res = await apiFetch("/me");
                if (res.ok) {
                    const data = await res.json();
                    if (!data.is_faculty && !data.is_admin) {
                        console.warn("Unauthorized: Non-faculty access attempt blocked.");
                        router.push("/?error=unauthorized_faculty");
                    } else {
                        setIsAuthorized(true);
                        setUserEmail(data.email || "");
                        setUserId(data.id || "");
                    }
                } else {
                    router.push("/login");
                }
            } catch (err) {
                console.error("Faculty auth check failed:", err);
                router.push("/login");
            }
        };

        verifyFaculty();
    }, [router]);

    // ── 2. INITIAL DATA LOADING ON AUTHORIZATION ────────────────────────────────
    useEffect(() => {
        if (!isAuthorized) return;

        const loadInitialData = async () => {
            // Load faculty profile matching authenticated email
            try {
                const facRes = await apiFetch("/faculty");
                if (facRes.ok) {
                    const list: Faculty[] = await facRes.json();
                    const current = list.find(f => f.email.toLowerCase() === userEmail.toLowerCase()) || list[0];
                    if (current) {
                        setFacultyProfile(current);
                        setAvailabilityText(current.availability || "");
                        if (!eventOrganizer) {
                            setEventOrganizer(current.name);
                        }
                    }
                }
            } catch (err) {
                console.error("Failed to load faculty profile:", err);
            }

            // Load department config
            try {
                const confRes = await apiFetch("/department/config");
                if (confRes.ok) {
                    setDeptConfig(await confRes.json());
                }
            } catch (err) {
                console.error("Failed to load department config:", err);
            }

            // Load requests
            fetchRequests();
            // Load notices
            fetchNotices();
            // Load events
            fetchEvents();
            // Load documents
            fetchDocuments();
        };

        loadInitialData();
    }, [isAuthorized, userEmail]);

    // ── 3. DATA FETCHING HELPERS ────────────────────────────────────────────────
    const fetchRequests = async () => {
        setIsRequestsLoading(true);
        try {
            const res = await apiFetch("/requests");
            if (res.ok) {
                setRequests(await res.json());
            }
        } catch (err) {
            console.error("Failed to fetch requests:", err);
        } finally {
            setIsRequestsLoading(false);
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
            console.error("Failed to fetch notices:", err);
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
            console.error("Failed to fetch events:", err);
        } finally {
            setIsEventsLoading(false);
        }
    };

    const fetchDocuments = async () => {
        setIsDocsLoading(true);
        try {
            const res = await apiFetch("/admin/docs");
            if (res.ok) {
                setDocuments(await res.json());
            }
        } catch (err) {
            console.error("Failed to fetch documents:", err);
        } finally {
            setIsDocsLoading(false);
        }
    };

    // ── 4. HUMAN APPROVAL ACTIONS FOR STUDENT REQUESTS ──────────────────────────
    const handleStatusUpdate = async (requestId: string, newStatus: StudentRequestStatus) => {
        const comments = reviewComments[requestId] || "";
        if (newStatus === "More Information Required" && !comments.trim()) {
            alert("Please provide remarks in the input box specifying what additional information is required from the student.");
            return;
        }

        setActionLoading(requestId);
        try {
            const res = await apiFetch(`/requests/${requestId}/status`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    status: newStatus,
                    comments: comments,
                    assigned_to: facultyProfile?.id
                })
            });

            if (res.ok) {
                const updated = await res.json();
                setRequests(prev => prev.map(r => r.id === requestId ? { ...r, ...updated } : r));
                setReviewComments(prev => ({ ...prev, [requestId]: "" }));
            } else {
                alert("Failed to update request status.");
            }
        } catch (err) {
            console.error("Status update error:", err);
        } finally {
            setActionLoading(null);
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

    // ── 5. NOTICES MANAGEMENT ───────────────────────────────────────────────────
    const handlePostNotice = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsPostingNotice(true);
        setNoticeMsg("");
        try {
            const res = await apiFetch("/db/notices", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: noticeTitle.trim(),
                    content: noticeContent.trim(),
                    category: noticeCategory,
                    department: "AIML"
                })
            });
            if (res.ok) {
                const newNotice = await res.json();
                setNotices(prev => [newNotice, ...prev]);
                setNoticeMsg("Notice published to department board!");
                setNoticeTitle("");
                setNoticeContent("");
                setTimeout(() => setNoticeMsg(""), 3500);
            } else {
                setNoticeMsg("Failed to publish notice.");
            }
        } catch (err) {
            console.error("Failed to post notice:", err);
            setNoticeMsg("Error publishing notice.");
        } finally {
            setIsPostingNotice(false);
        }
    };

    const handleDeleteNotice = async (noticeId: string) => {
        if (!confirm("Are you sure you want to remove this notice?")) return;
        setDeletingNoticeId(noticeId);
        try {
            const res = await apiFetch(`/db/notices/${noticeId}`, { method: "DELETE" });
            if (res.ok) {
                setNotices(prev => prev.filter(n => n.id !== noticeId));
            } else {
                alert("Failed to delete notice.");
            }
        } catch (err) {
            console.error("Failed to delete notice:", err);
        } finally {
            setDeletingNoticeId(null);
        }
    };

    // ── 6. EVENTS MANAGEMENT ────────────────────────────────────────────────────
    const handleCreateEvent = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsCreatingEvent(true);
        setEventMsg("");
        try {
            const res = await apiFetch("/events", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: eventTitle.trim(),
                    description: eventDesc.trim(),
                    date_time: eventDateTime.trim(),
                    location: eventLocation.trim(),
                    organizer: eventOrganizer.trim() || facultyProfile?.name || "AIML Faculty",
                    department: "AIML"
                })
            });
            if (res.ok) {
                const newEvt = await res.json();
                setEvents(prev => [newEvt, ...prev]);
                setEventMsg("Event scheduled successfully!");
                setEventTitle("");
                setEventDesc("");
                setEventDateTime("");
                setEventLocation("");
                setShowEventForm(false);
                setTimeout(() => setEventMsg(""), 3500);
            } else {
                setEventMsg("Failed to create event.");
            }
        } catch (err) {
            console.error("Failed to create event:", err);
            setEventMsg("Error creating event.");
        } finally {
            setIsCreatingEvent(false);
        }
    };

    // ── 7. RAG ACADEMIC DOCUMENT UPLOAD ─────────────────────────────────────────
    const handleUploadDoc = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!docFile) return;
        setIsUploadingDoc(true);
        setUploadMsg("");

        const formData = new FormData();
        formData.append("file", docFile);
        formData.append("department", "AIML");
        formData.append("course", docCourse);
        formData.append("category", docCategory);
        formData.append("year", "2026");

        try {
            const res = await apiFetch("/upload", {
                method: "POST",
                body: formData
            });
            if (res.ok) {
                setUploadMsg(`Successfully uploaded ${docFile.name} to AIML knowledge base!`);
                setDocFile(null);
                fetchDocuments();
                setTimeout(() => setUploadMsg(""), 4000);
            } else {
                setUploadMsg("Upload failed.");
            }
        } catch (err) {
            console.error("Upload error:", err);
            setUploadMsg("Error uploading file.");
        } finally {
            setIsUploadingDoc(false);
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
                alert("Failed to load document preview");
            }
        } catch (err) {
            console.error("Error viewing document", err);
        }
    };

    // ── 8. PROFILE & AVAILABILITY UPDATE ────────────────────────────────────────
    const handleSaveAvailability = async () => {
        if (!facultyProfile) return;
        setIsSavingAvailability(true);
        setAvailSuccess("");
        try {
            const res = await apiFetch(`/faculty/${facultyProfile.id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ availability: availabilityText })
            });
            if (res.ok) {
                setAvailSuccess("Office hours & student consultation availability updated!");
                setFacultyProfile(prev => prev ? { ...prev, availability: availabilityText } : null);
                setTimeout(() => setAvailSuccess(""), 3500);
            } else {
                alert("Failed to update availability.");
            }
        } catch (err) {
            console.error("Failed to update availability:", err);
        } finally {
            setIsSavingAvailability(false);
        }
    };

    // Loading Screen
    if (isAuthorized === null) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-background">
                <div className="w-12 h-12 border-4 border-accent rounded-full border-t-transparent animate-spin mb-4" />
                <p className="text-sm font-medium text-accent">Verifying Faculty Credentials...</p>
            </div>
        );
    }

    // Filter requests according to assignment and status
    const filteredRequests = requests.filter(r => {
        // Scope filter: Assigned to Me vs All
        if (requestScope === "assigned" && facultyProfile?.id) {
            if (r.assigned_to !== facultyProfile.id) return false;
        }

        // Status filter
        if (statusFilter === "all") return true;
        const st = r.status.toLowerCase();
        if (statusFilter === "under review") return st === "under review" || st === "in review";
        return st === statusFilter.toLowerCase();
    });

    const pendingRequestsCount = requests.filter(r => r.status === "Pending" || r.status === "Under Review").length;
    const assignedToMeCount = facultyProfile?.id
        ? requests.filter(r => r.assigned_to === facultyProfile.id).length
        : 0;

    return (
        <div className="min-h-screen bg-background text-foreground flex flex-col">
            {/* Top Navigation */}
            <header className="border-b border-white/10 bg-black/50 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-20">
                <div className="flex items-center gap-4">
                    <Link href="/" className="flex items-center gap-2 group">
                        <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center text-accent border border-accent/40 shadow-[0_0_10px_rgba(0,255,65,0.3)]">
                            <span className="font-mono font-bold text-xs">AI</span>
                        </div>
                        <div>
                            <span className="font-bold text-foreground group-hover:text-accent transition-colors">AIDA</span>
                            <span className="text-xs text-muted-foreground ml-2 hidden sm:inline">• Faculty Portal</span>
                        </div>
                    </Link>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs px-2.5 py-1 rounded-full bg-accent/10 text-accent border border-accent/30 font-mono hidden sm:inline">
                        Faculty Role Verified
                    </span>
                    <Link
                        href="/events"
                        className="text-xs px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20 transition-colors font-bold"
                    >
                        Public Events
                    </Link>
                    <Link
                        href="/"
                        className="text-xs px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-foreground transition-colors border border-white/10"
                    >
                        Chat with AIDA
                    </Link>
                </div>
            </header>

            {/* Main Content Area */}
            <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 space-y-6">
                {/* Faculty Welcome & Quick Status Banner */}
                <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 border border-white/10">
                    <div>
                        <div className="flex items-center gap-2">
                            <h1 className="text-2xl font-bold text-foreground">
                                {facultyProfile?.name || "Faculty Member"}
                            </h1>
                            <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-accent/20 text-accent border border-accent/40">
                                {facultyProfile?.designation || "Faculty"}
                            </span>
                        </div>
                        <p className="text-xs sm:text-sm text-accent mt-0.5 font-medium">
                            {facultyProfile?.department || "AIML"} Department • Semester 6 Academic Session
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            Specialization: <span className="text-foreground">{facultyProfile?.specialization || "AI & Machine Learning"}</span>
                            {facultyProfile?.contact_info && (
                                <span className="ml-2">• {facultyProfile.contact_info}</span>
                            )}
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-2 text-xs">
                        <div className="px-3 py-2 rounded-xl bg-black/40 border border-white/10 text-center">
                            <span className="block text-accent font-bold text-base leading-tight">{pendingRequestsCount}</span>
                            <span className="text-[11px] text-muted-foreground">Action Required</span>
                        </div>
                        <div className="px-3 py-2 rounded-xl bg-black/40 border border-white/10 text-center">
                            <span className="block text-primary font-bold text-base leading-tight">{assignedToMeCount}</span>
                            <span className="text-[11px] text-muted-foreground">Assigned to Me</span>
                        </div>
                        <div className="px-3 py-2 rounded-xl bg-black/40 border border-white/10 text-center">
                            <span className="block text-amber-400 font-bold text-base leading-tight">{events.length}</span>
                            <span className="text-[11px] text-muted-foreground">Active Events</span>
                        </div>
                    </div>
                </div>

                {/* Dashboard Tabs */}
                <div className="flex border-b border-white/10 gap-2 overflow-x-auto">
                    {[
                        { id: "requests", label: "Student Requests Review", badge: pendingRequestsCount },
                        { id: "notices", label: "Department Notices", badge: notices.length },
                        { id: "events", label: "Department Events", badge: events.length },
                        { id: "upload", label: "Course Documents (RAG)", badge: documents.length },
                        { id: "profile", label: "Profile & Department Info" }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as FacultyTab)}
                            className={`pb-3 px-4 text-sm font-semibold transition-colors border-b-2 whitespace-nowrap cursor-pointer flex items-center gap-2 ${activeTab === tab.id
                                ? "border-accent text-accent"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                                }`}
                        >
                            <span>{tab.label}</span>
                            {tab.badge !== undefined && (
                                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${activeTab === tab.id
                                    ? "bg-accent/20 text-accent"
                                    : "bg-white/10 text-muted-foreground"
                                    }`}>
                                    {tab.badge}
                                </span>
                            )}
                        </button>
                    ))}
                </div>

                {/* =========================================================================
                    TAB 1: STUDENT REQUESTS (HUMAN APPROVAL WORKFLOW)
                   ========================================================================= */}
                {activeTab === "requests" && (
                    <div className="space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-bold text-foreground">Student Requests Review Queue</h2>
                                <p className="text-xs text-muted-foreground">
                                    Human approval is required for sensitive academic decisions. AI assists in drafting, but only authorized staff can approve or reject.
                                </p>
                            </div>

                            {/* Scope Selector: Assigned to Me vs All */}
                            <div className="flex items-center gap-2 bg-black/40 p-1 rounded-xl border border-white/10 self-start sm:self-auto">
                                <button
                                    onClick={() => setRequestScope("all")}
                                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${requestScope === "all"
                                        ? "bg-accent/20 text-accent font-bold"
                                        : "text-muted-foreground hover:text-foreground"
                                        }`}
                                >
                                    All Requests ({requests.length})
                                </button>
                                <button
                                    onClick={() => setRequestScope("assigned")}
                                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${requestScope === "assigned"
                                        ? "bg-accent/20 text-accent font-bold"
                                        : "text-muted-foreground hover:text-foreground"
                                        }`}
                                >
                                    Assigned to Me ({assignedToMeCount})
                                </button>
                            </div>
                        </div>

                        {/* Status Filter Pills */}
                        <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-xs text-muted-foreground mr-1">Status:</span>
                            {["all", "pending", "under review", "more information required", "approved", "rejected"].map(filter => (
                                <button
                                    key={filter}
                                    onClick={() => setStatusFilter(filter)}
                                    className={`px-2.5 py-1 rounded-full text-xs capitalize transition-colors cursor-pointer ${statusFilter === filter
                                        ? "bg-accent/20 text-accent border border-accent/40 font-bold"
                                        : "bg-white/5 text-muted-foreground hover:text-foreground border border-white/5"
                                        }`}
                                >
                                    {filter === "more information required" ? "More Info Req." : filter}
                                </button>
                            ))}
                        </div>

                        {isRequestsLoading ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">Loading student requests...</div>
                        ) : filteredRequests.length === 0 ? (
                            <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                No requests found for the selected filter ({requestScope === "assigned" ? "Assigned to Me" : "All"}, status: &quot;{statusFilter}&quot;).
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {filteredRequests.map(req => {
                                    const hasHistory = req.history && req.history.length > 0;
                                    const isHistoryOpen = !!expandedHistory[req.id];
                                    const isAssignedToMe = facultyProfile?.id && req.assigned_to === facultyProfile.id;

                                    return (
                                        <div
                                            key={req.id}
                                            className="glass-panel p-5 rounded-xl border border-white/10 space-y-3.5 hover:border-accent/30 transition-colors"
                                        >
                                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                                <div className="flex items-center gap-2.5 flex-wrap">
                                                    <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${getStatusBadge(req.status)}`}>
                                                        {req.status}
                                                    </span>
                                                    <span className="font-bold text-foreground text-sm">{req.request_type}</span>
                                                    {isAssignedToMe && (
                                                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/40 font-mono">
                                                            Assigned to You
                                                        </span>
                                                    )}
                                                    {req.students && (
                                                        <span className="text-xs text-muted-foreground font-mono">
                                                            ({req.students.full_name} • {req.students.enrollment_no} • {req.students.section})
                                                        </span>
                                                    )}
                                                </div>
                                                <span className="text-xs text-muted-foreground">
                                                    Submitted: {new Date(req.created_at).toLocaleDateString()}
                                                </span>
                                            </div>

                                            <p className="text-sm text-foreground/90 bg-black/30 p-3 rounded-lg border border-white/5 whitespace-pre-wrap">
                                                {req.description}
                                            </p>

                                            {req.comments && (
                                                <div className="text-xs text-muted-foreground bg-accent/5 p-2.5 rounded-lg border border-accent/20">
                                                    <strong className="text-accent font-semibold">Latest Remark: </strong>
                                                    {req.comments}
                                                </div>
                                            )}

                                            {/* Human Action Review Controls */}
                                            <div className="pt-2 space-y-2 border-t border-white/5">
                                                <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center justify-between">
                                                    <input
                                                        type="text"
                                                        placeholder="Add review feedback / remark (required when requesting more info)..."
                                                        value={reviewComments[req.id] || ""}
                                                        onChange={e => setReviewComments(prev => ({ ...prev, [req.id]: e.target.value }))}
                                                        className="flex-1 px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:border-accent"
                                                    />
                                                    <div className="flex gap-1.5 shrink-0 flex-wrap">
                                                        <button
                                                            onClick={() => handleStatusUpdate(req.id, "Approved")}
                                                            disabled={actionLoading === req.id || req.status === "Approved"}
                                                            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/40 transition-colors disabled:opacity-40 cursor-pointer"
                                                        >
                                                            Approve
                                                        </button>
                                                        <button
                                                            onClick={() => handleStatusUpdate(req.id, "Rejected")}
                                                            disabled={actionLoading === req.id || req.status === "Rejected"}
                                                            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/40 transition-colors disabled:opacity-40 cursor-pointer"
                                                        >
                                                            Reject
                                                        </button>
                                                        <button
                                                            onClick={() => handleStatusUpdate(req.id, "More Information Required")}
                                                            disabled={actionLoading === req.id || req.status === "More Information Required"}
                                                            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 border border-amber-500/40 transition-colors disabled:opacity-40 cursor-pointer"
                                                        >
                                                            Request Info
                                                        </button>
                                                        <button
                                                            onClick={() => handleStatusUpdate(req.id, "Under Review")}
                                                            disabled={actionLoading === req.id || req.status === "Under Review"}
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
                                                            onClick={() => setExpandedHistory(prev => ({ ...prev, [req.id]: !prev[req.id] }))}
                                                            className="text-xs text-muted-foreground hover:text-accent transition-colors flex items-center gap-1 cursor-pointer font-medium"
                                                        >
                                                            <span>{isHistoryOpen ? "Hide" : "View"} Audit History ({req.history?.length})</span>
                                                        </button>

                                                        {isHistoryOpen && (
                                                            <div className="mt-2.5 space-y-2 pl-3 border-l-2 border-accent/40">
                                                                {req.history?.map((item, idx) => (
                                                                    <div key={idx} className="text-xs space-y-0.5">
                                                                        <div className="flex items-center gap-2">
                                                                            <span className="font-semibold text-foreground">{item.action}</span>
                                                                            <span className="text-muted-foreground">•</span>
                                                                            <span className="text-accent font-mono text-[11px]">
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
                    TAB 2: DEPARTMENT NOTICES (PUBLISH & MANAGE)
                   ========================================================================= */}
                {activeTab === "notices" && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Publish Notice Form */}
                        <div className="lg:col-span-1 glass-panel p-6 rounded-2xl border border-white/10 space-y-4 h-fit">
                            <h2 className="text-base font-bold text-foreground">Publish Department Notice</h2>
                            <p className="text-xs text-muted-foreground">
                                Circulars published here appear in the Student Portal and are indexed by the AIDA Notices Agent.
                            </p>

                            {noticeMsg && (
                                <div className="p-3 text-xs text-green-400 bg-green-500/10 rounded-lg border border-green-500/20">
                                    {noticeMsg}
                                </div>
                            )}

                            <form onSubmit={handlePostNotice} className="space-y-4">
                                <div>
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Notice Title</label>
                                    <input
                                        type="text"
                                        required
                                        value={noticeTitle}
                                        onChange={e => setNoticeTitle(e.target.value)}
                                        placeholder="e.g. Lab 401 Capstone Review Submission"
                                        className="w-full mt-1 px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                    />
                                </div>

                                <div>
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Category</label>
                                    <select
                                        value={noticeCategory}
                                        onChange={e => setNoticeCategory(e.target.value)}
                                        className="w-full mt-1 px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                    >
                                        <option value="Academic">Academic</option>
                                        <option value="Exam">Exam</option>
                                        <option value="Lab">Lab & Compute</option>
                                        <option value="Event">Event & Hackathon</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Content</label>
                                    <textarea
                                        required
                                        rows={5}
                                        value={noticeContent}
                                        onChange={e => setNoticeContent(e.target.value)}
                                        placeholder="Provide complete circular details, deadlines, and instructions..."
                                        className="w-full mt-1 px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                    />
                                </div>

                                <button
                                    type="submit"
                                    disabled={isPostingNotice || !noticeTitle.trim() || !noticeContent.trim()}
                                    className="w-full py-2.5 rounded-xl text-xs font-bold bg-accent text-black hover:opacity-90 transition-opacity disabled:opacity-40 cursor-pointer"
                                >
                                    {isPostingNotice ? "Publishing..." : "Publish Circular"}
                                </button>
                            </form>
                        </div>

                        {/* Manage Published Notices */}
                        <div className="lg:col-span-2 space-y-4">
                            <div className="flex items-center justify-between">
                                <h2 className="text-base font-bold text-foreground">Manage Published Department Notices</h2>
                                <span className="text-xs text-muted-foreground font-mono">{notices.length} Active Notices</span>
                            </div>

                            {isNoticesLoading ? (
                                <div className="p-8 text-center text-sm text-muted-foreground">Loading notices...</div>
                            ) : notices.length === 0 ? (
                                <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                    No published notices found. Use the form on the left to post an announcement.
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {notices.map(notice => (
                                        <div
                                            key={notice.id}
                                            className="glass-panel p-5 rounded-xl border border-white/10 space-y-3 hover:border-accent/30 transition-colors"
                                        >
                                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-accent/20 text-accent border border-accent/40 uppercase">
                                                        {notice.category}
                                                    </span>
                                                    {notice.is_pinned && (
                                                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40">
                                                            PINNED
                                                        </span>
                                                    )}
                                                    <span className="font-bold text-foreground text-sm">{notice.title}</span>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <span className="text-xs text-muted-foreground">
                                                        {new Date(notice.date).toLocaleDateString()}
                                                    </span>
                                                    <button
                                                        onClick={() => handleDeleteNotice(notice.id)}
                                                        disabled={deletingNoticeId === notice.id}
                                                        className="text-xs text-red-400 hover:text-red-300 font-semibold transition-colors disabled:opacity-40 cursor-pointer"
                                                    >
                                                        {deletingNoticeId === notice.id ? "Deleting..." : "Delete"}
                                                    </button>
                                                </div>
                                            </div>

                                            <p className="text-xs text-foreground/80 bg-black/30 p-3 rounded-lg border border-white/5 whitespace-pre-wrap leading-relaxed">
                                                {notice.content}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* =========================================================================
                    TAB 3: DEPARTMENT EVENTS (VIEW & SCHEDULE)
                   ========================================================================= */}
                {activeTab === "events" && (
                    <div className="space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-bold text-foreground">Department Events, Workshops & Seminars</h2>
                                <p className="text-xs text-muted-foreground">
                                    Manage technical workshops, symposiums, and guest lectures. Scheduled events are indexed by the AIDA Event Agent.
                                </p>
                            </div>
                            <button
                                onClick={() => setShowEventForm(!showEventForm)}
                                className="px-4 py-2 rounded-xl text-xs font-bold bg-accent text-black hover:opacity-90 transition-opacity cursor-pointer self-start sm:self-auto"
                            >
                                {showEventForm ? "Close Event Form" : "+ Schedule New Event"}
                            </button>
                        </div>

                        {eventMsg && (
                            <div className="p-3 text-xs text-green-400 bg-green-500/10 rounded-lg border border-green-500/20">
                                {eventMsg}
                            </div>
                        )}

                        {/* Collapsible Create Event Form */}
                        {showEventForm && (
                            <div className="glass-panel p-6 rounded-2xl border border-accent/40 bg-accent/[0.02] space-y-4">
                                <h3 className="text-sm font-bold text-accent uppercase tracking-wider">Schedule Department Event</h3>
                                <form onSubmit={handleCreateEvent} className="space-y-4">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs font-bold text-muted-foreground uppercase">Event Title</label>
                                            <input
                                                type="text"
                                                required
                                                value={eventTitle}
                                                onChange={e => setEventTitle(e.target.value)}
                                                placeholder="e.g. Edge AI Workshop with NVIDIA Jetson"
                                                className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs font-bold text-muted-foreground uppercase">Date & Time</label>
                                            <input
                                                type="text"
                                                required
                                                value={eventDateTime}
                                                onChange={e => setEventDateTime(e.target.value)}
                                                placeholder="e.g. 2026-11-20 10:00 AM – 1:00 PM"
                                                className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                            />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs font-bold text-muted-foreground uppercase">Venue / Location</label>
                                            <input
                                                type="text"
                                                required
                                                value={eventLocation}
                                                onChange={e => setEventLocation(e.target.value)}
                                                placeholder="e.g. Robotics & Vision Lab (Lab 402)"
                                                className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs font-bold text-muted-foreground uppercase">Organizer / Faculty Lead</label>
                                            <input
                                                type="text"
                                                required
                                                value={eventOrganizer}
                                                onChange={e => setEventOrganizer(e.target.value)}
                                                placeholder="e.g. Prof. M. Rao (AIML Department)"
                                                className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="text-xs font-bold text-muted-foreground uppercase">Event Description & Agendas</label>
                                        <textarea
                                            required
                                            rows={3}
                                            value={eventDesc}
                                            onChange={e => setEventDesc(e.target.value)}
                                            placeholder="Detail what students will learn, prerequisites, and registration details..."
                                            className="w-full mt-1 px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                        />
                                    </div>

                                    <div className="flex justify-end gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setShowEventForm(false)}
                                            className="px-4 py-2 rounded-xl text-xs font-bold bg-white/5 hover:bg-white/10 text-muted-foreground transition-colors cursor-pointer"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="submit"
                                            disabled={isCreatingEvent}
                                            className="px-5 py-2 rounded-xl text-xs font-bold bg-accent text-black hover:opacity-90 transition-opacity disabled:opacity-40 cursor-pointer"
                                        >
                                            {isCreatingEvent ? "Scheduling..." : "Save & Publish Event"}
                                        </button>
                                    </div>
                                </form>
                            </div>
                        )}

                        {/* Events Grid */}
                        {isEventsLoading ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">Loading department events...</div>
                        ) : events.length === 0 ? (
                            <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                No department events currently scheduled. Click &quot;Schedule New Event&quot; above to create one.
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {events.map(event => (
                                    <div
                                        key={event.id}
                                        className="glass-panel p-5 rounded-xl border border-white/10 space-y-3 hover:border-amber-500/30 transition-colors flex flex-col justify-between"
                                    >
                                        <div className="space-y-2">
                                            <div className="flex items-center justify-between gap-2">
                                                <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40 uppercase">
                                                    Department Event
                                                </span>
                                                <span className="text-xs text-muted-foreground font-mono">
                                                    {event.date_time}
                                                </span>
                                            </div>

                                            <h3 className="font-bold text-foreground text-base">{event.title}</h3>

                                            <p className="text-xs text-foreground/80 line-clamp-3">
                                                {event.description}
                                            </p>
                                        </div>

                                        <div className="pt-3 border-t border-white/5 space-y-1 text-xs text-muted-foreground">
                                            <div className="flex items-center gap-1.5">
                                                <span className="text-accent font-semibold">Venue:</span>
                                                <span className="text-foreground">{event.location}</span>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                <span className="text-accent font-semibold">Organizer:</span>
                                                <span>{event.organizer}</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* =========================================================================
                    TAB 4: COURSE DOCUMENTS & RAG KNOWLEDGE BASE
                   ========================================================================= */}
                {activeTab === "upload" && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Upload Form */}
                        <div className="lg:col-span-1 glass-panel p-6 rounded-2xl border border-white/10 space-y-4 h-fit">
                            <h2 className="text-base font-bold text-foreground">Upload Course Material (RAG)</h2>
                            <p className="text-xs text-muted-foreground">
                                Upload course syllabi, lab manuals, and capstone guidelines. AIDA indexes these to answer student queries with precise citations.
                            </p>

                            {uploadMsg && (
                                <div className="p-3 text-xs text-green-400 bg-green-500/10 rounded-lg border border-green-500/20">
                                    {uploadMsg}
                                </div>
                            )}

                            <form onSubmit={handleUploadDoc} className="space-y-4">
                                <div>
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Course ID</label>
                                    <select
                                        value={docCourse}
                                        onChange={e => setDocCourse(e.target.value)}
                                        className="w-full mt-1 px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                    >
                                        <option value="AI401">AI401 – Machine Learning Foundations</option>
                                        <option value="AI402">AI402 – Deep Learning & Neural Networks</option>
                                        <option value="AI403">AI403 – Natural Language Processing</option>
                                        <option value="AI404">AI404 – Computer Vision</option>
                                        <option value="AI405">AI405 – Reinforcement Learning & Robotics</option>
                                        <option value="AI406">AI406 – AI Ethics & Governance</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Category</label>
                                    <select
                                        value={docCategory}
                                        onChange={e => setDocCategory(e.target.value)}
                                        className="w-full mt-1 px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                    >
                                        <option value="Lab Manuals">Lab Manuals</option>
                                        <option value="AIML Syllabus">Curriculum & Syllabus</option>
                                        <option value="Project Guidelines">Capstone Project Guidelines</option>
                                        <option value="Academic Regulations">Academic Regulations</option>
                                        <option value="Lecture Notes">Lecture Notes & Resources</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Select Document (PDF / MD / TXT)</label>
                                    <input
                                        type="file"
                                        accept=".pdf,.md,.txt,.docx"
                                        required
                                        onChange={e => setDocFile(e.target.files?.[0] || null)}
                                        className="w-full mt-1 px-3 py-3 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground file:mr-4 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-accent/20 file:text-accent hover:file:bg-accent/30 cursor-pointer"
                                    />
                                </div>

                                <button
                                    type="submit"
                                    disabled={isUploadingDoc || !docFile}
                                    className="w-full py-2.5 rounded-xl text-xs font-bold bg-accent text-black hover:opacity-90 transition-opacity disabled:opacity-40 cursor-pointer"
                                >
                                    {isUploadingDoc ? "Ingesting Document..." : "Upload & Vectorize"}
                                </button>
                            </form>
                        </div>

                        {/* Document Directory */}
                        <div className="lg:col-span-2 space-y-4">
                            <div className="flex items-center justify-between">
                                <h2 className="text-base font-bold text-foreground">Indexed Knowledge Base Documents</h2>
                                <span className="text-xs text-muted-foreground font-mono">{documents.length} Files Ingested</span>
                            </div>

                            {isDocsLoading ? (
                                <div className="p-8 text-center text-sm text-muted-foreground">Loading documents...</div>
                            ) : documents.length === 0 ? (
                                <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                    No documents indexed yet. Upload course materials on the left to populate the knowledge base.
                                </div>
                            ) : (
                                <div className="space-y-2.5">
                                    {documents.map((doc, idx) => (
                                        <div
                                            key={idx}
                                            className="glass-panel p-4 rounded-xl border border-white/10 flex items-center justify-between gap-3 hover:border-accent/30 transition-colors"
                                        >
                                            <div className="space-y-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="font-bold text-foreground text-sm truncate">{doc.name}</span>
                                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-muted-foreground border border-white/5">
                                                        {(doc.size / 1024).toFixed(1)} KB
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <span className="text-accent font-semibold">{doc.category}</span>
                                                    {doc.course && (
                                                        <>
                                                            <span>•</span>
                                                            <span className="font-mono text-primary">{doc.course}</span>
                                                        </>
                                                    )}
                                                    {doc.year && (
                                                        <>
                                                            <span>•</span>
                                                            <span>{doc.year}</span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>

                                            <button
                                                onClick={() => handleViewDoc(doc.name)}
                                                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 hover:bg-white/10 text-foreground transition-colors border border-white/10 shrink-0 cursor-pointer"
                                            >
                                                Preview
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* =========================================================================
                    TAB 5: PROFILE & DEPARTMENT INFORMATION
                   ========================================================================= */}
                {activeTab === "profile" && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Left: Faculty Personal & Office Hours Details */}
                        <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-5">
                            <div>
                                <h2 className="text-base font-bold text-foreground">Faculty Member Profile</h2>
                                <p className="text-xs text-muted-foreground">
                                    Information verified by the department. AIDA retrieves this data when answering faculty inquiries.
                                </p>
                            </div>

                            <div className="space-y-3 text-sm">
                                <div className="grid grid-cols-3 py-2 border-b border-white/5">
                                    <span className="text-xs text-muted-foreground font-semibold">Full Name</span>
                                    <span className="col-span-2 font-bold text-foreground">{facultyProfile?.name || "Dr. Suresh Kumar"}</span>
                                </div>
                                <div className="grid grid-cols-3 py-2 border-b border-white/5">
                                    <span className="text-xs text-muted-foreground font-semibold">Designation</span>
                                    <span className="col-span-2 text-accent font-semibold">{facultyProfile?.designation || "Associate Professor"}</span>
                                </div>
                                <div className="grid grid-cols-3 py-2 border-b border-white/5">
                                    <span className="text-xs text-muted-foreground font-semibold">Department</span>
                                    <span className="col-span-2 text-foreground font-mono">{facultyProfile?.department || "AIML"}</span>
                                </div>
                                <div className="grid grid-cols-3 py-2 border-b border-white/5">
                                    <span className="text-xs text-muted-foreground font-semibold">Official Email</span>
                                    <span className="col-span-2 text-foreground font-mono text-xs">{facultyProfile?.email || userEmail}</span>
                                </div>
                                <div className="grid grid-cols-3 py-2 border-b border-white/5">
                                    <span className="text-xs text-muted-foreground font-semibold">Specialization</span>
                                    <span className="col-span-2 text-foreground">{facultyProfile?.specialization || "AI & Machine Learning"}</span>
                                </div>
                                <div className="grid grid-cols-3 py-2 border-b border-white/5">
                                    <span className="text-xs text-muted-foreground font-semibold">Courses Handled</span>
                                    <span className="col-span-2 text-primary font-mono text-xs">
                                        {facultyProfile?.subjects_handled?.join(", ") || "AI401, AI402"}
                                    </span>
                                </div>
                                <div className="grid grid-cols-3 py-2 border-b border-white/5">
                                    <span className="text-xs text-muted-foreground font-semibold">Cabin / Office</span>
                                    <span className="col-span-2 text-foreground">{facultyProfile?.contact_info || "Cabin 402, AIML Block"}</span>
                                </div>
                            </div>

                            {/* Office Hours & Student Consultation Editor */}
                            <div className="pt-4 border-t border-white/10 space-y-3">
                                <div>
                                    <h3 className="text-sm font-bold text-foreground">Office Hours & Consultation Availability</h3>
                                    <p className="text-xs text-muted-foreground">
                                        Keep your consultation hours updated. AIDA uses this info when answering student queries about your availability.
                                    </p>
                                </div>

                                {availSuccess && (
                                    <div className="p-3 text-xs text-green-400 bg-green-500/10 rounded-lg border border-green-500/20">
                                        {availSuccess}
                                    </div>
                                )}

                                <input
                                    type="text"
                                    value={availabilityText}
                                    onChange={e => setAvailabilityText(e.target.value)}
                                    placeholder="e.g. Mon & Wed: 2:00 PM – 4:00 PM (Cabin 402)"
                                    className="w-full px-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-accent"
                                />

                                <button
                                    onClick={handleSaveAvailability}
                                    disabled={isSavingAvailability || !availabilityText.trim()}
                                    className="px-4 py-2 rounded-xl text-xs font-bold bg-accent text-black hover:opacity-90 transition-opacity disabled:opacity-40 cursor-pointer"
                                >
                                    {isSavingAvailability ? "Updating..." : "Save Office Hours"}
                                </button>
                            </div>
                        </div>

                        {/* Right: Department Information & Infrastructure */}
                        <div className="space-y-6">
                            {/* Department Info */}
                            <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4">
                                <div>
                                    <h2 className="text-base font-bold text-foreground">Department Identity & Infrastructure</h2>
                                    <p className="text-xs text-muted-foreground">
                                        Artificial Intelligence & Machine Learning (AIML) Department
                                    </p>
                                </div>

                                <div className="space-y-2.5 text-xs">
                                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-black/30 border border-white/5">
                                        <span className="text-muted-foreground">Head of Department:</span>
                                        <span className="font-bold text-foreground">Dr. A. Sharma (Professor & HOD)</span>
                                    </div>
                                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-black/30 border border-white/5">
                                        <span className="text-muted-foreground">Department Code:</span>
                                        <span className="font-bold text-accent font-mono">{deptConfig?.department_code || "AIML"}</span>
                                    </div>
                                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-black/30 border border-white/5">
                                        <span className="text-muted-foreground">Student Sections:</span>
                                        <span className="font-bold text-primary font-mono">
                                            {deptConfig?.student_sections?.join(", ") || "AIML-A, AIML-B"}
                                        </span>
                                    </div>
                                </div>

                                <h3 className="text-xs font-bold text-muted-foreground uppercase pt-2">Specialized Computing Laboratories</h3>
                                <div className="space-y-2">
                                    {deptConfig?.laboratories ? (
                                        deptConfig.laboratories.map((lab, i) => (
                                            <div key={i} className="p-3 rounded-lg bg-black/20 border border-white/5 space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span className="font-bold text-foreground text-xs">{lab.name}</span>
                                                    <span className="text-[11px] text-accent font-mono">{lab.location}</span>
                                                </div>
                                                <p className="text-[11px] text-muted-foreground">{lab.description}</p>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="space-y-2">
                                            <div className="p-3 rounded-lg bg-black/20 border border-white/5 space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span className="font-bold text-foreground text-xs">Computing Lab 401: High-Performance GPU Cluster</span>
                                                    <span className="text-[11px] text-accent font-mono">Cabin 401</span>
                                                </div>
                                                <p className="text-[11px] text-muted-foreground">RTX 4090 Workstations & Deep Learning compute node</p>
                                            </div>
                                            <div className="p-3 rounded-lg bg-black/20 border border-white/5 space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span className="font-bold text-foreground text-xs">Computing Lab 402: Robotics & Edge AI Lab</span>
                                                    <span className="text-[11px] text-accent font-mono">Cabin 402</span>
                                                </div>
                                                <p className="text-[11px] text-muted-foreground">NVIDIA Jetson Orin kits and computer vision setups</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
