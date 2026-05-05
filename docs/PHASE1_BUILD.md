# Phase 1 Build Log

## What Was Done (Session — 2026-05-04)

---

## 1. Supabase Schema — COMPLETE ✅

All 10 migrations applied to project `tnholnjrhnnqytmpqacb` (US East).

| Migration | Tables Created |
|---|---|
| `enable_extensions` | pgvector, uuid-ossp extensions |
| `schools_users` | `schools`, `users` |
| `courses_enrollments_index_chunks` | `courses`, `enrollments`, `index_chunks` |
| `chat_sessions_messages` | `chat_sessions`, `chat_messages` |
| `quiz_mastery_mindmap` | `quiz_attempts`, `mastery_scores`, `mind_maps` |
| `student_materials` | `student_materials` |
| `parent_links` | `parent_links` |
| `platform_config` | `ai_config`, `feature_flags`, `audit_logs`, `api_usage`, `notifications` |
| `users_auth_method` | Added `auth_method` column to `users` |
| `sessions` | `sessions` (refresh token tracking) |
| `platform_config_table` | `platform_config` (Supabase-backed runtime config) |

**18 tables total. All RLS-enabled.**

### Config Architecture — Two-Tier Design
```
Tier 1 — Boot secrets (env vars only, never in DB)
  SUPABASE_URL, SUPABASE_SERVICE_KEY   ← needed to connect to Supabase
  JWT_SECRET                           ← JWT signing key
  ENCRYPTION_KEY                       ← Fernet key for token encryption

Tier 2 — Runtime config (Supabase tables, editable without redeploy)
  platform_config  ← AI provider, Canvas URL, email, storage, app behaviour
  ai_config        ← structured AI model config + settings JSONB
  feature_flags    ← per-feature on/off per school
```

When a school is first created, `db/seed_config.py` inserts default rows.
School admin can change any value through the admin panel (Phase 2).
Config changes are automatically audit-logged (trigger on platform_config).
Backend caches config per school — admin changes take effect on next request.

