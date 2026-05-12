# Lumina v2 — Claude Code Context

## What is Lumina
An AI-powered Socratic tutoring platform for students, built on top of Canvas LMS.
NOT a Canvas replacement. NOT a teacher tool. A student study companion.

**Pilot school:** Dwight Global Online School (USA) — dwight.instructure.com
**Domicile:** New York + Florida (triggers specific state privacy laws — see Compliance)
**Why it exists:** Online students are alone when stuck. Canvas AI is teacher-configured
and assignment-scoped. Lumina is student-initiated, always-on, and knows the student's
full course context including private materials (textbooks etc).

**Differentiator vs Canvas IgniteAI:**
Canvas builds AI for teachers (grading, rubrics, assignment setup).
Lumina is for students at 11pm who are stuck and have no teacher to ask.

---

## Codebase
- **Local path:** /Users/ny/Downloads/CursorProjects/Lumina-v2/
- **GitHub:** AYDXB09/Lumina-v2 (SSH: git@github-aydxb09:AYDXB09/Lumina-v2.git)
- **SSH key:** ~/.ssh/id_ed25519_aydxb09 | Host alias: github-aydxb09
- **Stack:** React 19 + Vite (frontend) + FastAPI Python (backend)
- **Old hackathon repo:** /Users/ny/Downloads/CursorProjects/School-AI/school-ai/ — DO NOT TOUCH

### Built in v2 (this repo)
- Canvas API Key auth (JWT + httpOnly refresh cookie, sessions in Supabase)
- Provider abstraction layer: AI (K2 / OpenRouter / Anthropic / NVIDIA NIM / Groq / Gemini), Storage (Supabase), Email (Resend)
- Canvas sync: courses, modules, pages, assignments, announcements → Supabase
- pgvector RAG: sentence-transformers all-MiniLM-L6-v2 (384-dim), HNSW index
- SSE streaming chat with tool-call loop (K2/OpenRouter/Anthropic) or direct stream (DeepSeek/Llama/Groq)
- SSE heartbeat pings every 5s (queue-based, not wait_for) — prevents Railway proxy from dropping idle connections
- Chat history persisted to Supabase, restored on course switch; capped at 4 messages sent to AI (token budget)
- System prompt injection: today's date + enrolled courses + active course name + upcoming assignments + quizzes/exams + calendar events (15-day window)
- Proactive RAG injection: top 3 course content chunks semantically matched to user's query, injected before AI call
- AI provider + model switchable at runtime via Supabase `global_config` table (no redeploy needed, 60s cache)
- React frontend: Sidebar (course list, no "All Courses") + ChatView (SSE streaming + thinking timer + persistent per-message timer + working stop button) + LoginScreen
- iCal calendar integration: personal calendars + Canvas auto-calendar, JSONB cache, injected into AI context
- RightPanel: 5 tabs — Assignments / Notices / Quizzes / Feedback / Mind Map
- SettingsModal: 5 tabs — General / Calendar / Materials / Admin KB (teachers only) / Account
- Auto-index Canvas content on first student login (background task)
- WelcomeScreen quick-action buttons in ChatView (course-specific + global)
- Mind map: pure React SVG, hierarchical tree layout, zoom/pan, "Ask AI" integration
- Student material upload: multi-file + folder select, filename tag extraction, tag-aware embeddings
- Admin knowledge base: shared_materials table, grade/subject/doc_type tagging, bulk upload
- Embedding model pre-warmed on startup (eliminates cold-start delay on first sign-in)
- Subject prompt modules: Economics (EconGraphs iframes), Mathematics (Desmos), Physics (PhET) — lazy-loaded per course
- Interactive widgets: `[ECONGRAPH: id]`, `[DESMOS: id]`, `[PHET: id]` markers rendered as collapsible iframes in chat

### Not yet ported from v1
- Adaptive quiz generator
- Voice mode (STT/TTS)

---

## Running Locally

### One command (recommended)
```bash
cd /Users/ny/Downloads/CursorProjects/Lumina-v2
./dev.sh
```
Starts backend (:8000) + frontend (:5173) together. Ctrl+C stops both.
Kills any existing processes on those ports automatically.

### Manual (if needed)
```bash
# Backend
cd /Users/ny/Downloads/CursorProjects/Lumina-v2/backend
python3 main.py

# Frontend (separate terminal)
cd /Users/ny/Downloads/CursorProjects/Lumina-v2/frontend
npm run dev
```

### .env location
`/Users/ny/Downloads/CursorProjects/Lumina-v2/backend/.env`
Note: .env changes require backend restart

---

## Tech Stack — Dual Architecture

