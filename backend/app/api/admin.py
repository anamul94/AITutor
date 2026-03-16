from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import and_, case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_db
from app.core.config import settings
from app.core.runtime_settings import get_premium_trial_days, set_premium_trial_days
from app.core.security import get_password_hash
from app.models.course import Course, LLMUsageEvent, Lesson, Module, UserProgress
from app.models.user import User
from app.schemas.course import CourseResponse, LessonContentResponse
from app.schemas.user import (
    AdminInsightsResponse,
    AdminRegisterRequest,
    AdminStatsResponse,
    AdminTrialDaysResponse,
    AdminTrialDaysUpdateRequest,
    AdminUserPlanUpdateRequest,
    AdminUserStatusUpdateRequest,
    DailyRegistrationStat,
    TokenUsageByModelStat,
    TokenUsageByUserStat,
    UserResponse,
)

router = APIRouter()


def get_day_window_utc() -> tuple[datetime, datetime]:
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    return start_of_day, end_of_day


async def attach_course_progress_percentages(
    db: AsyncSession,
    user_id: int,
    courses: list[Course],
) -> None:
    if not courses:
        return

    course_ids = [course.id for course in courses]
    total_lessons_by_course = {
        course.id: sum(len(module.lessons) for module in course.modules)
        for course in courses
    }

    completed_result = await db.execute(
        select(Module.course_id, func.count(func.distinct(UserProgress.lesson_id)))
        .select_from(UserProgress)
        .join(Lesson, UserProgress.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .where(Module.course_id.in_(course_ids))
        .where(UserProgress.user_id == user_id)
        .where(UserProgress.is_completed.is_(True))
        .group_by(Module.course_id)
    )
    completed_by_course = {
        course_id: int(completed_count)
        for course_id, completed_count in completed_result.all()
    }

    for course in courses:
        total_lessons = total_lessons_by_course.get(course.id, 0)
        completed_lessons = completed_by_course.get(course.id, 0)
        progress_percentage = (completed_lessons * 100.0 / total_lessons) if total_lessons else 0.0
        setattr(course, "progress_percentage", round(progress_percentage, 1))


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_admin(admin_in: AdminRegisterRequest, db: AsyncSession = Depends(get_db)):
    if admin_in.admin_key != settings.ADMIN_REGISTRATION_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin registration key")

    existing = await db.execute(select(User).where(User.email == admin_in.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    admin_user = User(
        email=admin_in.email,
        hashed_password=get_password_hash(admin_in.password),
        is_admin=True,
        plan_type="premium",
        trial_expires_at=None,
    )
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    return admin_user


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
):
    start_of_day, end_of_day = get_day_window_utc()

    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = int(total_users_result.scalar() or 0)

    users_today_result = await db.execute(
        select(func.count(User.id))
        .where(User.created_at >= start_of_day)
        .where(User.created_at < end_of_day)
    )
    users_registered_today = int(users_today_result.scalar() or 0)

    # "Active users" means users who generated any LLM-backed content today.
    active_users_result = await db.execute(
        select(func.count(func.distinct(LLMUsageEvent.user_id)))
        .where(LLMUsageEvent.user_id.is_not(None))
        .where(LLMUsageEvent.created_at >= start_of_day)
        .where(LLMUsageEvent.created_at < end_of_day)
    )
    active_users = int(active_users_result.scalar() or 0)

    courses_today_result = await db.execute(
        select(func.count(Course.id))
        .where(Course.created_at >= start_of_day)
        .where(Course.created_at < end_of_day)
    )
    courses_generated_today = int(courses_today_result.scalar() or 0)

    lessons_today_result = await db.execute(
        select(func.count(Lesson.id))
        .where(Lesson.content_generated_at.is_not(None))
        .where(Lesson.content_generated_at >= start_of_day)
        .where(Lesson.content_generated_at < end_of_day)
    )
    lessons_generated_today = int(lessons_today_result.scalar() or 0)

    total_tokens_result = await db.execute(select(func.coalesce(func.sum(LLMUsageEvent.total_tokens), 0)))
    total_token_usage = int(total_tokens_result.scalar() or 0)

    today_tokens_result = await db.execute(
        select(func.coalesce(func.sum(LLMUsageEvent.total_tokens), 0))
        .where(LLMUsageEvent.created_at >= start_of_day)
        .where(LLMUsageEvent.created_at < end_of_day)
    )
    token_usage_today = int(today_tokens_result.scalar() or 0)

    return AdminStatsResponse(
        total_users=total_users,
        users_registered_today=users_registered_today,
        active_users=active_users,
        courses_generated_today=courses_generated_today,
        lessons_generated_today=lessons_generated_today,
        total_content_generated_today=courses_generated_today + lessons_generated_today,
        total_token_usage=total_token_usage,
        token_usage_today=token_usage_today,
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc(), User.id.desc()))
    return result.scalars().all()


@router.get("/users/{user_id}/courses", response_model=list[CourseResponse])
async def list_user_courses(
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
):
    user_result = await db.execute(select(User).where(User.id == user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await db.execute(
        select(Course)
        .options(selectinload(Course.modules).selectinload(Module.lessons))
        .where(Course.created_by == user_id)
        .order_by(Course.created_at.desc(), Course.id.desc())
    )
    courses = result.scalars().all()
    await attach_course_progress_percentages(db, user_id, courses)
    return courses


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_admin_course(
    course_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Course)
        .options(selectinload(Course.modules).selectinload(Module.lessons))
        .where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    await attach_course_progress_percentages(db, course.created_by, [course])
    return course


@router.get("/lessons/{lesson_id}", response_model=LessonContentResponse)
async def get_admin_lesson(
    lesson_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Lesson)
        .options(selectinload(Lesson.module).selectinload(Module.course))
        .where(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    return {
        "id": lesson.id,
        "module_id": lesson.module_id,
        "course_id": lesson.module.course_id,
        "title": lesson.title,
        "description": lesson.description,
        "content": lesson.content,
        "quiz_data": lesson.quiz_data,
        "progress": [],
    }


@router.patch("/users/{user_id}/plan", response_model=UserResponse)
async def update_user_plan(
    payload: AdminUserPlanUpdateRequest,
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin plan cannot be changed from this endpoint",
        )

    target_user.plan_type = payload.plan_type
    # Manual admin assignment should remain stable (non-expiring) until changed again.
    target_user.trial_expires_at = None

    db.add(target_user)
    await db.commit()
    await db.refresh(target_user)
    return target_user


@router.patch("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    payload: AdminUserStatusUpdateRequest,
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin status cannot be changed from this endpoint",
        )

    target_user.is_active = payload.is_active
    db.add(target_user)
    await db.commit()
    await db.refresh(target_user)
    return target_user


@router.get("/insights", response_model=AdminInsightsResponse)
async def get_admin_insights(
    days: int = Query(default=14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
):
    start_of_day, end_of_day = get_day_window_utc()
    lookback_start = start_of_day - timedelta(days=days - 1)

    daily_rows_result = await db.execute(
        select(func.date(User.created_at).label("day"), func.count(User.id).label("user_count"))
        .where(User.created_at >= lookback_start)
        .where(User.created_at < end_of_day)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    rows_by_date = {
        day.isoformat(): int(user_count)
        for day, user_count in daily_rows_result.all()
        if day is not None
    }

    daily_registrations: list[DailyRegistrationStat] = []
    for offset in range(days):
        day = (lookback_start + timedelta(days=offset)).date().isoformat()
        daily_registrations.append(
            DailyRegistrationStat(
                date=day,
                user_count=rows_by_date.get(day, 0),
            )
        )

    today_users_result = await db.execute(
        select(User)
        .where(User.created_at >= start_of_day)
        .where(User.created_at < end_of_day)
        .order_by(User.created_at.desc(), User.id.desc())
    )
    today_registered_users = today_users_result.scalars().all()

    today_usage_sum = func.coalesce(
        func.sum(
            case(
                (
                    and_(
                        LLMUsageEvent.created_at >= start_of_day,
                        LLMUsageEvent.created_at < end_of_day,
                    ),
                    LLMUsageEvent.total_tokens,
                ),
                else_=0,
            )
        ),
        0,
    )
    total_usage_sum = func.coalesce(func.sum(LLMUsageEvent.total_tokens), 0)

    token_usage_result = await db.execute(
        select(
            User.id,
            User.email,
            total_usage_sum.label("total_tokens"),
            today_usage_sum.label("token_usage_today"),
        )
        .outerjoin(LLMUsageEvent, LLMUsageEvent.user_id == User.id)
        .group_by(User.id, User.email)
        .order_by(total_usage_sum.desc(), User.id.asc())
    )

    token_usage_per_user = [
        TokenUsageByUserStat(
            user_id=int(user_id),
            email=email,
            total_tokens=int(total_tokens or 0),
            token_usage_today=int(token_usage_today or 0),
        )
        for user_id, email, total_tokens, token_usage_today in token_usage_result.all()
    ]

    today_input_usage_sum = func.coalesce(
        func.sum(
            case(
                (
                    and_(
                        LLMUsageEvent.created_at >= start_of_day,
                        LLMUsageEvent.created_at < end_of_day,
                    ),
                    LLMUsageEvent.input_tokens,
                ),
                else_=0,
            )
        ),
        0,
    )
    today_output_usage_sum = func.coalesce(
        func.sum(
            case(
                (
                    and_(
                        LLMUsageEvent.created_at >= start_of_day,
                        LLMUsageEvent.created_at < end_of_day,
                    ),
                    LLMUsageEvent.output_tokens,
                ),
                else_=0,
            )
        ),
        0,
    )
    today_total_usage_sum = func.coalesce(
        func.sum(
            case(
                (
                    and_(
                        LLMUsageEvent.created_at >= start_of_day,
                        LLMUsageEvent.created_at < end_of_day,
                    ),
                    LLMUsageEvent.total_tokens,
                ),
                else_=0,
            )
        ),
        0,
    )
    model_provider_label = func.coalesce(LLMUsageEvent.model_provider, literal("unknown")).label("model_provider")
    model_name_label = func.coalesce(LLMUsageEvent.model_name, literal("unknown")).label("model_name")
    token_usage_by_model_result = await db.execute(
        select(
            model_provider_label,
            model_name_label,
            func.coalesce(func.sum(LLMUsageEvent.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(LLMUsageEvent.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(LLMUsageEvent.total_tokens), 0).label("total_tokens"),
            today_input_usage_sum.label("input_tokens_today"),
            today_output_usage_sum.label("output_tokens_today"),
            today_total_usage_sum.label("total_tokens_today"),
        )
        .group_by(model_provider_label, model_name_label)
        .order_by(func.coalesce(func.sum(LLMUsageEvent.total_tokens), 0).desc(), model_provider_label.asc(), model_name_label.asc())
    )
    token_usage_by_model = [
        TokenUsageByModelStat(
            model_provider=str(model_provider or "unknown"),
            model_name=str(model_name or "unknown"),
            input_tokens=int(input_tokens or 0),
            output_tokens=int(output_tokens or 0),
            total_tokens=int(total_tokens or 0),
            input_tokens_today=int(input_tokens_today or 0),
            output_tokens_today=int(output_tokens_today or 0),
            total_tokens_today=int(total_tokens_today or 0),
        )
        for (
            model_provider,
            model_name,
            input_tokens,
            output_tokens,
            total_tokens,
            input_tokens_today,
            output_tokens_today,
            total_tokens_today,
        ) in token_usage_by_model_result.all()
    ]

    return AdminInsightsResponse(
        lookback_days=days,
        daily_registrations=daily_registrations,
        today_registered_users=today_registered_users,
        token_usage_per_user=token_usage_per_user,
        token_usage_by_model=token_usage_by_model,
    )


@router.get("/settings/trial-days", response_model=AdminTrialDaysResponse)
async def get_trial_days_setting(
    db: AsyncSession = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
):
    premium_trial_days = await get_premium_trial_days(db)
    return AdminTrialDaysResponse(premium_trial_days=premium_trial_days)


@router.put("/settings/trial-days", response_model=AdminTrialDaysResponse)
async def update_trial_days_setting(
    payload: AdminTrialDaysUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
):
    premium_trial_days = await set_premium_trial_days(db, payload.premium_trial_days)
    return AdminTrialDaysResponse(premium_trial_days=premium_trial_days)
