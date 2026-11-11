# ==================== LOAD ENV ====================
import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

# ==================== IMPORTS ====================
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
import json
import shutil
import requests
import csv
import re

from rag import load_index, ingest_documents
import traceback


# ==================== LIFESPAN (STARTUP) ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to Qdrant vector store on server startup."""
    try:
        load_index()
        print("Qdrant index connected successfully!")
    except RuntimeError:
        print("WARNING: Qdrant collection not found. Run 'python ingest.py' first.")
    yield


# ==================== APP ====================
app = FastAPI(title="AIDA – AI-Driven Department Agent API", lifespan=lifespan)

# ==================== CORS ====================
# Restrict to the frontend origin. Set FRONTEND_URL in .env for production.
# Defaults to localhost:3000 for local development.
_ALLOWED_ORIGINS_RAW = os.getenv("FRONTEND_URL", "http://localhost:3000")
_ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in _ALLOWED_ORIGINS_RAW.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# ==================== SUPABASE CONFIG ====================
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
if SUPABASE_URL.endswith("/rest/v1"):
    SUPABASE_URL = SUPABASE_URL[:-len("/rest/v1")].rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Supabase environment variables not set")

# Note: LLM is now configured inside agents/ (supervisor, timetable_agent, response_writer)

# ==================== AUTH (SUPABASE) ====================
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        response = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
            },
            timeout=10
        )

        if response.status_code != 200:
            print(f"Supabase auth failed with status {response.status_code}: {response.text}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user_data = response.json()
        
        # Verify role
        user_role = "student"
        try:
            role_resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/user_roles?id=eq.{user_data['id']}&select=role",
                headers={
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "apikey": SUPABASE_SERVICE_ROLE_KEY,
                },
                timeout=5
            )
            if role_resp.status_code == 200:
                roles = role_resp.json()
                if roles and len(roles) > 0 and roles[0].get("role"):
                    user_role = roles[0].get("role")
        except Exception as e:
            print(f"Error fetching role: {e}")
            user_role = "student"

        # Fallback to user_metadata if role was not found in user_roles table
        if user_role == "student" and user_data.get("user_metadata", {}).get("role"):
            user_role = user_data["user_metadata"]["role"]

        user_data["role"] = user_role
        user_data["is_admin"] = (user_role == "admin")
        user_data["is_faculty"] = (user_role in ("faculty", "admin"))

        return user_data
    except requests.exceptions.RequestException as e:
        print(f"Supabase network error: {e}")
        raise HTTPException(status_code=500, detail=f"Auth network error: {str(e)}")
    except Exception as e:
        print(f"Unexpected auth error: {e}")
        raise HTTPException(status_code=500, detail=f"Auth internal error: {str(e)}")