Two deployment targets sharing identical application code.
Only infrastructure layer differs — environment variables switch providers.

### Non-AWS (default)
| Layer | Tech | Notes |
|---|---|---|
| Frontend + Backend | FastAPI serves React build | Single Railway service, one URL |
| Database | Supabase (Postgres + pgvector) | US East region |
| AI | Configurable via AI_PROVIDER env var | See providers below |
| File storage | Supabase Storage | Student uploads (PDFs, textbooks) |
| Email | Resend | DPA available, no SES sandbox issues |
| Secrets | Railway Variables | Simple env var management |

### AWS (later — for schools that require it)
| Layer | Tech | Notes |
|---|---|---|
| Frontend + Backend | ECS Fargate (same Docker image) | |
| Database | RDS Postgres + pgvector | |
| AI | Bedrock (Claude) | AWS DPA covers no-training guarantee |
| File storage | S3 | |
| Email | Resend | SES excluded — production access unreliable |
| Secrets | AWS Secrets Manager | |

### AI Provider Abstraction
**Primary control: Supabase `global_config` table (no redeploy needed)**
```sql
UPDATE global_config SET value = 'groq'                    WHERE key = 'ai_provider';
UPDATE global_config SET value = 'llama-3.3-70b-versatile' WHERE key = 'ai_model';
```
Takes effect within 60 seconds (cache TTL). Falls back to env vars if no DB row.

Env var fallback (requires redeploy):
```
AI_PROVIDER=k2          → K2Provider
AI_PROVIDER=openrouter  → OpenRouterProvider
AI_PROVIDER=anthropic   → AnthropicProvider
AI_PROVIDER=nvidia      → NvidiaProvider  (NVIDIA NIM)
AI_PROVIDER=groq        → GroqProvider    (LPU — fast)
AI_PROVIDER=gemini      → GeminiProvider  (Google AI Studio)
```

**Tool calling support:**
- K2, OpenRouter, Anthropic: full OpenAI-style tool calling
- Llama + DeepSeek: tool loop disabled — uses pre-injected context + proactive RAG instead
  - Controlled by `MODELS_WITHOUT_TOOL_SUPPORT = ("deepseek", "llama")` in `backend/chat/engine.py`
- Tool loop also disabled whenever `course_id` is set (context already pre-injected)

**Currently running:** Groq `llama-3.3-70b-versatile` (3–8s responses)
**Railway env vars needed:** `AI_PROVIDER=groq`, `GROQ_API_KEY=...`, `GROQ_MODEL=llama-3.3-70b-versatile`

**Groq free tier limits:** 12,000 TPM. System prompt ~3,200 tokens + 4-message history. Stays under limit for normal use.
If hitting limits: switch model in Supabase to `llama-3.1-8b-instant` (higher TPM, lower quality).

**Performance:** Course selected → assignments + quizzes + calendar (15-day window) + top 3 RAG chunks pre-injected → 1 AI call per message.

---

## Railway Deployment

**Status:** In progress — account created, GitHub repo connected, env vars set, first deploy triggered.

### Deployed service
- **Platform:** Railway (railway.app)
- **Account:** AYDXB09 (GitHub SSO)
- **Repo:** AYDXB09/Lumina-v2 — auto-deploys on every push to `main`
- **URL:** https://lumina-v2-production.up.railway.app

### Environment variables set in Railway
| Variable | Value | Notes |
|---|---|---|
| `SUPABASE_URL` | https://tnholnjrhnnqytmpqacb.supabase.co | |
| `SUPABASE_SERVICE_KEY` | ... | Service role key |
| `JWT_SECRET` | ... | Same as local .env |
| `ENCRYPTION_KEY` | ... | Fernet key |
| `AI_PROVIDER` | `groq` | ⚠️ Update if not done yet |
| `GROQ_API_KEY` | `gsk_...` | |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | ⚠️ Update if not done yet |
| `NVIDIA_API_KEY` | ... | Keep for fallback |
| `REFRESH_EXPIRE_DAYS` | `90` | |
| `RESEND_API_KEY` | ... | |
| `ALLOWED_ORIGINS` | `https://lumina-v2-production.up.railway.app` | |

### Post-deploy checklist
- [x] Railway deployed and live
- [x] `/health` returns `{"status":"ok","provider":"groq",...}`
- [x] SSE heartbeat prevents proxy timeout
- [ ] Test login with Canvas API key on Railway
- [ ] Enable "Remove on Inactivity" in Railway service settings

