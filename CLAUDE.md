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
- Provider abstraction layer: AI (K2 / OpenRouter / Anthropic / NVIDIA NIM), Storage (Supabase), Email (Resend)
- Canvas sync: courses, modules, pages, assignments, announcements → Supabase
- pgvector RAG: sentence-transformers all-MiniLM-L6-v2 (384-dim), HNSW index
- SSE streaming chat with tool-call loop (K2/OpenRouter/Anthropic) or direct stream (DeepSeek)
- Chat history persisted to Supabase, restored on course switch
- System prompt injection: today's date + enrolled courses + upcoming assignments (avoids tool calls)
- React frontend: Sidebar (course list) + ChatView (SSE streaming) + LoginScreen

### Not yet ported from v1
- Adaptive quiz generator
- Mind map / knowledge graph
- Voice mode (STT/TTS)
- PDF / student material upload (schema exists, indexer built, no UI yet)

---

## Running Locally

### Backend
```bash
cd /Users/ny/Downloads/CursorProjects/Lumina-v2/backend
source .venv/bin/activate
uvicorn main:app --reload
```
Runs on http://localhost:8000

### Frontend
```bash
cd /Users/ny/Downloads/CursorProjects/Lumina-v2/frontend
npm run dev
```
Runs on http://localhost:5173 (proxies /auth and /api to :8000)

### .env location
`/Users/ny/Downloads/CursorProjects/Lumina-v2/backend/.env`
Note: .env changes require uvicorn restart (Ctrl+C then up arrow + Enter)

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
Switch via `AI_PROVIDER` env var — no code changes needed:
```
AI_PROVIDER=k2          → K2Provider      (K2-Think-v2 direct)
AI_PROVIDER=openrouter  → OpenRouterProvider
AI_PROVIDER=anthropic   → AnthropicProvider
AI_PROVIDER=nvidia      → NvidiaProvider  (NVIDIA NIM — Llama, DeepSeek etc.)
```

**Tool calling support:**
- K2, OpenRouter, Anthropic, Llama on NVIDIA: full OpenAI-style tool calling
- DeepSeek on NVIDIA: tool calling disabled (outputs raw DSML syntax) — uses pre-injected context instead

**Currently running:** NVIDIA NIM with `meta/llama-3.3-70b-instruct`

**Performance:** When a course is selected, assignments are pre-injected into the system prompt → 1 AI call per message (no tool loop overhead).

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

### Future auth (same DB schema, same Canvas API calls)
- **Canvas OAuth2** — requires Developer Key from Dwight Canvas admin
- **LTI 1.3** — requires school IT, unlocks deep linking + roster provisioning

---

## Key Files
| File | Purpose |
|---|---|
| `backend/main.py` | FastAPI app, routes wired, SPA catch-all |
| `backend/auth/routes.py` | Canvas API key login, JWT, refresh, logout |
| `backend/auth/middleware.py` | JWT dependency, role guards |
| `backend/auth/canvas.py` | Canvas token validation + retrieval abstraction |
| `backend/auth/encrypt.py` | Fernet encryption for Canvas tokens at rest |
| `backend/canvas/client.py` | Canvas REST client (pagination, HTML stripping) |
| `backend/canvas/sync.py` | sync_courses(), get_course_content() |
| `backend/canvas/routes.py` | /api/canvas/courses — list, sync, index |
| `backend/rag/embedder.py` | all-MiniLM-L6-v2 singleton |
| `backend/rag/indexer.py` | chunk + embed + store in pgvector |
| `backend/rag/search.py` | match_index_chunks + match_student_materials RPC |
| `backend/chat/engine.py` | Tool-call loop + direct stream, system prompt builder |
| `backend/chat/prompt.py` | Socratic tutor system prompt |
| `backend/chat/tools.py` | ToolExecutor — reads from Supabase cache |
| `backend/chat/routes.py` | POST /api/chat/stream (SSE), sessions CRUD |
| `backend/providers/ai/` | K2, OpenRouter, Anthropic, NVIDIA providers |
| `backend/config.py` | All env vars |
| `frontend/src/App.jsx` | Auth gate → MainLayout (Sidebar + ChatView) |
| `frontend/src/contexts/AuthContext.jsx` | In-memory JWT, cookie refresh, authFetch |
| `frontend/src/components/LoginScreen.jsx` | Canvas URL + API key form |
| `frontend/src/components/Sidebar.jsx` | Course list, sync button, user info |
| `frontend/src/components/ChatView.jsx` | SSE chat, tool status, history restore |
| `frontend/src/api.js` | streamChat(), fetchCourses(), fetchSessions() |
| `.mcp.json` | Supabase MCP config |

---

## DB Schema (all migrations applied to Supabase)

### Core Identity
- `schools` — id, name, canvas_url, created_at
- `users` — id, canvas_user_id, school_id, name, email, avatar_url, canvas_role,
  auth_method, canvas_access_token (encrypted), canvas_refresh_token,
  canvas_token_expires_at, last_active_at
