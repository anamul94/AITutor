from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.course import Course, Module, Lesson, UserProgress
from app.schemas.course import CourseGenerateRequest, CourseResponse, LessonContentResponse, UserProgressResponse, UserProgressRequest
from app.core.llm import generate_course_syllabus, generate_lesson_content

router = APIRouter()

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

@router.post("/generate", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def generate_and_save_course(
    request: CourseGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Takes a topic, asks the LLM to generate a syllabus structure, and saves it to the database.
    """
    topic = request.topic
    
    # 1. Ask LLM to generate the syllabus
    try:
        generated_course = await generate_course_syllabus(
            topic=topic,
            learning_goal=request.learning_goal,
            preferred_level=request.preferred_level,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Generation failed: {str(e)}")

    # 2. Save Course to DB
    new_course = Course(
        title=generated_course.title,
        description=generated_course.description,
        topic=topic,
        learning_goal=request.learning_goal,
        preferred_level=request.preferred_level,
        created_by=current_user.id
    )
    db.add(new_course)
    await db.flush() # flush to get the course ID

    # 3. Save Modules and Lessons to DB
    for g_module in generated_course.modules:
        new_module = Module(
            course_id=new_course.id,
            title=g_module.title,
            order_index=g_module.order_index
        )
        db.add(new_module)
        await db.flush()

        for g_lesson in g_module.lessons:
            new_lesson = Lesson(
                module_id=new_module.id,
                title=g_lesson.title,
                description=g_lesson.description,
                order_index=g_lesson.order_index
            )
            db.add(new_lesson)
            
    await db.commit()
    
    # Reload Course with relationships so we can return it
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons)
        )
        .where(Course.id == new_course.id)
    )
    final_course = result.scalar_one_or_none()

    if final_course:
        await attach_course_progress_percentages(db, current_user.id, [final_course])

    return final_course

@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch a course structure by ID.
    """
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons)
        )
        .where(Course.id == course_id)
        .where(Course.created_by == current_user.id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    await attach_course_progress_percentages(db, current_user.id, [course])
    return course

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a course owned by the current user.
    """
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .where(Course.created_by == current_user.id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    await db.delete(course)
    await db.commit()

@router.get("/user/courses", response_model=list[CourseResponse])
async def get_user_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch all courses created by the current user.
    """
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons)
        )
        .where(Course.created_by == current_user.id)
        .order_by(Course.created_at.desc(), Course.id.desc())
    )
    courses = result.scalars().all()
    await attach_course_progress_percentages(db, current_user.id, courses)
    return courses

@router.get("/lessons/{lesson_id}", response_model=LessonContentResponse)
async def get_or_generate_lesson_content(
    lesson_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch a lesson's content. If it hasn't been generated yet, use the LLM to write the content
    and create a quiz, then save it and return it. JIT (Just-In-Time) Generation.
    """
    # Load lesson only if it belongs to the current user (prevents IDOR via lesson_id).
    result = await db.execute(
        select(Lesson)
        .options(
            selectinload(Lesson.module).selectinload(Module.course),
        )
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(Lesson.id == lesson_id)
        .where(Course.created_by == current_user.id)
    )
    lesson = result.scalar_one_or_none()
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    progress_result = await db.execute(
        select(UserProgress)
        .where(UserProgress.lesson_id == lesson.id)
        .where(UserProgress.user_id == current_user.id)
    )
    current_user_progress = progress_result.scalars().all()

    def format_response(l: Lesson, progress_rows: list[UserProgress]):
        return {
            "id": l.id,
            "module_id": l.module_id,
            "course_id": l.module.course_id,
            "title": l.title,
            "description": l.description,
            "content": l.content,
            "quiz_data": l.quiz_data,
            "progress": progress_rows
        }

    # If content already exists, return it!
    if lesson.content:
        return format_response(lesson, current_user_progress)
        
    # Content does NOT exist. We need to generate it just in time!
    try:
        generated_data = await generate_lesson_content(
            course_title=lesson.module.course.title,
            module_title=lesson.module.title,
            lesson_title=lesson.title,
            lesson_description=lesson.description,
            learning_goal=lesson.module.course.learning_goal,
            preferred_level=lesson.module.course.preferred_level,
        )
        
        # Save generated content to database
        lesson.content = generated_data.content_markdown
        # Quizzes come back as Pydantic objects, dump to dict to store in JSONB
        lesson.quiz_data = [q.model_dump() for q in generated_data.quiz]
        
        await db.commit()
        await db.refresh(lesson)
        
        return format_response(lesson, current_user_progress)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LLM Generation failed: {repr(e)}")

@router.get("/{course_id}/progress", response_model=list[UserProgressResponse])
async def get_course_progress(
    course_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user progress for all lessons in a course.
    """
    course_result = await db.execute(
        select(Course.id)
        .where(Course.id == course_id)
        .where(Course.created_by == current_user.id)
    )
    if not course_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Course not found")

    result = await db.execute(
        select(UserProgress)
        .join(Lesson, UserProgress.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .where(Module.course_id == course_id)
        .where(UserProgress.user_id == current_user.id)
    )
    return result.scalars().all()

@router.post("/lessons/{lesson_id}/progress", response_model=UserProgressResponse)
async def update_lesson_progress(
    progress_req: UserProgressRequest,
    lesson_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update or create a user's progress for a specific lesson.
    """
    owned_lesson_result = await db.execute(
        select(Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(Lesson.id == lesson_id)
        .where(Course.created_by == current_user.id)
    )
    if not owned_lesson_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Check if progress exists
    result = await db.execute(
        select(UserProgress)
        .where(UserProgress.lesson_id == lesson_id)
        .where(UserProgress.user_id == current_user.id)
    )
    progress = result.scalar_one_or_none()
    
    if progress:
        progress.is_completed = progress_req.is_completed
        if progress_req.quiz_score is not None:
            progress.quiz_score = progress_req.quiz_score
    else:
        progress = UserProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            is_completed=progress_req.is_completed,
            quiz_score=progress_req.quiz_score
        )
        db.add(progress)
        
    await db.commit()
    await db.refresh(progress)
    return progress
