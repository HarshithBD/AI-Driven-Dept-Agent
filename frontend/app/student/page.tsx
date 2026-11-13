"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "../../lib/api-client";
import { StudentRequest, Notice, DepartmentEvent, Faculty } from "../../lib/department-db-types";

type StudentTab = "requests" | "timetable" | "deadlines" | "notices" | "faculty";

export default function StudentDashboard() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<StudentTab>("requests");
    const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
    const [userEmail, setUserEmail] = useState("");

    // Request Submission State
    const [requestType, setRequestType] = useState("Lab Compute Access");
    const [requestDesc, setRequestDesc] = useState("");
    const [isSubmittingReq, setIsSubmittingReq] = useState(false);
    const [reqSuccess, setReqSuccess] = useState("");

    // My Requests State
    const [myRequests, setMyRequests] = useState<StudentRequest[]>([]);
    const [isReqLoading, setIsReqLoading] = useState(false);
    const [requestStatusFilter, setRequestStatusFilter] = useState("all");
    const [replyText, setReplyText] = useState<Record<string, string>>({});
    const [isReplying, setIsReplying] = useState<Record<string, boolean>>({});
    const [expandedHistory, setExpandedHistory] = useState<Record<string, boolean>>({});

    // Department Data State
    const [selectedSection, setSelectedSection] = useState<"AIML-A" | "AIML-B">("AIML-A");
    const [timetableRows, setTimetableRows] = useState<Record<string, string>[]>([]);
    const [deadlines, setDeadlines] = useState<Record<string, string>[]>([]);
    const [notices, setNotices] = useState<Notice[]>([]);
    const [events, setEvents] = useState<DepartmentEvent[]>([]);
    const [facultyList, setFacultyList] = useState<Faculty[]>([]);

    // ── STRICT AUTHENTICATION GUARD ──────────────────────────────────────────
    useEffect(() => {
        const verifyUser = async () => {
            const token = localStorage.getItem("token");
            if (!token) {
                router.push("/login");
                return;
            }

            try {
                const res = await apiFetch("/me");
                if (res.ok) {
                    const data = await res.json();
                    setIsAuthorized(true);
                    setUserEmail(data.email || "");

                    const profileRes = await apiFetch("/students/me");
                    if (profileRes.ok) {
                        const profile = await profileRes.json();
                        if (profile.section === "AIML-A" || profile.section === "AIML-B") {
                            setSelectedSection(profile.section);
                        }
                    }
                } else {
                    router.push("/login");
                }
            } catch (err) {
                console.error("Auth verification error:", err);
                router.push("/login");
            }
        };

        verifyUser();
    }, [router]);

    // Load Student Data
    useEffect(() => {
        if (!isAuthorized) return;

        const loadData = async () => {
            setIsReqLoading(true);
            try {
                // Fetch student's own requests
                const reqRes = await apiFetch("/requests/my");
                if (reqRes.ok) {
                    setMyRequests(await reqRes.json());
                }

                const timetableRes = await apiFetch(`/timetable?group=${encodeURIComponent(selectedSection)}`);
                if (timetableRes.ok) {
                    setTimetableRows(await timetableRes.json());
                }

                // Fetch deadlines
                const dRes = await apiFetch("/deadlines");
                if (dRes.ok) {
                    setDeadlines(await dRes.json());
                }

                // Fetch notices
                const nRes = await apiFetch("/db/notices");
                if (nRes.ok) {
                    setNotices(await nRes.json());
                }

                // Fetch events
                const eRes = await apiFetch("/events");
                if (eRes.ok) {
                    setEvents(await eRes.json());
                }

                // Fetch faculty list
                const fRes = await apiFetch("/faculty");
                if (fRes.ok) {
                    setFacultyList(await fRes.json());
                }
            } catch (err) {
                console.error("Failed to load student dashboard data:", err);
            } finally {
                setIsReqLoading(false);
            }
        };

        loadData();
    }, [isAuthorized, selectedSection]);

    // Handle Submit Request
    const handleSubmitRequest = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!requestDesc.trim()) return;
        setIsSubmittingReq(true);
        setReqSuccess("");

        try {
            const res = await apiFetch("/requests", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    request_type: requestType,
                    description: requestDesc
                })
            });

            if (res.ok) {
                const newReq = await res.json();
                setMyRequests(prev => [newReq, ...prev]);
                setReqSuccess("Your request has been submitted for faculty review!");
                setRequestDesc("");
                setTimeout(() => setReqSuccess(""), 4000);
            } else {
                alert("Failed to submit request.");
            }
        } catch (err) {
            console.error("Submission error:", err);
        } finally {
            setIsSubmittingReq(false);
        }
    };

    const handleReplyRequest = async (requestId: string) => {
        const text = replyText[requestId];
        if (!text || !text.trim()) return;
        setIsReplying(prev => ({ ...prev, [requestId]: true }));
        try {
            const res = await apiFetch(`/requests/${requestId}/reply`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ additional_info: text.trim() })
            });
            if (res.ok) {
                const updated = await res.json();
                setMyRequests(prev => prev.map(r => r.id === requestId ? updated : r));
                setReplyText(prev => ({ ...prev, [requestId]: "" }));
            } else {
                alert("Failed to send reply.");
            }
        } catch (err) {
            console.error("Reply error:", err);
            alert("Error sending additional information.");
        } finally {
            setIsReplying(prev => ({ ...prev, [requestId]: false }));
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

    if (isAuthorized === null) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-background">
                <div className="w-12 h-12 border-4 border-primary rounded-full border-t-transparent animate-spin mb-4" />
                <p className="text-sm font-medium text-primary">Loading Student Portal...</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background text-foreground flex flex-col">
            {/* Header */}
            <header className="border-b border-white/10 bg-black/40 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-20">
                <div className="flex items-center gap-4">
                    <Link href="/" className="flex items-center gap-2 group">
                        <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary border border-primary/40 shadow-[0_0_10px_rgba(0,229,255,0.3)]">
                            <span className="font-mono font-bold text-xs">AI</span>
                        </div>
                        <div>
                            <span className="font-bold text-foreground group-hover:text-primary transition-colors">AIDA</span>
                            <span className="text-xs text-muted-foreground ml-2 hidden sm:inline">• Student Portal</span>
                        </div>
                    </Link>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground hidden sm:inline font-mono">
                        {userEmail}
                    </span>
                    <Link
                        href="/events"
                        className="text-xs px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20 transition-colors font-bold"
                    >
                        Events
                    </Link>
                    <Link
                        href="/"
                        className="text-xs px-3 py-1.5 rounded-lg bg-primary/20 text-primary border border-primary/40 hover:bg-primary/30 transition-colors font-bold"
                    >
                        Chat with AIDA
                    </Link>
                </div>
            </header>

            {/* Main Container */}
            <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 space-y-6">
                {/* Welcome Card */}
                <div className="glass-panel p-6 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 border border-white/10">
                    <div>
                        <h1 className="text-2xl font-bold text-foreground">AIML Student Portal</h1>
                        <p className="text-xs sm:text-sm text-primary mt-0.5">
                            Artificial Intelligence & Machine Learning • Semester 6
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            Track your academic requests, schedules, assignments, and faculty office hours.
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <Link
                            href="/"
                            className="px-4 py-2 rounded-xl text-xs font-bold bg-primary text-black hover:opacity-90 transition-opacity"
                        >
                            Open AI Assistant
                        </Link>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-white/10 gap-2 overflow-x-auto">
                    {[
                        { id: "requests", label: "My Requests & Approvals" },
                        { id: "timetable", label: "Class Timetable" },
                        { id: "deadlines", label: "Assignments & Deadlines" },
                        { id: "notices", label: "Notices & Events" },
                        { id: "faculty", label: "Faculty Directory & Hours" }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as StudentTab)}
                            className={`pb-3 px-4 text-sm font-semibold transition-colors border-b-2 whitespace-nowrap cursor-pointer ${activeTab === tab.id
                                ? "border-primary text-primary"
                                : "border-transparent text-muted-foreground hover:text-foreground"
                                }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* TAB 1: SUBMIT & TRACK REQUESTS */}
                {activeTab === "requests" && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Left Column: Submission Form */}
                        <div className="lg:col-span-1 glass-panel p-5 rounded-2xl border border-white/10 space-y-4">
                            <h2 className="text-base font-bold text-foreground">Submit New Request</h2>
                            <p className="text-xs text-muted-foreground">
                                Submit academic or administrative requests for department approval.
                            </p>

                            {reqSuccess && (
                                <div className="p-3 text-xs text-green-400 bg-green-500/10 rounded-lg border border-green-500/20">
                                    {reqSuccess}
                                </div>
                            )}

                            <form onSubmit={handleSubmitRequest} className="space-y-4">
                                <div>
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Request Type</label>
                                    <select
                                        value={requestType}
                                        onChange={e => setRequestType(e.target.value)}
                                        className="w-full mt-1 px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-primary"
                                    >
                                        <option value="Lab Compute Access">Lab Compute Access (GPU Cluster)</option>
                                        <option value="Bonafide Certificate">Bonafide Certificate</option>
                                        <option value="Leave of Absence">Leave of Absence</option>
                                        <option value="Project Guide Allocation">Project Guide Allocation</option>
                                        <option value="Course Exemption">Course Exemption</option>
                                        <option value="Other">Other Academic Grievance</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="text-xs font-bold text-muted-foreground uppercase">Reason / Description</label>
                                    <textarea
                                        required
                                        rows={4}
                                        value={requestDesc}
                                        onChange={e => setRequestDesc(e.target.value)}
                                        placeholder="Explain your request clearly..."
                                        className="w-full mt-1 px-3 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-foreground focus:outline-none focus:border-primary"
                                    />
                                </div>

                                <button
                                    type="submit"
                                    disabled={isSubmittingReq || !requestDesc.trim()}
                                    className="w-full py-2.5 rounded-xl text-xs font-bold bg-primary text-black hover:opacity-90 transition-opacity disabled:opacity-40 cursor-pointer"
                                >
                                    {isSubmittingReq ? "Submitting..." : "Submit Request"}
                                </button>
                            </form>
                        </div>

                        {/* Right Column: Tracking Queue */}
                        <div className="lg:col-span-2 space-y-4">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                                <h2 className="text-base font-bold text-foreground">My Submitted Requests</h2>
                                <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="text-xs text-muted-foreground mr-1">Filter:</span>
                                    {["all", "pending", "under review", "more information required", "approved", "rejected"].map(filter => (
                                        <button
                                            key={filter}
                                            onClick={() => setRequestStatusFilter(filter)}
                                            className={`px-2.5 py-1 rounded-full text-[11px] capitalize transition-colors cursor-pointer ${requestStatusFilter === filter
                                                ? "bg-primary/20 text-primary border border-primary/40 font-bold"
                                                : "bg-white/5 text-muted-foreground hover:text-foreground border border-white/5"
                                                }`}
                                        >
                                            {filter === "more information required" ? "More Info Req." : filter}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {isReqLoading ? (
                                <div className="p-6 text-center text-sm text-muted-foreground">Loading your requests...</div>
                            ) : myRequests.length === 0 ? (
                                <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                    You have not submitted any requests yet. Use the form on the left to submit a request.
                                </div>
                            ) : (() => {
                                const filtered = requestStatusFilter === "all"
                                    ? myRequests
                                    : myRequests.filter(r => {
                                        const st = r.status.toLowerCase();
                                        if (requestStatusFilter === "under review") return st === "under review" || st === "in review";
                                        return st === requestStatusFilter;
                                    });

                                if (filtered.length === 0) {
                                    return (
                                        <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                            No requests found with status &quot;{requestStatusFilter}&quot;.
                                        </div>
                                    );
                                }

                                return (
                                    <div className="space-y-4">
                                        {filtered.map(req => {
                                            const isMoreInfoReq = req.status === "More Information Required";
                                            const hasHistory = req.history && req.history.length > 0;
                                            const isHistoryOpen = !!expandedHistory[req.id];

                                            return (
                                                <div
                                                    key={req.id}
                                                    className={`glass-panel p-5 rounded-xl border transition-colors space-y-3.5 ${isMoreInfoReq
                                                        ? "border-amber-500/40 bg-amber-500/[0.03]"
                                                        : "border-white/10"
                                                        }`}
                                                >
                                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                                        <div className="flex items-center gap-2.5 flex-wrap">
                                                            <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${getStatusBadge(req.status)}`}>
                                                                {req.status}
                                                            </span>
                                                            <span className="font-bold text-foreground text-sm">{req.request_type}</span>
                                                        </div>
                                                        <span className="text-xs text-muted-foreground">
                                                            Submitted: {new Date(req.created_at).toLocaleDateString()}
                                                        </span>
                                                    </div>

                                                    <p className="text-sm text-foreground/90 bg-black/30 p-3 rounded-lg border border-white/5">
                                                        {req.description}
                                                    </p>

                                                    {req.comments && (
                                                        <div className="text-xs text-muted-foreground bg-primary/5 p-3 rounded-lg border border-primary/20">
                                                            <strong className="text-primary font-semibold">Faculty / Admin Feedback: </strong>
                                                            {req.comments}
                                                        </div>
                                                    )}

                                                    {/* Interactive Reply Area when More Information Required */}
                                                    {isMoreInfoReq && (
                                                        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2.5">
                                                            <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold">
                                                                <span>Action Needed: Faculty requested clarification or additional documents</span>
                                                            </div>
                                                            <textarea
                                                                rows={2}
                                                                value={replyText[req.id] || ""}
                                                                onChange={e => setReplyText(prev => ({ ...prev, [req.id]: e.target.value }))}
                                                                placeholder="Type your response, clarification, or document links here..."
                                                                className="w-full px-3 py-2 bg-black/50 border border-amber-500/30 rounded-lg text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:border-amber-400"
                                                            />
                                                            <div className="flex justify-end">
                                                                <button
                                                                    onClick={() => handleReplyRequest(req.id)}
                                                                    disabled={isReplying[req.id] || !replyText[req.id]?.trim()}
                                                                    className="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-amber-500 hover:bg-amber-400 text-black transition-colors disabled:opacity-40 cursor-pointer"
                                                                >
                                                                    {isReplying[req.id] ? "Submitting..." : "Submit Additional Information"}
                                                                </button>
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* Audit Timeline / History */}
                                                    {hasHistory && (
                                                        <div className="pt-2 border-t border-white/5">
                                                            <button
                                                                onClick={() => setExpandedHistory(prev => ({ ...prev, [req.id]: !prev[req.id] }))}
                                                                className="text-xs text-muted-foreground hover:text-primary transition-colors flex items-center gap-1 cursor-pointer font-medium"
                                                            >
                                                                <span>{isHistoryOpen ? "Hide" : "View"} Request History & Audit Trail ({req.history?.length})</span>
                                                            </button>

                                                            {isHistoryOpen && (
                                                                <div className="mt-3 space-y-2 pl-3 border-l-2 border-primary/30">
                                                                    {req.history?.map((item, idx) => (
                                                                        <div key={idx} className="text-xs space-y-0.5">
                                                                            <div className="flex items-center gap-2">
                                                                                <span className="font-semibold text-foreground">{item.action}</span>
                                                                                <span className="text-muted-foreground">•</span>
                                                                                <span className="text-primary font-mono text-[11px]">
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
                                            );
                                        })}
                                    </div>
                                );
                            })()}
                        </div>
                    </div>
                )}

                {/* TAB: CLASS TIMETABLE */}
                {activeTab === "timetable" && (
                    <div className="space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-bold text-foreground">Class Timetable</h2>
                                <p className="text-xs text-muted-foreground">Schedule loaded from the department timetable CSV.</p>
                            </div>
                            <label className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
                                Section
                                <select
                                    value={selectedSection}
                                    onChange={e => setSelectedSection(e.target.value as "AIML-A" | "AIML-B")}
                                    className="px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-foreground"
                                >
                                    <option value="AIML-A">AIML-A</option>
                                    <option value="AIML-B">AIML-B</option>
                                </select>
                            </label>
                        </div>
                        {isReqLoading ? (
                            <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                Loading timetable...
                            </div>
                        ) : timetableRows.length === 0 ? (
                            <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                No timetable has been uploaded for {selectedSection}.
                            </div>
                        ) : (
                            <div className="glass-panel rounded-2xl border border-white/10 overflow-x-auto">
                                <table className="w-full text-left text-xs">
                                    <thead className="bg-white/5 text-muted-foreground uppercase">
                                        <tr>
                                            {["day", "time", "course_id", "course_name", "faculty", "room"].map(header => (
                                                <th key={header} className="px-4 py-3">{header.replace("_", " ")}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {timetableRows.map((row, index) => (
                                            <tr key={`${row.day}-${row.time}-${row.course_id}-${index}`}>
                                                {["day", "time", "course_id", "course_name", "faculty", "room"].map(key => (
                                                    <td key={key} className="px-4 py-3 text-foreground">{row[key] || "—"}</td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                {/* TAB 2: DEADLINES */}
                {activeTab === "deadlines" && (
                    <div className="space-y-4">
                        <h2 className="text-lg font-bold text-foreground">Upcoming Deadlines & Submissions</h2>
                        {isReqLoading ? (
                            <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                Loading deadlines...
                            </div>
                        ) : deadlines.length === 0 ? (
                            <div className="glass-panel p-8 rounded-2xl text-center text-sm text-muted-foreground border border-white/10">
                                No upcoming deadlines found.
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {deadlines.map((dl, idx) => (
                                    <div key={idx} className="glass-panel p-4 rounded-xl border border-white/10 space-y-2">
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs font-mono font-bold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                                                {dl.course_id}
                                            </span>
                                            <span className="text-xs font-bold text-red-400">
                                                Due: {dl.due_date}
                                            </span>
                                        </div>
                                        <h3 className="text-sm font-bold text-foreground">{dl.title}</h3>
                                        <p className="text-xs text-muted-foreground leading-relaxed">{dl.description}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* TAB 3: NOTICES & EVENTS */}
                {activeTab === "notices" && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Notices Column */}
                        <div className="space-y-4">
                            <h2 className="text-lg font-bold text-foreground">Department Notices</h2>
                            {notices.length === 0 ? (
                                <div className="glass-panel p-6 rounded-xl text-center text-xs text-muted-foreground border border-white/10">
                                    No notices published yet.
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {notices.map((n, idx) => (
                                        <div key={idx} className="glass-panel p-4 rounded-xl border border-white/10 space-y-1.5">
                                            <div className="flex items-center justify-between">
                                                <span className="text-xs font-bold text-primary">{n.category}</span>
                                                <span className="text-[11px] text-muted-foreground">{n.date}</span>
                                            </div>
                                            <h3 className="text-sm font-bold text-foreground">{n.title}</h3>
                                            <p className="text-xs text-muted-foreground">{n.content}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Events Column */}
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <h2 className="text-lg font-bold text-foreground">Upcoming Department Events</h2>
                                <Link
                                    href="/events"
                                    className="text-xs text-primary hover:underline font-semibold"
                                >
                                    View Calendar & Details →
                                </Link>
                            </div>
                            {events.length === 0 ? (
                                <div className="glass-panel p-6 rounded-xl text-center text-xs text-muted-foreground border border-white/10">
                                    No upcoming events scheduled.
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {events.map((evt, idx) => (
                                        <div key={idx} className="glass-panel p-4 rounded-xl border border-white/10 space-y-1.5">
                                            <div className="flex items-center justify-between">
                                                <span className="text-xs font-bold text-accent">{evt.organizer}</span>
                                                <span className="text-[11px] text-muted-foreground">
                                                    {new Date(evt.date_time).toLocaleDateString()}
                                                </span>
                                            </div>
                                            <h3 className="text-sm font-bold text-foreground">{evt.title}</h3>
                                            <p className="text-xs text-muted-foreground">{evt.description}</p>
                                            <p className="text-[11px] text-primary/80 font-mono mt-1">📍 {evt.location}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* TAB 4: FACULTY DIRECTORY & OFFICE HOURS */}
                {activeTab === "faculty" && (
                    <div className="space-y-4">
                        <h2 className="text-lg font-bold text-foreground">AIML Faculty Directory & Consultation Hours</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {facultyList.map(f => (
                                <div key={f.id} className="glass-panel p-5 rounded-xl border border-white/10 space-y-2">
                                    <h3 className="text-sm font-bold text-foreground">{f.name}</h3>
                                    <p className="text-xs text-primary font-medium">{f.designation}</p>
                                    <p className="text-xs text-muted-foreground">{f.contact_info}</p>
                                    <div className="pt-2 border-t border-white/5 space-y-1">
                                        <p className="text-[11px] text-muted-foreground">
                                            <strong className="text-foreground">Availability: </strong>
                                            {f.availability || "By appointment"}
                                        </p>
                                        <p className="text-[11px] text-muted-foreground">
                                            <strong className="text-foreground">Courses: </strong>
                                            {f.subjects_handled?.join(", ") || "AI401, AI402"}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
