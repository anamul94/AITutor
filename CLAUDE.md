# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AITutor is a full-stack AI-powered learning platform with two core features:
1. **Course Generator** — users enter a topic and an LLM generates a full course syllabus with modules and lessons (JIT content generation per lesson).
2. **DSA Coach** — two coaching modes (`learn_topic`, `solve_problem`) implemented as LangGraph multi-step graphs that guide learners through DSA problems interactively.

## Stack

- **Backend**: FastAPI (async) + SQLAlchemy (async) + PostgreSQL + Alembic migrations
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **AI**: LangChain + LangGraph agents; supports AWS Bedrock (default) or any OpenAI-compatible provider

---

## Commands

### Backend

```bash
cd backend

# Activate virtualenv
source venv/bin/activate

# Run dev server
uvicorn app.main:app --reload --port 8000

# Run all tests
python -m pytest backend/tests/

# Run a single test file
python -m pytest backend/tests/test_dsa_coach_prompt_inputs.py

# Run a single test case
python -m pytest backend/tests/test_syllabus_prompt_inputs.py::SyllabusPromptInputTests::test_language_normalization

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Frontend

```bash
cd frontend

npm run dev       # dev server on :3000
npm run build     # production build
npm run lint      # ESLint
```

---

## Architecture

### Backend layout (`backend/app/`)

```
app/
  main.py              # FastAPI app; registers all routers
  api/
    auth.py            # JWT login/register/logout endpoints
    course.py          # Course + lesson CRUD and JIT content generation
    dsa_coach.py       # DSA coaching session and turn endpoints
    admin.py           # Admin-only endpoints
    deps.py            # get_db, get_current_user, get_current_admin FastAPI deps
  agents/
    course_agent.py    # Course syllabus generation (LangChain chain)
    lesson_agent.py    # Lesson content generation (LangChain chain)
    lesson_quiz_agent.py # Quiz generation (LangChain chain)
    dsa_coach_agent.py # Router: delegates to learn or solve agent
    dsa_learn_agent.py # learn_topic LangGraph graph (2-step: analyze → respond)
    dsa_solve_agent.py # solve_problem LangGraph graph (3-step: detect_mode → analyze → respond/reflect)
  core/
    config.py          # Pydantic Settings (DATABASE_URL, SECRET_KEY, plan limits, etc.)
    llm_providers.py   # get_llm_client(): returns (llm, context_dict); selects Bedrock or OpenAI-compat via LLM_PROVIDER env var
    llm_json.py        # parse_pydantic_from_response(), extract_json_object_text() — used for openai-compatible providers that can't do structured output natively
    llm_usage.py       # Token usage extraction and LLMUsagePayload building
    llm.py             # Re-exports from agents + providers for convenience
    security.py        # Password hashing (bcrypt)
  models/
    user.py            # User SQLAlchemy model + declarative Base
    course.py          # Course, Module, Lesson, UserProgress, LLMUsageEvent models
    dsa_coach.py       # DSACoachSession, DSACoachTurn, DSAWeakArea models
  schemas/             # Pydantic request/response schemas (mirror models/)
```

### LLM Provider selection

`LLM_PROVIDER` env var controls which backend is used:
- `bedrock` (default) — uses `ChatBedrockConverse` with `BEDROCK_MODEL_ID` and AWS credentials
- `openai-compatible` — uses `ChatOpenAI` pointed at `OPENAI_COMPAT_BASE_URL` (default: OpenRouter)

Because OpenAI-compatible providers don't support `.with_structured_output()` reliably, agents have a dual code path: structured output for Bedrock, manual JSON parsing via `parse_pydantic_from_response()` for openai-compatible.

### DSA Coaching agents (LangGraph)

Both `dsa_learn_agent.py` and `dsa_solve_agent.py` build a module-level `StateGraph` compiled into a singleton graph (`_DSA_LEARN_GRAPH` / `_DSA_SOLVE_GRAPH`). Each turn invokes the graph with `ainvoke()`.

- **learn_topic graph**: `START → analyze_turn → learn_response → END`
- **solve_problem graph**: `START → detect_mode → analyze_turn → [solve_response | reflection_response] → END`

The analysis step produces a Pydantic schema (e.g. `SolveTurnAnalysisSchema`) with routing signals. Weak area signals extracted per turn are upserted into `DSAWeakArea`.

### Frontend layout (`frontend/src/`)

```
app/                   # Next.js App Router pages
  dashboard/           # Main user dashboard (course list, generate modal)
  course/[id]/         # Course view with module/lesson list
  lesson/[id]/         # Lesson content + quiz
  dsa-learn/           # DSA learn_topic coaching UI
  dsa-solve/           # DSA solve_problem coaching UI
  login/ register/     # Auth pages
  admin/               # Admin dashboard
context/
  AuthContext.tsx      # JWT auth state; token stored in localStorage
lib/
  api.ts               # Axios instance with baseURL=NEXT_PUBLIC_API_URL, auto-injects Bearer token
components/
  dsa/DSAModeChat.tsx  # Shared chat UI for both DSA coaching modes
```

### Auth flow

- JWT issued on login, stored in `localStorage` as `token`
- `api.ts` interceptor injects it as `Authorization: Bearer <token>` on every request
- Backend `get_current_user` dep decodes JWT and loads the `User` row
- `is_admin` flag gates admin routes; `plan_type` (`free`/`premium`) gates daily usage limits

### Rate limiting (free plan)

Enforced in `course.py`: `FREE_DAILY_COURSE_LIMIT` (default 1) and `FREE_DAILY_LESSON_LIMIT` (default 2) from `Settings`. Rows are counted by UTC day window. Premium trial expiry is checked and auto-downgraded at request time.

### Key env vars

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | asyncpg connection string |
| `SECRET_KEY` | JWT signing key |
| `LLM_PROVIDER` | `bedrock` or `openai-compatible` |
| `BEDROCK_MODEL_ID` | Bedrock model ID (default: `global.anthropic.claude-sonnet-4-6`) |
| `OPENAI_COMPAT_BASE_URL` | Base URL for OpenAI-compat provider |
| `OPENAI_COMPAT_API_KEY` | API key (also checks `OPEN_ROUTER_API_KEY`, `OPENAI_API_KEY`) |
| `OPENAI_COMPAT_MODEL_ID` | Model name for openai-compat provider |
| `NEXT_PUBLIC_API_URL` | Frontend → backend base URL (default: `http://localhost:8000`) |
