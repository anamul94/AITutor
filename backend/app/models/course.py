from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.user import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    topic = Column(String, index=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", backref="courses")
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")

class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)

    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    title = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=True)  # Markdown content generated dynamically
    quiz_data = Column(JSON, nullable=True) # JSON generated dynamically

    module = relationship("Module", back_populates="lessons")
    progress = relationship("UserProgress", back_populates="lesson", cascade="all, delete-orphan")

class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    is_completed = Column(Boolean, default=False)
    quiz_score = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="progress")
    lesson = relationship("Lesson", back_populates="progress")