def require_admin(user=Depends(get_current_user)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

def require_faculty_or_admin(user=Depends(get_current_user)):
    if not (user.get("is_admin") or user.get("is_faculty")):
        raise HTTPException(status_code=403, detail="Faculty or Admin privileges required")
    return user

# ==================== HEALTH & CONFIG ====================
from department_config import get_department_metadata, DEPARTMENT_CODE, DEPARTMENT_NAME

@app.get("/")
def root():
    return {
        "message": "AIDA – AI-Driven Department Agent API running",
        "department": DEPARTMENT_CODE,
        "department_name": DEPARTMENT_NAME
    }

@app.get("/department/config")
def get_config():
    """Return department metadata, subjects, sections, and laboratories."""
    return get_department_metadata()

# ==================== CURRENT USER ====================
@app.get("/me")
def me(user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user.get("role", "student"),
        "is_admin": user.get("is_admin", False),
        "is_faculty": user.get("is_faculty", False)
    }

# ==================== ASSIGN ROLE ====================
class RoleAssignRequest(BaseModel):
    user_id: str
    role: str

@app.post("/assign-role")
def assign_role(request: RoleAssignRequest):
    if request.role not in ["student", "faculty", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'student', 'faculty', or 'admin'.")
        
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/user_roles",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            },
            json={"id": request.user_id, "role": request.role},
            timeout=5
        )
        if response.status_code not in (200, 201, 204):
            print(f"[Assign-Role Error] Supabase returned status {response.status_code}: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Failed to assign role: {response.text}")
        return {"message": "Role assigned successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Assign-Role Exception] {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== TAG STORAGE HELPERS ====================
_BACKEND_DIR = Path(__file__).resolve().parent
DOC_TAGS_PATH = str(_BACKEND_DIR / "doc_tags.json")
DOCS_DATA_DIR = _BACKEND_DIR / "data" / "docs"
NOTICES_DATA_DIR = _BACKEND_DIR / "data" / "notices"
TIMETABLE_DATA_DIR = _BACKEND_DIR / "data" / "timetable"

# Allowlist for uploaded file extensions (documents only)
_ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".md", ".txt", ".docx"}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

def _load_tags() -> dict:
    if not os.path.exists(DOC_TAGS_PATH):
        return {}
    with open(DOC_TAGS_PATH, "r") as f:
        return json.load(f)

def _save_tags(tags: dict) -> None:
    with open(DOC_TAGS_PATH, "w") as f:
        json.dump(tags, f, indent=2)

def _safe_filename(filename: str) -> str:
    """Strip any directory component and reject traversal attempts."""
    name = os.path.basename(filename)
    if not name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return name

# ==================== FILE UPLOAD (FACULTY / ADMIN) ====================
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    department: str = Form(default=DEPARTMENT_CODE),
    category: str = Form(default="Academic Resources"),
    year: str = Form(default=""),
    course: str = Form(default=""),
    user=Depends(require_faculty_or_admin),
):
    # Validate filename and extension
    safe_name = _safe_filename(file.filename or "")
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in _ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Supported: {', '.join(_ALLOWED_UPLOAD_EXTENSIONS)}"
        )

    # Read and size-check before writing
    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds maximum allowed size of 20 MB")

    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = DOCS_DATA_DIR / safe_name

    with open(dest_path, "wb") as f:
        f.write(contents)

    # Save tags for this file
    tags = _load_tags()
    tags[safe_name] = {
        "department": department.strip() or DEPARTMENT_CODE,
        "category": category.strip() or "Academic Resources",
        "year": year.strip(),
        "course": course.strip(),
    }
    _save_tags(tags)

    return {
        "message": f"Document '{safe_name}' uploaded successfully",
        "path": str(dest_path.relative_to(_BACKEND_DIR)),
        "tags": tags[safe_name]
    }

# ==================== ADMIN & FACULTY DOC ROUTING ====================
@app.get("/admin/docs")
def list_admin_docs(user=Depends(require_faculty_or_admin)):
    if not DOCS_DATA_DIR.exists():
        return []
    
    tags = _load_tags()
    files = []
    for filename in sorted(DOCS_DATA_DIR.iterdir()):
        if filename.suffix == ".json" or not filename.is_file():
            continue
        file_tags = tags.get(filename.name, {})
        files.append({
            "name": filename.name,
            "size": filename.stat().st_size,
            "department": file_tags.get("department", DEPARTMENT_CODE),
            "category": file_tags.get("category", "Academic Resources"),
            "year": file_tags.get("year", ""),
            "course": file_tags.get("course", ""),
        })
    return files

@app.delete("/admin/docs/{filename}")
def delete_admin_doc(filename: str, user=Depends(require_admin)):
    safe_name = _safe_filename(filename)
    file_path = DOCS_DATA_DIR / safe_name
    
    if not file_path.resolve().is_relative_to(DOCS_DATA_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        file_path.unlink()
        # Also clean up tags entry
        tags = _load_tags()
        tags.pop(safe_name, None)
        _save_tags(tags)
        return {"message": f"Deleted {safe_name} successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/docs/{filename}/view")
def view_admin_doc(filename: str, user=Depends(require_faculty_or_admin)):
    safe_name = _safe_filename(filename)
    file_path = DOCS_DATA_DIR / safe_name
    
    # Path traversal protection
    if not file_path.resolve().is_relative_to(DOCS_DATA_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(str(file_path))

@app.get("/admin/logs")
def get_admin_logs(user=Depends(require_admin)):
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/chat_logs?select=*&order=created_at.desc&limit=100",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
            },
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=500, detail="Failed to fetch logs")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-timetable")
async def upload_timetable(
    file: UploadFile = File(...),
    group: str = Form(default=""),
    user=Depends(require_admin)
):
    TIMETABLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if group.strip():
        # Save group-specific file: timetable_CS-A.csv, timetable_CS-B.csv etc.
        safe_group = group.strip().upper().replace(" ", "-")
        path = TIMETABLE_DATA_DIR / f"timetable_{safe_group}.csv"
    else:
        # Falling back to shared / global timetable
        path = TIMETABLE_DATA_DIR / "timetable.csv"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {
        "message": "Timetable uploaded successfully",
        "path": os.path.join("data", "timetable", path.name),
    }

