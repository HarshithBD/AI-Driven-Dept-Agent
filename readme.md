# AIDA – AI-Driven Department Agent

> An enterprise-grade, multi-agent artificial intelligence department assistant for the **Artificial Intelligence & Machine Learning (AIML) Department**, engineered with **LangGraph Orchestration + RAG + Model Context Protocol (MCP) + Role-Based Access Control (RBAC)**.

[![Next.js](https://img.shields.io/badge/Frontend-Next.js_16_App_Router-black?logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-1C3C3C?logo=langchain)](https://langchain.com/langgraph)
[![FAISS](https://img.shields.io/badge/Vector_Store-FAISS_Dense_Index-00599C)](https://github.com/facebookresearch/faiss)
[![Supabase](https://img.shields.io/badge/Auth%20%26%20DB-Supabase_PostgreSQL-3ECF8E?logo=supabase)](https://supabase.com)
[![Gemini](https://img.shields.io/badge/LLM-Gemini_3.8_Flash-4285F4?logo=google)](https://ai.google.dev)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript_v5-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.9_%2F_3.11+-3776AB?logo=python)](https://python.org)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Multi-Agent Pipeline](#multi-agent-pipeline)
- [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
- [Database Setup & Migrations](#database-setup--migrations)
- [Environment Variables](#environment-variables)
- [Backend Installation](#backend-installation)
- [Frontend Installation](#frontend-installation)
- [Commands to Run the Application](#commands-to-run-the-application)
- [Instructions for Adding Department Documents (RAG)](#instructions-for-adding-department-documents-rag)
- [Example AI Queries](#example-ai-queries)
- [Project Directory Structure](#project-directory-structure)
- [Known Limitations & Future Roadmap](#known-limitations--future-roadmap)

---

## Overview

**AIDA (AI-Driven Department Agent)** is an autonomous academic and administrative operations system designed specifically for collegiate engineering departments. Unlike general conversational chatbots, AIDA connects directly to structured department databases, official regulatory handbooks, course syllabi, live timetable schedules, and human approval request queues.

AIDA integrates a **LangGraph Supervisor Multi-Agent Graph** that categorizes student and faculty inquiries, routes them to specialized agents, executes verified queries against PostgreSQL and FAISS vector databases, and presents grounded answers with source citations. AIDA strictly adheres to a **Human-In-The-Loop Governance Model**: while AIDA assists students in drafting petitions and understanding policies, all sensitive approvals (leaves, bonafide certificates, OD permissions, lab compute grants) are rendered exclusively by authorized human faculty advisors or department administrators.

---

## Key Features

### 1. Multi-Agent AI Assistant
- **Supervisor Routing**: Natural language intent classification using Gemini with deterministic section-clarification shortcuts.
- **Faculty Information Agent**: Queries live instructor profiles, Head of Department (HOD), subjects handled, research specializations, office consultation hours, and sanitizes private contact details.
- **Timetable & Deadline Agent**: Connects to the Timetable MCP Server to retrieve cohort schedules (`AIML-A`, `AIML-B`), classroom assignments, and assignment/exam deadlines.
- **Department Notices Agent**: Fetches and filters official bulletins and circulars (Academic, Exam, Lab, Event).
- **Events & Workshop Agent**: Resolves questions regarding upcoming hackathons, distinguished talks, edge computing workshops, venues, and faculty organizers.
- **RAG Academic Agent**: Semantically searches course syllabi (AI401–AI405), academic regulations (attendance/passing marks), lab workstation rules, and Capstone project guidelines with page-level citations.
- **Request Assistance Tool**: Explains petition requirements, provides drafting templates, tracks student request status, and enforces human-only decision rules.

### 2. Student Portal (`/student`)
- **Real-Time AI Chat**: Streaming responses with expandable agent routing traces and source links.
- **Request Submission**: Submit formal requests for Bonafide Certificates, Medical/Casual Leave, On-Duty (OD) permissions, Project Guide allocation, and GPU compute access.
- **Request Status Tracking**: Real-time status inspection (`Pending`, `Under Review`, `Approved`, `Rejected`, `More Information Required`) with reviewer remarks.
- **Department Schedule**: Interactive timetable matrix and upcoming assignment deadlines view.
- **Notice Board**: Department circulars with pinned announcement indicators.

### 3. Faculty Dashboard (`/faculty`)
- **Assigned Request Queue**: Review requests submitted by students assigned to the faculty member or cohort.
- **Human Approval Actions**: One-click status transitions (`Approve`, `Reject`, `Request Info`, `Under Review`) with mandatory reviewer comments.
- **Notice Board Management**: Draft and publish official department circulars.
- **Event Scheduling**: Post workshops, guest lectures, and student symposiums with venue and date controls.
- **Academic Document Upload**: Upload course syllabi, assignment rubrics, and lab manuals directly to the RAG knowledge base.
- **Faculty Profile**: Inspect handled subjects, specializations, and office consultation availability.

### 4. Admin Management Suite (`/admin`)
- **Analytics Overview**: High-level KPIs: Total Students, Total Faculty, Active Notices, Upcoming Events, Pending Requests, RAG Documents, and section distribution graphs.
- **Student Roster Manager**: Full CRUD on student records, enrollment numbers, semesters, and sections.
- **Faculty Directory Manager**: Full CRUD on faculty titles, specializations, office hours, and contact details.
- **Curriculum Catalog Manager**: Full CRUD on semester courses, credits, and course descriptions.
- **Timetable Management**: Upload CSV schedules, view parsed day/time grids, and purge schedules.
- **Document Knowledge Base**: Upload PDFs/markdown files, preview document text, delete documents, and trigger FAISS vector index rebuilding.
- **Audit & Telemetry Logs**: Real-time query classifications, agent routes, execution latencies, and user activity feeds.
- **Destructive Action Guards**: Interactive confirmation dialogs and input validation across all deletion endpoints.

---

## Technology Stack

| Domain | Technology | Description |
| :--- | :--- | :--- |
| **Frontend Framework** | **Next.js 16 (App Router)** | Modern React server & client components with streaming UI. |
| **Styling & Design** | **Tailwind CSS v4** | Dark neon cyber-glassmorphism theme with fluid responsiveness. |
| **Backend Framework** | **FastAPI (Python 3.9 / 3.11+)** | Asynchronous REST and Server-Sent Events (SSE) streaming API. |
| **Agent Orchestration** | **LangGraph / LangChain** | StateGraph pipeline with conditional routing and shared state. |
| **LLM Provider** | **Google Gemini (gemini-3.8-flash)** | Intent classification, parameter extraction, and markdown synthesis. |
| **Vector Database** | **FAISS (Dense Similarity Search)** | Vector indexing with multi-chunk metadata preservation. |
| **Relational Database** | **Supabase PostgreSQL** | Cloud PostgreSQL with Row Level Security (RLS) & REST PostgREST. |
| **Local Fallback DB** | **In-Memory / SQLite Engine** | Seamless offline persistence layer in `db_service.py`. |
| **Tool Protocol** | **Model Context Protocol (MCP)** | Decoupled FastMCP servers for timetable and notice tools. |

---

## System Architecture

```text
                               +-----------------------------+
                               |     Next.js 16 Frontend     |
                               |  (/, /student, /faculty,    |
                               |   /admin, /events, /login)  |
                               +-----------------------------+
                                              |
                                              | REST APIs / SSE Streaming
                                              v
                               +-----------------------------+
                               |       FastAPI Backend       |
                               | (main.py + Auth Middleware) |
                               +-----------------------------+
                                              |
               +------------------------------+------------------------------+
               |                                                             |
               v                                                             v
+-----------------------------+                               +-----------------------------+
|    LangGraph Multi-Agent    |                               |  Department Database Layer  |
|          Pipeline           |                               |      (db_service.py)        |
+-----------------------------+                               +-----------------------------+
| • Supervisor Agent          |                               | • Supabase PostgREST Engine |
| • Faculty Info Agent        |                               | • In-Memory Fallback Store  |
| • Timetable & Deadline Agent|                               | • Tables: faculty, students,|
| • Notices Agent             |                               |   subjects, timetable,      |
| • Events & Workshop Agent   |                               |   events, notices, requests,|
| • RAG Academic Agent        |                               |   academic_documents        |
| • Request Assistance Tool   |                               +-----------------------------+
| • Response Writer Node      |                                              |
+-----------------------------+                                              v
               |                                              +-----------------------------+
               v                                              |    PostgreSQL Database      |
+-----------------------------+                               |  (Supabase / Local Cloud)   |
|     FAISS Vector Store      |                               +-----------------------------+
| (backend/data/docs/ FAISS)  |
+-----------------------------+
```

---

## Multi-Agent Pipeline

AIDA processes every incoming query through a coordinated LangGraph pipeline:

1. **Query Ingestion**: The user query and conversation history are delivered to `supervisor_node`.
2. **Context Disambiguation**: Deterministic checks detect section clarification replies (e.g. `AIML-A`, `A`, `Section B`) without invoking the LLM.
3. **Intent Classification**: The Supervisor classifies the request into one of:
   - `faculty` -> Routed to `faculty_agent`.
   - `timetable` / `deadline` -> Routed to `timetable_agent`.
   - `notices` -> Routed to `notices_agent`.
   - `events` -> Routed to `events_agent`.
   - `rag` -> Routed to `rag_agent`.
   - `requests` -> Routed to `requests_agent`.
   - `general` -> Routed directly to `response_writer`.
4. **Specialist Execution**: The target specialist node performs structured database queries, MCP lookups, or FAISS vector similarity searches and populates `state["context"]` and `state["sources"]`.
5. **Synthesis & Policy Validation**: The `response_writer` formats the gathered context into markdown, incorporates verified citations, and validates human-only approval policies before streaming the output to the user.

---

## Role-Based Access Control (RBAC)

AIDA enforces security at both the Next.js client router and FastAPI backend dependencies:

| Capability | Student | Faculty | Administrator | Enforcing Guard |
| :--- | :---: | :---: | :---: | :--- |
| Chat with AIDA AI Assistant | Yes | Yes | Yes | `get_current_user` |
| View Timetable, Notices, Events, Directory | Yes | Yes | Yes | `get_current_user` |
| Submit Student Request & Track History | Yes | No | No | Student UI & `get_current_user` |
| Review Assigned Student Requests | No | Yes | Yes | `require_faculty_or_admin` |
| Approve / Reject Student Requests | No | Yes | Yes | `require_faculty_or_admin` |
| Publish Department Notices & Events | No | Yes | Yes | `require_faculty_or_admin` |
| Upload Course Documents to RAG | No | Yes | Yes | `require_faculty_or_admin` |
| Delete Student Requests | No | No | **Yes** | `require_admin` |
| Delete Faculty Records | No | No | **Yes** | `require_admin` |
| Delete Enrolled Student Records | No | No | **Yes** | `require_admin` |
| Delete Curriculum Subjects | No | No | **Yes** | `require_admin` |
| Purge Timetables & Deadlines | No | No | **Yes** | `require_admin` |
| Delete RAG Docs & Rebuild FAISS Vectors | No | No | **Yes** | `require_admin` |
| Access Latency & Supervisor Telemetry | No | No | **Yes** | `require_admin` |
| Access Department Analytics KPI Overview | No | No | **Yes** | `require_admin` |

---

## Database Setup & Migrations

The database schema is structured for enterprise production on Supabase PostgreSQL with built-in Row Level Security (RLS).

### Automated Setup
To run migrations directly using Python:
```bash
cd backend
python setup_aida_db.py
```

### Manual Supabase Setup
1. Open your **Supabase Dashboard** -> **SQL Editor**.
2. Copy the contents of [`backend/migrations/001_aida_department_schema.sql`](file:///c:/Users/harsh/OneDrive/Desktop/main%20project/Campus-Asistant/backend/migrations/001_aida_department_schema.sql).
3. Click **Run**. This creates:
   - `user_roles`
   - `faculty`
   - `students`
   - `subjects`
   - `timetable`
   - `notices`
   - `events`
   - `academic_documents`
   - `student_requests`
   - Performance indexes and default Greenfield Institute AIML seed data.

---

## Environment Variables

### Backend Configuration (`backend/.env`)
Create `backend/.env` with the following variables:

```env
# Supabase Configuration
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your-supabase-service-role-key>
SUPABASE_DB_URL=postgresql://postgres:<password>@db.<your-project>.supabase.co:5432/postgres

# Google Gemini LLM API
GEMINI_API_KEY=<your-google-gemini-api-key>
LLM_MODEL=gemini-3.8-flash

# Department Identifiers
DEPARTMENT_CODE=AIML
DEPARTMENT_NAME=Artificial Intelligence and Machine Learning
INSTITUTION_NAME=Greenfield Institute of Technology
```

### Frontend Configuration (`frontend/.env.local`)
Create `frontend/.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-supabase-anon-key>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Backend Installation

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Build FAISS vector database for documents
python -c "from rag import rebuild_vector_store; rebuild_vector_store()"
```

---

## Frontend Installation

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install Node.js packages
npm install

# 3. Verify TypeScript compilation
npm run build
```

---

## Commands to Run the Application

To run the complete system, launch both the backend and frontend servers in separate terminal sessions:

### Terminal 1: Backend Server (FastAPI)
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 8000
```
*Backend API will be running at:* `http://localhost:8000`  
*API Swagger Documentation:* `http://localhost:8000/docs`

### Terminal 2: Frontend Server (Next.js)
```powershell
cd frontend
npm run dev
```
*Frontend will be running at:* `http://localhost:3000`

---

## Instructions for Adding Department Documents (RAG)

AIDA supports PDF, Markdown (`.md`), and Plain Text (`.txt`) documents for semantic retrieval:

### Method A: Via the Admin / Faculty Dashboard (Recommended)
1. Log in as an **Administrator** or **Faculty** member.
2. Navigate to **Admin Dashboard** (`/admin`) -> **Documents** tab, or **Faculty Dashboard** (`/faculty`) -> **Upload** tab.
3. Select your document (`.pdf`, `.md`, `.txt`).
4. Choose the appropriate category:
   - `AIML Syllabus`
   - `Academic Regulations`
   - `Project Guidelines`
   - `Laboratory Manuals`
   - `Department Policies`
5. Select Course (e.g. `AI401`) and Academic Year.
6. Click **Upload & Index Document**. The backend extracts text, chunks with metadata, generates embeddings, and adds them to the live vector index.

### Method B: Manual File Ingestion
1. Place your `.pdf`, `.md`, or `.txt` files in `backend/data/docs/`.
2. Run the index rebuild command:
   ```powershell
   python -c "from rag import rebuild_vector_store; rebuild_vector_store()"
   ```

---

## Example AI Queries

Test AIDA's multi-agent routing with these representative questions:

### Faculty Inquiries
- *"Who is the Head of the Department?"*
- *"Who teaches Machine Learning Foundations (AI401)?"*
- *"What is Prof. Rao's research specialization and when is his office consultation availability?"*
- *"Where is Dr. Verma's cabin and what is his email address?"*

### Timetable & Deadlines
- *"What classes does Section AIML-A have on Monday?"*
- *"What time is the Deep Learning lab scheduled in Lab 401?"*
- *"When is the AI401 assignment submission deadline?"*

### Notices & Announcements
- *"What are the latest announcements on the department notice board?"*
- *"Are there any notices regarding midterm examinations or assessments?"*
- *"Show recent administrative circulars for AIML students."*

### Department Events & Workshops
- *"What is the next department event?"*
- *"Are there any technical workshops scheduled this month?"*
- *"Where is the upcoming Edge AI with NVIDIA Jetson workshop being held?"*
- *"Who is organizing the Annual AIML Hackathon?"*

### Syllabi & Academic Policies (RAG)
- *"What is the mandatory attendance threshold and condonation policy?"*
- *"What topics and modules are covered in the AI401 syllabus?"*
- *"What are the Capstone project team size requirements and review milestones?"*
- *"What are the GPU cluster access rules and storage quotas in Lab 401?"*

### Student Request Workflow & Governance
- *"How do I apply for a Bonafide Certificate for an education loan?"*
- *"Can you approve my medical leave of absence for 3 days?"* *(Demonstrates AI rejection rule -> human faculty approval required)*
- *"How do I submit an On-Duty (OD) request for an external hackathon?"*
- *"Help me draft a request description for GPU cluster compute access."*

---

## Project Directory Structure

```text
Campus-Asistant/
├── backend/
│   ├── main.py                     # FastAPI server, endpoints, and SSE streaming
│   ├── graph.py                    # LangGraph multi-agent StateGraph definition
│   ├── db_service.py               # Supabase + In-memory relational database service
│   ├── department_config.py        # AIML department metadata, courses, sections, labs
│   ├── setup_aida_db.py            # Database migration execution script
│   ├── agents/                     # Specialist LangGraph agents
│   │   ├── supervisor.py           # Natural language intent classification
│   │   ├── faculty_agent.py        # Faculty information and availability agent
│   │   ├── timetable_agent.py      # Timetable & deadline retrieval agent
│   │   ├── notices_agent.py        # Department notices agent
│   │   ├── events_agent.py         # Department events & workshop agent
│   │   ├── rag_agent.py            # RAG document retrieval agent
│   │   ├── requests_agent.py       # Student request assistance & governance tool
│   │   ├── planner_agent.py        # Study plan generator agent
│   │   ├── response_writer.py      # Markdown synthesis and citation writer
│   │   └── state.py                # LangGraph shared state TypedDict
│   ├── rag/                        # RAG ingestion and retrieval package
│   │   ├── parser.py               # Multi-format document parser (PDF/MD/TXT)
│   │   ├── chunker.py              # Recursive chunker with metadata tagging
│   │   ├── embeddings.py           # Dense embedding generator
│   │   ├── vectorstore.py          # FAISS vector store manager
│   │   └── pipeline.py             # Document search orchestrator
│   ├── migrations/                 # PostgreSQL migrations
│   │   └── 001_aida_department_schema.sql  # Core department schema & seeds
│   ├── data/                       # Local data stores
│   │   ├── docs/                   # Academic PDFs and syllabus markdown files
│   │   ├── timetables/             # Timetable CSVs and deadlines
│   │   └── notices/                # Notices JSON storage
│   └── test/                       # Unit and integration test suites
│       ├── test_integrated_architecture.py  # Multi-agent graph routing suite
│       ├── test_student_requests_unit.py    # Request workflow & governance suite
│       ├── test_events_agent_unit.py        # Event agent & CRUD suite
│       ├── test_faculty_agent_unit.py       # Faculty agent & sanitization suite
│       └── test_rag_system_unit.py          # RAG extraction and grounding suite
│
├── frontend/
│   ├── app/                        # Next.js App Router pages
│   │   ├── page.tsx                # Main Chat interface with streaming AIDA
│   │   ├── login/page.tsx          # Login page with role checks
│   │   ├── signup/page.tsx         # User registration with role selection
│   │   ├── student/page.tsx        # Student Portal (Requests, schedule, notices)
│   │   ├── faculty/page.tsx        # Faculty Dashboard (Approvals, upload, notices)
│   │   ├── admin/page.tsx          # Admin Suite (10 management modules)
│   │   ├── events/page.tsx         # Department Events bulletin page
│   │   └── components/             # Reusable UI components
│   │       ├── ChatInterface.tsx   # Interactive chat box with typewriter streaming
│   │       └── Sidebar.tsx         # Role-aware sidebar with session history
│   └── lib/
│       ├── api-client.ts           # Authenticated fetch wrapper
│       ├── department-config.ts    # Frontend department configuration
│       ├── department-db-types.ts  # TypeScript type definitions
│       └── supabase.ts             # Supabase browser client
│
└── README.md                       # Comprehensive project documentation
```

---

## Known Limitations & Future Roadmap

### Current Operational Limitations
1. **Static Timetable CSV vs Live Dynamic Calendar Sync**:
   - Timetable schedules are loaded from uploaded CSV files. Ad-hoc, unscheduled verbal class cancellations by faculty are not reflected unless updated via the Admin Timetable module or published as a notice.
2. **Document Vector Indexing Latency for Large PDF Uploads**:
   - While vector search executes in milliseconds, ingesting large PDFs (>100 pages) creates multiple embeddings asynchronously, taking 5–15 seconds before newly uploaded chunks become queryable.
3. **Turnaround for Student Request Decisions**:
   - While AIDA assists students in drafting requests immediately, formal decisions require human review by faculty or administrators. Processing times depend on human availability.
4. **Upstream LLM Service Dependency**:
   - Conversational synthesis relies on the Google Gemini API. In the event of upstream rate-limiting or network downtime, the system displays structured fallback messages.

### Recommended Future Improvements
- [ ] **Push & Email Notifications**: Automated email notifications (via Resend or SendGrid) to students when a faculty member updates request status.
- [ ] **Google Calendar / Outlook Sync**: Real-time synchronization of department events and lectures directly into students' personal calendar feeds.
- [ ] **Multi-Department Scalability**: Dynamic multi-tenant support allowing multiple engineering departments (CSE, ECE, Mechanical) to maintain isolated data catalogs within a single institution.
- [ ] **Voice-to-Text Querying**: Hands-free voice inquiry support on mobile devices using Web Speech API or Whisper.
