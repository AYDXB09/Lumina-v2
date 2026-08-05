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
- pgvector RAG: Gemini embedding API `gemini-embedding-001` (768-dim), HNSW index — no local model
- SSE streaming chat with tool-call loop (K2/OpenRouter/Anthropic) or direct stream (DeepSeek/Llama/Groq)
- SSE heartbeat pings every 5s (queue-based, not wait_for) — prevents Railway proxy from dropping idle connections
- Chat history persisted to Supabase, restored on course switch; capped at 4 messages sent to AI (token budget)
- System prompt injection: today's date + enrolled courses + active course name + upcoming assignments + quizzes/exams + calendar events (15-day window)
- Proactive RAG injection: top 3 course content chunks semantically matched to user's query, injected before AI call
- AI provider + model configured via Railway env vars (`AI_PROVIDER`, `GEMINI_MODEL`, etc.) — change in Railway and restart
- React frontend: Sidebar (course list, no "All Courses") + ChatView (SSE streaming + thinking timer + persistent per-message timer + working stop button) + LoginScreen
- iCal calendar integration: personal calendars + Canvas auto-calendar, JSONB cache, injected into AI context
- RightPanel: 6 tabs — Assignments / Notices / Quizzes / Feedback / Mind Map / Plan
- Study plan generation: cross-course day-by-day plan from upcoming assignments/exams + calendar; deterministic scheduling (backend), AI fills in task text + plain-language reasoning per task (provider-agnostic, works with any of the 6 AI providers)
- SettingsModal: 5 tabs — General / Calendar / Materials / Admin KB (teachers only) / Account
- Auto-index Canvas content on first student login (background task)
- WelcomeScreen quick-action buttons in ChatView (course-specific + global)
- Mind map: pure React SVG, hierarchical tree layout, zoom/pan, "Ask AI" integration
- Student material upload: multi-file + folder select, filename tag extraction, tag-aware embeddings
- Admin knowledge base: shared_materials table, grade/subject/doc_type tagging, bulk upload
- No local embedding model — Gemini API call (~150ms) replaces sentence-transformers (was 11s on Railway CPU)
- Subject prompt modules: Economics, Mathematics, Physics, Chemistry, Biology, English, History, Languages, Psychology, CS, Geography, **Global Politics** — lazy-loaded per course
- Interactive widgets: `[ECONGRAPH: id]`, `[DESMOS: id]`, `[PHET: id]`, `[KINETIC: id]`, `[LIFESCIENCE: id]`, `[EXPLORABLES: id]` markers rendered as collapsible iframes
- New Chat button in ChatView header — deletes session + messages from Supabase (fire-and-forget), clears local state
- SettingsModal Account tab shows live AI model/provider from `/health` endpoint
- Comprehensive system prompt: grades, general knowledge, IB EE/IA/TOK, YouTube links, citations, error analysis, deadline awareness, response length calibration
- **IB IA full reference** injected into system prompt: all DP subjects with word counts, mark weights, criteria names, typical timeline, official IB links — AI never deflects IA questions to Canvas

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
**Single source of truth: Railway environment variables**
Set `AI_PROVIDER` + the matching model var, then restart the service.

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

**Currently running:** Gemini `gemini-2.5-flash-lite` (fast, free tier via Google AI Studio)
**Railway env vars needed:** `AI_PROVIDER=gemini`, `GEMINI_API_KEY=...`, `GEMINI_MODEL=gemini-2.5-flash-lite`
**Embedding:** `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`, `GEMINI_EMBEDDING_DIMS=768` (same API key)

**Groq free tier limits:** 12,000 TPM. System prompt ~3,200 tokens + 4-message history. Stays under limit for normal use.
If hitting limits: update `GROQ_MODEL=llama-3.1-8b-instant` in Railway and restart.

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
| `AI_PROVIDER` | `gemini` | |
| `GEMINI_API_KEY` | `AIza...` | Google AI Studio key |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | |
| `GEMINI_EMBEDDING_DIMS` | `768` | |
| `GROQ_API_KEY` | `gsk_...` | Keep for fallback |
| `NVIDIA_API_KEY` | ... | Keep for fallback |
| `REFRESH_EXPIRE_DAYS` | `90` | |
| `RESEND_API_KEY` | ... | |
| `ALLOWED_ORIGINS` | `https://lumina-v2-production.up.railway.app` | |