@app.post("/upload-deadlines")
async def upload_deadlines(file: UploadFile = File(...), user=Depends(require_admin)):
    TIMETABLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = TIMETABLE_DATA_DIR / "deadlines.csv"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"message": "Deadlines uploaded successfully"}

def _read_timetable_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read schedule CSV: {exc}") from exc

@app.get("/deadlines")
def get_student_deadlines(user=Depends(get_current_user)):
    """Return read-only deadline data for authenticated department users."""
    rows = _read_timetable_csv(TIMETABLE_DATA_DIR / "deadlines.csv")
    return sorted(rows, key=lambda row: row.get("due_date", ""))

@app.get("/timetable")
def get_student_timetable(group: str = "AIML-A", user=Depends(get_current_user)):
    """Return the requested section timetable to authenticated department users."""
    group_name = group.strip().upper().replace(" ", "-")
    if not re.fullmatch(r"[A-Z0-9-]+", group_name):
        raise HTTPException(status_code=400, detail="Invalid timetable section")

    group_path = TIMETABLE_DATA_DIR / f"timetable_{group_name}.csv"
    if group_path.exists():
        return _read_timetable_csv(group_path)

    rows = _read_timetable_csv(TIMETABLE_DATA_DIR / "timetable.csv")
    if rows and "student_group" in rows[0]:
        rows = [row for row in rows if row.get("student_group", "").strip().upper() == group_name]
    return rows

@app.get("/admin/deadlines")
def get_admin_deadlines(user=Depends(require_admin)):
    """Read deadlines.csv and return rows as a list of dicts."""
    path = TIMETABLE_DATA_DIR / "deadlines.csv"
    if not path.exists():
        return {"exists": False, "rows": [], "headers": []}
    try:
        rows = _read_timetable_csv(path)
        headers = list(rows[0].keys()) if rows else []
        return {
            "exists": True,
            "rows": rows,
            "headers": headers,
            "size": path.stat().st_size,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/deadlines")
def delete_admin_deadlines(user=Depends(require_admin)):
    """Delete the uploaded deadlines.csv file."""
    path = TIMETABLE_DATA_DIR / "deadlines.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No deadlines file found")
    try:
        path.unlink()
        return {"message": "Deadlines deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/notices")
def get_admin_notices(user=Depends(require_admin)):
    path = NOTICES_DATA_DIR / "notices.json"
    if not path.exists():
        return []
    with open(path, "r") as f:
        return json.load(f)

@app.get("/admin/timetable")
def get_admin_timetable(user=Depends(require_admin)):
    """List all uploaded timetable files with their row counts."""
    timetable_dir = TIMETABLE_DATA_DIR
    if not timetable_dir.exists():
        return []
    results = []
    for fname in sorted(os.listdir(timetable_dir)):
        if not fname.endswith(".csv") or fname == "deadlines.csv":
            continue
        fpath = timetable_dir / fname
        try:
            rows = _read_timetable_csv(fpath)
            # Derive the group label from the filename
            if fname == "timetable.csv":
                group_label = "Shared / Global"
            else:
                group_label = fname.replace("timetable_", "").replace(".csv", "")
            # Read column headers for the first file to show in preview
            headers = list(rows[0].keys()) if rows else []
            results.append({
                "filename": fname,
                "group": group_label,
                "rows": rows,
                "headers": headers,
                "row_count": len(rows),
                "size": fpath.stat().st_size,
            })
        except Exception as e:
            results.append({"filename": fname, "group": fname, "error": str(e), "rows": [], "headers": [], "row_count": 0, "size": 0})
    return results

