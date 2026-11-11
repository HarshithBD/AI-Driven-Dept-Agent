# AIDA – AI-Driven Department Agent — Frontend

A premium enterprise-grade Next.js application for the AIML Department with a dark-mode neon design system.
AIDA is an AI-powered department assistant that helps students, faculty, and administrators access department-specific academic and administrative information.

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Styling**: Tailwind CSS v4
- **Auth**: Supabase Auth
- **State**: React `useState` / `useEffect` hooks

## Structure

```
app/
├── page.tsx              # Chat interface (typewriter streaming, session history)
├── login/page.tsx         # Login (glassmorphic neon card)
├── signup/page.tsx        # Signup with role selection (Student / Admin)
├── admin/page.tsx         # Admin control panel (6 tabs)
└── components/
    ├── ChatInterface.tsx   # Main chat — streaming, process logs
    └── Sidebar.tsx         # Session list sidebar

lib/
├── supabase.ts             # Supabase browser client
└── api-client.ts           # apiFetch() — attaches Bearer token automatically
```

## Admin Tabs

| Tab | Description |
|---|---|
| Documents | Upload PDF/DOCX with tags; view, preview, delete per file |
| Timetable | Upload per-group CSV; expandable per-group registry; delete per group |
| Deadlines | Upload deadlines CSV; color-coded cards by type; delete all |
| Notices | Upload notices JSON; per-item delete on hover |
| Telemetry | Live query logs (intent, latency, user ID) |
| Rebuild Engine | Trigger FAISS re-ingestion |

## Running

```bash
npm install
cp .env.local.example .env.local   # add Supabase keys
npm run dev                         # http://localhost:3000
```

## Environment Variables (`frontend/.env.local`)

```env
NEXT_PUBLIC_SUPABASE_URL=<supabase-project-url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase-anon-key>
```
