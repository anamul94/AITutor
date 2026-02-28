# AITutor

AI-native learning platform that turns a topic into a complete course, generates lessons on demand, and tracks learner/admin analytics.

> Generate course -> open lesson -> get structured content + quiz -> mark progress.

## Demo

- Learner flow: topic to full syllabus in one click
- Lesson flow: just-in-time lesson generation with quiz
- Admin flow: user control (plan/status) + usage analytics

### Screenshots

> Add your screenshots to `docs/screenshots/` using the filenames below.

![Dashboard](docs/screenshots/dashboard.png)
![Course Syllabus](docs/screenshots/course-syllabus.png)
![Lesson View](docs/screenshots/lesson-view.png)
![Admin Analytics](docs/screenshots/admin-analytics.png)

## Why It Stands Out

- **Adaptive generation**: supports learning goal + preferred level (`beginner/intermediate/advanced/auto`).
- **Pedagogical structure**: lessons follow a strict instructional template for consistent quality.
- **Built-in assessment**: every lesson includes a 3-question MCQ quiz with explanations.
- **Just-in-time lesson generation**: compute is used only when content is opened.
- **Plan-aware access control**:
  - 1-day premium trial by default (admin-configurable)
  - automatic downgrade to free
  - free limits: 1 course/day, 2 lessons/day
- **Admin operations**:
  - make user premium/free
  - activate/deactivate user
  - date-wise registration insights
  - per-user token usage (today + total)
- **Production-minded safeguards**:
  - user-level data isolation (prevents cross-user lesson access)
  - proper 429 handling for plan limits
  - concurrency guard to prevent duplicate lesson token logging

## Quick Start

```bash
# 1) DB
docker compose up -d

# 2) Backend
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
./venv/bin/alembic upgrade head
./venv/bin/uvicorn app.main:app --reload

# 3) Frontend
cd ../frontend
npm install
cp .env.example .env.local
npm run dev
```

Open:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

## Environment

Backend (`backend/.env`):
- `DATABASE_URL`
- `SECRET_KEY`
- `ADMIN_REGISTRATION_KEY`
- `PREMIUM_TRIAL_DAYS`
- `FREE_DAILY_COURSE_LIMIT`
- `FREE_DAILY_LESSON_LIMIT`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `BEDROCK_MODEL_ID`

Frontend (`frontend/.env.local`):
- `NEXT_PUBLIC_API_URL=http://localhost:8000`

## API Highlights

- `POST /api/courses/generate`
- `GET /api/courses/lessons/{lesson_id}`
- `POST /api/courses/lessons/{lesson_id}/progress`
- `GET /api/admin/stats`
- `GET /api/admin/insights`
- `PATCH /api/admin/users/{user_id}/plan`
- `PATCH /api/admin/users/{user_id}/status`
- `GET /api/admin/settings/trial-days`
- `PUT /api/admin/settings/trial-days`

## License

Specify your license here (e.g., MIT).