@app.delete("/admin/timetable/{filename}")
def delete_admin_timetable(filename: str, user=Depends(require_admin)):
    """Delete a specific timetable file by filename (e.g. timetable_CS-A.csv)."""
    timetable_dir = os.path.abspath(TIMETABLE_DATA_DIR)
    file_path = os.path.join(timetable_dir, filename)
    if not file_path.startswith(timetable_dir):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.endswith(".csv") or filename == "deadlines.csv":
        raise HTTPException(status_code=400, detail="Invalid file")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        os.remove(file_path)
        return {"message": f"Deleted {filename} successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/notices/{notice_index}")
def delete_admin_notice(notice_index: int, user=Depends(require_admin)):
    """Delete a single notice by its index in the notices.json array."""
    path = NOTICES_DATA_DIR / "notices.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="notices.json not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if notice_index < 0 or notice_index >= len(data):
            raise HTTPException(status_code=404, detail="Notice index out of range")
        data.pop(notice_index)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"message": "Notice deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-notices")
async def upload_notices(file: UploadFile = File(...), user=Depends(require_admin)):
    # Only allow .json uploads for notices
    safe_name = _safe_filename(file.filename or "notices.json")
    if not safe_name.endswith(".json"):
        raise HTTPException(status_code=400, detail="Notices file must be a .json file")
    NOTICES_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = NOTICES_DATA_DIR / "notices.json"
    contents = await file.read()
    # Validate JSON before writing
    try:
        json.loads(contents)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in notices file")
    with open(path, "wb") as f:
        f.write(contents)
    return {"message": "Notices updated successfully"}

@app.post("/rebuild-index")
def rebuild_index(user=Depends(require_admin)):
    try:
        # Read saved tags and pass to ingestion
        tags_map = _load_tags()
        chunks_count = ingest_documents(str(DOCS_DATA_DIR), tags_map=tags_map)
        # Reload the index into memory
        load_index()
        return {
            "message": "Search index rebuilt successfully!",
            "chunks_count": chunks_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from graph import campus_graph

# ==================== CHAT SESSIONS ====================
@app.get("/chat/sessions")
def get_chat_sessions(user=Depends(get_current_user)):
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/chat_sessions?user_id=eq.{user['id']}&select=id,title,updated_at&order=updated_at.desc",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
            },
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch sessions")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/sessions/{session_id}")
def get_chat_session(session_id: str, user=Depends(get_current_user)):
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/chat_sessions?id=eq.{session_id}&user_id=eq.{user['id']}&select=messages",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if not data:
                raise HTTPException(status_code=404, detail="Session not found")
            return data[0]["messages"]
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch session")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SessionRenameRequest(BaseModel):
    title: str

@app.put("/chat/sessions/{session_id}")
def rename_chat_session(session_id: str, request: SessionRenameRequest, user=Depends(get_current_user)):
    try:
        response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/chat_sessions?id=eq.{session_id}&user_id=eq.{user['id']}",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Content-Type": "application/json",
            },
            json={"title": request.title},
            timeout=5
        )
        if response.status_code in (200, 204):
            return {"message": "Session renamed successfully"}
        raise HTTPException(status_code=response.status_code, detail="Failed to rename session")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id: str, user=Depends(get_current_user)):
    try:
        response = requests.delete(
            f"{SUPABASE_URL}/rest/v1/chat_sessions?id=eq.{session_id}&user_id=eq.{user['id']}",
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
            },
            timeout=5
        )
        if response.status_code in (200, 204):
            return {"message": "Session deleted successfully"}
        raise HTTPException(status_code=response.status_code, detail="Failed to delete session")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CHAT ====================
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    session_id: str | None = None

import json
import uuid

