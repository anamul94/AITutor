from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Literal, Optional

PlanType = Literal["free", "premium"]

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class AdminRegisterRequest(UserBase):
    password: str
    admin_key: str

class AdminUserPlanUpdateRequest(BaseModel):
    plan_type: PlanType

class AdminUserStatusUpdateRequest(BaseModel):
    is_active: bool

class AdminTrialDaysUpdateRequest(BaseModel):
    premium_trial_days: int = Field(ge=0, le=365)

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    plan_type: PlanType
    trial_expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

class AdminStatsResponse(BaseModel):
    total_users: int
    users_registered_today: int
    active_users: int
    courses_generated_today: int
    lessons_generated_today: int
    total_content_generated_today: int
    total_token_usage: int
    token_usage_today: int


class DailyRegistrationStat(BaseModel):
    date: str
    user_count: int


class TokenUsageByUserStat(BaseModel):
    user_id: int
    email: EmailStr
    total_tokens: int
    token_usage_today: int


class AdminInsightsResponse(BaseModel):
    lookback_days: int = Field(ge=1, le=90)
    daily_registrations: list[DailyRegistrationStat]
    today_registered_users: list[UserResponse]
    token_usage_per_user: list[TokenUsageByUserStat]


class AdminTrialDaysResponse(BaseModel):
    premium_trial_days: int
