from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.course import Course, LLMUsageEvent, Lesson
from app.models.user import User
from app.schemas.user import (
    AdminInsightsResponse,
    AdminRegisterRequest,
    AdminStatsResponse,
    AdminUserPlanUpdateRequest,
    AdminUserStatusUpdateRequest,
    DailyRegistrationStat,
    TokenUsageByUserStat,
    UserResponse,
)

router = APIRouter()


def get_day_window_utc() -> tuple[datetime, datetime]:
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    return start_of_day, end_of_day


# @router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
# async def register_admin(admin_in: AdminRegisterRequest, db: AsyncSession = Depends(get_db)):
#     if admin_in.admin_key != settings.ADMIN_REGISTRATION_KEY:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin registration key")
#
#     existing = await db.execute(select(User).where(User.email == admin_in.email))
#     if existing.scalar_one_or_none():
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")
#
#     admin_user = User(
#         email=admin_in.email,
#         hashed_password=get_password_hash(admin_in.password),
#         is_admin=True,
#         plan_type="premium",
#         trial_expires_at=None,
#     )
#     db.add(admin_user)
#     await db.commit()
#     await db.refresh(admin_user)
#     return admin_user


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

    return AdminInsightsResponse(
        lookback_days=days,
        daily_registrations=daily_registrations,
        today_registered_users=today_registered_users,
        token_usage_per_user=token_usage_per_user,
    )