@app.post("/chat")
async def chat(request: ChatRequest, user=Depends(get_current_user)):
    # Generate new session ID if one doesn't exist
    session_id = request.session_id if request.session_id else str(uuid.uuid4())
    is_new_session = not bool(request.session_id)

    # Calculate title from first message
    title = request.message[:50] + "..." if len(request.message) > 50 else request.message

    if is_new_session:
        try:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/chat_sessions",
                headers={
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "apikey": SUPABASE_SERVICE_ROLE_KEY,
                    "Content-Type": "application/json",
                    "Prefer": "resolution=ignore-duplicates"
                },
                json={
                    "id": session_id,
                    "user_id": user["id"],
                    "title": title,
                    "messages": request.history + [{"role": "user", "content": request.message}],
                    "updated_at": "now()"
                },
                timeout=5
            )
        except Exception as e:
            print(f"Error pre-saving chat session: {e}")

    async def event_generator():
        import time
        start_time = time.time()
        final_intent = "unknown"
        
        # We need to accumulate the full trace array and final response to sync to the database
        assistant_traces = []
        assistant_response = ""
        
        try:
            # Yield the session_id first so the frontend can lock it in natively
            yield json.dumps({"type": "session_id", "session_id": session_id}) + "\n"
            
            # First trace
            trace_msg = "> [Supervisor Agent] Analyzing query intent..."
            assistant_traces.append(trace_msg)
            yield json.dumps({"type": "trace", "message": trace_msg}) + "\n"

            user_role = user.get("role", "student") if isinstance(user, dict) else getattr(user, "role", "student")
            user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
            user_email = user.get("email") if isinstance(user, dict) else getattr(user, "email", None)

            # Run the LangGraph multi-agent pipeline
            # pyrefly: ignore [missing-attribute]
            async for event in campus_graph.astream({
                "query": request.message,
                "history": request.history,
                "intent": "",
                "context": [],
                "sources": [],
                "response": "",
                "user_role": user_role,
                "user_id": user_id,
                "user_email": user_email,
            }, stream_mode="updates"):
                
                for node_name, state_update in event.items():
                    if node_name == "supervisor":
                        final_intent = state_update.get("intent", "unknown")
                        trace_msg = f"> [Supervisor Agent] Intent classified as: {final_intent.upper()}"
                        assistant_traces.append(trace_msg)
                        yield json.dumps({"type": "trace", "message": trace_msg}) + "\n"
                    
                    elif node_name == "rag_agent":
                        trace_msg = "> [RAG Agent] Searching vector database for relevant university documents..."
                        assistant_traces.append(trace_msg)
                        yield json.dumps({"type": "trace", "message": trace_msg}) + "\n"
                        
                    elif node_name == "timetable_agent":
                        trace_msg = "> [Timetable Agent] Querying Timetable MCP Server for live schedules and deadlines..."
                        assistant_traces.append(trace_msg)
                        yield json.dumps({"type": "trace", "message": trace_msg}) + "\n"

                    elif node_name == "faculty_agent":
                        trace_msg = "> [Faculty Agent] Querying department database for faculty directory, courses, and availability..."
                        assistant_traces.append(trace_msg)
                        yield json.dumps({"type": "trace", "message": trace_msg}) + "\n"

                    elif node_name == "events_agent":
                        trace_msg = "> [Event Agent] Searching department event calendar, workshops, and seminars..."
                        assistant_traces.append(trace_msg)
                        yield json.dumps({"type": "trace", "message": trace_msg}) + "\n"

                    elif node_name == "notices_agent":
                        trace_msg = "> [Notices Agent] Fetching latest announcements from department notice board..."
                        assistant_traces.append(trace_msg)
                        yield json.dumps({"type": "trace", "message": trace_msg}) + "\n"
                        
                    elif node_name == "planner_agent":
                        trace_msg = "> [Planner Agent] Generating personalized study schedule..."
                        assistant_traces.append(trace_msg)
                        yield json.dumps({"type": "trace", "message": trace_msg}) + "\n"

                    elif node_name == "requests_agent":
                        trace_msg = "> [Request Assistance Tool] Retrieving request guidelines, submission workflows, and human review policies..."
                        assistant_traces.append(trace_msg)
                        yield json.dumps({"type": "trace", "message": trace_msg}) + "\n"
                        
                    elif node_name == "response_writer":
                        trace_msg = "> [Response Writer] Synthesizing final response based on retrieved context..."
                        assistant_traces.append(trace_msg)
                        yield json.dumps({"type": "trace", "message": trace_msg}) + "\n"
                        
                        assistant_response = state_update.get("response", "")
                        yield json.dumps({
                            "type": "result",
                            "response": assistant_response,
                            "sources": state_update.get("sources", [])
                        }) + "\n"
            
            # Save the full chat state to Supabase
            # Note: We must construct the final messages array reflecting the user msg and new AI response
            updated_messages = request.history + [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": assistant_response, "traces": assistant_traces}
            ]

            payload = {
                "id": session_id,
                "user_id": user["id"],
                "title": title if is_new_session else None, # Only set title if new session, though we use upsert
                "messages": updated_messages,
                "updated_at": "now()"
            }
            if is_new_session:
                payload["title"] = title
            else:
                # If it's an existing session, we omit title to avoid overwriting it
                payload.pop("title", None)

            try:
                requests.post(
                    f"{SUPABASE_URL}/rest/v1/chat_sessions",
                    headers={
                        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                        "apikey": SUPABASE_SERVICE_ROLE_KEY,
                        "Content-Type": "application/json",
                        "Prefer": "resolution=merge-duplicates"
                    },
                    json=payload,
                    timeout=5
                )
            except Exception as db_err:
                print(f"Error saving chat session: {db_err}")

            # Log telemetry (existing)
            latency_ms = int((time.time() - start_time) * 1000)
            try:
                requests.post(
                    f"{SUPABASE_URL}/rest/v1/chat_logs",
                    headers={
                        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                        "apikey": SUPABASE_SERVICE_ROLE_KEY,
                        "Content-Type": "application/json"
                    },
                    json={
                        "user_id": user["id"],
                        "query": request.message,
                        "intent": final_intent,
                        "latency_ms": latency_ms
                    },
                    timeout=5
                )
            except Exception as e:
                print(f"Error saving chat log to Supabase: {e}")

        except Exception as e:
            print(f"Error in chat stream generator: {e}")
            traceback.print_exc()
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


