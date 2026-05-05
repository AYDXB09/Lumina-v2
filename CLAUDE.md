# Lumina — Claude Code Context

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
- **Local path:** /Users/ny/Downloads/CursorProjects/School-AI/school-ai/
- **GitHub:** AYDXB09/school-ai (SSH: git@github-aydxb09:AYDXB09/school-ai.git)
- **SSH key:** ~/.ssh/id_ed25519_aydxb09 | Host alias: github-aydxb09
- **Stack:** React 19 + Vite (frontend) + FastAPI Python (backend)
- **Current state:** Feature-complete hackathon build, 67+ commits, clean working tree

### Existing features (already built)
- Socratic AI chat (K2-Think-v2 model, SSE streaming)
- Canvas API integration (courses, assignments, announcements)
- ChromaDB RAG (semantic search over course content)
- Adaptive quiz generator (dynamic difficulty, LaTeX support)
- Mind map / knowledge graph (SVG force-directed, concept extraction)
- Voice mode (STT/TTS loop)
- PDF / transcript upload
- All state in localStorage (to be migrated to Supabase)

---

## Tech Stack — Dual Architecture

Two deployment targets sharing identical application code.
Only infrastructure layer differs — environment variables switch providers.

### Non-AWS (default — build this first)
| Layer | Tech | Notes |
|---|---|---|
| Frontend + Backend | FastAPI serves React build | Single Railway service, one URL |
| Database | Supabase (Postgres + pgvector) | US East region |
| AI | Anthropic API direct | No-training guarantee, no OpenRouter middleman |
| File storage | Supabase Storage | Student uploads (PDFs, textbooks) |
| Email | Resend | Instant setup, DPA available, no SES sandbox issues |
| Queue | Railway Redis + Celery | RAG background indexing |
| Secrets | Environment variables | Railway env var management |

### AWS (later — for schools that require it)
| Layer | Tech | Notes |
|---|---|---|
| Frontend + Backend | ECS Fargate (same Docker image) | |
| Database | RDS Postgres + pgvector | |
| AI | Bedrock (Claude) | AWS DPA covers no-training guarantee |
| File storage | S3 | |
| Email | Resend | SES avoided — production access is unreliable |
| Queue | ElastiCache Redis + Celery | |
| Secrets | AWS Secrets Manager | |

**Note on AWS:** AWS architecture is for schools with existing AWS relationships or
strict data residency requirements. Not the default path. Implement after Non-AWS
is fully working. AWS SES is explicitly excluded — use Resend in both architectures.

### Provider Abstraction Layer (backend)
All provider-dependent code lives behind interfaces. Env vars switch implementations:
```
AI_PROVIDER=anthropic          → AnthropicProvider
AI_PROVIDER=bedrock            → BedrockProvider

STORAGE_PROVIDER=supabase      → SupabaseStorageProvider
STORAGE_PROVIDER=s3            → S3StorageProvider

EMAIL_PROVIDER=resend          → ResendEmailProvider
```
Database code (SQLAlchemy) is identical for both — both use Postgres + pgvector.

---

## Supabase Project (Lumina)
- **Project ID:** tnholnjrhnnqytmpqacb
- **URL:** https://tnholnjrhnnqytmpqacb.supabase.co
- **Region:** US East (North Virginia)
- **MCP:** supabase-lumina (configured in .mcp.json at project root)
- Separate account from carpooling project

---

## Authentication

### Current approach: Canvas API Key (POC)
Student generates their own Canvas API key (Account → Settings → New Access Token)
and pastes it into Lumina. No admin approval needed. Lumina validates it by calling
/api/v1/users/self, then issues its own session JWT.

**Why this works:**
- Student authenticates themselves — data accessed on their behalf
- Canvas API key does not expire unless student revokes it
- Same Canvas permissions as the student — cannot access other students' data
- No school admin dependency to get started

**Session management:**
- Lumina JWT (7 days) stored in browser cookie
- Refresh token (90 days) stored in `sessions` table, httpOnly cookie
- Silent refresh on expiry — student never re-enters their Canvas key
- Only re-prompts for Canvas API key after 90 days inactive

### Future auth methods (same DB schema, same Canvas API calls)
- **Canvas OAuth2:** Student clicks "Login with Canvas" — requires Developer Key
  approval from Dwight's Canvas admin
- **LTI 1.3:** Canvas launches Lumina directly — requires school IT involvement,
  unlocks deep linking + roster provisioning

`auth_method` column in `users` table tracks which method was used.
`CanvasAuthProvider.get_canvas_token(user_id)` abstracts all three methods —
Canvas API calls are identical regardless of auth method.

---

## Roles (simplified — student-centered)
```
student       → core user (Canvas API key or OAuth)
teacher       → light read-only monitoring only
parent        → consent + periodic report
school_admin  → platform config (AI model, API keys, feature flags)
```
Canvas roles (student/teacher) derived from Canvas API — not stored separately.
No dept_head / coordinator / dean / principal — dropped intentionally.
Reason: Lumina is student-centered. Not a school admin tool.