### Local vs Railway workflow
- **Daily dev:** `./dev.sh` (localhost only — free, instant restarts)
- **External testing:** push to GitHub → Railway auto-deploys in ~3 min
- **Cost:** Railway Hobby $5/month + $5 credit. "Remove on Inactivity" keeps costs near zero when not actively testing.

### Architecture note
FastAPI serves the React build as a SPA catch-all. The Dockerfile builds the frontend
(`npm run build`) and copies `dist/` into `backend/static/` before starting uvicorn.
Single Railway service, single public URL — no separate frontend hosting needed.

---

## Supabase Project (Lumina)
- **Project ID:** tnholnjrhnnqytmpqacb
- **URL:** https://tnholnjrhnnqytmpqacb.supabase.co
- **Region:** US East (North Virginia)
- **MCP:** supabase-lumina (configured in .mcp.json at project root)

---

## Authentication

### Current: Canvas API Key
Student generates their own Canvas API key (Account → Settings → New Access Token)
and pastes it into Lumina. No admin approval needed.

**Session flow:**
1. Student submits Canvas URL + API key
2. Backend validates via `/api/v1/users/self`
3. Upserts school + user in Supabase, encrypts Canvas token (Fernet)
4. Issues Lumina JWT (7 days) + refresh token (90 days, httpOnly cookie)
5. Silent refresh on expiry — student never re-enters Canvas key
6. Only re-prompts after 90 days inactive
7. First login detected → background task auto-syncs + indexes all Canvas courses

**Auth response key:** Always returns `canvas_role` (not `role`) — both login and `/auth/me` are consistent.
Frontend isAdmin check falls back on both keys: `(user.canvas_role || user.role || "")`.

### Admin / Teacher role
`ADMIN_ROLES = ("TeacherEnrollment", "TaEnrollment", "DesignerEnrollment", "AccountAdmin", "teacher", "admin")`
in `backend/admin/routes.py`. Substring match on lowercase `canvas_role`.
SettingsModal shows "Admin KB" tab for matching roles.

### Future auth (same DB schema, same Canvas API calls)
- **Canvas OAuth2** — requires Developer Key from Dwight Canvas admin
- **LTI 1.3** — requires school IT, unlocks deep linking + roster provisioning

---

## Key Files
| File | Purpose |
|---|---|
| `backend/main.py` | FastAPI app, routes wired, SPA catch-all; embedder pre-warm in lifespan |
| `backend/auth/routes.py` | Canvas API key login, JWT, refresh, logout; first-login auto-index |
| `backend/auth/middleware.py` | JWT dependency, role guards |
| `backend/auth/canvas.py` | Canvas token validation + retrieval abstraction |
| `backend/auth/encrypt.py` | Fernet encryption for Canvas tokens at rest |
| `backend/canvas/client.py` | Canvas REST client (pagination, HTML stripping, get_profile) |
| `backend/canvas/sync.py` | sync_courses(), get_course_content(), _ensure_canvas_ical() |
| `backend/canvas/routes.py` | /api/canvas/courses — list, sync, index |
| `backend/cal/__init__.py` | Empty — package named `cal` (NOT `calendar` — stdlib conflict) |
| `backend/cal/parser.py` | iCal fetch+parse: fetch_and_parse(), RRULE expansion, webcal:// handling |
| `backend/cal/routes.py` | /api/calendar — sources CRUD, events, sync, prompt endpoint |
| `backend/rag/embedder.py` | all-MiniLM-L6-v2 singleton; pre-warmed on startup |
| `backend/rag/indexer.py` | chunk + embed + store in pgvector; `_build_tag_prefix()` for tag-aware embeddings |
| `backend/rag/search.py` | match_index_chunks + match_student_materials RPC |
| `backend/chat/engine.py` | Tool-call loop + direct stream, system prompt builder (_build_system_prompt) |
| `backend/chat/prompt.py` | Socratic tutor system prompt |
| `backend/chat/tools.py` | ToolExecutor — reads from Supabase cache |
| `backend/chat/routes.py` | POST /api/chat/stream (SSE), sessions CRUD |
| `backend/materials/routes.py` | Multi-file upload, filename tag extraction, student RAG indexing |
| `backend/mindmap/routes.py` | /api/mindmap/{course_id} — get, save, regenerate |
| `backend/admin/routes.py` | Admin KB upload (shared_materials), list, delete, patch tags |
| `backend/providers/ai/` | K2, OpenRouter, Anthropic, NVIDIA, Groq, Gemini providers |
| `backend/providers/ai/__init__.py` | Factory with Supabase global_config lookup (60s cache); no lru_cache |
| `backend/chat/subject_prompts/` | Per-subject prompt modules; dispatcher lazy-imports only matching subject |
| `frontend/src/components/InteractiveWidget.jsx` | Collapsible iframe for ECONGRAPH/DESMOS/PHET markers |
| `frontend/src/components/ChatMessage.jsx` | Parses widget markers from AI output via parseSegments() |
| `backend/config.py` | All env vars |
| `frontend/src/App.jsx` | Auth gate → MainLayout; auto-selects first course; chatSendRef for RightPanel→Chat |
| `frontend/src/contexts/AuthContext.jsx` | In-memory JWT, cookie refresh, authFetch |
| `frontend/src/contexts/SettingsContext.jsx` | User settings with defaults incl. calendarFetchWindow, calendarSyncFrequency |
| `frontend/src/components/LoginScreen.jsx` | Canvas URL + API key form |
| `frontend/src/components/Sidebar.jsx` | Course list (no All Courses), sync button, user info |
| `frontend/src/components/ChatView.jsx` | SSE chat, tool status, history restore, thinking timer, persistent per-message timer, WelcomeScreen quick actions |
| `frontend/src/components/RightPanel.jsx` | 5-tab panel: Assignments / Notices / Quizzes / Feedback / Mind Map |
| `frontend/src/components/MindMapView.jsx` | Pure React SVG mind map; drag/zoom/fit; "Ask AI" integration |
| `frontend/src/components/SettingsModal.jsx` | 5-tab modal: General / Calendar / Materials / Admin KB / Account |
| `frontend/src/api.js` | streamChat(), fetchCourses(), uploadMaterial() (multi-file), fetchMindMap(), fetchAdminMaterials(), etc. |
| `.mcp.json` | Supabase MCP config |