### Post-deploy checklist
- [x] Railway deployed and live
- [x] `/health` returns live provider/model from `get_active_config()` (not hardcoded env var)
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
| `backend/main.py` | FastAPI app, routes wired, SPA catch-all; no pre-warm (Gemini API replaces local model) |
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
| `backend/rag/embedder.py` | Gemini embedding API (`gemini-embedding-001`, 768-dim); async `embed()` and `embed_one()` |
| `backend/rag/indexer.py` | chunk + embed + store in pgvector; `_build_tag_prefix()` for tag-aware embeddings |
| `backend/rag/search.py` | match_index_chunks + match_student_materials RPC |
| `backend/chat/engine.py` | Tool-call loop + direct stream, system prompt builder (_build_system_prompt) |
| `backend/chat/prompt.py` | Socratic tutor system prompt + full IB IA reference table (all subjects, marks, deadlines, links) |
| `backend/chat/tools.py` | ToolExecutor — reads from Supabase cache |
| `backend/chat/routes.py` | POST /api/chat/stream (SSE), sessions CRUD; DELETE /api/chat/sessions/{id} |
| `backend/materials/routes.py` | Multi-file upload, filename tag extraction, student RAG indexing |
| `backend/mindmap/routes.py` | /api/mindmap/{course_id} — get, save, regenerate |
| `backend/studyplan/generator.py` | Cross-course study plan: `_gather_commitments()` (assignments/exams, 30-day lookahead), `_build_skeleton()` (deterministic day placement, not AI), `_fill_content()` (one `provider.complete()` call fills task text + reasoning) |
| `backend/studyplan/routes.py` | GET /api/studyplan (cached-or-generate), POST /api/studyplan/regenerate |
| `backend/admin/routes.py` | Admin KB upload (shared_materials), list, delete, patch tags |
| `backend/providers/ai/` | K2, OpenRouter, Anthropic, NVIDIA, Groq, Gemini providers |
| `backend/providers/ai/__init__.py` | Provider factory — reads `AI_PROVIDER` env var, builds singleton instance |
| `backend/chat/subject_prompts/` | 12 subject modules (Economics, Maths, Physics, Chemistry, Biology, English, History, Languages, Psychology, CS, Geography, Global Politics); dispatcher lazy-imports only matching subject |
| `backend/chat/subject_prompts/__init__.py` | Registry + dispatcher; add new subjects here |
| `backend/chat/subject_prompts/global_politics.py` | IB Global Politics — exam technique, key concepts, Engagement Activity IA (criteria A–C, 30 marks) |
| `frontend/src/components/InteractiveWidget.jsx` | Collapsible iframes for ECONGRAPH/DESMOS/PHET/KINETIC/LIFESCIENCE/EXPLORABLES markers |
| `frontend/src/components/ChatMessage.jsx` | Parses widget markers from AI output via parseSegments() |
| `backend/config.py` | All env vars |
| `frontend/src/App.jsx` | Auth gate → MainLayout; auto-selects first course; chatSendRef for RightPanel→Chat |
| `frontend/src/contexts/AuthContext.jsx` | In-memory JWT, cookie refresh, authFetch |
| `frontend/src/contexts/SettingsContext.jsx` | User settings with defaults incl. calendarFetchWindow, calendarSyncFrequency |
| `frontend/src/components/LoginScreen.jsx` | Canvas URL + API key form |
| `frontend/src/components/Sidebar.jsx` | Course list (no All Courses), sync button, user info |
| `frontend/src/components/ChatView.jsx` | SSE chat, tool status, history restore, thinking timer, persistent per-message timer, WelcomeScreen quick actions |
| `frontend/src/components/RightPanel.jsx` | 6-tab panel: Assignments / Notices / Quizzes / Feedback / Mind Map / Plan |
| `frontend/src/components/MindMapView.jsx` | Pure React SVG mind map; drag/zoom/fit; "Ask AI" integration |
| `frontend/src/components/StudyPlanView.jsx` | Cross-course study plan — day cards, plan-level summary, per-task reason, "Ask AI about this" |
| `frontend/src/components/SettingsModal.jsx` | 5-tab modal: General / Calendar / Materials / Admin KB / Account |
| `frontend/src/api.js` | streamChat(), fetchCourses(), uploadMaterial() (multi-file), fetchMindMap(), fetchStudyPlan(), regenerateStudyPlan(), fetchAdminMaterials(), deleteSession(), etc. |
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
  embedding vector(768), metadata JSONB
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
  embedding vector(768), metadata JSONB, uploaded_at
  - metadata includes: subjects[], grade_levels[], doc_type, original_filename, size_bytes