# ==============================================================================
# AIDA DEPARTMENT ENTITIES & HUMAN APPROVAL WORKFLOW API
# ==============================================================================
import db_service
from typing import Optional, List

# -------------------- 1. FACULTY --------------------
class FacultyCreateRequest(BaseModel):
    name: str
    designation: str
    department: str = DEPARTMENT_CODE
    email: str
    contact_info: Optional[str] = None
    specialization: Optional[str] = None
    subjects_handled: Optional[List[str]] = []
    availability: Optional[str] = None

class FacultyUpdateRequest(BaseModel):
    name: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[str] = None
    contact_info: Optional[str] = None
    specialization: Optional[str] = None
    subjects_handled: Optional[List[str]] = None
    availability: Optional[str] = None
    is_active: Optional[bool] = None

@app.get("/faculty")
def list_faculty(department: str = DEPARTMENT_CODE):
    """Retrieve faculty directory for the department."""
    return db_service.get_faculty_list(department=department)

@app.post("/faculty")
def add_faculty(data: FacultyCreateRequest, user=Depends(require_admin)):
    """Create a new faculty record (Admin only)."""
    try:
        return db_service.create_faculty(data.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/faculty/{faculty_id}")
def edit_faculty(faculty_id: str, data: FacultyUpdateRequest, user=Depends(require_faculty_or_admin)):
    """Update a faculty record."""
    try:
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        return db_service.update_faculty(faculty_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/faculty/{faculty_id}")
def remove_faculty(faculty_id: str, user=Depends(require_admin)):
    """Remove a faculty record (Admin only)."""
    success = db_service.delete_faculty(faculty_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete faculty")
    return {"message": "Faculty deleted successfully"}


# -------------------- 2. STUDENTS --------------------
class StudentCreateRequest(BaseModel):
    enrollment_no: str
    full_name: str
    email: str
    department: str = DEPARTMENT_CODE
    semester: int = 6
    section: str = "AIML-A"
    batch_year: Optional[str] = "2023-2027"
    contact_number: Optional[str] = None

@app.get("/students")
def list_students(section: Optional[str] = None, user=Depends(require_faculty_or_admin)):
    """List students, optionally filtered by section (Faculty/Admin only)."""
    return db_service.get_students_list(section=section)

@app.get("/students/me")
def get_my_student_profile(user=Depends(get_current_user)):
    """Get the student profile associated with the currently authenticated user."""
    profile = db_service.get_student_by_user_id(user["id"])
    if not profile:
        return {
            "id": None,
            "user_id": user["id"],
            "email": user["email"],
            "full_name": user.get("email", "").split("@")[0].title(),
            "department": DEPARTMENT_CODE,
            "section": "AIML-A",
            "semester": 6
        }
    return profile

@app.post("/students")
def register_student(data: StudentCreateRequest, user=Depends(get_current_user)):
    """Register or save student profile."""
    payload = data.model_dump()
    payload["user_id"] = user["id"]
    try:
        return db_service.create_student(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class StudentUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[str] = None
    batch_year: Optional[str] = None
    contact_number: Optional[str] = None

@app.put("/students/{student_id}")
def edit_student(student_id: str, data: StudentUpdateRequest, user=Depends(require_admin)):
    """Update student record (Admin only)."""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        return db_service.update_student(student_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/students/{student_id}")
def remove_student(student_id: str, user=Depends(require_admin)):
    """Delete student record (Admin only)."""
    success = db_service.delete_student(student_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete student")
    return {"message": "Student record deleted successfully"}


# -------------------- 3. SUBJECTS --------------------
class SubjectCreateRequest(BaseModel):
    id: str
    name: str
    department: str = DEPARTMENT_CODE
    semester: int = 6
    credits: int = 3
    description: Optional[str] = None
    syllabus_url: Optional[str] = None
    faculty_in_charge_id: Optional[str] = None

class SubjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    semester: Optional[int] = None
    credits: Optional[int] = None
    description: Optional[str] = None

@app.get("/subjects")
def list_subjects(department: str = DEPARTMENT_CODE):
    """Retrieve catalog of academic subjects for the department."""
    return db_service.get_subjects_list(department=department)

@app.post("/subjects")
def create_subject(data: SubjectCreateRequest, user=Depends(require_admin)):
    """Create or update a subject in the catalog (Admin only)."""
    try:
        return db_service.create_subject(data.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/subjects/{subject_id}")
def edit_subject(subject_id: str, data: SubjectUpdateRequest, user=Depends(require_admin)):
    """Update subject in catalog (Admin only)."""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        return db_service.update_subject(subject_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/subjects/{subject_id}")
def remove_subject(subject_id: str, user=Depends(require_admin)):
    """Delete subject from catalog (Admin only)."""
    success = db_service.delete_subject(subject_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete subject")
    return {"message": "Subject deleted successfully"}


# -------------------- 4. EVENTS --------------------
class EventCreateRequest(BaseModel):
    title: str
    description: str
    date_time: str
    location: str
    organizer: str
    department: str = DEPARTMENT_CODE

class EventUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date_time: Optional[str] = None
    location: Optional[str] = None
    organizer: Optional[str] = None

@app.get("/events")
def list_events(upcoming: bool = False, department: str = DEPARTMENT_CODE):
    """List department events, hackathons, and guest lectures."""
    return db_service.get_events_list(department=department, upcoming_only=upcoming)

@app.get("/events/{event_id}")
def get_event(event_id: str):
    """Get details for a specific department event."""
    event = db_service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.post("/events")
def create_event(data: EventCreateRequest, user=Depends(require_faculty_or_admin)):
    """Create a new department event (Faculty/Admin only)."""
    payload = data.model_dump()
    payload["created_by"] = user["id"]
    try:
        return db_service.create_event(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/events/{event_id}")
def update_event(event_id: str, data: EventUpdateRequest, user=Depends(require_faculty_or_admin)):
    """Update event information (Faculty/Admin only)."""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        return db_service.update_event(event_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/events/{event_id}")
def delete_event(event_id: str, user=Depends(require_faculty_or_admin)):
    """Delete an event (Faculty/Admin only)."""
    success = db_service.delete_event(event_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete event")
    return {"message": "Event deleted successfully"}


# -------------------- 5. STUDENT REQUESTS (HUMAN APPROVAL WORKFLOW) --------------------
class StudentRequestCreate(BaseModel):
    request_type: str
    description: str
    student_id: Optional[str] = None

class StudentRequestStatusUpdate(BaseModel):
    status: str
    comments: Optional[str] = None
    assigned_to: Optional[str] = None

class StudentRequestReply(BaseModel):
    additional_info: str

@app.get("/requests")
def list_all_requests(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    user=Depends(require_faculty_or_admin)
):
    """
    List all student requests for faculty/admin review.
    Supports filtering by status ('Pending', 'Under Review', 'Approved', 'Rejected', 'More Information Required').
    """
    return db_service.get_student_requests(status=status, assigned_to=assigned_to)

@app.get("/requests/my")
def list_my_requests(user=Depends(get_current_user)):
    """List requests submitted by the currently logged-in student."""
    return db_service.get_student_requests(user_id=user["id"])

@app.get("/requests/{request_id}")
def get_student_request_detail(request_id: str, user=Depends(get_current_user)):
    """Get detailed student request data including full review history timeline."""
    req = db_service.get_student_request_by_id(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    # Authorization: Students can only view their own requests, while faculty/admin can view any request
    if not (user.get("is_faculty") or user.get("is_admin")):
        if req.get("user_id") and req["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Unauthorized to view this request")
    return req

@app.post("/requests")
def submit_student_request(data: StudentRequestCreate, user=Depends(get_current_user)):
    """Submit a new student request into the approval queue."""
    payload = data.model_dump()
    payload["user_id"] = user["id"]
    try:
        return db_service.create_student_request(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/requests/{request_id}/reply")
def reply_student_request(
    request_id: str,
    data: StudentRequestReply,
    user=Depends(get_current_user)
):
    """
    Student submits additional information requested by faculty/administrator.
    Transitions status from 'More Information Required' back to 'Under Review'.
    """
    actor_name = user.get("email", "Student").split("@")[0].replace(".", " ").title()
    try:
        updated = db_service.add_student_request_reply(
            request_id=request_id,
            user_id=user["id"],
            additional_info=data.additional_info,
            actor_name=actor_name
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Request not found or unauthorized")
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/requests/{request_id}/status")
def review_student_request(
    request_id: str,
    data: StudentRequestStatusUpdate,
    user=Depends(require_faculty_or_admin)
):
    """
    Human Approval Action:
    Faculty or Administrator approves, rejects, requests more information, or transitions a student request.
    """
    valid_statuses = {"Pending", "Under Review", "In Review", "Approved", "Rejected", "More Information Required"}
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    actor_name = user.get("email", "Staff").split("@")[0].replace(".", " ").title()
    actor_role = user.get("role", "faculty").capitalize()

    try:
        return db_service.update_student_request_status(
            request_id=request_id,
            status=data.status,
            comments=data.comments,
            assigned_to=data.assigned_to,
            actor_name=actor_name,
            actor_role=actor_role
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/requests/{request_id}")
def remove_student_request(request_id: str, user=Depends(require_admin)):
    """Delete student request (Admin only)."""
    success = db_service.delete_student_request(request_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete request")
    return {"message": "Request deleted successfully"}


# -------------------- 6. DB-BACKED NOTICES --------------------
class NoticeCreateRequest(BaseModel):
    title: str
    content: str
    department: str = DEPARTMENT_CODE
    category: str = "Academic"
    is_pinned: bool = False

class NoticeUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    is_pinned: Optional[bool] = None

@app.get("/db/notices")
def list_db_notices(department: str = DEPARTMENT_CODE, limit: int = 50):
    """Fetch notices from database."""
    return db_service.get_db_notices(department=department, limit=limit)

@app.post("/db/notices")
def add_db_notice(data: NoticeCreateRequest, user=Depends(require_faculty_or_admin)):
    """Add notice to database (Faculty/Admin only)."""
    payload = data.model_dump()
    payload["created_by"] = user["id"]
    try:
        return db_service.create_db_notice(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/db/notices/{notice_id}")
def edit_db_notice(notice_id: str, data: NoticeUpdateRequest, user=Depends(require_faculty_or_admin)):
    """Update notice in database (Faculty/Admin only)."""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        return db_service.update_db_notice(notice_id, update_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/db/notices/{notice_id}")
def remove_db_notice(notice_id: str, user=Depends(require_faculty_or_admin)):
    """Delete notice from database."""
    success = db_service.delete_db_notice(notice_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete notice")
    return {"message": "Notice deleted successfully"}


# -------------------- 7. DEPARTMENT OVERVIEW & ANALYTICS --------------------
@app.get("/admin/overview")
def get_admin_overview(user=Depends(require_admin)):
    """Aggregated department statistics for the Admin Dashboard."""
    return db_service.get_department_overview_stats()