---

## DB Schema (all migrations applied to Supabase)

### Core Identity
- `schools` — id, name, canvas_url, created_at
- `users` — id, canvas_user_id, school_id, name, email, avatar_url, canvas_role,
  auth_method, canvas_access_token (encrypted), canvas_refresh_token,
  canvas_token_expires_at, last_active_at,
  **calendar_sources JSONB** (list of {id, label, url, auto} objects)
- `sessions` — id, user_id, refresh_token (hashed), auth_method, expires_at,
  last_used_at, user_agent
- `enrollments` — user_id, course_id, canvas_role, synced_at
- `parent_links` — id, student_id, parent_email, consent_status,
  reporting_frequency, token, consented_at

### Canvas Sync
- `courses` — id, canvas_course_id, school_id, name, course_code, canvas_data JSONB, synced_at
- `index_chunks` — id, course_id, source_type, source_id, content,
  embedding vector(384), metadata JSONB
  - source_type: page / assignment / announcement / file / **quiz**
  - metadata includes: title, due_at, is_exam (bool), time_limit, points_possible
  - HNSW index on embedding (vector_cosine_ops)
- Supabase RPC functions: `match_index_chunks`, `match_student_materials`

### Calendar
- `calendar_cache` — user_id, source_id, label, events JSONB (array of expanded event objects), fetched_at
  - Unique constraint on (user_id, source_id)
  - One row per source per user — upsert on refresh, never written on fetch failure
  - Event schema: {uid, title, start (ISO-8601), end (ISO-8601), all_day, location, description, type, url}
  - event.type: "class" | "assignment_due" | "personal" | "other"

### Student Activity
- `student_materials` — id, user_id, course_id, filename, content,
  embedding vector(384), metadata JSONB, uploaded_at
  - metadata includes: subjects[], grade_levels[], doc_type, original_filename, size_bytes
- `chat_sessions` — id, user_id, course_id, title, created_at, updated_at
- `chat_messages` — id, session_id, role (user/assistant), content, thinking JSONB, created_at
- `quiz_attempts` — id, user_id, course_id, questions JSONB, answers JSONB, score, difficulty, created_at
- `mastery_scores` — id, user_id, course_id, concept, score FLOAT, evidence JSONB, updated_at
- `mind_maps` — id, user_id, course_id, graph_data JSONB, updated_at

### Admin Knowledge Base
- `shared_materials` — id, school_id, uploaded_by, filename, content, embedding vector(384),
  tags JSONB, metadata JSONB, uploaded_at
  - tags: {grade_levels[], subjects[], doc_type, expiry_date, applicable, chunk}
  - metadata: {title, description, source, chunk, total_chunks}
  - HNSW index on embedding; GIN index on tags
- Supabase RPC: `match_shared_materials` — grade_level `@>` containment, expiry date, applicable filters

