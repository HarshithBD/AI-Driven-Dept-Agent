# AIDA Security Controls

This document summarises every security control implemented in AIDA and notes any known limitations.

---

## 1. Secrets Management

| Control | Implementation |
|---|---|
| No secrets in code | All keys loaded via `python-dotenv` from `backend/.env` and `frontend/.env.local`. |
| `.env` excluded from git | Root `.gitignore` patterns: `.env`, `.env.local`, `.env.*.local`. |
| `.env.example` provided | Placeholder values only — no real credentials. |

**How to obtain credentials:**

| Variable | Service | Where to obtain |
|---|---|---|
| `SUPABASE_URL` | Supabase | Dashboard → Project Settings → API → Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase | Dashboard → Project Settings → API → service_role |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase | Dashboard → Project Settings → API → anon |
| `GOOGLE_API_KEY` | Google AI Studio | <https://aistudio.google.com/app/apikey> |

---

## 2. Authentication & Session Management

- **Provider**: Supabase Auth (email/password with bcrypt hashing managed by Supabase).
- **Backend verification**: Every protected endpoint calls `GET /auth/v1/user` with the bearer token against the Supabase Auth service. Invalid or expired JWTs receive **HTTP 401**.
- **Role fetching**: After auth verification, the user's role is read from the `user_roles` table (service-role key). Falls back to `user_metadata.role` if the row is missing.
- **Frontend**: Token stored in `localStorage`. Expired tokens trigger automatic redirect to `/login?expired=true` via the `apiFetch` wrapper.

**Known limitation**: `localStorage` is accessible to same-origin JavaScript. For higher-security deployments, consider switching to `httpOnly` session cookies.

---

## 3. Role-Based Access Control (RBAC)

Three roles are enforced **server-side** in `backend/main.py`:

| Role | Guard Dependency | Enforced at |
|---|---|---|
| Any authenticated user | `get_current_user` | FastAPI `Depends` |
| Faculty or Admin | `require_faculty_or_admin` | FastAPI `Depends` |
| Admin only | `require_admin` | FastAPI `Depends` |

Students **cannot** reach faculty or admin endpoints; the guard raises **HTTP 403** before any business logic executes.

The agent tools (`submit_request`, `escalate`) enforce the user's role extracted from the verified JWT — the LLM cannot override these checks.

---

## 4. Input Validation

- **Pydantic models** on every request body. Extra fields are silently ignored; required fields raise **HTTP 422** if missing or wrong type.
- **Enum constraints**: `status` in `PUT /requests/{id}/status` is validated against an allowlist; unknown values return **HTTP 400**.
- **File uploads**: Extension allowlist (`{.pdf, .md, .txt, .docx}`), 20 MB size cap, `os.path.basename()` to strip directory components, and path-traversal check via `Path.is_relative_to()`.
- **Timetable section**: validated with `re.fullmatch(r"[A-Z0-9-]+")` before filesystem lookup.

---

## 5. Parameterised Database Access

All Supabase queries use the **PostgREST REST API** with query parameters, never string-concatenated SQL. The `db_service.py` layer passes typed Python objects to `requests.get/post/patch/delete`. Direct PostgreSQL access uses the SQLAlchemy ORM (via Supabase DB URL) with parameterised queries.

---

## 6. Prompt Injection Defence

- Retrieved RAG chunks and user messages are passed as **data parameters** to the LangChain messages (`HumanMessage`, `SystemMessage`), not concatenated into the system prompt.
- The agent may only call tools from an **explicit allowlist** (`get_faculty_info`, `get_timetable`, `get_notices`, `search_documents`, `submit_request`, `escalate_to_faculty`).
- Write actions (`submit_request`, status transitions) validate the user's role **server-side** before persisting anything — the LLM result is never trusted for authorisation decisions.
- The `requests_agent` and `response_writer` enforce a hard rule: AI must refuse to approve, reject, or finalize requests and must refer to human reviewers.

---

