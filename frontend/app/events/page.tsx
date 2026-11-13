"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "../../lib/api-client";
import { DepartmentEvent } from "../../lib/department-db-types";

type EventFilter = "all" | "upcoming" | "workshops" | "seminars" | "hackathons";

export default function EventsPage() {
    // User & Permissions State
    const [userRole, setUserRole] = useState<{
        isAuthenticated: boolean;
        isFaculty: boolean;
        isAdmin: boolean;
        email: string;
    }>({
        isAuthenticated: false,
        isFaculty: false,
        isAdmin: false,
        email: "",
    });

    // Events State
    const [events, setEvents] = useState<DepartmentEvent[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [errorMsg, setErrorMsg] = useState("");
    const [successMsg, setSuccessMsg] = useState("");

    // Filter & Search
    const [activeFilter, setActiveFilter] = useState<EventFilter>("all");
    const [searchQuery, setSearchQuery] = useState("");

    // Detail Modal State
    const [selectedEvent, setSelectedEvent] = useState<DepartmentEvent | null>(null);

    // Create / Edit Modal State
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [editingEvent, setEditingEvent] = useState<DepartmentEvent | null>(null);

    // Form State
    const [formTitle, setFormTitle] = useState("");
    const [formDesc, setFormDesc] = useState("");
    const [formDateTime, setFormDateTime] = useState("");
    const [formLocation, setFormLocation] = useState("");
    const [formOrganizer, setFormOrganizer] = useState("AIML Department");
    const [isSaving, setIsSaving] = useState(false);

    // ── CHECK USER AUTH & ROLES ──────────────────────────────────────────────
    useEffect(() => {
        const checkAuth = async () => {
            const token = localStorage.getItem("token");
            if (!token) {
                setUserRole({ isAuthenticated: false, isFaculty: false, isAdmin: false, email: "" });
                return;
            }

            try {
                const res = await apiFetch("/me");
                if (res.ok) {
                    const data = await res.json();
                    setUserRole({
                        isAuthenticated: true,
                        isFaculty: Boolean(data.is_faculty),
                        isAdmin: Boolean(data.is_admin),
                        email: data.email || "",
                    });
                }
            } catch (e) {
                console.error("Auth check failed:", e);
            }
        };

        checkAuth();
    }, []);

    // ── FETCH EVENTS ────────────────────────────────────────────────────────
    const fetchEvents = async () => {
        setIsLoading(true);
        setErrorMsg("");
        try {
            const res = await apiFetch("/events");
            if (res.ok) {
                const data: DepartmentEvent[] = await res.json();
                setEvents(data);
            } else {
                setErrorMsg("Failed to load department events. Please try again.");
            }
        } catch (e) {
            console.error("Error fetching events:", e);
            setErrorMsg("Could not connect to the events service.");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchEvents();
    }, []);

    // ── FORM MANAGEMENT ─────────────────────────────────────────────────────
    const openCreateModal = () => {
        setFormTitle("");
        setFormDesc("");
        // Set default date to tomorrow at 10:00 AM
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(10, 0, 0, 0);
        setFormDateTime(tomorrow.toISOString().slice(0, 16));
        setFormLocation("");
        setFormOrganizer("AIML Department");
        setEditingEvent(null);
        setIsCreateModalOpen(true);
    };

    const openEditModal = (event: DepartmentEvent) => {
        setEditingEvent(event);
        setFormTitle(event.title);
        setFormDesc(event.description);
        try {
            setFormDateTime(new Date(event.date_time).toISOString().slice(0, 16));
        } catch {
            setFormDateTime(event.date_time);
        }
        setFormLocation(event.location);
        setFormOrganizer(event.organizer);
        setIsCreateModalOpen(true);
    };

    const handleSaveEvent = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formTitle || !formDateTime || !formLocation || !formOrganizer) {
            setErrorMsg("Please fill out all required fields.");
            return;
        }

        setIsSaving(true);
        setErrorMsg("");
        setSuccessMsg("");

        try {
            const payload = {
                title: formTitle,
                description: formDesc,
                date_time: new Date(formDateTime).toISOString(),
                location: formLocation,
                organizer: formOrganizer,
                department: "AIML",
            };

            if (editingEvent) {
                // Update existing event
                const res = await apiFetch(`/events/${editingEvent.id}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "Failed to update event");
                }
                setSuccessMsg("Event updated successfully!");
            } else {
                // Create new event
                const res = await apiFetch("/events", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "Failed to create event");
                }
                setSuccessMsg("New event created successfully!");
            }

            setIsCreateModalOpen(false);
            setEditingEvent(null);
            fetchEvents();
        } catch (err: unknown) {
            console.error("Save event error:", err);
            setErrorMsg(err instanceof Error ? err.message : "Failed to save event. Check authorization.");
        } finally {
            setIsSaving(false);
        }
    };

    const handleDeleteEvent = async (eventId: string, eventTitle: string) => {
        if (!confirm(`Are you sure you want to delete the event: "${eventTitle}"?`)) {
            return;
        }

        setErrorMsg("");
        setSuccessMsg("");

        try {
            const res = await apiFetch(`/events/${eventId}`, {
                method: "DELETE",
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Failed to delete event");
            }
            setSuccessMsg(`Event "${eventTitle}" deleted successfully.`);
            if (selectedEvent?.id === eventId) {
                setSelectedEvent(null);
            }
            fetchEvents();
        } catch (err: unknown) {
            console.error("Delete event error:", err);
            setErrorMsg(err instanceof Error ? err.message : "Failed to delete event. Check authorization.");
        }
    };

    // ── FILTERING & SEARCHING ────────────────────────────────────────────────
    const now = new Date();

    const filteredEvents = events.filter((evt) => {
        const titleMatch = evt.title.toLowerCase().includes(searchQuery.toLowerCase());
        const descMatch = evt.description.toLowerCase().includes(searchQuery.toLowerCase());
        const locMatch = evt.location.toLowerCase().includes(searchQuery.toLowerCase());
        const orgMatch = evt.organizer.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesSearch = !searchQuery || titleMatch || descMatch || locMatch || orgMatch;

        if (!matchesSearch) return false;

        const evtDate = new Date(evt.date_time);
        const text = `${evt.title} ${evt.description}`.toLowerCase();

        if (activeFilter === "upcoming") {
            return evtDate >= now;
        } else if (activeFilter === "workshops") {
            return text.includes("workshop") || text.includes("hands-on");
        } else if (activeFilter === "seminars") {
            return text.includes("seminar") || text.includes("talk") || text.includes("lecture");
        } else if (activeFilter === "hackathons") {
            return text.includes("hackathon") || text.includes("competition");
        }

        return true;
    });

    const isAuthorizedManager = userRole.isFaculty || userRole.isAdmin;

    return (
        <div className="min-h-screen bg-[#07090e] text-foreground flex flex-col">
            {/* Top Navigation Bar */}
            <header className="border-b border-white/10 bg-black/50 backdrop-blur-md sticky top-0 z-30">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link
                            href="/"
                            className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors group"
                            title="Back to AIDA Chat"
                        >
                            <svg className="w-5 h-5 text-primary group-hover:-translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                            </svg>
                            <span className="font-bold text-sm hidden sm:inline">AIDA Chat</span>
                        </Link>
                        <div className="h-4 w-px bg-white/20"></div>
                        <div>
                            <h1 className="text-base font-bold text-foreground flex items-center gap-2">
                                <span>Department Events</span>
                                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/30">
                                    AIML Dept
                                </span>
                            </h1>
                            <p className="text-xs text-muted-foreground hidden md:block">
                                Official calendar for hackathons, workshops, seminars, and distinguished talks
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        {isAuthorizedManager && (
                            <button
                                onClick={openCreateModal}
                                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-primary text-primary-foreground font-semibold rounded-lg text-xs hover:bg-primary/90 transition-all shadow-md shadow-primary/20"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                <span>Create Event</span>
                            </button>
                        )}

                        <div className="flex items-center gap-2 text-xs">
                            {userRole.isAuthenticated ? (
                                <span className="text-xs text-muted-foreground bg-white/5 border border-white/10 px-2.5 py-1 rounded-md">
                                    {userRole.isAdmin ? "👑 Admin" : userRole.isFaculty ? "🎓 Faculty" : "🎒 Student"}
                                </span>
                            ) : (
                                <Link
                                    href="/login"
                                    className="text-xs text-primary hover:underline px-2.5 py-1 rounded-md border border-primary/30 bg-primary/10"
                                >
                                    Sign In
                                </Link>
                            )}
                        </div>
                    </div>
                </div>
            </header>

            {/* Notification Banners */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full mt-4">
                {errorMsg && (
                    <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-center justify-between">
                        <span>{errorMsg}</span>
                        <button onClick={() => setErrorMsg("")} className="text-red-400 hover:text-white font-bold ml-2">✕</button>
                    </div>
                )}
                {successMsg && (
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center justify-between">
                        <span>{successMsg}</span>
                        <button onClick={() => setSuccessMsg("")} className="text-emerald-400 hover:text-white font-bold ml-2">✕</button>
                    </div>
                )}
            </div>

            {/* Main Content Area */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full flex-1">
                {/* Search & Filter Bar */}
                <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center mb-8">
                    {/* Category Filter Pills */}
                    <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
                        {(
                            [
                                { id: "all", label: "All Events" },
                                { id: "upcoming", label: "Upcoming" },
                                { id: "workshops", label: "Workshops" },
                                { id: "seminars", label: "Seminars & Talks" },
                                { id: "hackathons", label: "Hackathons" },
                            ] as { id: EventFilter; label: string }[]
                        ).map((filter) => (
                            <button
                                key={filter.id}
                                onClick={() => setActiveFilter(filter.id)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${activeFilter === filter.id
                                        ? "bg-primary/20 text-primary border border-primary/40 shadow-[0_0_12px_rgba(0,229,255,0.2)]"
                                        : "bg-white/5 text-muted-foreground hover:text-foreground hover:bg-white/10 border border-white/5"
                                    }`}
                            >
                                {filter.label}
                            </button>
                        ))}
                    </div>

                    {/* Search Input */}
                    <div className="relative w-full md:w-72">
                        <svg
                            className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Search by title, location, organizer..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 transition-colors"
                        />
                        {searchQuery && (
                            <button
                                onClick={() => setSearchQuery("")}
                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white text-xs"
                            >
                                ✕
                            </button>
                        )}
                    </div>
                </div>

                {/* Events Grid */}
                {isLoading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {[1, 2, 3].map((n) => (
                            <div key={n} className="h-64 rounded-2xl bg-white/5 border border-white/10 animate-pulse p-6"></div>
                        ))}
                    </div>
                ) : filteredEvents.length === 0 ? (
                    <div className="text-center py-16 px-4 bg-white/5 rounded-2xl border border-white/10 border-dashed max-w-xl mx-auto">
                        <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto mb-3">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <h3 className="text-sm font-bold text-foreground">No Department Events Found</h3>
                        <p className="text-xs text-muted-foreground mt-1">
                            {searchQuery
                                ? `No events match "${searchQuery}". Try a different keyword.`
                                : "There are currently no events matching this category."}
                        </p>
                        {isAuthorizedManager && (
                            <button
                                onClick={openCreateModal}
                                className="mt-4 px-4 py-2 bg-primary text-primary-foreground text-xs font-semibold rounded-lg hover:bg-primary/90 transition-all"
                            >
                                Schedule First Event
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredEvents.map((evt) => {
                            const evtDate = new Date(evt.date_time);
                            const isUpcoming = evtDate >= now;

                            return (
                                <div
                                    key={evt.id}
                                    className="bg-black/40 backdrop-blur-md rounded-2xl border border-white/10 p-5 flex flex-col justify-between hover:border-primary/40 hover:shadow-[0_0_20px_rgba(0,229,255,0.1)] transition-all group"
                                >
                                    <div>
                                        {/* Status & Organizer Header */}
                                        <div className="flex items-center justify-between mb-3">
                                            <span
                                                className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${isUpcoming
                                                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                                                        : "bg-gray-500/10 text-gray-400 border-gray-500/30"
                                                    }`}
                                            >
                                                {isUpcoming ? "Upcoming" : "Past Event"}
                                            </span>
                                            <span className="text-[11px] font-medium text-accent truncate max-w-[140px]">
                                                {evt.organizer}
                                            </span>
                                        </div>

                                        {/* Event Title */}
                                        <h3 className="text-base font-bold text-foreground group-hover:text-primary transition-colors leading-snug line-clamp-2 mb-2">
                                            {evt.title}
                                        </h3>

                                        {/* Description Snippet */}
                                        <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed mb-4">
                                            {evt.description}
                                        </p>
                                    </div>

                                    {/* Event Metadata Footer */}
                                    <div className="pt-3 border-t border-white/5 space-y-2">
                                        <div className="flex items-center gap-2 text-xs text-foreground/80">
                                            <svg className="w-3.5 h-3.5 text-primary shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                            </svg>
                                            <span className="truncate">
                                                {evtDate.toLocaleDateString(undefined, {
                                                    weekday: "short",
                                                    month: "short",
                                                    day: "numeric",
                                                    year: "numeric",
                                                })}{" "}
                                                •{" "}
                                                {evtDate.toLocaleTimeString(undefined, {
                                                    hour: "2-digit",
                                                    minute: "2-digit",
                                                })}
                                            </span>
                                        </div>

                                        <div className="flex items-center gap-2 text-xs text-foreground/80">
                                            <svg className="w-3.5 h-3.5 text-secondary shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                            </svg>
                                            <span className="truncate font-mono text-[11px] text-primary/90">
                                                {evt.location}
                                            </span>
                                        </div>

                                        {/* Actions Row */}
                                        <div className="pt-2 flex items-center justify-between gap-2">
                                            <button
                                                onClick={() => setSelectedEvent(evt)}
                                                className="text-xs font-semibold text-primary hover:text-primary/80 transition-colors"
                                            >
                                                View Details →
                                            </button>

                                            {isAuthorizedManager && (
                                                <div className="flex items-center gap-1.5">
                                                    <button
                                                        onClick={() => openEditModal(evt)}
                                                        className="p-1 text-muted-foreground hover:text-primary hover:bg-white/5 rounded transition-colors"
                                                        title="Edit Event"
                                                    >
                                                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                        </svg>
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeleteEvent(evt.id, evt.title)}
                                                        className="p-1 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                                                        title="Delete Event"
                                                    >
                                                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                        </svg>
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </main>

            {/* ── EVENT DETAILS MODAL ────────────────────────────────────────── */}
            {selectedEvent && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-[#0b0f19] border border-white/10 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative space-y-4">
                        <button
                            onClick={() => setSelectedEvent(null)}
                            className="absolute top-4 right-4 text-muted-foreground hover:text-white p-1 rounded-md"
                        >
                            ✕
                        </button>

                        <div className="flex items-center gap-2">
                            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/30">
                                {selectedEvent.department} Department Event
                            </span>
                            <span className="text-xs text-accent font-semibold">{selectedEvent.organizer}</span>
                        </div>

                        <h2 className="text-xl font-bold text-foreground leading-snug">{selectedEvent.title}</h2>

                        <div className="bg-white/5 border border-white/5 rounded-xl p-3.5 space-y-2 text-xs">
                            <div className="flex items-center gap-2 text-foreground/90">
                                <span className="font-semibold text-primary">🗓️ Date & Time:</span>
                                <span>
                                    {new Date(selectedEvent.date_time).toLocaleDateString(undefined, {
                                        weekday: "long",
                                        year: "numeric",
                                        month: "long",
                                        day: "numeric",
                                    })}{" "}
                                    at{" "}
                                    {new Date(selectedEvent.date_time).toLocaleTimeString(undefined, {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                    })}
                                </span>
                            </div>
                            <div className="flex items-center gap-2 text-foreground/90">
                                <span className="font-semibold text-secondary">📍 Venue / Room:</span>
                                <span className="font-mono text-primary">{selectedEvent.location}</span>
                            </div>
                            <div className="flex items-center gap-2 text-foreground/90">
                                <span className="font-semibold text-accent">👥 Organized By:</span>
                                <span>{selectedEvent.organizer}</span>
                            </div>
                        </div>

                        <div>
                            <h4 className="text-xs font-bold text-foreground mb-1 uppercase tracking-wider text-muted-foreground">
                                Overview & Description
                            </h4>
                            <p className="text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap">
                                {selectedEvent.description}
                            </p>
                        </div>

                        <div className="pt-3 border-t border-white/5 flex items-center justify-between">
                            <span className="text-[11px] text-muted-foreground">
                                Event ID: <span className="font-mono">{selectedEvent.id.slice(0, 8)}...</span>
                            </span>
                            <div className="flex items-center gap-2">
                                {isAuthorizedManager && (
                                    <button
                                        onClick={() => {
                                            const evt = selectedEvent;
                                            setSelectedEvent(null);
                                            openEditModal(evt);
                                        }}
                                        className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-foreground text-xs font-semibold rounded-lg transition-colors"
                                    >
                                        Edit
                                    </button>
                                )}
                                <button
                                    onClick={() => setSelectedEvent(null)}
                                    className="px-4 py-1.5 bg-primary text-primary-foreground text-xs font-semibold rounded-lg hover:bg-primary/90 transition-colors"
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ── CREATE / EDIT EVENT MODAL ──────────────────────────────────── */}
            {isCreateModalOpen && (
                <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-[#0b0f19] border border-white/10 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative space-y-4">
                        <button
                            onClick={() => setIsCreateModalOpen(false)}
                            className="absolute top-4 right-4 text-muted-foreground hover:text-white p-1 rounded-md"
                        >
                            ✕
                        </button>

                        <div>
                            <h2 className="text-lg font-bold text-foreground">
                                {editingEvent ? "Edit Department Event" : "Create Department Event"}
                            </h2>
                            <p className="text-xs text-muted-foreground mt-0.5">
                                {editingEvent
                                    ? "Update schedule, location, or details for this event."
                                    : "Add a workshop, seminar, hackathon, or guest lecture to the AIML calendar."}
                            </p>
                        </div>

                        <form onSubmit={handleSaveEvent} className="space-y-3.5 text-xs">
                            <div>
                                <label className="block font-semibold text-foreground mb-1">
                                    Event Title <span className="text-red-400">*</span>
                                </label>
                                <input
                                    type="text"
                                    required
                                    value={formTitle}
                                    onChange={(e) => setFormTitle(e.target.value)}
                                    placeholder="e.g. Hands-on Workshop: Edge AI with NVIDIA Jetson"
                                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary/50"
                                />
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <div>
                                    <label className="block font-semibold text-foreground mb-1">
                                        Date & Time <span className="text-red-400">*</span>
                                    </label>
                                    <input
                                        type="datetime-local"
                                        required
                                        value={formDateTime}
                                        onChange={(e) => setFormDateTime(e.target.value)}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary/50"
                                    />
                                </div>
                                <div>
                                    <label className="block font-semibold text-foreground mb-1">
                                        Organizer <span className="text-red-400">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        required
                                        value={formOrganizer}
                                        onChange={(e) => setFormOrganizer(e.target.value)}
                                        placeholder="e.g. AIML Robotics Club / Student Chapter"
                                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary/50"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block font-semibold text-foreground mb-1">
                                    Location / Venue <span className="text-red-400">*</span>
                                </label>
                                <input
                                    type="text"
                                    required
                                    value={formLocation}
                                    onChange={(e) => setFormLocation(e.target.value)}
                                    placeholder="e.g. Robotics & Vision Lab (Lab 402) / Seminar Hall 2"
                                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground focus:outline-none focus:border-primary/50"
                                />
                            </div>

                            <div>
                                <label className="block font-semibold text-foreground mb-1">
                                    Event Description <span className="text-red-400">*</span>
                                </label>
                                <textarea
                                    required
                                    rows={4}
                                    value={formDesc}
                                    onChange={(e) => setFormDesc(e.target.value)}
                                    placeholder="Provide detailed information regarding speakers, agenda, target audience, registration requirements..."
                                    className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-foreground focus:outline-none focus:border-primary/50 leading-relaxed"
                                />
                            </div>

                            <div className="pt-3 border-t border-white/5 flex items-center justify-end gap-2">
                                <button
                                    type="button"
                                    onClick={() => setIsCreateModalOpen(false)}
                                    className="px-4 py-2 bg-white/10 text-foreground font-semibold rounded-lg hover:bg-white/20 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={isSaving}
                                    className="px-5 py-2 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
                                >
                                    {isSaving ? "Saving..." : editingEvent ? "Save Changes" : "Create Event"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