### Platform Config
- `ai_config` — id, school_id, provider, model_id, api_key_encrypted, settings JSONB (per-school, has FK constraint)
- `global_config` — key TEXT PRIMARY KEY, value TEXT — global platform settings (no FK)
  - `ai_provider` → active AI provider (e.g. "groq")
  - `ai_model` → active model name (e.g. "llama-3.3-70b-versatile")
  - Change here takes effect in <60s — no redeploy needed
- `feature_flags` — school_id, feature, enabled
- `audit_logs` — id, user_id, action, target_type, target_id, metadata JSONB, created_at
- `api_usage` — id, school_id, user_id, model_id, input_tokens, output_tokens, created_at
- `notifications` — id, user_id, type, payload JSONB, sent_at, read_at

---

## Architecture Decisions

### Chat Performance
- Enrolled courses pre-injected into system prompt on every request
- Active course name explicitly stated: "Currently active course: X" — AI never asks "which course?"
- When a course is selected: assignments + quizzes/exams injected → tool loop disabled → 1 AI call
- Calendar events (15-day window) injected if user has calendars connected
- Proactive RAG: top 3 semantically matched course content chunks injected per query
- When no course selected: tool loop enabled → AI can call get_assignments, get_announcements, search_course_content
- Conversation history capped at 4 messages before sending to AI (token budget control)
- All tool reads from Supabase cache (not live Canvas) — fast

### Tool Calling
- Tools read from Supabase (already synced) — not live Canvas API
- Disabled for: Llama + DeepSeek models (MODELS_WITHOUT_TOOL_SUPPORT) AND whenever course_id is set
- Proactive RAG injection compensates for disabled tools on Groq/Llama

### Stream Reliability (routes.py + engine.py)
- SSE heartbeat: queue-based producer/consumer pattern in `routes.py`
  - Producer task runs `run_chat()` independently, feeds asyncio.Queue
  - Consumer yields `: heartbeat\n\n` every 5s of silence — keeps Railway proxy alive
  - DO NOT use `asyncio.wait_for(__anext__())` — it corrupts async generator state on cancellation
- Per-token timeout: `_aiter_with_timeout(60s)` in direct stream path
- Stop button: AbortController in `streamChat()` (api.js), abort fn stored in `abortRef` in ChatView
- Timing logs: `system_prompt_build=Xs prompt_chars=N` and `ttft=Xs model=...`

### System Prompt Injection (_build_system_prompt in engine.py)
Injects in order:
1. Today's date + active model name + tool capability note
2. Student's enrolled courses + **active course name** (bold, explicit)
3. If course selected: assignments (with `[EXAM]` tag) + quizzes/exams (with `[QUIZ]`/`[EXAM]` tags, time_limit)
4. Calendar events from `calendar_cache` — **15-day** forward window, all sources merged
   - Multi-day events displayed as range: `"Sat 10 May–Sun 11 May"` — AI told ALL days are blocked
   - Filter: `(start_date <= window_end_date) AND (end_date >= now_date)` — catches ongoing multi-day events
5. Subject prompt module (Economics/Physics/Maths) — lazy-loaded only for matching course
6. Proactive RAG chunks — top 3 results from semantic search on user's query

### Socratic Method (prompt.py)
- **Factual questions** (exam structure, syllabus, definitions, dates): answer directly and completely first
- **Problem-solving questions** (how do I solve X, why does Y happen): guide with hints, Socratic method
- DO NOT apply Socratic method to factual lookups — students need information, not questions

### Calendar Integration
- **Storage:** `users.calendar_sources` JSONB (source list) + `calendar_cache` table (event cache per source)
- **Canvas auto-calendar:** `_ensure_canvas_ical()` in `sync.py` calls `/users/self/profile` to get iCal URL, stores as `{id:"canvas", auto:True}`; runs at start of `sync_courses()`
- **Personal calendars:** User adds via Settings → Calendar tab; immediately fetched with 3-month window
- **Protocol:** `webcal://` and `webcals://` normalized to `https://` before httpx fetch
- **Sync strategy:** Default `query` (fetch on demand); options: query / login / daily / weekly / monthly
- **Failure handling:** `_fetch_and_cache()` returns `(events, error)` tuple — NEVER writes to DB on error (prevents empty cache masking failures); retry triggered when `events == []`
- **Cache invalidation:** STALE_HOURS per sync_frequency; "query" = always refresh; "login" = never auto-refresh

### RAG
- pgvector in Supabase (replaced ChromaDB)
- HNSW index on index_chunks.embedding and student_materials.embedding
- Chunk size: 500 chars, 100 char overlap
- Embeddings: all-MiniLM-L6-v2 (384-dim), normalized

