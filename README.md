# AITutor

AI-powered course and lesson generation platform with user plans, progress tracking, and an admin analytics/control panel.

For a short public/open-source showcase version, see [README.public.md](/media/aa/4afee987-9fd2-4bf2-a0d9-275bb3cde63f/aa/WORK/Personal-Project/AITutor/README.public.md).

## What It Does

### Learner features
- Generate a full course syllabus from a single topic.
- Personalize generation with:
  - `learning_goal` (optional, 10-300 chars)
  - `preferred_level` (`beginner | intermediate | advanced | auto`)
- Structured syllabus with ordered modules and lessons.
- Just-in-time lesson generation when a lesson is opened.
- Rich lesson content in markdown with a strict educational structure.
- Per-lesson quiz generation (3 MCQs with explanations).
- Mark lesson complete and track course progress percentage.
- Delete user-owned courses.

### Plan and usage features
- New user starts on a 7-day premium trial.
- Automatic fallback to free plan after trial expiry.
- Free plan limits:
  - 1 course generation/day
  - 2 lesson generations/day
- Token usage tracking for syllabus + lesson generation.
- Concurrency-safe lesson generation to prevent duplicate token logging.

### Admin features
- Separate admin registration endpoint with admin key.
- Global dashboard stats:
  - total users
  - users registered today
  - active users today
  - courses/lessons generated today
  - token usage (today + total)
- Date-wise registration insights.
- List of today registered users.
- Per-user token usage stats.
- User management:
  - set plan to free/premium
  - activate/deactivate users

## Tech Stack

- Backend: FastAPI, SQLAlchemy (async), Alembic, PostgreSQL
- AI: LangChain + AWS Bedrock (`langchain-aws`)
- Frontend: Next.js (App Router), React, TypeScript, Tailwind, Framer Motion

## Project Structure

```text
AITutor/
  backend/
    app/
      api/        # auth, course, admin routes
      core/       # config, security, llm
      models/     # SQLAlchemy models
      schemas/    # Pydantic schemas
    migrations/   # Alembic migrations
  frontend/
    src/app/      # Next.js routes
    src/context/  # auth context
    src/lib/      # axios api client
```

## Quick Start

### 1) Prerequisites
- Python 3.12+
- Node.js 20+
- Docker + Docker Compose

### 2) Start database

```bash
docker compose up -d
```

This starts PostgreSQL on `localhost:5430`.

### 3) Backend setup

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
./venv/bin/alembic upgrade head
```

Edit `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5430/aitutordb
SECRET_KEY=replace_with_strong_secret
ADMIN_REGISTRATION_KEY=replace_with_strong_admin_key
ACCESS_TOKEN_EXPIRE_MINUTES=10080

PREMIUM_TRIAL_DAYS=7
FREE_DAILY_COURSE_LIMIT=1
FREE_DAILY_LESSON_LIMIT=2

AWS_ACCESS_KEY_ID=replace_me
AWS_SECRET_ACCESS_KEY=replace_me
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-6
```

Run backend:

```bash
./venv/bin/uvicorn app.main:app --reload
```

Backend base URL: `http://localhost:8000`

### 4) Frontend setup

```bash
cd ../frontend
npm install
cp .env.example .env.local
```

Edit `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run frontend:

```bash
npm run dev
```

Frontend URL: `http://localhost:3000`

## Makefile Commands

From project root:

```bash
make install    # install backend+frontend deps
make db-up      # start postgres
make migrate    # run alembic migrations
make backend    # run backend
make frontend   # run frontend
```

## API Overview

### Auth
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

### Courses and lessons
- `POST /api/courses/generate`
- `GET /api/courses/user/courses`
- `GET /api/courses/{course_id}`
- `DELETE /api/courses/{course_id}`
- `GET /api/courses/lessons/{lesson_id}`
- `POST /api/courses/lessons/{lesson_id}/progress`
- `GET /api/courses/{course_id}/progress`

### Admin
- `POST /api/admin/register`
- `GET /api/admin/stats`
- `GET /api/admin/insights?days=14`
- `GET /api/admin/users`
- `PATCH /api/admin/users/{user_id}/plan`
- `PATCH /api/admin/users/{user_id}/status`

## Security and Access Rules

- All course and lesson fetch/update operations are owner-scoped.
- Users cannot access another user's course/lesson via ID injection.
- Inactive users are blocked from login and protected routes.
- Admin endpoints require authenticated admin user.

## Notes

- Keep `.env` files out of version control.
- If Google Fonts are blocked in your environment, Next.js build may fail on font fetch.
- For production, tighten CORS and rotate all secrets/keys.

## Roadmap

- End-of-course final assessment.
- Capstone/project-based completion flow.
- Trend charts and exportable analytics in admin panel.