## 7. Output Safety (XSS Prevention)

- **Frontend**: `react-markdown` renders all AI responses as sanitised markdown. React's JSX escapes all dynamic values by default; no `dangerouslySetInnerHTML` is used in the application.
- **Backend**: API responses are JSON; no HTML is generated server-side.
- **Content-Security-Policy**: Added in `frontend/next.config.ts` via Next.js response headers. CSP restricts `script-src`, `connect-src`, `frame-ancestors 'none'`, and disables `object-src`.

---

## 8. CORS

CORS is restricted to the frontend origin via the `FRONTEND_URL` environment variable (defaults to `http://localhost:3000`). Set `FRONTEND_URL=https://yourdomain.com` in production. The `allow_credentials=True` flag is set alongside the specific origin list.

---

## 9. Rate Limiting

> **Current status**: Basic rate limiting is not yet implemented in the application layer.

**Recommendation**: Add `slowapi` (wraps `limits`) to `requirements.txt` and decorate `/chat` and `/login`-related endpoints:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, ...):
    ...
```

For the login flow (handled by Supabase Auth), Supabase applies server-side rate limiting automatically.

---

## 10. Security Headers

Applied globally via `frontend/next.config.ts`:

| Header | Value |
|---|---|
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | Restricts scripts, styles, connections, frames |
| `Permissions-Policy` | Disables camera, microphone, geolocation |

---

## 11. File Upload Security

- Extension allowlist enforced before writing: `.pdf`, `.md`, `.txt`, `.docx`.
- Maximum file size: **20 MB** (HTTP 413 if exceeded).
- Files stored in `backend/data/docs/` — outside the web root, never executed.
- Filenames sanitised with `os.path.basename()` and path-traversal checked with `Path.is_relative_to()`.
- Endpoint protected by `require_faculty_or_admin`.

---

## 12. Error Handling & Logging

- FastAPI's default exception handler returns generic messages (e.g., `"detail": "Invalid or expired token"`). Stack traces are **not** returned to clients.
- Server-side `print()` statements log intent, latency, and error class — never passwords, tokens, or full user queries.
- Student IDs in Supabase telemetry logs are UUIDs, not names or enrollment numbers.

---

## 13. HTTPS Configuration

The application is **HTTPS-ready**:

- **Backend**: Run uvicorn with `--ssl-keyfile` and `--ssl-certfile` flags, or place behind an nginx/Caddy reverse proxy that terminates TLS.
- **Frontend**: Vercel, Netlify, and most Next.js hosts provide automatic TLS. For self-hosting, use Caddy or certbot/Let's Encrypt.
- CSP includes `upgrade-insecure-requests` to automatically upgrade mixed-content HTTP references to HTTPS.

---

## 14. Dependency Audit

Backend dependencies are pinned in `backend/requirements.txt`. Run periodically:

```bash
pip install pip-audit
pip-audit -r backend/requirements.txt
```

Frontend:

```bash
cd frontend && npm audit
```

> **Known limitation**: `passlib[bcrypt]` v1.7.4 has an upstream deprecation warning about bcrypt 4.x compatibility but no active CVE. Upgrade to `passlib==1.7.5` (when released) or switch to `argon2-cffi` for new password hashing.

---

## 15. Known Limitations & Recommended Improvements

| Item | Current Status | Recommended Fix |
|---|---|---|
| Rate limiting on `/chat` | Not implemented | Add `slowapi` with `20/minute` per IP |
| Session tokens in `localStorage` | Moderate risk | Switch to `httpOnly` cookies + CSRF protection |
| `passlib` bcrypt warning | Harmless but noisy | Pin `bcrypt==4.0.1` or upgrade passlib |
| Supabase RLS policies | Permissive (`USING (true)`) | Restrict with `auth.uid()` predicates per row |
| Uploaded documents not virus-scanned | No AV check | Integrate ClamAV or cloud AV on upload |
| No audit log for admin actions | Missing | Log CRUD actions to a separate `audit_log` table |