### Tag-Aware Embeddings (student materials + admin KB)
- Before embedding, `_build_tag_prefix(metadata)` builds a header like:
  `"Subject: Mathematics | Grade: 8 | Type: exam paper\n\n"`
- This prefix is prepended to each chunk text before calling `embed()` — the tag context enters the vector
- Original chunk text (without prefix) is stored in `content` for display
- Effect: a query about "Grade 8 maths exams" ranks tagged materials higher via cosine similarity
- Shared between `rag/indexer.py` (`index_student_material`) and `admin/routes.py` (admin upload)

### Filename Tag Extraction (`_extract_tags_from_filename` in `materials/routes.py`)
Infers subject, grade levels, and doc_type automatically from filenames:
- **Subjects:** token matching against `_SUBJECT_MAP` (Math/Maths → Mathematics, Chem → Chemistry, etc.)
- **Grade levels:** Range patterns first (`Grade11_12`, `Gr9-10`), then single (`Grade8`, `Gr7`)
  — no trailing `\b` on grade patterns because `_` is `\w` and breaks word boundary detection
- **Doc type:** keyword matching (exam/test/mock → exam_paper, notes/summary → notes, etc.)
- Auto-tags stored in `student_materials.metadata` and returned to frontend for display as tag pills

### Multi-File Upload (student materials)
- Backend: `files: List[UploadFile]` — processes sequentially, returns `{results[], total, ok_count}`
- Each result: `{filename, ok, chunks, size_bytes, auto_tags}` or `{filename, ok, error}`
- Frontend: two hidden inputs — `multiple` for file picker, `webkitdirectory` for folder picker
- Batch result summary shown inline: "✓ 5 files indexed · 1 failed: …"
- `api.js#uploadMaterial` accepts `File | File[]` — always sends as `files` (plural) form field

### Admin Knowledge Base Upload
- Same form supports multiple files — tags (grade_levels, subjects, doc_type, expiry_date, applicable) apply to all selected files in the batch
- Useful for bulk-uploading a set of past papers for the same subject/grade
- Files processed sequentially with per-file error handling; partial success is possible

### Startup Performance
- Embedding model (`all-MiniLM-L6-v2`) pre-warmed in FastAPI lifespan hook via `ThreadPoolExecutor`
- Eliminates 2–3 s cold-start on first sign-in / first upload
- Runs in background thread — does not block the event loop during startup

### Canvas Sync
- Triggered manually via POST /api/canvas/courses/sync
- **Auto-index on first login:** `auth/routes.py` detects first login (no existing enrollments), runs `sync_courses()` + `index_course_content()` per course in background task via FastAPI `BackgroundTasks`
- Returns `first_login: True` in auth response so frontend can show loading indicator
- Background indexing via FastAPI BackgroundTasks (Celery/Redis deferred for future scale)

### Auth
- Fernet symmetric encryption for Canvas tokens at rest
- JWT secret + encryption key generated per deployment
- httpOnly cookie for refresh token (XSS safe)
- Access token in memory only (never localStorage)

### Email
- Resend for all transactional email (both architectures)
- AWS SES excluded — production access approval unreliable

### Frontend — Sidebar
- No "All Courses" option — courses are project workspaces, not a global feed
- First course auto-selected on load: `setSelectedCourse(prev => prev ?? list[0])`

### Frontend — ChatView
- **Thinking indicator:** When `loading && !streamingText` → shows `"Thinking… 2.4s"` (live counter)
- **Response timer:** After each AI response, shows `⏱ 14.2s` badge below the message
- Timer is **persistent on all assistant messages** — not just the latest one (removed `i === messages.length - 1` guard)
- Timer uses `setInterval` every 100ms; `sendTimeRef` captures send time; `timerRef` holds interval handle; `_ms` stored on each message object
- **`messagesRef`:** Always-current ref kept in sync with `messages` state via `useEffect`. `handleSend` reads from `messagesRef.current` instead of the `messages` closure — prevents stale closure bug where RightPanel "Ask AI" would wipe existing messages (and their timer badges) by spreading an empty initial array
- **WelcomeScreen quick actions:** 4 course-specific buttons + 2 global; use `handleSend(overrideText)` pattern
- `registerSend` prop: ChatView exposes `fireQuickAction` fn to App.jsx via callback; App stores in `chatSendRef`, passes to RightPanel as `onAskAI`

### Frontend — RightPanel
- 5 tabs: Assignments / Notices / Quizzes / Feedback / Mind Map
- Quizzes: shows `[EXAM]` badge (red pill), quiz_type, time_limit, points, due date
- Feedback: shows score, grade, submitted date, teacher comments
- Mind Map tab renders `<MindMapView>` full-height; "Ask AI about this" fires `onAskAI(prompt)` → closes panel + sends to chat
- All non-mindmap tab APIs called in parallel on course switch with `.catch()` fallback