### Key schema decisions informed by Canvas LMS:
- `canvas_user_id` stored as TEXT (Canvas IDs are integers but safer as text)
- `canvas_refresh_token` added to users (OAuth tokens expire, API keys don't)
- `auth_method` column: `api_key` | `oauth` | `lti` (future-proofed)
- `index_chunks.source_type`: module / page / file / assignment / announcement
  (maps directly to Canvas REST API endpoints)
- HNSW index on embeddings (not IVFFlat — works on empty tables)
- `sessions` table for server-side refresh token tracking + revocation

---

## 2. Backend — IN PROGRESS 🔄

### New directory structure created:
```
backend/
├── providers/
│   ├── ai/           # AI provider abstraction
│   ├── storage/      # Storage provider abstraction
│   └── email/        # Email provider abstraction
├── auth/             # Auth utilities
└── db/               # Database client
```

### Files built so far:

#### `backend/config.py` — UPDATED ✅
Added all new config values. Existing K2 + Canvas config preserved.

New env vars added:
```env
# AI
AI_PROVIDER=k2                        # k2 | openrouter | anthropic | bedrock
OPENROUTER_API_KEY=                   # OpenRouter API key
OPENROUTER_MODEL=MBZUAI-IFM/K2-Think-v2
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5

# Storage
STORAGE_PROVIDER=supabase             # supabase | s3

# Email
EMAIL_PROVIDER=resend
RESEND_API_KEY=
EMAIL_FROM=Lumina <noreply@lumina.school>

# Supabase
SUPABASE_URL=https://tnholnjrhnnqytmpqacb.supabase.co
SUPABASE_SERVICE_KEY=                 # service role key (not anon key)

# Auth
JWT_SECRET=                           # generate with: openssl rand -hex 32
JWT_EXPIRE_MINUTES=10080              # 7 days
REFRESH_EXPIRE_DAYS=90
ENCRYPTION_KEY=                       # generate with Fernet.generate_key()
```

#### `backend/db/client.py` — NEW ✅
Supabase singleton client using service role key.
All server-side DB operations go through this (bypasses RLS).

#### `backend/auth/encrypt.py` — NEW ✅
Fernet symmetric encryption for Canvas tokens stored in Supabase.
- `encrypt_token(plaintext)` → ciphertext stored in DB
- `decrypt_token(ciphertext)` → plaintext used for API calls
- Dev fallback: derives key from JWT_SECRET if ENCRYPTION_KEY not set

#### `backend/auth/jwt_utils.py` — NEW ✅
Lumina JWT management:
- `create_access_token(user_id, role, school_id)` → 7-day JWT
- `verify_access_token(token)` → decoded payload or raises
- `generate_refresh_token()` → (raw_token, hashed_token) pair
  - Raw sent to client (cookie)
  - Hash stored in `sessions` table

#### `backend/auth/canvas.py` — NEW ✅
Canvas credential validation + token retrieval abstraction:
- `validate_canvas_api_key(canvas_url, api_key)` → calls Canvas `/api/v1/users/self`
- `get_canvas_token(user_id)` → returns valid Canvas token for any auth method
  - `api_key`: decrypt from DB
  - `oauth`: TODO Phase 4 (refresh if near expiry)
  - `lti`: TODO Phase 5

---

## 3. Still To Build

### Backend
- [ ] `backend/auth/routes.py` — Auth endpoints:
  - `POST /auth/apikey` — validate Canvas key, upsert user, return JWT + refresh token
  - `GET /auth/me` — return current user from JWT
  - `POST /auth/refresh` — silent JWT renewal using refresh token
  - `POST /auth/logout` — delete session from DB
- [ ] `backend/auth/middleware.py` — JWT verification dependency for protected routes
- [ ] `backend/providers/ai/base.py` — AIProvider interface
- [ ] `backend/providers/ai/k2.py` — K2-Think-v2 direct
- [ ] `backend/providers/ai/openrouter.py` — OpenRouter
- [ ] `backend/providers/ai/anthropic.py` — Anthropic direct
- [ ] `backend/providers/storage/base.py` + `supabase.py`
- [ ] `backend/providers/email/base.py` + `resend.py`
- [ ] `backend/main.py` — wire up auth routes, serve React static build
- [ ] `backend/requirements.txt` — add: supabase, PyJWT, cryptography, resend, httpx

### Frontend
- [ ] `src/contexts/AuthContext.jsx` — auth state (user, token, login/logout)
- [ ] `src/components/LoginScreen.jsx` — Canvas URL + API key form with instructions
- [ ] Update `src/App.jsx` — auth gate (show LoginScreen if not authenticated)
- [ ] Update `src/api.js` — pass JWT in Authorization header to backend
- [ ] Update `src/canvasApi.js` — get Canvas token from AuthContext (not localStorage)

### Deployment
- [ ] `Dockerfile` — builds React, copies into FastAPI static dir
- [ ] `docker-compose.yml` — local dev with hot reload
- [ ] `.env.example` — all required env vars documented

---

## 4. How Auth Flow Works (Once Complete)

```
Student opens Lumina
    ↓
Sees LoginScreen:
  - Canvas URL: https://dwight.instructure.com
  - API Key: [paste token]          ← from Canvas Account → Settings → New Access Token
    ↓
POST /auth/apikey { canvas_url, api_key }
    ↓
Backend calls Canvas /api/v1/users/self
    ↓ (valid)
Upsert user in Supabase users table (encrypted token stored)
Issue Lumina JWT (7 days) + refresh token (90 days)
    ↓
JWT stored in httpOnly cookie
Frontend stores user info in React context
    ↓
Student sees their dashboard
Canvas API calls use token from AuthContext
    ↓
7 days later: JWT expires
Silent POST /auth/refresh → new JWT issued
Student sees nothing
    ↓
90 days inactive: refresh token expires
LoginScreen shown — student pastes same Canvas key (it hasn't expired)
```

---

## 5. AI Providers Supported

| Provider | Model | When to use |
|---|---|---|
| K2-Think-v2 direct | MBZUAI-IFM/K2-Think-v2 | Default — best reasoning for tutoring |
| OpenRouter | Any model incl. K2 | When K2 direct is unavailable, or to access other models |
| Anthropic direct | claude-sonnet-4-5 | When no-training guarantee is required (compliance) |
| Bedrock | Claude via AWS | Phase 5 — AWS deployment path |

Set `AI_PROVIDER` env var to switch. No code changes needed.

---

## 6. Environment Variables Needed (Non-AWS path)

Create `backend/.env` with:
```env
# Canvas (dev/test — student provides at runtime in prod)
CANVAS_API_URL=https://dwight.instructure.com
CANVAS_API_TOKEN=

# AI — pick one
AI_PROVIDER=k2
K2_API_KEY=
OPENROUTER_API_KEY=

# Supabase
SUPABASE_URL=https://tnholnjrhnnqytmpqacb.supabase.co
SUPABASE_SERVICE_KEY=         # Dashboard → Project Settings → API → service_role

# Auth (generate these)
JWT_SECRET=                   # openssl rand -hex 32
ENCRYPTION_KEY=               # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Email
RESEND_API_KEY=

# Server
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=http://localhost:5173
```
