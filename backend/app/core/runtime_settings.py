from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.settings import AppSetting

PREMIUM_TRIAL_DAYS_KEY = "premium_trial_days"


def normalize_trial_days(value: int) -> int:
    return max(0, min(365, int(value)))


async def get_premium_trial_days(db: AsyncSession) -> int:
    result = await db.execute(
        select(AppSetting).where(AppSetting.key == PREMIUM_TRIAL_DAYS_KEY)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        return normalize_trial_days(settings.PREMIUM_TRIAL_DAYS)

    try:
        return normalize_trial_days(int(setting.value))
    except (TypeError, ValueError):
        return normalize_trial_days(settings.PREMIUM_TRIAL_DAYS)


async def set_premium_trial_days(db: AsyncSession, days: int) -> int:
    normalized_days = normalize_trial_days(days)
    result = await db.execute(
        select(AppSetting).where(AppSetting.key == PREMIUM_TRIAL_DAYS_KEY)
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = str(normalized_days)
    else:
        setting = AppSetting(key=PREMIUM_TRIAL_DAYS_KEY, value=str(normalized_days))
        db.add(setting)

    await db.commit()
    return normalized_days