### Frontend — MindMapView
- Pure React SVG — no d3 dependency
- `buildLayout(topics)`: hierarchical tree with column packing to prevent node overlap
- `buildEdgePath(src, tgt)`: cubic Bezier paths
- Viewport: drag (pointerdown/pointermove/pointerup), wheel zoom, fit-to-screen default
- Fetches from `/api/mindmap/{course_id}`, regenerate button, selected-node detail panel at bottom

### Frontend — SettingsModal
- **5 tabs:** General / Calendar / Materials / Admin KB (teachers only) / Account
- **Calendar tab:** compact 2×2 grid for personal calendars; fetch window + sync frequency use inline `<Tooltip>` (not hint text)
- **Materials tab:** multi-file + folder upload; auto-tag pills on uploaded file cards; batch result display
- **Admin KB tab:** grade level checkboxes (Gr 6–12), subjects field, doc_type selector, expiry date, applicable toggle; supports multi-file selection with tags applied to all
- **isAdmin check:** `["teacher","teacherenrollment","taenrollment","accountadmin","admin"].some(r => (user.canvas_role || user.role || "").toLowerCase().includes(r))`

---

## Known Pitfalls

- **Package naming:** Calendar package MUST be `cal/` not `calendar/` — Python stdlib `calendar` module is imported by `jwt` library (`from calendar import timegm`); naming our package `calendar` breaks JWT
- **`_format_rubric` in canvas/client.py:** Decorated `@staticmethod` so must use `CanvasClient.strip_html()` not `self.strip_html()`
- **MODELS_WITHOUT_TOOL_SUPPORT:** Tuple `("deepseek", "llama")` — substring match on lowercase model name. If switching to a new model that supports tools, verify it's not accidentally matched
- **Calendar inline fetch:** Only triggers when `len(events) == 0`. If a source legitimately has 0 events, it will be re-fetched every time (acceptable — better than serving stale empty cache from failed fetch)
- **Grade regex — no trailing `\b`:** `\bgrade[\s_\-]?(\d+)` must NOT use `\b` after the digit — underscore is `\w` so `grade8_exam` would not match. Use bare `grade[\s_\-]?(\d{1,2})` instead.
- **`canvas_role` vs `role` key:** Auth login returns `canvas_role` (fixed — was `role`). Frontend isAdmin falls back on both keys just in case. `/auth/me` returns `canvas_role` from DB.
- **`webkitdirectory` in JSX:** Non-standard attribute — needs `// eslint-disable-next-line react/no-unknown-property` above it. Set as `webkitdirectory=""` (empty string) not `webkitdirectory={true}`.
- **Admin multi-file upload:** Sends one request per file (sequential loop) — not batched. Keeps the single-file backend endpoint simple; partial success is possible.
- **SSE heartbeat — DO NOT use `asyncio.wait_for(__anext__())`:** Cancels the coroutine mid-execution on timeout, corrupting async generator state → blank responses. Use queue-based producer/consumer pattern instead (see `chat/routes.py`).
- **Groq TPM limits:** Free tier is 12,000 TPM. System prompt ~3,200 tokens + history. Keep history at 4 messages max. If hitting limits, switch to `llama-3.1-8b-instant` via Supabase global_config.
- **Gemini model names for new accounts:** `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-flash` all return 404 "not available to new users". Query `/api/debug/ai-ping` (returns model list) to find available models.
- **global_config table:** `ai_config` has a school_id FK constraint — cannot use NULL. Use `global_config` (key/value, no FK) for platform-wide settings.
- **Stop button:** Must call `abortRef.current?.()` on click when `loading=true`. Button disabled state must NOT include `|| loading` — that makes it unclickable when streaming.
- **Proactive RAG is async:** `rag_search()` is async — call with `await`, not via `asyncio.to_thread`. Its internals (embedder, Supabase) are sync but the function is declared async.

---

## Compliance

Dwight domiciled in NY + FL. FERPA does not apply (private school, no federal funding).

| Regulation | Applies | Key requirement |
|---|---|---|
| NY Education Law §2-d | ✅ | DPA with Dwight before launch |
| Florida SDPA FS §1002.222 | ✅ | Signed agreement before data collection |
| COPPA | ✅ | Parental consent for under-13 |
| GDPR | ✅ likely | International students — data minimisation, right to deletion |
| CCPA | ⚠️ check | If CA-resident students enrolled |