- `chat_sessions` — id, user_id, course_id, title, created_at, updated_at
- `chat_messages` — id, session_id, role (user/assistant), content, thinking JSONB, created_at
- `quiz_attempts` — id, user_id, course_id, questions JSONB, answers JSONB, score, difficulty, created_at
- `mastery_scores` — id, user_id, course_id, concept, score FLOAT, evidence JSONB, updated_at
- `mind_maps` — id, user_id, course_id, graph_data JSONB, updated_at
- `study_plans` — id, user_id (UNIQUE — one plan per user, cross-course not per-course), plan_data JSONB, generated_at, updated_at
  - plan_data: {summary, days: [{date, tasks: [{course, title, duration_min, reason}]}]}

### Admin Knowledge Base
- `shared_materials` — id, school_id, uploaded_by, filename, content, embedding vector(768),
  tags JSONB, metadata JSONB, uploaded_at
  - tags: {grade_levels[], subjects[], doc_type, expiry_date, applicable, chunk}
  - metadata: {title, description, source, chunk, total_chunks}
  - HNSW index on embedding; GIN index on tags
- Supabase RPC: `match_shared_materials` — grade_level `@>` containment, expiry date, applicable filters

### Platform Config
- `ai_config` — id, school_id, provider, model_id, api_key_encrypted, settings JSONB (per-school, has FK constraint)
- `global_config` — key TEXT PRIMARY KEY, value TEXT — reserved for future platform settings
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
5. Subject prompt module (11 subjects) — lazy-loaded only for matching course
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
- HNSW index on index_chunks.embedding, student_materials.embedding, shared_materials.embedding
- Chunk size: 500 chars, 100 char overlap
- Embeddings: Gemini `gemini-embedding-001` (768-dim), normalized, via async API call (~150ms)
- No local model — `sentence-transformers` and `numpy` removed from requirements
- `embed()` and `embed_one()` in `rag/embedder.py` are async — always `await` them

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
- No local embedding model — Railway starts faster, uses less memory
- Embedding is a ~150ms Gemini API call per request; no pre-warm needed

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
- **New Chat:** calls `DELETE /api/chat/sessions/{id}` (fire-and-forget) before clearing local state. Session + messages are deleted from Supabase immediately — navigate-away-and-back cannot restore the cleared conversation. Do NOT use sessionStorage or module-level flags for this — React Strict Mode double-invokes effects and `key`-based remounts reset all refs; only the DB delete is reliable.

### Frontend — RightPanel
- 6 tabs: Assignments / Notices / Quizzes / Feedback / Mind Map / Plan
- Quizzes: shows `[EXAM]` badge (red pill), quiz_type, time_limit, points, due date
- Feedback: shows score, grade, submitted date, teacher comments
- Mind Map tab renders `<MindMapView>` full-height; "Ask AI about this" fires `onAskAI(prompt)` → closes panel + sends to chat
- Plan tab renders `<StudyPlanView>` full-height; deliberately ignores the `course` prop (cross-course, not per-course)
- All non-mindmap/non-studyplan tab APIs called in parallel on course switch with `.catch()` fallback

### Frontend — MindMapView
- Pure React SVG — no d3 dependency
- `buildLayout(topics)`: hierarchical tree with column packing to prevent node overlap
- `buildEdgePath(src, tgt)`: cubic Bezier paths
- Viewport: drag (pointerdown/pointermove/pointerup), wheel zoom, fit-to-screen default
- Fetches from `/api/mindmap/{course_id}`, regenerate button, selected-node detail panel at bottom