---

## Confirmed Features (from lumina_feature_requirements.csv)

### Student (core)
- AI Chat Tutor (Socratic)
- Canvas Course Sync (courses + metadata)
- Canvas Modules & Pages Sync (primary RAG source — lecture notes, readings)
- Canvas Files Sync (PDFs, slides auto-indexed)
- Canvas Assignments Sync (names, due dates, descriptions)
- Canvas Announcements Sync (teacher announcements in AI context)
- Non-Canvas Material Upload (private — student's own textbooks, notes)
- Adaptive Quiz
- Mind Map
- Mastery Tracking (from quiz performance only — NOT Canvas grades)
- Voice Mode
- Chat History (persistent, per course)
- Progress Dashboard (own scores + mastery)
- Mobile / PWA

### Teacher (read-only monitoring)
- Per-Student Drill-Down (AI usage + quiz results — supplementary only)
- Quiz Review (what topics students are asking about)

### Parent
- Consent Flow (email via Resend, AI risk disclosure, opt-in)
- Opt-In Reporting (weekly / monthly / none)
- Progress Report View (read-only)
- Withdraw Consent

### School Admin
- User Management
- Role Assignment
- AI Model Config (provider, model ID, API key — one model at a time)
- Canvas API Config (school Canvas URL + credentials)
- Feature Toggles
- Usage Monitoring (token consumption, cost estimates)
- Audit Logs
- Data Retention Policy

### Platform
- Canvas API Key login now → OAuth2 → LTI 1.3 (progressive)
- Transactional email via Resend
- Dark Mode (already exists)
- Audit Trail (all AI interactions logged)

### Explicitly excluded (not replicating Canvas)
- Canvas Grades View (students use Canvas for this)
- Assignment Reminders (Canvas already does this)
- Struggling Student Alerts (Canvas has predictive analytics)
- Canvas Enrollments / Submissions / Grades Sync
- Offline Access
- Multi-School / Tenant (single school for POC)

---

## DB Schema (built in Supabase — all migrations applied)

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
- `courses` — id, canvas_course_id, school_id, name, course_code,
  canvas_data JSONB, synced_at
- `index_chunks` — id, course_id, source_type, source_id, content,
  embedding vector(384), metadata JSONB
  - source_type: module / page / file / assignment / announcement
  - HNSW index on embedding (vector_cosine_ops)

### Student Activity
- `student_materials` — id, user_id, course_id, filename, content,
  embedding vector(384), metadata JSONB, uploaded_at
- `chat_sessions` — id, user_id, course_id, title, created_at, updated_at
- `chat_messages` — id, session_id, role (user/assistant), content,
  thinking JSONB, created_at
- `quiz_attempts` — id, user_id, course_id, questions JSONB, answers JSONB,
  score, difficulty, created_at
- `mastery_scores` — id, user_id, course_id, concept, score FLOAT,
  evidence JSONB, updated_at
- `mind_maps` — id, user_id, course_id, graph_data JSONB, updated_at

### Platform Config
- `ai_config` — id, school_id, provider, model_id, api_key_encrypted,
  settings JSONB
- `feature_flags` — school_id, feature, enabled
- `audit_logs` — id, user_id, action, target_type, target_id, metadata JSONB,
  created_at
- `api_usage` — id, school_id, user_id, model_id, input_tokens, output_tokens,
  created_at
- `notifications` — id, user_id, type, payload JSONB, sent_at, read_at

---

## Architecture Decisions

### Auth
- Canvas API Key for POC — student self-service, no admin dependency
- Canvas OAuth2 next — requires Developer Key from school Canvas admin
- LTI 1.3 later — unlocks deep linking, roster provisioning, single-click launch
- All three methods share identical Canvas API calls
- CanvasAuthProvider abstraction handles token retrieval + refresh

### AI Model
- One model at a time, swappable via school_admin panel (no code change)
- **Anthropic API direct** (not OpenRouter) — cleaner compliance chain,
  explicit no-training guarantee on API data
- Bedrock on AWS path (same guarantee, within AWS compliance boundary)
- K2-Think-v2 was the hackathon model — Anthropic Claude for production

### RAG / Indexing
- pgvector in Supabase (replaced ChromaDB — hosted, persistent, no extra service)
- HNSW index — works on empty table, no training data needed
- Auto-index triggered on student's first login
- Background job (Celery + Redis) — indexing doesn't block the UI
- sentence-transformers all-MiniLM-L6-v2 for embeddings (384 dimensions)
- index_chunks (Canvas content) + student_materials both searched at query time

### Canvas API
- REST API with student's own API token (scoped to their permissions)
- Fetch: courses, modules, module items, pages, files, assignments, announcements
- Pagination handled (per_page=100)
- Student can only access what they themselves can see in Canvas
- DAP (Data Access Platform): skip — bulk analytics tool, not real-time
- xAPI: skip — Canvas implementation limited to page views only

### Data Minimisation
- Only sync course materials students already have access to
- No grades, no submissions, no other students' data
- Canvas content indexed then not stored raw long-term
- Audit logs store metadata only — not full message content
- Retention policy configurable per school in ai_config

### Email
- Resend for all transactional email (both Non-AWS and AWS paths)
- AWS SES explicitly excluded — production access approval is unreliable
- Use cases: parent consent requests, weekly/monthly reports, breach notifications

---

## Compliance

Dwight Global Online School is domiciled in **New York and Florida**.
FERPA does not directly apply (private school, no federal funding) but the
following regulations do:

| Regulation | Applies | Key Requirements for Lumina |
|---|---|---|
| **NY Education Law §2-d** | ✅ Yes — NY domicile | Sign Parents' Bill of Rights DPA with Dwight before launch. No commercial use of student data. Bind all sub-processors. Breach notification required. Delete all data on contract end. |
| **Florida SDPA FS §1002.222** | ✅ Yes — FL domicile | Signed agreement before data collection. Educational purpose only. No behavioural profiling. No sale/transfer of student data. Breach notification. |
| **COPPA** | ✅ Yes — federal | Parental consent required for any student under 13. Applies regardless of school type. |
| **GDPR** | ✅ Likely — international students | Dwight is an international school. EU/UK students trigger GDPR. Data minimisation, right to deletion, lawful basis for processing. |
| **FERPA** | ⚠️ Not required | Private school with no federal funding. But worth building to FERPA standard — signals seriousness to future public school customers. |
| **CCPA** | ⚠️ Check | If California-resident students are enrolled. |

**Before pilot launch (legal blockers):**
1. Sign NY §2-d compliant DPA with Dwight
2. Sign FL SDPA compliant agreement with Dwight
3. Verify all sub-processors have signed DPAs:
   - Supabase ✅ DPA available
   - Railway ⚠️ Limited DPA — acceptable for POC
   - Resend ✅ DPA available
   - Anthropic ✅ No-training guarantee on API data

**Data the school needs to understand flows through:**
Canvas → Lumina (Railway) → Supabase → Anthropic API
Each hop must be covered by the DPA chain.

---

## Roadmap

### Phase 1 — Foundation (current)
- [x] Supabase schema (all migrations applied)
- [ ] Canvas API Key auth (POST /auth/apikey + frontend login screen)
- [ ] Provider abstraction layer (AI, storage, email)
- [ ] Auto-index Canvas courses on first student login
- [ ] Migrate chat history + quiz results from localStorage to Supabase
- [ ] Deploy to Railway (single service — FastAPI serves React build)

### Phase 2 — Multi-user
- [ ] Every Dwight student can log in
- [ ] school_admin panel (AI model config, Canvas URL, feature flags)
- [ ] Parent consent flow + Resend email
- [ ] Sign DPA with Dwight

### Phase 3 — Monitoring
- [ ] Teacher read-only view (per-student AI usage + quiz topics)
- [ ] Audit trail + notifications

### Phase 4 — Auth upgrade
- [ ] Canvas OAuth2 (requires Developer Key from Dwight admin)
- [ ] LTI 1.3 (requires school IT involvement)

### Phase 5 — AWS path (for schools requiring it)
- [ ] ECS Fargate + RDS Postgres + Bedrock + S3
- [ ] Single AWS account deployment option
- [ ] School runs inside their own AWS account (full data sovereignty)

---

## Key Files
| File | Purpose |
|---|---|
| src/App.jsx | Main chat interface (~1765 lines, needs splitting) |
| src/api.js | K2 API client + SSE streaming |
| src/canvasApi.js | Canvas REST API integration (996 lines) |
| src/courseWorkspace.js | Concept extraction + knowledge graph |
| src/systemPrompt.js | Socratic teaching system prompt |
| backend/main.py | FastAPI app, SSE endpoints |
| backend/tool_controller.py | LLM function-calling orchestrator |
| backend/canvas_tools.py | Canvas API tools for LLM |
| backend/rag.py | ChromaDB RAG (to be replaced with pgvector) |
| lumina_feature_requirements.csv | Feature decisions (Y/N/?) with comments |
| .mcp.json | Supabase MCP config (supabase-lumina) |

---

## Next Immediate Step
Build Phase 1 backend auth + provider abstraction:
1. `POST /auth/apikey` — validate Canvas key, upsert user, return JWT + refresh token
2. `GET /auth/me` — return current user
3. `POST /auth/refresh` — silent JWT renewal
4. `POST /auth/logout` — invalidate session
5. Provider abstraction: AnthropicProvider, SupabaseStorageProvider, ResendEmailProvider
6. Frontend login screen — Canvas URL + API key input, replace localStorage auth