**Sub-processor DPA status:**
- Supabase ✅ | Railway ⚠️ limited | Resend ✅ | Anthropic ✅ | NVIDIA ⚠️ check for student data

---

## Roadmap

### Phase 1 — Foundation ✅ COMPLETE
- [x] Supabase schema (18 tables + calendar_cache + shared_materials, all migrations applied)
- [x] Canvas API Key auth (POST /auth/apikey, /auth/me, /auth/refresh, /auth/logout)
- [x] Provider abstraction (K2, OpenRouter, Anthropic, NVIDIA NIM)
- [x] Canvas sync (courses, modules, pages, assignments, announcements, quizzes)
- [x] pgvector RAG (index_chunks + student_materials, HNSW, match RPCs)
- [x] SSE streaming chat with tool loop
- [x] Chat history persisted to Supabase + restored on course switch
- [x] React frontend: login, sidebar, chat UI
- [x] Dockerfile + docker-compose
- [x] Auto-index Canvas on first student login (background task)
- [x] iCal calendar integration (personal + Canvas auto-calendar)
- [x] Calendar + quizzes/exams injected into AI system prompt
- [x] RightPanel: 5 tabs (Assignments / Notices / Quizzes / Feedback / Mind Map)
- [x] SettingsModal: 5 tabs (General / Calendar / Materials / Admin KB / Account)
- [x] Thinking indicator + persistent per-message response timer in ChatView
- [x] WelcomeScreen quick-action buttons in ChatView
- [x] Mind map — pure React SVG, zoom/pan, Ask AI integration
- [x] Student material upload — multi-file + folder, filename tag extraction, tag-aware embeddings
- [x] Admin knowledge base — shared_materials, grade/subject/doc_type tagging, bulk upload
- [x] Embedding model pre-warmed on startup (fast first sign-in)
- [x] No "All Courses" — first course auto-selected, courses are project workspaces
- [x] Calendar settings hints → inline tooltips (Fetch window, Sync frequency)
- [x] Personal calendars in compact 2×2 grid in Settings

### Phase 1 — Remaining
- [x] Complete Railway deployment — live at https://lumina-v2-production.up.railway.app
- [x] SSE heartbeat — queue-based, prevents Railway proxy timeout
- [x] Working stop button — AbortController wired through streamChat → ChatView
- [x] AI provider/model switchable via Supabase global_config (no redeploy)
- [x] Proactive RAG injection — course content chunks injected per query
- [x] Token budget control — 4-message history cap, 15-day calendar window
- [x] Active course injected explicitly — AI never asks "which subject?"
- [x] Socratic method fixed — factual questions get direct answers
- [x] Timer badge persistence fix — `messagesRef` prevents stale closure
- [x] Subject prompt modules — Economics (EconGraphs), Maths (Desmos), Physics (PhET)
- [x] InteractiveWidget component — collapsible iframes for ECONGRAPH/DESMOS/PHET markers
- [ ] Study plan generation
- [ ] Switch Railway to Groq (set AI_PROVIDER=groq, GROQ_API_KEY, GROQ_MODEL in Railway vars)

### Phase 2 — Subject Modules (foundation built, expand content)
**Economics (IB + AP):**
- [x] EconGraphs iframe integration (6 pilot graphs)
- [x] IBDP exam technique injected into Economics course prompts
- [ ] AP Micro / AP Macro split prompts (ap_micro.py, ap_macro.py)
- [ ] Custom SVG for missing diagrams (price ceiling/floor, Lorenz curve, standalone AD-AS, tariff)

**Later subjects (same pattern):**
- [ ] Chemistry subject prompt + Ketcher 2D molecules
- [ ] Biology subject prompt
- [ ] Chemistry/Biology 3D structures — Miew

### Phase 3 — Full student experience
- [ ] Adaptive quiz generator (port from v1)
- [ ] Mastery tracking — `mastery_scores` table exists, nothing uses it yet
- [ ] Step-by-step Socratic worked examples (problem-solving mode)
- [ ] Voice mode (port from v1)
- [ ] Parent consent flow + Resend email
- [ ] Sign DPA with Dwight

### Phase 4 — School admin & monitoring
- [ ] school_admin panel (AI model config, feature flags)
- [ ] Teacher read-only view (per-student AI usage + quiz topics)
- [ ] Audit trail + notifications

### Phase 5 — Auth upgrade
- [ ] Canvas OAuth2 (requires Developer Key from Dwight admin)
- [ ] LTI 1.3 (requires school IT)

### Phase 6 — AWS path (for schools requiring it)
- [ ] ECS Fargate + RDS Postgres + Bedrock + S3