### Study Plan Generation (backend/studyplan/)
- **Cross-course by design** — assignments/exams span multiple classes, so a plan only prioritizes correctly if it sees all of them at once, not just the selected course
- **Deterministic scheduling, AI-filled content** — day-by-day slot placement (`_build_skeleton()`) is plain Python, not an AI decision, so the schedule is always logically sound (every commitment gets at least one prep day, no day overloaded past `MAX_TASKS_PER_DAY`, no double-booking). The AI's job is narrower: fill in the actual task text + a plain-language `reason` per task, plus a plan-level `summary`
- **Provider-agnostic** — uses `provider.complete()` (non-streaming, implemented by all 6 providers) rather than tool-calling, so it works identically regardless of `AI_PROVIDER` — including models with tool-calling disabled (Llama/DeepSeek)
- **JSON-in-response-text, not structured tool output** — prompts for plain JSON, strips markdown fences, parses; retries once with a stricter "ONLY JSON" prompt on parse failure; falls back to skeleton-only generic task text if both attempts fail, so the feature degrades gracefully instead of erroring out
- **Weighting:** exam/IA > quiz > assignment (`TYPE_WEIGHT` in `generator.py`) — controls how many prep sessions a commitment gets, not just when
- **Storage:** one row per user in `study_plans` (upsert on `user_id`), regenerated manually via button — not on every login, since assignments/calendar don't change minute-to-minute and regeneration costs an AI call
- **Not yet done:** no live end-to-end test with real synced student data yet — structure is verified (backend imports resolve, frontend builds clean) but AI output quality on real assignments hasn't been checked

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
- **Groq TPM limits:** Free tier is 12,000 TPM. System prompt ~3,200 tokens + history. Keep history at 4 messages max. If hitting limits, update `GROQ_MODEL=llama-3.1-8b-instant` in Railway and restart.
- **Gemini model names for new accounts:** `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-flash` all return 404 "not available to new users". Query `/api/debug/ai-ping` (returns model list) to find available models.
- **global_config table:** `ai_config` has a school_id FK constraint — cannot use NULL. Use `global_config` (key/value, no FK) for platform-wide settings.
- **Stop button:** Must call `abortRef.current?.()` on click when `loading=true`. Button disabled state must NOT include `|| loading` — that makes it unclickable when streaming.
- **Proactive RAG is async:** `rag_search()` is async — call with `await`. `embed()` and `embed_one()` are also async (Gemini API calls) — never call them without `await`.
- **Gemini `extra_body={"thinking": ...}` is REMOVED, do not re-add it (fixed 2026-08-05):** This used to disable thinking tokens on `gemini-2.5-flash` variants, but Google's OpenAI-compatible endpoint now rejects the field outright — every `stream()`/`complete()` call failed with `400 Invalid JSON payload received. Unknown name "thinking": Cannot find field`. This was a **live production outage** (chat was fully broken, both locally and on Railway, since it's a runtime API call not a library version issue) discovered while testing the study plan feature, which was the first thing to ever exercise `provider.complete()` — `stream()` had the identical bug but nothing had surfaced it recently. Verified fix: removing the `extra_body` kwarg entirely from both methods in `providers/ai/gemini.py` restores working calls. If thinking-token suppression is needed again for `gemini-2.5-flash` (non-lite) in the future, check Google's current OpenAI-compat docs for the correct field shape first — don't blindly restore the old one.
- **Local Gemini API key:** `backend/.env` `GEMINI_API_KEY` must start with `AQ.` (not `yAQ.` — the `y` prefix makes it invalid). If all chat responses are blank and logs show Gemini 500 errors, check the key. Valid keys return a 200 for a simple curl test against `v1beta/models/gemini-2.5-flash-lite:generateContent`.
- **IB IA content in subject modules is large:** Each subject module now contains full IA criteria tables (~1,000 tokens each). These are lazy-loaded per course so they don't bloat unrelated requests. Do NOT move IA criteria back into the base `prompt.py` — it pushed `prompt_chars` to 28,000+ and caused Gemini 500s. Base prompt should stay under ~12,000 chars.

---

## Database Security — RLS Posture

**Current state (verified 2026-08-05):** all 22 tables in `public` have RLS **enabled with zero policies** — effectively deny-all for any request using the anon/publishable key. This is intentional, not an oversight: the backend (`backend/`) is the only thing that ever talks to Supabase, always via `SUPABASE_SERVICE_KEY` (service-role, bypasses RLS entirely). Confirmed by auditing the frontend:
- `@supabase/supabase-js` is not in `frontend/package.json` — no Supabase client library exists client-side
- `grep -rl "supabase" frontend/src/` returns nothing
- Every network call in `frontend/src/api.js` and `frontend/src/contexts/AuthContext.jsx` goes through `fetch`/`authFetch` against the FastAPI backend (`API_BASE`), never Supabase directly