- `sessions` — id, user_id, refresh_token (hashed), auth_method, expires_at,
  last_used_at, user_agent
- `enrollments` — user_id, course_id, canvas_role, synced_at
- `parent_links` — id, student_id, parent_email, consent_status,
  reporting_frequency, token, consented_at

### Canvas Sync
- `courses` — id, canvas_course_id, school_id, name, course_code, canvas_data JSONB, synced_at
- `index_chunks` — id, course_id, source_type, source_id, content,
  embedding vector(384), metadata JSONB
  - source_type: page / assignment / announcement / file
  - HNSW index on embedding (vector_cosine_ops)
- Supabase RPC functions: `match_index_chunks`, `match_student_materials`

### Student Activity
- `student_materials` — id, user_id, course_id, filename, content,
  embedding vector(384), metadata JSONB, uploaded_at
- `chat_sessions` — id, user_id, course_id, title, created_at, updated_at
- `chat_messages` — id, session_id, role (user/assistant), content, thinking JSONB, created_at
- `quiz_attempts` — id, user_id, course_id, questions JSONB, answers JSONB, score, difficulty, created_at
- `mastery_scores` — id, user_id, course_id, concept, score FLOAT, evidence JSONB, updated_at
- `mind_maps` — id, user_id, course_id, graph_data JSONB, updated_at

### Platform Config
- `ai_config` — id, school_id, provider, model_id, api_key_encrypted, settings JSONB
- `feature_flags` — school_id, feature, enabled
- `audit_logs` — id, user_id, action, target_type, target_id, metadata JSONB, created_at
- `api_usage` — id, school_id, user_id, model_id, input_tokens, output_tokens, created_at
- `notifications` — id, user_id, type, payload JSONB, sent_at, read_at

---

## Architecture Decisions

### Chat Performance
- Enrolled courses pre-injected into system prompt on every request (skips get_courses tool call)
- When a course is selected: upcoming assignments also injected → tool loop disabled → 1 AI call
- When no course selected: tool loop enabled → AI can call get_assignments, get_announcements, search_course_content
- All tool reads from Supabase cache (not live Canvas) — fast

### Tool Calling
- Tools read from Supabase (already synced) — not live Canvas API
- Falls back to live Canvas only if data not yet indexed
- DeepSeek models: tool loop disabled entirely (incompatible format on NVIDIA NIM)

### RAG
- pgvector in Supabase (replaced ChromaDB)
- HNSW index on index_chunks.embedding and student_materials.embedding
- Chunk size: 500 chars, 100 char overlap
- Embeddings: all-MiniLM-L6-v2 (384-dim), normalized

### Canvas Sync
- Triggered manually via POST /api/canvas/courses/sync
- Auto-index on first login: NOT YET BUILT (next task)
- Background indexing via FastAPI BackgroundTasks (Celery/Redis deferred)

### Auth
- Fernet symmetric encryption for Canvas tokens at rest
- JWT secret + encryption key generated per deployment
- httpOnly cookie for refresh token (XSS safe)
- Access token in memory only (never localStorage)

### Email
- Resend for all transactional email (both architectures)
- AWS SES excluded — production access approval unreliable

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
- [x] Supabase schema (18 tables, all migrations applied)
- [x] Canvas API Key auth (POST /auth/apikey, /auth/me, /auth/refresh, /auth/logout)
- [x] Provider abstraction (K2, OpenRouter, Anthropic, NVIDIA NIM)
- [x] Canvas sync (courses, modules, pages, assignments, announcements)
- [x] pgvector RAG (index_chunks + student_materials, HNSW, match RPCs)
- [x] SSE streaming chat with tool loop
- [x] Chat history persisted to Supabase + restored on course switch
- [x] React frontend: login, sidebar, chat UI
- [x] Dockerfile + docker-compose

### Phase 1 — Remaining
- [ ] Auto-index Canvas on first student login (currently manual sync required)
- [ ] Deploy to Railway

### Phase 2 — Full student experience
- [ ] Adaptive quiz generator (port from v1)
- [ ] Mind map (port from v1)
- [ ] PDF / student material upload + indexing UI
- [ ] Voice mode (port from v1)
- [ ] school_admin panel (AI model config, feature flags)
- [ ] Parent consent flow + Resend email
- [ ] Sign DPA with Dwight

### Phase 3 — Monitoring
- [ ] Teacher read-only view (per-student AI usage + quiz topics)
- [ ] Audit trail + notifications

### Phase 4 — Auth upgrade
- [ ] Canvas OAuth2 (requires Developer Key from Dwight admin)
- [ ] LTI 1.3 (requires school IT)

### Phase 5 — AWS path
- [ ] ECS Fargate + RDS Postgres + Bedrock + S3
