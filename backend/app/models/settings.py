from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func

from app.models.user import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(String(255), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