**Open design decision (not yet made):** keep this backend-only/deny-all posture long-term, or eventually write real per-user RLS policies (e.g. `chat_sessions`, `student_materials`, `mind_maps` scoped to `auth.uid()`) so a future direct-from-frontend Supabase client integration would be possible without going through the backend first. No urgency — current architecture is safe as-is. Revisit only if there's ever a reason to let the frontend query Supabase directly (e.g. Supabase Realtime subscriptions, reducing backend round-trips).

Also cleaned up in this pass (see `supabase-lumina` MCP, 2026-08-05): dropped 2 duplicate embedding indexes, added 6 missing FK-covering indexes, pinned `search_path` on 6 `SECURITY DEFINER`/trigger functions to prevent search_path hijacking, revoked public `EXECUTE` on the `rls_auto_enable()` event-trigger function, and moved the `vector` extension out of `public` into a dedicated `extensions` schema.

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
- [x] No "All Courses" — first course auto-selected, courses are project workspaces
- [x] Calendar settings hints → inline tooltips (Fetch window, Sync frequency)
- [x] Personal calendars in compact 2×2 grid in Settings

### Phase 1 — Remaining
- [x] Complete Railway deployment — live at https://lumina-v2-production.up.railway.app
- [x] SSE heartbeat — queue-based, prevents Railway proxy timeout
- [x] Working stop button — AbortController wired through streamChat → ChatView
- [x] AI provider/model configured via Railway env vars (single source of truth)
- [x] Proactive RAG injection — course content chunks injected per query
- [x] Token budget control — 4-message history cap, 15-day calendar window
- [x] Active course injected explicitly — AI never asks "which subject?"
- [x] Socratic method fixed — factual questions get direct answers
- [x] Timer badge persistence fix — `messagesRef` prevents stale closure
- [x] Subject prompt modules — Economics (EconGraphs), Maths (Desmos), Physics (PhET)
- [x] InteractiveWidget component — collapsible iframes for ECONGRAPH/DESMOS/PHET markers
- [x] Switched to Gemini `gemini-2.5-flash-lite` (AI_PROVIDER=gemini in Railway)
- [x] Gemini embedding API (768-dim) — replaced sentence-transformers, 11s → ~150ms per query
- [x] New Chat button in ChatView with confirmation dialog
- [x] Comprehensive system prompt — grades, IB EE/IA/TOK, YouTube links, error analysis, 11 subject modules
- [x] New interactive widgets: KINETIC (KineticGraphs), LIFESCIENCE (EPAM Miew), EXPLORABLES
- [x] Subject modules: Chemistry, Biology, English, History, Languages, Psychology, CS, Geography
- [x] New Chat bug fix — deletes session from Supabase; navigate-away-and-back no longer restores cleared conversation
- [x] IB IA full reference in system prompt — all subjects, word counts, mark weights, criteria, timeline, official links
- [x] IB IA criteria in every subject module — Math (A–E, 20 marks), Physics/Chem/Bio (A–E, 24 marks), Economics (commentary criteria + HL research project), English (IO criteria), History, Psychology, Languages (IO), Global Politics (Engagement Activity)
- [x] Global Politics subject module — new (was missing); exam technique + key concepts + IA
- [x] Study plan generation — cross-course, deterministic scheduling + AI-filled task content/reasoning, provider-agnostic (`backend/studyplan/`); not yet tested end-to-end against real synced student data

### Phase 2 — Subject Modules (foundation built, expand content)
**Economics (IB + AP):**
- [x] EconGraphs iframe integration (6 pilot graphs)
- [x] KineticGraphs integration (game theory + advanced diagrams)
- [x] IBDP exam technique injected into Economics course prompts
- [ ] AP Micro / AP Macro split prompts (ap_micro.py, ap_macro.py)
- [ ] Custom SVG for missing diagrams (price ceiling/floor, Lorenz curve, standalone AD-AS, tariff)

**Sciences:**
- [x] Chemistry subject prompt + PhET sims + EPAM LifeScience molecular viewer
- [x] Biology subject prompt + PhET sims + EPAM LifeScience
- [ ] Ketcher 2D molecule drawing for organic chemistry

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
